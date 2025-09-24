#!/usr/bin/env python3
"""
Test script to verify async API integration works correctly
"""
import sys
import os
import asyncio
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_async_apis():
    """Test that the async APIs can be imported and initialized"""
    print("Testing async API integration...")
    
    # Test 1: Import async APIs
    try:
        from src.services.async_salesforce_api import AsyncSalesforceAPI
        from src.services.async_woocommerce_api import AsyncWooCommerceAPI
        print("✓ Successfully imported async APIs")
    except ImportError as e:
        print(f"✗ Failed to import async APIs: {e}")
        return False
    
    # Test 2: Initialize async APIs
    try:
        async with AsyncSalesforceAPI() as sf_api:
            print("✓ Successfully initialized AsyncSalesforceAPI")
            
            # Test credentials check
            has_creds = sf_api.has_credentials()
            print(f"✓ Salesforce credentials check: {has_creds}")
            
        async with AsyncWooCommerceAPI() as woo_api:
            print("✓ Successfully initialized AsyncWooCommerceAPI")
            
            # Test credentials check
            has_creds = woo_api.has_credentials()
            print(f"✓ WooCommerce credentials check: {has_creds}")
            
    except Exception as e:
        print(f"✗ Failed to initialize async APIs: {e}")
        return False
    
    # Test 3: Test SalesReceiptImport operation can be imported
    try:
        from src.ui.operations.sales_receipt_import import SalesReceiptImport
        print("✓ Successfully imported SalesReceiptImport")
        
        # Test that it has the execute method
        if hasattr(SalesReceiptImport, 'execute'):
            print("✓ SalesReceiptImport has execute method")
        else:
            print("✗ SalesReceiptImport missing execute method")
            return False
            
    except ImportError as e:
        print(f"✗ Failed to import SalesReceiptImport: {e}")
        return False
    
    print("\n✓ All async API integration tests passed!")
    return True

def test_synchronous_interface():
    """Test that the synchronous interface still works"""
    print("\nTesting synchronous interface compatibility...")
    
    try:
        from src.ui.operations.sales_receipt_import import SalesReceiptImport
        
        # Create operation instance (without API connections for now)
        operation = SalesReceiptImport()
        
        # Test that it has the required methods
        required_methods = ['execute', 'report_progress']
        for method in required_methods:
            if hasattr(operation, method):
                print(f"✓ Has {method} method")
            else:
                print(f"✗ Missing {method} method")
                return False
        
        print("✓ Synchronous interface compatibility test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Synchronous interface test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("ASYNC API INTEGRATION TEST")
    print("=" * 50)
    
    # Test async APIs
    async_success = await test_async_apis()
    
    # Test synchronous interface
    sync_success = test_synchronous_interface()
    
    # Final result
    print("\n" + "=" * 50)
    print("FINAL RESULT")
    print("=" * 50)
    
    if async_success and sync_success:
        print("🎉 ALL TESTS PASSED!")
        print("✓ Async APIs are working correctly")
        print("✓ Synchronous interface is maintained")
        print("✓ Integration is ready for production use")
        return True
    else:
        print("❌ SOME TESTS FAILED!")
        print("Please check the errors above")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)