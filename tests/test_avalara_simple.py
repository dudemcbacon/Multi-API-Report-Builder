#!/usr/bin/env python3
"""
Simple test script for Avalara API authentication
"""
import os
import base64
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available, using system environment variables only")

def test_env_credentials():
    """Test environment variable setup"""
    print("🔍 Checking Avalara Environment Variables")
    print("=" * 50)
    
    account_id = os.getenv('AVALARA_ACCOUNT_ID')
    license_key = os.getenv('AVALARA_LICENSE_KEY')
    environment = os.getenv('AVALARA_ENVIRONMENT', 'sandbox')
    
    print(f"Account ID: {account_id}")
    print(f"License Key: {'*' * len(license_key) if license_key else 'None'}")
    print(f"Environment: {environment}")
    
    if not account_id or not license_key:
        print("\n❌ ERROR: Missing Avalara credentials")
        print("Please set the following in your .env file:")
        print("AVALARA_ACCOUNT_ID=your_actual_account_id")
        print("AVALARA_LICENSE_KEY=your_actual_license_key")
        print("AVALARA_ENVIRONMENT=sandbox")
        return False
    
    if account_id == 'your_account_id' or license_key == 'your_license_key':
        print("\n❌ ERROR: Placeholder credentials detected")
        print("Please replace with actual credentials from your Avalara account")
        return False
    
    print("\n✅ Environment variables are set")
    return True

def test_auth_format():
    """Test authentication format"""
    print("\n🔍 Testing Authentication Format")
    print("=" * 50)
    
    account_id = os.getenv('AVALARA_ACCOUNT_ID')
    license_key = os.getenv('AVALARA_LICENSE_KEY')
    
    if not account_id or not license_key:
        print("❌ Skipping - no credentials")
        return False
    
    # Test base64 encoding
    auth_string = f"{account_id}:{license_key}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    print(f"Auth string length: {len(auth_string)}")
    print(f"Base64 encoded: {auth_b64[:20]}...")
    
    # Test that it's valid base64
    try:
        decoded = base64.b64decode(auth_b64).decode('ascii')
        print("✅ Base64 encoding/decoding works")
        return True
    except Exception as e:
        print(f"❌ Base64 error: {e}")
        return False

def test_avalara_endpoints():
    """Test which Avalara endpoints to use"""
    print("\n🔍 Testing Avalara Endpoints")
    print("=" * 50)
    
    environment = os.getenv('AVALARA_ENVIRONMENT', 'sandbox')
    
    if environment.lower() == 'production':
        base_url = "https://rest.avatax.com"
    else:
        base_url = "https://sandbox-rest.avatax.com"
    
    api_url = f"{base_url}/api/v2"
    
    print(f"Environment: {environment}")
    print(f"Base URL: {base_url}")
    print(f"API URL: {api_url}")
    
    endpoints = [
        "/utilities/ping",
        "/accounts",
        "/companies",
        "/transactions",
        "/definitions/taxcodes",
        "/definitions/jurisdictions"
    ]
    
    print("\nAvailable endpoints:")
    for endpoint in endpoints:
        print(f"  {api_url}{endpoint}")
    
    return True

def provide_setup_instructions():
    """Provide setup instructions"""
    print("\n📋 Avalara Setup Instructions")
    print("=" * 50)
    
    print("1. Get Avalara Credentials:")
    print("   - For Sandbox: https://sandbox-admin.avalara.com")
    print("   - For Production: https://admin.avalara.com")
    print("   - Go to Settings > License and API Keys")
    print("   - Copy your Account ID and License Key")
    
    print("\n2. Update .env file:")
    print("   AVALARA_ACCOUNT_ID=your_actual_account_id")
    print("   AVALARA_LICENSE_KEY=your_actual_license_key")
    print("   AVALARA_ENVIRONMENT=sandbox")
    
    print("\n3. Test with curl (replace with your credentials):")
    print("   curl -u 'account_id:license_key' \\")
    print("        'https://sandbox-rest.avatax.com/api/v2/utilities/ping'")
    
    print("\n4. Expected response:")
    print("   {\"authenticated\": true, \"...\"}")

if __name__ == "__main__":
    print("🧪 Avalara API Setup Test")
    print("=" * 60)
    
    # Run tests
    tests = [
        test_env_credentials,
        test_auth_format,
        test_avalara_endpoints
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    if not all_passed:
        provide_setup_instructions()
    else:
        print("\n✅ All setup tests passed!")
        print("Your Avalara credentials appear to be configured correctly.")
        print("Try running the main application now.")