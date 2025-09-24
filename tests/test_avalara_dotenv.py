#!/usr/bin/env python3
"""
Test specifically for async_avalara_api.py dotenv loading
"""
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_avalara_dotenv():
    """Test that async_avalara_api.py properly loads environment variables"""
    
    print("Testing async_avalara_api.py dotenv loading")
    print("=" * 60)
    
    # Check environment variables before import
    print("\n1. Environment variables before importing async_avalara_api:")
    print(f"AVALARA_ACCOUNT_ID: {os.getenv('AVALARA_ACCOUNT_ID')}")
    print(f"AVALARA_LICENSE_KEY: {'*' * len(os.getenv('AVALARA_LICENSE_KEY')) if os.getenv('AVALARA_LICENSE_KEY') else 'None'}")
    print(f"AVALARA_ENVIRONMENT: {os.getenv('AVALARA_ENVIRONMENT')}")
    
    # Import the module
    print("\n2. Importing async_avalara_api module...")
    try:
        from services.async_avalara_api import AsyncAvalaraAPI
        print("[OK] Module imported successfully")
    except Exception as e:
        print(f"[ERROR] Module import failed: {e}")
        return False
    
    # Check class-level variables
    print("\n3. Checking class-level environment variables:")
    print(f"AsyncAvalaraAPI.ACCOUNT_ID: {AsyncAvalaraAPI.ACCOUNT_ID}")
    print(f"AsyncAvalaraAPI.LICENSE_KEY: {'*' * len(AsyncAvalaraAPI.LICENSE_KEY) if AsyncAvalaraAPI.LICENSE_KEY else 'None'}")
    print(f"AsyncAvalaraAPI.ENVIRONMENT: {AsyncAvalaraAPI.ENVIRONMENT}")
    
    # Create instance
    print("\n4. Creating API instance...")
    try:
        api = AsyncAvalaraAPI(verbose_logging=True)
        print("[OK] API instance created successfully")
        print(f"   - account_id: {api.account_id}")
        print(f"   - license_key: {'*' * len(api.license_key) if api.license_key else 'None'}")
        print(f"   - environment: {api.environment}")
        print(f"   - base_url: {api.base_url}")
    except Exception as e:
        print(f"[ERROR] API instance creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Check if credentials are loaded
    if api.account_id and api.license_key:
        print("\n[OK] Credentials successfully loaded from environment variables!")
        return True
    else:
        print("\n[ERROR] Credentials not loaded properly")
        print(f"Missing: account_id={bool(api.account_id)}, license_key={bool(api.license_key)}")
        return False

if __name__ == "__main__":
    success = test_avalara_dotenv()
    sys.exit(0 if success else 1)