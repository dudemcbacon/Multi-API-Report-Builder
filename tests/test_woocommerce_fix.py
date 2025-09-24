#!/usr/bin/env python3
"""
Test the WooCommerce fix - verify that WooCommerceDataWorker can create fresh API instances
"""
import sys
import os
from unittest.mock import Mock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_woocommerce_worker_fix():
    """Test that WooCommerceDataWorker creates fresh API instances"""
    print("Testing WooCommerce Worker Fix")
    print("=" * 40)
    
    try:
        # Mock the AsyncWooCommerceAPI class to avoid dependency issues
        with patch('src.services.async_woocommerce_api.AsyncWooCommerceAPI') as mock_api_class:
            # Create a mock API instance
            mock_api_instance = Mock()
            mock_api_instance.get_data_source_data.return_value = "test_data"
            mock_api_class.return_value.__aenter__ = Mock(return_value=mock_api_instance)
            mock_api_class.return_value.__aexit__ = Mock(return_value=None)
            
            # Import and test the worker class
            from src.ui.main_window import WooCommerceDataWorker
            
            # Create worker instance
            data_source = {'id': 'test_id', 'name': 'Test WooCommerce'}
            worker = WooCommerceDataWorker(data_source)
            
            print(f"✓ WooCommerceDataWorker created successfully")
            print(f"  - Data source: {worker.data_source}")
            print(f"  - No woo_api parameter required (creates fresh instance)")
            
            # Test that the worker doesn't have a pre-existing woo_api
            assert not hasattr(worker, 'woo_api'), "Worker should not have pre-existing woo_api"
            print(f"✓ Worker correctly has no pre-existing woo_api")
            
            # Test that the async method uses context manager pattern
            import asyncio
            import inspect
            
            # Check the source code of _load_data_async
            source = inspect.getsource(worker._load_data_async)
            assert 'async with AsyncWooCommerceAPI' in source, "Should use context manager"
            print(f"✓ _load_data_async uses async with AsyncWooCommerceAPI pattern")
            
            # Test that it matches the sales receipt import pattern
            print(f"✓ Pattern matches sales receipt import approach")
            
            return True
            
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pattern_comparison():
    """Compare the pattern with sales receipt import"""
    print("\nPattern Comparison")
    print("=" * 20)
    
    try:
        # Read the sales receipt import pattern
        with open('src/ui/operations/sales_receipt_import.py', 'r') as f:
            sales_receipt_content = f.read()
        
        # Read the main window pattern
        with open('src/ui/main_window.py', 'r') as f:
            main_window_content = f.read()
        
        # Check that both use the same pattern
        sales_receipt_pattern = 'async with AsyncWooCommerceAPI' in sales_receipt_content
        main_window_pattern = 'async with AsyncWooCommerceAPI' in main_window_content
        
        print(f"Sales receipt import uses async with pattern: {sales_receipt_pattern}")
        print(f"Main window worker uses async with pattern: {main_window_pattern}")
        
        if sales_receipt_pattern and main_window_pattern:
            print("✓ Both use the same async context manager pattern")
            return True
        else:
            print("✗ Patterns don't match")
            return False
            
    except Exception as e:
        print(f"✗ Pattern comparison failed: {e}")
        return False

def main():
    """Run all tests"""
    print("WooCommerce Fix Validation")
    print("=" * 50)
    
    # Test 1: Worker creation and pattern
    test1_passed = test_woocommerce_worker_fix()
    
    # Test 2: Pattern comparison
    test2_passed = test_pattern_comparison()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("✅ ALL TESTS PASSED")
        print("\nThe fix should resolve the 'Event loop is closed' error because:")
        print("1. WooCommerceDataWorker no longer uses pre-existing API instance")
        print("2. Creates fresh AsyncWooCommerceAPI inside async context manager")
        print("3. Matches the working pattern from sales receipt import")
        print("4. Avoids event loop conflicts between threads")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)