"""
Connection Manager for handling API connections and status tracking
"""
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from src.services.async_salesforce_api import AsyncSalesforceAPI
from src.services.async_woocommerce_api import AsyncWooCommerceAPI
from src.services.async_avalara_api import AsyncAvalaraAPI
from src.services.auth_manager import SalesforceAuthManager
from src.models.config import ConfigManager

logger = logging.getLogger(__name__)

class ConnectionManager(QObject):
    """
    Manages API connections and connection status for all services
    """
    
    # Signals for connection status changes
    connection_status_changed = pyqtSignal(str, bool)  # api_type, connected
    connection_error = pyqtSignal(str, str)  # api_type, error_message
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        # API instances
        self.sf_api: Optional[AsyncSalesforceAPI] = None
        self.woo_api: Optional[AsyncWooCommerceAPI] = None
        self.avalara_api: Optional[AsyncAvalaraAPI] = None

        # Connection state tracking
        self.sf_connected = False
        self.woo_connected = False
        self.avalara_connected = False
        
        # Initialize APIs
        self._initialize_apis()
    
    def _initialize_apis(self):
        """Initialize API instances based on configuration"""
        try:
            # Initialize Salesforce API
            if self.config.salesforce:
                logger.info("[CONNECTION-MANAGER] Initializing Salesforce API")
                self.sf_api = AsyncSalesforceAPI(
                    instance_url=self.config.salesforce.login_url,
                    consumer_key=self.config.salesforce.consumer_key,
                    consumer_secret=self.config.salesforce.consumer_secret,
                    verbose_logging=False
                )
            
            # Initialize WooCommerce API
            logger.info("[CONNECTION-MANAGER] Initializing WooCommerce API")
            self.woo_api = AsyncWooCommerceAPI(verbose_logging=False)
            
            # Initialize Avalara API
            logger.info("[CONNECTION-MANAGER] Initializing Avalara API")
            self.avalara_api = AsyncAvalaraAPI(verbose_logging=False)


        except Exception as e:
            logger.error(f"[CONNECTION-MANAGER] Error initializing APIs: {e}")
    
    async def test_connection(self, api_type: str) -> Dict[str, Any]:
        """
        Test connection for a specific API type
        
        Args:
            api_type: 'salesforce', 'woocommerce', or 'avalara'
            
        Returns:
            Dictionary with connection test results
        """
        try:
            logger.info(f"[CONNECTION-MANAGER] Testing {api_type} connection")
            
            if api_type == 'salesforce':
                if not self.sf_api:
                    return {'success': False, 'error': 'No Salesforce API instance'}
                result = await self.sf_api.test_connection()
                
            elif api_type == 'woocommerce':
                if not self.woo_api:
                    return {'success': False, 'error': 'No WooCommerce API instance'}
                result = await self.woo_api.test_connection()
                
            elif api_type == 'avalara':
                if not self.avalara_api:
                    return {'success': False, 'error': 'No Avalara API instance'}
                # Create fresh API instance for connection test
                async with AsyncAvalaraAPI() as fresh_api:
                    result = await fresh_api.test_connection()


            else:
                return {'success': False, 'error': f'Unknown API type: {api_type}'}
            
            # Update connection state
            success = result.get('success', False)
            if api_type == 'salesforce':
                self.sf_connected = success
            elif api_type == 'woocommerce':
                self.woo_connected = success
            elif api_type == 'avalara':
                self.avalara_connected = success

            # Emit status change signal
            self.connection_status_changed.emit(api_type, success)
            
            if not success:
                self.connection_error.emit(api_type, result.get('error', 'Unknown error'))
            
            return result
            
        except Exception as e:
            logger.error(f"[CONNECTION-MANAGER] Error testing {api_type} connection: {e}")
            error_result = {'success': False, 'error': str(e)}
            self.connection_error.emit(api_type, str(e))
            return error_result
    
    async def test_all_connections(self) -> Dict[str, Dict[str, Any]]:
        """
        Test all API connections concurrently
        
        Returns:
            Dictionary with results for all API types
        """
        logger.info("[CONNECTION-MANAGER] Testing all API connections")
        
        # Test all connections concurrently
        results = await asyncio.gather(
            self.test_connection('salesforce'),
            self.test_connection('woocommerce'),
            self.test_connection('avalara'),
            return_exceptions=True
        )

        return {
            'salesforce': results[0] if not isinstance(results[0], Exception) else {'success': False, 'error': str(results[0])},
            'woocommerce': results[1] if not isinstance(results[1], Exception) else {'success': False, 'error': str(results[1])},
            'avalara': results[2] if not isinstance(results[2], Exception) else {'success': False, 'error': str(results[2])}
        }
    
    def get_connection_status(self, api_type: str) -> bool:
        """Get current connection status for an API type"""
        if api_type == 'salesforce':
            return self.sf_connected
        elif api_type == 'woocommerce':
            return self.woo_connected
        elif api_type == 'avalara':
            return self.avalara_connected
        else:
            return False
    
    def get_all_connection_status(self) -> Dict[str, bool]:
        """Get connection status for all APIs"""
        return {
            'salesforce': self.sf_connected,
            'woocommerce': self.woo_connected,
            'avalara': self.avalara_connected,
        }
    
    def get_api_instance(self, api_type: str):
        """Get API instance for a specific type"""
        if api_type == 'salesforce':
            return self.sf_api
        elif api_type == 'woocommerce':
            return self.woo_api
        elif api_type == 'avalara':
            return self.avalara_api
        else:
            return None
    
    async def restore_salesforce_session(self) -> bool:
        """
        Restore Salesforce session from stored credentials
        
        Returns:
            True if session restored successfully
        """
        try:
            logger.info("[CONNECTION-MANAGER] Restoring Salesforce session")
            
            if not self.sf_api:
                logger.error("[CONNECTION-MANAGER] No Salesforce API instance")
                return False
            
            # Check if we have an existing auth manager with valid credentials
            if hasattr(self.sf_api, 'auth_manager') and self.sf_api.auth_manager:
                auth_manager = self.sf_api.auth_manager
                
                # Check if we have stored credentials
                if auth_manager.has_credentials():
                    logger.info("[CONNECTION-MANAGER] Found stored credentials")
                    
                    # Test the connection
                    result = await self.test_connection('salesforce')
                    
                    if result.get('success'):
                        logger.info("[CONNECTION-MANAGER] Salesforce session restored successfully")
                        return True
                    else:
                        logger.warning("[CONNECTION-MANAGER] Stored credentials invalid")
                        return False
                else:
                    logger.info("[CONNECTION-MANAGER] No stored credentials found")
                    return False
            else:
                logger.info("[CONNECTION-MANAGER] No auth manager available")
                return False
                
        except Exception as e:
            logger.error(f"[CONNECTION-MANAGER] Error restoring Salesforce session: {e}")
            return False
    
    async def restore_woocommerce_session(self) -> bool:
        """
        Restore WooCommerce session
        
        Returns:
            True if session restored successfully
        """
        try:
            logger.info("[CONNECTION-MANAGER] Restoring WooCommerce session")
            
            if not self.woo_api:
                logger.error("[CONNECTION-MANAGER] No WooCommerce API instance")
                return False
            
            # Test the connection
            result = await self.test_connection('woocommerce')
            
            if result.get('success'):
                logger.info("[CONNECTION-MANAGER] WooCommerce session restored successfully")
                return True
            else:
                logger.warning("[CONNECTION-MANAGER] WooCommerce connection failed")
                return False
                
        except Exception as e:
            logger.error(f"[CONNECTION-MANAGER] Error restoring WooCommerce session: {e}")
            return False
    
    async def initialize_avalara_session(self) -> bool:
        """
        Initialize Avalara session
        
        Returns:
            True if session initialized successfully
        """
        try:
            logger.info("[CONNECTION-MANAGER] Initializing Avalara session")
            
            if not self.avalara_api:
                logger.error("[CONNECTION-MANAGER] No Avalara API instance")
                return False
            
            # Test the connection
            result = await self.test_connection('avalara')
            
            if result.get('success'):
                logger.info("[CONNECTION-MANAGER] Avalara session initialized successfully")
                return True
            else:
                logger.warning("[CONNECTION-MANAGER] Avalara connection failed")
                return False
                
        except Exception as e:
            logger.error(f"[CONNECTION-MANAGER] Error initializing Avalara session: {e}")
            return False
    
    def disconnect_all(self):
        """Disconnect all APIs and reset connection state"""
        logger.info("[CONNECTION-MANAGER] Disconnecting all APIs")
        
        self.sf_connected = False
        self.woo_connected = False
        self.avalara_connected = False

        # Emit status change signals
        self.connection_status_changed.emit('salesforce', False)
        self.connection_status_changed.emit('woocommerce', False)
        self.connection_status_changed.emit('avalara', False)
    
    def get_connection_summary(self) -> Dict[str, Any]:
        """Get a summary of all connection statuses"""
        connected_count = sum([self.sf_connected, self.woo_connected, self.avalara_connected])

        return {
            'connected_count': connected_count,
            'total_count': 3,
            'salesforce': self.sf_connected,
            'woocommerce': self.woo_connected,
            'avalara': self.avalara_connected,
            'all_connected': connected_count == 3,
            'none_connected': connected_count == 0
        }