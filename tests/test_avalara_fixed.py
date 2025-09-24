#!/usr/bin/env python3
"""
Test the fixed Avalara API implementation
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_avalara_fixes():
    """Test both connection and transactions with fixes"""
    
    print("Testing Fixed Avalara API Implementation")
    print("=" * 60)
    
    from services.async_avalara_api import AsyncAvalaraAPI
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            print(f"\n1. API Instance Created:")
            print(f"   - account_id: {api.account_id}")
            print(f"   - environment: {api.environment}")
            print(f"   - base_url: {api.base_url}")
            
            print(f"\n2. Testing Connection...")
            connection_result = await api.test_connection()
            print(f"   - success: {connection_result.get('success', False)}")
            print(f"   - account_info: {connection_result.get('account_info', 'None')}")
            
            if connection_result.get('success'):
                print(f"\n3. Testing Companies...")
                companies = await api.get_companies()
                print(f"   - companies found: {len(companies)}")
                if companies:
                    print(f"   - first company: {companies[0].get('name', 'Unknown')} (ID: {companies[0].get('id', 'Unknown')})")
                
                print(f"\n4. Testing Transactions (last 30 days)...")
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                print(f"   - date range: {start_date} to {end_date}")
                
                transactions = await api.get_transactions(start_date, end_date)
                print(f"   - transactions found: {len(transactions)}")
                if transactions:
                    print(f"   - first transaction: {transactions[0]}")
                
                return True
            else:
                print("   - Connection failed, skipping other tests")
                return False
                
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_avalara_fixes())
    print(f"\nTest Result: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)