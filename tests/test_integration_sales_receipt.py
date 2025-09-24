#!/usr/bin/env python3
"""
Integration tests for the complete sales receipt import process
Tests the full pipeline from API data to final output
"""
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import polars as pl

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.salesforce_api import SalesforceAPI
from services.woocommerce_api import WooCommerceAPI
from ui.operations.sales_receipt_import import SalesReceiptImport

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_salesforce_data_retrieval():
    """Test Salesforce data retrieval for sales receipt import"""
    print("=" * 60)
    print("TESTING SALESFORCE DATA RETRIEVAL")
    print("=" * 60)
    
    try:
        sf_api = SalesforceAPI()
        
        # Test connection
        print("Testing Salesforce connection...")
        connection_result = sf_api.test_connection()
        
        if not connection_result['success']:
            print(f"✗ Salesforce connection failed: {connection_result.get('error')}")
            return False, None
        
        print("✓ Salesforce connection successful")
        
        # Try to get the sales receipt report data
        sales_receipt_report_id = "00ORl000007JNmTMAW"
        
        print(f"Retrieving sales receipt report data (ID: {sales_receipt_report_id})...")
        start_time = time.time()
        
        report_data = sf_api.get_report_data(sales_receipt_report_id)
        
        retrieval_time = time.time() - start_time
        
        if report_data is None:
            print("✗ No data retrieved from Salesforce report")
            return False, None
        
        print(f"✓ Retrieved {len(report_data)} rows in {retrieval_time:.2f} seconds")
        print(f"✓ Columns: {len(report_data.columns)}")
        
        # Show column names
        print("✓ Available columns:")
        for i, col in enumerate(report_data.columns):
            print(f"     {i+1:2d}. {col}")
            if i >= 19:  # Show first 20 columns
                remaining = len(report_data.columns) - 20
                if remaining > 0:
                    print(f"     ... and {remaining} more columns")
                break
        
        # Show sample data
        if len(report_data) > 0:
            print("\n✓ Sample data (first row):")
            first_row = report_data.head(1).to_dicts()[0]
            for key, value in list(first_row.items())[:5]:
                print(f"     {key}: {value}")
            if len(first_row) > 5:
                print(f"     ... and {len(first_row) - 5} more fields")
        
        return True, report_data
        
    except Exception as e:
        print(f"✗ Exception during Salesforce data retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_woocommerce_data_retrieval():
    """Test WooCommerce data retrieval for fee matching"""
    print("\n" + "=" * 60)
    print("TESTING WOOCOMMERCE DATA RETRIEVAL")
    print("=" * 60)
    
    try:
        woo_api = WooCommerceAPI()
        
        # Test with recent date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Last 30 days
        
        print(f"Retrieving WooCommerce data for last 30 days...")
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        start_time = time.time()
        
        # Get payments data
        payments = woo_api.get_payments_paginated(
            start_date=start_date,
            end_date=end_date,
            limit=100  # Reasonable limit for testing
        )
        
        retrieval_time = time.time() - start_time
        
        print(f"✓ Retrieved {len(payments)} payments in {retrieval_time:.2f} seconds")
        
        if payments:
            print("✓ Sample payment data:")
            sample_payment = payments[0]
            for key, value in list(sample_payment.items())[:5]:
                print(f"     {key}: {value}")
            if len(sample_payment) > 5:
                print(f"     ... and {len(sample_payment) - 5} more fields")
        
        return True, payments
        
    except Exception as e:
        print(f"✗ Exception during WooCommerce data retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def test_sales_receipt_import_processing(sf_data: Optional[pl.DataFrame], woo_data: List[Dict]):
    """Test the complete sales receipt import processing"""
    print("\n" + "=" * 60)
    print("TESTING SALES RECEIPT IMPORT PROCESSING")
    print("=" * 60)
    
    if sf_data is None:
        print("✗ No Salesforce data available for processing")
        return False
    
    try:
        # Initialize the sales receipt import operation
        print("Initializing SalesReceiptImport operation...")
        operation = SalesReceiptImport()
        print("✓ Operation initialized")
        
        # Test with a smaller subset for processing speed
        test_data = sf_data.head(100) if len(sf_data) > 100 else sf_data
        print(f"✓ Using {len(test_data)} rows for testing")
        
        # Step 1: Validation
        print("\nStep 1: Data Validation...")
        start_time = time.time()
        
        errors = operation._validate_data(test_data)
        
        validation_time = time.time() - start_time
        print(f"✓ Validation completed in {validation_time:.3f} seconds")
        print(f"✓ Found {len(errors)} validation errors")
        
        if errors:
            print("  Sample errors:")
            for error in errors[:3]:  # Show first 3 errors
                print(f"    - {error}")
            if len(errors) > 3:
                print(f"    ... and {len(errors) - 3} more errors")
        
        # Step 2: Filtering
        print("\nStep 2: Data Filtering...")
        start_time = time.time()
        
        filtered_data = operation._filter_rows(test_data)
        
        filtering_time = time.time() - start_time
        print(f"✓ Filtering completed in {filtering_time:.3f} seconds")
        print(f"✓ Filtered from {len(test_data)} to {len(filtered_data)} rows")
        
        # Step 3: Transformations
        print("\nStep 3: Data Transformations...")
        start_time = time.time()
        
        transformed_data = operation._apply_transformations(filtered_data)
        
        transformation_time = time.time() - start_time
        print(f"✓ Transformations completed in {transformation_time:.3f} seconds")
        print(f"✓ Processed {len(transformed_data)} rows")
        
        # Step 4: Business Rules (this is where the boolean expressions were fixed)
        print("\nStep 4: Business Rules Application...")
        start_time = time.time()
        
        try:
            main_df, credit_df, errors_df = operation._apply_business_rules_lazy(transformed_data)
            
            business_rules_time = time.time() - start_time
            print(f"✓ Business rules completed in {business_rules_time:.3f} seconds")
            print(f"✓ Results:")
            print(f"    - Main records:   {len(main_df)}")
            print(f"    - Credit records: {len(credit_df)}")
            print(f"    - Error records:  {len(errors_df)}")
            
            # Verify the data structure
            if len(main_df) > 0:
                print(f"✓ Main data columns: {len(main_df.columns)}")
                print("  Sample main data columns:")
                for col in main_df.columns[:5]:
                    print(f"    - {col}")
                if len(main_df.columns) > 5:
                    print(f"    ... and {len(main_df.columns) - 5} more columns")
            
            return True, {
                'validation_time': validation_time,
                'filtering_time': filtering_time,
                'transformation_time': transformation_time,
                'business_rules_time': business_rules_time,
                'main_records': len(main_df),
                'credit_records': len(credit_df),
                'error_records': len(errors_df),
                'total_time': validation_time + filtering_time + transformation_time + business_rules_time
            }
            
        except Exception as e:
            print(f"✗ Business rules processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False, None
        
    except Exception as e:
        print(f"✗ Exception during sales receipt import processing: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_end_to_end_integration():
    """Test the complete end-to-end integration"""
    print("\n" + "=" * 60)
    print("TESTING END-TO-END INTEGRATION")
    print("=" * 60)
    
    try:
        # Use the actual operation execute method with a small date range
        operation = SalesReceiptImport()
        
        # Test with last 7 days to keep it manageable
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        print(f"Testing complete operation for date range:")
        print(f"  Start: {start_date.strftime('%Y-%m-%d')}")
        print(f"  End:   {end_date.strftime('%Y-%m-%d')}")
        
        start_time = time.time()
        
        # This should test the complete pipeline
        result = operation.execute(start_date, end_date)
        
        total_time = time.time() - start_time
        
        if result:
            print(f"✓ End-to-end operation completed in {total_time:.2f} seconds")
            print("✓ Operation executed successfully")
            
            # If result contains data, show summary
            if hasattr(result, 'items') and result.items():
                print("✓ Result summary:")
                for key, value in result.items():
                    if hasattr(value, '__len__') and not isinstance(value, str):
                        print(f"    {key}: {len(value)} items")
                    else:
                        print(f"    {key}: {value}")
            
            return True, total_time
        else:
            print("⚠ Operation completed but returned no result")
            return True, total_time  # Still consider it a success if no errors
        
    except Exception as e:
        print(f"✗ End-to-end integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def test_boolean_expressions_in_real_scenario(sf_data: Optional[pl.DataFrame]):
    """Specifically test that boolean expressions work with real data"""
    print("\n" + "=" * 60)
    print("TESTING BOOLEAN EXPRESSIONS WITH REAL DATA")
    print("=" * 60)
    
    if sf_data is None:
        print("✗ No Salesforce data available for boolean expression testing")
        return False
    
    try:
        operation = SalesReceiptImport()
        
        # Test the specific methods that had boolean expression issues
        test_data = sf_data.head(50) if len(sf_data) > 50 else sf_data
        
        print(f"Testing boolean expressions with {len(test_data)} real records...")
        
        # Test 1: Validation (where the main boolean expression issue was)
        print("\nTest 1: Validation boolean expressions...")
        start_time = time.time()
        
        errors = operation._validate_data(test_data)
        
        validation_time = time.time() - start_time
        print(f"✓ Validation boolean expressions work: {validation_time:.3f}s ({len(errors)} errors)")
        
        # Test 2: Filter rows (had boolean expressions)
        print("\nTest 2: Filtering boolean expressions...")
        start_time = time.time()
        
        filtered_data = operation._filter_rows(test_data)
        
        filtering_time = time.time() - start_time
        print(f"✓ Filtering boolean expressions work: {filtering_time:.3f}s")
        
        # Test 3: Business rules (complex boolean expressions)
        print("\nTest 3: Business rules boolean expressions...")
        start_time = time.time()
        
        transformed_data = operation._apply_transformations(filtered_data)
        main_df, credit_df, errors_df = operation._apply_business_rules_lazy(transformed_data)
        
        business_time = time.time() - start_time
        print(f"✓ Business rules boolean expressions work: {business_time:.3f}s")
        print(f"  - Processing completed without 'truth value of Expr' errors")
        print(f"  - Main: {len(main_df)}, Credit: {len(credit_df)}, Errors: {len(errors_df)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Boolean expression test failed: {e}")
        
        # Check if it's the specific error we fixed
        if "truth value of an Expr is ambiguous" in str(e):
            print("✗ CRITICAL: The boolean expression error still exists!")
            print("  This indicates the fixes were not complete.")
        
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests"""
    print("SALES RECEIPT IMPORT INTEGRATION TESTS")
    print("This will test the complete pipeline from API data to final output")
    print("=" * 70)
    
    all_success = True
    
    # Test 1: Salesforce data retrieval
    sf_success, sf_data = test_salesforce_data_retrieval()
    all_success &= sf_success
    
    # Test 2: WooCommerce data retrieval
    woo_success, woo_data = test_woocommerce_data_retrieval()
    all_success &= woo_success
    
    # Test 3: Sales receipt processing
    if sf_data is not None:
        processing_success, processing_metrics = test_sales_receipt_import_processing(sf_data, woo_data)
        all_success &= processing_success
        
        if processing_metrics:
            print(f"\n✓ Processing Performance Summary:")
            print(f"  - Total processing time: {processing_metrics['total_time']:.3f}s")
            print(f"  - Records processed: {processing_metrics['main_records'] + processing_metrics['credit_records']}")
            print(f"  - Processing rate: {(processing_metrics['main_records'] + processing_metrics['credit_records']) / processing_metrics['total_time']:.1f} records/second")
    
    # Test 4: Boolean expressions specifically
    if sf_data is not None:
        boolean_success = test_boolean_expressions_in_real_scenario(sf_data)
        all_success &= boolean_success
    
    # Test 5: End-to-end integration
    e2e_success, e2e_time = test_end_to_end_integration()
    all_success &= e2e_success
    
    # Final results
    print("\n" + "=" * 70)
    if all_success:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        print("✓ Salesforce API integration working")
        print("✓ WooCommerce API integration working")
        print("✓ Sales receipt import processing working")
        print("✓ Boolean expression fixes confirmed working")
        print("✓ End-to-end pipeline working")
        print("\nThe system is ready for performance optimizations!")
    else:
        print("❌ SOME INTEGRATION TESTS FAILED!")
        print("Please review the errors above before proceeding.")
        print("Fix any issues before implementing performance optimizations.")
    print("=" * 70)
    
    return all_success

if __name__ == "__main__":
    main()