#!/usr/bin/env python3
"""
Test script for Avalara API integration
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.async_avalara_api import AsyncAvalaraAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_avalara_connection():
    """Test basic Avalara connection"""
    print("=" * 60)
    print("Testing Avalara API Connection")
    print("=" * 60)
    
    # Check environment variables
    account_id = os.getenv('AVALARA_ACCOUNT_ID')
    license_key = os.getenv('AVALARA_LICENSE_KEY')
    environment = os.getenv('AVALARA_ENVIRONMENT', 'sandbox')
    
    print(f"Account ID: {account_id}")
    print(f"License Key: {'*' * len(license_key) if license_key else 'None'}")
    print(f"Environment: {environment}")
    print()
    
    if not account_id or not license_key:
        print("❌ ERROR: Missing Avalara credentials in environment variables")
        print("Please set AVALARA_ACCOUNT_ID and AVALARA_LICENSE_KEY in your .env file")
        return False
    
    if account_id == 'your_account_id' or license_key == 'your_license_key':
        print("❌ ERROR: Avalara credentials are still set to placeholder values")
        print("Please update the .env file with your actual Avalara credentials")
        print("You can get these from your Avalara AvaTax account:")
        print("1. Go to https://sandbox-admin.avalara.com (for sandbox) or https://admin.avalara.com (for production)")
        print("2. Navigate to Settings > License and API Keys")
        print("3. Copy your Account ID and License Key")
        return False
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            print("✅ API instance created successfully")
            
            # Test connection
            result = await api.test_connection()
            print(f"Connection test result: {result}")
            
            if result.get('success'):
                print("✅ Connection successful!")
                return True
            else:
                print(f"❌ Connection failed: {result.get('error', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"❌ Exception during connection test: {e}")
        return False

async def test_avalara_companies():
    """Test fetching companies from Avalara"""
    print("=" * 60)
    print("Testing Avalara Companies API")
    print("=" * 60)
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            # Test companies endpoint
            companies = await api.get_companies()
            print(f"Companies result: {companies}")
            
            if isinstance(companies, list):
                print(f"✅ Successfully fetched {len(companies)} companies")
                if companies:
                    print(f"First company: {companies[0]}")
                return True
            else:
                print(f"❌ Expected list, got: {type(companies)}")
                return False
                
    except Exception as e:
        print(f"❌ Exception during companies test: {e}")
        return False

async def test_avalara_transactions():
    """Test fetching transactions from Avalara"""
    print("=" * 60)
    print("Testing Avalara Transactions API")
    print("=" * 60)
    
    # Use last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_str = start_date.strftime('%Y-%m-%d')
    end_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Date range: {start_str} to {end_str}")
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            # Test transactions endpoint
            transactions = await api.get_transactions(start_str, end_str)
            print(f"Transactions result type: {type(transactions)}")
            print(f"Transactions result: {transactions}")
            
            if isinstance(transactions, list):
                print(f"✅ Successfully fetched {len(transactions)} transactions")
                if transactions:
                    print(f"First transaction: {transactions[0]}")
                return True
            else:
                print(f"❌ Expected list, got: {type(transactions)}")
                return False
                
    except Exception as e:
        print(f"❌ Exception during transactions test: {e}")
        return False

async def test_avalara_tax_codes():
    """Test fetching tax codes from Avalara"""
    print("=" * 60)
    print("Testing Avalara Tax Codes API")
    print("=" * 60)
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            # Test tax codes endpoint
            tax_codes = await api.get_tax_codes()
            print(f"Tax codes result: {tax_codes}")
            
            if isinstance(tax_codes, list):
                print(f"✅ Successfully fetched {len(tax_codes)} tax codes")
                if tax_codes:
                    print(f"First tax code: {tax_codes[0]}")
                return True
            else:
                print(f"❌ Expected list, got: {type(tax_codes)}")
                return False
                
    except Exception as e:
        print(f"❌ Exception during tax codes test: {e}")
        return False

async def test_avalara_dataframe_conversion():
    """Test converting Avalara data to DataFrame"""
    print("=" * 60)
    print("Testing Avalara DataFrame Conversion")
    print("=" * 60)
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            # Test companies
            companies = await api.get_companies()
            if companies:
                companies_df = api.to_dataframe(companies, "companies")
                print(f"✅ Companies DataFrame: {companies_df.shape}")
                print(f"Companies columns: {companies_df.columns}")
            
            # Test transactions
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            start_str = start_date.strftime('%Y-%m-%d')
            end_str = end_date.strftime('%Y-%m-%d')
            
            transactions = await api.get_transactions(start_str, end_str)
            if transactions:
                transactions_df = api.to_dataframe(transactions, "transactions")
                print(f"✅ Transactions DataFrame: {transactions_df.shape}")
                print(f"Transactions columns: {transactions_df.columns}")
            
            return True
                
    except Exception as e:
        print(f"❌ Exception during DataFrame conversion test: {e}")
        return False

async def test_manual_auth():
    """Test manual authentication with explicit credentials"""
    print("=" * 60)
    print("Testing Manual Authentication")
    print("=" * 60)
    
    # Try with explicit credentials
    account_id = os.getenv('AVALARA_ACCOUNT_ID')
    license_key = os.getenv('AVALARA_LICENSE_KEY')
    
    if not account_id or not license_key:
        print("❌ Missing credentials")
        return False
    
    try:
        # Test with explicit parameters
        api = AsyncAvalaraAPI(
            account_id=account_id,
            license_key=license_key,
            environment='sandbox',
            verbose_logging=True
        )
        
        async with api:
            print("✅ Manual API instance created")
            
            # Test ping endpoint first
            result = await api._make_request('GET', '/utilities/ping')
            print(f"Ping result: {result}")
            
            # Test connection
            conn_result = await api.test_connection()
            print(f"Connection result: {conn_result}")
            
            return conn_result.get('success', False)
            
    except Exception as e:
        print(f"❌ Exception during manual auth test: {e}")
        return False

async def run_all_tests():
    """Run all Avalara tests"""
    print("🧪 Starting Avalara API Integration Tests")
    print("=" * 80)
    
    tests = [
        ("Connection Test", test_avalara_connection),
        ("Manual Auth Test", test_manual_auth),
        ("Companies Test", test_avalara_companies),
        ("Transactions Test", test_avalara_transactions),
        ("Tax Codes Test", test_avalara_tax_codes),
        ("DataFrame Conversion Test", test_avalara_dataframe_conversion)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n🔍 Running {test_name}...")
        try:
            success = await test_func()
            if success:
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                failed += 1
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs above.")
        return False

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Note: python-dotenv not installed, relying on system environment variables")
    
    # Run tests
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)