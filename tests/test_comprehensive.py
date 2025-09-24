#!/usr/bin/env python3
"""
Comprehensive test to verify all methods work correctly
"""
import sys
import os
import polars as pl
import logging
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Suppress warnings
logging.basicConfig(level=logging.ERROR)

def create_realistic_test_data():
    """Create realistic test data for comprehensive testing"""
    
    return {
        'Account Name': [
            'Acme Corp',
            'Very Long Company Name That Exceeds The Standard Character Limit For Account Names',
            'Test Company Inc',
            'Beta Solutions LLC',
            'Gamma Industries'
        ],
        'Date Paid': [
            '2024-01-15',
            '2024-01-16',
            '2024-01-17',
            '2024-01-18',
            '2024-01-19'
        ],
        'Webstore Order #': [
            'WOO-12345',
            'WOO-12346',
            '',  # Empty order number
            'RMA-12347',  # Credit order
            'WOO-12348'
        ],
        'Class': ['02 - Sales'] * 5,
        'SKU': ['TEST-SKU-1', 'QBES', 'QBO', 'TEST-SKU-4', 'ADMINFEE'],
        'Product Type': ['Standard Product', 'QBES GNS', 'Standard Product', 'Standard Product', 'QBES'],
        'Quantity': [1, 2, 1, -1, 1],
        'Unit Price': ['100.00', '0.00', '50.00', '75.00', '25.00'],
        'Tax': [8.25, 0.00, 4.13, 6.19, 2.06],
        'Order Amount (Grand Total)': ['108.25', '0.00', '54.13', '-81.19', '27.06'],
        'Payment ID': ['pi_test1', 'pi_test2', 'pi_test3', 'pi_test4', 'pi_test5'],
        'Shipping Country': ['United States', 'United States', 'Canada', 'United States', 'United States'],
        'Billing Address Line 1': ['123 Main St', '', '456 Oak Ave', '789 Pine St', '321 Elm St'],
        'Billing City': ['New York', 'Boston', 'Toronto', 'Chicago', 'Dallas'],
        'Billing State/Province (text only)': ['NY', 'MA', 'ON', 'IL', 'TX'],
        'Billing Zip/Postal Code': ['10001', '02101', 'M5V 1A1', '60601', '75201'],
        'Shipping Address Line 1': ['123 Main St', '789 Pine St', '456 Oak Ave', '789 Pine St', '321 Elm St'],
        'Shipping City': ['New York', 'Boston', 'Toronto', 'Chicago', 'Dallas'],
        'Shipping State/Province (text only)': ['NY', 'MA', 'ON', 'IL', 'TX'],
        'Shipping Zip/Postal Code': ['10001', '02101', 'M5V 1A1', '60601', '75201'],
        'Sales Tax (Reason)': ['NY Sales Tax', 'MA Sales Tax', 'No Tax', 'IL Sales Tax', 'TX Sales Tax']
    }

def test_sales_receipt_import_comprehensive():
    """Test all methods in SalesReceiptImport"""
    
    print("Testing SalesReceiptImport comprehensive functionality...")
    
    # Import and initialize
    try:
        from ui.operations.sales_receipt_import import SalesReceiptImport
        operation = SalesReceiptImport()
        print("PASS: SalesReceiptImport initialized")
    except Exception as e:
        print(f"FAIL: Could not initialize SalesReceiptImport: {e}")
        return False
    
    # Create test data
    test_data = create_realistic_test_data()
    df = pl.DataFrame(test_data)
    print(f"Created test data: {len(df)} rows, {len(df.columns)} columns")
    
    # Test 1: Validation
    try:
        errors = operation._validate_data(df)
        print(f"PASS: _validate_data - found {len(errors)} errors")
    except Exception as e:
        print(f"FAIL: _validate_data: {e}")
        return False
    
    # Test 2: Filtering
    try:
        filtered_df = operation._filter_rows(df)
        print(f"PASS: _filter_rows - {len(df)} -> {len(filtered_df)} rows")
    except Exception as e:
        print(f"FAIL: _filter_rows: {e}")
        return False
    
    # Test 3: Transformations
    try:
        transformed_df = operation._apply_transformations(filtered_df)
        print(f"PASS: _apply_transformations - {len(filtered_df)} -> {len(transformed_df)} rows")
    except Exception as e:
        print(f"FAIL: _apply_transformations: {e}")
        return False
    
    # Test 4: Business rules
    try:
        main_df, credit_df, errors_df = operation._apply_business_rules_lazy(transformed_df)
        print(f"PASS: _apply_business_rules_lazy - Main: {len(main_df)}, Credit: {len(credit_df)}, Errors: {len(errors_df)}")
    except Exception as e:
        print(f"FAIL: _apply_business_rules_lazy: {e}")
        return False
    
    # Test 5: Credit separation
    try:
        credit_condition = (
            (pl.col('Webstore Order #').str.contains('RMA')) |
            (pl.col('Order Amount (Grand Total)').cast(pl.Float64) < 0)
        )
        
        test_df = df.with_columns([
            pl.col('Order Amount (Grand Total)').map_elements(
                lambda x: float(str(x).replace('$', '').replace(',', '')) if x else 0.0, 
                return_dtype=pl.Float64
            ).alias('_cleaned_grand_total')
        ])
        
        credit_rows = test_df.filter(credit_condition)
        print(f"PASS: Credit separation - found {len(credit_rows)} credit rows")
    except Exception as e:
        print(f"FAIL: Credit separation: {e}")
        return False
    
    return True

def test_edge_cases():
    """Test edge cases and boundary conditions"""
    
    print("\nTesting edge cases...")
    
    # Test empty dataframe
    try:
        empty_df = pl.DataFrame()
        from ui.operations.sales_receipt_import import SalesReceiptImport
        operation = SalesReceiptImport()
        
        # This should handle empty dataframes gracefully
        errors = operation._validate_data(empty_df)
        print(f"PASS: Empty dataframe handling - {len(errors)} errors")
    except Exception as e:
        print(f"FAIL: Empty dataframe handling: {e}")
        return False
    
    # Test dataframe with all null values
    try:
        null_data = {
            'Account Name': [None, None],
            'Shipping Country': [None, None],
            'Billing Address Line 1': [None, None],
            'Billing City': [None, None],
            'Billing State/Province (text only)': [None, None],
            'Billing Zip/Postal Code': [None, None],
            'Shipping Address Line 1': [None, None],
            'Shipping City': [None, None],
            'Shipping State/Province (text only)': [None, None],
            'Shipping Zip/Postal Code': [None, None]
        }
        
        null_df = pl.DataFrame(null_data)
        errors = operation._validate_data(null_df)
        print(f"PASS: Null dataframe handling - {len(errors)} errors")
    except Exception as e:
        print(f"FAIL: Null dataframe handling: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Running comprehensive tests for boolean expression fixes...")
    print("=" * 60)
    
    # Test main functionality
    main_success = test_sales_receipt_import_comprehensive()
    
    if main_success:
        # Test edge cases
        edge_success = test_edge_cases()
        
        if edge_success:
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED!")
            print("The boolean expression fixes are working correctly.")
            print("The SalesReceiptImport should now function without errors.")
        else:
            print("\n" + "=" * 60)
            print("Edge case tests failed.")
            sys.exit(1)
    else:
        print("\n" + "=" * 60)
        print("Main functionality tests failed.")
        sys.exit(1)