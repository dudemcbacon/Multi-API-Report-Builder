"""
Sales Receipt Import Operation
Processes Salesforce sales receipts with WooCommerce fee matching
"""
import logging
from typing import Optional, Dict, Any, List, Tuple, Set
import polars as pl
from datetime import datetime
import re
import asyncio

from .base_operation import BaseOperation

logger = logging.getLogger(__name__)

# Compile regex patterns for better performance
CURRENCY_PATTERN = re.compile(r'[^\d.-]')
PARENTHESES_PATTERN = re.compile(r'^\((.+)\)$')

def _fast_clean_currency_core(value_str: str) -> float:
    """Fast currency cleaning (numba disabled for compatibility)"""
    if not value_str:
        return 0.0
    
    # Handle negative values in parentheses
    is_negative = False
    if value_str.startswith('(') and value_str.endswith(')'):
        is_negative = True
        value_str = value_str[1:-1]
    
    # Handle negative sign
    if value_str.startswith('-'):
        is_negative = True
        value_str = value_str[1:]
    
    # Remove common formatting using regex for better performance
    clean_str = CURRENCY_PATTERN.sub('', value_str)
    
    if not clean_str:
        return 0.0
    
    try:
        result = float(clean_str)
        return -result if is_negative else result
    except (ValueError, TypeError):
        return 0.0


