"""
Production-ready Async WooCommerce API implementation using aiohttp
High-performance alternative to the current requests-based implementation
"""
import asyncio
import aiohttp
import base64
import logging
import os
from typing import Dict, List, Optional, Any
import polars as pl

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass  # dotenv not available, use system environment variables

logger = logging.getLogger(__name__)

def _format_currency_amount(amount_cents, currency='USD'):
    """
    Convert currency amount from cents to dollars with proper decimal formatting
    
    Args:
        amount_cents: Amount in cents (e.g., 4660 for $46.60)
        currency: Currency code (default: USD)
        
    Returns:
        Float value in dollars (e.g., 46.60)
    """
    if amount_cents is None:
        return 0.0
    
    try:
        # Convert from cents to dollars
        amount_dollars = float(amount_cents) / 100.0
        return round(amount_dollars, 2)
    except (TypeError, ValueError):
        return 0.0

class AsyncWooCommerceAPI:
    """
    High-performance async WooCommerce API client using aiohttp
    Handles all WooCommerce API operations with Basic authentication
    """
    
    # Secure credential management - use environment variables  
    CONSUMER_KEY = os.getenv('WOO_CONSUMER_KEY')
    CONSUMER_SECRET = os.getenv('WOO_CONSUMER_SECRET')
    STORE_URL = os.getenv('WOO_STORE_URL', 'https://shop.company.com')
    
    def __init__(self, store_url: str = None, verbose_logging: bool = False):
        """
        Initialize Async WooCommerce API client
        
        Args:
            store_url: WooCommerce store URL (defaults to production URL)
            verbose_logging: Enable detailed logging for debugging (default: False for production)
        """
        self.store_url = store_url or self.STORE_URL
        self.api_base_url = f"{self.store_url}/wp-json/wc/v3"
        self.session: Optional[aiohttp.ClientSession] = None
        self.verbose_logging = verbose_logging
        
        # Create basic auth header
        auth_string = f"{self.CONSUMER_KEY}:{self.CONSUMER_SECRET}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0',
            'Accept': 'application/json'
        }
        
        # Optimized connection pool settings for WooCommerce API performance
        self.connector_config = {
            'limit': 50,  # Reduced total pool size for single-host usage
            'limit_per_host': 20,  # Optimized for WooCommerce server
            'ttl_dns_cache': 600,  # Longer DNS cache for stable endpoints
            'use_dns_cache': True,
            'keepalive_timeout': 60,  # Longer keepalive for session reuse
            'enable_cleanup_closed': True,
            'force_close': False,  # Reuse connections when possible
            'ssl': True,  # Enable SSL verification for security
        }
    
    async def _ensure_session(self):
        """Ensure we have an active aiohttp session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(**self.connector_config)
            # Optimized timeouts for API responsiveness
            timeout = aiohttp.ClientTimeout(total=60, connect=5, sock_read=30)
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self.headers
            )
    
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    def has_credentials(self) -> bool:
        """Check if API credentials are configured"""
        return bool(self.CONSUMER_KEY and self.CONSUMER_SECRET)
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the WooCommerce API connection asynchronously
        
        Returns:
            Dict with connection status and performance metrics
        """
        await self._ensure_session()
        
        try:
            # Test with a simple products query
            test_url = f"{self.api_base_url}/products"
            params = {'per_page': 1}
            
            start_time = asyncio.get_event_loop().time()
            
            async with self.session.get(test_url, params=params) as response:
                end_time = asyncio.get_event_loop().time()
                response_time = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'response_time': response_time,
                        'products_found': len(data),
                        'api_url': self.api_base_url,
                        'details': f'Connection successful. Found {len(data)} products.'
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'error': f'HTTP {response.status}',
                        'response_time': response_time,
                        'details': error_text
                    }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'response_time': 0,
                'details': 'Connection test failed'
            }
    
    async def get_payments_by_page(self, page: int = 1, per_page: int = 100, essential_fields_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get payments from a specific page (optimized for iterative matching)
        
        Args:
            page: Page number to fetch (1-based)
            per_page: Number of payments per page (max 100)
            essential_fields_only: Return only payment_id and fees for memory efficiency
            
        Returns:
            List of payment dictionaries for the requested page
        """
        await self._ensure_session()
        
        try:
            # WooPayments endpoint for all transactions (no date filtering)
            if self.verbose_logging:
                logger.info(f"[ASYNC-WOO-API] Getting WooPayments transactions (page {page}, {per_page} per page)")
            
            payments_url = f"{self.api_base_url}/payments/reports/transactions"
            
            # No date filtering - get specific page
            params = {
                'per_page': min(per_page, 100),  # API limit of 100
                'page': page
            }
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-WOO-API] WooPayments params: {params}")
            
            async with self.session.get(payments_url, params=params) as response:
                if response.status == 200:
                    # Optimized JSON processing - direct data extraction
                    response_data = await response.json()
                    
                    # Handle WooPayments response structure efficiently
                    payments = response_data.get('data', response_data) if isinstance(response_data, dict) else response_data
                    
                    # Return empty list if no data (avoid additional checks)
                    if not payments:
                        return []
                    
                    if self.verbose_logging:
                        logger.info(f"[ASYNC-WOO-API] Retrieved {len(payments)} payments from page {page}")
                    
                    # Return only essential fields for memory efficiency if requested
                    if essential_fields_only:
                        return [{'payment_id': p.get('payment_id', ''), 
                                'fees': _format_currency_amount(p.get('fees', 0), p.get('currency', 'USD'))} 
                               for p in payments if p.get('payment_id')]
                    
                    return payments
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-API] Failed to get payments page {page}: HTTP {response.status}: {error_text[:300]}")
                    return []
        
        except Exception as e:
            logger.error(f"[ASYNC-WOO-API] Error getting payments page {page}: {e}")
            return []
    
    async def get_payments_concurrent_pages(self, start_page: int = 1, num_pages: int = 3, per_page: int = 100, essential_fields_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get multiple pages of payments concurrently for improved performance
        
        Args:
            start_page: Starting page number (1-based)
            num_pages: Number of pages to fetch concurrently
            per_page: Number of payments per page (max 100)
            essential_fields_only: Return only payment_id and fees for memory efficiency
            
        Returns:
            Combined list of payment dictionaries from all pages
        """
        await self._ensure_session()
        
        try:
            # Create concurrent tasks for multiple pages
            tasks = []
            for i in range(num_pages):
                page = start_page + i
                task = self.get_payments_by_page(page=page, per_page=per_page, essential_fields_only=essential_fields_only)
                tasks.append(task)
            
            # Execute all page requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine all successful results
            all_payments = []
            for result in results:
                if isinstance(result, list):
                    all_payments.extend(result)
                elif isinstance(result, Exception):
                    if self.verbose_logging:
                        logger.warning(f"[ASYNC-WOO-API] Concurrent page fetch failed: {result}")
            
            if self.verbose_logging:
                logger.info(f"[ASYNC-WOO-API] Retrieved {len(all_payments)} payments from {num_pages} concurrent pages")
            
            return all_payments
            
        except Exception as e:
            logger.error(f"[ASYNC-WOO-API] Error in concurrent page fetching: {e}")
            return []
    
    async def get_data_sources(self) -> List[Dict[str, Any]]:
        """
        Get available WooCommerce data sources
        
        Returns:
            List of available data sources with metadata
        """
        # Return the same data sources as the sync API
        return [
            {
                'id': 'products',
                'name': 'Products',
                'description': 'All products in your WooCommerce store',
                'type': 'products',
                'icon': 'fa5s.box',
                'modified': ''
            },
            {
                'id': 'orders',
                'name': 'Orders',
                'description': 'Customer orders and transactions',
                'type': 'orders',
                'icon': 'fa5s.shopping-cart',
                'modified': ''
            },
            {
                'id': 'customers',
                'name': 'Customers',
                'description': 'Customer accounts and information',
                'type': 'customers',
                'icon': 'fa5s.users',
                'modified': ''
            },
            {
                'id': 'transactions',
                'name': 'Payment Transactions',
                'description': 'WooPayments transaction data with fees',
                'type': 'transactions',
                'icon': 'fa5s.credit-card',
                'modified': ''
            },
            {
                'id': 'transaction_fees',
                'name': 'Transaction Fees Summary',
                'description': 'Payment processing fees and costs',
                'type': 'transaction_fees',
                'icon': 'fa5s.money-bill-wave',
                'modified': ''
            }
        ]
    
    async def get_products(self, per_page: int = 100, page: int = 1) -> Optional[pl.DataFrame]:
        """
        Get products from WooCommerce asynchronously
        
        Args:
            per_page: Number of products per page (max 100)
            page: Page number to retrieve
            
        Returns:
            Polars DataFrame with product data, or None if failed
        """
        await self._ensure_session()
        
        try:
            url = f"{self.api_base_url}/products"
            params = {
                'per_page': min(per_page, 100),
                'page': page
            }
            
            logger.info(f"[ASYNC-WOO-PRODUCTS] Fetching page {page} with {per_page} items per page")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    products = await response.json()
                    
                    if not products:
                        logger.info("[ASYNC-WOO-PRODUCTS] No products found")
                        return pl.DataFrame()
                    
                    # Convert to DataFrame
                    df = pl.DataFrame(products)
                    logger.info(f"[ASYNC-WOO-PRODUCTS] Retrieved {len(df)} products")
                    
                    return df
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-PRODUCTS] Error: HTTP {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-WOO-PRODUCTS] Exception: {e}")
            return None
    
    async def get_orders(self, per_page: int = 100, page: int = 1, status: str = 'any') -> Optional[pl.DataFrame]:
        """
        Get orders from WooCommerce asynchronously
        
        Args:
            per_page: Number of orders per page (max 100)
            page: Page number to retrieve
            status: Order status filter (default: 'any')
            
        Returns:
            Polars DataFrame with order data, or None if failed
        """
        await self._ensure_session()
        
        try:
            url = f"{self.api_base_url}/orders"
            params = {
                'per_page': min(per_page, 100),
                'page': page,
                'status': status
            }
            
            logger.info(f"[ASYNC-WOO-ORDERS] Fetching page {page} with status '{status}'")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    orders = await response.json()
                    
                    if not orders:
                        logger.info("[ASYNC-WOO-ORDERS] No orders found")
                        return pl.DataFrame()
                    
                    # Convert to DataFrame
                    df = pl.DataFrame(orders)
                    logger.info(f"[ASYNC-WOO-ORDERS] Retrieved {len(df)} orders")
                    
                    return df
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-ORDERS] Error: HTTP {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-WOO-ORDERS] Exception: {e}")
            return None
    
    async def get_customers(self, per_page: int = 100, page: int = 1) -> Optional[pl.DataFrame]:
        """
        Get customers from WooCommerce asynchronously
        
        Args:
            per_page: Number of customers per page (max 100)
            page: Page number to retrieve
            
        Returns:
            Polars DataFrame with customer data, or None if failed
        """
        await self._ensure_session()
        
        try:
            url = f"{self.api_base_url}/customers"
            params = {
                'per_page': min(per_page, 100),
                'page': page
            }
            
            logger.info(f"[ASYNC-WOO-CUSTOMERS] Fetching page {page}")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    customers = await response.json()
                    
                    if not customers:
                        logger.info("[ASYNC-WOO-CUSTOMERS] No customers found")
                        return pl.DataFrame()
                    
                    # Convert to DataFrame
                    df = pl.DataFrame(customers)
                    logger.info(f"[ASYNC-WOO-CUSTOMERS] Retrieved {len(df)} customers")
                    
                    return df
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-CUSTOMERS] Error: HTTP {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-WOO-CUSTOMERS] Exception: {e}")
            return None
    
    async def get_transactions(self, per_page: int = 100, page: int = 1, date_after: str = None, 
                             date_before: str = None, fetch_order_numbers: bool = True) -> Optional[pl.DataFrame]:
        """
        Get payment transactions from WooCommerce asynchronously
        
        Args:
            per_page: Number of transactions per page (max 100)
            page: Page number to retrieve
            date_after: Start date filter (YYYY-MM-DD format)
            date_before: End date filter (YYYY-MM-DD format)
            fetch_order_numbers: Whether to fetch order numbers for transactions
            
        Returns:
            Polars DataFrame with transaction data, or None if failed
        """
        await self._ensure_session()
        
        try:
            # Try WooPayments endpoint first
            url = f"{self.api_base_url}/payments/reports/transactions"
            params = {
                'per_page': min(per_page, 100),
                'page': page
            }
            
            # Add date filters
            if date_after:
                params['date_after'] = f"{date_after} 00:00:00" if ' ' not in date_after else date_after
            if date_before:
                params['date_before'] = f"{date_before} 23:59:59" if ' ' not in date_before else date_before
            
            logger.info(f"[ASYNC-WOO-TRANSACTIONS] Trying WooPayments endpoint with params: {params}")
            
            async with self.session.get(url, params=params) as response:
                if response.status in [404, 400]:
                    # WooPayments not available, try orders endpoint
                    logger.warning(f"[ASYNC-WOO-TRANSACTIONS] WooPayments endpoint failed (HTTP {response.status})")
                    return await self._get_transactions_from_orders(per_page, page, date_after, date_before)
                    
                elif response.status == 200:
                    transactions = await response.json()
                    
                    # Handle different response structures
                    if isinstance(transactions, dict):
                        transaction_data = transactions.get('data', transactions)
                    else:
                        transaction_data = transactions
                    
                    if not transaction_data:
                        logger.info("[ASYNC-WOO-TRANSACTIONS] No transactions found")
                        return pl.DataFrame()
                    
                    # Convert to DataFrame
                    df = pl.DataFrame(transaction_data)
                    logger.info(f"[ASYNC-WOO-TRANSACTIONS] Retrieved {len(df)} transactions")
                    
                    # Note: Order number fetching not implemented in async version yet
                    
                    return df
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-TRANSACTIONS] Error: HTTP {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-WOO-TRANSACTIONS] Exception: {e}")
            return None
    
    async def _get_transactions_from_orders(self, per_page: int, page: int, 
                                          date_after: str = None, date_before: str = None) -> Optional[pl.DataFrame]:
        """
        Fallback method to get transactions from orders endpoint
        """
        try:
            url = f"{self.api_base_url}/orders"
            params = {
                'per_page': min(per_page, 100),
                'page': page
            }
            
            # Orders API uses ISO format with T separator
            if date_after:
                params['after'] = f"{date_after}T00:00:00" if 'T' not in date_after else date_after
            if date_before:
                params['before'] = f"{date_before}T23:59:59" if 'T' not in date_before else date_before
            
            logger.info(f"[ASYNC-WOO-TRANSACTIONS] Trying orders endpoint as fallback with params: {params}")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    orders = await response.json()
                    
                    if not orders:
                        return pl.DataFrame()
                    
                    # Convert orders to transaction format
                    transaction_data = []
                    for order in orders:
                        fees = 0.0
                        if 'fee_lines' in order and order['fee_lines']:
                            for fee_line in order['fee_lines']:
                                fees += float(fee_line.get('total', 0))
                        
                        transaction_record = {
                            'transaction_id': f"order_{order.get('id', '')}",
                            'payment_id': order.get('transaction_id', ''),
                            'order_id': order.get('id', ''),
                            'date': order.get('date_created', ''),
                            'type': 'sale',
                            'amount': float(order.get('total', 0)),
                            'fees': fees,
                            'net': float(order.get('total', 0)) - fees,
                            'currency': order.get('currency', 'USD'),
                            'status': order.get('status', ''),
                            'source': 'orders_endpoint'
                        }
                        transaction_data.append(transaction_record)
                    
                    df = pl.DataFrame(transaction_data)
                    logger.info(f"[ASYNC-WOO-TRANSACTIONS] Converted {len(df)} orders to transaction format")
                    return df
                else:
                    error_text = await response.text()
                    logger.error(f"[ASYNC-WOO-TRANSACTIONS] Orders endpoint also failed: {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"[ASYNC-WOO-TRANSACTIONS] Exception in orders fallback: {e}")
            return None
    
    
    async def get_all_transactions(self, date_after: str = None, date_before: str = None, 
                                 fetch_order_numbers: bool = True, use_parallel: bool = True) -> Optional[pl.DataFrame]:
        """
        Get all transactions across all pages asynchronously
        
        Args:
            date_after: Start date filter (YYYY-MM-DD format)
            date_before: End date filter (YYYY-MM-DD format)
            fetch_order_numbers: Whether to fetch order numbers for transactions
            use_parallel: Whether to use parallel fetching for multiple pages
            
        Returns:
            Combined Polars DataFrame with all transaction data, or None if failed
        """
        try:
            # First, get the first page to check total pages
            first_page = await self.get_transactions(100, 1, date_after, date_before, fetch_order_numbers)
            
            if first_page is None:
                return None
            
            if len(first_page) == 0:
                logger.info("[ASYNC-WOO-ALL-TRANSACTIONS] No transactions found")
                return first_page
            
            # For now, just return the first page
            # TODO: Implement pagination logic with headers to get total pages
            logger.info(f"[ASYNC-WOO-ALL-TRANSACTIONS] Retrieved {len(first_page)} transactions from first page")
            
            # In the future, implement parallel page fetching if needed
            # This would involve checking response headers for X-WP-TotalPages
            
            return first_page
            
        except Exception as e:
            logger.error(f"[ASYNC-WOO-ALL-TRANSACTIONS] Exception: {e}")
            return None
    
    async def get_payment_fees_vectorized(self, payment_ids: List[str], date_after: str = None, 
                                        date_before: str = None) -> Optional[pl.DataFrame]:
        """
        Vectorized lookup of payment fees for multiple payment IDs
        
        Args:
            payment_ids: List of payment IDs to lookup (e.g., ['pi_xxx', 'pi_yyy'])
            date_after: Start date filter to narrow search (YYYY-MM-DD format)
            date_before: End date filter to narrow search (YYYY-MM-DD format)
            
        Returns:
            Polars DataFrame with payment_id and fees columns, or None if failed
        """
        try:
            if not payment_ids:
                logger.warning("[ASYNC-WOO-VECTORIZED] No payment IDs provided")
                return pl.DataFrame(schema={'payment_id': pl.Utf8, 'fees': pl.Float64})
            
            # Filter for only payment IDs that start with 'pi_' to optimize
            valid_payment_ids = [pid for pid in payment_ids if str(pid).startswith('pi_')]
            
            if not valid_payment_ids:
                logger.info("[ASYNC-WOO-VECTORIZED] No valid Stripe payment IDs found")
                return pl.DataFrame(schema={'payment_id': pl.Utf8, 'fees': pl.Float64})
            
            logger.info(f"[ASYNC-WOO-VECTORIZED] Fetching fees for {len(valid_payment_ids)} payment IDs")
            
            # Get all transactions for the date range
            all_transactions_df = await self.get_all_transactions(
                date_after=date_after,
                date_before=date_before,
                fetch_order_numbers=False,
                use_parallel=True
            )
            
            if all_transactions_df is None or len(all_transactions_df) == 0:
                logger.warning("[ASYNC-WOO-VECTORIZED] No transactions found for date range")
                return pl.DataFrame(schema={'payment_id': pl.Utf8, 'fees': pl.Float64})
            
            # Filter transactions for the requested payment IDs using vectorized operations
            payment_ids_set = set(valid_payment_ids)
            
            # Use Polars filtering for high performance
            matching_transactions = all_transactions_df.filter(
                pl.col('payment_id').is_in(payment_ids_set) &
                (pl.col('fees') > 0)  # Only include transactions with actual fees
            ).select(['payment_id', 'fees'])
            
            logger.info(f"[ASYNC-WOO-VECTORIZED] Found {len(matching_transactions)} matching transactions with fees")
            
            # Remove duplicates, keeping the highest fee for each payment_id
            if len(matching_transactions) > 0:
                fee_df = matching_transactions.group_by('payment_id').agg(
                    pl.col('fees').max().alias('fees')
                )
                logger.info(f"[ASYNC-WOO-VECTORIZED] Deduplicated to {len(fee_df)} unique payment IDs")
                return fee_df
            else:
                return pl.DataFrame(schema={'payment_id': pl.Utf8, 'fees': pl.Float64})
                
        except Exception as e:
            logger.error(f"[ASYNC-WOO-VECTORIZED] Exception: {e}")
            return None
    
    async def create_payment_fees_cache(self, payment_ids: List[str], date_after: str = None, 
                                      date_before: str = None) -> Dict[str, float]:
        """
        Create a cache dictionary of payment fees for quick lookups
        
        Args:
            payment_ids: List of payment IDs to lookup
            date_after: Start date filter
            date_before: End date filter
            
        Returns:
            Dictionary mapping payment_id to fees amount
        """
        try:
            # Get fees DataFrame
            fees_df = await self.get_payment_fees_vectorized(payment_ids, date_after, date_before)
            
            if fees_df is None or len(fees_df) == 0:
                return {}
            
            # Convert to dictionary
            fee_dict = {}
            for row in fees_df.iter_rows(named=True):
                fee_dict[row['payment_id']] = row['fees']
            
            logger.info(f"[ASYNC-WOO-CACHE] Created fee cache with {len(fee_dict)} entries")
            return fee_dict
            
        except Exception as e:
            logger.error(f"[ASYNC-WOO-CACHE] Exception creating fee cache: {e}")
            return {}
    
    async def get_transaction_fees_summary(self, date_after: str = None, date_before: str = None) -> Optional[pl.DataFrame]:
        """
        Get a summary of transaction fees grouped by payment method
        
        Args:
            date_after: Start date filter (YYYY-MM-DD format)
            date_before: End date filter (YYYY-MM-DD format)
            
        Returns:
            Polars DataFrame with fee summary by payment method, or None if failed
        """
        try:
            # Get all transactions
            transactions_df = await self.get_all_transactions(date_after, date_before, fetch_order_numbers=False)
            
            if transactions_df is None or len(transactions_df) == 0:
                logger.warning("[ASYNC-WOO-FEE-SUMMARY] No transactions found")
                return pl.DataFrame()
            
            # Group by payment type/method if available, otherwise create summary
            if 'type' in transactions_df.columns:
                summary_df = transactions_df.group_by('type').agg([
                    pl.count().alias('transaction_count'),
                    pl.col('amount').sum().alias('total_amount'),
                    pl.col('fees').sum().alias('total_fees'),
                    pl.col('net').sum().alias('total_net')
                ])
            else:
                # Create a single summary row
                summary_df = pl.DataFrame({
                    'payment_method': ['All Transactions'],
                    'transaction_count': [len(transactions_df)],
                    'total_amount': [transactions_df['amount'].sum()],
                    'total_fees': [transactions_df['fees'].sum()],
                    'total_net': [transactions_df.get_column('net').sum() if 'net' in transactions_df.columns 
                                else transactions_df['amount'].sum() - transactions_df['fees'].sum()]
                })
            
            logger.info(f"[ASYNC-WOO-FEE-SUMMARY] Created fee summary with {len(summary_df)} payment methods")
            return summary_df
            
        except Exception as e:
            logger.error(f"[ASYNC-WOO-FEE-SUMMARY] Exception: {e}")
            return None
    
    async def get_data_source_data(self, source_id: str, start_date: str = None, end_date: str = None, use_date_filtering: bool = False) -> Optional[pl.DataFrame]:
        """
        Get data for a specific data source
        
        Args:
            source_id: ID of the data source to retrieve
            start_date: Optional start date filter (YYYY-MM-DD format) - only used if use_date_filtering=True
            end_date: Optional end date filter (YYYY-MM-DD format) - only used if use_date_filtering=True
            use_date_filtering: Whether to apply date filtering at API level (default: False for initial loads)
            
        Returns:
            Polars DataFrame with data (limited to 1000 results), or None if failed
        """
        logger.info(f"[ASYNC-WOO-DATA] Loading data for source: {source_id} (max 1000 results)")
        if use_date_filtering and start_date and end_date:
            logger.info(f"[ASYNC-WOO-DATA] API-level date filtering: {start_date} to {end_date}")
        
        if source_id == 'products':
            return await self.get_products(per_page=100, page=1)  # Limit to first 100
        elif source_id == 'orders':
            return await self.get_orders(per_page=100, page=1)  # Limit to first 100
        elif source_id == 'customers':
            return await self.get_customers(per_page=100, page=1)  # Limit to first 100
        elif source_id == 'transactions':
            # For transactions, apply date filtering only if requested
            if use_date_filtering:
                return await self.get_all_transactions(date_after=start_date, date_before=end_date)
            else:
                return await self.get_all_transactions()  # No date filtering, limited internally
        elif source_id == 'transaction_fees':
            # For fees summary, apply date filtering only if requested
            if use_date_filtering:
                return await self.get_transaction_fees_summary(date_after=start_date, date_before=end_date)
            else:
                return await self.get_transaction_fees_summary()  # No date filtering
        elif source_id == 'orders_pending':
            return await self.get_orders(per_page=100, page=1, status='pending')
        elif source_id == 'orders_completed':
            return await self.get_orders(per_page=100, page=1, status='completed')
        else:
            logger.error(f"[ASYNC-WOO-DATA] Unknown data source: {source_id}")
            return None
    
    def disconnect(self):
        """Disconnect from WooCommerce API and clear session"""
        if self.session and not self.session.closed:
            # We can't await here, so we'll just close sync
            # The session will be cleaned up by the event loop
            pass
        
        logger.info("[ASYNC-WOO-API] Disconnected from WooCommerce API")