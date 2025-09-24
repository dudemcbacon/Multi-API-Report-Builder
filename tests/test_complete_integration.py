#!/usr/bin/env python3
"""
Test the complete Avalara integration including data loading and UI format
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_complete_integration():
    """Test the complete Avalara integration flow"""
    
    print("Testing Complete Avalara Integration")
    print("=" * 60)
    
    try:
        from services.async_avalara_api import AsyncAvalaraAPI
        
        # Test both connection and data loading
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            print(f"\n1. Testing Connection...")
            connection_result = await api.test_connection()
            
            if not connection_result.get('success'):
                print(f"✗ Connection failed: {connection_result}")
                return False
            
            print(f"✓ Connection successful: {connection_result.get('account_info')}")
            
            print(f"\n2. Testing Company Retrieval...")
            companies = await api.get_companies()
            if not companies:
                print("✗ No companies found")
                return False
            
            print(f"✓ Found {len(companies)} companies")
            company = companies[0]
            print(f"  - Company: {company.get('name', 'Unknown')} (Code: {company.get('companyCode', 'N/A')})")
            
            print(f"\n3. Testing Transaction Loading (Last 30 Days)...")
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            print(f"  - Date range: {start_date} to {end_date}")
            
            transactions = await api.get_transactions(start_date, end_date)
            print(f"✓ Retrieved {len(transactions)} transactions")
            
            if transactions:
                print(f"  - Sample transaction keys: {list(transactions[0].keys())}")
                print(f"  - Sample transaction: {transactions[0]}")
            else:
                print("  - No transactions found (this may be normal for test accounts)")
            
            print(f"\n4. Testing DataFrame Conversion...")
            dataframe = api.to_dataframe(transactions, "transactions")
            print(f"✓ DataFrame created: {type(dataframe).__name__}")
            
            if hasattr(dataframe, 'shape'):
                print(f"  - Shape: {dataframe.shape}")
                if hasattr(dataframe, 'columns'):
                    print(f"  - Columns: {list(dataframe.columns)}")
            else:
                print(f"  - Length: {len(dataframe) if hasattr(dataframe, '__len__') else 'unknown'}")
            
            print(f"\n5. Testing Edge Cases...")
            
            # Test with different date ranges
            test_ranges = [
                # Future date (should return empty)
                ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), 
                 (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')),
                # Far past (should return empty)
                ('2020-01-01', '2020-01-02'),
            ]
            
            for test_start, test_end in test_ranges:
                test_transactions = await api.get_transactions(test_start, test_end)
                test_df = api.to_dataframe(test_transactions, "transactions")
                print(f"  - {test_start} to {test_end}: {len(test_transactions)} transactions -> DataFrame with {len(test_df) if hasattr(test_df, '__len__') else 'unknown'} rows")
            
            print(f"\n6. Testing Error Handling...")
            
            # Test invalid date format
            try:
                await api.get_transactions("invalid-date", "2024-01-01")
                print("✗ Should have failed with invalid date")
                return False
            except ValueError:
                print("✓ Correctly rejected invalid date format")
            except Exception as e:
                print(f"✓ Handled invalid date with exception: {type(e).__name__}")
            
            print(f"\n7. Integration Summary...")
            return {
                'connection': connection_result.get('success', False),
                'companies_found': len(companies),
                'transactions_found': len(transactions),
                'dataframe_created': dataframe is not None,
                'dataframe_type': type(dataframe).__name__,
                'dataframe_length': len(dataframe) if hasattr(dataframe, '__len__') else 0
            }
            
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("Avalara Integration Validation")
    print("=" * 40)
    
    try:
        result = await test_complete_integration()
        
        if isinstance(result, dict):
            print(f"\n" + "=" * 60)
            print("INTEGRATION TEST RESULTS:")
            print(f"  ✓ Connection: {result['connection']}")
            print(f"  ✓ Companies found: {result['companies_found']}")
            print(f"  ✓ Transactions found: {result['transactions_found']}")
            print(f"  ✓ DataFrame created: {result['dataframe_created']}")
            print(f"  ✓ DataFrame type: {result['dataframe_type']}")
            print(f"  ✓ DataFrame length: {result['dataframe_length']}")
            
            # Overall success criteria
            success = (result['connection'] and 
                      result['companies_found'] > 0 and 
                      result['dataframe_created'])
            
            print(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if success else '❌ FAILED'}")
            
            if success:
                print("\nThe Avalara integration is working correctly!")
                print("- ✅ Environment variables loaded")
                print("- ✅ API authentication successful") 
                print("- ✅ Company data retrieved")
                print("- ✅ Transaction endpoint working")
                print("- ✅ DataFrame conversion working")
                print("- ✅ Error handling implemented")
            
            return success
        else:
            print(f"\n❌ Integration test failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)