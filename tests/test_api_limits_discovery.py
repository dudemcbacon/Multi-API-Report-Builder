#!/usr/bin/env python3
"""
Test script to systematically discover WooPayments API limits
Comprehensive testing of parameters and response analysis
"""
import sys
import json
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from woocommerce import API

# WooCommerce API credentials
CONSUMER_KEY = "ck_EXAMPLE1234567890abcdefghijklmnop"
CONSUMER_SECRET = "cs_EXAMPLE0987654321zyxwvutsrqponmlk"
STORE_URL = "https://shop.company.com"

def test_api_limits():
    """Systematically test API limits and capabilities"""
    
    api = API(
        url=STORE_URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version="wc/v3",
        timeout=30,
        query_string_auth=True
    )
    
    print("="*80)
    print("WooPayments API Limits Discovery")
    print("Systematic testing to find actual API capabilities")
    print("="*80)
    
    # Base parameters
    base_params = {
        'date_after': '2025-05-01 00:00:00',
        'date_before': '2025-05-31 23:59:59',
        'page': 1
    }
    
    # Test 1: Binary search for maximum per_page
    print(f"\n{'-'*60}")
    print("TEST 1: Binary Search for Maximum per_page")
    print(f"{'-'*60}")
    
    min_val = 1
    max_val = 500
    actual_limit = None
    
    while min_val <= max_val:
        mid = (min_val + max_val) // 2
        params = base_params.copy()
        params['per_page'] = mid
        
        print(f"\n   Testing per_page = {mid}")
        
        try:
            response = api.get("payments/reports/transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                actual_count = len(data)
                
                if actual_count < mid and actual_count > 0:
                    # Found the limit
                    actual_limit = actual_count
                    print(f"   ✅ Found limit! API returns max {actual_limit} records")
                    break
                elif actual_count == mid:
                    # Can go higher
                    print(f"   ✅ Got {actual_count} records, trying higher...")
                    min_val = mid + 1
                else:
                    print(f"   ⚠️  Unexpected: requested {mid}, got {actual_count}")
                    max_val = mid - 1
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                max_val = mid - 1
        except Exception as e:
            print(f"   ❌ Error: {e}")
            max_val = mid - 1
    
    if actual_limit:
        print(f"\n🎯 CONFIRMED: API limit is {actual_limit} records per page")
    
    # Test 2: Inspect response headers thoroughly
    print(f"\n{'-'*60}")
    print("TEST 2: Response Headers Analysis")
    print(f"{'-'*60}")
    
    params = base_params.copy()
    params['per_page'] = 50  # Try above expected limit
    
    try:
        response = api.get("payments/reports/transactions", params=params)
        headers = dict(response.headers)
        
        print("\n   All Response Headers:")
        for header, value in sorted(headers.items()):
            print(f"   {header}: {value}")
        
        # Look for specific headers
        print("\n   Key Headers:")
        important_headers = [
            'x-wp-total', 'x-wp-totalpages', 'link',
            'x-ratelimit-limit', 'x-ratelimit-remaining',
            'x-pagination-limit', 'x-max-results'
        ]
        
        for header in important_headers:
            for h, v in headers.items():
                if header in h.lower():
                    print(f"   ✓ {h}: {v}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: Test with explicit format parameters
    print(f"\n{'-'*60}")
    print("TEST 3: Format and Response Type Parameters")
    print(f"{'-'*60}")
    
    format_tests = [
        {'per_page': 100, 'format': 'json'},
        {'per_page': 100, 'response_type': 'full'},
        {'per_page': 100, 'include_all': 'true'},
        {'per_page': 100, 'no_limit': 'true'},
        {'per_page': 100, '_method': 'GET'},
        {'per_page': 100, 'v': '2'},  # Try API v2
    ]
    
    for test_params in format_tests:
        params = base_params.copy()
        params.update(test_params)
        
        param_str = ', '.join(f"{k}={v}" for k, v in test_params.items() if k != 'per_page')
        print(f"\n   Testing: per_page=100 with {param_str}")
        
        try:
            response = api.get("payments/reports/transactions", params=params)
            if response.status_code == 200:
                data = response.json()
                count = len(data)
                print(f"   Result: {count} records")
                if count > 25:
                    print(f"   🎉 SUCCESS! Got {count} records with these parameters!")
            else:
                print(f"   Failed: Status {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)[:50]}")
    
    # Test 4: Check WooCommerce vs WooPayments endpoints
    print(f"\n{'-'*60}")
    print("TEST 4: WooCommerce Core vs WooPayments Endpoints")
    print(f"{'-'*60}")
    
    # Test regular WooCommerce orders endpoint for comparison
    print("\n   Testing WooCommerce Orders endpoint (for comparison):")
    params = {
        'after': '2025-05-01T00:00:00',
        'before': '2025-05-31T23:59:59',
        'per_page': 100,
        'page': 1
    }
    
    try:
        response = api.get("orders", params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Orders endpoint: Got {len(data)} records with per_page=100")
            if len(data) > 25:
                print(f"   📝 Note: Regular WooCommerce supports higher limits!")
        else:
            print(f"   ❌ Orders endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Try direct URL manipulation
    print(f"\n{'-'*60}")
    print("TEST 5: Direct URL Parameter Testing")
    print(f"{'-'*60}")
    
    # Build URL with parameters in different ways
    endpoint = "payments/reports/transactions"
    
    # Try URL with larger limit directly
    test_urls = [
        f"{endpoint}?per_page=100",
        f"{endpoint}?limit=100",
        f"{endpoint}?perpage=100",
        f"{endpoint}?count=100"
    ]
    
    for i, url_suffix in enumerate(test_urls):
        print(f"\n   Test {i+1}: {url_suffix}")
        
        # Add date parameters
        params = {
            'date_after': '2025-05-01 00:00:00',
            'date_before': '2025-05-31 23:59:59'
        }
        
        try:
            # The API library will append params to the URL
            response = api.get(url_suffix, params=params)
            if response.status_code == 200:
                data = response.json()
                print(f"   Got {len(data)} records")
            else:
                print(f"   Status {response.status_code}")
        except Exception as e:
            print(f"   Error: {str(e)[:50]}")
    
    # Summary
    print(f"\n{'='*80}")
    print("DISCOVERY SUMMARY")
    print(f"{'='*80}")
    
    if actual_limit:
        print(f"\n📊 Key Finding: API limit is {actual_limit} records per page")
        
        if actual_limit == 25:
            print("\n🔍 Analysis:")
            print("   - WooPayments API has hardcoded 25-record limit")
            print("   - This is different from core WooCommerce endpoints")
            print("   - Limitation appears to be by design")
            
            print("\n💡 Optimization Options:")
            print("   1. Use parallel fetching (already tested)")
            print("   2. Cache results when possible")
            print("   3. Use payment_id matching (already implemented)")
            print("   4. Consider webhooks for real-time updates")
        else:
            print(f"\n✅ Can use per_page={actual_limit}!")
            print("   - Update code to use this limit")
            print("   - Significant performance improvement available")
    else:
        print("\n⚠️  Could not determine exact limit")
        print("   - Recommend staying with per_page=25")

if __name__ == "__main__":
    test_api_limits()