"""
Production-ready Async Salesforce API implementation using aiohttp
High-performance alternative to the current requests-based implementation
"""
import asyncio
import aiohttp
import logging
import re
from typing import Dict, List, Optional, Any
import polars as pl

from .auth_manager import SalesforceAuthManager

logger = logging.getLogger(__name__)

# Security validation functions (duplicated from salesforce_api.py for independence)
def validate_report_id(report_id: str) -> bool:
    """Validate Salesforce report ID format"""
    if not report_id or not isinstance(report_id, str):
        return False
    # Salesforce IDs are 15 or 18 characters, alphanumeric
    pattern = r'^[a-zA-Z0-9]{15}([a-zA-Z0-9]{3})?$'
    return bool(re.match(pattern, report_id))

def validate_soql_query(query: str) -> bool:
    """Basic SOQL query validation to prevent injection"""
    if not query or not isinstance(query, str):
        return False
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r';\s*drop\s+',
        r';\s*delete\s+',
        r';\s*update\s+',
        r';\s*insert\s+',
        r'--',
        r'/\*',
        r'\*/',
    ]
    
    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, query_lower):
            return False
    
    # Must start with SELECT
    if not query_lower.strip().startswith('select'):
        return False
        
    return True

def validate_filter_parameter(column: str, operator: str, value: str) -> bool:
    """Validate Salesforce report filter parameters"""
    if not all(isinstance(param, str) for param in [column, operator, value]):
        return False
    
    # Validate column name (letters, numbers, dots, underscores only)
    if not re.match(r'^[a-zA-Z0-9._]+$', column):
        return False
    
    # Validate operator (whitelist of allowed operators)
    allowed_operators = {
        'equals', 'notEqual', 'lessThan', 'greaterThan', 
        'lessOrEqual', 'greaterOrEqual', 'contains', 
        'notContain', 'startsWith', 'includes', 'excludes'
    }
    if operator not in allowed_operators:
        return False
    
    # Value should not contain control characters
    if re.search(r'[\x00-\x1f\x7f]', value):
        return False
        
    return True

