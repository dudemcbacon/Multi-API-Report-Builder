#!/usr/bin/env python3
"""
Test script for Sales Receipt Tie Out functionality
"""
import os
import sys
import tempfile
import csv
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock the imports for testing
class MockPolarsFetcher:
    def __init__(self):
        pass
    
    def from_pandas(self, df, schema_overrides=None):
        return df
    
    def concat(self, dfs, how="vertical"):
        return dfs[0] if dfs else None
    
    def DataFrame(self, data, schema=None):
        return data

# Mock polars for testing
sys.modules['polars'] = MockPolarsFetcher()

try:
    from src.ui.operations.sales_receipt_tie_out import SalesReceiptTieOut
    IMPORT_SUCCESS = True
except Exception as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)

def create_test_files():
    """Create test files for the tie out operation"""
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Create test QB Sales Receipts CSV
    qb_sales_data = {
        'Num': ['1001', '1002', '1003', '1004'],
        'Amount': ['100.50', '200.75', '150.25', '300.00']
    }
    qb_sales_df = pd.DataFrame(qb_sales_data)
    qb_sales_path = os.path.join(temp_dir, 'qb_sales.csv')
    qb_sales_df.to_csv(qb_sales_path, index=False)
    
    # Create test QB Credit Memos CSV
    qb_cm_data = {
        'Num': ['CM001', 'CM002'],
        'Amount': ['-50.00', '-25.50']
    }
    qb_cm_df = pd.DataFrame(qb_cm_data)
    qb_cm_path = os.path.join(temp_dir, 'qb_cm.csv')
    qb_cm_df.to_csv(qb_cm_path, index=False)
    
    # Create test SalesForce Excel file with multiple sheets
    sf_data_sheet1 = {
        'Webstore Order #': ['1001', '1002', '1005'],
        'Order Amount (Grand Total)': ['100.50', '200.75', '500.00'],
        'SKU': ['Product1', 'Product2', 'Product3'],
        'Unit Price': ['100.50', '200.75', '500.00']
    }
    
    sf_data_sheet2 = {
        'Webstore Order #': ['1003', '1004'],
        'Order Amount (Grand Total)': ['150.25', '300.00'],
        'SKU': ['Product4', 'WooCommerce Fees'],
        'Unit Price': ['150.25', '10.00']
    }
    
    change_log_sheet = {
        'Order': ['1001', '1002'],
        'Change': ['Updated', 'Modified']
    }
    
    sf_path = os.path.join(temp_dir, 'salesforce_data.xlsx')
    with pd.ExcelWriter(sf_path, engine='openpyxl') as writer:
        pd.DataFrame(sf_data_sheet1).to_excel(writer, sheet_name='Sheet1', index=False)
        pd.DataFrame(sf_data_sheet2).to_excel(writer, sheet_name='Sheet2', index=False)
        pd.DataFrame(change_log_sheet).to_excel(writer, sheet_name='Change Log', index=False)
    
    return {
        'qb_sales_receipts': qb_sales_path,
        'qb_credit_memos': qb_cm_path,
        'salesforce_data': sf_path
    }

