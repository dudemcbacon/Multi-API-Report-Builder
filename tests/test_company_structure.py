#!/usr/bin/env python3
"""
Test to see the company structure from Avalara API
"""
import os
import sys
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_company_structure():
    """Test to see the full company object structure"""
    
    print("Testing Avalara Company Structure")
    print("=" * 60)
    
    from services.async_avalara_api import AsyncAvalaraAPI
    
    try:
        async with AsyncAvalaraAPI(verbose_logging=True) as api:
            print(f"\n1. Getting Companies...")
            companies = await api.get_companies()
            print(f"   - companies found: {len(companies)}")
            
            if companies:
                print(f"\n2. First Company Details:")
                company = companies[0]
                for key, value in company.items():
                    print(f"   - {key}: {value}")
                
                return True
            else:
                print("   - No companies found")
                return False
                
    except Exception as e:
        print(f"\nException: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_company_structure())
    sys.exit(0 if success else 1)