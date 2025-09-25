"""
Data Source Manager for handling data loading, caching, and worker management
"""
import logging
from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtCore import QObject, pyqtSignal
from datetime import datetime, timedelta

# Import the worker classes
from ..workers import BaseAsyncDataWorker, WooCommerceDataWorker, AvalaraDataWorker, QuickBaseDataWorker


logger = logging.getLogger(__name__)

class DataSourceManager(QObject):
    """
    Manages data loading, caching, and worker thread coordination
    """
    
    # Signals for data events
    data_loaded = pyqtSignal(object, str)  # DataFrame, data_source_name
    data_loading_started = pyqtSignal(str)  # data_source_name
    data_loading_error = pyqtSignal(str, str)  # data_source_name, error_message
    
    # Signals for reports/data sources loaded
    reports_loaded = pyqtSignal(list)  # List of reports
    data_sources_loaded = pyqtSignal(str, list)  # api_type, List of data sources
    
    def __init__(self):
        super().__init__()
        
        # Data caches
        self.salesforce_reports_cache = []
        self.woocommerce_data_sources_cache = []
        self.avalara_data_sources_cache = []
        self.quickbase_data_sources_cache = []
        
        # Active workers
        self.active_workers = {}
        
        # Initialize Avalara data sources
        self._initialize_avalara_data_sources()
    
    def _initialize_avalara_data_sources(self):
        """Initialize Avalara data sources structure"""
        self.avalara_data_sources_cache = [
            {
                'id': 'companies',
                'name': 'Companies',
                'type': 'companies',
                'icon': 'fa5s.building',
                'data_type': 'companies',
                'modified': 'Static'
            },
            {
                'id': 'transactions',
                'name': 'Transactions',
                'type': 'transactions',
                'icon': 'fa5s.receipt',
                'data_type': 'transactions',
                'modified': 'Dynamic'
            },
            {
                'id': 'tax_codes',
                'name': 'Tax Codes',
                'type': 'tax_codes',
                'icon': 'fa5s.tags',
                'data_type': 'tax_codes',
                'modified': 'Static'
            },
            {
                'id': 'jurisdictions',
                'name': 'Jurisdictions',
                'type': 'jurisdictions',
                'icon': 'fa5s.map-marker-alt',
                'data_type': 'jurisdictions',
                'modified': 'Static'
            }
        ]
    
    def load_data_source(self, data_source: Dict[str, Any], start_date: str = None, end_date: str = None):
        """
        Load data from a specific data source using appropriate worker
        
        Args:
            data_source: Dictionary containing data source information
            start_date: Optional start date for data filtering
            end_date: Optional end date for data filtering
        """
        try:
            api_type = data_source.get('api_type', 'unknown')
            source_name = data_source.get('name', 'Unknown')
            
            logger.info(f"[DATA-MANAGER] Loading data source: {source_name} ({api_type})")
            
            # Emit loading started signal
            self.data_loading_started.emit(source_name)
            
            # Create appropriate worker based on API type
            if api_type == 'woocommerce':
                self._load_woocommerce_data(data_source)
            elif api_type == 'avalara':
                self._load_avalara_data(data_source, start_date, end_date)
            elif api_type == 'salesforce':
                self._load_salesforce_data(data_source, start_date, end_date)
            elif api_type == 'quickbase':
                self._load_quickbase_data(data_source)
            else:
                error_msg = f"Unsupported API type: {api_type}"
                logger.error(f"[DATA-MANAGER] {error_msg}")
                self.data_loading_error.emit(source_name, error_msg)
                
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error loading data source: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))
    
    def _load_woocommerce_data(self, data_source: Dict[str, Any]):
        """Load WooCommerce data using worker thread"""
        try:
            source_name = data_source.get('name', 'Unknown')
            
            # Stop any existing worker for this source
            if source_name in self.active_workers:
                self.active_workers[source_name].quit()
                self.active_workers[source_name].wait()
                del self.active_workers[source_name]
            
            # Create and start worker
            worker = WooCommerceDataWorker(data_source)
            worker.data_loaded.connect(self._on_worker_data_loaded)
            worker.error_occurred.connect(self._on_worker_error)
            worker.finished.connect(lambda: self._on_worker_finished(source_name))
            
            self.active_workers[source_name] = worker
            worker.start()
            
            logger.info(f"[DATA-MANAGER] Started WooCommerce worker for: {source_name}")
            
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error starting WooCommerce worker: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))
    
    def _load_avalara_data(self, data_source: Dict[str, Any], start_date: str = None, end_date: str = None):
        """Load Avalara data using worker thread"""
        try:
            source_name = data_source.get('name', 'Unknown')
            
            # Stop any existing worker for this source
            if source_name in self.active_workers:
                self.active_workers[source_name].quit()
                self.active_workers[source_name].wait()
                del self.active_workers[source_name]
            
            # Create and start worker
            worker = AvalaraDataWorker(data_source, start_date, end_date)
            worker.data_loaded.connect(self._on_worker_data_loaded)
            worker.error_occurred.connect(self._on_worker_error)
            worker.finished.connect(lambda: self._on_worker_finished(source_name))
            
            self.active_workers[source_name] = worker
            worker.start()
            
            logger.info(f"[DATA-MANAGER] Started Avalara worker for: {source_name}")
            
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error starting Avalara worker: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))

    def _load_quickbase_data(self, data_source: Dict[str, Any]):
        """Load QuickBase data using worker thread"""
        try:
            source_name = data_source.get('name', 'Unknown')

            # Stop any existing worker for this source
            if source_name in self.active_workers:
                self.active_workers[source_name].quit()
                self.active_workers[source_name].wait()
                del self.active_workers[source_name]

            # Get QuickBase credentials from config or environment
            import os
            realm_hostname = os.getenv('QUICKBASE_REALM_HOSTNAME')
            user_token = os.getenv('QUICKBASE_USER_TOKEN')
            app_id = os.getenv('QUICKBASE_APP_ID')

            # Create and start worker
            worker = QuickBaseDataWorker(data_source, realm_hostname, user_token, app_id)
            worker.data_loaded.connect(self._on_worker_data_loaded)
            worker.error_occurred.connect(self._on_worker_error)
            worker.finished.connect(lambda: self._on_worker_finished(source_name))

            self.active_workers[source_name] = worker
            worker.start()

            logger.info(f"[DATA-MANAGER] Started QuickBase worker for: {source_name}")

        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error starting QuickBase worker: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))
    
    def _load_salesforce_data(self, data_source: Dict[str, Any], start_date: str = None, end_date: str = None):
        """Load Salesforce data using appropriate method"""
        try:
            source_name = data_source.get('name', 'Unknown')
            source_type = data_source.get('type', 'report')
            
            logger.info(f"[DATA-MANAGER] Loading Salesforce data: {source_name} (type: {source_type})")
            
            if source_type == 'custom_report':
                # Handle custom SOQL queries
                self._load_salesforce_custom_query(data_source)
            else:
                # Handle regular reports (this would need to be implemented)
                # For now, emit an error
                error_msg = f"Standard Salesforce reports not yet supported in DataSourceManager"
                logger.warning(f"[DATA-MANAGER] {error_msg}")
                self.data_loading_error.emit(source_name, error_msg)
                
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error loading Salesforce data: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))
    
    def _load_salesforce_custom_query(self, data_source: Dict[str, Any]):
        """Load data from a custom Salesforce SOQL query"""
        try:
            source_name = data_source.get('name', 'Unknown')
            query = data_source.get('query', '')
            
            if not query:
                error_msg = "No SOQL query provided"
                logger.error(f"[DATA-MANAGER] {error_msg}")
                self.data_loading_error.emit(source_name, error_msg)
                return
            
            logger.info(f"[DATA-MANAGER] Executing custom SOQL query for: {source_name}")
            
            # Create a custom worker for SOQL execution
            # We'll need to create a custom worker class or use the existing SalesforceConnectionWorker
            from ..workers import SalesforceConnectionWorker
            
            # Get the Salesforce API instance from the main window
            # This is a bit of a hack, but it works for now
            import inspect
            frame = inspect.currentframe()
            while frame:
                if 'self' in frame.f_locals and hasattr(frame.f_locals['self'], 'sf_api'):
                    sf_api = frame.f_locals['self'].sf_api
                    break
                frame = frame.f_back
            
            if not sf_api:
                error_msg = "Salesforce API instance not available"
                logger.error(f"[DATA-MANAGER] {error_msg}")
                self.data_loading_error.emit(source_name, error_msg)
                return
            
            # Create worker to execute SOQL query
            worker = SalesforceConnectionWorker("execute_soql", sf_api, query=query, source_name=source_name)
            worker.report_data_loaded.connect(self._on_salesforce_custom_data_loaded)
            worker.error_occurred.connect(lambda op, err: self._on_worker_error(err))
            worker.finished.connect(lambda: self._on_worker_finished(source_name))
            
            # Stop any existing worker for this source
            if source_name in self.active_workers:
                self.active_workers[source_name].quit()
                self.active_workers[source_name].wait()
                del self.active_workers[source_name]
            
            self.active_workers[source_name] = worker
            worker.start()
            
            logger.info(f"[DATA-MANAGER] Started custom SOQL worker for: {source_name}")
            
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error starting custom SOQL worker: {e}")
            self.data_loading_error.emit(data_source.get('name', 'Unknown'), str(e))
    
    def _on_salesforce_custom_data_loaded(self, dataframe, source_name: str):
        """Handle custom Salesforce data loaded"""
        logger.info(f"[DATA-MANAGER] Custom Salesforce data loaded for: {source_name}")
        if hasattr(dataframe, 'shape'):
            logger.info(f"[DATA-MANAGER] DataFrame shape: {dataframe.shape}")
        
        # Emit data loaded signal
        self.data_loaded.emit(dataframe, source_name)
    
    def _on_worker_data_loaded(self, dataframe, source_name: str):
        """Handle worker data loaded signal"""
        logger.info(f"[DATA-MANAGER] Worker data loaded for: {source_name}")
        if hasattr(dataframe, 'shape'):
            logger.info(f"[DATA-MANAGER] DataFrame shape: {dataframe.shape}")
        
        # Emit data loaded signal
        self.data_loaded.emit(dataframe, source_name)
    
    def _on_worker_error(self, error_message: str):
        """Handle worker error signal"""
        logger.error(f"[DATA-MANAGER] Worker error: {error_message}")
        # Try to determine source name from active workers
        # This is a limitation - we could improve this by enhancing the worker error signal
        self.data_loading_error.emit("Unknown", error_message)
    
    def _on_worker_finished(self, source_name: str):
        """Handle worker finished signal"""
        logger.info(f"[DATA-MANAGER] Worker finished for: {source_name}")
        
        # Clean up worker reference
        if source_name in self.active_workers:
            del self.active_workers[source_name]
    
    def update_salesforce_reports(self, reports: List[Dict[str, Any]]):
        """Update Salesforce reports cache"""
        logger.info(f"[DATA-MANAGER] Updating Salesforce reports cache with {len(reports)} reports")
        self.salesforce_reports_cache = reports
        self.reports_loaded.emit(reports)
    
    def update_woocommerce_data_sources(self, data_sources: List[Dict[str, Any]]):
        """Update WooCommerce data sources cache"""
        logger.info(f"[DATA-MANAGER] Updating WooCommerce data sources cache with {len(data_sources)} sources")
        self.woocommerce_data_sources_cache = data_sources
        self.data_sources_loaded.emit('woocommerce', data_sources)
    
    def update_avalara_data_sources(self, data_sources: List[Dict[str, Any]]):
        """Update Avalara data sources cache"""
        logger.info(f"[DATA-MANAGER] Updating Avalara data sources cache with {len(data_sources)} sources")
        self.avalara_data_sources_cache = data_sources
        self.data_sources_loaded.emit('avalara', data_sources)

    def update_quickbase_data_sources(self, data_sources: List[Dict[str, Any]]):
        """Update QuickBase data sources cache"""
        logger.info(f"[DATA-MANAGER] Updating QuickBase data sources cache with {len(data_sources)} sources")
        self.quickbase_data_sources_cache = data_sources
        self.data_sources_loaded.emit('quickbase', data_sources)
    
    def get_salesforce_reports(self) -> List[Dict[str, Any]]:
        """Get cached Salesforce reports"""
        return self.salesforce_reports_cache
    
    def get_woocommerce_data_sources(self) -> List[Dict[str, Any]]:
        """Get cached WooCommerce data sources"""
        return self.woocommerce_data_sources_cache
    
    def get_avalara_data_sources(self) -> List[Dict[str, Any]]:
        """Get cached Avalara data sources"""
        return self.avalara_data_sources_cache

    def get_quickbase_data_sources(self) -> List[Dict[str, Any]]:
        """Get cached QuickBase data sources"""
        return self.quickbase_data_sources_cache
    
    def get_data_source_by_id(self, api_type: str, source_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific data source by ID"""
        if api_type == 'woocommerce':
            sources = self.woocommerce_data_sources_cache
        elif api_type == 'avalara':
            sources = self.avalara_data_sources_cache
        elif api_type == 'quickbase':
            sources = self.quickbase_data_sources_cache
        else:
            return None
        
        for source in sources:
            if source.get('id') == source_id:
                return source
        
        return None
    
    def stop_all_workers(self):
        """Stop all active workers"""
        logger.info("[DATA-MANAGER] Stopping all active workers")
        
        for source_name, worker in self.active_workers.items():
            try:
                worker.quit()
                worker.wait(5000)  # Wait up to 5 seconds
                logger.info(f"[DATA-MANAGER] Stopped worker for: {source_name}")
            except Exception as e:
                logger.error(f"[DATA-MANAGER] Error stopping worker for {source_name}: {e}")
        
        self.active_workers.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached data"""
        return {
            'salesforce_reports': len(self.salesforce_reports_cache),
            'woocommerce_sources': len(self.woocommerce_data_sources_cache),
            'avalara_sources': len(self.avalara_data_sources_cache),
            'active_workers': len(self.active_workers),
            'worker_names': list(self.active_workers.keys())
        }
    
    def clear_all_caches(self):
        """Clear all data caches"""
        logger.info("[DATA-MANAGER] Clearing all data caches")
        
        self.salesforce_reports_cache.clear()
        self.woocommerce_data_sources_cache.clear()
        self.avalara_data_sources_cache.clear()
        
        # Reinitialize Avalara data sources
        self._initialize_avalara_data_sources()
    
    def load_salesforce_reports_async(self, api_instance, callback: Callable[[List[Dict[str, Any]]], None]):
        """
        Load Salesforce reports asynchronously
        
        Args:
            api_instance: Salesforce API instance
            callback: Callback function to handle loaded reports
        """
        # This would typically use a worker thread, but for now we'll keep it simple
        # In a full implementation, you'd create a SalesforceReportsWorker
        logger.info("[DATA-MANAGER] Loading Salesforce reports (async placeholder)")
        
        # For now, just use the existing cached data
        if self.salesforce_reports_cache:
            callback(self.salesforce_reports_cache)
        else:
            logger.info("[DATA-MANAGER] No cached Salesforce reports available")
            callback([])
    
    def load_woocommerce_data_sources_async(self, api_instance, callback: Callable[[List[Dict[str, Any]]], None]):
        """
        Load WooCommerce data sources asynchronously
        
        Args:
            api_instance: WooCommerce API instance
            callback: Callback function to handle loaded data sources
        """
        logger.info("[DATA-MANAGER] Loading WooCommerce data sources (async placeholder)")
        
        try:
            if api_instance:
                # Get data sources from API
                data_sources = api_instance.get_data_sources()
                self.update_woocommerce_data_sources(data_sources)
                callback(data_sources)
            else:
                logger.warning("[DATA-MANAGER] No WooCommerce API instance available")
                callback([])
                
        except Exception as e:
            logger.error(f"[DATA-MANAGER] Error loading WooCommerce data sources: {e}")
            callback([])