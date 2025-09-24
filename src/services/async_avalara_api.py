"""
Production-ready Async Avalara API implementation using aiohttp
High-performance integration with Avalara REST API v2
"""
import asyncio
import aiohttp
import base64
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import polars as pl
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass  # dotenv not available, use system environment variables

logger = logging.getLogger(__name__)

class AsyncAvalaraAPI:
    """
    High-performance async Avalara API client using aiohttp
    Implements Avalara REST API v2 with efficient connection management
    """
    
    # Secure credential management - use environment variables
    ACCOUNT_ID = os.getenv('AVALARA_ACCOUNT_ID')
    LICENSE_KEY = os.getenv('AVALARA_LICENSE_KEY')
    ENVIRONMENT = os.getenv('AVALARA_ENVIRONMENT')
    
    def __init__(self, account_id: str = None, license_key: str = None, environment: str = None, verbose_logging: bool = False):
        """
        Initialize Async Avalara API client
        
        Args:
            account_id: Avalara account ID (defaults to env var)
            license_key: Avalara license key (defaults to env var)
            environment: Environment (sandbox/production, defaults to env var)
            verbose_logging: Enable detailed logging for debugging (default: False for production)
        """
        self.account_id = account_id or self.ACCOUNT_ID
        self.license_key = license_key or self.LICENSE_KEY
        self.environment = environment or self.ENVIRONMENT or 'sandbox'
        self.verbose_logging = verbose_logging
        
        # Validate required credentials
        if not self.account_id or not self.license_key:
            raise ValueError("Missing required Avalara credentials. Please set AVALARA_ACCOUNT_ID and AVALARA_LICENSE_KEY environment variables.")
        
        # Validate environment
        if self.environment.lower() not in ['sandbox', 'production']:
            logger.warning(f"[ASYNC-AVALARA-API] Invalid environment '{self.environment}', defaulting to sandbox")
            self.environment = 'sandbox'
        
        # Determine API base URL
        if self.environment.lower() == 'production':
            self.base_url = "https://rest.avatax.com"
        else:
            self.base_url = "https://sandbox-rest.avatax.com"
            
        self.api_version = "v2"
        self.api_base_url = f"{self.base_url}/api/{self.api_version}"
        
        # Create basic auth header
        auth_string = f"{self.account_id}:{self.license_key}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0',
            'X-Avalara-Client': 'SalesForceReportPull;1.0;AsyncAPI;1.0'
        }
        
        # Optimized connection pool settings for Avalara API
        self.connector_config = {
            'limit': 30,  # Reduced for single API host
            'limit_per_host': 20,  # Respect Avalara rate limits
            'ttl_dns_cache': 600,  # Longer DNS cache for stable endpoints
            'use_dns_cache': True,
            'keepalive_timeout': 60,  # Longer keepalive for session reuse
            'enable_cleanup_closed': True,
            'force_close': False,  # Reuse connections when possible
            'ssl': True,  # Enable SSL verification for security
        }
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limit_remaining = 1000  # Avalara default rate limit
        self._rate_limit_reset = datetime.now() + timedelta(minutes=1)
        
        if self.verbose_logging:
            logger.info(f"[ASYNC-AVALARA-API] Initialized for {self.environment} environment")
            logger.info(f"[ASYNC-AVALARA-API] Base URL: {self.base_url}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(**self.connector_config)
            # Optimized timeouts for API responsiveness
            timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            if self.verbose_logging:
                logger.info("[ASYNC-AVALARA-API] Session closed")
    
    async def _check_rate_limit(self):
        """Check and handle rate limiting"""
        now = datetime.now()
        if now > self._rate_limit_reset:
            self._rate_limit_remaining = 1000  # Reset rate limit
            self._rate_limit_reset = now + timedelta(minutes=1)
        
        if self._rate_limit_remaining <= 10:  # Conservative threshold
            sleep_time = (self._rate_limit_reset - now).total_seconds()
            if sleep_time > 0:
                if self.verbose_logging:
                    logger.warning(f"[ASYNC-AVALARA-API] Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
    
    async def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an authenticated request to Avalara API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            
        Returns:
            API response as dictionary
        """
        await self._ensure_session()
        await self._check_rate_limit()
        
        url = f"{self.api_base_url}/{endpoint.lstrip('/')}"
        
        if self.verbose_logging:
            logger.info(f"[ASYNC-AVALARA-API] {method} {url}")
            if params:
                logger.info(f"[ASYNC-AVALARA-API] Params: {params}")
        
        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data if data else None
            ) as response:
                # Update rate limit info from headers
                if 'X-Rate-Limit-Remaining' in response.headers:
                    self._rate_limit_remaining = int(response.headers['X-Rate-Limit-Remaining'])
                if 'X-Rate-Limit-Reset' in response.headers:
                    reset_timestamp = int(response.headers['X-Rate-Limit-Reset'])
                    self._rate_limit_reset = datetime.fromtimestamp(reset_timestamp)
                
                response_text = await response.text()
                
                if self.verbose_logging:
                    logger.info(f"[ASYNC-AVALARA-API] Status: {response.status}")
                    logger.info(f"[ASYNC-AVALARA-API] Rate limit remaining: {self._rate_limit_remaining}")
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"[ASYNC-AVALARA-API] JSON decode error: {e}")
                        return {"error": "Invalid JSON response", "raw_response": response_text}
                
                elif response.status == 401:
                    logger.error(f"[ASYNC-AVALARA-API] Authentication failed - Check account ID and license key")
                    logger.error(f"[ASYNC-AVALARA-API] Using Account ID: {self.account_id}")
                    logger.error(f"[ASYNC-AVALARA-API] Using Environment: {self.environment}")
                    logger.error(f"[ASYNC-AVALARA-API] Full response: {response_text}")
                    return {"error": "Authentication failed - Check account ID and license key", "status": 401, "details": response_text}
                
                elif response.status == 429:
                    logger.warning(f"[ASYNC-AVALARA-API] Rate limit exceeded")
                    return {"error": "Rate limit exceeded", "status": 429}
                
                else:
                    logger.error(f"[ASYNC-AVALARA-API] HTTP {response.status}: {response_text}")
                    return {"error": f"HTTP {response.status}", "details": response_text}
                    
        except aiohttp.ClientError as e:
            logger.error(f"[ASYNC-AVALARA-API] Request error: {e}")
            return {"error": "Network error", "details": str(e)}
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Unexpected error: {e}")
            return {"error": "Unexpected error", "details": str(e)}
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Avalara API
        
        Returns:
            Dictionary with connection test results
        """
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-AVALARA-API] Testing connection...")
            
            # Test with a simple API call to get account info
            result = await self._make_request('GET', '/utilities/ping')
            
            if "error" in result:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'details': result.get('details', 'Connection test failed')
                }
            
            # Also test authentication with account info
            account_result = await self._make_request('GET', '/accounts')
            
            if "error" in account_result:
                return {
                    'success': False,
                    'error': account_result.get('error', 'Authentication failed'),
                    'details': account_result.get('details', 'Could not retrieve account information')
                }
            
            # Extract account information
            accounts = account_result.get('value', [])
            account_info = "No accounts found"
            if accounts:
                account_info = f"Connected to {len(accounts)} account(s)"
                if len(accounts) > 0:
                    first_account = accounts[0]
                    account_name = first_account.get('name', 'Unknown')
                    account_info += f" - Primary: {account_name}"
            
            return {
                'success': True,
                'message': 'Connection successful',
                'account_info': account_info,
                'environment': self.environment,
                'rate_limit_remaining': self._rate_limit_remaining
            }
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Connection test failed: {e}")
            return {
                'success': False,
                'error': 'Connection test failed',
                'details': str(e)
            }
    
    async def get_companies(self) -> List[Dict[str, Any]]:
        """
        Get list of companies from Avalara
        
        Returns:
            List of company dictionaries
        """
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-AVALARA-API] Fetching companies...")
            
            result = await self._make_request('GET', '/companies')
            
            if "error" in result:
                logger.error(f"[ASYNC-AVALARA-API] Error fetching companies: {result}")
                return []
            
            companies = result.get('value', [])
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(companies)} companies")
            
            return companies
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error fetching companies: {e}")
            return []
    
    async def get_transactions(self, start_date: str, end_date: str, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get transactions for a date range using official Avalara API format
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            company_id: Optional company code to filter by
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Validate date format
            if not start_date or not end_date:
                raise ValueError("Both start_date and end_date are required")
            
            # Validate date format (basic check)
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError as e:
                raise ValueError(f"Invalid date format. Use YYYY-MM-DD. Error: {e}")
            
            # Validate date range
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if start_dt > end_dt:
                raise ValueError("start_date cannot be after end_date")
            
            # Check if date range is reasonable (not more than 1 year)
            if (end_dt - start_dt).days > 365:
                logger.warning(f"[ASYNC-AVALARA-API] Large date range requested: {(end_dt - start_dt).days} days. Consider smaller ranges for better performance.")
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Fetching transactions from {start_date} to {end_date}")
            
            # If no company_id provided, get the first company
            if not company_id:
                logger.info("[ASYNC-AVALARA-API] No company_id provided, fetching companies first")
                companies = await self.get_companies()
                if not companies:
                    logger.error("[ASYNC-AVALARA-API] No companies found, cannot fetch transactions")
                    return []
                # Use companyCode for transactions endpoint
                company_id = companies[0].get('companyCode')
                if not company_id:
                    # Fallback to id if companyCode not available
                    company_id = companies[0].get('id')
                logger.info(f"[ASYNC-AVALARA-API] Using company identifier: {company_id}")
            
            # Use official Avalara API format with required $filter parameter
            # Format: $filter=date between 'YYYY-MM-DD' and 'YYYY-MM-DD'
            date_filter = f"date between '{start_date}' and '{end_date}'"
            
            params = {
                '$filter': date_filter,
                '$top': 1000,  # API max is 1000 records per request
                '$orderby': 'date desc'  # Order by date descending for latest first
            }
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Using filter: {date_filter}")
                logger.info(f"[ASYNC-AVALARA-API] Company identifier: {company_id}")
            
            # Use correct Avalara API endpoint: /companies/{companyCode}/transactions
            endpoint = f'/companies/{company_id}/transactions'
            result = await self._make_request('GET', endpoint, params=params)
            
            if "error" in result:
                logger.error(f"[ASYNC-AVALARA-API] Error fetching transactions: {result}")
                # If we got a 404, try with numeric company ID instead
                if result.get('status') == 404 and not str(company_id).isdigit():
                    logger.info(f"[ASYNC-AVALARA-API] Retrying with numeric company ID...")
                    companies = await self.get_companies()
                    if companies:
                        numeric_id = companies[0].get('id')
                        if numeric_id and str(numeric_id).isdigit():
                            endpoint = f'/companies/{numeric_id}/transactions'
                            result = await self._make_request('GET', endpoint, params=params)
                            if "error" not in result:
                                transactions = result.get('value', [])
                                if self.verbose_logging:
                                    logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(transactions)} transactions using numeric ID")
                                return transactions
                return []
            
            transactions = result.get('value', [])
            logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(transactions)} transactions")
            
            if transactions:
                if self.verbose_logging:
                    logger.info(f"[ASYNC-AVALARA-API] Sample transaction keys: {list(transactions[0].keys())}")
                    # Log first transaction for debugging
                    logger.info(f"[ASYNC-AVALARA-API] Sample transaction data: {transactions[0]}")
            else:
                logger.info(f"[ASYNC-AVALARA-API] No transactions found for date range {start_date} to {end_date}")
                logger.info(f"[ASYNC-AVALARA-API] This might be normal if no transactions occurred in this period")
            
            return transactions
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error fetching transactions: {e}")
            return []
    
    async def get_tax_codes(self) -> List[Dict[str, Any]]:
        """
        Get available tax codes
        
        Returns:
            List of tax code dictionaries
        """
        try:
            if self.verbose_logging:
                logger.info("[ASYNC-AVALARA-API] Fetching tax codes...")
            
            result = await self._make_request('GET', '/definitions/taxcodes')
            
            if "error" in result:
                logger.error(f"[ASYNC-AVALARA-API] Error fetching tax codes: {result}")
                return []
            
            tax_codes = result.get('value', [])
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(tax_codes)} tax codes")
            
            return tax_codes
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error fetching tax codes: {e}")
            return []
    
    async def get_jurisdictions(self, country: str = "US") -> List[Dict[str, Any]]:
        """
        Get jurisdictions for a country
        
        Args:
            country: Country code (default: US)
            
        Returns:
            List of jurisdiction dictionaries
        """
        try:
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Fetching jurisdictions for {country}...")
            
            params = {
                'country': country,
                '$top': 500  # Limit results
            }
            
            result = await self._make_request('GET', '/definitions/jurisdictions', params=params)
            
            if "error" in result:
                logger.error(f"[ASYNC-AVALARA-API] Error fetching jurisdictions: {result}")
                return []
            
            jurisdictions = result.get('value', [])
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(jurisdictions)} jurisdictions")
            
            return jurisdictions
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error fetching jurisdictions: {e}")
            return []
    
    async def get_reports(self, start_date: str, end_date: str, company_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available reports for a date range
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            company_id: Optional company ID to filter by
            
        Returns:
            List of available report types
        """
        try:
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Fetching reports from {start_date} to {end_date}")
            
            params = {
                'startDate': start_date,
                'endDate': end_date
            }
            
            if company_id:
                params['companyId'] = company_id
            
            result = await self._make_request('GET', '/reports', params=params)
            
            if "error" in result:
                logger.error(f"[ASYNC-AVALARA-API] Error fetching reports: {result}")
                return []
            
            reports = result.get('value', [])
            if self.verbose_logging:
                logger.info(f"[ASYNC-AVALARA-API] Retrieved {len(reports)} reports")
            
            return reports
            
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error fetching reports: {e}")
            return []
    
    def to_dataframe(self, data: List[Dict[str, Any]], data_type: str = "generic") -> pl.DataFrame:
        """
        Convert API response data to Polars DataFrame
        
        Args:
            data: List of dictionaries from API response
            data_type: Type of data for optimized column handling
            
        Returns:
            Polars DataFrame
        """
        logger.info(f"[ASYNC-AVALARA-API] Converting {len(data) if data else 0} {data_type} records to DataFrame")
        
        if not data:
            logger.info(f"[ASYNC-AVALARA-API] No data to convert, returning empty DataFrame")
            return pl.DataFrame()
        
        try:
            # Handle different data types with optimized schemas
            if data_type == "transactions":
                logger.info(f"[ASYNC-AVALARA-API] Processing transaction data with columns: {list(data[0].keys()) if data else 'None'}")
                
                # Optimize for transaction data
                df = pl.DataFrame(data)
                logger.info(f"[ASYNC-AVALARA-API] Created DataFrame with shape: {df.shape}")
                
                # Ensure numeric columns are properly typed
                numeric_columns = ['totalAmount', 'totalTax', 'totalTaxable', 'totalExempt']
                for col in numeric_columns:
                    if col in df.columns:
                        df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False))
                        logger.info(f"[ASYNC-AVALARA-API] Converted column {col} to Float64")
                
                logger.info(f"[ASYNC-AVALARA-API] Final transaction DataFrame: {df.shape[0]} rows, {df.shape[1]} columns")
                return df
            
            elif data_type == "companies":
                logger.info(f"[ASYNC-AVALARA-API] Processing company data")
                
                # Optimize for company data
                df = pl.DataFrame(data)
                # Ensure date columns are properly typed
                date_columns = ['createdDate', 'modifiedDate']
                for col in date_columns:
                    if col in df.columns:
                        df = df.with_columns(pl.col(col).str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S", strict=False))
                return df
            
            else:
                # Generic handling
                logger.info(f"[ASYNC-AVALARA-API] Processing generic data type: {data_type}")
                return pl.DataFrame(data)
                
        except Exception as e:
            logger.error(f"[ASYNC-AVALARA-API] Error converting to DataFrame: {e}")
            logger.error(f"[ASYNC-AVALARA-API] Data sample: {data[0] if data else 'No data'}")
            # Fallback to basic DataFrame creation
            try:
                basic_df = pl.DataFrame(data)
                logger.info(f"[ASYNC-AVALARA-API] Fallback DataFrame created with shape: {basic_df.shape}")
                return basic_df
            except Exception as e2:
                logger.error(f"[ASYNC-AVALARA-API] Fallback DataFrame creation failed: {e2}")
                return pl.DataFrame()