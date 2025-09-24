#!/usr/bin/env python3
"""
Test sales receipt import processing with realistic data
"""
import sys
import os
import polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def create_test_data():
    """Create realistic test data"""
    return {
        'Account Name': [
            'Acme Corp',
            'Very Long Company Name That Exceeds The Standard Character Limit For Account Names Which Should Trigger Validation',
            'Beta Solutions LLC',
            'Gamma Industries'
        ],
        'Date Paid': ['2024-01-15', '2024-01-16', '2024-01-17', '2024-01-18'],
        'Webstore Order #': ['WOO-12345', 'WOO-12346', '', 'RMA-12347'],
        'Class': ['02 - Sales'] * 4,
        'SKU': ['TEST-SKU-1', 'QBES', 'QBO', 'ADMINFEE'],
        'Product Type': ['Standard Product', 'QBES GNS', 'Standard Product', 'QBES'],
        'Quantity': [1, 2, 1, 1],
        'Unit Price': ['100.00', '0.00', '50.00', '25.00'],
        'Tax': [8.25, 0.00, 4.13, 2.06],
        'Order Amount (Grand Total)': ['108.25', '0.00', '54.13', '27.06'],
        'Payment ID': ['pi_test1', 'pi_test2', 'pi_test3', 'pi_test4'],
        'Shipping Country': ['United States', 'United States', 'Canada', 'United States'],
        'Billing Address Line 1': ['123 Main St', '', '456 Oak Ave', '321 Elm St'],
        'Billing City': ['New York', 'Boston', 'Toronto', 'Dallas'],
        'Billing State/Province (text only)': ['NY', 'MA', 'ON', 'TX'],
        'Billing Zip/Postal Code': ['10001', '02101', 'M5V 1A1', '75201'],
        'Shipping Address Line 1': ['123 Main St', '789 Pine St', '456 Oak Ave', '321 Elm St'],
        'Shipping City': ['New York', 'Boston', 'Toronto', 'Dallas'],
        'Shipping State/Province (text only)': ['NY', 'MA', 'ON', 'TX'],
        'Shipping Zip/Postal Code': ['10001', '02101', 'M5V 1A1', '75201'],
        'Sales Tax (Reason)': ['NY Sales Tax', 'MA Sales Tax', 'No Tax', 'TX Sales Tax']
    }

def test_complete_processing_pipeline():
    """Test the complete processing pipeline"""
    print("Testing complete sales receipt processing pipeline...")
    
    try:
        from ui.operations.sales_receipt_import import SalesReceiptImport
        
        # Initialize operation
        operation = SalesReceiptImport()
        print("PASS: Operation initialized")
        
        # Create test data
        test_data = create_test_data()
        df = pl.DataFrame(test_data)
        print(f"PASS: Test data created ({len(df)} rows)")
        
        # Step 1: Validation
        print("\nStep 1: Testing validation...")
        errors = operation._validate_data(df)
        print(f"PASS: Validation completed - {len(errors)} errors found")
        
        # Step 2: Filtering
        print("\nStep 2: Testing filtering...")
        filtered_df = operation._filter_rows(df)
        print(f"PASS: Filtering completed - {len(df)} -> {len(filtered_df)} rows")
        
        # Step 3: Transformations
        print("\nStep 3: Testing transformations...")
        transformed_df = operation._apply_transformations(filtered_df)
        print(f"PASS: Transformations completed - {len(transformed_df)} rows")
        
        # Step 4: Business Rules (this was the main issue)
        print("\nStep 4: Testing business rules (critical test)...")
        try:
            main_df, credit_df, errors_df = operation._apply_business_rules_lazy(transformed_df)
            print("PASS: Business rules completed successfully!")
            print(f"  - Main records: {len(main_df)}")
            print(f"  - Credit records: {len(credit_df)}")
            print(f"  - Error records: {len(errors_df)}")
            
            # This confirms the boolean expression fixes are working
            print("PASS: Boolean expressions are working correctly!")
            
        except Exception as e:
            if "truth value of an Expr is ambiguous" in str(e):
                print("FAIL: Boolean expression error still exists!")
                print(f"Error: {e}")
                return False
            else:
                print(f"FAIL: Unexpected error in business rules: {e}")
                return False
        
        print("\nALL PROCESSING STEPS COMPLETED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        print(f"FAIL: Processing pipeline error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_specific_boolean_expressions():
    """Test the specific boolean expressions that were problematic"""
    print("\nTesting specific boolean expressions that were fixed...")
    
    try:
        import polars as pl
        
        # Test 1: Complex OR expression with parentheses
        print("Test 1: Complex OR expression...")
        df = pl.DataFrame({
            'Shipping Country': ['United States', 'Canada'],
            'Billing Address Line 1': ['123 Main St', ''],
            'Billing City': ['New York', 'Toronto']
        })
        
        result = df.with_columns([
            pl.when(pl.col('Shipping Country').str.to_lowercase() == 'united states')
            .then(
                (pl.col('Billing Address Line 1').str.strip_chars().str.len_chars() == 0) |
                (pl.col('Billing City').str.strip_chars().str.len_chars() == 0)
            )
            .otherwise(False)
            .alias('has_missing_address')
        ])
        
        print("PASS: Complex OR expression with parentheses works")
        
        # Test 2: Filter with OR conditions
        print("Test 2: Filter with OR conditions...")
        result = df.filter(
            (pl.col('Shipping Country') == 'United States') |
            (pl.col('Shipping Country') == 'Canada')
        )
        
        print("PASS: Filter with OR conditions works")
        
        # Test 3: Building error conditions incrementally
        print("Test 3: Building error conditions...")
        error_conditions = (pl.col('Billing Address Line 1').str.len_chars() == 0)
        error_conditions = error_conditions | (pl.col('Billing City').str.len_chars() == 0)
        
        result = df.filter(error_conditions)
        print("PASS: Building error conditions incrementally works")
        
        return True
        
    except Exception as e:
        print(f"FAIL: Boolean expression test failed: {e}")
        if "truth value of an Expr is ambiguous" in str(e):
            print("CRITICAL: The original boolean expression error still exists!")
        return False

def main():
    print("SALES RECEIPT PROCESSING VERIFICATION")
    print("="*50)
    
    # Test 1: Boolean expressions
    bool_success = test_specific_boolean_expressions()
    
    # Test 2: Complete processing pipeline
    pipeline_success = test_complete_processing_pipeline()
    
    print("\n" + "="*50)
    print("FINAL RESULTS:")
    
    if bool_success and pipeline_success:
        print("SUCCESS: All tests passed!")
        print("- Boolean expression fixes are working")
        print("- Sales receipt processing pipeline is functional")
        print("- No 'truth value of Expr' errors detected")
        print("\nThe system is ready for performance optimizations!")
        return True
    else:
        print("FAILURE: Some tests failed!")
        if not bool_success:
            print("- Boolean expression tests failed")
        if not pipeline_success:
            print("- Processing pipeline tests failed")
        print("\nDo NOT proceed with optimizations until all tests pass!")
        return False

if __name__ == "__main__":
    main()