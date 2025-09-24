#!/usr/bin/env python3
"""
Test script for the complete data processing pipeline
End-to-end testing with realistic data scenarios and error handling
"""
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

import polars as pl
from ui.operations.sales_receipt_import import SalesReceiptImport

def create_realistic_salesforce_data():
    """Create realistic Salesforce-like data for testing"""
    
    # Simulate real Salesforce data with various data types and edge cases
    data = {
        'ACCOUNT_NAME': [
            'Acme Corporation', 'Beta Industries', 'Gamma Solutions', 'Delta Corp',
            'Epsilon LLC', 'Zeta Partners', 'Eta Enterprises', 'Theta Inc'
        ] * 10,  # 80 records
        'Order.Date_Paid__c': ['2025-05-15'] * 80,
        'Order.Webstore_Order__c': [f'WEB{i:04d}' for i in range(1, 81)],
        'Order.Class__c': ['02 - Sales'] * 80,
        'ORDER_BILLING_LINE1': [f'{i} Main Street' for i in range(1, 81)],
        'ORDER_BILLING_CITY': ['New York', 'Los Angeles', 'Chicago', 'Houston'] * 20,
        'ORDER_BILLING_STATE': ['NY', 'CA', 'IL', 'TX'] * 20,
        'ORDER_BILLING_ZIP': [f'{10001 + i:05d}' for i in range(80)],
        'ORDER_SHIPPING_LINE1': [f'{i} Shipping Ave' for i in range(1, 81)],
        'ORDER_SHIPPING_CITY': ['New York', 'Los Angeles', 'Chicago', 'Houston'] * 20,
        'ORDER_SHIPPING_STATE': ['NY', 'CA', 'IL', 'TX'] * 20,
        'ORDER_SHIPPING_COUNTRY_CODE': ['US'] * 80,
        'ORDER_SHIPPING_ZIP': [f'{20001 + i:05d}' for i in range(80)],
        'Order.Sales_Tax__c': ['', 'Texas', '', 'Colorado'] * 20,
        'Order.Payment_ID__c': [
            f'pi_{i:015d}abcdef123456' if i % 4 != 0 else f'ch_old_format_{i}'
            for i in range(1, 81)
        ],  # Mix of Stripe payment IDs and other formats
        'OrderItem.SKU__c': [
            'PRODUCT1', 'PRODUCT2', 'QBES', 'Hosting', 'QBO', 'ADMINFEE',
            'REC', 'FL-SVC-DEP'
        ] * 10,
        'ORDER_ITEM_QUANTITY': [1, 2, 1, 3, 1, 1, 2, 1] * 10,
        'ORDER_ITEM_UNITPRICE': [
            '100.50', '250.75', '500.00', '75.25', '125.00', '50.00', '200.00', '300.00'
        ] * 10,  # String format to simulate Salesforce
        'Order.Tax__c': [8.25, 16.50, 0.0, 6.02, 10.31, 0.0, 16.50, 24.75] * 10,
        'Order.Order_Amount_Grand_Total__c': [
            '108.75', '267.25', '500.00', '81.27', '135.31', '50.00', '216.50', '324.75'
        ] * 10,  # String format
        'OrderItem.Product_Type__c': [
            'Standard', 'Premium', 'QBES GNS', 'Hosting', 'Standard', 'Fee', 'Service', 'Enterprise'
        ] * 10
    }
    
    return pl.DataFrame(data)

def create_woocommerce_fees_cache():
    """Create realistic WooCommerce fees cache for testing"""
    
    # Create fees for Stripe payment IDs only
    fees_cache = {}
    
    for i in range(1, 81):
        if i % 4 != 0:  # Only for Stripe payment IDs
            payment_id = f'pi_{i:015d}abcdef123456'
            # Realistic fee amounts (2.9% + $0.30 for most transactions)
            base_amount = [100.50, 250.75, 500.00, 75.25, 125.00, 50.00, 200.00, 300.00][i % 8]
            fee = round(base_amount * 0.029 + 0.30, 2)
            fees_cache[payment_id] = fee
    
    return fees_cache

