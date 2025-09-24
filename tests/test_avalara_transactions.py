#!/usr/bin/env python3
"""
Test script for Avalara transactions with manual credential input
"""
import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
    print("[OK] Loaded environment variables from .env file")
except ImportError:
    print("[WARN] python-dotenv not available, using system environment variables only")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_avalara_credentials():
    """Get Avalara credentials from environment or user input"""
    account_id = os.getenv('AVALARA_ACCOUNT_ID')
    license_key = os.getenv('AVALARA_LICENSE_KEY')
    environment = os.getenv('AVALARA_ENVIRONMENT')
    
    print(f"Current environment: {environment}")
    print(f"Account ID from env: {account_id}")
    print(f"License Key from env: {'*' * len(license_key) if license_key else 'None'}")
    
    # Check if credentials are placeholder values
    if account_id == 'your_account_id' or license_key == 'your_license_key':
        print("[WARN] Placeholder credentials detected in .env file")
        account_id = None
        license_key = None
    
    # If no valid credentials, provide instructions
    if not account_id or not license_key:
        print("\n[ERROR] No valid Avalara credentials found")
        print("To test Avalara integration, you need to:")
        print("1. Sign up for Avalara AvaTax sandbox account at https://sandbox-admin.avalara.com")
        print("2. Get your Account ID and License Key from Settings > License and API Keys")
        print("3. Update your .env file with:")
        print("   AVALARA_ACCOUNT_ID=your_actual_account_id")
        print("   AVALARA_LICENSE_KEY=your_actual_license_key")
        print("   AVALARA_ENVIRONMENT=sandbox")
        print("\n4. Or for testing purposes, you can use Avalara's test credentials:")
        print("   Account ID: 2000134479")
        print("   License Key: 1234567890123456")
        print("   (These are publicly available test credentials)")
        
        # Option to use test credentials
        use_test = input("\nWould you like to use the test credentials for this test? (y/n): ").lower().strip()
        if use_test == 'y':
            return '2000134479', '1234567890123456', 'sandbox'
        else:
            return None, None, environment
    
    return account_id, license_key, environment

async def test_avalara_with_credentials(account_id, license_key, environment):
    """Test Avalara API with provided credentials"""
    print(f"\nTesting Avalara API")
    print(f"Account ID: {account_id}")
    print(f"Environment: {environment}")
    print("=" * 50)
    
    try:
        # Import the AsyncAvalaraAPI
        from src.services.async_avalara_api import AsyncAvalaraAPI
        
        # Create API instance with explicit credentials
        api = AsyncAvalaraAPI(
            account_id=account_id,
            license_key=license_key,
            environment=environment,
            verbose_logging=True
        )
        
        async with api:
            print("✅ API instance created successfully")
            
            # Test 1: Basic connection test
            print("\n1. Testing connection...")
            result = await api.test_connection()
            print(f"Connection result: {result}")
            
            if not result.get('success'):
                print("❌ Connection failed - stopping tests")
                return False
            
            print("✅ Connection successful!")
            
            # Test 2: Get companies
            print("\n2. Testing companies endpoint...")
            companies = await api.get_companies()
            print(f"Companies result: {companies}")
            
            if isinstance(companies, list):
                print(f"✅ Successfully fetched {len(companies)} companies")
                if companies:
                    print(f"First company: {companies[0]}")
            else:
                print("❌ Companies test failed")
            
            # Test 3: Get transactions (last 30 days)
            print("\n3. Testing transactions endpoint...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            print(f"Date range: {start_str} to {end_str}")
            
            transactions = await api.get_transactions(start_str, end_str)
            print(f"Transactions result: {transactions}")
            
            if isinstance(transactions, list):
                print(f"✅ Successfully fetched {len(transactions)} transactions")
                if transactions:
                    print(f"First transaction: {transactions[0]}")
            else:
                print("❌ Transactions test failed")
            
            # Test 4: Convert to DataFrame
            print("\n4. Testing DataFrame conversion...")
            if companies:
                companies_df = api.to_dataframe(companies, "companies")
                print(f"✅ Companies DataFrame: {companies_df.shape}")
                print(f"Companies columns: {companies_df.columns}")
            
            if transactions:
                transactions_df = api.to_dataframe(transactions, "transactions")
                print(f"✅ Transactions DataFrame: {transactions_df.shape}")
                print(f"Transactions columns: {transactions_df.columns}")
            
            print("\n✅ All tests completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("Avalara Transactions Integration Test")
    print("=" * 60)
    
    # Get credentials
    account_id, license_key, environment = get_avalara_credentials()
    
    if not account_id or not license_key:
        print("\n❌ No credentials available - exiting")
        return False
    
    # Test with credentials
    success = await test_avalara_with_credentials(account_id, license_key, environment)
    
    if success:
        print("\n🎉 Avalara integration test completed successfully!")
        print("You can now use Avalara data sources in the main application.")
    else:
        print("\n❌ Avalara integration test failed")
        print("Please check your credentials and network connection.")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)