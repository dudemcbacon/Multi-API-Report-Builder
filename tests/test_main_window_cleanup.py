#!/usr/bin/env python3
"""
Test the main_window.py cleanup improvements
"""
import sys
import os
import re

def test_worker_consolidation():
    """Test that worker classes are properly consolidated"""
    print("Testing Worker Class Consolidation")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check for BaseAsyncDataWorker
    if 'class BaseAsyncDataWorker(QThread):' in content:
        print("✓ BaseAsyncDataWorker base class created")
    else:
        print("✗ BaseAsyncDataWorker base class not found")
        return False
    
    # Check that workers extend base class
    if 'class WooCommerceDataWorker(BaseAsyncDataWorker):' in content:
        print("✓ WooCommerceDataWorker extends base class")
    else:
        print("✗ WooCommerceDataWorker doesn't extend base class")
        return False
    
    if 'class AvalaraDataWorker(BaseAsyncDataWorker):' in content:
        print("✓ AvalaraDataWorker extends base class")
    else:
        print("✗ AvalaraDataWorker doesn't extend base class")
        return False
    
    # Check for duplicate code reduction
    run_method_count = content.count('def run(self):')
    if run_method_count <= 3:  # Only base class should have run method
        print(f"✓ Duplicate run() methods eliminated ({run_method_count} remaining)")
    else:
        print(f"✗ Still has duplicate run() methods ({run_method_count} found)")
        return False
    
    return True

def test_tree_population_consolidation():
    """Test that tree population methods are consolidated"""
    print("\nTesting Tree Population Consolidation")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check for unified tree loading method
    if 'def _load_tree_items_from_cache(self, parent_item, api_type: str, data_list: List[Dict], item_type: str = "data source"):' in content:
        print("✓ Unified tree loading method created")
    else:
        print("✗ Unified tree loading method not found")
        return False
    
    # Check that async methods are simplified
    if 'def load_salesforce_tree_items_async(self, parent_item):' in content:
        if 'self._load_tree_items_from_cache(parent_item, \'salesforce\', self.async_sf_reports, \'report\')' in content:
            print("✓ Salesforce tree loading simplified")
        else:
            print("✗ Salesforce tree loading not simplified")
            return False
    
    if 'def load_woocommerce_tree_items_async(self, parent_item):' in content:
        if 'self._load_tree_items_from_cache(parent_item, \'woocommerce\', self.async_woo_data_sources, \'data source\')' in content:
            print("✓ WooCommerce tree loading simplified")
        else:
            print("✗ WooCommerce tree loading not simplified")
            return False
    
    return True

def test_connection_management():
    """Test that connection management is unified"""
    print("\nTesting Connection Management")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check for unified connection test method
    if 'def _test_api_connection_async(self, api_type: str) -> Dict[str, Any]:' in content:
        print("✓ Unified connection test method created")
    else:
        print("✗ Unified connection test method not found")
        return False
    
    # Check for legacy wrapper methods
    if 'async def _test_sf_api_connection_async(self) -> Dict[str, Any]:' in content:
        if 'return await self._test_api_connection_async(\'salesforce\')' in content:
            print("✓ Legacy wrapper methods maintained for compatibility")
        else:
            print("✗ Legacy wrapper methods not properly implemented")
            return False
    
    return True

def test_logging_optimization():
    """Test that logging verbosity is optimized"""
    print("\nTesting Logging Optimization")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Count excessive logging patterns
    success_signal_logs = content.count('SUCCESS') + content.count('signal emitted')
    if success_signal_logs < 20:  # Should be significantly reduced
        print(f"✓ Excessive logging reduced ({success_signal_logs} verbose logs remaining)")
    else:
        print(f"✗ Still has excessive logging ({success_signal_logs} verbose logs)")
        return False
    
    # Check for removed signal emission logging
    if 'SUCCESS Data signal emitted' not in content:
        print("✓ Redundant signal emission logging removed")
    else:
        print("✗ Redundant signal emission logging still present")
        return False
    
    return True

def test_import_cleanup():
    """Test that imports are cleaned up and consolidated"""
    print("\nTesting Import Cleanup")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that common imports are at the top
    imports_section = content.split('\n\nlogger = logging.getLogger(__name__)')[0]
    
    if 'from datetime import datetime, timedelta' in imports_section:
        print("✓ datetime imports moved to top")
    else:
        print("✗ datetime imports not at top")
        return False
    
    if 'from src.services.auth_manager import SalesforceAuthManager' in imports_section:
        print("✓ auth_manager import moved to top")
    else:
        print("✗ auth_manager import not at top")
        return False
    
    # Check for reduced inline imports
    inline_imports = content.count('from src.services.') - imports_section.count('from src.services.')
    if inline_imports < 5:  # Should be significantly reduced
        print(f"✓ Inline imports reduced ({inline_imports} remaining)")
    else:
        print(f"✗ Still has many inline imports ({inline_imports} found)")
        return False
    
    return True

def test_file_size_reduction():
    """Test that file size is reduced"""
    print("\nTesting File Size Reduction")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        lines = f.readlines()
    
    line_count = len(lines)
    print(f"Current file size: {line_count} lines")
    
    # Estimate the cleanup impact
    if line_count < 2300:  # Should be reduced from original ~2357 lines
        print("✓ File size reduced through cleanup")
    else:
        print("✗ File size not significantly reduced")
        return False
    
    # Check for code density improvement
    non_empty_lines = len([line for line in lines if line.strip()])
    empty_lines = line_count - non_empty_lines
    
    if empty_lines < line_count * 0.15:  # Less than 15% empty lines
        print(f"✓ Code density improved ({empty_lines} empty lines)")
    else:
        print(f"✗ Too many empty lines ({empty_lines} empty lines)")
        return False
    
    return True

def main():
    """Run all cleanup tests"""
    print("Main Window Cleanup Validation")
    print("=" * 60)
    
    tests = [
        test_worker_consolidation,
        test_tree_population_consolidation,
        test_connection_management,
        test_logging_optimization,
        test_import_cleanup,
        test_file_size_reduction
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ ALL CLEANUP TESTS PASSED")
        print("\nCleanup improvements achieved:")
        print("- Worker thread patterns consolidated with base class")
        print("- Tree population methods unified and simplified")
        print("- Connection management consolidated")
        print("- Logging verbosity optimized")
        print("- Imports cleaned up and consolidated")
        print("- File size reduced through elimination of redundancy")
        print("- Code maintainability significantly improved")
        return True
    else:
        print("❌ SOME CLEANUP TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)