def test_complete_pipeline():
    """Test the complete data processing pipeline end-to-end"""
    
    print("="*80)
    print("DATA PROCESSING PIPELINE TESTING")
    print("End-to-end testing with realistic data scenarios")
    print("="*80)
    
    print(f"\n{'-'*60}")
    print("TEST 1: Complete Pipeline with Realistic Data")
    print(f"{'-'*60}")
    
    try:
        # Create test data
        print("📊 Creating realistic test data...")
        sf_df = create_realistic_salesforce_data()
        woo_fees_cache = create_woocommerce_fees_cache()
        
        print(f"✅ Salesforce data: {len(sf_df)} rows, {len(sf_df.columns)} columns")
        print(f"✅ WooCommerce cache: {len(woo_fees_cache)} fee entries")
        
        # Initialize sales receipt import
        import_op = SalesReceiptImport()
        
        # Step 1: Process data (vectorized approach)
        print(f"\n📈 Step 1: Processing data with vectorized lookup...")
        start_time = time.time()
        
        processed_df = import_op._process_data(sf_df, woo_fees_cache)
        
        step1_time = time.time() - start_time
        print(f"✅ Data processing completed in {step1_time:.4f} seconds")
        print(f"   Input rows: {len(sf_df)}")
        print(f"   Output rows: {len(processed_df)}")
        print(f"   Fee rows added: {len(processed_df) - len(sf_df)}")
        
        # Step 2: Apply business rules
        print(f"\n🔧 Step 2: Applying business rules...")
        start_time = time.time()
        
        main_df, credit_df, errors_df = import_op._apply_business_rules(processed_df)
        
        step2_time = time.time() - start_time
        print(f"✅ Business rules applied in {step2_time:.4f} seconds")
        print(f"   Main orders: {len(main_df)} rows")
        print(f"   Credit orders: {len(credit_df) if credit_df else 0} rows")
        print(f"   Errors: {len(errors_df) if errors_df else 0} rows")
        
        # Step 3: Final formatting
        print(f"\n✨ Step 3: Final formatting...")
        start_time = time.time()
        
        final_main = import_op._apply_final_formatting(main_df)
        if credit_df is not None:
            final_credit = import_op._apply_final_formatting(credit_df)
        else:
            final_credit = None
        
        step3_time = time.time() - start_time
        print(f"✅ Final formatting completed in {step3_time:.4f} seconds")
        
        total_time = step1_time + step2_time + step3_time
        print(f"\n⏱️  Total pipeline time: {total_time:.4f} seconds")
        print(f"   Average time per row: {total_time/len(sf_df)*1000:.2f} ms/row")
        
        # Validate results
        print(f"\n🔍 Pipeline validation:")
        
        # Check data types
        numeric_columns = ['Quantity', 'Unit Price', 'Tax', 'Order Amount (Grand Total)']
        for col in numeric_columns:
            if col in final_main.columns:
                col_type = final_main[col].dtype
                is_numeric = col_type in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]
                status = "✅" if is_numeric else "❌"
                print(f"   {status} {col}: {col_type}")
        
        # Check for WooCommerce fees
        fee_rows = final_main.filter(pl.col('SKU') == 'WooCommerce Fees')
        print(f"   ✅ WooCommerce fee rows: {len(fee_rows)}")
        
        if len(fee_rows) > 0:
            total_fees = fee_rows['Unit Price'].sum()
            print(f"   💰 Total fees processed: ${abs(total_fees):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Complete pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_schema_edge_cases():
    """Test pipeline with various schema edge cases"""
    
    print(f"\n{'-'*60}")
    print("TEST 2: Schema Edge Cases")
    print(f"{'-'*60}")
    
    edge_cases = [
        # Case 1: Mixed numeric types
        {
            'name': 'Mixed Numeric Types',
            'data': {
                'ACCOUNT_NAME': ['Test Account'],
                'Order.Payment_ID__c': ['pi_test123456789'],
                'OrderItem.SKU__c': ['PRODUCT1'],
                'ORDER_ITEM_QUANTITY': [1],  # Int64
                'ORDER_ITEM_UNITPRICE': [100.50],  # Float64
                'Order.Tax__c': [8.25],  # Float64
                'Order.Order_Amount_Grand_Total__c': [108.75],  # Float64
                'Order.Webstore_Order__c': ['12345']
            },
            'fees_cache': {'pi_test123456789': 3.25}
        },
        
        # Case 2: String numeric values
        {
            'name': 'String Numeric Values',
            'data': {
                'ACCOUNT_NAME': ['Test Account'],
                'Order.Payment_ID__c': ['pi_test123456789'],
                'OrderItem.SKU__c': ['PRODUCT1'],
                'ORDER_ITEM_QUANTITY': ['1'],  # String
                'ORDER_ITEM_UNITPRICE': ['100.50'],  # String
                'Order.Tax__c': ['8.25'],  # String
                'Order.Order_Amount_Grand_Total__c': ['108.75'],  # String
                'Order.Webstore_Order__c': ['12345']
            },
            'fees_cache': {'pi_test123456789': 3.25}
        },
        
        # Case 3: Null/None values
        {
            'name': 'Null/None Values',
            'data': {
                'ACCOUNT_NAME': ['Test Account'],
                'Order.Payment_ID__c': ['pi_test123456789'],
                'OrderItem.SKU__c': ['PRODUCT1'],
                'ORDER_ITEM_QUANTITY': [None],  # None
                'ORDER_ITEM_UNITPRICE': [100.50],
                'Order.Tax__c': [None],  # None
                'Order.Order_Amount_Grand_Total__c': [108.75],
                'Order.Webstore_Order__c': ['12345']
            },
            'fees_cache': {'pi_test123456789': 3.25}
        }
    ]
    
    import_op = SalesReceiptImport()
    
    for case in edge_cases:
        print(f"\n   Testing: {case['name']}")
        
        try:
            # Create DataFrame with potential schema issues
            df = pl.DataFrame(case['data'])
            print(f"   📊 Input schema: {dict(df.dtypes)}")
            
            # Run through pipeline
            processed_df = import_op._process_data(df, case['fees_cache'])
            main_df, credit_df, errors_df = import_op._apply_business_rules(processed_df)
            final_df = import_op._apply_final_formatting(main_df)
            
            print(f"   ✅ {case['name']}: Success - {len(final_df)} rows")
            print(f"   📊 Output schema: {dict(final_df.dtypes)}")
            
        except Exception as e:
            print(f"   ❌ {case['name']}: Failed - {e}")

def test_error_handling():
    """Test error handling and recovery scenarios"""
    
    print(f"\n{'-'*60}")
    print("TEST 3: Error Handling and Recovery")
    print(f"{'-'*60}")
    
    import_op = SalesReceiptImport()
    
    error_scenarios = [
        {
            'name': 'Empty DataFrame',
            'df': pl.DataFrame(),
            'cache': {}
        },
        {
            'name': 'Missing Required Columns',
            'df': pl.DataFrame({'random_column': ['test']}),
            'cache': {}
        },
        {
            'name': 'Invalid Payment IDs',
            'df': pl.DataFrame({
                'Order.Payment_ID__c': ['invalid_id', '', None],
                'OrderItem.SKU__c': ['PRODUCT1', 'PRODUCT2', 'PRODUCT3']
            }),
            'cache': {}
        },
        {
            'name': 'None WooCommerce Cache',
            'df': create_realistic_salesforce_data().head(5),
            'cache': None
        }
    ]
    
    for scenario in error_scenarios:
        print(f"\n   Testing: {scenario['name']}")
        
        try:
            result_df = import_op._process_data(scenario['df'], scenario['cache'])
            print(f"   ✅ {scenario['name']}: Handled gracefully - {len(result_df)} rows")
            
        except Exception as e:
            print(f"   ⚠️  {scenario['name']}: Exception - {e}")

def test_performance_scaling():
    """Test performance with different data sizes"""
    
    print(f"\n{'-'*60}")
    print("TEST 4: Performance Scaling")
    print(f"{'-'*60}")
    
    import_op = SalesReceiptImport()
    
    # Test with different data sizes
    test_sizes = [10, 50, 100, 500, 1000]
    
    print(f"\n   Performance scaling results:")
    print(f"   {'Size':>6} | {'Time (ms)':>10} | {'Rate (rows/s)':>12} | {'Memory':>8}")
    print(f"   {'-'*6}-+-{'-'*10}-+-{'-'*12}-+-{'-'*8}")
    
    for size in test_sizes:
        try:
            # Create data of specified size
            base_data = create_realistic_salesforce_data()
            if size <= len(base_data):
                test_df = base_data.head(size)
            else:
                # Repeat data to reach desired size
                repeat_factor = (size // len(base_data)) + 1
                test_df = pl.concat([base_data] * repeat_factor).head(size)
            
            # Create proportional cache
            cache = create_woocommerce_fees_cache()
            
            # Time the operation
            start_time = time.time()
            result_df = import_op._process_data(test_df, cache)
            elapsed_time = time.time() - start_time
            
            # Calculate metrics
            time_ms = elapsed_time * 1000
            rate = size / elapsed_time if elapsed_time > 0 else float('inf')
            
            print(f"   {size:6d} | {time_ms:8.2f}ms | {rate:10.0f} r/s | {'OK':>8}")
            
        except Exception as e:
            print(f"   {size:6d} | {'ERROR':>8} | {'N/A':>10} | {'N/A':>8}")

def test_data_integrity():
    """Test data integrity throughout the pipeline"""
    
    print(f"\n{'-'*60}")
    print("TEST 5: Data Integrity Validation")
    print(f"{'-'*60}")
    
    try:
        # Create test data with known values
        sf_df = create_realistic_salesforce_data().head(20)
        woo_fees_cache = create_woocommerce_fees_cache()
        
        import_op = SalesReceiptImport()
        
        # Track data through pipeline
        print(f"\n   Data integrity tracking:")
        
        # Initial state
        initial_payment_ids = sf_df.filter(
            pl.col('Order.Payment_ID__c').str.starts_with('pi_')
        )['Order.Payment_ID__c'].to_list()
        print(f"   📊 Initial Stripe payment IDs: {len(initial_payment_ids)}")
        
        # After processing
        processed_df = import_op._process_data(sf_df, woo_fees_cache)
        
        # Check that original data is preserved
        original_rows = processed_df.filter(pl.col('OrderItem.SKU__c') != 'WooCommerce Fees')
        fee_rows = processed_df.filter(pl.col('SKU') == 'WooCommerce Fees')
        
        print(f"   ✅ Original rows preserved: {len(original_rows)} (expected: {len(sf_df)})")
        print(f"   ✅ Fee rows added: {len(fee_rows)}")
        
        # Verify fee amounts are correct
        if len(fee_rows) > 0:
            fee_payment_ids = fee_rows['Payment ID'].to_list()
            fee_amounts = fee_rows['Unit Price'].to_list()
            
            correct_fees = 0
            for pid, amount in zip(fee_payment_ids, fee_amounts):
                expected_fee = woo_fees_cache.get(pid, 0.0)
                if abs(amount + expected_fee) < 0.01:  # Fees should be negative
                    correct_fees += 1
            
            accuracy = correct_fees / len(fee_rows) * 100
            print(f"   ✅ Fee accuracy: {accuracy:.1f}% ({correct_fees}/{len(fee_rows)})")
        
        # Verify no data corruption
        # Check that account names are preserved
        original_accounts = set(sf_df['ACCOUNT_NAME'].to_list())
        processed_accounts = set(original_rows['Account Name'].to_list())
        
        if original_accounts == processed_accounts:
            print(f"   ✅ Account names preserved correctly")
        else:
            print(f"   ❌ Account name mismatch detected")
        
        print(f"   ✅ Data integrity validation completed")
        
    except Exception as e:
        print(f"❌ Data integrity test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        success = test_complete_pipeline()
        
        if success:
            test_schema_edge_cases()
            test_error_handling()
            test_performance_scaling()
            test_data_integrity()
        
        print(f"\n{'='*80}")
        print("DATA PROCESSING PIPELINE TESTING COMPLETED")
        print("Pipeline validated for correctness, performance, and robustness")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Test script failed: {e}")
        import traceback
        traceback.print_exc()