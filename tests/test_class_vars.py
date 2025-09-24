#!/usr/bin/env python3
"""
Test to check class-level variables in AsyncAvalaraAPI
"""
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_class_variables():
    """Test the class-level environment variables"""
    
    print("Testing AsyncAvalaraAPI class-level variables")
    print("=" * 60)
    
    # Check environment variables directly
    print("\n1. Direct environment variable check:")
    print(f"AVALARA_ACCOUNT_ID: {os.getenv('AVALARA_ACCOUNT_ID')}")
    print(f"AVALARA_LICENSE_KEY: {'*' * len(os.getenv('AVALARA_LICENSE_KEY')) if os.getenv('AVALARA_LICENSE_KEY') else 'None'}")
    print(f"AVALARA_ENVIRONMENT: {os.getenv('AVALARA_ENVIRONMENT')}")
    
    # Import and check class variables
    print("\n2. Importing AsyncAvalaraAPI...")
    from services.async_avalara_api import AsyncAvalaraAPI
    
    print("\n3. Class-level variables:")
    print(f"AsyncAvalaraAPI.ACCOUNT_ID: {AsyncAvalaraAPI.ACCOUNT_ID}")
    print(f"AsyncAvalaraAPI.LICENSE_KEY: {'*' * len(AsyncAvalaraAPI.LICENSE_KEY) if AsyncAvalaraAPI.LICENSE_KEY else 'None'}")
    print(f"AsyncAvalaraAPI.ENVIRONMENT: {AsyncAvalaraAPI.ENVIRONMENT}")
    
    # Test fresh instance (like the UI does)
    print("\n4. Creating fresh instance (like UI does):")
    fresh_api = AsyncAvalaraAPI(verbose_logging=False)
    print(f"fresh_api.account_id: {fresh_api.account_id}")
    print(f"fresh_api.license_key: {'*' * len(fresh_api.license_key) if fresh_api.license_key else 'None'}")
    print(f"fresh_api.environment: {fresh_api.environment}")
    
    # Check if credentials are available
    has_credentials = bool(fresh_api.account_id and fresh_api.license_key)
    print(f"\n5. Fresh instance has credentials: {has_credentials}")
    
    return has_credentials

if __name__ == "__main__":
    success = test_class_variables()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)