class SalesReceiptImport(BaseOperation):
    """Sales Receipt Import operation implementation"""
    
    # Configuration (from JavaScript)
    CONFIG = {
        'TAX_STATES': ["Texas", "Colorado", "Georgia", "Nevada", "Virginia"],
        'TAX_STATE_MAPPINGS': {
            "Texas": "Texas",
            "Colorado": "CO Sales Tax",
            "Georgia": "GA Sales Tax",
            "Nevada": "NV Sales Tax",
            "Virginia": "VA Sales Tax"
        },
        'REMOVAL_SKUS': [
            "QBO", "FL-CX", "FCX", "FSI-CS", "QBH", "SWKACMRECCO",
            "INT-MS", "42643", "498415",
            "498422", "498014", "498414",
            "498108", "498080"
        ],
        'SPECIAL_SKUS': {
            'ADMIN_FEE': "ADMINFEE",
            'QBO_SPECIAL': "QBOSP"
        },
        'REMOVAL_PRODUCT_TYPES': ["QBES GNS", "QBES RENEWAL"],
        'ADMINFEE_SKU_MAPPINGS': {
            "QBES": "ENTERPRISE",
            "Hosting": "QBH-DS"
        },
        'SKU_REPLACEMENTS': {
            "REC": "FL-SVC-DEP"
        },
        'CHAR_LIMITS': {
            'ACCOUNT_NAME': 41,
            'ADDRESS': 41
        },
        'DEFAULT_CLASS': "02 - Sales",
        'CREDIT_ORDER_PATTERN': "RMA",
        'SALESFORCE_REPORT_ID': "00ORl000007JNmTMAW",
        'COLUMN_MAPPING': {
            # Map from expected field names to actual Salesforce field names
            'Account Name': 'ACCOUNT_NAME',
            'Date Paid': 'Order.Date_Paid__c',
            'Webstore Order #': 'Order.Webstore_Order__c',
            'Class': 'Order.Class__c',
            'Billing Address Line 1': 'ORDER_BILLING_LINE1',
            'Billing Address Line 2': 'ORDER_BILLING_LINE2',
            'Billing City': 'ORDER_BILLING_CITY',
            'Billing State/Province (text only)': 'ORDER_BILLING_STATE',
            'Billing Zip/Postal Code': 'ORDER_BILLING_ZIP',
            'Shipping Address Line 1': 'ORDER_SHIPPING_LINE1',
            'Shipping Address Line 2': 'ORDER_SHIPPING_LINE2',
            'Shipping City': 'ORDER_SHIPPING_CITY',
            'Shipping State/Province (text only)': 'ORDER_SHIPPING_STATE',
            'Shipping Country': 'ORDER_SHIPPING_COUNTRY_CODE',
            'Shipping Zip/Postal Code': 'ORDER_SHIPPING_ZIP',
            'Sales Tax (Reason)': 'Order.Sales_Tax__c',
            'Payment ID': 'Order.Payment_ID__c',
            'SKU': 'OrderItem.SKU__c',
            'Quantity': 'ORDER_ITEM_QUANTITY',
            'Unit Price': 'ORDER_ITEM_UNITPRICE',
            'Tax': 'Order.Tax__c',
            'Order Amount (Grand Total)': 'Order.Order_Amount_Grand_Total__c',
            'Product Type': 'OrderItem.Product_Type__c'
        }
    }
    
    def execute(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Execute the sales receipt import operation with async APIs"""
        try:
            # Run the async version in a new event loop
            return asyncio.run(self._execute_async(start_date, end_date))
        except Exception as e:
            logger.error(f"Sales Receipt Import error: {e}", exc_info=True)
            raise
    
    async def _execute_async(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Execute the sales receipt import operation with async APIs"""
        try:
            self.report_progress(0, "Starting Sales Receipt Import...")
            
            # Step 1: Fetch Salesforce data
            self.report_progress(10, "Fetching Salesforce report data...")
            sf_df = await self._fetch_salesforce_data_async(start_date, end_date)
            if sf_df is None or len(sf_df) == 0:
                self.report_progress(100, "No Salesforce data found for date range")
                return None
                
            # Step 2: Fetch WooCommerce data using vectorized approach
            self.report_progress(30, "Fetching WooCommerce fee data...")
            woo_fees_dict = await self._fetch_woocommerce_fees_vectorized_async(sf_df, start_date, end_date)
            
            # Step 3: Process and merge data
            self.report_progress(50, "Processing data and matching orders...")
            processed_df = self._process_data(sf_df, woo_fees_dict)
            
            # Step 4: Apply business rules using lazy evaluation
            self.report_progress(70, "Applying business rules and formatting...")
            main_df, credit_df, errors_df = self._apply_business_rules_lazy(processed_df)
            
            # Step 5: Normalize grand totals (must be done after all rows are added)
            self.report_progress(80, "Normalizing grand totals...")
            main_df = self._normalize_grand_totals(main_df)
            if credit_df is not None:
                credit_df = self._normalize_grand_totals(credit_df)
            
            # Step 6: Final formatting
            self.report_progress(90, "Finalizing data...")
            main_df = self._apply_final_formatting(main_df)
            if credit_df is not None:
                credit_df = self._apply_final_formatting(credit_df)
            
            self.report_progress(100, "Operation completed successfully")
            
            return {
                'main': main_df,
                'credit': credit_df,
                'errors': errors_df
            }
            
        except Exception as e:
            logger.error(f"Sales Receipt Import error: {e}", exc_info=True)
            raise
            
    async def _fetch_salesforce_data_async(self, start_date: str, end_date: str) -> Optional[pl.DataFrame]:
        """Fetch Salesforce report data with date filter using async API"""
        try:
            # Import async API
            from ...services.async_salesforce_api import AsyncSalesforceAPI
            
            # Get authentication details from the existing sf_api instance
            if not self.sf_api:
                logger.error("No Salesforce API instance available")
                return None
                
            # Get the auth manager from the existing API
            auth_manager = self.sf_api.auth_manager
            if not auth_manager:
                logger.error("No auth manager available from Salesforce API")
                return None
                
            # Create async API instance with existing auth manager and optimized settings
            # This ensures both APIs share the same authentication state
            async with AsyncSalesforceAPI(auth_manager=auth_manager, verbose_logging=False) as sf_api:
                # Try to apply server-side filtering first with the known date field
                logger.info(f"Attempting to filter Salesforce data by date range: {start_date} to {end_date}")
                
                # Use the actual Salesforce date field name we discovered
                try:
                    logger.info("Attempting to filter by 'Order.Date_Paid__c' field and exclude blank webstore orders...")
                    
                    # Use separate filters for start and end date (more compatible format)
                    # Also exclude blank/null/placeholder webstore order numbers
                    filters = [
                        {
                            'column': 'Order.Date_Paid__c',
                            'operator': 'greaterOrEqual',
                            'value': start_date
                        },
                        {
                            'column': 'Order.Date_Paid__c',
                            'operator': 'lessOrEqual', 
                            'value': end_date
                        },
                        {
                            'column': 'Order.Webstore_Order__c',
                            'operator': 'notEqual',
                            'value': ''
                        },
                        {
                            'column': 'Order.Webstore_Order__c',
                            'operator': 'notEqual',
                            'value': '-'
                        }
                    ]
                    
                    # Get the report data with date filtering
                    sf_df = await sf_api.get_report_data(
                        self.CONFIG['SALESFORCE_REPORT_ID'],
                        filters=filters
                    )
                    
                    if sf_df is not None and len(sf_df) > 0:
                        logger.info(f"Successfully filtered by date range: {len(sf_df)} rows")
                        # Normalize column names to match expected field names
                        sf_df = self._normalize_column_names(sf_df)
                        logger.info(f"Normalized columns: {sf_df.columns}")
                        return sf_df
                    else:
                        logger.warning("Date filtering returned no data")
                        
                except Exception as e:
                    logger.warning(f"Failed to filter by 'Order.Date_Paid__c': {e}")
                
                # Fallback: Load without filters and apply client-side filtering
                try:
                    logger.info("Falling back to loading without filters and applying client-side filtering...")
                    sf_df = await sf_api.get_report_data(
                        self.CONFIG['SALESFORCE_REPORT_ID'],
                        filters=None
                    )
                    
                    if sf_df is not None and len(sf_df) > 0:
                        logger.info(f"Retrieved {len(sf_df)} rows without filters")
                        logger.info(f"Available columns: {sf_df.columns}")
                        
                        # Normalize column names first
                        sf_df = self._normalize_column_names(sf_df)
                        logger.info(f"Normalized columns: {sf_df.columns}")
                        
                        # Apply client-side date filtering if date column exists
                        if 'Date Paid' in sf_df.columns:
                            logger.info("Applying client-side date and webstore order filtering...")
                            original_count = len(sf_df)
                            
                            # Convert date strings to datetime for comparison
                            import polars as pl
                            from datetime import datetime
                            
                            # Filter by date range and exclude blank webstore orders
                            date_filter = (pl.col('Date Paid') >= start_date) & (pl.col('Date Paid') <= end_date)
                            
                            # Add webstore order filter if column exists
                            if 'Webstore Order #' in sf_df.columns:
                                webstore_filter = (pl.col('Webstore Order #').is_not_null()) & (pl.col('Webstore Order #') != '') & (pl.col('Webstore Order #') != '-')
                                sf_df = sf_df.filter(date_filter & webstore_filter)
                                logger.info("Applied both date and webstore order filters")
                            else:
                                sf_df = sf_df.filter(date_filter)
                                logger.info("Applied date filter only (webstore order column not found)")
                            
                            filtered_count = len(sf_df)
                            logger.info(f"Client-side filtering: {original_count} -> {filtered_count} rows")
                        else:
                            logger.warning("No 'Date Paid' column found for client-side filtering")
                        
                        return sf_df
                        
                except Exception as e:
                    logger.warning(f"Failed to load report without filters: {e}")
                
                # All attempts failed
                logger.error("All attempts to load and filter Salesforce data failed")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching Salesforce data: {e}")
            raise
    
    def _normalize_column_names(self, df: pl.DataFrame) -> pl.DataFrame:
        """Normalize Salesforce column names to expected field names"""
        # Create reverse mapping from Salesforce field names to expected names
        reverse_mapping = {v: k for k, v in self.CONFIG['COLUMN_MAPPING'].items()}
        
        # Rename columns that exist in the mapping
        rename_dict = {}
        for col in df.columns:
            if col in reverse_mapping:
                rename_dict[col] = reverse_mapping[col]
                logger.info(f"Mapping column: {col} -> {reverse_mapping[col]}")
        
        if rename_dict:
            df = df.rename(rename_dict)
            logger.info(f"Renamed {len(rename_dict)} columns")
        else:
            logger.warning("No columns found in mapping - using original names")
            
        return df
    
    def _normalize_order_id(self, order_id: str) -> str:
        """Normalize order ID to handle different formats between systems"""
        if not order_id:
            return order_id
            
        # Convert to string and strip whitespace
        normalized = str(order_id).strip()
        
        # Remove common prefixes
        prefixes_to_remove = ['#', 'order_', 'ORDER_', 'wc_order_']
        for prefix in prefixes_to_remove:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove common suffixes
        suffixes_to_remove = ['_order', '_ORDER']
        for suffix in suffixes_to_remove:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break
        
        return normalized
            
    async def _fetch_woocommerce_fees_vectorized_async(self, sf_df: pl.DataFrame, start_date: str, end_date: str) -> Optional[Dict[str, float]]:
        """Fetch WooCommerce fee data using vectorized lookup for optimal performance with async API"""
        try:
            from ...services.async_woocommerce_api import AsyncWooCommerceAPI
            
            logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Starting vectorized WooCommerce fee lookup")
            
            # Create async API instance with optimized settings
            async with AsyncWooCommerceAPI(verbose_logging=False) as woo_api:
                # Test connection first
                logger.info("[FETCH-WOO-VECTORIZED-ASYNC] Testing WooCommerce connection...")
                try:
                    test_result = await woo_api.test_connection()
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Connection test result: {test_result}")
                    if not test_result.get('success'):
                        logger.error(f"[FETCH-WOO-VECTORIZED-ASYNC] Connection test failed: {test_result}")
                        return {}
                except Exception as e:
                    logger.error(f"[FETCH-WOO-VECTORIZED-ASYNC] Connection test error: {e}")
                    return {}
                
                # Extract payment IDs from Salesforce data that start with 'pi_'
                payment_ids = sf_df.filter(
                    pl.col('Payment ID').str.starts_with('pi_')
                ).select('Payment ID').to_series().to_list()
                
                if not payment_ids:
                    logger.info("[FETCH-WOO-VECTORIZED-ASYNC] No Stripe payment IDs found in Salesforce data")
                    return {}
                
                logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Found {len(payment_ids)} payment IDs to lookup")
                
                # Get WooCommerce payments data page by page until all Salesforce payment IDs are matched
                fees_cache = {}
                unmatched_payment_ids = set(payment_ids)
                
                logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Need to match {len(unmatched_payment_ids)} payment IDs")
                
                # Fetch page by page for optimal performance
                current_page = 1
                max_pages = 100  # Safety limit (10,000 payments total)
                per_page = 100   # WooCommerce API limit
                
                while unmatched_payment_ids and current_page <= max_pages:
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Fetching page {current_page} ({per_page} payments), {len(unmatched_payment_ids)} IDs still unmatched")
                    
                    # Get payments data from current page with memory optimization
                    payments_data = await woo_api.get_payments_by_page(page=current_page, per_page=per_page, essential_fields_only=True)
                    
                    if not payments_data:
                        logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] No payments data returned from page {current_page} - reached end")
                        break
                    
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Retrieved {len(payments_data)} payments from page {current_page}")
                    
                    # Process payments and look for matches
                    matches_found = 0
                    for payment in payments_data:
                        payment_id = payment.get('payment_id', '')
                        if payment_id and payment_id in unmatched_payment_ids:
                            # Extract fee amount from payment data structure
                            fee_amount = payment.get('fees', 0)
                            if fee_amount:
                                fees_cache[payment_id] = float(fee_amount)
                                unmatched_payment_ids.remove(payment_id)
                                matches_found += 1
                    
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Found {matches_found} matches on page {current_page}, {len(unmatched_payment_ids)} still unmatched")
                    
                    # If we found all matches, we can stop immediately
                    if not unmatched_payment_ids:
                        logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] All payment IDs matched after {current_page} pages!")
                        break
                    
                    # If we got fewer payments than requested per_page, we've reached the end
                    if len(payments_data) < per_page:
                        logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Reached end of payments data after {current_page} pages")
                        break
                    
                    # Move to next page
                    current_page += 1
                
                if unmatched_payment_ids:
                    logger.warning(f"[FETCH-WOO-VECTORIZED-ASYNC] Could not match {len(unmatched_payment_ids)} payment IDs: {list(unmatched_payment_ids)[:10]}...")  # Show first 10
                
                if fees_cache:
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Successfully created fees cache with {len(fees_cache)} entries")
                    
                    # Count non-zero fees for logging
                    non_zero_fees = sum(1 for fee in fees_cache.values() if fee > 0)
                    logger.info(f"[FETCH-WOO-VECTORIZED-ASYNC] Found {non_zero_fees} payment IDs with fees > 0")
                    
                    return fees_cache
                else:
                    logger.warning("[FETCH-WOO-VECTORIZED-ASYNC] Failed to create fees cache")
                    return {}
            
        except Exception as e:
            logger.error(f"[FETCH-WOO-VECTORIZED-ASYNC] Error in vectorized WooCommerce lookup: {e}", exc_info=True)
            return {}
    
    def _fetch_woocommerce_data(self, start_date: str, end_date: str) -> Optional[pl.DataFrame]:
        """Fetch WooCommerce transaction data"""
        try:
            logger.info(f"[FETCH-WOO] Starting WooCommerce data fetch")
            logger.info(f"[FETCH-WOO] WooCommerce API instance: {self.woo_api is not None}")
            
            if not self.woo_api:
                logger.error("[FETCH-WOO] No WooCommerce API instance available")
                return pl.DataFrame()
            
            # Test connection first
            logger.info("[FETCH-WOO] Testing WooCommerce connection...")
            try:
                test_result = self.woo_api.test_connection()
                logger.info(f"[FETCH-WOO] Connection test result: {test_result}")
                if not test_result.get('success'):
                    logger.error(f"[FETCH-WOO] Connection test failed: {test_result}")
                    return pl.DataFrame()
            except Exception as e:
                logger.error(f"[FETCH-WOO] Connection test error: {e}")
                return pl.DataFrame()
            
            # Fetch transactions with date filtering and pagination to get all available data
            logger.info(f"[FETCH-WOO] Fetching WooCommerce transactions for date range: {start_date} to {end_date}")
            woo_df = self.woo_api.get_all_transactions(
                #date_after=start_date,
                #date_before=end_date,
                fetch_order_numbers=False  # Use payment_id matching for 50% performance improvement
            )
            
            if woo_df is None:
                logger.warning("[FETCH-WOO] get_transactions returned None")
                return pl.DataFrame()  # Return empty DataFrame
            
            if len(woo_df) == 0:
                logger.warning("[FETCH-WOO] get_transactions returned empty DataFrame")
                return pl.DataFrame()
                
            logger.info(f"[FETCH-WOO] Successfully fetched {len(woo_df)} WooCommerce transactions")
            logger.info(f"[FETCH-WOO] WooCommerce DataFrame columns: {woo_df.columns}")
            
            # Log sample of fee data
            if 'fees' in woo_df.columns:
                fees_summary = woo_df.select(pl.col('fees')).describe()
                logger.info(f"[FETCH-WOO] Fees column summary: {fees_summary}")
                
                # Count orders with fees > 0
                with_fees = woo_df.filter(pl.col('fees') > 0)
                logger.info(f"[FETCH-WOO] Orders with fees > 0: {len(with_fees)} out of {len(woo_df)}")
            else:
                logger.warning("[FETCH-WOO] No 'fees' column found in WooCommerce data")
                
            return woo_df
            
        except Exception as e:
            logger.error(f"[FETCH-WOO] Error fetching WooCommerce data: {e}", exc_info=True)
            # Return empty DataFrame on error to continue processing
            return pl.DataFrame()
            
    def _process_data(self, sf_df: pl.DataFrame, woo_fees_dict: Optional[Dict[str, float]]) -> pl.DataFrame:
        """Process and merge Salesforce and WooCommerce data using vectorized lookup"""
        
        # First, normalize data types in the Salesforce DataFrame to ensure consistency
        sf_df_normalized = self._normalize_salesforce_data_types(sf_df)
        
        # Filter Salesforce data for orders with Payment IDs starting with 'pi_' using Polars
        sf_with_payments = sf_df_normalized.filter(
            pl.col('Payment ID').str.starts_with('pi_')
        )
        
        logger.info(f"[PROCESS-DATA] Filtered Salesforce data: {len(sf_with_payments)} orders with 'pi_' Payment IDs (from {len(sf_df_normalized)} total)")
        
        # Add all original Salesforce records to result
        result_df = sf_df_normalized.clone()
        
        # If we have WooCommerce fees data, create fee rows using vectorized lookup
        if woo_fees_dict and len(sf_with_payments) > 0:
            
            # Add fees column using vectorized lookup
            sf_with_fees = sf_with_payments.with_columns([
                pl.col('Payment ID').map_elements(
                    lambda pid: woo_fees_dict.get(pid, 0.0),
                    return_dtype=pl.Float64
                ).alias('woo_fees')
            ])
            
            # Filter for orders that actually have fees > 0
            matched_df = sf_with_fees.filter(pl.col('woo_fees') > 0)
            
            logger.info(f"[PROCESS-DATA] Successfully matched {len(matched_df)} orders with WooCommerce fees using vectorized lookup")
            
            if len(matched_df) > 0:
                # Get unique payment IDs to avoid duplicate fee rows per order group
                # Use the first record for each payment ID to create a single fee row per order
                unique_payment_fees = matched_df.group_by('Payment ID', maintain_order=True).first()
                
                # Ensure columns are in the same order as the original DataFrame
                unique_payment_fees = unique_payment_fees.select(matched_df.columns)
                
                logger.info(f"[PROCESS-DATA] Creating {len(unique_payment_fees)} unique fee rows (one per order group, reduced from {len(matched_df)} total items)")
                
                # Create fee rows using Polars operations with type matching to original data
                fee_rows = unique_payment_fees.with_columns([
                    pl.lit('WooCommerce Fees').alias('SKU'),
                    pl.lit(1).cast(pl.Int64).alias('Quantity'),  # Match normalized Quantity type
                    (-pl.col('woo_fees')).cast(pl.Float64).alias('Unit Price')  # Match normalized Unit Price type
                ]).drop('woo_fees')  # Remove the helper column
                
                # Align schemas and combine original data with fee rows
                result_df_aligned, fee_rows_aligned = self._align_dataframe_schemas(result_df, fee_rows)
                result_df = pl.concat([result_df_aligned, fee_rows_aligned], how="vertical")
                
                logger.info(f"[PROCESS-DATA] Added {len(fee_rows)} WooCommerce fee rows using vectorized approach")
                logger.info(f"[PROCESS-DATA] Total rows after adding fees: {len(result_df)}")
                
                # Log sample fee row for debugging
                if len(fee_rows_aligned) > 0:
                    sample_fee = fee_rows_aligned.head(1).to_dicts()[0]
                    logger.info(f"[PROCESS-DATA] Sample fee row: Order={sample_fee.get('Webstore Order #')}, SKU={sample_fee.get('SKU')}, Qty={sample_fee.get('Quantity')}, Price={sample_fee.get('Unit Price')}")
        
        # Check for any records without order numbers (should be none after API filtering)
        records_without_orders = sf_df_normalized.filter(
            (pl.col('Webstore Order #').is_null()) | 
            (pl.col('Webstore Order #') == '') |
            (pl.col('Webstore Order #') == '-')
        )
        
        if len(records_without_orders) > 0:
            logger.warning(f"[PROCESS-DATA] Found {len(records_without_orders)} records without order numbers (API filtering may have failed)")
        else:
            logger.info("[PROCESS-DATA] No records without order numbers found (API filtering successful)")
        
        return result_df
        
    def _apply_business_rules(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Optional[pl.DataFrame], Optional[pl.DataFrame]]:
        """Apply business rules from the JavaScript logic"""
        if len(df) == 0:
            return df, None, None
            
        # Step 1: Validate data and collect errors
        errors = self._validate_data(df)
        
        # Step 2: Filter rows based on removal criteria
        df = self._filter_rows(df)
        
        # Step 3: Apply transformations
        df = self._apply_transformations(df)
        
        # Step 4: Process tax rows
        df = self._process_tax_rows(df)
        
        # Step 5: Split credit orders
        main_df, credit_df = self._split_credit_orders(df)
        
        # Step 6: Make credit quantities and prices positive
        if credit_df is not None:
            credit_df = self._make_credits_positive(credit_df)
        
        # Create errors DataFrame
        errors_df = None
        if errors:
            errors_df = pl.DataFrame(errors)
            
        return main_df, credit_df, errors_df
    
    def _apply_business_rules_lazy(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Optional[pl.DataFrame], Optional[pl.DataFrame]]:
        """Apply business rules using lazy evaluation for better performance"""
        if len(df) == 0:
            return df, None, None
        
        # Convert to LazyFrame for lazy evaluation
        lazy_df = df.lazy()
        
        # Step 1-3: Chain operations using lazy evaluation
        processed_lazy = (
            lazy_df
            # Apply filtering
            .pipe(self._filter_rows_lazy)
            # Apply transformations
            .pipe(self._apply_transformations_lazy)
            # Add tax rows
            .pipe(self._process_tax_rows_lazy)
        )
        
        # Collect the lazy frame
        processed_df = processed_lazy.collect()
        
        # Step 4: Validate data AFTER processing (only validate final data that will be reported)
        errors = self._validate_data(processed_df)
        
        # Step 7: Split credit orders
        main_df, credit_df = self._split_credit_orders(processed_df)
        
        # Step 8: Make credit quantities and prices positive
        if credit_df is not None:
            credit_df = self._make_credits_positive(credit_df)
        
        # Create errors DataFrame
        errors_df = None
        if errors:
            errors_df = pl.DataFrame(errors)
            
        return main_df, credit_df, errors_df
    
    def _filter_rows_lazy(self, lazy_df: pl.LazyFrame) -> pl.LazyFrame:
        """Lazy version of filter_rows - returns LazyFrame for chaining"""
        # This would be implemented similar to _filter_rows but returning LazyFrame
        # For now, fall back to eager evaluation
        return lazy_df.collect().pipe(self._filter_rows).lazy()
    
    def _apply_transformations_lazy(self, lazy_df: pl.LazyFrame) -> pl.LazyFrame:
        """Lazy version of apply_transformations - returns LazyFrame for chaining"""
        # This would be implemented similar to _apply_transformations but returning LazyFrame
        # For now, fall back to eager evaluation
        return lazy_df.collect().pipe(self._apply_transformations).lazy()
    
    def _process_tax_rows_lazy(self, lazy_df: pl.LazyFrame) -> pl.LazyFrame:
        """Lazy version of process_tax_rows - returns LazyFrame for chaining"""
        # This would be implemented similar to _process_tax_rows but returning LazyFrame
        # For now, fall back to eager evaluation
        return lazy_df.collect().pipe(self._process_tax_rows).lazy()
        
    def _validate_data(self, df: pl.DataFrame) -> List[Dict[str, Any]]:
        """Validate data and return list of errors using vectorized operations"""
        errors = []
        
        if len(df) == 0:
            return errors
        
        # Vectorized validation using Polars expressions
        validation_df = df.with_columns([
            # Account name length check
            (pl.col('Account Name').str.len_chars() > self.CONFIG['CHAR_LIMITS']['ACCOUNT_NAME']).alias('account_name_too_long'),
            
            # US address check
            (pl.col('Shipping Country').str.to_lowercase() == 'united states').alias('is_us_address'),
            
            # Required fields check for US addresses
            pl.when(pl.col('Shipping Country').str.to_lowercase() == 'united states')
            .then(
                (pl.col('Billing Address Line 1').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Billing City').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Billing State/Province (text only)').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Billing Zip/Postal Code').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Shipping Address Line 1').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Shipping City').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Shipping State/Province (text only)').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Shipping Zip/Postal Code').str.strip_chars().str.len_chars() == 0)
            )
            .otherwise(False)
            .alias('missing_required_fields')
        ])
        
        # Check address fields length
        address_fields = [col for col in df.columns if 'Address' in col]
        for field in address_fields:
            validation_df = validation_df.with_columns([
                (pl.col(field).str.len_chars() > self.CONFIG['CHAR_LIMITS']['ADDRESS']).alias(f'{field}_too_long')
            ])
        
        # Filter rows with validation errors
        error_conditions = (pl.col('account_name_too_long')) | (pl.col('missing_required_fields'))
        for field in address_fields:
            error_conditions = error_conditions | (pl.col(f'{field}_too_long'))
        
        error_rows = validation_df.filter(error_conditions)
        
        # Convert to error list (only for rows with errors - much faster)
        for row in error_rows.iter_rows(named=True):
            row_errors = []
            
            # Check account name length
            if row.get('account_name_too_long', False):
                account_name = str(row.get('Account Name', ''))
                row_errors.append({
                    'field': 'Account Name',
                    'issue': f'Exceeded character limit ({len(account_name)} chars)'
                })
            
            # Check address fields
            for field in address_fields:
                if row.get(f'{field}_too_long', False):
                    value = str(row.get(field, ''))
                    row_errors.append({
                        'field': field,
                        'issue': f'Exceeded character limit ({len(value)} chars)'
                    })
            
            # Check required fields for US addresses
            if row.get('missing_required_fields', False):
                row_errors.append({
                    'field': 'US Address Fields',
                    'issue': 'Missing required field(s) for US address'
                })
            
            if row_errors:
                errors.append({
                    'Order #': row.get('Webstore Order #', ''),
                    'Account Name': str(row.get('Account Name', '')),
                    'Issues': '; '.join([f"{e['field']}: {e['issue']}" for e in row_errors])
                })
                
        return errors
        
    def _filter_rows(self, df: pl.DataFrame) -> pl.DataFrame:
        """Filter rows based on removal criteria using vectorized operations"""
        if len(df) == 0:
            return df
        
        # Identify ADMINFEE orders using vectorized operations
        admin_fee_orders = df.filter(
            pl.col('SKU').str.strip_chars().str.to_uppercase() == self.CONFIG['SPECIAL_SKUS']['ADMIN_FEE']
        ).select('Webstore Order #').unique().to_series().to_list()
        
        # Create filtering conditions using vectorized operations
        df_processed = df.with_columns([
            # Clean unit price for calculations
            pl.col('Unit Price').map_elements(
                lambda x: self._clean_currency(x),
                return_dtype=pl.Float64
            ).alias('_clean_unit_price'),
            
            # Check if order is ADMINFEE
            pl.col('Webstore Order #').is_in(admin_fee_orders).alias('_is_admin_fee'),
            
            # Check removal criteria
            (pl.col('Unit Price').map_elements(lambda x: self._clean_currency(x), return_dtype=pl.Float64) == 0).alias('_zero_price'),
            
            # Check product type removal
            pl.col('Product Type').str.contains('|'.join(self.CONFIG['REMOVAL_PRODUCT_TYPES'])).alias('_removal_product_type'),
            
            # Check SKU removal (with QBOSP exception)
            pl.when(
                pl.col('SKU').str.contains('QBO') & 
                pl.col('SKU').str.contains(self.CONFIG['SPECIAL_SKUS']['QBO_SPECIAL'])
            ).then(False)
            .otherwise(
                pl.col('SKU').str.contains('|'.join(self.CONFIG['REMOVAL_SKUS']))
            ).alias('_removal_sku'),
            
            # Overall removal flag
            pl.when(pl.col('Webstore Order #').is_in(admin_fee_orders))
            .then(False)  # Don't remove ADMINFEE orders
            .otherwise(
                (pl.col('Unit Price').map_elements(lambda x: self._clean_currency(x), return_dtype=pl.Float64) == 0) |
                (pl.col('Product Type').str.contains('|'.join(self.CONFIG['REMOVAL_PRODUCT_TYPES']))) |
                (pl.col('SKU').str.contains('|'.join(self.CONFIG['REMOVAL_SKUS'])) & 
                 ~(pl.col('SKU').str.contains('QBO') & pl.col('SKU').str.contains(self.CONFIG['SPECIAL_SKUS']['QBO_SPECIAL'])))
            ).alias('_should_remove')
        ])
        
        # Apply SKU mappings for ADMINFEE orders
        df_processed = df_processed.with_columns([
            pl.when(
                pl.col('_is_admin_fee') & pl.col('Product Type').str.contains('QBES')
            ).then(pl.lit(self.CONFIG['ADMINFEE_SKU_MAPPINGS']['QBES']))
            .when(
                pl.col('_is_admin_fee') & pl.col('Product Type').str.contains('Hosting')
            ).then(pl.lit(self.CONFIG['ADMINFEE_SKU_MAPPINGS']['Hosting']))
            .otherwise(pl.col('SKU'))
            .alias('SKU')
        ])
        
        # Calculate removal adjustments per order
        removal_adjustments = (
            df_processed.filter(pl.col('_should_remove'))
            .with_columns([
                (pl.col('_clean_unit_price') * pl.col('Quantity').cast(pl.Float64)).alias('_removal_amount')
            ])
            .group_by('Webstore Order #')
            .agg(pl.sum('_removal_amount').alias('adjustment'))
            .filter(pl.col('Webstore Order #').is_not_null())
        )
        
        # Keep only non-removed rows
        filtered_df = df_processed.filter(~pl.col('_should_remove'))
        
        # Apply removal adjustments to grand totals (last row per order)
        if len(removal_adjustments) > 0:
            # Identify last row per order
            filtered_df = filtered_df.with_columns([
                pl.col('Webstore Order #').shift(-1).alias('_next_order_id')
            ]).with_columns([
                (pl.col('Webstore Order #') != pl.col('_next_order_id')).alias('_is_last_in_order')
            ])
            
            # Join with adjustments and apply to last row of each order
            filtered_df = filtered_df.join(
                removal_adjustments,
                on='Webstore Order #',
                how='left'
            ).with_columns([
                pl.when(pl.col('_is_last_in_order') & pl.col('adjustment').is_not_null())
                .then(
                    pl.col('Order Amount (Grand Total)').map_elements(
                        lambda x: self._clean_currency(x),
                        return_dtype=pl.Float64
                    ) - pl.col('adjustment')
                )
                .otherwise(pl.col('Order Amount (Grand Total)'))
                .alias('Order Amount (Grand Total)')
            ]).drop(['_next_order_id', '_is_last_in_order', 'adjustment'])
        
        # Clean up helper columns
        result_df = filtered_df.drop([
            '_clean_unit_price', '_is_admin_fee', '_zero_price', 
            '_removal_product_type', '_removal_sku', '_should_remove'
        ])
        
        return result_df
        
    def _apply_transformations(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply various transformations to the data using vectorized operations"""
        if len(df) == 0:
            return df
        
        # Apply all transformations using vectorized Polars operations
        transformed_df = df.with_columns([
            # Handle non-US addresses for Shipping State
            pl.when(
                pl.col('Shipping Country').str.to_lowercase() != 'united states'
            ).then(
                pl.when(
                    (pl.col('Shipping State/Province (text only)').is_null()) | 
                    (pl.col('Shipping State/Province (text only)') == '')
                ).then(pl.col('Shipping Country'))
                .otherwise(pl.col('Shipping State/Province (text only)'))
            ).otherwise(pl.col('Shipping State/Province (text only)'))
            .alias('Shipping State/Province (text only)'),
            
            # Handle non-US addresses for Billing State
            pl.when(
                pl.col('Shipping Country').str.to_lowercase() != 'united states'
            ).then(
                pl.when(
                    (pl.col('Billing State/Province (text only)').is_null()) | 
                    (pl.col('Billing State/Province (text only)') == '')
                ).then(pl.col('Shipping Country'))
                .otherwise(pl.col('Billing State/Province (text only)'))
            ).otherwise(pl.col('Billing State/Province (text only)'))
            .alias('Billing State/Province (text only)'),
            
            # Set tax reason for taxable states
            pl.when(
                pl.col('Shipping State/Province (text only)').is_in(self.CONFIG['TAX_STATES'])
            ).then(
                pl.col('Shipping State/Province (text only)').map_elements(
                    lambda state: self.CONFIG['TAX_STATE_MAPPINGS'].get(state, state),
                    return_dtype=pl.Utf8
                )
            ).otherwise(pl.col('Sales Tax (Reason)'))
            .alias('Sales Tax (Reason)'),
            
            # Set default class
            pl.lit(self.CONFIG['DEFAULT_CLASS']).alias('Class'),
            
            # Apply SKU replacements
            pl.col('SKU').map_elements(
                lambda sku: self._apply_sku_replacement(str(sku)),
                return_dtype=pl.Utf8
            ).alias('SKU')
        ])
        
        return transformed_df
    
    def _apply_sku_replacement(self, sku: str) -> str:
        """Apply SKU replacement patterns"""
        for pattern, replacement in self.CONFIG['SKU_REPLACEMENTS'].items():
            if pattern in sku:
                return replacement
        return sku
        
    def _process_tax_rows(self, df: pl.DataFrame) -> pl.DataFrame:
        """Add tax rows where applicable using optimized Polars operations"""
        # Sort by order ID
        df = df.sort('Webstore Order #')
        
        # Create a column to identify last row per order
        df_with_last = df.with_columns([
            pl.col('Webstore Order #').shift(-1).alias('next_order_id')
        ]).with_columns([
            (pl.col('Webstore Order #') != pl.col('next_order_id')).alias('is_last_in_order')
        ])
        
        # Filter for taxable rows (last row of order with tax)
        tax_states = list(self.CONFIG['TAX_STATE_MAPPINGS'].values())
        taxable_last_rows = df_with_last.filter(
            (pl.col('is_last_in_order') == True) &
            (pl.col('Sales Tax (Reason)').is_in(tax_states)) &
            (pl.col('Tax') != 0) &
            (pl.col('Tax').is_not_null())
        )
        
        # Create tax rows using Polars operations with explicit type casting
        if len(taxable_last_rows) > 0:
            tax_rows = taxable_last_rows.with_columns([
                pl.lit(1).cast(pl.Int64).alias('Quantity'),  # Explicit Int64 casting
                pl.col('Tax').cast(pl.Float64).alias('Unit Price'),  # Explicit Float64 casting
                pl.col('Sales Tax (Reason)').alias('SKU')
            ]).drop(['next_order_id', 'is_last_in_order'])
            
            # Combine original data (without helper columns) with tax rows
            original_data = df_with_last.drop(['next_order_id', 'is_last_in_order'])
            original_data_aligned, tax_rows_aligned = self._align_dataframe_schemas(original_data, tax_rows)
            result_df = pl.concat([original_data_aligned, tax_rows_aligned], how="vertical")
        else:
            # No tax rows to add
            result_df = df_with_last.drop(['next_order_id', 'is_last_in_order'])
        
        return result_df
        
    def _split_credit_orders(self, df: pl.DataFrame) -> Tuple[pl.DataFrame, Optional[pl.DataFrame]]:
        """Split credit orders from main orders using optimized Polars operations"""
        if len(df) == 0:
            return df, None
        
        # Clean grand total column for processing
        df_cleaned = df.with_columns(
            pl.col('Order Amount (Grand Total)').map_elements(
                lambda x: self._clean_currency(x),
                return_dtype=pl.Float64
            ).alias('_cleaned_grand_total')
        )
        
        # Identify credit orders using Polars filter conditions
        credit_condition = (
            (pl.col('Webstore Order #').str.contains(self.CONFIG['CREDIT_ORDER_PATTERN'])) |
            (pl.col('_cleaned_grand_total') < 0)
        )
        
        # Get unique credit order IDs
        credit_order_ids = df_cleaned.filter(credit_condition).select('Webstore Order #').unique()
        
        if len(credit_order_ids) == 0:
            # No credit orders found
            return df, None
        
        # Convert to list for join operation
        credit_ids_list = credit_order_ids.to_series().to_list()
        
        # Split using anti_join and join
        main_df = df.join(
            credit_order_ids, 
            on='Webstore Order #', 
            how='anti'
        )
        
        credit_df = df.join(
            credit_order_ids, 
            on='Webstore Order #', 
            how='inner'
        )
        
        return main_df, credit_df if len(credit_df) > 0 else None
        
    def _normalize_grand_totals(self, df: pl.DataFrame) -> pl.DataFrame:
        """Calculate and set grand total as sum of quantity * unit_price for each order group"""
        if len(df) == 0:
            return df
        
        logger.info(f"[NORMALIZE-GRAND-TOTALS] Starting with {len(df)} rows")
        
        # Sort by order ID first to ensure proper grouping
        df_sorted = df.sort('Webstore Order #')
        
        # Calculate the actual grand total for each order group as sum(quantity * unit_price)
        # Handle potential null values by filling with 0
        df_with_calcs = df_sorted.with_columns([
            pl.col('Quantity').fill_null(0).alias('_qty'),
            pl.col('Unit Price').fill_null(0).alias('_unit_price')
        ]).with_columns([
            (pl.col('_qty') * pl.col('_unit_price')).alias('_line_total')
        ])
        
        # Use window function to calculate grand total per order group (safer than group_by + join)
        df_with_totals = df_with_calcs.with_columns([
            pl.sum('_line_total').over('Webstore Order #').alias('_calculated_grand_total')
        ])
        
        logger.info(f"[NORMALIZE-GRAND-TOTALS] After calculations: {len(df_with_totals)} rows")
        
        # Create a column to identify the last row in each order group
        df_with_last = df_with_totals.with_columns([
            pl.col('Webstore Order #').shift(-1).alias('_next_order_id')
        ]).with_columns([
            ((pl.col('Webstore Order #') != pl.col('_next_order_id')) | pl.col('_next_order_id').is_null()).alias('_is_last_in_order')
        ])
        
        # Set grand total: calculated total for last row, 0 for all others
        result_df = df_with_last.with_columns([
            pl.when(pl.col('_is_last_in_order'))
            .then(pl.col('_calculated_grand_total').round(2))
            .otherwise(0)
            .alias('Order Amount (Grand Total)')
        ]).drop(['_next_order_id', '_is_last_in_order', '_qty', '_unit_price', '_line_total', '_calculated_grand_total'])
        
        logger.info(f"[NORMALIZE-GRAND-TOTALS] Final result: {len(result_df)} rows")
        
        # Log WooCommerce fee rows for debugging
        fee_rows = result_df.filter(pl.col('SKU') == 'WooCommerce Fees')
        logger.info(f"[NORMALIZE-GRAND-TOTALS] WooCommerce fee rows in result: {len(fee_rows)}")
        
        return result_df
        
    def _make_credits_positive(self, df: pl.DataFrame) -> pl.DataFrame:
        """Make quantities and unit prices positive for credit orders using optimized Polars operations"""
        if len(df) == 0:
            return df
        
        # Use Polars native operations to make negative values positive
        result_df = df.with_columns([
            pl.when(pl.col('Quantity').is_not_null() & (pl.col('Quantity') < 0))
            .then(pl.col('Quantity').abs())
            .otherwise(pl.col('Quantity'))
            .alias('Quantity'),
            
            pl.when(pl.col('Unit Price').is_not_null() & (pl.col('Unit Price') < 0))
            .then(pl.col('Unit Price').abs())
            .otherwise(pl.col('Unit Price'))
            .alias('Unit Price')
        ])
        
        return result_df
        
    def _apply_final_formatting(self, df: pl.DataFrame) -> pl.DataFrame:
        """Apply final formatting to the DataFrame"""
        # Ensure numeric columns are properly typed
        numeric_columns = ['Quantity', 'Unit Price', 'Tax', 'Order Amount (Grand Total)']
        
        for col in numeric_columns:
            if col in df.columns:
                # Convert to float, handling currency strings
                df = df.with_columns(
                    pl.col(col).map_elements(
                        lambda x: self._clean_currency(x),
                        return_dtype=pl.Float64
                    )
                )
        
        return df
        
    def _clean_currency(self, value) -> float:
        """Clean currency value to float using optimized method"""
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        
        # Handle string currency values
        value_str = str(value).strip()
        
        # Handle empty or placeholder values
        if not value_str or value_str in ['', '-', 'N/A', 'null', 'None']:
            return 0.0
        
        # Use optimized numba function for string processing
        try:
            # Clean the string first to remove currency symbols
            cleaned_str = value_str.replace('$', '').replace(',', '').replace(' ', '')
            return _fast_clean_currency_core(cleaned_str)
        except Exception:
            # Fallback to original method if numba fails
            try:
                # Handle negative values in parentheses format like (295.00)
                is_negative = False
                if value_str.startswith('(') and value_str.endswith(')'):
                    is_negative = True
                    value_str = value_str[1:-1]  # Remove parentheses
                
                # Remove common currency symbols and formatting
                value_str = value_str.replace('$', '').replace(',', '').replace(' ', '')
                
                # Handle negative sign
                if value_str.startswith('-'):
                    is_negative = True
                    value_str = value_str[1:]
                
                result = float(value_str)
                return -result if is_negative else result
            except ValueError:
                logger.warning(f"Could not parse currency value: '{value}', defaulting to 0.0")
                return 0.0
    
    def _normalize_salesforce_data_types(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Normalize Salesforce data types to ensure consistent types for processing
        
        Args:
            df: Raw Salesforce DataFrame
            
        Returns:
            DataFrame with normalized data types
        """
        try:
            # Define expected numeric columns and their target types
            numeric_columns = {
                'Quantity': pl.Int64,
                'Unit Price': pl.Float64,
                'Tax': pl.Float64,
                'Order Amount (Grand Total)': pl.Float64
            }
            
            # Create list of casting expressions
            cast_expressions = []
            
            for col in df.columns:
                if col in numeric_columns:
                    # Use the _clean_currency method for numeric columns that might be strings
                    if col in ['Unit Price', 'Order Amount (Grand Total)', 'Tax']:
                        cast_expressions.append(
                            pl.col(col).map_elements(
                                lambda x: self._clean_currency(x),
                                return_dtype=numeric_columns[col]
                            ).alias(col)
                        )
                    else:
                        # For Quantity, handle as integer with safe conversion
                        def safe_int_convert(x):
                            try:
                                if x is None or str(x).strip() in ['', 'None', 'null']:
                                    return 0
                                return int(float(str(x)))
                            except (ValueError, TypeError):
                                return 0
                        
                        cast_expressions.append(
                            pl.col(col).map_elements(
                                safe_int_convert,
                                return_dtype=numeric_columns[col]
                            ).alias(col)
                        )
                else:
                    # Keep other columns as-is
                    cast_expressions.append(pl.col(col))
            
            # Apply all casting operations
            normalized_df = df.with_columns(cast_expressions)
            
            logger.debug(f"[DATA-NORMALIZE] Normalized data types: {list(normalized_df.dtypes)}")
            
            return normalized_df
            
        except Exception as e:
            logger.warning(f"[DATA-NORMALIZE] Failed to normalize data types: {e}")
            # Return original DataFrame if normalization fails
            return df
    
    def _align_dataframe_schemas(self, df1: pl.DataFrame, df2: pl.DataFrame) -> Tuple[pl.DataFrame, pl.DataFrame]:
        """
        Align schemas of two DataFrames to ensure compatible types for concatenation
        
        Args:
            df1: First DataFrame (reference schema)
            df2: Second DataFrame to align with first
            
        Returns:
            Tuple of aligned DataFrames with compatible schemas
        """
        try:
            # Get common columns
            common_cols = set(df1.columns) & set(df2.columns)
            
            if not common_cols:
                # No common columns, return as-is
                return df1, df2
            
            # Cast df2 columns to match df1 types
            cast_expressions = []
            for col in common_cols:
                df1_type = df1[col].dtype
                df2_type = df2[col].dtype
                
                if df1_type != df2_type:
                    logger.debug(f"[SCHEMA-ALIGN] Casting column '{col}' from {df2_type} to {df1_type}")
                    cast_expressions.append(pl.col(col).cast(df1_type))
                else:
                    cast_expressions.append(pl.col(col))
            
            # Apply casting to df2
            df2_aligned = df2.with_columns(cast_expressions)
            
            return df1, df2_aligned
            
        except Exception as e:
            logger.warning(f"[SCHEMA-ALIGN] Failed to align schemas: {e}")
            # Return original DataFrames if alignment fails
            return df1, df2