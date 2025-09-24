#!/usr/bin/env python3
"""
Verify WooCommerce fix by checking code patterns and syntax
"""
import sys
import os
import re

def verify_fix():
    """Verify the WooCommerce fix is correctly implemented"""
    print("Verifying WooCommerce Fix Implementation")
    print("=" * 50)
    
    # Check main_window.py
    with open('src/ui/main_window.py', 'r') as f:
        main_window_content = f.read()
    
    # Check sales_receipt_import.py
    with open('src/ui/operations/sales_receipt_import.py', 'r') as f:
        sales_receipt_content = f.read()
    
    print("1. Checking WooCommerceDataWorker constructor...")
    
    # Check that WooCommerceDataWorker __init__ only takes data_source
    init_pattern = r'def __init__\(self, data_source: Dict\[str, Any\]\):'
    if re.search(init_pattern, main_window_content):
        print("✓ WooCommerceDataWorker.__init__ correctly takes only data_source")
    else:
        print("✗ WooCommerceDataWorker.__init__ signature incorrect")
        return False
    
    print("2. Checking async context manager pattern...")
    
    # Check that _load_data_async uses async with pattern
    async_pattern = r'async with AsyncWooCommerceAPI.*as woo_api:'
    if re.search(async_pattern, main_window_content):
        print("✓ _load_data_async uses async with AsyncWooCommerceAPI pattern")
    else:
        print("✗ _load_data_async doesn't use async with pattern")
        return False
    
    print("3. Checking worker instantiation...")
    
    # Check that worker is created without woo_api parameter
    worker_pattern = r'self\.woo_worker = WooCommerceDataWorker\(data_source\)'
    if re.search(worker_pattern, main_window_content):
        print("✓ WooCommerceDataWorker instantiated correctly without woo_api")
    else:
        print("✗ WooCommerceDataWorker instantiation incorrect")
        return False
    
    print("4. Comparing with sales receipt import pattern...")
    
    # Both should use async with AsyncWooCommerceAPI
    both_use_pattern = (
        'async with AsyncWooCommerceAPI' in main_window_content and
        'async with AsyncWooCommerceAPI' in sales_receipt_content
    )
    
    if both_use_pattern:
        print("✓ Both files use the same async context manager pattern")
    else:
        print("✗ Patterns don't match between files")
        return False
    
    print("5. Checking for event loop issues...")
    
    # Check that no pre-existing API instance is passed
    no_api_passing = 'self.woo_api' not in re.search(r'class WooCommerceDataWorker.*?(?=class|\Z)', main_window_content, re.DOTALL).group()
    
    if no_api_passing:
        print("✓ No pre-existing API instance passed to worker")
    else:
        print("✗ Pre-existing API instance still being used")
        return False
    
    print("\n" + "=" * 50)
    print("✅ ALL CHECKS PASSED")
    print("\nSummary of the fix:")
    print("- WooCommerceDataWorker now creates fresh AsyncWooCommerceAPI instances")
    print("- Uses async context manager pattern like sales receipt import")
    print("- Avoids 'Event loop is closed' error from reusing API instances")
    print("- Worker creates new event loop and fresh API instance in that loop")
    print("- This matches the working pattern from sales receipt import")
    
    return True

if __name__ == "__main__":
    success = verify_fix()
    sys.exit(0 if success else 1)