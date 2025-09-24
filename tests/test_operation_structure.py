#!/usr/bin/env python3
"""
Test script to verify operation structure and logic
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_operation_import():
    """Test that we can import the operation class"""
    try:
        from src.ui.operations.sales_receipt_tie_out import SalesReceiptTieOut
        print("✓ SalesReceiptTieOut import successful")
        return True
    except Exception as e:
        print(f"✗ SalesReceiptTieOut import failed: {e}")
        return False

def test_operation_structure():
    """Test the basic operation structure"""
    try:
        # This will fail due to missing dependencies, but we can test the import
        from src.ui.operations.base_operation import BaseOperation
        print("✓ BaseOperation import successful")
        return True
    except Exception as e:
        print(f"✗ BaseOperation import failed: {e}")
        return False

def test_method_existence():
    """Test that required methods exist"""
    try:
        # Import without executing
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sales_receipt_tie_out", 
            os.path.join(os.path.dirname(__file__), 'src', 'ui', 'operations', 'sales_receipt_tie_out.py')
        )
        module = importlib.util.module_from_spec(spec)
        
        # Check if class exists
        source = spec.loader.get_data(spec.origin).decode('utf-8')
        
        required_methods = [
            'def execute',
            'def _load_file',
            'def _create_combined_workbook',
            'def _process_tie_out_analysis',
            'def _process_sfdc_data',
            'def _build_woocommerce_fees_map',
            'def _process_qb_data',
            'def _create_sfdc_to_qb_tieout',
            'def _create_qb_to_avalara_tieout'
        ]
        
        missing_methods = []
        for method in required_methods:
            if method not in source:
                missing_methods.append(method)
        
        if missing_methods:
            print(f"✗ Missing methods: {missing_methods}")
            return False
        else:
            print("✓ All required methods present")
            return True
            
    except Exception as e:
        print(f"✗ Method existence test failed: {e}")
        return False

def test_schema_definitions():
    """Test that schema definitions are consistent"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "sales_receipt_tie_out", 
            os.path.join(os.path.dirname(__file__), 'src', 'ui', 'operations', 'sales_receipt_tie_out.py')
        )
        source = spec.loader.get_data(spec.origin).decode('utf-8')
        
        # Check for schema definitions
        schema_checks = [
            "'SFDC Order #': pl.String",
            "'SFDC Amount': pl.Float64",
            "'QB Order #': pl.String",
            "'QB Amount': pl.Float64",
            "'Difference': pl.Float64",
            "'Notes': pl.String"
        ]
        
        schema_found = all(check in source for check in schema_checks)
        
        if schema_found:
            print("✓ Schema definitions are consistent")
            return True
        else:
            print("✗ Schema definitions missing or inconsistent")
            return False
            
    except Exception as e:
        print(f"✗ Schema definition test failed: {e}")
        return False

def run_tests():
    """Run all structure tests"""
    print("Testing Sales Receipt Tie Out Operation Structure")
    print("=" * 50)
    
    tests = [
        test_operation_import,
        test_operation_structure,
        test_method_existence,
        test_schema_definitions
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\nRunning {test.__name__}...")
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Structure Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("✓ All structure tests passed!")
        return True
    else:
        print("✗ Some structure tests failed!")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)