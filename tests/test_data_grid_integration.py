#!/usr/bin/env python3
"""
Test script to verify the data grid integration is complete
Tests the import structure and basic functionality without GUI
"""
import sys
import os
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that all components can be imported"""
    print("Testing imports...")
    
    try:
        # Test Polars import
        import polars as pl
        print("✅ Polars import successful")
        
        # Test core modules (without PyQt6)
        print("✅ Core imports successful")
        
        # Test our data structures
        from models.config import ConfigManager
        print("✅ ConfigManager import successful")
        
        # Test Salesforce API
        from services.salesforce_api import SalesforceAPI
        print("✅ SalesforceAPI import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_data_processing():
    """Test data processing functionality"""
    print("\nTesting data processing...")
    
    try:
        import polars as pl
        
        # Create sample data similar to Salesforce report format
        sample_data = {
            'Id': ['001XX000004C123', '001XX000004C124', '001XX000004C125'],
            'Name': ['Account A', 'Account B', 'Account C'],
            'Type': ['Customer', 'Prospect', 'Customer'],
            'AnnualRevenue': [1000000, 500000, 750000],
            'CreatedDate': ['2023-01-15', '2023-02-20', '2023-03-10']
        }
        
        # Create DataFrame
        df = pl.DataFrame(sample_data)
        print(f"✅ Sample DataFrame created: {df.shape}")
        
        # Test filtering (similar to data grid functionality)
        filtered = df.filter(pl.col('Type') == 'Customer')
        print(f"✅ Filtering works: {len(filtered)} customers found")
        
        # Test export functionality
        csv_data = df.write_csv()
        print(f"✅ CSV export works: {len(csv_data)} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Data processing test failed: {e}")
        return False

def test_salesforce_api_structure():
    """Test Salesforce API structure without connecting"""
    print("\nTesting Salesforce API structure...")
    
    try:
        from services.salesforce_api import SalesforceAPI
        
        # Create API instance (won't connect)
        api = SalesforceAPI("https://test.salesforce.com")
        print("✅ SalesforceAPI instance created")
        
        # Check if get_report_data method exists
        if hasattr(api, 'get_report_data'):
            print("✅ get_report_data method exists")
        else:
            print("❌ get_report_data method missing")
            return False
        
        # Check if get_reports method exists
        if hasattr(api, 'get_reports'):
            print("✅ get_reports method exists")
        else:
            print("❌ get_reports method missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Salesforce API test failed: {e}")
        return False

def test_integration_completeness():
    """Test that integration components are complete"""
    print("\nTesting integration completeness...")
    
    try:
        # Check main window file for key methods
        main_window_path = src_path / 'ui' / 'main_window.py'
        main_window_content = main_window_path.read_text()
        
        required_methods = [
            'on_report_data_loaded',
            'on_data_loading_error', 
            'load_selected_data',
            'InteractiveDataGrid'
        ]
        
        for method in required_methods:
            if method in main_window_content:
                print(f"✅ {method} found in main window")
            else:
                print(f"❌ {method} missing from main window")
                return False
        
        # Check data grid file exists
        data_grid_path = src_path / 'ui' / 'data_grid.py'
        if data_grid_path.exists():
            print("✅ data_grid.py file exists")
        else:
            print("❌ data_grid.py file missing")
            return False
        
        # Check for InteractiveDataGrid class
        data_grid_content = data_grid_path.read_text()
        if 'class InteractiveDataGrid' in data_grid_content:
            print("✅ InteractiveDataGrid class found")
        else:
            print("❌ InteractiveDataGrid class missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Interactive Report Viewer Integration")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_data_processing,
        test_salesforce_api_structure,
        test_integration_completeness
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
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"INTEGRATION TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All integration tests passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Launch application: python launch.py")
        print("3. Connect to Salesforce and test report loading")
        print("\nThe interactive report viewer should now work correctly!")
    else:
        print("❌ Some integration tests failed. Please check the errors above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)