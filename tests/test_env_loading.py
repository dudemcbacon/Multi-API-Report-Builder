#!/usr/bin/env python3
"""
Test script to verify environment variable loading works correctly
"""
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_env_loading():
    """Test that all API files properly load environment variables"""
    
    print("Testing Environment Variable Loading")
    print("=" * 60)
    
    # Test basic .env file loading
    print("\n1. Testing direct .env file loading...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("[OK] dotenv available and loaded")
    except ImportError:
        print("[ERROR] dotenv not available")
        return False
    
    # Test Avalara credentials
    print("\n2. Testing Avalara credentials from .env...")
    avalara_account_id = os.getenv('AVALARA_ACCOUNT_ID')
    avalara_license_key = os.getenv('AVALARA_LICENSE_KEY')
    avalara_environment = os.getenv('AVALARA_ENVIRONMENT')
    
    print(f"AVALARA_ACCOUNT_ID: {avalara_account_id}")
    print(f"AVALARA_LICENSE_KEY: {'*' * len(avalara_license_key) if avalara_license_key else 'None'}")
    print(f"AVALARA_ENVIRONMENT: {avalara_environment}")
    
    # Test WooCommerce credentials
    print("\n3. Testing WooCommerce credentials from .env...")
    woo_consumer_key = os.getenv('WOO_CONSUMER_KEY')
    woo_consumer_secret = os.getenv('WOO_CONSUMER_SECRET')
    woo_store_url = os.getenv('WOO_STORE_URL')
    
    print(f"WOO_CONSUMER_KEY: {'*' * len(woo_consumer_key) if woo_consumer_key else 'None'}")
    print(f"WOO_CONSUMER_SECRET: {'*' * len(woo_consumer_secret) if woo_consumer_secret else 'None'}")
    print(f"WOO_STORE_URL: {woo_store_url}")
    
    # Test Salesforce credentials
    print("\n4. Testing Salesforce credentials from .env...")
    sf_consumer_key = os.getenv('SF_CONSUMER_KEY')
    sf_consumer_secret = os.getenv('SF_CONSUMER_SECRET')
    
    print(f"SF_CONSUMER_KEY: {'*' * len(sf_consumer_key) if sf_consumer_key else 'None'}")
    print(f"SF_CONSUMER_SECRET: {'*' * len(sf_consumer_secret) if sf_consumer_secret else 'None'}")
    
    # Test importing API modules
    print("\n5. Testing API module imports...")
    
    try:
        from services.async_avalara_api import AsyncAvalaraAPI
        api = AsyncAvalaraAPI()
        print(f"[OK] AsyncAvalaraAPI imported successfully")
        print(f"   - ACCOUNT_ID: {api.ACCOUNT_ID}")
        print(f"   - LICENSE_KEY: {'*' * len(api.LICENSE_KEY) if api.LICENSE_KEY else 'None'}")
        print(f"   - ENVIRONMENT: {api.ENVIRONMENT}")
    except Exception as e:
        print(f"[ERROR] AsyncAvalaraAPI import failed: {e}")
    
    try:
        from services.async_woocommerce_api import AsyncWooCommerceAPI
        api = AsyncWooCommerceAPI()
        print(f"[OK] AsyncWooCommerceAPI imported successfully")
        print(f"   - CONSUMER_KEY: {'*' * len(api.CONSUMER_KEY) if api.CONSUMER_KEY else 'None'}")
        print(f"   - CONSUMER_SECRET: {'*' * len(api.CONSUMER_SECRET) if api.CONSUMER_SECRET else 'None'}")
        print(f"   - STORE_URL: {api.STORE_URL}")
    except Exception as e:
        print(f"[ERROR] AsyncWooCommerceAPI import failed: {e}")
    
    try:
        from services.auth_manager import SalesforceAuthManager
        auth_manager = SalesforceAuthManager()
        print(f"[OK] SalesforceAuthManager imported successfully")
        print(f"   - CONSUMER_KEY: {'*' * len(auth_manager.CONSUMER_KEY) if auth_manager.CONSUMER_KEY else 'None'}")
    except Exception as e:
        print(f"[ERROR] SalesforceAuthManager import failed: {e}")
    
    print("\n[OK] Environment variable loading test completed!")
    return True

if __name__ == "__main__":
    success = test_env_loading()
    sys.exit(0 if success else 1)