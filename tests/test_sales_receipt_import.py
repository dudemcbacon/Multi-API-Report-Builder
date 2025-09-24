#!/usr/bin/env python3
"""
Test script for sales receipt import operations
"""
import sys
import os
import polars as pl
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui.operations.sales_receipt_import import SalesReceiptImport

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_polars_boolean_expressions():
    """Test that Polars boolean expressions work correctly"""
    print("Testing Polars boolean expressions...")
    
    # Create test data
    test_data = {
        'Account Name': ['Test Account 1', 'Test Account 2'],
        'Shipping Country': ['United States', 'Canada'],
        'Billing Address Line 1': ['123 Main St', ''],
        'Billing City': ['New York', 'Toronto'],
        'Billing State/Province (text only)': ['NY', 'ON'],
        'Billing Zip/Postal Code': ['10001', 'M5V 1A1'],
        'Shipping Address Line 1': ['123 Main St', '456 Oak Ave'],
        'Shipping City': ['New York', 'Toronto'],
        'Shipping State/Province (text only)': ['NY', 'ON'],
        'Shipping Zip/Postal Code': ['10001', 'M5V 1A1']
    }
    
    df = pl.DataFrame(test_data)
    print(f"Created test DataFrame with {len(df)} rows")
    print(df)
    
    # Test the problematic boolean expression
    try:
        print("\nTesting problematic boolean expression (using |)...")
        
        # This should fail with the current code
        result = df.with_columns([
            pl.when(pl.col('Shipping Country').str.to_lowercase() == 'united states')
            .then(
                pl.col('Billing Address Line 1').str.strip_chars().str.len_chars() == 0 |
                pl.col('Billing City').str.strip_chars().str.len_chars() == 0 |
                pl.col('Billing State/Province (text only)').str.strip_chars().str.len_chars() == 0 |
                pl.col('Billing Zip/Postal Code').str.strip_chars().str.len_chars() == 0 |
                pl.col('Shipping Address Line 1').str.strip_chars().str.len_chars() == 0 |
                pl.col('Shipping City').str.strip_chars().str.len_chars() == 0 |
                pl.col('Shipping State/Province (text only)').str.strip_chars().str.len_chars() == 0 |
                pl.col('Shipping Zip/Postal Code').str.strip_chars().str.len_chars() == 0
            )
            .otherwise(False)
            .alias('missing_required_fields')
        ])
        
        print("ERROR: This should have failed!")
        
    except TypeError as e:
        print(f"SUCCESS: Got expected error: {e}")
        print("This confirms the issue with | operator")
    
    # Test the correct boolean expression
    try:
        print("\nTesting correct boolean expression (using or())...")
        
        # This should work
        result = df.with_columns([
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
        
        print("SUCCESS: Boolean expression with parentheses worked!")
        print(result.select(['Account Name', 'Shipping Country', 'missing_required_fields']))
        
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")

def test_sales_receipt_import_validation():
    """Test the actual sales receipt import validation"""
    print("\n" + "="*50)
    print("Testing SalesReceiptImport validation...")
    print("="*50)
    
    # Create test data that should trigger validation errors
    test_data = {
        'Account Name': ['Test Account 1', 'Test Account 2', 'Very Long Account Name That Exceeds The Character Limit For Account Names'],
        'Shipping Country': ['United States', 'United States', 'Canada'],
        'Billing Address Line 1': ['123 Main St', '', '456 Oak Ave'],  # Second row has empty address
        'Billing City': ['New York', 'Boston', 'Toronto'],
        'Billing State/Province (text only)': ['NY', 'MA', 'ON'],
        'Billing Zip/Postal Code': ['10001', '02101', 'M5V 1A1'],
        'Shipping Address Line 1': ['123 Main St', '789 Pine St', '456 Oak Ave'],
        'Shipping City': ['New York', 'Boston', 'Toronto'],
        'Shipping State/Province (text only)': ['NY', 'MA', 'ON'],
        'Shipping Zip/Postal Code': ['10001', '02101', 'M5V 1A1']
    }
    
    df = pl.DataFrame(test_data)
    print(f"Created test DataFrame with {len(df)} rows")
    
    # Initialize SalesReceiptImport
    try:
        import_operation = SalesReceiptImport()
        print("SalesReceiptImport initialized successfully")
        
        # Test validation
        print("\nTesting _validate_data method...")
        errors = import_operation._validate_data(df)
        print(f"Validation returned {len(errors)} errors")
        
        if errors:
            print("Validation errors found:")
            for error in errors:
                print(f"  - {error}")
        else:
            print("No validation errors found")
            
    except Exception as e:
        print(f"ERROR in SalesReceiptImport: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting sales receipt import tests...")
    print("="*50)
    
    test_polars_boolean_expressions()
    test_sales_receipt_import_validation()
    
    print("\nTests completed!")