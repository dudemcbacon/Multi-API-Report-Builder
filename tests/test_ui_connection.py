#!/usr/bin/env python3
"""
Test to mimic exactly what the UI is doing for Avalara connection
"""
import os
import sys
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_ui_connection():
    """Test the exact same async connection that the UI uses"""
    
    print("Testing UI Avalara connection (exact same code)")
    print("=" * 60)
    
    # Import the module
    from services.async_avalara_api import AsyncAvalaraAPI
    
    print("\n1. Creating fresh AsyncAvalaraAPI instance (like UI does)...")
    
    # This is exactly what the UI does:
    async with AsyncAvalaraAPI(verbose_logging=True) as api:
        print(f"   - account_id: {api.account_id}")
        print(f"   - license_key: {'*' * len(api.license_key) if api.license_key else 'None'}")
        print(f"   - environment: {api.environment}")
        print(f"   - base_url: {api.base_url}")
        
        print("\n2. Testing connection...")
        result = await api.test_connection()
        
        print(f"\n3. Connection result:")
        print(f"   - success: {result.get('success', False)}")
        print(f"   - error: {result.get('error', 'None')}")
        print(f"   - details: {result.get('details', 'None')}")
        print(f"   - account_info: {result.get('account_info', 'None')}")
        print(f"   - environment: {result.get('environment', 'None')}")
        
        return result

async def main():
    """Main test function"""
    try:
        result = await test_ui_connection()
        success = result.get('success', False)
        print(f"\nFinal result: {'SUCCESS' if success else 'FAILED'}")
        return success
    except Exception as e:
        print(f"\nException occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)