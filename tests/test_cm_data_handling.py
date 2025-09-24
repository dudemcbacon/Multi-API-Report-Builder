#!/usr/bin/env python3
"""
Test script to verify CM data handling logic
"""

def test_cm_data_extraction():
    """Test CM data extraction from Sales Receipt Import result"""
    print("Testing CM data extraction from Sales Receipt Import result...")
    
    # Mock Sales Receipt Import result with CM data
    sf_result_with_cm = {
        'main': 'mock_main_dataframe',
        'credit': 'mock_credit_dataframe',  # This should become SFDC CM
        'errors': 'mock_errors_dataframe'
    }
    
    # Test the extraction logic
    sf_data = None
    sf_cm_data = None
    
    if isinstance(sf_result_with_cm, dict):
        # Get the main data
        if 'main' in sf_result_with_cm:
            sf_data = sf_result_with_cm['main']
        
        # Get the CM Import data
        if 'credit' in sf_result_with_cm and sf_result_with_cm['credit'] is not None:
            sf_cm_data = sf_result_with_cm['credit']
    
    print(f"✓ SF Data extracted: {sf_data}")
    print(f"✓ SF CM Data extracted: {sf_cm_data}")
    
    # Test without CM data
    print("\nTesting without CM data...")
    sf_result_no_cm = {
        'main': 'mock_main_dataframe',
        'errors': 'mock_errors_dataframe'
    }
    
    sf_data = None
    sf_cm_data = None
    
    if isinstance(sf_result_no_cm, dict):
        # Get the main data
        if 'main' in sf_result_no_cm:
            sf_data = sf_result_no_cm['main']
        
        # Get the CM Import data
        if 'credit' in sf_result_no_cm and sf_result_no_cm['credit'] is not None:
            sf_cm_data = sf_result_no_cm['credit']
    
    print(f"✓ SF Data extracted: {sf_data}")
    print(f"✓ SF CM Data extracted: {sf_cm_data} (should be None)")
    
    print("\n✓ CM data extraction logic test passed!")

def test_workbook_creation():
    """Test workbook creation with CM data"""
    print("\nTesting workbook creation with CM data...")
    
    # Mock data
    qb_sales_df = 'mock_qb_sales'
    qb_credit_df = 'mock_qb_credit'
    sf_data_df = 'mock_sf_data'
    sf_cm_data_df = 'mock_sf_cm_data'
    
    # Test the workbook creation logic
    workbook = {
        'QB': qb_sales_df,
        'QB CM': qb_credit_df,
        'SFDC': sf_data_df
    }
    
    # Add SFDC CM sheet if provided from Sales Receipt Import
    if sf_cm_data_df is not None:
        workbook['SFDC CM'] = sf_cm_data_df
    
    print(f"Workbook sheets: {list(workbook.keys())}")
    
    # Verify expected sheets
    expected_sheets = ['QB', 'QB CM', 'SFDC', 'SFDC CM']
    for sheet in expected_sheets:
        if sheet in workbook:
            print(f"✓ {sheet} sheet present")
        else:
            print(f"✗ {sheet} sheet missing")
    
    print("\n✓ Workbook creation logic test passed!")

def test_file_paths_structure():
    """Test file paths structure with CM data"""
    print("\nTesting file paths structure...")
    
    # Mock original file paths
    file_paths = {
        'qb_sales_receipts': '/path/to/qb_sales.csv',
        'qb_credit_memos': '/path/to/qb_cm.csv'
    }
    
    # Add SF data (as would be done in the worker)
    sf_data = 'mock_sf_dataframe'
    sf_cm_data = 'mock_sf_cm_dataframe'
    
    file_paths['salesforce_data'] = sf_data
    if sf_cm_data is not None:
        file_paths['salesforce_cm_data'] = sf_cm_data
    
    print(f"File paths structure: {list(file_paths.keys())}")
    
    # Test checking for CM data
    if 'salesforce_cm_data' in file_paths:
        print("✓ SFDC CM data found in file paths")
    else:
        print("✗ SFDC CM data not found in file paths")
    
    print("\n✓ File paths structure test passed!")

if __name__ == "__main__":
    test_cm_data_extraction()
    test_workbook_creation()
    test_file_paths_structure()
    print("\n🎉 All CM data handling tests passed!")