#!/usr/bin/env python3
"""
Test script using existing WooCommerce API class to test pagination
Run this in your main environment where dependencies are available
"""
import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

try:
    from src.services.woocommerce_api import WooCommerceAPI
    print("✅ WooCommerce API class imported successfully")
except ImportError as e:
    print(f"❌ Failed to import WooCommerce API: {e}")
    sys.exit(1)

# Setup logging to see debug output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pagination_solutions():
    """Test different approaches to get ALL transactions from WooPayments API"""
    
    print("="*80)
    print("WooPayments API Pagination Testing")
    print("Using existing WooCommerceAPI class")
    print("Date range: 2025-05-01 to 2025-05-31")
    print("="*80)
    
    # Initialize API
    woo_api = WooCommerceAPI()
    
    # Test connection first
    print("\n1. Testing connection...")
    connection_result = woo_api.test_connection()
    if not connection_result.get('success'):
        print(f"❌ Connection failed: {connection_result}")
        return
    print(f"✅ Connected: {connection_result.get('details')}")
    
    # Test different approaches
    approaches = [
        {
            'name': 'Current approach (get_transactions)',
            'method': 'single_call',
            'params': {'per_page': 100, 'page': 1}
        },
        {
            'name': 'Current get_all_transactions method',
            'method': 'get_all',
            'params': {}
        },
        {
            'name': 'Manual pagination with per_page=25',
            'method': 'manual_pagination',
            'params': {'per_page': 25}
        },
        {
            'name': 'Manual pagination with per_page=100',
            'method': 'manual_pagination', 
            'params': {'per_page': 100}
        }
    ]
    
    results = {}
    
    for approach in approaches:
        print(f"\n{'-'*60}")
        print(f"Testing: {approach['name']}")
        print(f"{'-'*60}")
        
        try:
            if approach['method'] == 'single_call':
                # Test single call with parameters
                result_df = woo_api.get_transactions(
                    per_page=approach['params']['per_page'],
                    page=approach['params']['page'],
                    date_after='2025-05-01',
                    date_before='2025-05-31',
                    fetch_order_numbers=False  # Skip for speed
                )
                
            elif approach['method'] == 'get_all':
                # Test current get_all_transactions method
                result_df = woo_api.get_all_transactions(
                    date_after='2025-05-01',
                    date_before='2025-05-31',
                    fetch_order_numbers=False  # Skip for speed
                )
                
            elif approach['method'] == 'manual_pagination':
                # Manual pagination simulation
                all_transactions = []
                page = 1
                max_pages = 10  # Safety limit
                per_page = approach['params']['per_page']
                
                while page <= max_pages:
                    print(f"  Fetching page {page} (per_page={per_page})...")
                    
                    page_df = woo_api.get_transactions(
                        per_page=per_page,
                        page=page,
                        date_after='2025-05-01',
                        date_before='2025-05-31',
                        fetch_order_numbers=False
                    )
                    
                    if page_df is None or len(page_df) == 0:
                        print(f"    No data on page {page}, stopping")
                        break
                    
                    print(f"    Page {page}: {len(page_df)} transactions")
                    all_transactions.append(page_df)
                    
                    # If we got fewer than requested, we've reached the end
                    if len(page_df) < per_page:
                        print(f"    Reached last page (got {len(page_df)} < {per_page})")
                        break
                    
                    page += 1
                
                # Combine all pages
                if all_transactions:
                    import polars as pl
                    result_df = pl.concat(all_transactions, how="vertical")
                    print(f"  Combined {len(all_transactions)} pages")
                else:
                    result_df = None
            
            # Analyze results
            if result_df is not None and len(result_df) > 0:
                print(f"✅ SUCCESS: {len(result_df)} transactions")
                
                # Check date range
                if 'date' in result_df.columns:
                    dates = result_df['date'].to_list()
                    dates = [d for d in dates if d]  # Remove None values
                    if dates:
                        dates.sort()
                        print(f"   Date range: {dates[0]} to {dates[-1]}")
                
                # Check fees
                if 'fees' in result_df.columns:
                    total_fees = result_df['fees'].sum()
                    fees_with_values = result_df.filter(result_df['fees'] > 0)
                    print(f"   Total fees: ${total_fees:.2f}")
                    print(f"   Transactions with fees: {len(fees_with_values)}")
                
                # Check unique orders
                if 'order_id' in result_df.columns:
                    unique_orders = result_df['order_id'].n_unique()
                    print(f"   Unique orders: {unique_orders}")
                
                results[approach['name']] = {
                    'count': len(result_df),
                    'total_fees': float(total_fees) if 'fees' in result_df.columns else 0,
                    'success': True
                }
                
            else:
                print("❌ No data returned")
                results[approach['name']] = {
                    'count': 0,
                    'total_fees': 0,
                    'success': False
                }
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results[approach['name']] = {
                'count': 0,
                'total_fees': 0,
                'success': False,
                'error': str(e)
            }
    
    # Summary
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}")
    
    best_approach = None
    best_count = 0
    
    for name, result in results.items():
        status = "✅" if result['success'] else "❌"
        count = result['count']
        fees = result.get('total_fees', 0)
        
        print(f"{status} {name}")
        print(f"    Transactions: {count}")
        print(f"    Total fees: ${fees:.2f}")
        
        if 'error' in result:
            print(f"    Error: {result['error']}")
        
        if count > best_count:
            best_count = count
            best_approach = name
        
        print()
    
    if best_approach:
        print(f"🏆 BEST APPROACH: {best_approach}")
        print(f"   Returned {best_count} transactions")
    else:
        print("❌ No successful approaches found")
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_pagination_solutions()