"""
Status Manager for handling status bar, connection status, and UI status updates
"""
import logging
from typing import Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QLabel, QStatusBar, QProgressBar

logger = logging.getLogger(__name__)

class StatusManager(QObject):
    """
    Manages all status-related UI elements and updates
    """
    
    # Signals for status changes
    status_updated = pyqtSignal(str)  # status_message
    connection_status_updated = pyqtSignal(str, str)  # status_text, style
    progress_updated = pyqtSignal(int)  # progress_value
    
    def __init__(self, connection_status_label: QLabel, toolbar_status_label: QLabel, 
                 status_bar: QStatusBar, progress_bar: QProgressBar):
        super().__init__()
        
        # UI elements
        self.connection_status_label = connection_status_label
        self.toolbar_status_label = toolbar_status_label
        self.status_bar = status_bar
        self.progress_bar = progress_bar
        
        # Status tracking
        self.current_connection_status = {}
        self.current_message = ""
        self.is_loading = False
        
        # Initialize status
        self._initialize_status()
    
    def _initialize_status(self):
        """Initialize status elements to default state"""
        self.update_connection_status({'salesforce': False, 'woocommerce': False, 'avalara': False})
        self.update_status_message("Ready")
        self.hide_progress()
    
    def update_connection_status(self, connection_status: Dict[str, bool]):
        """
        Update connection status display based on API connection states
        
        Args:
            connection_status: Dictionary with connection status for each API
        """
        try:
            self.current_connection_status = connection_status.copy()
            
            # Calculate connection summary
            sf_connected = connection_status.get('salesforce', False)
            woo_connected = connection_status.get('woocommerce', False)
            avalara_connected = connection_status.get('avalara', False)

            connected_count = sum([sf_connected, woo_connected, avalara_connected])

            # Generate status text and styling
            if connected_count == 3:
                status_text = "All Connected"
                style = "color: green; font-weight: bold;"
                status_message = "All APIs connected successfully"
            elif connected_count > 0:
                status_text = f"{connected_count}/3 Connected"
                style = "color: orange; font-weight: bold;"
                status_message = f"{connected_count} of 3 APIs connected"
            else:
                status_text = "Not Connected"
                style = "color: red; font-weight: bold;"
                status_message = "No API connections"
            
            # Update UI elements
            self.connection_status_label.setText(status_text)
            self.connection_status_label.setStyleSheet(style)
            
            self.toolbar_status_label.setText(status_text)
            self.toolbar_status_label.setStyleSheet(style)
            
            # Update status bar if not currently showing other messages
            if not self.is_loading:
                self.status_bar.showMessage(status_message)
                self.current_message = status_message
            
            # Emit signal
            self.connection_status_updated.emit(status_text, style)
            
            logger.info(f"[STATUS-MANAGER] Connection status updated: {status_text} ({connected_count}/3)")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error updating connection status: {e}")
    
    def update_individual_connection_status(self, api_type: str, connected: bool):
        """
        Update connection status for a specific API

        Args:
            api_type: The API type ('salesforce', 'woocommerce', 'avalara')
            connected: Whether the API is connected
        """
        if api_type in self.current_connection_status:
            self.current_connection_status[api_type] = connected
            self.update_connection_status(self.current_connection_status)
    
    def update_status_message(self, message: str, timeout: int = 0):
        """
        Update status bar message
        
        Args:
            message: Message to display
            timeout: Timeout in milliseconds (0 = permanent)
        """
        try:
            self.status_bar.showMessage(message, timeout)
            self.current_message = message
            self.status_updated.emit(message)
            
            logger.info(f"[STATUS-MANAGER] Status message updated: {message}")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error updating status message: {e}")
    
    def show_temporary_message(self, message: str, timeout: int = 5000):
        """
        Show a temporary message that will revert to the previous message
        
        Args:
            message: Temporary message to show
            timeout: Timeout in milliseconds
        """
        try:
            previous_message = self.current_message
            self.status_bar.showMessage(message, timeout)
            
            # Use QTimer to restore previous message after timeout
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(timeout, lambda: self.status_bar.showMessage(previous_message))
            
            logger.info(f"[STATUS-MANAGER] Temporary message shown: {message}")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error showing temporary message: {e}")
    
    def show_progress(self, message: str = "Loading..."):
        """
        Show progress bar and loading message
        
        Args:
            message: Loading message to display
        """
        try:
            self.is_loading = True
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.update_status_message(message)
            
            logger.info(f"[STATUS-MANAGER] Progress shown: {message}")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error showing progress: {e}")
    
    def update_progress(self, value: int, message: str = None):
        """
        Update progress bar value and optionally message
        
        Args:
            value: Progress value (0-100)
            message: Optional message to update
        """
        try:
            self.progress_bar.setValue(value)
            
            if message:
                self.update_status_message(message)
            
            self.progress_updated.emit(value)
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error updating progress: {e}")
    
    def hide_progress(self):
        """Hide progress bar and restore normal status"""
        try:
            self.is_loading = False
            self.progress_bar.setVisible(False)
            self.progress_bar.setValue(0)
            
            # Restore connection status message
            if self.current_connection_status:
                connected_count = sum(self.current_connection_status.values())
                if connected_count == 3:
                    message = "All APIs connected successfully"
                elif connected_count > 0:
                    message = f"{connected_count} of 3 APIs connected"
                else:
                    message = "Ready"
                
                self.update_status_message(message)
            
            logger.info("[STATUS-MANAGER] Progress hidden")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error hiding progress: {e}")
    
    def show_error(self, message: str, timeout: int = 10000):
        """
        Show error message with red styling
        
        Args:
            message: Error message to display
            timeout: Timeout in milliseconds
        """
        try:
            # Store current styles
            connection_style = self.connection_status_label.styleSheet()
            toolbar_style = self.toolbar_status_label.styleSheet()
            
            # Apply error styling
            error_style = "color: red; font-weight: bold;"
            self.connection_status_label.setText("Error")
            self.connection_status_label.setStyleSheet(error_style)
            
            self.toolbar_status_label.setText("Error")
            self.toolbar_status_label.setStyleSheet(error_style)
            
            # Show error message
            self.show_temporary_message(f"Error: {message}", timeout)
            
            # Restore original styling after timeout
            from PyQt6.QtCore import QTimer
            def restore_styling():
                self.connection_status_label.setStyleSheet(connection_style)
                self.toolbar_status_label.setStyleSheet(toolbar_style)
                self.update_connection_status(self.current_connection_status)
            
            QTimer.singleShot(timeout, restore_styling)
            
            logger.error(f"[STATUS-MANAGER] Error shown: {message}")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error showing error message: {e}")
    
    def show_success(self, message: str, timeout: int = 3000):
        """
        Show success message with green styling
        
        Args:
            message: Success message to display
            timeout: Timeout in milliseconds
        """
        try:
            # Show success message
            self.show_temporary_message(f"Success: {message}", timeout)
            
            logger.info(f"[STATUS-MANAGER] Success shown: {message}")
            
        except Exception as e:
            logger.error(f"[STATUS-MANAGER] Error showing success message: {e}")
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """Get summary of current connection status"""
        connected_count = sum(self.current_connection_status.values())
        
        return {
            'connected_count': connected_count,
            'total_count': 3,
            'salesforce': self.current_connection_status.get('salesforce', False),
            'woocommerce': self.current_connection_status.get('woocommerce', False),
            'avalara': self.current_connection_status.get('avalara', False),
            'all_connected': connected_count == 3,
            'none_connected': connected_count == 0,
            'current_message': self.current_message,
            'is_loading': self.is_loading
        }
    
    def get_detailed_status(self) -> Dict[str, Any]:
        """Get detailed status information"""
        return {
            'connection_status': self.current_connection_status.copy(),
            'status_message': self.current_message,
            'is_loading': self.is_loading,
            'progress_value': self.progress_bar.value(),
            'progress_visible': self.progress_bar.isVisible()
        }
    
    def reset_status(self):
        """Reset all status elements to default state"""
        logger.info("[STATUS-MANAGER] Resetting status to default")
        
        self.current_connection_status = {'salesforce': False, 'woocommerce': False, 'avalara': False}
        self.current_message = ""
        self.is_loading = False
        
        self._initialize_status()
    
    def set_disconnected_state(self):
        """Set all status elements to disconnected state"""
        logger.info("[STATUS-MANAGER] Setting disconnected state")
        
        self.update_connection_status({'salesforce': False, 'woocommerce': False, 'avalara': False})
        self.update_status_message("Disconnected")
        self.hide_progress()