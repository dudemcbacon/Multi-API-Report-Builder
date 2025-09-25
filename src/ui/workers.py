"""
Worker classes for background operations in the UI
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from PyQt6.QtCore import QThread, pyqtSignal

from src.services.async_jwt_salesforce_api import AsyncJWTSalesforceAPI
from src.services.async_woocommerce_api import AsyncWooCommerceAPI
from src.services.async_avalara_api import AsyncAvalaraAPI
from src.services.async_quickbase_api import AsyncQuickBaseAPI

logger = logging.getLogger(__name__)

class BaseAsyncDataWorker(QThread):
    """Base class for async data loading worker threads"""
    
    data_loaded = pyqtSignal(object, str)  # DataFrame, data_source_name
    error_occurred = pyqtSignal(str)
    
    def __init__(self, data_source: Dict[str, Any], worker_name: str, **kwargs):
        super().__init__()
        self.data_source = data_source
        self.worker_name = worker_name
        self.kwargs = kwargs
        
    def run(self):
        """Run the async data loading in this thread"""
        logger.info(f"[{self.worker_name}] Starting data load for: {self.data_source.get('name')}")
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async operation
            result = loop.run_until_complete(self._load_data_async())
            
            if result is not None:
                logger.info(f"[{self.worker_name}] Data loaded successfully: {type(result).__name__}")
                if hasattr(result, 'shape'):
                    logger.info(f"[{self.worker_name}] DataFrame shape: {result.shape}")
                self.data_loaded.emit(result, self.data_source['name'])
            else:
                logger.error(f"[{self.worker_name}] No data returned")
                self.error_occurred.emit(f"No data returned from {self.worker_name} API")
                
        except Exception as e:
            logger.error(f"[{self.worker_name}] Error loading data: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()
            
    async def _load_data_async(self):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _load_data_async")

class WooCommerceDataWorker(BaseAsyncDataWorker):
    """Worker thread for WooCommerce data operations"""
    
    def __init__(self, data_source: Dict[str, Any]):
        super().__init__(data_source, "WOO-WORKER")
        
    async def _load_data_async(self):
        """Async method to load WooCommerce data"""
        async with AsyncWooCommerceAPI(verbose_logging=False) as woo_api:
            return await woo_api.get_data_source_data(self.data_source['id'])

class AvalaraDataWorker(BaseAsyncDataWorker):
    """Worker thread for Avalara data operations"""
    
    def __init__(self, data_source: Dict[str, Any], start_date: str = None, end_date: str = None):
        super().__init__(data_source, "AVALARA-WORKER", start_date=start_date, end_date=end_date)
        
    async def _load_data_async(self):
        """Async method to load Avalara data"""
        
        data_type = self.data_source.get('data_type', 'companies')
        start_date = self.kwargs.get('start_date')
        end_date = self.kwargs.get('end_date')
        
        async with AsyncAvalaraAPI(verbose_logging=False) as api:
            if data_type == 'companies':
                raw_data = await api.get_companies()
                return api.to_dataframe(raw_data, "companies")
            elif data_type == 'transactions':
                if start_date and end_date:
                    raw_data = await api.get_transactions(start_date, end_date)
                else:
                    # Use default date range
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    raw_data = await api.get_transactions(start_date, end_date)
                return api.to_dataframe(raw_data, "transactions")
            elif data_type == 'tax_codes':
                raw_data = await api.get_tax_codes()
                return api.to_dataframe(raw_data, "tax_codes")
            elif data_type == 'jurisdictions':
                raw_data = await api.get_jurisdictions()
                return api.to_dataframe(raw_data, "jurisdictions")
            else:
                raise ValueError(f"Unknown Avalara data type: {data_type}")

class QuickBaseDataWorker(BaseAsyncDataWorker):
    """Worker thread for QuickBase data operations"""

    def __init__(self, data_source: Dict[str, Any], realm_hostname: str = None,
                 user_token: str = None, app_id: str = None):
        super().__init__(data_source, "QB-WORKER")
        self.realm_hostname = realm_hostname
        self.user_token = user_token
        self.app_id = app_id

    async def _load_data_async(self):
        """Async method to load QuickBase data - simplified using quickbase-client library"""
        async with AsyncQuickBaseAPI(
            realm_hostname=self.realm_hostname,
            user_token=self.user_token,
            app_id=self.app_id,
            verbose_logging=False
        ) as api:
            # Get identifiers from data source
            table_id = self.data_source.get('table_id')
            report_id = self.data_source.get('report_id')

            logger.info(f"[QB-WORKER] Loading data: table_id={table_id}, report_id={report_id}")

            if not table_id:
                logger.error("[QB-WORKER] No table_id provided")
                return None

            # Use the simplified get_report_data method
            return await api.get_report_data(table_id, report_id)

class SalesforceConnectionWorker(QThread):
    """Worker thread for Salesforce operations to avoid blocking UI"""
    
    connection_result = pyqtSignal(dict)
    reports_loaded = pyqtSignal(list)
    report_data_loaded = pyqtSignal(object, str)  # DataFrame, report_name
    report_metadata_loaded = pyqtSignal(dict, str)  # metadata, report_id
    error_occurred = pyqtSignal(str, str)  # operation, error_message
    
    def __init__(self, operation: str, sf_api: AsyncJWTSalesforceAPI, **kwargs):
        super().__init__()
        self.operation = operation
        self.sf_api = sf_api
        self.kwargs = kwargs
        self.report_id = kwargs.get('report_id')
        self.report_name = kwargs.get('report_name', 'Unknown Report')
    
    def run(self):
        logger.info(f"[WORKER-{self.operation.upper()}] " + "=" * 40)
        logger.info(f"[WORKER-{self.operation.upper()}] Starting worker operation: {self.operation}")
        logger.info(f"[WORKER-{self.operation.upper()}] Thread: {QThread.currentThread()}")
        logger.info(f"[WORKER-{self.operation.upper()}] " + "=" * 40)
        
        # Use async execution for all operations, with proper event loop management
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async operation
            loop.run_until_complete(self._run_async())
        except Exception as e:
            logger.error(f"[WORKER-{self.operation.upper()}] Error in async operation: {e}")
            self.error_occurred.emit(self.operation, str(e))
        finally:
            loop.close()
    
    async def _run_async(self):
        """Run the async operation based on operation type"""
        if self.operation == "test_connection":
            await self._test_connection_async()
        elif self.operation == "load_reports":
            await self._load_reports_async()
        elif self.operation == "load_report_data":
            await self._load_report_data_async()
        elif self.operation == "load_objects":
            await self._load_objects_async()
        elif self.operation == "execute_soql":
            await self._execute_soql_async()
        elif self.operation == "get_report_metadata":
            await self._get_report_metadata_async()
        else:
            raise ValueError(f"Unknown operation: {self.operation}")
    
    async def _test_connection_async(self):
        """Test Salesforce connection"""
        try:
            logger.info("[WORKER-TEST] Testing Salesforce connection...")
            
            # JWT authentication doesn't require browser interaction
            # Just test the connection directly (will authenticate automatically)
            result = await self.sf_api.test_connection()
            logger.info(f"[WORKER-TEST] JWT connection test result: {result}")
            self.connection_result.emit(result)
        except Exception as e:
            logger.error(f"[WORKER-TEST] Connection test failed: {e}")
            self.error_occurred.emit("test_connection", str(e))
    
    async def _load_reports_async(self):
        """Load Salesforce reports"""
        try:
            logger.info("[WORKER-REPORTS] Loading Salesforce reports...")
            reports = await self.sf_api.get_reports()
            logger.info(f"[WORKER-REPORTS] Loaded {len(reports)} reports")
            self.reports_loaded.emit(reports)
        except Exception as e:
            logger.error(f"[WORKER-REPORTS] Failed to load reports: {e}")
            self.error_occurred.emit("load_reports", str(e))
    
    async def _load_report_data_async(self):
        """Load specific report data"""
        try:
            logger.info(f"[WORKER-DATA] Loading report data for: {self.report_name}")
            
            # Get date range and field from kwargs
            start_date = self.kwargs.get('start_date')
            end_date = self.kwargs.get('end_date')
            date_field = self.kwargs.get('date_field')
            
            if start_date and end_date and date_field:
                logger.info(f"[WORKER-DATA] Using date range: {start_date} to {end_date} on field: {date_field}")
                # Create proper filters for date range
                date_filters = [
                    {
                        'column': date_field,
                        'operator': 'greaterOrEqual',
                        'value': start_date
                    },
                    {
                        'column': date_field,
                        'operator': 'lessOrEqual',
                        'value': end_date
                    }
                ]
                dataframe = await self.sf_api.get_report_data(self.report_id, filters=date_filters)
            else:
                logger.info("[WORKER-DATA] Using default date range (no filtering)")
                dataframe = await self.sf_api.get_report_data(self.report_id)
            
            logger.info(f"[WORKER-DATA] Report data loaded: {type(dataframe).__name__}")
            if hasattr(dataframe, 'shape'):
                logger.info(f"[WORKER-DATA] DataFrame shape: {dataframe.shape}")
            
            self.report_data_loaded.emit(dataframe, self.report_name)
        except Exception as e:
            logger.error(f"[WORKER-DATA] Failed to load report data: {e}")
            self.error_occurred.emit("load_report_data", str(e))
    
    async def _load_objects_async(self):
        """Load Salesforce objects"""
        try:
            logger.info("[WORKER-OBJECTS] Loading Salesforce objects...")
            objects = await self.sf_api.get_all_objects()
            logger.info(f"[WORKER-OBJECTS] Loaded {len(objects)} objects")
            
            # Return objects in connection_result format for compatibility
            result = {
                'success': True,
                'objects': objects
            }
            self.connection_result.emit(result)
        except Exception as e:
            logger.error(f"[WORKER-OBJECTS] Failed to load objects: {e}")
            self.error_occurred.emit("load_objects", str(e))
    
    async def _execute_soql_async(self):
        """Execute a custom SOQL query"""
        try:
            query = self.kwargs.get('query', '')
            source_name = self.kwargs.get('source_name', 'Custom Query')
            
            if not query:
                raise ValueError("No SOQL query provided")
            
            logger.info(f"[WORKER-SOQL] Executing SOQL query for: {source_name}")
            logger.info(f"[WORKER-SOQL] Query: {query}")
            
            # Execute the SOQL query
            dataframe = await self.sf_api.execute_soql(query, paginate=True)
            
            if dataframe is not None:
                logger.info(f"[WORKER-SOQL] Query executed successfully: {len(dataframe)} rows")
                self.report_data_loaded.emit(dataframe, source_name)
            else:
                logger.error(f"[WORKER-SOQL] Query returned no data")
                self.error_occurred.emit("execute_soql", "Query returned no data")
                
        except Exception as e:
            logger.error(f"[WORKER-SOQL] Failed to execute SOQL query: {e}")
            self.error_occurred.emit("execute_soql", str(e))
    
    async def _get_report_metadata_async(self):
        """Get report metadata including available fields"""
        try:
            report_id = self.kwargs.get('report_id', '')
            
            if not report_id:
                raise ValueError("No report ID provided")
            
            logger.info(f"[WORKER-METADATA] Fetching metadata for report: {report_id}")
            
            # Get report metadata
            metadata = await self.sf_api.get_report_describe(report_id)
            
            if metadata is not None:
                logger.info(f"[WORKER-METADATA] Successfully retrieved report metadata")
                self.report_metadata_loaded.emit(metadata, report_id)
            else:
                logger.error(f"[WORKER-METADATA] Failed to retrieve report metadata")
                self.error_occurred.emit("get_report_metadata", "Failed to retrieve report metadata")
                
        except Exception as e:
            logger.error(f"[WORKER-METADATA] Error getting report metadata: {e}")
            self.error_occurred.emit("get_report_metadata", str(e))


class QuickBaseConnectionWorker(QThread):
    """Worker thread for QuickBase operations to avoid blocking UI"""

    connection_result = pyqtSignal(dict)
    apps_loaded = pyqtSignal(list)
    tables_loaded = pyqtSignal(list, str)  # tables, app_id
    reports_loaded = pyqtSignal(list, str)  # reports, table_id
    report_data_loaded = pyqtSignal(object, str)  # DataFrame, source_name
    error_occurred = pyqtSignal(str, str)  # operation, error_message

    def __init__(self, operation: str, api_instance=None, **kwargs):
        """
        Initialize QuickBase worker

        Args:
            operation: Operation to perform ('test_connection', 'list_apps', 'list_tables', 'list_reports', 'get_report_data')
            api_instance: AsyncQuickBaseAPI instance
            **kwargs: Additional parameters for specific operations
        """
        super().__init__()
        self.operation = operation
        self.api = api_instance
        self.kwargs = kwargs
        self.loop = None

    def run(self):
        """Run the requested operation"""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

            logger.info(f"[QB-WORKER] Starting operation: {self.operation}")

            if self.operation == "test_connection":
                self.test_connection()
            elif self.operation == "list_apps":
                self.list_apps()
            elif self.operation == "list_tables":
                self.list_tables()
            elif self.operation == "list_reports":
                self.list_reports()
            elif self.operation == "get_report_data":
                self.get_report_data()
            else:
                logger.error(f"[QB-WORKER] Unknown operation: {self.operation}")
                self.error_occurred.emit(self.operation, f"Unknown operation: {self.operation}")

        except Exception as e:
            logger.error(f"[QB-WORKER] Error in {self.operation}: {e}")
            self.error_occurred.emit(self.operation, str(e))
        finally:
            # Clean up event loop
            if self.loop:
                self.loop.close()

    def test_connection(self):
        """Test QuickBase API connection"""
        try:
            logger.info("[QB-WORKER] Testing QuickBase connection")

            # Run async operation
            result = self.loop.run_until_complete(self.api.test_connection())

            logger.info(f"[QB-WORKER] Connection test result: {result.get('success', False)}")
            self.connection_result.emit(result)

        except Exception as e:
            logger.error(f"[QB-WORKER] Connection test error: {e}")
            self.error_occurred.emit("test_connection", str(e))

    def list_apps(self):
        """List available QuickBase applications"""
        try:
            logger.info("[QB-WORKER] Listing QuickBase apps")

            # Run async operation
            apps = self.loop.run_until_complete(self.api.get_apps())

            logger.info(f"[QB-WORKER] Retrieved {len(apps)} apps")
            self.apps_loaded.emit(apps)

        except Exception as e:
            logger.error(f"[QB-WORKER] Error listing apps: {e}")
            self.error_occurred.emit("list_apps", str(e))

    def list_tables(self):
        """List tables for a QuickBase application"""
        try:
            app_id = self.kwargs.get('app_id')
            if not app_id:
                raise ValueError("app_id is required for listing tables")

            logger.info(f"[QB-WORKER] Listing tables for app: {app_id}")

            # Run async operation
            tables = self.loop.run_until_complete(self.api.get_tables(app_id))

            logger.info(f"[QB-WORKER] Retrieved {len(tables)} tables")
            self.tables_loaded.emit(tables, app_id)

        except Exception as e:
            logger.error(f"[QB-WORKER] Error listing tables: {e}")
            self.error_occurred.emit("list_tables", str(e))

    def list_reports(self):
        """List reports for a QuickBase table"""
        try:
            table_id = self.kwargs.get('table_id')
            if not table_id:
                raise ValueError("table_id is required for listing reports")

            logger.info(f"[QB-WORKER] Listing reports for table: {table_id}")

            # Run async operation
            reports = self.loop.run_until_complete(self.api.get_reports(table_id))

            logger.info(f"[QB-WORKER] Retrieved {len(reports)} reports")
            self.reports_loaded.emit(reports, table_id)

        except Exception as e:
            logger.error(f"[QB-WORKER] Error listing reports: {e}")
            self.error_occurred.emit("list_reports", str(e))

    def get_report_data(self):
        """Get data from a QuickBase report or table"""
        try:
            table_id = self.kwargs.get('table_id')
            report_id = self.kwargs.get('report_id')
            source_name = self.kwargs.get('source_name', 'QuickBase Report')
            query = self.kwargs.get('query')
            limit = self.kwargs.get('limit')

            if not table_id:
                raise ValueError("table_id is required for getting report data")

            logger.info(f"[QB-WORKER] Getting data from table: {table_id}, report: {report_id}")

            # Run async operation
            df = self.loop.run_until_complete(
                self.api.get_report_data(table_id, report_id, query, limit)
            )

            if df is not None and not df.is_empty():
                logger.info(f"[QB-WORKER] Retrieved {len(df)} rows")
                self.report_data_loaded.emit(df, source_name)
            else:
                logger.warning("[QB-WORKER] No data retrieved")
                self.error_occurred.emit("get_report_data", "No data retrieved from QuickBase")

        except Exception as e:
            logger.error(f"[QB-WORKER] Error getting report data: {e}")
            self.error_occurred.emit("get_report_data", str(e))


class AsyncAutoConnectWorker(QThread):
    """Async worker for auto-connecting to APIs with optimizations"""
    
    # Signals for connection results
    connection_progress = pyqtSignal(str)  # Progress message
    connection_completed = pyqtSignal(dict)  # Results: {'sf_connected': bool, 'woo_connected': bool, 'avalara_connected': bool, 'quickbase_connected': bool}
    error_occurred = pyqtSignal(str, str)  # api_type, error_message
    data_sources_loaded = pyqtSignal(str, list)  # api_type, data_sources
    quickbase_table_reports_loaded = pyqtSignal(str, list)  # table_id, reports
    
    def __init__(self, config, sf_api_instance=None, woo_api_instance=None):
        super().__init__()
        self.config = config
        self.sf_api_instance = sf_api_instance
        self.woo_api_instance = woo_api_instance
        self.results = {'sf_connected': False, 'woo_connected': False, 'avalara_connected': False, 'quickbase_connected': False}
        
    def run(self):
        """Run async auto-connect operations"""
        import asyncio
        
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Run the async operations
            loop.run_until_complete(self._async_auto_connect())
        except Exception as e:
            logger.error(f"[ASYNC-AUTO-CONNECT] Error: {e}")
            self.error_occurred.emit("general", str(e))
        finally:
            loop.close()
    
    async def _async_auto_connect(self):
        """Perform auto-connect operations asynchronously"""
        logger.info("[ASYNC-AUTO-CONNECT] Starting optimized auto-connect...")
        
        # Test Salesforce connection
        await self._test_salesforce_connection()

        # Test WooCommerce connection
        await self._test_woocommerce_connection()

        # Test Avalara connection
        await self._test_avalara_connection()

        # Test QuickBase connection
        await self._test_quickbase_connection()

        # Emit completion signal
        self.connection_completed.emit(self.results)
        logger.info(f"[ASYNC-AUTO-CONNECT] Auto-connect completed: {self.results}")
    
    async def _test_salesforce_connection(self):
        """Test Salesforce connection and load reports if successful"""
        try:
            self.connection_progress.emit("Testing Salesforce connection...")
            
            if self.sf_api_instance:
                # Test existing API instance
                result = await self.sf_api_instance.test_connection()
                
                if result.get('success'):
                    self.results['sf_connected'] = True
                    logger.info("[ASYNC-AUTO-CONNECT] Salesforce connection successful")
                    
                    # Load reports if connection successful
                    self.connection_progress.emit("Loading Salesforce reports...")
                    try:
                        reports = await self.sf_api_instance.get_reports()
                        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(reports)} Salesforce reports")
                        self.data_sources_loaded.emit("salesforce", reports)
                    except Exception as e:
                        logger.warning(f"[ASYNC-AUTO-CONNECT] Failed to load Salesforce reports: {e}")
                        self.data_sources_loaded.emit("salesforce", [])
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.warning(f"[ASYNC-AUTO-CONNECT] Salesforce connection failed: {error_msg}")
                    self.results['sf_connected'] = False
                    # Emit error signal to trigger authentication if needed
                    self.error_occurred.emit("salesforce", error_msg)
            else:
                logger.info("[ASYNC-AUTO-CONNECT] No Salesforce API instance available")
                self.results['sf_connected'] = False
                
        except Exception as e:
            logger.error(f"[ASYNC-AUTO-CONNECT] Salesforce connection error: {e}")
            self.results['sf_connected'] = False
            self.error_occurred.emit("salesforce", str(e))
    
    async def _test_woocommerce_connection(self):
        """Test WooCommerce connection and load data sources if successful"""
        try:
            self.connection_progress.emit("Testing WooCommerce connection...")
            
            # Always create a fresh API instance to avoid event loop issues
            from src.services.async_woocommerce_api import AsyncWooCommerceAPI
            async with AsyncWooCommerceAPI(verbose_logging=False) as woo_api:
                result = await woo_api.test_connection()
                
                if result.get('success'):
                    self.results['woo_connected'] = True
                    logger.info("[ASYNC-AUTO-CONNECT] WooCommerce connection successful")
                    
                    # Load data sources if connection successful
                    self.connection_progress.emit("Loading WooCommerce data sources...")
                    try:
                        data_sources = await woo_api.get_data_sources()
                        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(data_sources)} WooCommerce data sources")
                        self.data_sources_loaded.emit("woocommerce", data_sources)
                    except Exception as e:
                        logger.warning(f"[ASYNC-AUTO-CONNECT] Failed to load WooCommerce data sources: {e}")
                        self.data_sources_loaded.emit("woocommerce", [])
                else:
                    logger.warning(f"[ASYNC-AUTO-CONNECT] WooCommerce connection failed: {result.get('error')}")
                    self.results['woo_connected'] = False
                
        except Exception as e:
            logger.error(f"[ASYNC-AUTO-CONNECT] WooCommerce connection error: {e}")
            self.results['woo_connected'] = False
            self.error_occurred.emit("woocommerce", str(e))
    
    async def _test_avalara_connection(self):
        """Test Avalara connection and load data sources if successful"""
        try:
            self.connection_progress.emit("Testing Avalara connection...")
            
            # Always create a fresh API instance to avoid event loop issues
            from src.services.async_avalara_api import AsyncAvalaraAPI
            async with AsyncAvalaraAPI(verbose_logging=False) as avalara_api:
                result = await avalara_api.test_connection()
                
                if result.get('success'):
                    self.results['avalara_connected'] = True
                    logger.info("[ASYNC-AUTO-CONNECT] Avalara connection successful")
                    
                    # Load data sources if connection successful
                    self.connection_progress.emit("Loading Avalara data sources...")
                    try:
                        # Create list of available data sources for Avalara
                        data_sources = [
                            {'id': 'companies', 'name': 'Companies', 'type': 'companies', 'data_type': 'companies', 'icon': 'fa5s.building', 'modified': ''},
                            {'id': 'transactions', 'name': 'Transactions', 'type': 'transactions', 'data_type': 'transactions', 'icon': 'fa5s.receipt', 'modified': ''},
                            {'id': 'tax_codes', 'name': 'Tax Codes', 'type': 'tax_codes', 'data_type': 'tax_codes', 'icon': 'fa5s.tags', 'modified': ''},
                            {'id': 'jurisdictions', 'name': 'Jurisdictions', 'type': 'jurisdictions', 'data_type': 'jurisdictions', 'icon': 'fa5s.map-marker-alt', 'modified': ''}
                        ]
                        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(data_sources)} Avalara data sources")
                        self.data_sources_loaded.emit("avalara", data_sources)
                    except Exception as e:
                        logger.warning(f"[ASYNC-AUTO-CONNECT] Failed to load Avalara data sources: {e}")
                        self.data_sources_loaded.emit("avalara", [])
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.warning(f"[ASYNC-AUTO-CONNECT] Avalara connection failed: {error_msg}")
                    self.results['avalara_connected'] = False
                    self.error_occurred.emit("avalara", error_msg)
                
        except Exception as e:
            logger.error(f"[ASYNC-AUTO-CONNECT] Avalara connection error: {e}")
            self.results['avalara_connected'] = False
            self.error_occurred.emit("avalara", str(e))

    async def _test_quickbase_connection(self):
        """Test QuickBase connection and load data sources if successful"""
        try:
            self.connection_progress.emit("Testing QuickBase connection...")

            # Always create a fresh API instance to avoid event loop issues
            from src.services.async_quickbase_api import AsyncQuickBaseAPI
            async with AsyncQuickBaseAPI(verbose_logging=False) as qb_api:
                result = await qb_api.test_connection()

                if result.get('success'):
                    self.results['quickbase_connected'] = True
                    logger.info("[ASYNC-AUTO-CONNECT] QuickBase connection successful")

                    # Load data sources if connection successful
                    self.connection_progress.emit("Loading QuickBase data sources...")
                    try:
                        # Get actual tables using async method
                        tables = await qb_api.get_apps()  # This now returns actual tables
                        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(tables)} QuickBase data sources")
                        self.data_sources_loaded.emit("quickbase", tables)

                        # Also load reports for the first few tables to populate tree
                        if len(tables) > 0:
                            self.connection_progress.emit("Loading QuickBase reports...")
                            for i, table in enumerate(tables[:3]):  # Load reports for first 3 tables
                                try:
                                    table_id = table.get('table_id', table.get('id'))
                                    if table_id:
                                        reports = await qb_api.get_reports(table_id)
                                        logger.info(f"[ASYNC-AUTO-CONNECT] Loaded {len(reports)} reports for table {table['name']}")
                                        # Emit signal for each table's reports
                                        self.quickbase_table_reports_loaded.emit(table_id, reports)
                                except Exception as e:
                                    logger.warning(f"[ASYNC-AUTO-CONNECT] Failed to load reports for table {table.get('name', 'Unknown')}: {e}")

                    except Exception as e:
                        logger.warning(f"[ASYNC-AUTO-CONNECT] Failed to load QuickBase data sources: {e}")
                        self.data_sources_loaded.emit("quickbase", [])
                else:
                    error_msg = result.get('message', result.get('error', 'Unknown error'))
                    logger.warning(f"[ASYNC-AUTO-CONNECT] QuickBase connection failed: {error_msg}")
                    self.results['quickbase_connected'] = False
                    self.error_occurred.emit("quickbase", error_msg)

        except Exception as e:
            logger.error(f"[ASYNC-AUTO-CONNECT] QuickBase connection error: {e}")
            self.results['quickbase_connected'] = False
            self.error_occurred.emit("quickbase", str(e))

