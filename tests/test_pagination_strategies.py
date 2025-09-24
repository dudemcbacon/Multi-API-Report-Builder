#!/usr/bin/env python3
"""
Test script to explore different pagination strategies for WooPayments API
Tests various approaches to optimize data fetching
"""
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from woocommerce import API

# WooCommerce API credentials
CONSUMER_KEY = "ck_EXAMPLE1234567890abcdefghijklmnop"
CONSUMER_SECRET = "cs_EXAMPLE0987654321zyxwvutsrqponmlk"
STORE_URL = "https://shop.company.com"

def create_api():
    """Create API instance"""
    return API(
        url=STORE_URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version="wc/v3",
        timeout=30,
        query_string_auth=True
    )

def test_pagination_strategies():
    """Test different pagination strategies"""
    
    print("="*80)
    print("WooPayments API Pagination Strategies Test")
    print("Comparing different approaches to fetch all data efficiently")
    print("="*80)
    
    # Base parameters
    base_params = {
        'date_after': '2025-05-01 00:00:00',
        'date_before': '2025-05-31 23:59:59'
    }
    
    # Strategy 1: Sequential pagination (current approach)
    print(f"\n{'-'*60}")
    print("STRATEGY 1: Sequential Pagination (Current)")
    print(f"{'-'*60}")
    
    api = create_api()
    start_time = time.time()
    all_transactions = []
    page = 1
    
    while True:
        params = base_params.copy()
        params['page'] = page
        params['per_page'] = 25
        
        try:
            response = api.get("payments/reports/transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                all_transactions.extend(data)
                print(f"   Page {page}: {len(data)} records")
                if len(data) < 25:
                    break
                page += 1
            else:
                print(f"   Page {page} failed: {response.status_code}")
                break
        except Exception as e:
            print(f"   Error: {e}")
            break
    
    sequential_time = time.time() - start_time
    print(f"\n   Total: {len(all_transactions)} records in {sequential_time:.2f} seconds")
    print(f"   Rate: {len(all_transactions)/sequential_time:.1f} records/second")
    
    # Strategy 2: Parallel page fetching
    print(f"\n{'-'*60}")
    print("STRATEGY 2: Parallel Page Fetching")
    print(f"{'-'*60}")
    
    def fetch_page(page_num):
        """Fetch a single page"""
        api_instance = create_api()
        params = base_params.copy()
        params['page'] = page_num
        params['per_page'] = 25
        
        try:
            response = api_instance.get("payments/reports/transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                return page_num, data
            else:
                return page_num, None
        except Exception as e:
            print(f"   Page {page_num} error: {e}")
            return page_num, None
    
    start_time = time.time()
    all_transactions_parallel = []
    
    # First, get page 1 to determine if we need more pages
    page1_data = fetch_page(1)
    if page1_data[1]:
        all_transactions_parallel.extend(page1_data[1])
        print(f"   Page 1: {len(page1_data[1])} records")
        
        if len(page1_data[1]) == 25:
            # Fetch pages 2-6 in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(fetch_page, i): i for i in range(2, 7)}
                
                for future in as_completed(futures):
                    page_num, data = future.result()
                    if data:
                        all_transactions_parallel.extend(data)
                        print(f"   Page {page_num}: {len(data)} records")
                        if len(data) < 25:
                            break
    
    parallel_time = time.time() - start_time
    print(f"\n   Total: {len(all_transactions_parallel)} records in {parallel_time:.2f} seconds")
    print(f"   Rate: {len(all_transactions_parallel)/parallel_time:.1f} records/second")
    
    # Strategy 3: Try different parameter names
    print(f"\n{'-'*60}")
    print("STRATEGY 3: Alternative Parameter Names")
    print(f"{'-'*60}")
    
    alternative_params = [
        {'limit': 100, 'offset': 0},
        {'pagesize': 100, 'page': 1},
        {'page_size': 100, 'page': 1},
        {'count': 100, 'page': 1},
        {'max_results': 100, 'page': 1}
    ]
    
    api = create_api()
    
    for alt_params in alternative_params:
        params = base_params.copy()
        params.update(alt_params)
        
        param_str = ', '.join(f"{k}={v}" for k, v in alt_params.items())
        print(f"\n   Testing: {param_str}")
        
        try:
            response = api.get("payments/reports/transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS: {len(data)} records returned")
                if len(data) > 25:
                    print(f"   🎉 FOUND WORKING PARAMETER! Got more than 25 records!")
            else:
                print(f"   ❌ Failed: Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Strategy 4: Check for bulk/batch endpoints
    print(f"\n{'-'*60}")
    print("STRATEGY 4: Alternative Endpoints")
    print(f"{'-'*60}")
    
    alternative_endpoints = [
        "payments/transactions",
        "payments/reports/transactions/batch",
        "payments/bulk/transactions",
        "payments/export/transactions",
        "reports/payments/transactions"
    ]
    
    for endpoint in alternative_endpoints:
        print(f"\n   Testing endpoint: {endpoint}")
        
        params = base_params.copy()
        params['per_page'] = 100
        params['page'] = 1
        
        try:
            response = api.get(endpoint, params=params)
            if response.status_code == 200:
                data = response.json()
                # Handle different response structures
                if isinstance(data, dict) and 'data' in data:
                    count = len(data['data'])
                elif isinstance(data, list):
                    count = len(data)
                else:
                    count = 0
                
                print(f"   ✅ Endpoint exists! Got {count} records")
                if count > 25:
                    print(f"   🎉 SUPPORTS LARGER PAGE SIZE!")
            else:
                print(f"   ❌ Status {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
    
    # Results Summary
    print(f"\n{'='*80}")
    print("STRATEGY COMPARISON")
    print(f"{'='*80}")
    
    print(f"\n📊 Performance Results:")
    print(f"   Sequential (25/page):  {sequential_time:.2f}s ({len(all_transactions)/sequential_time:.1f} rec/s)")
    print(f"   Parallel (25/page):    {parallel_time:.2f}s ({len(all_transactions_parallel)/parallel_time:.1f} rec/s)")
    
    improvement = ((sequential_time - parallel_time) / sequential_time) * 100
    print(f"   Parallel improvement:  {improvement:.1f}% faster")
    
    print(f"\n💡 RECOMMENDATIONS:")
    
    if improvement > 20:
        print("   ✅ Implement parallel fetching for significant speedup")
        print(f"   - {improvement:.1f}% performance improvement")
        print("   - Especially beneficial for large date ranges")
    else:
        print("   ⚠️  Parallel fetching provides minimal benefit")
        print("   - Consider only for very large datasets")
    
    print("\n   Next steps:")
    print("   1. Run test_woopayments_page_sizes.py to confirm 25-record limit")
    print("   2. If limit confirmed, implement parallel fetching")
    print("   3. Otherwise, increase per_page parameter")

if __name__ == "__main__":
    test_pagination_strategies()