class AsyncSalesforceAPI:
    """
    High-performance async Salesforce API client using aiohttp
    Handles all Salesforce API operations with OAuth 2.0 authentication
    """
    
    def __init__(self, instance_url: str = "https://login.salesforce.com", consumer_key: Optional[str] = None, consumer_secret: Optional[str] = None, auth_manager: Optional[SalesforceAuthManager] = None, verbose_logging: bool = False):
        """
        Initialize Async Salesforce API client
        
        Args:
            instance_url: Salesforce login URL
            consumer_key: Consumer key for OAuth (optional, will use environment variable if not provided)
            consumer_secret: Consumer secret for OAuth (optional)
            auth_manager: Existing auth manager instance to reuse (optional)
            verbose_logging: Enable detailed logging for debugging (default: False for production)
        """
        self.instance_url = instance_url
        self.verbose_logging = verbose_logging
        
        if auth_manager:
            self.auth_manager = auth_manager
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Using existing auth manager instance")
        else:
            # Create new auth manager with consumer key if provided
            self.auth_manager = SalesforceAuthManager(instance_url, consumer_secret)
            # Set consumer key if provided (auth manager gets it from environment by default)
            if consumer_key:
                self.auth_manager.CONSUMER_KEY = consumer_key
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Created new auth manager instance")
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Optimized connection pool settings for Salesforce API
        self.connector_config = {
            'limit': 50,  # Reduced total pool size for single-host usage
            'limit_per_host': 20,  # Optimized for Salesforce servers
            'ttl_dns_cache': 600,  # Longer DNS cache for stable Salesforce endpoints
            'use_dns_cache': True,
            'keepalive_timeout': 90,  # Longer keepalive for Salesforce session reuse
            'enable_cleanup_closed': True,
            'force_close': False,  # Enable connection reuse
        }
        
        # Session-level auth caching
        self._cached_token_valid = None
        self._cached_access_token = None
        self._cached_instance_url = None
    
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session for the current event loop"""
        current_loop = asyncio.get_event_loop()
        
        # Check if session exists and is valid for current loop
        session_invalid = (
            self.session is None or 
            self.session.closed or
            getattr(self.session, '_loop', None) != current_loop
        )
        
        if session_invalid:
            # Close existing session if it exists but is invalid
            if self.session and not self.session.closed:
                try:
                    await self.session.close()
                except Exception as e:
                    logger.warning(f"[ASYNC-SF-API] Error closing old session: {e}")
            
            # Create new session for current event loop
            connector = aiohttp.TCPConnector(**self.connector_config)
            # Optimized timeouts for Salesforce API responsiveness
            timeout = aiohttp.ClientTimeout(total=90, connect=10, sock_read=60)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            )
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] Created new session for event loop: {id(current_loop)}")
    
    def _get_cached_auth_info(self) -> Optional[tuple]:
        """
        Get cached authentication info to avoid redundant calls
        
        Returns:
            Tuple of (access_token, instance_url) if valid, None otherwise
        """
        # Always check token validity first - tokens may have been refreshed externally
        token_is_valid = self.auth_manager.is_token_valid()
        
        # If we have cached info and token is still valid, return cached
        if (self._cached_token_valid is True and 
            self._cached_access_token is not None and 
            self._cached_instance_url is not None and 
            token_is_valid):
            
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Using cached auth info (token still valid)")
            return (self._cached_access_token, self._cached_instance_url)
        
        # Cache miss or token changed - refresh cache
        if token_is_valid:
            self._cached_token_valid = True
            self._cached_access_token = self.auth_manager.access_token
            self._cached_instance_url = self.auth_manager.get_instance_url()
            
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Refreshed auth info cache with valid token")
            
            return (self._cached_access_token, self._cached_instance_url)
        else:
            # Token is invalid - try to refresh it
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Token invalid - attempting refresh...")
            
            if self.auth_manager.refresh_token:
                # Only try to refresh if we have a refresh token
                if self.auth_manager.refresh_access_token():
                    # Refresh successful - update cache
                    self._cached_token_valid = True
                    self._cached_access_token = self.auth_manager.access_token
                    self._cached_instance_url = self.auth_manager.get_instance_url()
                    
                    if self.verbose_logging:
                        logger.info("[ASYNC-SF-API] Token refreshed successfully")
                    
                    return (self._cached_access_token, self._cached_instance_url)
                else:
                    # Refresh failed - clear cache
                    self._cached_token_valid = False
                    self._cached_access_token = None
                    self._cached_instance_url = None
                    
                    if self.verbose_logging:
                        logger.info("[ASYNC-SF-API] Token refresh failed - cleared auth cache")
                    
                    return None
            else:
                # No refresh token available - clear cache and return None
                self._cached_token_valid = False
                self._cached_access_token = None
                self._cached_instance_url = None
                
                if self.verbose_logging:
                    logger.info("[ASYNC-SF-API] No refresh token available - cleared auth cache")
                
                return None
    
    def _clear_auth_cache(self):
        """Clear cached auth info"""
        self._cached_token_valid = None
        self._cached_access_token = None
        self._cached_instance_url = None
    
    async def _get_auth_info(self) -> Optional[Dict[str, str]]:
        """Get auth info for API calls"""
        auth_info = self._get_cached_auth_info()
        if auth_info is None:
            return None
        
        access_token, instance_url = auth_info
        return {
            'access_token': access_token,
            'instance_url': instance_url
        }
    
    async def close(self):
        """Close the aiohttp session safely"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                if self.verbose_logging:
                    logger.info("[ASYNC-SF-API] Session closed successfully")
            except Exception as e:
                logger.warning(f"[ASYNC-SF-API] Error closing session: {e}")
            finally:
                self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def has_credentials(self) -> bool:
        """Check if OAuth credentials are available"""
        return self.auth_manager.has_credentials()
    
    async def connect_with_browser(self, parent_widget=None) -> bool:
        """
        Connect to Salesforce using system browser OAuth flow
        
        Args:
            parent_widget: Parent widget (unused but kept for compatibility)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        logger.info("[ASYNC-SF-API] Starting Salesforce browser connection")
        
        try:
            # Use auth manager directly for OAuth authentication
            logger.info("[ASYNC-SF-API] Starting OAuth authentication...")
            auth_result = self.auth_manager.authenticate_with_browser()
            logger.info(f"[ASYNC-SF-API] OAuth authentication result: {auth_result}")
            
            if not auth_result:
                logger.error("[ASYNC-SF-API] OAuth authentication failed")
                return False
            
            logger.info("[ASYNC-SF-API] OAuth authentication successful")
            
            # Clear cache to force refresh with new tokens
            self._clear_auth_cache()
            
            # Test the connection
            logger.info("[ASYNC-SF-API] Testing connection after OAuth success...")
            test_result = await self.test_connection()
            
            if test_result.get('success', False):
                logger.info("[ASYNC-SF-API] Connection test successful")
                return True
            else:
                logger.error(f"[ASYNC-SF-API] Connection test failed: {test_result.get('error', 'Unknown error')}")
                return False
            
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] OAuth connection error: {e}")
            return False
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the Salesforce connection asynchronously
        
        Returns:
            Dict with connection status and details
        """
        await self._ensure_session()
        
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Getting access token from auth manager...")
            
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] Token is expired and no refresh token available")
                logger.info("[ASYNC-SF-API] Attempting automatic re-authentication...")
                # Clear cache and try to authenticate automatically
                self._clear_auth_cache()
                if not await self.connect_with_browser():
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Unable to obtain access token after automatic re-authentication'
                    }
                
                # Refresh auth info after successful authentication
                auth_info = self._get_cached_auth_info()
                if auth_info is None:
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Unable to obtain access token after re-authentication'
                    }
            
            access_token, instance_url = auth_info
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] Access token: {'Present' if access_token else 'Missing'}")
                logger.info(f"[ASYNC-SF-API] Instance URL: {instance_url}")
            
            if not access_token or not instance_url:
                logger.warning("[ASYNC-SF-API] Missing access token or instance URL, attempting re-authentication...")
                # Clear cache and try to authenticate
                self._clear_auth_cache()
                if not await self.connect_with_browser():
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Unable to obtain access token'
                    }
                
                # Refresh auth info after successful authentication
                auth_info = self._get_cached_auth_info()
                if auth_info is None:
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Unable to obtain access token after re-authentication'
                    }
                
                access_token, instance_url = auth_info
                if self.verbose_logging:
                    logger.info(f"[ASYNC-SF-API] After re-auth - Access token: {'Present' if access_token else 'Missing'}")
                    logger.info(f"[ASYNC-SF-API] After re-auth - Instance URL: {instance_url}")
            
            # Test connection with organization query
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            test_url = f"{instance_url}/services/data/v63.0/query"
            params = {'q': 'SELECT Id, Name FROM Organization LIMIT 1'}
            
            async with self.session.get(test_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    org_name = 'Unknown Organization'
                    if data.get('records') and len(data['records']) > 0:
                        org_name = data['records'][0].get('Name', 'Unknown Organization')
                    
                    return {
                        'success': True,
                        'organization': org_name,
                        'instance_url': instance_url,
                        'details': f'Connection successful. Organization: {org_name}'
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f'HTTP {response.status}',
                        'details': error_text
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Connection test failed'
            }
    
    async def get_reports(self) -> List[Dict[str, Any]]:
        """
        Get list of available reports asynchronously
        
        Returns:
            List of report dictionaries with metadata
        """
        await self._ensure_session()
        
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Getting access token for reports...")
            
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] Token is expired and no refresh token available")
                logger.warning("[ASYNC-SF-API] No authentication available - returning empty result")
                return []
            
            access_token, instance_url = auth_info
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] Access token: {'Present' if access_token else 'Missing'}")
                logger.info(f"[ASYNC-SF-API] Instance URL: {instance_url}")
            
            if not access_token or not instance_url:
                logger.warning("[ASYNC-SF-API] Missing access token or instance URL for reports")
                return []
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Query reports
            reports_query = """
                SELECT Id, Name, Description, FolderName, CreatedDate, LastModifiedDate, 
                       Format, LastRunDate, OwnerId, Owner.Name
                FROM Report 
                ORDER BY FolderName, Name
            """
            
            reports_url = f"{instance_url}/services/data/v63.0/query"
            params = {'q': reports_query}
            
            async with self.session.get(reports_url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    reports = []
                    for record in data.get('records', []):
                        report = {
                            'id': record['Id'],
                            'name': record['Name'],
                            'description': record.get('Description', ''),
                            'folder': record.get('FolderName', 'Unfiled Public Reports'),
                            'format': record.get('Format', 'Tabular'),
                            'created_date': record.get('CreatedDate', ''),
                            'modified_date': record.get('LastModifiedDate', ''),
                            'last_run_date': record.get('LastRunDate', ''),
                            'owner_id': record.get('OwnerId', ''),
                            'owner_name': record.get('Owner', {}).get('Name', '') if record.get('Owner') else ''
                        }
                        reports.append(report)
                    
                    if self.verbose_logging:
                        logger.info(f"[ASYNC-SF-API] Retrieved {len(reports)} reports")
                    return reports
                else:
                    logger.error(f"[ASYNC-SF-API] Failed to get reports: HTTP {response.status}")
                    return []
        
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error retrieving reports: {e}")
            return []
    
    async def get_report_data(self, report_id: str, 
                             filters: Optional[List[Dict[str, str]]] = None, 
                             essential_fields_only: Optional[List[str]] = None) -> Optional[pl.DataFrame]:
        """
        Get data from a specific report asynchronously
        
        Args:
            report_id: Salesforce report ID
            filters: Optional list of filters
            essential_fields_only: Optional list of field names to return for memory efficiency
            
        Returns:
            Polars DataFrame with report data, or None if failed
        """
        # Validate report ID for security
        if not validate_report_id(report_id):
            logger.error(f"Invalid report ID rejected for security reasons: {report_id}")
            return None
        
        # Validate filters if provided
        if filters:
            for filter_item in filters:
                column = filter_item.get('column', '')
                operator = filter_item.get('operator', '')
                value = filter_item.get('value', '')
                if not validate_filter_parameter(column, operator, value):
                    logger.error(f"Invalid filter parameter rejected for security reasons: {filter_item}")
                    return None
        
        await self._ensure_session()
        
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Getting access token for report data...")
            
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] Token is expired and no refresh token available")
                logger.warning("[ASYNC-SF-API] No authentication available - returning empty result")
                return None
            
            access_token, instance_url = auth_info
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] Access token: {'Present' if access_token else 'Missing'}")
                logger.info(f"[ASYNC-SF-API] Instance URL: {instance_url}")
            
            if not access_token or not instance_url:
                logger.error("[ASYNC-SF-API] Missing access token or instance URL")
                return None
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Construct Analytics API endpoint URL
            api_endpoint = f"{instance_url}/services/data/v63.0/analytics/reports/{report_id}"
            
            # Run the report to get data
            run_endpoint = f"{api_endpoint}?includeDetails=true"
            
            if filters:
                # Apply filters if provided
                filter_payload = {
                    "reportMetadata": {
                        "reportFilters": []
                    }
                }
                
                for filter_item in filters:
                    column = filter_item.get('column')
                    operator = filter_item.get('operator', 'equals')
                    value = filter_item.get('value')
                    
                    if column and value:
                        sf_filter = {
                            "column": column,
                            "operator": operator,
                            "value": value
                        }
                        filter_payload["reportMetadata"]["reportFilters"].append(sf_filter)
                
                # Use POST with filters
                async with self.session.post(run_endpoint, headers=headers, json=filter_payload) as response:
                    if response.status != 200:
                        logger.error(f"[ASYNC-SF-API] Failed to run report: HTTP {response.status}")
                        return None
                    
                    report_data = await response.json()
            else:
                # Use GET without filters
                async with self.session.get(run_endpoint, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"[ASYNC-SF-API] Failed to run report: HTTP {response.status}")
                        return None
                    
                    report_data = await response.json()
            
            # Parse response and create DataFrame
            if not report_data:
                logger.error(f"[ASYNC-SF-API] No data returned for report {report_id}")
                return None
            
            # Extract records from the factMap and reportMetadata
            metadata = report_data.get('reportMetadata', {})
            detail_columns = metadata.get('detailColumns', [])
            
            if not detail_columns:
                logger.warning(f"[ASYNC-SF-API] No detail columns found in report {report_id}")
                return pl.DataFrame()
            
            # Get data from factMap
            fact_map = report_data.get('factMap', {})
            records = []
            
            # Extract records - typically in factMap['T!T']['rows'] - optimized processing
            if 'T!T' in fact_map and 'rows' in fact_map['T!T']:
                rows_data = fact_map['T!T']['rows']
                
                # Optimized record processing with list comprehension
                if essential_fields_only:
                    # Memory-efficient processing - only extract essential fields
                    essential_indices = [
                        i for i, col in enumerate(detail_columns) 
                        if col in essential_fields_only
                    ]
                    records = [
                        {
                            detail_columns[i]: cell.get('label', cell.get('value', ''))
                            for i, cell in enumerate(row.get('dataCells', []))
                            if i in essential_indices and i < len(detail_columns)
                        }
                        for row in rows_data
                        if row.get('dataCells')
                    ]
                else:
                    # Full record processing
                    records = [
                        {
                            detail_columns[i]: cell.get('label', cell.get('value', ''))
                            for i, cell in enumerate(row.get('dataCells', []))
                            if i < len(detail_columns)
                        }
                        for row in rows_data
                        if row.get('dataCells')  # Only process rows with data
                    ]
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] Retrieved {len(records)} records from report {report_id}")
            
            if not records:
                return pl.DataFrame()
            
            # Create Polars DataFrame
            df = pl.DataFrame(records)
            return df
            
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error retrieving report data for {report_id}: {e}")
            return None
    
    async def get_report_describe(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get report metadata including available fields and their types
        
        Args:
            report_id: Salesforce report ID
            
        Returns:
            Dictionary containing report metadata, or None if failed
        """
        # Validate report ID for security
        if not validate_report_id(report_id):
            logger.error(f"Invalid report ID rejected for security reasons: {report_id}")
            return None
        
        await self._ensure_session()
        
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-SF-API] Getting report metadata...")
            
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] Token is expired and no refresh token available")
                return None
            
            access_token, instance_url = auth_info
            
            if not access_token or not instance_url:
                logger.error("[ASYNC-SF-API] Missing access token or instance URL")
                return None
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            # Construct Analytics API describe endpoint URL
            describe_endpoint = f"{instance_url}/services/data/v63.0/analytics/reports/{report_id}/describe"
            
            # Fetch report metadata
            async with self.session.get(describe_endpoint, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-SF-API] Failed to get report metadata: HTTP {response.status} - {error_text}")
                    return None
                
                report_metadata = await response.json()
                
                if self.verbose_logging:
                    logger.info(f"[ASYNC-SF-API] Successfully retrieved report metadata for {report_id}")
                
                return report_metadata
                
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error getting report metadata: {e}")
            return None
    
    async def execute_soql(self, query: str, paginate: bool = False, max_records: int = 10000) -> Optional[pl.DataFrame]:
        """
        Execute SOQL query asynchronously
        
        Args:
            query: SOQL query string
            paginate: Whether to automatically handle pagination for large result sets
            max_records: Maximum number of records to fetch when paginating
            
        Returns:
            Polars DataFrame with query results, or None if failed
        """
        # Validate SOQL query for security
        if not validate_soql_query(query):
            logger.error("Invalid SOQL query rejected for security reasons")
            return None
            
        await self._ensure_session()
        
        try:
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] Token is expired and no refresh token available")
                logger.warning("[ASYNC-SF-API] No authentication available - returning empty result")
                return None
            
            access_token, instance_url = auth_info
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            all_records = []
            next_records_url = None
            soql_url = f"{instance_url}/services/data/v63.0/query"
            params = {'q': query}
            
            # Execute initial query
            async with self.session.get(soql_url, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if not result or 'records' not in result:
                        logger.warning(f"[ASYNC-SF-API] No results found for query: {query}")
                        return pl.DataFrame()
                    
                    records = result['records']
                    if records:
                        all_records.extend(records)
                    
                    # Check if there are more records to fetch
                    next_records_url = result.get('nextRecordsUrl') if paginate else None
                    
                else:
                    logger.error(f"[ASYNC-SF-API] Failed to execute SOQL: HTTP {response.status}")
                    return None
            
            # Handle pagination if requested and more records available
            if paginate and next_records_url and len(all_records) < max_records:
                if self.verbose_logging:
                    logger.info(f"[ASYNC-SF-API] Paginating SOQL query, fetched {len(all_records)} records so far...")
                
                while next_records_url and len(all_records) < max_records:
                    # Construct full URL for next page
                    next_url = f"{instance_url}{next_records_url}"
                    
                    async with self.session.get(next_url, headers=headers) as response:
                        if response.status == 200:
                            result = await response.json()
                            
                            records = result.get('records', [])
                            if records:
                                # Limit records to not exceed max_records
                                remaining_slots = max_records - len(all_records)
                                all_records.extend(records[:remaining_slots])
                            
                            # Check for next page
                            next_records_url = result.get('nextRecordsUrl')
                            if len(all_records) >= max_records:
                                break
                                
                        else:
                            logger.error(f"[ASYNC-SF-API] Failed to fetch next page: HTTP {response.status}")
                            break
            
            if not all_records:
                return pl.DataFrame()
            
            # Convert to list of dictionaries (removing Salesforce metadata) - optimized
            clean_records = [
                {k: v for k, v in record.items() 
                 if k != 'attributes' and not isinstance(v, dict)}
                for record in all_records
            ]
            
            # Create DataFrame with fallback for schema inference issues
            try:
                df = pl.DataFrame(clean_records)
            except Exception as schema_error:
                # Fallback with extended schema inference for mixed types (e.g., date fields)
                logger.warning(f"[ASYNC-SF-API] Schema inference failed, retrying with extended inference: {schema_error}")
                df = pl.DataFrame(clean_records, infer_schema_length=None)
            if self.verbose_logging:
                logger.info(f"[ASYNC-SF-API] SOQL query returned {len(df)} rows{'(paginated)' if paginate and len(all_records) > 2000 else ''}")
            return df
        
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error executing SOQL query: {e}")
            return None
    
    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        Get list of available Salesforce dashboards
        
        Returns:
            List of dashboard dictionaries with metadata
        """
        await self._ensure_session()
        
        try:
            if not self.auth_manager.is_authenticated():
                logger.error("[ASYNC-SF-API] Not authenticated with Salesforce")
                return []
            
            # Get auth info
            auth_info = await self._get_auth_info()
            if not auth_info:
                logger.error("[ASYNC-SF-API] Could not get auth info for dashboards")
                return []
            
            instance_url = auth_info['instance_url']
            access_token = auth_info['access_token']
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Query for dashboards using Analytics API
            dashboards_url = f"{instance_url}/services/data/v63.0/analytics/dashboards"
            
            logger.info("[ASYNC-SF-API] Fetching dashboards...")
            
            async with self.session.get(dashboards_url, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    dashboards = []
                    if isinstance(result, dict) and 'dashboards' in result:
                        for dashboard in result['dashboards']:
                            dashboards.append({
                                'id': dashboard.get('id', ''),
                                'name': dashboard.get('name', ''),
                                'description': dashboard.get('description', ''),
                                'folder_name': dashboard.get('folderName', ''),
                                'type': 'dashboard'
                            })
                    
                    logger.info(f"[ASYNC-SF-API] Retrieved {len(dashboards)} dashboards")
                    return dashboards
                    
                elif response.status == 404:
                    # Analytics API might not be available
                    logger.warning("[ASYNC-SF-API] Analytics API not available, trying alternative approach")
                    
                    # Try SOQL query as fallback
                    soql = "SELECT Id, Title, Description, FolderName FROM Dashboard LIMIT 200"
                    dashboard_df = await self.execute_soql(soql)
                    
                    if dashboard_df is not None and len(dashboard_df) > 0:
                        dashboards = []
                        for row in dashboard_df.iter_rows(named=True):
                            dashboards.append({
                                'id': row.get('Id', ''),
                                'name': row.get('Title', ''),
                                'description': row.get('Description', ''),
                                'folder_name': row.get('FolderName', ''),
                                'type': 'dashboard'
                            })
                        
                        logger.info(f"[ASYNC-SF-API] Retrieved {len(dashboards)} dashboards via SOQL")
                        return dashboards
                    else:
                        logger.warning("[ASYNC-SF-API] No dashboards found via SOQL")
                        return []
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-SF-API] Error fetching dashboards: HTTP {response.status} - {error_text}")
                    return []
                    
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Exception fetching dashboards: {e}")
            return []
    
    async def get_all_objects(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of all available Salesforce objects
        
        Args:
            use_cache: Whether to use cached object list (default: True)
            
        Returns:
            List of object information dictionaries
        """
        await self._ensure_session()
        
        try:
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] No authentication available")
                return []
            
            access_token, instance_url = auth_info
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get all sobjects
            sobjects_url = f"{instance_url}/services/data/v63.0/sobjects"
            
            async with self.session.get(sobjects_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    objects = []
                    for obj in data.get('sobjects', []):
                        objects.append({
                            'name': obj.get('name'),
                            'label': obj.get('label'),
                            'labelPlural': obj.get('labelPlural'),
                            'custom': obj.get('custom', False),
                            'queryable': obj.get('queryable', False),
                            'searchable': obj.get('searchable', False),
                            'retrieveable': obj.get('retrieveable', False),
                            'createable': obj.get('createable', False),
                            'updateable': obj.get('updateable', False),
                            'deleteable': obj.get('deleteable', False),
                            'keyPrefix': obj.get('keyPrefix', ''),
                            'urls': obj.get('urls', {})
                        })
                    
                    if self.verbose_logging:
                        logger.info(f"[ASYNC-SF-API] Retrieved {len(objects)} objects")
                    
                    return objects
                else:
                    logger.error(f"[ASYNC-SF-API] Failed to get objects: HTTP {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error retrieving objects: {e}")
            return []
    
    async def describe_object(self, object_name: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get detailed description of a Salesforce object including all fields
        
        Args:
            object_name: API name of the object (e.g., 'Account', 'CustomObject__c')
            use_cache: Whether to use cached description (default: True)
            
        Returns:
            Object description dictionary with fields, relationships, etc.
        """
        await self._ensure_session()
        
        try:
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] No authentication available")
                return None
            
            access_token, instance_url = auth_info
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Describe specific object
            describe_url = f"{instance_url}/services/data/v63.0/sobjects/{object_name}/describe"
            
            async with self.session.get(describe_url, headers=headers) as response:
                if response.status == 200:
                    description = await response.json()
                    
                    # Process fields for easier consumption
                    fields = []
                    for field in description.get('fields', []):
                        fields.append({
                            'name': field.get('name'),
                            'label': field.get('label'),
                            'type': field.get('type'),
                            'length': field.get('length'),
                            'precision': field.get('precision'),
                            'scale': field.get('scale'),
                            'custom': field.get('custom', False),
                            'nillable': field.get('nillable', True),
                            'createable': field.get('createable', False),
                            'updateable': field.get('updateable', False),
                            'filterable': field.get('filterable', False),
                            'sortable': field.get('sortable', False),
                            'groupable': field.get('groupable', False),
                            'unique': field.get('unique', False),
                            'relationshipName': field.get('relationshipName'),
                            'referenceTo': field.get('referenceTo', []),
                            'picklistValues': field.get('picklistValues', [])
                        })
                    
                    result = {
                        'name': description.get('name'),
                        'label': description.get('label'),
                        'labelPlural': description.get('labelPlural'),
                        'custom': description.get('custom', False),
                        'fields': fields,
                        'recordTypeInfos': description.get('recordTypeInfos', []),
                        'childRelationships': description.get('childRelationships', []),
                        'urls': description.get('urls', {})
                    }
                    
                    if self.verbose_logging:
                        logger.info(f"[ASYNC-SF-API] Retrieved description for {object_name} with {len(fields)} fields")
                    
                    return result
                else:
                    logger.error(f"[ASYNC-SF-API] Failed to describe object {object_name}: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error describing object {object_name}: {e}")
            return None
    
    async def get_global_describe(self, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get global describe information for all objects (more efficient than get_all_objects)
        
        Args:
            use_cache: Whether to use cached global describe (default: True)
            
        Returns:
            Global describe dictionary with all object metadata
        """
        await self._ensure_session()
        
        try:
            # Use cached auth info for better performance
            auth_info = self._get_cached_auth_info()
            if auth_info is None:
                logger.warning("[ASYNC-SF-API] No authentication available")
                return None
            
            access_token, instance_url = auth_info
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Global describe endpoint
            describe_url = f"{instance_url}/services/data/v63.0/sobjects/describe"
            
            async with self.session.get(describe_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if self.verbose_logging:
                        logger.info(f"[ASYNC-SF-API] Retrieved global describe with {len(data.get('sobjects', []))} objects")
                    
                    return data
                else:
                    logger.error(f"[ASYNC-SF-API] Failed to get global describe: HTTP {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-SF-API] Error getting global describe: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from Salesforce and clear session"""
        if self.session and not self.session.closed:
            # We can't await here, so we'll just close sync
            # The session will be cleaned up by the event loop
            pass
        
        # Clear cached auth info
        self._clear_auth_cache()
        self.auth_manager.clear_credentials()
        
        if self.verbose_logging:
            logger.info("[ASYNC-SF-API] Disconnected from Salesforce")