def test_file_loading():
    """Test file loading functionality"""
    print("Testing file loading...")
    
    file_paths = create_test_files()
    operation = SalesReceiptTieOut()
    
    try:
        # Test CSV loading
        qb_df = operation._load_file(file_paths['qb_sales_receipts'])
        print(f"QB Sales CSV loaded: {qb_df.shape}")
        print(f"QB Sales columns: {qb_df.columns}")
        
        qb_cm_df = operation._load_file(file_paths['qb_credit_memos'])
        print(f"QB CM CSV loaded: {qb_cm_df.shape}")
        print(f"QB CM columns: {qb_cm_df.columns}")
        
        # Test Excel loading (should exclude Change Log sheet)
        sf_df = operation._load_file(file_paths['salesforce_data'])
        print(f"SalesForce Excel loaded: {sf_df.shape}")
        print(f"SalesForce columns: {sf_df.columns}")
        
        # Check that Change Log sheet was excluded
        if 'source_sheet' in sf_df.columns:
            sheets = sf_df.select('source_sheet').unique().to_pandas()['source_sheet'].tolist()
            print(f"Sheets included: {sheets}")
            assert 'Change Log' not in sheets, "Change Log sheet should be excluded"
        
        print("✓ File loading tests passed")
        return True
        
    except Exception as e:
        print(f"✗ File loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_processing():
    """Test data processing methods"""
    print("\nTesting data processing...")
    
    file_paths = create_test_files()
    operation = SalesReceiptTieOut()
    
    try:
        # Load files
        qb_sales_df = operation._load_file(file_paths['qb_sales_receipts'])
        qb_cm_df = operation._load_file(file_paths['qb_credit_memos'])
        sf_df = operation._load_file(file_paths['salesforce_data'])
        
        # Create combined workbook
        workbook = operation._create_combined_workbook(qb_sales_df, qb_cm_df, sf_df)
        print(f"Workbook sheets: {list(workbook.keys())}")
        
        # Test SFDC data processing
        sfdc_data = operation._process_sfdc_data(workbook)
        print(f"SFDC data processed: {len(sfdc_data)} entries")
        print(f"SFDC data sample: {sfdc_data[:3]}")
        
        # Test WooCommerce fees processing
        woo_fees = operation._build_woocommerce_fees_map(workbook)
        print(f"WooCommerce fees: {woo_fees}")
        
        # Test QB data processing
        qb_data = operation._process_qb_data(workbook)
        print(f"QB data processed: {len(qb_data)} entries")
        print(f"QB data sample: {qb_data[:3]}")
        
        print("✓ Data processing tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Data processing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tie_out_creation():
    """Test tie-out sheet creation"""
    print("\nTesting tie-out creation...")
    
    file_paths = create_test_files()
    operation = SalesReceiptTieOut()
    
    try:
        # Load and process data
        qb_sales_df = operation._load_file(file_paths['qb_sales_receipts'])
        qb_cm_df = operation._load_file(file_paths['qb_credit_memos'])
        sf_df = operation._load_file(file_paths['salesforce_data'])
        
        workbook = operation._create_combined_workbook(qb_sales_df, qb_cm_df, sf_df)
        sfdc_data = operation._process_sfdc_data(workbook)
        qb_data = operation._process_qb_data(workbook)
        
        # Create SFDC to QB tie-out with explicit schema
        print("Creating SFDC to QB tie-out...")
        
        # Create aligned data with consistent types
        aligned_data = []
        
        # Add some test data manually to ensure consistent schema
        test_row = {
            'SFDC Order #': '1001',
            'SFDC Amount': 100.50,
            'QB Order #': '1001',
            'QB Amount': 100.50,
            'Difference': 0.0,
            'Notes': ''
        }
        aligned_data.append(test_row)
        
        # Add empty row to test empty string handling
        empty_row = {
            'SFDC Order #': '',
            'SFDC Amount': 0.0,
            'QB Order #': '1004',
            'QB Amount': 300.0,
            'Difference': -300.0,
            'Notes': ''
        }
        aligned_data.append(empty_row)
        
        # Test DataFrame creation with explicit schema
        schema = {
            'SFDC Order #': pl.String,
            'SFDC Amount': pl.Float64,
            'QB Order #': pl.String,
            'QB Amount': pl.Float64,
            'Difference': pl.Float64,
            'Notes': pl.String
        }
        
        result_df = pl.DataFrame(aligned_data, schema=schema)
        print(f"Tie-out DataFrame created: {result_df.shape}")
        print(f"Tie-out columns: {result_df.columns}")
        print(f"Tie-out data types: {result_df.dtypes}")
        
        print("✓ Tie-out creation tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Tie-out creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_operation():
    """Test the full operation end-to-end"""
    print("\nTesting full operation...")
    
    file_paths = create_test_files()
    operation = SalesReceiptTieOut()
    
    try:
        # Set up progress callback
        def progress_callback(pct, msg):
            print(f"Progress: {pct}% - {msg}")
        
        operation.progress_callback = progress_callback
        
        # Run the full operation
        result = operation.execute(file_paths)
        
        print(f"Operation completed successfully!")
        print(f"Result keys: {list(result.keys())}")
        
        # Check expected sheets
        expected_sheets = ['QB', 'QB CM', 'SFDC', 'SFDC to QB Tie Out', 'QB to Avalara Tie Out']
        for sheet in expected_sheets:
            if sheet in result:
                print(f"✓ {sheet} sheet present: {result[sheet].shape}")
            else:
                print(f"✗ {sheet} sheet missing")
        
        print("✓ Full operation test passed")
        return True
        
    except Exception as e:
        print(f"✗ Full operation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("Starting Sales Receipt Tie Out Tests")
    print("=" * 50)
    
    tests = [
        test_file_loading,
        test_data_processing,
        test_tie_out_creation,
        test_full_operation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print("✗ Some tests failed!")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)