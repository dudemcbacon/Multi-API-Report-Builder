#!/usr/bin/env python3
"""
Test script to investigate WooPayments API pagination
Tests different pagination approaches to get ALL transactions for date range
"""
import sys
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from woocommerce import API

# WooCommerce API credentials
CONSUMER_KEY = "ck_EXAMPLE1234567890abcdefghijklmnop"
CONSUMER_SECRET = "cs_EXAMPLE0987654321zyxwvutsrqponmlk"
STORE_URL = "https://shop.company.com"

def test_pagination_approaches():
    """Test different pagination approaches for WooPayments API"""
    
    api = API(
        url=STORE_URL,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        version="wc/v3",
        timeout=30,
        query_string_auth=True
    )
    
    print("="*80)
    print("WooPayments API Pagination Testing")
    print("Date range: 2025-05-01 to 2025-05-31")
    print("="*80)
    
    # Base parameters (working date format)
    base_params = {
        'date_after': '2025-05-01 00:00:00',
        'date_before': '2025-05-31 23:59:59'
    }
    
    print(f"\nBase parameters: {base_params}")
    
    # Test 1: Current approach (no pagination - should get 25 results)
    print(f"\n{'-'*60}")
    print("TEST 1: Current approach (no pagination)")
    print(f"{'-'*60}")
    
    try:
        response = api.get("payments/reports/transactions", params=base_params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: {len(data)} transactions")
            if data:
                first_date = data[0].get('date', 'N/A')
                last_date = data[-1].get('date', 'N/A')
                print(f"   Date range: {last_date} to {first_date}")
                
                # Check for fees
                total_fees = sum(t.get('fees', 0) for t in data)
                print(f"   Total fees: ${total_fees:.2f}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 2: Add per_page parameter
    print(f"\n{'-'*60}")
    print("TEST 2: With per_page=100")
    print(f"{'-'*60}")
    
    params_with_per_page = base_params.copy()
    params_with_per_page['per_page'] = 100
    
    try:
        response = api.get("payments/reports/transactions", params=params_with_per_page)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: {len(data)} transactions")
            if data:
                first_date = data[0].get('date', 'N/A')
                last_date = data[-1].get('date', 'N/A')
                print(f"   Date range: {last_date} to {first_date}")
                
                # Check for fees
                total_fees = sum(t.get('fees', 0) for t in data)
                print(f"   Total fees: ${total_fees:.2f}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error}")
            except:
                print(f"   Raw error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 3: Add pagination parameters
    print(f"\n{'-'*60}")
    print("TEST 3: With pagination (page=1, per_page=100)")
    print(f"{'-'*60}")
    
    params_with_pagination = base_params.copy()
    params_with_pagination['page'] = 1
    params_with_pagination['per_page'] = 100
    
    try:
        response = api.get("payments/reports/transactions", params=params_with_pagination)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS: {len(data)} transactions")
            if data:
                first_date = data[0].get('date', 'N/A')
                last_date = data[-1].get('date', 'N/A')
                print(f"   Date range: {last_date} to {first_date}")
                
                # Check for fees
                total_fees = sum(t.get('fees', 0) for t in data)
                print(f"   Total fees: ${total_fees:.2f}")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error}")
            except:
                print(f"   Raw error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    # Test 4: Multi-page pagination simulation
    print(f"\n{'-'*60}")
    print("TEST 4: Multi-page pagination (simulating loop)")
    print(f"{'-'*60}")
    
    all_transactions = []
    page = 1
    max_pages = 5  # Safety limit for testing
    
    while page <= max_pages:
        params_page = base_params.copy()
        params_page['page'] = page
        params_page['per_page'] = 25  # Use smaller page size to test pagination
        
        print(f"  Fetching page {page}...")
        
        try:
            response = api.get("payments/reports/transactions", params=params_page)
            if response.status_code == 200:
                data = response.json()
                print(f"    Page {page}: {len(data)} transactions")
                
                if not data or len(data) == 0:
                    print(f"    No more data on page {page}, stopping")
                    break
                
                all_transactions.extend(data)
                
                # If we got fewer than requested, we've reached the end
                if len(data) < 25:
                    print(f"    Reached last page (got {len(data)} < 25)")
                    break
                    
                page += 1
            else:
                print(f"    ❌ Page {page} failed: Status {response.status_code}")
                try:
                    error = response.json()
                    print(f"    Error: {error}")
                except:
                    print(f"    Raw error: {response.text[:200]}")
                break
        except Exception as e:
            print(f"    ❌ Page {page} error: {e}")
            break
    
    if all_transactions:
        print(f"\n✅ TOTAL COLLECTED: {len(all_transactions)} transactions from {page-1} pages")
        if all_transactions:
            first_date = all_transactions[0].get('date', 'N/A')
            last_date = all_transactions[-1].get('date', 'N/A')
            print(f"   Complete date range: {last_date} to {first_date}")
            
            # Check for fees
            total_fees = sum(t.get('fees', 0) for t in all_transactions)
            print(f"   Total fees: ${total_fees:.2f}")
            
            # Show unique order IDs
            order_ids = set(t.get('order_id') for t in all_transactions if t.get('order_id'))
            print(f"   Unique orders: {len(order_ids)}")
    else:
        print("❌ No transactions collected from pagination")
    
    # Test 5: Alternative endpoints
    print(f"\n{'-'*60}")
    print("TEST 5: Alternative endpoint (payments/transactions)")
    print(f"{'-'*60}")
    
    try:
        response = api.get("payments/transactions", params=base_params)
        if response.status_code == 200:
            data = response.json()
            # This endpoint returns data in 'data' key
            if isinstance(data, dict) and 'data' in data:
                transactions = data['data']
                print(f"✅ SUCCESS: {len(transactions)} transactions")
                if transactions:
                    first_date = transactions[0].get('date', 'N/A')
                    last_date = transactions[-1].get('date', 'N/A')
                    print(f"   Date range: {last_date} to {first_date}")
                    
                    # Check for fees
                    total_fees = sum(t.get('fees', 0) for t in transactions)
                    print(f"   Total fees: ${total_fees:.2f}")
            else:
                print(f"✅ SUCCESS: Response structure: {type(data)}")
                if isinstance(data, list):
                    print(f"   {len(data)} transactions")
        else:
            print(f"❌ FAILED: Status {response.status_code}")
    except Exception as e:
        print(f"❌ ERROR: {e}")
    
    print(f"\n{'='*80}")
    print("PAGINATION TESTING COMPLETE")
    print("Look for the approach that returns the most transactions!")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_pagination_approaches()