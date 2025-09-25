"""
Async JWT Salesforce API implementation using JWT Bearer Flow authentication.
Server-to-server authentication using RSA certificates without browser interaction.
"""

import asyncio
import aiohttp
import logging
import re
import os
from typing import Dict, List, Optional, Any
import polars as pl
from datetime import datetime, timedelta
from urllib.parse import urljoin
from pathlib import Path

from ..utils.jwt_utils import generate_jwt_token

logger = logging.getLogger(__name__)

# Security validation functions (kept from original implementation)
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


class AsyncJWTSalesforceAPI:
    """
    High-performance async Salesforce API client using JWT Bearer Flow authentication.
    Handles all Salesforce API operations with JWT server-to-server authentication.
    """

    def __init__(self, instance_url: str = "https://login.salesforce.com",
                 consumer_key: Optional[str] = None, jwt_subject: Optional[str] = None,
                 jwt_key_path: Optional[str] = None, jwt_key_id: Optional[str] = None,
                 sandbox: bool = False, verbose_logging: bool = False):
        """
        Initialize Async JWT Salesforce API client

        Args:
            instance_url: Salesforce login URL
            consumer_key: Consumer key for JWT (Connected App consumer key)
            jwt_subject: JWT subject (typically username/email)
            jwt_key_path: Path to private key file for JWT signing
            jwt_key_id: Optional key ID for the certificate
            sandbox: Whether to use sandbox environment
            verbose_logging: Enable detailed logging for debugging
        """
        self.verbose_logging = verbose_logging

        # JWT configuration from parameters or environment
        self.consumer_key = consumer_key or os.getenv('SF_CLIENT_ID')
        self.jwt_subject = jwt_subject or os.getenv('SF_JWT_SUBJECT')
        self.jwt_key_path = jwt_key_path or os.getenv('SF_JWT_KEY_PATH')
        self.jwt_key_id = jwt_key_id or os.getenv('SF_JWT_KEY_ID')

        # Set login URL based on environment
        if sandbox or "test.salesforce.com" in instance_url:
            self.login_url = "https://test.salesforce.com"
        else:
            self.login_url = "https://login.salesforce.com"

        self.instance_url = instance_url
        self.session: Optional[aiohttp.ClientSession] = None

        # Authentication state
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._authenticated = False

        # Optimized connection pool settings for Salesforce API
        self.connector_config = {
            'limit': 50,
            'limit_per_host': 20,
            'ttl_dns_cache': 600,
            'use_dns_cache': True,
            'keepalive_timeout': 90,
            'enable_cleanup_closed': True,
            'force_close': False,
        }

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
                    logger.warning(f"[ASYNC-JWT-SF-API] Error closing old session: {e}")

            # Create new session for current event loop
            connector = aiohttp.TCPConnector(**self.connector_config)
            timeout = aiohttp.ClientTimeout(total=90, connect=10, sock_read=60)

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'SalesForceReportPull-JWTAsyncAPI/1.0',
                    'Accept': 'application/json'
                }
            )

            if self.verbose_logging:
                logger.info(f"[ASYNC-JWT-SF-API] Created new session for event loop: {id(current_loop)}")

    def _generate_jwt_assertion(self) -> Optional[str]:
        """Generate JWT assertion for Salesforce authentication"""
        try:
            return generate_jwt_token(
                issuer=self.consumer_key,
                subject=self.jwt_subject,
                audience=self.login_url,
                private_key_path=self.jwt_key_path,
                key_id=self.jwt_key_id,
                lifetime_minutes=3  # JWT assertion should be short-lived
            )
        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Failed to generate JWT assertion: {e}")
            return None

    async def _exchange_jwt_for_token(self, jwt_assertion: str) -> Optional[Dict[str, Any]]:
        """Exchange JWT assertion for Salesforce access token"""
        try:
            token_endpoint = f"{self.login_url}/services/oauth2/token"

            # Prepare the request data
            data = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': jwt_assertion
            }

            if self.verbose_logging:
                logger.debug(f"[ASYNC-JWT-SF-API] Exchanging JWT assertion at: {token_endpoint}")

            # Make the token exchange request with proper form encoding
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            async with self.session.post(token_endpoint, data=data, headers=headers) as response:
                if response.status != 200:
                    error_detail = await response.text()
                    logger.error(f"[ASYNC-JWT-SF-API] JWT token exchange failed: {response.status} - {error_detail}")

                    # Provide specific error guidance
                    if "invalid_grant" in error_detail.lower():
                        logger.error("[ASYNC-JWT-SF-API] JWT assertion invalid - check certificate, key, and Connected App configuration")
                    elif "oauth_flow_disabled" in error_detail.lower():
                        logger.error("[ASYNC-JWT-SF-API] OAuth flow disabled in Connected App - JWT authentication should not require OAuth")

                    return None

                token_data = await response.json()
                if self.verbose_logging:
                    logger.debug(f"[ASYNC-JWT-SF-API] Token exchange successful, received: {list(token_data.keys())}")

                return token_data

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Failed to exchange JWT for access token: {e}")
            return None

    async def authenticate(self) -> bool:
        """
        Authenticate with Salesforce using JWT Bearer Flow

        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            await self._ensure_session()

            # Check if all required JWT parameters are available
            required_params = [self.consumer_key, self.jwt_subject, self.jwt_key_path]

            if not all(required_params):
                logger.error("[ASYNC-JWT-SF-API] JWT configuration incomplete - missing required parameters")
                logger.error(f"[ASYNC-JWT-SF-API] Consumer Key: {'Present' if self.consumer_key else 'Missing'}")
                logger.error(f"[ASYNC-JWT-SF-API] JWT Subject: {'Present' if self.jwt_subject else 'Missing'}")
                logger.error(f"[ASYNC-JWT-SF-API] JWT Key Path: {'Present' if self.jwt_key_path else 'Missing'}")
                return False

            if self.verbose_logging:
                logger.debug(f"[ASYNC-JWT-SF-API] Starting JWT authentication for user: {self.jwt_subject}")

            # Step 1: Generate JWT assertion
            jwt_token = self._generate_jwt_assertion()
            if not jwt_token:
                logger.error("[ASYNC-JWT-SF-API] Failed to generate JWT assertion")
                return False

            # Step 2: Exchange JWT for access token
            access_token_data = await self._exchange_jwt_for_token(jwt_token)
            if not access_token_data:
                logger.error("[ASYNC-JWT-SF-API] Failed to exchange JWT for access token")
                return False

            # Step 3: Store authentication data
            self.access_token = access_token_data.get('access_token')
            self.instance_url = access_token_data.get('instance_url')

            # Calculate token expiration (typically 1 hour)
            expires_in = access_token_data.get('expires_in', 3600)  # Default 1 hour
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

            self._authenticated = True
            logger.info(f"[ASYNC-JWT-SF-API] Successfully authenticated with Salesforce using JWT Bearer Flow")
            if self.verbose_logging:
                logger.debug(f"[ASYNC-JWT-SF-API] Instance URL: {self.instance_url}")

            return True

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] JWT authentication failed: {e}")
            return False

    def is_authenticated(self) -> bool:
        """Check if currently authenticated and token is valid"""
        if not self._authenticated or not self.access_token:
            return False

        # Check if token has expired
        if self.token_expires_at and datetime.utcnow() >= self.token_expires_at:
            if self.verbose_logging:
                logger.info("[ASYNC-JWT-SF-API] Access token has expired")
            self._authenticated = False
            return False

        return True

    def has_credentials(self) -> bool:
        """Check if JWT credentials are available for authentication"""
        return all([self.consumer_key, self.jwt_subject, self.jwt_key_path])

    async def connect_with_browser(self, parent_widget=None) -> bool:
        """
        Connect to Salesforce (JWT doesn't require browser, this method maintains compatibility)

        Args:
            parent_widget: Parent widget (unused but kept for compatibility)

        Returns:
            bool: True if connection successful, False otherwise
        """
        logger.info("[ASYNC-JWT-SF-API] Starting Salesforce JWT authentication")

        try:
            # JWT authentication doesn't require browser
            auth_result = await self.authenticate()

            if not auth_result:
                logger.error("[ASYNC-JWT-SF-API] JWT authentication failed")
                return False

            logger.info("[ASYNC-JWT-SF-API] JWT authentication successful")

            # Test the connection
            logger.info("[ASYNC-JWT-SF-API] Testing connection after JWT authentication...")
            test_result = await self.test_connection()

            if test_result.get('success', False):
                logger.info("[ASYNC-JWT-SF-API] Connection test successful")
                return True
            else:
                logger.error(f"[ASYNC-JWT-SF-API] Connection test failed: {test_result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] JWT connection error: {e}")
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
                logger.info("[ASYNC-JWT-SF-API] Testing Salesforce connection...")

            # Authenticate if not already authenticated
            if not self.is_authenticated():
                logger.info("[ASYNC-JWT-SF-API] Not authenticated, attempting JWT authentication...")
                if not await self.authenticate():
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'details': 'Unable to authenticate with JWT'
                    }

            if not self.access_token or not self.instance_url:
                return {
                    'success': False,
                    'error': 'Authentication failed',
                    'details': 'Missing access token or instance URL'
                }

            # Test connection with organization query
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            test_url = f"{self.instance_url}/services/data/v63.0/query"
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
                        'instance_url': self.instance_url,
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
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot get reports")
                return []

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Query reports
            reports_query = """
                SELECT Id, Name, Description, FolderName, CreatedDate, LastModifiedDate,
                       Format, LastRunDate, OwnerId, Owner.Name
                FROM Report
                ORDER BY FolderName, Name
            """

            reports_url = f"{self.instance_url}/services/data/v63.0/query"
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
                        logger.info(f"[ASYNC-JWT-SF-API] Retrieved {len(reports)} reports")
                    return reports
                else:
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to get reports: HTTP {response.status}")
                    return []

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error retrieving reports: {e}")
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
            logger.error(f"[ASYNC-JWT-SF-API] Invalid report ID rejected for security reasons: {report_id}")
            return None

        # Validate filters if provided
        if filters:
            for filter_item in filters:
                column = filter_item.get('column', '')
                operator = filter_item.get('operator', '')
                value = filter_item.get('value', '')
                if not validate_filter_parameter(column, operator, value):
                    logger.error(f"[ASYNC-JWT-SF-API] Invalid filter parameter rejected for security reasons: {filter_item}")
                    return None

        await self._ensure_session()

        try:
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot get report data")
                return None

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Construct Analytics API endpoint URL
            api_endpoint = f"{self.instance_url}/services/data/v63.0/analytics/reports/{report_id}"

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
                        logger.error(f"[ASYNC-JWT-SF-API] Failed to run report: HTTP {response.status}")
                        return None

                    report_data = await response.json()
            else:
                # Use GET without filters
                async with self.session.get(run_endpoint, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"[ASYNC-JWT-SF-API] Failed to run report: HTTP {response.status}")
                        return None

                    report_data = await response.json()

            # Parse response and create DataFrame
            if not report_data:
                logger.error(f"[ASYNC-JWT-SF-API] No data returned for report {report_id}")
                return None

            # Extract records from the factMap and reportMetadata
            metadata = report_data.get('reportMetadata', {})
            detail_columns = metadata.get('detailColumns', [])

            if not detail_columns:
                logger.warning(f"[ASYNC-JWT-SF-API] No detail columns found in report {report_id}")
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
                logger.info(f"[ASYNC-JWT-SF-API] Retrieved {len(records)} records from report {report_id}")

            if not records:
                return pl.DataFrame()

            # Create Polars DataFrame
            df = pl.DataFrame(records)
            return df

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error retrieving report data for {report_id}: {e}")
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
            logger.error("[ASYNC-JWT-SF-API] Invalid SOQL query rejected for security reasons")
            return None

        await self._ensure_session()

        try:
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot execute SOQL")
                return None

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            all_records = []
            next_records_url = None
            soql_url = f"{self.instance_url}/services/data/v63.0/query"
            params = {'q': query}

            # Execute initial query
            async with self.session.get(soql_url, headers=headers, params=params) as response:
                if response.status == 200:
                    result = await response.json()

                    if not result or 'records' not in result:
                        logger.warning(f"[ASYNC-JWT-SF-API] No results found for query: {query}")
                        return pl.DataFrame()

                    records = result['records']
                    if records:
                        all_records.extend(records)

                    # Check if there are more records to fetch
                    next_records_url = result.get('nextRecordsUrl') if paginate else None

                else:
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to execute SOQL: HTTP {response.status}")
                    return None

            # Handle pagination if requested and more records available
            if paginate and next_records_url and len(all_records) < max_records:
                if self.verbose_logging:
                    logger.info(f"[ASYNC-JWT-SF-API] Paginating SOQL query, fetched {len(all_records)} records so far...")

                while next_records_url and len(all_records) < max_records:
                    # Construct full URL for next page
                    next_url = f"{self.instance_url}{next_records_url}"

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
                            logger.error(f"[ASYNC-JWT-SF-API] Failed to fetch next page: HTTP {response.status}")
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
                logger.warning(f"[ASYNC-JWT-SF-API] Schema inference failed, retrying with extended inference: {schema_error}")
                df = pl.DataFrame(clean_records, infer_schema_length=None)

            if self.verbose_logging:
                logger.info(f"[ASYNC-JWT-SF-API] SOQL query returned {len(df)} rows{'(paginated)' if paginate and len(all_records) > 2000 else ''}")
            return df

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error executing SOQL query: {e}")
            return None

    async def get_dashboards(self) -> List[Dict[str, Any]]:
        """
        Get list of available Salesforce dashboards

        Returns:
            List of dashboard dictionaries with metadata
        """
        await self._ensure_session()

        try:
            if not self.is_authenticated():
                logger.error("[ASYNC-JWT-SF-API] Not authenticated with Salesforce")
                return []

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Query for dashboards using Analytics API
            dashboards_url = f"{self.instance_url}/services/data/v63.0/analytics/dashboards"

            logger.info("[ASYNC-JWT-SF-API] Fetching dashboards...")

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

                    logger.info(f"[ASYNC-JWT-SF-API] Retrieved {len(dashboards)} dashboards")
                    return dashboards

                elif response.status == 404:
                    # Analytics API might not be available
                    logger.warning("[ASYNC-JWT-SF-API] Analytics API not available, trying alternative approach")

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

                        logger.info(f"[ASYNC-JWT-SF-API] Retrieved {len(dashboards)} dashboards via SOQL")
                        return dashboards
                    else:
                        logger.warning("[ASYNC-JWT-SF-API] No dashboards found via SOQL")
                        return []
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-JWT-SF-API] Error fetching dashboards: HTTP {response.status} - {error_text}")
                    return []

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Exception fetching dashboards: {e}")
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
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot get objects")
                return []

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Get all sobjects
            sobjects_url = f"{self.instance_url}/services/data/v63.0/sobjects"

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
                        logger.info(f"[ASYNC-JWT-SF-API] Retrieved {len(objects)} objects")

                    return objects
                else:
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to get objects: HTTP {response.status}")
                    return []

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error retrieving objects: {e}")
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
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot describe object")
                return None

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Describe specific object
            describe_url = f"{self.instance_url}/services/data/v63.0/sobjects/{object_name}/describe"

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
                        logger.info(f"[ASYNC-JWT-SF-API] Retrieved description for {object_name} with {len(fields)} fields")

                    return result
                else:
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to describe object {object_name}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error describing object {object_name}: {e}")
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
            logger.error(f"[ASYNC-JWT-SF-API] Invalid report ID rejected for security reasons: {report_id}")
            return None

        await self._ensure_session()

        try:
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot get report metadata")
                return None

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            # Construct Analytics API describe endpoint URL
            describe_endpoint = f"{self.instance_url}/services/data/v63.0/analytics/reports/{report_id}/describe"

            # Fetch report metadata
            async with self.session.get(describe_endpoint, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to get report metadata: HTTP {response.status} - {error_text}")
                    return None

                report_metadata = await response.json()

                if self.verbose_logging:
                    logger.info(f"[ASYNC-JWT-SF-API] Successfully retrieved report metadata for {report_id}")

                return report_metadata

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error getting report metadata: {e}")
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
            if not self.is_authenticated():
                logger.warning("[ASYNC-JWT-SF-API] Not authenticated - cannot get global describe")
                return None

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            # Global describe endpoint
            describe_url = f"{self.instance_url}/services/data/v63.0/sobjects/describe"

            async with self.session.get(describe_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if self.verbose_logging:
                        logger.info(f"[ASYNC-JWT-SF-API] Retrieved global describe with {len(data.get('sobjects', []))} objects")

                    return data
                else:
                    logger.error(f"[ASYNC-JWT-SF-API] Failed to get global describe: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"[ASYNC-JWT-SF-API] Error getting global describe: {e}")
            return None

    def disconnect(self):
        """Disconnect from Salesforce and clear session"""
        self.access_token = None
        self.token_expires_at = None
        self._authenticated = False

        if self.verbose_logging:
            logger.info("[ASYNC-JWT-SF-API] Disconnected from Salesforce")

    async def close(self):
        """Close the aiohttp session safely"""
        if self.session and not self.session.closed:
            try:
                await self.session.close()
                if self.verbose_logging:
                    logger.info("[ASYNC-JWT-SF-API] Session closed successfully")
            except Exception as e:
                logger.warning(f"[ASYNC-JWT-SF-API] Error closing session: {e}")
            finally:
                self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()