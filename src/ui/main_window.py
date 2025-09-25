"""
Main application window for Salesforce Report Pull
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QMenuBar, QStatusBar, QToolBar, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QProgressBar, QMessageBox,
    QFrame, QApplication, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon
import qtawesome as qta
import qdarkstyle

from src.models.config import ConfigManager, SalesforceConfig
from src.services.async_jwt_salesforce_api import AsyncJWTSalesforceAPI
from src.services.async_woocommerce_api import AsyncWooCommerceAPI
from src.services.async_avalara_api import AsyncAvalaraAPI
from src.services.async_quickbase_api import AsyncQuickBaseAPI
from src.ui.settings_dialog import SettingsDialog
from src.ui.data_grid import InteractiveDataGrid
from src.ui.tabs.source_data_tab import SourceDataTab
from src.ui.tabs.operations_tab import OperationsTab
from src.ui.managers import ConnectionManager, TreePopulationManager, DataSourceManager, StatusManager

logger = logging.getLogger(__name__)


# Import worker classes from separate module
from .workers import SalesforceConnectionWorker, AsyncAutoConnectWorker

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize configuration
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # Remove async integration for now
        self._async_runner = None
        
        # API instances will be managed by ConnectionManager
        self.sf_api: Optional[AsyncJWTSalesforceAPI] = None
        self.woo_api: Optional[AsyncWooCommerceAPI] = None
        self.avalara_api: Optional[AsyncAvalaraAPI] = None
        self.quickbase_api: Optional[AsyncQuickBaseAPI] = None
        self.connection_worker: Optional[SalesforceConnectionWorker] = None
        self.reports_worker: Optional[SalesforceConnectionWorker] = None
        self.data_worker: Optional[SalesforceConnectionWorker] = None
        self.auto_connect_worker: Optional[AsyncAutoConnectWorker] = None
        
        # Store API instances for persistence across API switches
        self.api_instances = {}
        
        # Store async-loaded data for tree population
        self.async_sf_reports = []
        self.async_woo_data_sources = []
        self.async_avalara_data_sources = []
        self.async_quickbase_data_sources = []
        
        # Connection state tracking
        self.sf_connected = False
        self.woo_connected = False
        self.avalara_connected = False
        self.quickbase_connected = False
        
        
        # Setup UI
        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_status_bar()
        
        # Apply theme
        self.apply_theme()
        
        # Load saved window state
        self.restore_window_state()
        
        # Initialize managers after UI setup
        self.initialize_managers()
        
        # Auto-connect to all APIs on startup using async worker
        QTimer.singleShot(1000, self.async_auto_connect_all_apis)
    
    def initialize_managers(self):
        """Initialize manager classes for handling different aspects of the application"""
        # Initialize Connection Manager
        self.connection_manager = ConnectionManager(self.config_manager)
        
        # Use ConnectionManager's API instances
        self.sf_api = self.connection_manager.get_api_instance('salesforce')
        self.woo_api = self.connection_manager.get_api_instance('woocommerce')
        self.avalara_api = self.connection_manager.get_api_instance('avalara')
        self.quickbase_api = self.connection_manager.get_api_instance('quickbase')
        
        # Initialize Tree Population Manager
        self.tree_manager = TreePopulationManager(self.source_data_tab.data_tree)
        
        # Initialize Data Source Manager
        self.data_manager = DataSourceManager()
        
        # Initialize Status Manager
        self.status_manager = StatusManager(
            self.source_data_tab.connection_status,
            self.toolbar_status,
            self.status_bar,
            self.progress_bar
        )
        
        # Connect manager signals - use adapter methods to handle signal format conversion
        self.connection_manager.connection_status_changed.connect(self.on_individual_connection_status_changed)
        # Note: tree_manager will be updated via the adapter method
        self.data_manager.data_loaded.connect(self.on_report_data_loaded)
        self.data_manager.data_loading_error.connect(self.on_data_loading_error)
        
        logger.info("[MANAGERS] All managers initialized successfully")
    
    def setup_ui(self):
        """Setup main user interface"""
        self.setWindowTitle("Salesforce Report Pull - Multi-API Data Integration")
        self.setMinimumSize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Create main tab widget
        self.main_tabs = QTabWidget()
        main_layout.addWidget(self.main_tabs)
        
        # Create Source Data tab
        from src.ui.tabs.source_data_tab import SourceDataTab
        self.source_data_tab = SourceDataTab(self)
        self.source_data_tab.load_data_requested.connect(self.load_data_source)
        # Removed manual connection dialog - auto-connect handles all authentication
        self.main_tabs.addTab(self.source_data_tab, "Source Data")
        
        # Create Operations tab
        from src.ui.tabs.operations_tab import OperationsTab
        self.operations_tab = OperationsTab(self)
        self.main_tabs.addTab(self.operations_tab, "Operations")
        
        # Create Visualization tab
        from src.ui.tabs.visualization_tab import VisualizationTab
        self.visualization_tab = VisualizationTab(self)
        self.main_tabs.addTab(self.visualization_tab, "Visualization")
        
        # Keep references to commonly used widgets for compatibility
        self.data_tree = self.source_data_tab.data_tree
        self.connection_status = self.source_data_tab.connection_status
        self.search_box = self.source_data_tab.search_box
        self.load_btn = self.source_data_tab.load_btn
        self.tab_widget = self.source_data_tab.tab_widget
    
    def load_data_source(self, data_source: dict):
        """Handle data source loading request from source data tab"""
        api_type = data_source.get('api_type')
        
        if api_type == "salesforce":
            self.load_salesforce_report_data(data_source)
        elif api_type == "woocommerce":
            self.load_woocommerce_data_source(data_source)
        elif api_type == "avalara":
            self.load_avalara_data_source(data_source)
        elif api_type == "quickbase":
            self.load_quickbase_data_source(data_source)
        else:
            logger.error(f"Unknown API type: {api_type}")
            QMessageBox.warning(self, "Unknown API", f"Unknown API type: {api_type}")
    
    def load_salesforce_report_data(self, report_data):
        """Load Salesforce report data"""
        logger.info(f"[UI-LOAD-SF] Loading Salesforce report: {report_data['name']} (ID: {report_data['id']})")
        
        # Check if we have an API connection
        if not self.sf_api:
            logger.error("[UI-LOAD-SF] No Salesforce API connection")
            QMessageBox.warning(self, "No Connection", "Please connect to Salesforce first.")
            return
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_bar.showMessage(f"Loading report data: {report_data['name']}...")
        
        # Detect if this is a custom report (SOQL query) vs standard report (Salesforce report ID)
        is_custom_report = (
            report_data.get('type') == 'custom_report' or 
            (report_data['id'].strip().upper().startswith('SELECT') and 'FROM' in report_data['id'].upper())
        )
        
        if is_custom_report:
            # Route custom reports (SOQL queries) to the SOQL execution worker
            logger.info("[UI-LOAD-SF] Detected custom report - using SOQL execution path")
            self.data_worker = SalesforceConnectionWorker(
                "execute_soql",
                self.sf_api,
                query=report_data['id'],  # The 'id' field contains the SOQL query for custom reports
                source_name=report_data['name']
            )
        else:
            # Route standard reports to the traditional report data worker  
            logger.info("[UI-LOAD-SF] Detected standard report - using report data path")
            self.data_worker = SalesforceConnectionWorker(
                "load_report_data", 
                self.sf_api,
                report_id=report_data['id'],
                report_name=report_data['name'],
                start_date=report_data.get('start_date'),
                end_date=report_data.get('end_date'),
                date_field=report_data.get('date_field')
            )
        
        # Connect worker signals (both worker types emit report_data_loaded)
        self.data_worker.report_data_loaded.connect(self.on_report_data_loaded)
        self.data_worker.error_occurred.connect(self.on_data_loading_error)
        self.data_worker.finished.connect(self.on_data_worker_finished)
        self.data_worker.start()
        logger.info("[UI-LOAD-SF] SUCCESS Worker thread started")
    
    def load_woocommerce_data_source(self, data_source):
        """Load WooCommerce data source"""
        logger.info(f"[UI-LOAD-WOO] Loading WooCommerce data source: {data_source['name']}")
        
        # Check if we have an API connection
        if not self.woo_api:
            logger.error("[UI-LOAD-WOO] No WooCommerce API connection")
            QMessageBox.warning(self, "No Connection", "Please connect to WooCommerce first.")
            return
        
        # Show progress using status manager
        self.status_manager.show_progress(f"Loading WooCommerce data: {data_source['name']}...")
        
        try:
            # Get date range if provided
            start_date = data_source.get('start_date')
            end_date = data_source.get('end_date')
            
            # Log date range for client-side filtering
            if start_date and end_date:
                logger.info(f"[UI-LOAD-WOO] Date range available for client-side filtering: {start_date} to {end_date}")
            
            # Use data manager to load data
            self.data_manager.load_data_source(data_source, start_date, end_date)
            logger.info("[UI-LOAD-WOO] Data loading delegated to data manager")
                
        except Exception as e:
            logger.error(f"[UI-LOAD-WOO] ERROR loading WooCommerce data: {e}")
            logger.error("[UI-LOAD-WOO] Stack trace:", exc_info=True)
            self.status_manager.hide_progress()
            self.status_manager.show_error(f"Error loading {data_source['name']}: {str(e)}")
            QMessageBox.critical(self, "Loading Error", f"Error loading {data_source['name']}:\n{str(e)}")
    
    def on_report_data_loaded(self, dataframe, report_name: str):
        """Handle loaded report data"""
        logger.info("[UI-DATA-LOADED] " + "=" * 50)
        logger.info(f"[UI-DATA-LOADED] Report data loaded: {report_name}")
        logger.info(f"[UI-DATA-LOADED] Data shape: {dataframe.shape if dataframe is not None else 'None'}")
        logger.info("[UI-DATA-LOADED] " + "=" * 50)
        
        # Hide progress using status manager
        self.status_manager.hide_progress()
        
        if dataframe is None or len(dataframe) == 0:
            logger.warning("[UI-DATA-LOADED] Empty dataframe received")
            self.status_manager.show_temporary_message("No data found in report")
            QMessageBox.information(self, "No Data", f"No data found in report: {report_name}")
            return
        
        logger.info("[UI-DATA-LOADED] Creating data grid widget...")
        
        # Add to source data tab
        data_grid = self.source_data_tab.add_data_tab(dataframe, report_name)
        
        # Notify visualization tab about new dataset
        if hasattr(self, 'visualization_tab'):
            self.visualization_tab.add_dataset_from_grid(report_name, dataframe, data_grid)
        
        # Update status using status manager
        row_count = len(dataframe)
        col_count = len(dataframe.columns)
        self.status_manager.show_success(f"Loaded {report_name}: {row_count:,} rows, {col_count} columns", 5000)
        
        logger.info(f"[UI-DATA-LOADED] SUCCESS Data grid created and added to tab")
        logger.info("[UI-DATA-LOADED] " + "=" * 50)
    
    def on_data_loading_error(self, error_msg: str):
        """Handle data loading error"""
        logger.error("[UI-DATA-ERROR] " + "=" * 40)
        logger.error(f"[UI-DATA-ERROR] Data loading failed: {error_msg}")
        logger.error("[UI-DATA-ERROR] " + "=" * 40)
        
        # Hide progress and show error using status manager
        self.status_manager.hide_progress()
        self.status_manager.show_error(f"Data loading failed: {error_msg}")
        
        QMessageBox.critical(self, "Data Loading Error", 
                           f"Failed to load report data:\n{error_msg}")
    
    def load_avalara_data_source(self, data_source):
        """Load Avalara data source"""
        logger.info(f"[UI-LOAD-AVALARA] Loading Avalara data source: {data_source['name']}")
        
        # Check if we have an API connection
        if not self.avalara_api:
            logger.error("[UI-LOAD-AVALARA] No Avalara API connection")
            QMessageBox.warning(self, "No Connection", 
                              "Please connect to Avalara first.\n\n" +
                              "Make sure you have set your Avalara credentials in the .env file:\n" +
                              "AVALARA_ACCOUNT_ID=your_account_id\n" +
                              "AVALARA_LICENSE_KEY=your_license_key\n" +
                              "AVALARA_ENVIRONMENT=sandbox")
            return
        
        # Show progress using status manager
        self.status_manager.show_progress(f"Loading Avalara data: {data_source['name']}...")
        
        try:
            # Get date range if provided
            start_date = data_source.get('start_date')
            end_date = data_source.get('end_date')
            
            # Use data manager to load data
            self.data_manager.load_data_source(data_source, start_date, end_date)
            logger.info("[UI-LOAD-AVALARA] Data loading delegated to data manager")
                
        except Exception as e:
            logger.error(f"[UI-LOAD-AVALARA] ERROR loading Avalara data: {e}")
            logger.error("[UI-LOAD-AVALARA] Stack trace:", exc_info=True)
            self.status_manager.hide_progress()
            self.status_manager.show_error(f"Error loading {data_source['name']}: {str(e)}")
            QMessageBox.critical(self, "Loading Error", f"Error loading {data_source['name']}:\n{str(e)}")

    def load_quickbase_data_source(self, data_source):
        """Load QuickBase data source"""
        logger.info(f"[UI-LOAD-QB] Loading QuickBase data source: {data_source['name']}")

        # Check if we have an API connection
        if not self.quickbase_api:
            logger.error("[UI-LOAD-QB] No QuickBase API connection")
            QMessageBox.warning(self, "No Connection",
                              "Please connect to QuickBase first.\n\n" +
                              "Make sure you have set your QuickBase credentials in the .env file:\n" +
                              "QUICKBASE_USER_TOKEN=your_user_token\n" +
                              "QUICKBASE_APP_ID=your_app_id")
            return

        # Show progress using status manager
        self.status_manager.show_progress(f"Loading QuickBase data: {data_source['name']}...")

        try:
            # Get date range if provided
            start_date = data_source.get('start_date')
            end_date = data_source.get('end_date')

            # Use data manager to load data
            self.data_manager.load_data_source(data_source, start_date, end_date)
            logger.info("[UI-LOAD-QB] Data loading delegated to data manager")

        except Exception as e:
            logger.error(f"[UI-LOAD-QB] ERROR loading QuickBase data: {e}")
            logger.error("[UI-LOAD-QB] Stack trace:", exc_info=True)
            self.status_manager.hide_progress()
            self.status_manager.show_error(f"Error loading {data_source['name']}: {str(e)}")
            QMessageBox.critical(self, "Loading Error", f"Error loading {data_source['name']}:\n{str(e)}")

    def setup_menus(self):
        """Setup application menus"""
        menubar = self.menuBar()
        
        # File menu
        if menubar:
            file_menu = menubar.addMenu("File")
        else:
            return
        
        new_action = QAction(qta.icon('fa5s.file'), "New", self)
        new_action.setShortcut("Ctrl+N")
        if file_menu:
            file_menu.addAction(new_action)
            file_menu.addSeparator()
        
        export_action = QAction(qta.icon('fa5s.file-export'), "Export Current Data", self)
        export_action.setShortcut("Ctrl+E")
        if file_menu:
            file_menu.addAction(export_action)
            file_menu.addSeparator()
        
        exit_action = QAction(qta.icon('fa5s.sign-out-alt'), "Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        if file_menu:
            file_menu.addAction(exit_action)
        
        # Edit menu
        if menubar:
            edit_menu = menubar.addMenu("Edit")
        else:
            edit_menu = None
        
        settings_action = QAction(qta.icon('fa5s.cog'), "Settings", self)
        settings_action.triggered.connect(self.show_settings)
        if edit_menu:
            edit_menu.addAction(settings_action)
        
        # Data menu
        if menubar:
            data_menu = menubar.addMenu("Data")
        else:
            data_menu = None
        
        refresh_action = QAction(qta.icon('fa5s.sync'), "Refresh Data Sources", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_data_sources)
        if data_menu:
            data_menu.addAction(refresh_action)
        
        # Help menu
        if menubar:
            help_menu = menubar.addMenu("Help")
        else:
            help_menu = None
        
        about_action = QAction(qta.icon('fa5s.info'), "About", self)
        about_action.triggered.connect(self.show_about)
        if help_menu:
            help_menu.addAction(about_action)
    
    def setup_toolbar(self):
        """Setup application toolbar"""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        # Connection status indicator
        toolbar.addWidget(QLabel("Status:"))
        self.toolbar_status = QLabel("Disconnected")
        self.toolbar_status.setStyleSheet("color: red; font-weight: bold; margin: 0 10px;")
        toolbar.addWidget(self.toolbar_status)
        
        toolbar.addSeparator()
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync'))
        refresh_btn.clicked.connect(self.refresh_data_sources)
        toolbar.addWidget(refresh_btn)
        
        # Token Status button
        token_status_btn = QPushButton("Token Status")
        token_status_btn.setIcon(qta.icon('fa5s.key'))
        token_status_btn.clicked.connect(self.show_token_status)
        toolbar.addWidget(token_status_btn)
        
        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setIcon(qta.icon('fa5s.cog'))
        settings_btn.clicked.connect(self.show_settings)
        toolbar.addWidget(settings_btn)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_bar.showMessage("Ready")
    
    def apply_theme(self):
        """Apply dark theme to application"""
        if self.config.appearance.theme == "dark":
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
    
    def restore_window_state(self):
        """Restore window size and position"""
        if self.config.appearance.window_maximized:
            self.showMaximized()
        else:
            self.resize(self.config.appearance.window_width, self.config.appearance.window_height)
    
    def async_auto_connect_all_apis(self):
        """Start async auto-connect to all configured API services with optimizations"""
        logger.info("[ASYNC-AUTO-CONNECT] Starting optimized auto-connection to all APIs")
        
        # Update status to show connection in progress
        self.update_unified_connection_status(False, False, False, False)
        self.source_data_tab.update_connection_status("Connecting...", "orange")
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Initialize existing API instances - JWT auth doesn't need session restoration
        self.restore_woocommerce_session()
        self.initialize_avalara_api()
        self.initialize_quickbase_api()
        
        # Log JWT authentication status for transparency
        if self.sf_api and hasattr(self.sf_api, 'is_authenticated'):
            if self.sf_api.is_authenticated():
                logger.info("[ASYNC-AUTO-CONNECT] Salesforce JWT authenticated - will reuse")
            else:
                logger.info("[ASYNC-AUTO-CONNECT] Salesforce not authenticated - may need JWT authentication")
        
        # Start async worker with optimizations
        self.auto_connect_worker = AsyncAutoConnectWorker(
            self.config, 
            self.sf_api, 
            self.woo_api
        )
        
        # Connect signals
        self.auto_connect_worker.connection_progress.connect(self.on_auto_connect_progress)
        self.auto_connect_worker.connection_completed.connect(self.on_auto_connect_completed)
        self.auto_connect_worker.error_occurred.connect(self.on_auto_connect_error)
        self.auto_connect_worker.finished.connect(self.on_auto_connect_finished)
        self.auto_connect_worker.data_sources_loaded.connect(self.on_async_reports_loaded)
        self.auto_connect_worker.quickbase_table_reports_loaded.connect(self.on_quickbase_table_reports_loaded)
        
        # Start the worker
        self.auto_connect_worker.start()
        logger.info("[ASYNC-AUTO-CONNECT] Async worker started")
    
    def on_auto_connect_progress(self, message: str):
        """Handle progress updates from async auto-connect"""
        logger.info(f"[ASYNC-AUTO-CONNECT] Progress: {message}")
        if hasattr(self, 'status_bar'):
            self.status_bar.showMessage(message)
        
        # Update progress bar based on message
        if "Connecting to Salesforce" in message:
            self.progress_bar.setValue(10)
        elif "Salesforce authentication required" in message:
            self.progress_bar.setValue(20)
        elif "Salesforce connected" in message:
            self.progress_bar.setValue(50)
        elif "Connecting to WooCommerce" in message:
            self.progress_bar.setValue(60)
        elif "WooCommerce connected" in message:
            self.progress_bar.setValue(100)
    
    def on_auto_connect_completed(self, results: dict):
        """Handle completion of async auto-connect"""
        sf_connected = results.get('sf_connected', False)
        woo_connected = results.get('woo_connected', False)
        avalara_connected = results.get('avalara_connected', False)

        # Update state tracking with auto-connect results
        self.sf_connected = sf_connected
        self.woo_connected = woo_connected
        # Only update avalara_connected if the new result is successful, or if we don't currently have a connection
        if avalara_connected or not self.avalara_connected:
            self.avalara_connected = avalara_connected

        logger.info(f"[ASYNC-AUTO-CONNECT] Completed: SF={sf_connected}, WC={woo_connected}, Avalara={self.avalara_connected}")
        
        # Update connection status using actual state tracking
        self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)
        
        # Populate the unified tree with async-loaded data
        self.populate_unified_tree_async()
        
        # Update status bar and hide progress bar
        if hasattr(self, 'status_bar'):
            connected_count = sum([sf_connected, woo_connected, self.avalara_connected])
            if connected_count == 3:
                self.status_bar.showMessage("All APIs connected successfully")
            elif connected_count > 0:
                self.status_bar.showMessage(f"{connected_count}/3 APIs connected")
            else:
                self.status_bar.showMessage("Connection failed")
        
        # Hide progress bar
        self.progress_bar.setVisible(False)
    
    def on_async_reports_loaded(self, api_type: str, reports: list):
        """Handle async-loaded reports/data sources"""
        if api_type == "salesforce":
            self.async_sf_reports = reports
            logger.info(f"[ASYNC-AUTO-CONNECT] Cached {len(reports)} Salesforce reports")
        elif api_type == "woocommerce":
            self.async_woo_data_sources = reports
            logger.info(f"[ASYNC-AUTO-CONNECT] Cached {len(reports)} WooCommerce data sources")
        elif api_type == "avalara":
            self.async_avalara_data_sources = reports
            logger.info(f"[ASYNC-AUTO-CONNECT] Cached {len(reports)} Avalara data sources")
        elif api_type == "quickbase":
            self.async_quickbase_data_sources = reports
            logger.info(f"[ASYNC-AUTO-CONNECT] Cached {len(reports)} QuickBase data sources")

    def on_quickbase_table_reports_loaded(self, table_id: str, reports: list):
        """Handle QuickBase table reports loaded by async worker"""
        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(reports)} reports for QuickBase table {table_id}")
        # Update tree manager with reports for this table
        self.tree_manager.update_quickbase_table_reports(table_id, reports)

        # Note: Tree repopulation is handled by populate_unified_tree_async() to avoid multiple updates
        # Individual table report loading does not trigger immediate tree refresh

    def on_auto_connect_error(self, api_type: str, error_message: str):
        """Handle async auto-connect errors"""
        logger.error(f"[ASYNC-AUTO-CONNECT] {api_type} error: {error_message}")
        # Don't show error dialogs for auto-connect failures - just log them
        # Users can manually connect if needed
    
    def on_auto_connect_finished(self):
        """Handle async auto-connect worker completion"""
        logger.info("[ASYNC-AUTO-CONNECT] Worker finished")
        self.auto_connect_worker = None
    
    # Removed show_salesforce_connect_dialog - auto-connect handles all authentication automatically
    
    def on_individual_connection_status_changed(self, api_type: str, connected: bool):
        """
        Adapter method to handle individual API connection status changes from ConnectionManager
        Converts (str, bool) signal to Dict[str, bool] format expected by StatusManager

        Note: Tree population is handled separately via populate_unified_tree_async() to avoid multiple updates
        """
        try:
            # Get current connection states from connection manager
            current_status = {
                'salesforce': getattr(self.connection_manager, 'sf_connected', False),
                'woocommerce': getattr(self.connection_manager, 'woo_connected', False),
                'avalara': getattr(self.connection_manager, 'avalara_connected', False),
                'quickbase': getattr(self.connection_manager, 'quickbase_connected', False),
            }

            # Update the changed API status
            if api_type in current_status:
                current_status[api_type] = connected

            # Update status manager only - tree will be updated once when data is ready
            self.status_manager.update_connection_status(current_status)

            logger.info(f"[MAIN-WINDOW] Connection status updated: {api_type}={connected}, Full status: {current_status}")

        except Exception as e:
            logger.error(f"[MAIN-WINDOW] Error handling connection status change: {e}")

    def update_unified_connection_status(self, sf_connected: bool, woo_connected: bool, avalara_connected: bool = False, quickbase_connected: bool = False):
        """Update the connection status display for all APIs with token info"""
        # Use status manager to handle status updates
        connection_status = {
            'salesforce': sf_connected,
            'woocommerce': woo_connected,
            'avalara': avalara_connected,
            'quickbase': quickbase_connected,
        }
        
        # Update status using manager
        self.status_manager.update_connection_status(connection_status)
        
        # Enable custom report builder when Salesforce is connected
        if hasattr(self, 'source_data_tab'):
            self.source_data_tab.enable_custom_report_builder(sf_connected)
        
        # Enhanced status with token information for source data tab
        sf_status = "✓" if sf_connected else "✗"
        woo_status = "✓" if woo_connected else "✗"
        avalara_status = "✓" if avalara_connected else "✗"
        quickbase_status = "✓" if quickbase_connected else "✗"
        
        # Add authentication status for Salesforce
        sf_auth_info = ""
        if sf_connected and self.sf_api and hasattr(self.sf_api, 'is_authenticated'):
            if self.sf_api.is_authenticated():
                sf_auth_info = " (authenticated)"
            else:
                sf_auth_info = " (not authenticated)"
                sf_status = "⚠"  # Warning symbol for not authenticated

        status_text = f"SF: {sf_status}{sf_auth_info}  WC: {woo_status}  AV: {avalara_status}  QB: {quickbase_status}"

        # Count connected APIs for color determination
        connected_count = sum([sf_connected, woo_connected, avalara_connected, quickbase_connected])

        if connected_count == 4:
            # Check if Salesforce is actually authenticated
            if self.sf_api and hasattr(self.sf_api, 'is_authenticated') and not self.sf_api.is_authenticated():
                color = "orange"
            else:
                color = "green"
        elif connected_count > 0:
            color = "orange"
        else:
            color = "red"
        
        # Update source data tab connection status with detailed info
        self.source_data_tab.update_connection_status(status_text, color)
    
    # Async helper methods for API operations
    # Helper async methods removed - replaced with proper worker usage to fix event loop issues
    
    # _run_async_in_thread_simple removed - replaced with proper ConnectionManager usage to fix event loop issues
    
    def _set_sf_disconnected_state(self):
        """Set UI to Salesforce disconnected state"""
        logger.info("[SESSION-RESTORE] Setting UI to disconnected state")
        self.sf_connected = False
        self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)
    
    def _set_woo_disconnected_state(self):
        """Set UI to WooCommerce disconnected state"""
        logger.info("[WOO-RESTORE] Setting UI to disconnected state")
        self.woo_connected = False
        self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)
        self.status_bar.showMessage("WooCommerce not configured")
    
    def populate_unified_tree_async(self):
        """Populate the unified tree with async-loaded data (optimized)"""
        logger.info("[UNIFIED-TREE-ASYNC] Populating unified tree with async-loaded data")

        # Update tree manager with current data
        self.tree_manager.update_salesforce_data(self.async_sf_reports)
        self.tree_manager.update_woocommerce_data(self.async_woo_data_sources)
        self.tree_manager.update_avalara_data(self.async_avalara_data_sources)
        self.tree_manager.update_quickbase_data(self.async_quickbase_data_sources)

        # Get current connection status
        connection_status = {
            'salesforce': self.sf_connected,
            'woocommerce': self.woo_connected,
            'avalara': self.avalara_connected,
            'quickbase': self.quickbase_connected,
        }

        # Use tree manager to populate tree
        self.tree_manager.populate_unified_tree(connection_status)

        logger.info("[UNIFIED-TREE-ASYNC] Unified tree populated successfully with async data")
    
    
    
    
    
    
    
    def restore_salesforce_session(self):
        """Restore Salesforce session using JWT authentication"""
        logger.info("[SESSION-RESTORE] " + "=" * 50)
        logger.info("[SESSION-RESTORE] Attempting to restore Salesforce JWT session")
        logger.info("[SESSION-RESTORE] " + "=" * 50)

        try:
            # Use ConnectionManager's API instance instead of creating new ones
            if not self.sf_api:
                self.sf_api = self.connection_manager.get_api_instance('salesforce')
                logger.info("[SESSION-RESTORE] Using ConnectionManager's Salesforce JWT API instance")

            # Check if we have a JWT API instance and it's authenticated
            if self.sf_api and hasattr(self.sf_api, 'is_authenticated'):
                if self.sf_api.is_authenticated():
                    logger.info("[SESSION-RESTORE] JWT API already authenticated - keeping existing instance")
                    self.sf_connected = True
                    self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)
                    return
                else:
                    logger.info("[SESSION-RESTORE] JWT API not authenticated - will test connection")
            
            # Check if we have stored credentials and set up API instance
            if self.sf_api:
                logger.info("[SESSION-RESTORE] Checking for stored credentials...")
                has_creds = self.sf_api.has_credentials()
                logger.info(f"[SESSION-RESTORE] Has credentials: {has_creds}")

                if has_creds:
                    logger.info("[SESSION-RESTORE] Found JWT credentials - ready for connection testing")
                    logger.info("[SESSION-RESTORE] Connection testing will be handled by main auto-connect worker")
                    return True  # Credentials available, let main worker handle connection
                else:
                    logger.info("[SESSION-RESTORE] No JWT credentials found")
            else:
                logger.info("[SESSION-RESTORE] No Salesforce API instance available")
                
        except Exception as e:
            logger.error(f"[SESSION-RESTORE] ERROR Session restoration failed: {e}")
            logger.error(f"[SESSION-RESTORE] Exception type: {type(e).__name__}")
            logger.error("[SESSION-RESTORE] Stack trace:", exc_info=True)
        
        # If we get here, session restoration failed - show disconnected state
        logger.info("[SESSION-RESTORE] Setting UI to disconnected state")
        self.connection_status.setText("Not Connected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        self.toolbar_status.setText("Disconnected")
        self.toolbar_status.setStyleSheet("color: red; font-weight: bold;")
        
        logger.info("[SESSION-RESTORE] " + "=" * 50)
        logger.info("[SESSION-RESTORE] Session restoration completed")
        logger.info("[SESSION-RESTORE] " + "=" * 50)
        return False
    
    def restore_woocommerce_session(self):
        """Restore or create WooCommerce session with auto-connection"""
        logger.info("[WOO-RESTORE] " + "=" * 50)
        logger.info("[WOO-RESTORE] Auto-connecting to WooCommerce")
        logger.info("[WOO-RESTORE] " + "=" * 50)
        
        try:
            # Use ConnectionManager's API instance instead of creating new ones
            if not self.woo_api:
                self.woo_api = self.connection_manager.get_api_instance('woocommerce')
                logger.info("[WOO-RESTORE] Using ConnectionManager's WooCommerce API instance")
            
            # Set up WooCommerce API instance for main worker
            if self.woo_api:
                logger.info("[WOO-RESTORE] WooCommerce API instance ready for connection testing")
                logger.info("[WOO-RESTORE] Connection testing will be handled by main auto-connect worker")
                return True  # API instance available, let main worker handle connection
            
        except Exception as e:
            logger.error(f"[WOO-RESTORE] ERROR WooCommerce session restoration failed: {e}")
            logger.error(f"[WOO-RESTORE] Exception type: {type(e).__name__}")
            logger.error("[WOO-RESTORE] Stack trace:", exc_info=True)
        
        # If we get here, restoration failed - show disconnected state
        logger.info("[WOO-RESTORE] Setting UI to disconnected state")
        self.connection_status.setText("Not Connected")
        self.connection_status.setStyleSheet("color: red; font-weight: bold;")
        self.toolbar_status.setText("Disconnected")
        self.toolbar_status.setStyleSheet("color: red; font-weight: bold;")
        self.status_bar.showMessage("WooCommerce not configured")
        
        logger.info("[WOO-RESTORE] " + "=" * 50)
        logger.info("[WOO-RESTORE] WooCommerce session restoration completed")
        logger.info("[WOO-RESTORE] " + "=" * 50)
        return False
    
    def initialize_avalara_api(self):
        """Initialize or restore Avalara API session"""
        logger.info("[AVALARA-INIT] " + "=" * 50)
        logger.info("[AVALARA-INIT] Initializing Avalara API")
        logger.info("[AVALARA-INIT] " + "=" * 50)
        
        try:
            # Use ConnectionManager's API instance instead of creating new ones
            if not self.avalara_api:
                self.avalara_api = self.connection_manager.get_api_instance('avalara')
                logger.info("[AVALARA-INIT] Using ConnectionManager's Avalara API instance")
            
            # Test the connection
            if self.avalara_api:
                logger.info("[AVALARA-INIT] Testing Avalara connection...")
                
                def handle_avalara_test_result(result):
                    logger.info(f"[AVALARA-CALLBACK] Callback called with result: {result}")
                    if result.get('success', False):
                        logger.info("[AVALARA-INIT] SUCCESS Avalara connection successful")
                        
                        # Update connection state tracking
                        self.avalara_connected = True
                        
                        # Update UI to show connected state
                        account_info = result.get('account_info', 'Avalara Account')
                        environment = result.get('environment', 'sandbox')
                        
                        logger.info(f"[AVALARA-INIT] Connected to {account_info} ({environment})")
                        
                        # Update unified connection status instead of individual UI elements
                        self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)
                        
                        # Connection successful - data sources are already initialized
                        logger.info("[AVALARA-INIT] SUCCESS Avalara session initialized")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        logger.warning(f"[AVALARA-INIT] Connection test failed: {error_msg}")
                        
                        # Check if it's an authentication error
                        if 'Authentication failed' in error_msg or result.get('status') == 401:
                            logger.error("[AVALARA-INIT] Authentication failed - check credentials in .env file")
                            logger.error("[AVALARA-INIT] Please set AVALARA_ACCOUNT_ID and AVALARA_LICENSE_KEY")
                            logger.error("[AVALARA-INIT] Get credentials from https://sandbox-admin.avalara.com")
                        
                        self._set_avalara_disconnected_state()
                
                # Test connection using connection manager (simpler and thread-safe)
                from PyQt6.QtCore import QThread, QTimer

                class AvalaraTestThread(QThread):
                    def __init__(self, connection_manager):
                        super().__init__()
                        self.connection_manager = connection_manager
                        self.result = None

                    def run(self):
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            self.result = loop.run_until_complete(
                                self.connection_manager.test_connection('avalara')
                            )
                        except Exception as e:
                            self.result = {'success': False, 'error': str(e)}
                        finally:
                            loop.close()

                # Use QThread instead of raw threading.Thread for proper PyQt integration
                self.avalara_test_thread = AvalaraTestThread(self.connection_manager)
                self.avalara_test_thread.finished.connect(
                    lambda: QTimer.singleShot(0, lambda: handle_avalara_test_result(self.avalara_test_thread.result))
                )
                self.avalara_test_thread.start()
                return True  # Return immediately since async
            
        except Exception as e:
            logger.error(f"[AVALARA-INIT] ERROR Avalara initialization failed: {e}")
            logger.error(f"[AVALARA-INIT] Exception type: {type(e).__name__}")
            logger.error("[AVALARA-INIT] Stack trace:", exc_info=True)
        
        # If we get here, initialization failed - show disconnected state
        logger.info("[AVALARA-INIT] Setting UI to disconnected state")
        self._set_avalara_disconnected_state()
        
        logger.info("[AVALARA-INIT] " + "=" * 50)
        logger.info("[AVALARA-INIT] Avalara initialization completed")
        logger.info("[AVALARA-INIT] " + "=" * 50)
        return False
    
    def _set_avalara_disconnected_state(self):
        """Set UI to show Avalara disconnected state"""
        logger.info("[AVALARA-INIT] Setting Avalara disconnected state")
        
        # Update connection state tracking
        self.avalara_connected = False
        
        # Clear the data sources when disconnected
        self.async_avalara_data_sources = []
        
        # Update unified connection status instead of individual UI elements
        self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected)

    def initialize_quickbase_api(self):
        """Initialize or restore QuickBase API session"""
        logger.info("[QUICKBASE-INIT] " + "=" * 50)
        logger.info("[QUICKBASE-INIT] Initializing QuickBase API")
        logger.info("[QUICKBASE-INIT] " + "=" * 50)

        try:
            # Use ConnectionManager's API instance instead of creating new ones
            if not self.quickbase_api:
                self.quickbase_api = self.connection_manager.get_api_instance('quickbase')
                logger.info("[QUICKBASE-INIT] Using ConnectionManager's QuickBase API instance")

            # Test the connection
            if self.quickbase_api:
                logger.info("[QUICKBASE-INIT] Testing QuickBase connection...")

                def handle_quickbase_test_result(result):
                    logger.info(f"[QUICKBASE-CALLBACK] Callback called with result: {result}")
                    if result.get('success', False):
                        logger.info("[QUICKBASE-INIT] SUCCESS QuickBase connection successful")

                        # Update connection state tracking
                        self.quickbase_connected = True

                        # Update UI to show connected state
                        details = result.get('details', {})
                        realm = details.get('realm', 'Unknown')
                        apps_found = details.get('apps_found', 0)

                        logger.info(f"[QUICKBASE-INIT] Connected to {realm} ({apps_found} apps found)")

                        # Update unified connection status
                        self.update_unified_connection_status(
                            self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected
                        )

                        # Connection successful
                        logger.info("[QUICKBASE-INIT] SUCCESS QuickBase session initialized")
                    else:
                        error_msg = result.get('message', result.get('error', 'Unknown error'))
                        logger.warning(f"[QUICKBASE-INIT] Connection test failed: {error_msg}")

                        # Check if it's an authentication error
                        if 'Authentication failed' in error_msg or result.get('status') == 401:
                            logger.error("[QUICKBASE-INIT] Authentication failed - check credentials in .env file")
                            logger.error("[QUICKBASE-INIT] Please set QUICKBASE_REALM_HOSTNAME and QUICKBASE_USER_TOKEN")

                        self._set_quickbase_disconnected_state()

                # Create a test thread to avoid blocking the UI
                class QuickBaseTestThread(QThread):
                    def __init__(self, connection_manager):
                        super().__init__()
                        self.connection_manager = connection_manager
                        self.result = None

                    def run(self):
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            self.result = loop.run_until_complete(
                                self.connection_manager.test_connection('quickbase')
                            )
                        except Exception as e:
                            self.result = {'success': False, 'error': str(e)}
                        finally:
                            loop.close()

                # Use QThread instead of raw threading.Thread for proper PyQt integration
                self.quickbase_test_thread = QuickBaseTestThread(self.connection_manager)
                self.quickbase_test_thread.finished.connect(
                    lambda: QTimer.singleShot(0, lambda: handle_quickbase_test_result(self.quickbase_test_thread.result))
                )
                self.quickbase_test_thread.start()
                return True  # Return immediately since async

        except Exception as e:
            logger.error(f"[QUICKBASE-INIT] ERROR QuickBase initialization failed: {e}")
            logger.error(f"[QUICKBASE-INIT] Exception type: {type(e).__name__}")
            logger.error("[QUICKBASE-INIT] Stack trace:", exc_info=True)

        # If we get here, initialization failed - show disconnected state
        logger.info("[QUICKBASE-INIT] Setting UI to disconnected state")
        self._set_quickbase_disconnected_state()

        logger.info("[QUICKBASE-INIT] " + "=" * 50)
        logger.info("[QUICKBASE-INIT] QuickBase initialization completed")
        logger.info("[QUICKBASE-INIT] " + "=" * 50)
        return False

    def _set_quickbase_disconnected_state(self):
        """Set UI to show QuickBase disconnected state"""
        logger.info("[QUICKBASE-INIT] Setting QuickBase disconnected state")

        # Update connection state tracking
        self.quickbase_connected = False

        # Clear the data sources when disconnected
        self.async_quickbase_data_sources = []

        # Update unified connection status
        self.update_unified_connection_status(
            self.sf_connected, self.woo_connected, self.avalara_connected, self.quickbase_connected
        )

    def show_woocommerce_config_dialog(self):
        """Show WooCommerce configuration dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("WooCommerce Configuration")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        
        # Info label
        info_label = QLabel("Enter your WooCommerce store details:")
        layout.addWidget(info_label)
        
        # Form
        form_layout = QFormLayout()
        
        store_url_input = QLineEdit()
        store_url_input.setPlaceholderText("https://yourstore.com")
        form_layout.addRow("Store URL:", store_url_input)
        
        consumer_secret_input = QLineEdit()
        consumer_secret_input.setPlaceholderText("cs_xxxxxxxxxx")
        consumer_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Consumer Secret:", consumer_secret_input)
        
        # Info about consumer key
        key_info = QLabel(f"Consumer Key: {self.woo_api.CONSUMER_KEY if hasattr(self, 'woo_api') and self.woo_api else 'ck_EXAMPLE1234567890abcdefghijklmnop'} (hardcoded)")
        key_info.setStyleSheet("color: gray; font-size: 10px;")
        form_layout.addRow("", key_info)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            store_url = store_url_input.text().strip()
            consumer_secret = consumer_secret_input.text().strip()
            
            if store_url and consumer_secret:
                self.create_woocommerce_connection(store_url, consumer_secret)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Invalid Input", "Please enter both store URL and consumer secret.")
    
    def create_woocommerce_connection(self, store_url: str, consumer_secret: str):
        """Create WooCommerce API connection"""
        try:
            logger.info("[WOO-CONNECT] Creating WooCommerce API connection...")
            logger.info(f"[WOO-CONNECT] Store URL: {store_url}")
            
            # Update the ConnectionManager's WooCommerce API instance
            if hasattr(self.connection_manager, 'woo_api'):
                self.connection_manager.woo_api = AsyncWooCommerceAPI(store_url)
                self.woo_api = self.connection_manager.woo_api
            else:
                # Fallback to direct creation
                self.woo_api = AsyncWooCommerceAPI(store_url)
            
            # Store the API instance for persistence
            self.api_instances["woocommerce"] = self.woo_api
            
            # Test the connection using async wrapper
            def handle_connect_test_result(result):
                if result.get('success', False):
                    logger.info("[WOO-CONNECT] SUCCESS WooCommerce connection successful")
                    
                    # Update UI
                    store_name = result.get('store_name', 'WooCommerce Store')
                    wc_version = result.get('wc_version', 'Unknown')
                    
                    self.connection_status.setText("Connected")
                    self.connection_status.setStyleSheet("color: green; font-weight: bold;")
                    self.toolbar_status.setText("Connected")
                    self.toolbar_status.setStyleSheet("color: green; font-weight: bold;")
                    self.status_bar.showMessage(f"Connected to {store_name} (WC {wc_version})")
                    
                    # Load data sources
                    self.load_woocommerce_data_sources()
                    
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Connection Successful", f"Successfully connected to {store_name}")
                else:
                    logger.error(f"[WOO-CONNECT] Connection failed: {result.get('error', 'Unknown error')}")
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.warning(self, "Connection Failed", f"Failed to connect to WooCommerce:\\n{result.get('error', 'Unknown error')}")
            
            # Use AsyncAutoConnectWorker for proper async execution
            self.auto_connect_worker = AsyncAutoConnectWorker(
                self.config,
                sf_api_instance=None,
                woo_api_instance=self.woo_api
            )
            
            def handle_worker_result(results):
                if results.get('woo_connected'):
                    handle_connect_test_result({'success': True})
                else:
                    handle_connect_test_result({'success': False, 'error': 'Connection failed'})
            
            self.auto_connect_worker.connection_completed.connect(handle_worker_result)
            self.auto_connect_worker.start()
                
        except Exception as e:
            logger.error(f"[WOO-CONNECT] ERROR creating WooCommerce connection: {e}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Connection Error", f"Error creating WooCommerce connection:\n{str(e)}")
    
    def load_woocommerce_data_sources(self):
        """Load WooCommerce data sources into the tree"""
        logger.info("[WOO-LOAD] Loading WooCommerce data sources...")
        
        try:
            if not self.woo_api:
                logger.error("[WOO-LOAD] No WooCommerce API instance available")
                return
            
            # Clear existing tree
            self.data_tree.clear()
            
            # Get data sources using async wrapper
            def handle_data_sources_result(data_sources):
                logger.info(f"[WOO-LOAD] Found {len(data_sources)} data sources")
                
                
                # Keep tree collapsed by default - users can expand what they need
                self.data_tree.resizeColumnToContents(0)
                
                # Enable load button
                self.load_btn.setEnabled(True)
                
                logger.info("[WOO-LOAD] SUCCESS WooCommerce data sources loaded")
            
            # Use AsyncAutoConnectWorker which includes data sources loading
            self.auto_connect_worker = AsyncAutoConnectWorker(
                self.config,
                sf_api_instance=None,
                woo_api_instance=self.woo_api
            )
            
            def handle_data_sources_loaded(api_type, data_sources):
                if api_type == 'woocommerce':
                    handle_data_sources_result(data_sources)
            
            self.auto_connect_worker.data_sources_loaded.connect(handle_data_sources_loaded)
            self.auto_connect_worker.start()
            
        except Exception as e:
            logger.error(f"[WOO-LOAD] ERROR loading WooCommerce data sources: {e}")
            logger.error("[WOO-LOAD] Stack trace:", exc_info=True)
    
    
    # Removed all manual authentication methods - auto-connect handles all authentication automatically
    
    
    # Removed manual connection handling methods - auto-connect handles all authentication automatically
    
    def load_salesforce_reports(self):
        """Load Salesforce reports in background"""
        # Start loading in worker thread
        self.reports_worker = SalesforceConnectionWorker("load_reports", self.sf_api)
        self.reports_worker.reports_loaded.connect(self.on_reports_loaded)
        self.reports_worker.error_occurred.connect(self.on_reports_error)
        self.reports_worker.start()
    
    def on_reports_loaded(self, reports: list):
        """Handle loaded reports"""
        logger.info("[UI-REPORTS-LOADED] " + "=" * 40)
        logger.info("[UI-REPORTS-LOADED] Processing loaded reports")
        logger.info(f"[UI-REPORTS-LOADED] Number of reports: {len(reports)}")
        logger.info("[UI-REPORTS-LOADED] " + "=" * 40)
        
        logger.info("[UI-REPORTS-LOADED] Updating UI...")
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Loaded {len(reports)} reports")
        logger.info("[UI-REPORTS-LOADED] SUCCESS UI updated")
        
        # Clear existing tree
        logger.info("[UI-REPORTS-LOADED] Clearing data tree...")
        self.data_tree.clear()
        logger.info("[UI-REPORTS-LOADED] SUCCESS Data tree cleared")
        
        # Group reports by folder
        logger.info("[UI-REPORTS-LOADED] Grouping reports by folder...")
        folders = {}
        for report in reports:
            folder_name = report.get('folder', 'Unfiled Public Reports')
            if folder_name not in folders:
                folders[folder_name] = []
            folders[folder_name].append(report)
        logger.info(f"[UI-REPORTS-LOADED] SUCCESS Grouped into {len(folders)} folders")
        
        # Add folders and reports to tree
        logger.info("[UI-REPORTS-LOADED] Adding items to tree widget...")
        for folder_name, folder_reports in folders.items():
            folder_item = QTreeWidgetItem(self.data_tree, [folder_name, "Folder", ""])
            folder_item.setIcon(0, qta.icon('fa5s.folder'))
            
            for report in folder_reports:
                report_item = QTreeWidgetItem(folder_item, [
                    report['name'],
                    report['format'],
                    report.get('modified_date', '')[:10] if report.get('modified_date') else ''
                ])
                report_item.setIcon(0, qta.icon('fa5s.file-alt'))
                report_item.setData(0, Qt.ItemDataRole.UserRole, report)
        
        logger.info("[UI-REPORTS-LOADED] SUCCESS All items added to tree")
        
        # Keep tree collapsed by default - users can expand what they need
        logger.info("[UI-REPORTS-LOADED] Resizing tree columns...")
        self.data_tree.resizeColumnToContents(0)
        
        # Ensure auto-resize is connected for dynamic resizing
        if hasattr(self, 'source_data_tab') and hasattr(self.source_data_tab, 'auto_resize_name_column'):
            # Auto-resize functionality is already connected via SourceDataTab
            pass
        
        logger.info("[UI-REPORTS-LOADED] SUCCESS Tree resized")
        
        logger.info("[UI-REPORTS-LOADED] " + "=" * 40)
        logger.info("[UI-REPORTS-LOADED] SUCCESS Reports loading completed successfully")
        logger.info("[UI-REPORTS-LOADED] " + "=" * 40)
    
    def on_reports_error(self, error_msg: str):
        """Handle reports loading error"""
        logger.error("[UI-REPORTS-ERROR] " + "=" * 40)
        logger.error("[UI-REPORTS-ERROR] Reports loading failed")
        logger.error(f"[UI-REPORTS-ERROR] Error: {error_msg}")
        logger.error("[UI-REPORTS-ERROR] " + "=" * 40)
        
        logger.info("[UI-REPORTS-ERROR] Updating UI for error state...")
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(f"Error loading reports: {error_msg}")
        logger.info("[UI-REPORTS-ERROR] SUCCESS UI updated")
        
        logger.info("[UI-REPORTS-ERROR] Showing error message box...")
        QMessageBox.warning(self, "Reports Loading Error", f"Error loading reports:\n{error_msg}")
        logger.info("[UI-REPORTS-ERROR] SUCCESS Error message shown")
    
    def on_reports_worker_finished(self):
        """Handle reports worker thread completion"""
        logger.info("[UI-REPORTS-WORKER] Reports worker thread finished")
        if hasattr(self, 'reports_worker') and self.reports_worker:
            logger.info("[UI-REPORTS-WORKER] Cleaning up reports worker...")
            self.reports_worker.deleteLater()
            self.reports_worker = None
            logger.info("[UI-REPORTS-WORKER] SUCCESS Reports worker cleaned up")
    
    def on_data_worker_finished(self):
        """Handle data worker thread completion"""
        logger.info("[UI-DATA-WORKER] Data worker thread finished")
        if hasattr(self, 'data_worker') and self.data_worker:
            logger.info("[UI-DATA-WORKER] Cleaning up data worker...")
            self.data_worker.deleteLater()
            self.data_worker = None
            logger.info("[UI-DATA-WORKER] SUCCESS Data worker cleaned up")
    
    # Removed connection worker handling - auto-connect handles all authentication automatically
    
    def filter_tree(self, text: str):
        """Filter tree items based on search text"""
        search_text = text.lower()
        
        # If search is empty, collapse all and show everything
        if not search_text:
            self.data_tree.collapseAll()
            # Show all items
            for i in range(self.data_tree.topLevelItemCount()):
                api_parent = self.data_tree.topLevelItem(i)
                api_parent.setHidden(False)
                for j in range(api_parent.childCount()):
                    child_item = api_parent.child(j)
                    if child_item:
                        child_item.setHidden(False)
                    # If it's a folder, show all its children
                    if child_item:
                        for k in range(child_item.childCount()):
                            sub_child = child_item.child(k)
                            if sub_child:
                                sub_child.setHidden(False)
            return
        
        # Iterate through API parent nodes (Salesforce, WooCommerce)
        for i in range(self.data_tree.topLevelItemCount()):
            api_parent = self.data_tree.topLevelItem(i)
            api_visible = False
            
            # For each API, check its children (folders or data sources)
            for j in range(api_parent.childCount()):
                child_item = api_parent.child(j)
                child_visible = False
                
                # Check if this child is a folder (for Salesforce)
                if child_item and child_item.childCount() > 0:
                    # It's a folder with reports
                    if child_item:
                        for k in range(child_item.childCount()):
                            report_item = child_item.child(k)
                        if report_item is None:
                            continue
                        report_name = report_item.text(0).lower()
                        
                        if search_text in report_name:
                            if report_item:
                                report_item.setHidden(False)
                            child_visible = True
                        else:
                            if report_item:
                                report_item.setHidden(True)
                    
                    if child_item:
                        child_item.setHidden(not child_visible)
                    if child_visible:
                        api_visible = True
                        # Expand the folder to show matching reports
                        if child_item:
                            child_item.setExpanded(True)
                else:
                    # It's a direct data source (for WooCommerce)
                    if child_item:
                        item_name = child_item.text(0).lower()
                    else:
                        continue
                    if search_text in item_name:
                        if child_item:
                            child_item.setHidden(False)
                        api_visible = True
                    else:
                        if child_item:
                            child_item.setHidden(True)
            
            # Show/hide the API parent based on whether it has visible children
            if api_parent:
                api_parent.setHidden(not api_visible)
            # Expand API parent if it has matches
            if api_visible:
                if api_parent:
                    api_parent.setExpanded(True)
    
    def close_tab(self, index: int):
        """Close tab at index"""
        if index > 0:  # Don't close welcome tab
            self.tab_widget.removeTab(index)
    
    def refresh_data_sources(self):
        """Smart refresh - check existing connections before forcing new ones"""
        logger.info("[REFRESH] Starting smart refresh of data sources")
        
        # Check current connection status first
        sf_needs_refresh = True
        woo_needs_refresh = True
        
        # Check Salesforce connection
        if self.sf_api and hasattr(self.sf_api, 'is_authenticated'):
            if self.sf_api.is_authenticated():
                logger.info("[REFRESH] Salesforce JWT still authenticated - no re-auth needed")
                sf_needs_refresh = False
            else:
                logger.info("[REFRESH] Salesforce token expired - will need re-auth")
        
        # Check WooCommerce connection
        if self.woo_api:
            try:
                # Quick test to see if WooCommerce is still working
                test_result = self.woo_api.get_products(per_page=1)
                if test_result is not None:
                    logger.info("[REFRESH] WooCommerce connection still valid - no reconnection needed")
                    woo_needs_refresh = False
                else:
                    logger.info("[REFRESH] WooCommerce connection failed test - will reconnect")
            except Exception as e:
                logger.info(f"[REFRESH] WooCommerce connection test failed: {e} - will reconnect")
        
        # If both connections are valid, just refresh the tree without reconnecting
        if not sf_needs_refresh and not woo_needs_refresh:
            logger.info("[REFRESH] Both APIs still connected - refreshing tree only")
            self.populate_unified_tree_async()
        else:
            # Only reconnect APIs that actually need it
            if sf_needs_refresh or woo_needs_refresh:
                logger.info(f"[REFRESH] Reconnecting APIs - SF: {sf_needs_refresh}, WC: {woo_needs_refresh}")
                self.async_auto_connect_all_apis()
            else:
                # Just refresh the tree
                self.populate_unified_tree_async()
    
    def show_token_status(self):
        """Show detailed token and connection status"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from datetime import datetime
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Token & Connection Status")
        dialog.setModal(True)
        dialog.resize(500, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Salesforce status
        layout.addWidget(QLabel("<h3>Salesforce JWT Status</h3>"))

        if self.sf_api:
            if hasattr(self.sf_api, 'has_credentials') and self.sf_api.has_credentials():
                layout.addWidget(QLabel(f"✓ JWT credentials: Present"))
            else:
                layout.addWidget(QLabel(f"✗ JWT credentials: Missing"))

            if hasattr(self.sf_api, 'is_authenticated') and self.sf_api.is_authenticated():
                layout.addWidget(QLabel(f"✓ Authentication: Authenticated"))

                if hasattr(self.sf_api, 'access_token') and self.sf_api.access_token:
                    layout.addWidget(QLabel(f"✓ Access token: Present"))

                if hasattr(self.sf_api, 'instance_url') and self.sf_api.instance_url:
                    layout.addWidget(QLabel(f"✓ Instance URL: {self.sf_api.instance_url}"))
            else:
                layout.addWidget(QLabel("✗ Not authenticated"))
        else:
            layout.addWidget(QLabel("✗ No Salesforce JWT API instance"))
        
        # WooCommerce status
        layout.addWidget(QLabel("<h3>WooCommerce Status</h3>"))
        
        if self.woo_api:
            layout.addWidget(QLabel("✓ API instance: Present"))
            layout.addWidget(QLabel("✓ Authentication: Basic Auth (API Keys)"))
            
            # Test connection
            try:
                test_result = self.woo_api.get_products(per_page=1)
                if test_result is not None:
                    layout.addWidget(QLabel("✓ Connection test: Successful"))
                else:
                    layout.addWidget(QLabel("⚠ Connection test: Failed"))
            except Exception as e:
                layout.addWidget(QLabel(f"✗ Connection test: Error - {str(e)[:50]}..."))
        else:
            layout.addWidget(QLabel("✗ No WooCommerce API instance"))
        
        # Action buttons
        refresh_btn = QPushButton("Refresh Status")
        refresh_btn.clicked.connect(lambda: (dialog.accept(), self.show_token_status()))
        layout.addWidget(refresh_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec()
    
    def show_settings(self):
        """Show settings dialog"""
        settings_dialog = SettingsDialog(self.config_manager, self)
        settings_dialog.settings_changed.connect(self.on_settings_changed)
        settings_dialog.exec()
    
    def on_settings_changed(self):
        """Handle settings changes"""
        # Reload configuration
        self.config = self.config_manager.get_config()
        
        # Apply theme changes
        self.apply_theme()
        
        # Reset connection if Salesforce settings changed
        if self.sf_api:
            self.sf_api.disconnect()
            self.sf_api = None
            self.connection_status.setText("Settings Changed - Reconnect")
            self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
            self.toolbar_status.setText("Settings Changed")
            self.toolbar_status.setStyleSheet("color: orange; font-weight: bold;")
            self.data_tree.clear()
        
        self.status_bar.showMessage("Settings updated successfully")
    
    def on_tree_item_clicked(self):
        """Handle tree item selection"""
        current_item = self.data_tree.currentItem()
        if current_item:
            # Only enable load button for reports (items with UserRole data)
            report_data = current_item.data(0, Qt.ItemDataRole.UserRole)
            self.load_btn.setEnabled(report_data is not None)
        else:
            self.load_btn.setEnabled(False)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About", 
                         "Salesforce Report Pull\nMulti-API Data Integration Tool\n\nVersion 1.0")
    
    def closeEvent(self, a0):
        """Handle application close event"""
        # Clean up API resources
        if self.sf_api:
            # Schedule cleanup
            try:
                import asyncio
                asyncio.ensure_future(self.sf_api.close())
            except:
                pass  # Event loop might already be closed
        
        # Save window state
        if self.isMaximized():
            self.config.appearance.window_maximized = True
        else:
            self.config.appearance.window_maximized = False
            self.config.appearance.window_width = self.width()
            self.config.appearance.window_height = self.height()
        
        self.config_manager.save_config()
        
        # Call parent closeEvent
        super().closeEvent(a0)
        
        # Cleanup all workers
        logger.info("[MAIN-WINDOW] Cleaning up workers before exit...")

        # Clean up connection worker
        if hasattr(self, 'connection_worker') and self.connection_worker and self.connection_worker.isRunning():
            logger.info("[MAIN-WINDOW] Stopping connection worker...")
            self.connection_worker.quit()
            self.connection_worker.wait(3000)  # Wait up to 3 seconds

        # Clean up auto-connect worker
        if hasattr(self, 'auto_connect_worker') and self.auto_connect_worker and self.auto_connect_worker.isRunning():
            logger.info("[MAIN-WINDOW] Stopping auto-connect worker...")
            self.auto_connect_worker.quit()
            self.auto_connect_worker.wait(3000)  # Wait up to 3 seconds

        # Clean up reports worker
        if hasattr(self, 'reports_worker') and self.reports_worker and self.reports_worker.isRunning():
            logger.info("[MAIN-WINDOW] Stopping reports worker...")
            self.reports_worker.quit()
            self.reports_worker.wait(3000)  # Wait up to 3 seconds

        # Clean up data worker
        if hasattr(self, 'data_worker') and self.data_worker and self.data_worker.isRunning():
            logger.info("[MAIN-WINDOW] Stopping data worker...")
            self.data_worker.quit()
            self.data_worker.wait(3000)  # Wait up to 3 seconds

        # Clean up test threads
        if hasattr(self, 'avalara_test_thread') and self.avalara_test_thread and self.avalara_test_thread.isRunning():
            logger.info("[MAIN-WINDOW] Stopping Avalara test thread...")
            self.avalara_test_thread.quit()
            self.avalara_test_thread.wait(3000)  # Wait up to 3 seconds

        if hasattr(self, 'quickbase_test_thread') and self.quickbase_test_thread and self.quickbase_test_thread.isRunning():
            logger.info("[MAIN-WINDOW] Stopping QuickBase test thread...")
            self.quickbase_test_thread.quit()
            self.quickbase_test_thread.wait(3000)  # Wait up to 3 seconds

        # Clean up any other manager workers
        if hasattr(self, 'data_source_manager') and self.data_source_manager:
            # Stop any active workers in data source manager
            for worker_name, worker in getattr(self.data_source_manager, 'active_workers', {}).items():
                if worker and worker.isRunning():
                    logger.info(f"[MAIN-WINDOW] Stopping data source worker: {worker_name}")
                    worker.quit()
                    worker.wait(2000)  # Wait up to 2 seconds

        logger.info("[MAIN-WINDOW] All workers and test threads cleaned up")

        a0.accept()