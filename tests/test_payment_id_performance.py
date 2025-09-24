#!/usr/bin/env python3
"""
Performance comparison test: payment_id matching vs order number matching
Measures time savings and API call reduction
"""
import sys
import time
import logging
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.woocommerce_api import WooCommerceAPI

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def performance_comparison():
    """Compare performance of payment_id vs order number approaches"""
    
    print("="*80)
    print("Payment ID vs Order Number Performance Comparison")
    print("="*80)
    
    # Initialize API
    woo_api = WooCommerceAPI()
    
    # Test date range
    date_after = "2025-05-01"
    date_before = "2025-05-31"
    
    print(f"\nTesting date range: {date_after} to {date_before}")
    print("-"*80)
    
    # Test connection first
    print("\n🔍 Testing API connection...")
    connection_result = woo_api.test_connection()
    if not connection_result.get('success'):
        print(f"❌ Connection failed: {connection_result}")
        return
    print(f"✅ Connected: {connection_result.get('details')}")
    
    # Performance Test 1: WITHOUT order number fetching (FAST - Payment ID approach)
    print(f"\n{'-'*60}")
    print("TEST 1: Payment ID Approach (fetch_order_numbers=False)")
    print("This simulates the new payment_id matching approach")
    print(f"{'-'*60}")
    
    start_time = time.time()
    
    df_payment_id_approach = woo_api.get_all_transactions(
        date_after=date_after,
        date_before=date_before,
        fetch_order_numbers=False  # Skip order number lookups
    )
    
    time_payment_id = time.time() - start_time
    
    if df_payment_id_approach is not None:
        print(f"✅ SUCCESS: {len(df_payment_id_approach)} transactions")
        print(f"   Time taken: {time_payment_id:.2f} seconds")
        print(f"   Rate: {len(df_payment_id_approach) / time_payment_id:.1f} transactions/second")
        
        # Check payment_id availability
        if 'payment_id' in df_payment_id_approach.columns:
            payment_ids = df_payment_id_approach['payment_id'].to_list()
            pi_count = sum(1 for pid in payment_ids if pid and str(pid).startswith('pi_'))
            print(f"   Valid payment_ids (pi_*): {pi_count}")
            print(f"   Payment ID coverage: {(pi_count / len(df_payment_id_approach) * 100):.1f}%")
    else:
        print("❌ FAILED: Could not fetch transactions")
        return
    
    # Performance Test 2: WITH order number fetching (SLOW - Current approach)
    print(f"\n{'-'*60}")
    print("TEST 2: Order Number Approach (fetch_order_numbers=True)")
    print("This is the current order number matching approach")
    print(f"{'-'*60}")
    
    start_time = time.time()
    
    df_order_number_approach = woo_api.get_all_transactions(
        date_after=date_after,
        date_before=date_before,
        fetch_order_numbers=True  # Fetch order numbers (adds API calls)
    )
    
    time_order_number = time.time() - start_time
    
    if df_order_number_approach is not None:
        print(f"✅ SUCCESS: {len(df_order_number_approach)} transactions")
        print(f"   Time taken: {time_order_number:.2f} seconds")
        print(f"   Rate: {len(df_order_number_approach) / time_order_number:.1f} transactions/second")
        
        # Check order_number availability
        if 'order_number' in df_order_number_approach.columns:
            order_numbers = df_order_number_approach['order_number'].to_list()
            valid_orders = sum(1 for on in order_numbers if on and str(on) != '0')
            print(f"   Valid order_numbers: {valid_orders}")
            print(f"   Order number coverage: {(valid_orders / len(df_order_number_approach) * 100):.1f}%")
    else:
        print("❌ FAILED: Could not fetch transactions")
        return
    
    # Performance Analysis
    print(f"\n{'='*80}")
    print("PERFORMANCE ANALYSIS")
    print(f"{'='*80}")
    
    # Verify data integrity
    data_integrity_ok = len(df_payment_id_approach) == len(df_order_number_approach)
    print(f"\n📊 Data Integrity Check:")
    print(f"   Transaction count matches: {data_integrity_ok}")
    print(f"   Payment ID approach: {len(df_payment_id_approach)} transactions")
    print(f"   Order Number approach: {len(df_order_number_approach)} transactions")
    
    if 'fees' in df_payment_id_approach.columns and 'fees' in df_order_number_approach.columns:
        fees1 = df_payment_id_approach['fees'].sum()
        fees2 = df_order_number_approach['fees'].sum()
        fees_match = abs(fees1 - fees2) < 0.01
        print(f"   Total fees match: {fees_match} (${fees1:.2f} vs ${fees2:.2f})")
    
    # Performance metrics
    if data_integrity_ok and time_payment_id > 0 and time_order_number > 0:
        time_saved = time_order_number - time_payment_id
        percent_improvement = (time_saved / time_order_number) * 100
        speedup_factor = time_order_number / time_payment_id
        
        print(f"\n🚀 Performance Improvement:")
        print(f"   Payment ID approach: {time_payment_id:.2f} seconds")
        print(f"   Order Number approach: {time_order_number:.2f} seconds")
        print(f"   Time saved: {time_saved:.2f} seconds")
        print(f"   Performance improvement: {percent_improvement:.1f}% faster")
        print(f"   Speedup factor: {speedup_factor:.1f}x")
        
        # Estimate API call savings
        if df_order_number_approach is not None:
            unique_orders = len(df_order_number_approach)
            estimated_api_calls_saved = (unique_orders // 100) + 1  # Batch size is 100
            print(f"\n📡 API Call Reduction:")
            print(f"   Estimated order lookup API calls saved: {estimated_api_calls_saved}")
            print(f"   API calls per transaction (current): {estimated_api_calls_saved / unique_orders:.3f}")
            print(f"   API calls per transaction (new): 0 (payment_id is already included)")
        
        # ROI Analysis
        print(f"\n💰 Business Impact:")
        print(f"   Processing time reduction: {time_saved:.1f}s per operation")
        print(f"   User experience improvement: {percent_improvement:.1f}% faster")
        print(f"   API load reduction: ~{estimated_api_calls_saved} fewer calls")
        
        # Recommendation
        if percent_improvement > 30:  # Significant improvement threshold
            print(f"\n✅ STRONG RECOMMENDATION: Implement payment_id matching")
            print(f"   Performance gain of {percent_improvement:.1f}% justifies the change")
        elif percent_improvement > 10:
            print(f"\n🤔 MODERATE RECOMMENDATION: Consider payment_id matching")
            print(f"   Performance gain of {percent_improvement:.1f}% provides decent improvement")
        else:
            print(f"\n❌ NOT RECOMMENDED: Minimal performance gain")
            print(f"   Only {percent_improvement:.1f}% improvement may not justify change")
    
    # Test 3: Measure just the order lookup overhead
    print(f"\n{'-'*60}")
    print("TEST 3: Order Lookup Overhead Analysis")
    print(f"{'-'*60}")
    
    if df_payment_id_approach is not None and 'order_id' in df_payment_id_approach.columns:
        order_ids = [int(oid) for oid in df_payment_id_approach['order_id'].to_list() if oid and str(oid).isdigit()]
        
        if order_ids:
            print(f"   Testing order lookup for {len(order_ids)} orders...")
            
            start_time = time.time()
            order_lookup_result = woo_api._get_order_numbers_for_transactions(order_ids[:50])  # Test with first 50
            lookup_time = time.time() - start_time
            
            print(f"   Order lookup time (50 orders): {lookup_time:.2f} seconds")
            print(f"   Rate: {50 / lookup_time:.1f} orders/second")
            
            # Extrapolate for full dataset
            estimated_full_lookup_time = (len(order_ids) / 50) * lookup_time
            print(f"   Estimated full lookup time: {estimated_full_lookup_time:.2f} seconds")
    
    print(f"\n{'='*80}")
    print("PERFORMANCE TEST COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    performance_comparison()