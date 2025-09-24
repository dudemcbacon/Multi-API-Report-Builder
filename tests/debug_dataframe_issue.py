#!/usr/bin/env python3
"""
Debug script to identify the DataFrame creation issue
"""
import polars as pl

def test_dataframe_creation():
    """Test DataFrame creation with mixed data types"""
    print("Testing DataFrame creation with mixed data types...")
    
    # Test case 1: Simple consistent data
    print("\n1. Testing simple consistent data:")
    simple_data = [
        {'col1': 'A', 'col2': 1.0, 'col3': 'X'},
        {'col1': 'B', 'col2': 2.0, 'col3': 'Y'},
    ]
    
    try:
        df1 = pl.DataFrame(simple_data)
        print(f"✓ Simple data worked: {df1.shape}")
        print(f"  Data types: {df1.dtypes}")
    except Exception as e:
        print(f"✗ Simple data failed: {e}")
    
    # Test case 2: Data with empty strings
    print("\n2. Testing data with empty strings:")
    empty_string_data = [
        {'col1': 'A', 'col2': 1.0, 'col3': 'X'},
        {'col1': '', 'col2': 2.0, 'col3': 'Y'},
    ]
    
    try:
        df2 = pl.DataFrame(empty_string_data)
        print(f"✓ Empty string data worked: {df2.shape}")
        print(f"  Data types: {df2.dtypes}")
    except Exception as e:
        print(f"✗ Empty string data failed: {e}")
    
    # Test case 3: Data with mixed types in same column
    print("\n3. Testing data with mixed types in same column:")
    mixed_type_data = [
        {'col1': 'A', 'col2': 1.0, 'col3': 'X'},
        {'col1': 'B', 'col2': '', 'col3': 'Y'},  # Empty string in numeric column
    ]
    
    try:
        df3 = pl.DataFrame(mixed_type_data)
        print(f"✓ Mixed type data worked: {df3.shape}")
        print(f"  Data types: {df3.dtypes}")
    except Exception as e:
        print(f"✗ Mixed type data failed: {e}")
    
    # Test case 4: Data with explicit schema
    print("\n4. Testing data with explicit schema:")
    schema_data = [
        {'col1': 'A', 'col2': 1.0, 'col3': 'X'},
        {'col1': '', 'col2': 0.0, 'col3': 'Y'},  # Convert empty to 0.0
    ]
    
    schema = {
        'col1': pl.String,
        'col2': pl.Float64,
        'col3': pl.String
    }
    
    try:
        df4 = pl.DataFrame(schema_data, schema=schema)
        print(f"✓ Explicit schema data worked: {df4.shape}")
        print(f"  Data types: {df4.dtypes}")
    except Exception as e:
        print(f"✗ Explicit schema data failed: {e}")
    
    # Test case 5: Reproduce the exact issue from the error
    print("\n5. Testing tie-out data structure:")
    tie_out_data = [
        {
            'SFDC Order #': '1001',
            'SFDC Amount': 100.50,
            'QB Order #': '1001',
            'QB Amount': 100.50,
            'Difference': 0.0,
            'Notes': ''
        },
        {
            'SFDC Order #': '',  # Empty string
            'SFDC Amount': 0.0,
            'QB Order #': '1002',
            'QB Amount': 200.0,
            'Difference': -200.0,
            'Notes': ''
        }
    ]
    
    try:
        df5 = pl.DataFrame(tie_out_data)
        print(f"✓ Tie-out data worked: {df5.shape}")
        print(f"  Data types: {df5.dtypes}")
        print(f"  Sample data:\n{df5}")
    except Exception as e:
        print(f"✗ Tie-out data failed: {e}")
        
        # Try with explicit schema
        print("  Trying with explicit schema...")
        schema = {
            'SFDC Order #': pl.String,
            'SFDC Amount': pl.Float64,
            'QB Order #': pl.String,
            'QB Amount': pl.Float64,
            'Difference': pl.Float64,
            'Notes': pl.String
        }
        
        try:
            df5_schema = pl.DataFrame(tie_out_data, schema=schema)
            print(f"  ✓ With schema worked: {df5_schema.shape}")
            print(f"    Data types: {df5_schema.dtypes}")
        except Exception as e2:
            print(f"  ✗ With schema also failed: {e2}")
    
    # Test case 6: Check infer_schema_length parameter
    print("\n6. Testing with infer_schema_length parameter:")
    try:
        df6 = pl.DataFrame(tie_out_data, infer_schema_length=None)
        print(f"✓ With infer_schema_length=None worked: {df6.shape}")
    except Exception as e:
        print(f"✗ With infer_schema_length=None failed: {e}")

if __name__ == "__main__":
    test_dataframe_creation()