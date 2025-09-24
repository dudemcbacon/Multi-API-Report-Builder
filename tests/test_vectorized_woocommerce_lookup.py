#!/usr/bin/env python3
"""
Test script for the new vectorized WooCommerce lookup functionality
Validates the performance and correctness of the vectorized approach
"""
import sys
import time
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

import polars as pl
from services.woocommerce_api import WooCommerceAPI

def test_vectorized_payment_lookup():
    """Test the new vectorized payment fees lookup"""
    
    print("="*80)
    print("VECTORIZED WOOCOMMERCE LOOKUP TESTING")
    print("Testing the new get_payment_fees_vectorized method")
    print("="*80)
    
    # Test 1: API Connection
    print(f"\n{'-'*60}")
    print("TEST 1: WooCommerce API Connection")
    print(f"{'-'*60}")
    
    try:
        woo_api = WooCommerceAPI()
        print(f"✅ WooCommerce API instance created")
        
        # Test connection
        test_result = woo_api.test_connection()
        print(f"   Connection test: {test_result.get('success', False)}")
        
        if test_result.get('success'):
            print(f"   Store: {test_result.get('store_name', 'Unknown')}")
            print(f"   WooCommerce: {test_result.get('wc_version', 'Unknown')}")
        else:
            print(f"   Error: {test_result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False
    
    # Test 2: Sample Payment ID Data
    print(f"\n{'-'*60}")
    print("TEST 2: Sample Payment ID Preparation")
    print(f"{'-'*60}")
    
    # Create sample payment IDs (mix of valid and invalid)
    sample_payment_ids = [
        'pi_1234567890abcdef',
        'pi_0987654321fedcba', 
        'pi_1122334455667788',
        'pi_aabbccddeeff1122',
        'pi_ffee33dd22aa1199',
        'not_a_stripe_id',
        'ch_old_charge_format',
        '',
        None
    ]
    
    print(f"✅ Sample payment IDs prepared: {len(sample_payment_ids)} total")
    
    # Filter valid payment IDs
    valid_payment_ids = [pid for pid in sample_payment_ids if str(pid).startswith('pi_')]
    print(f"   Valid payment IDs: {len(valid_payment_ids)}")
    print(f"   Sample valid IDs: {valid_payment_ids[:3]}")
    
    # Test 3: Vectorized Lookup Method
    print(f"\n{'-'*60}")
    print("TEST 3: Vectorized Payment Fees Lookup")
    print(f"{'-'*60}")
    
    try:
        start_time = time.time()
        
        # Test the vectorized lookup
        fees_df = woo_api.get_payment_fees_vectorized(
            payment_ids=valid_payment_ids,
            date_after='2025-05-01',
            date_before='2025-05-31'
        )
        
        elapsed_time = time.time() - start_time
        
        if fees_df is not None:
            print(f"✅ Vectorized lookup successful in {elapsed_time:.2f} seconds")
            print(f"   Results: {len(fees_df)} payment fee records")
            print(f"   Schema: {fees_df.schema}")
            
            if len(fees_df) > 0:
                print(f"   Sample results:")
                print(fees_df.head())
                
                # Statistics
                total_fees = fees_df['fees'].sum()
                avg_fee = fees_df['fees'].mean()
                max_fee = fees_df['fees'].max()
                
                print(f"\n   Fee Statistics:")
                print(f"   - Total fees: ${total_fees:.2f}")
                print(f"   - Average fee: ${avg_fee:.2f}")
                print(f"   - Maximum fee: ${max_fee:.2f}")
            else:
                print(f"   No fee data found for date range")
                
        else:
            print(f"❌ Vectorized lookup returned None")
            
    except Exception as e:
        print(f"❌ Vectorized lookup failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: Payment Fees Cache Creation
    print(f"\n{'-'*60}")
    print("TEST 4: Payment Fees Cache Creation")
    print(f"{'-'*60}")
    
    try:
        start_time = time.time()
        
        # Test cache creation
        fees_cache = woo_api.create_payment_fees_cache(
            payment_ids=valid_payment_ids,
            date_after='2025-05-01',
            date_before='2025-05-31'
        )
        
        elapsed_time = time.time() - start_time
        
        if fees_cache:
            print(f"✅ Cache creation successful in {elapsed_time:.2f} seconds")
            print(f"   Cache size: {len(fees_cache)} entries")
            
            # Test cache lookups
            print(f"\n   Cache lookup tests:")
            for pid in valid_payment_ids[:3]:
                fee = fees_cache.get(pid, 'NOT_FOUND')
                print(f"   - {pid}: ${fee}")
            
            # Count non-zero fees
            non_zero_fees = sum(1 for fee in fees_cache.values() if fee > 0)
            print(f"\n   Cache statistics:")
            print(f"   - Total entries: {len(fees_cache)}")
            print(f"   - Non-zero fees: {non_zero_fees}")
            print(f"   - Zero fees: {len(fees_cache) - non_zero_fees}")
            
        else:
            print(f"❌ Cache creation returned empty dict")
            
    except Exception as e:
        print(f"❌ Cache creation failed: {e}")
        import traceback
        traceback.print_exc()
    
    return True

def test_salesforce_integration():
    """Test vectorized lookup with Salesforce-like data"""
    
    print(f"\n{'-'*60}")
    print("TEST 5: Salesforce Integration Simulation")
    print(f"{'-'*60}")
    
    # Create sample Salesforce DataFrame
    sf_sample_data = {
        'Account Name': [f'Account {i}' for i in range(10)],
        'Payment ID': [f'pi_test{i:03d}234567890abcdef' for i in range(10)],
        'Webstore Order #': [f'12{i:03d}' for i in range(10)],
        'SKU': [f'PRODUCT{i}' for i in range(10)],
        'Quantity': [1] * 10,
        'Unit Price': [100.0 + i * 10 for i in range(10)]
    }
    
    sf_df = pl.DataFrame(sf_sample_data)
    print(f"✅ Sample Salesforce data: {len(sf_df)} rows")
    print(f"   Payment IDs sample: {sf_df['Payment ID'].head(3).to_list()}")
    
    # Extract payment IDs (simulate the real process)
    payment_ids = sf_df.filter(
        pl.col('Payment ID').str.starts_with('pi_')
    ).select('Payment ID').to_series().to_list()
    
    print(f"✅ Extracted {len(payment_ids)} payment IDs from Salesforce data")
    
    # Test vectorized lookup with extracted IDs
    try:
        woo_api = WooCommerceAPI()
        
        start_time = time.time()
        fees_cache = woo_api.create_payment_fees_cache(
            payment_ids=payment_ids,
            date_after='2025-05-01',
            date_before='2025-05-31'
        )
        elapsed_time = time.time() - start_time
        
        print(f"✅ Vectorized lookup with Salesforce IDs: {elapsed_time:.2f}s")
        print(f"   Cache entries: {len(fees_cache)}")
        
        # Simulate the fee addition process
        if fees_cache:
            sf_with_fees = sf_df.with_columns([
                pl.col('Payment ID').map_elements(
                    lambda pid: fees_cache.get(pid, 0.0),
                    return_dtype=pl.Float64
                ).alias('woo_fees')
            ])
            
            # Filter for orders with fees > 0
            orders_with_fees = sf_with_fees.filter(pl.col('woo_fees') > 0)
            
            print(f"   Orders with fees: {len(orders_with_fees)} out of {len(sf_df)}")
            
            if len(orders_with_fees) > 0:
                print(f"   Sample orders with fees:")
                print(orders_with_fees[['Payment ID', 'woo_fees']].head())
        
    except Exception as e:
        print(f"❌ Salesforce integration test failed: {e}")

def performance_comparison():
    """Compare vectorized vs traditional approach performance"""
    
    print(f"\n{'-'*60}")
    print("TEST 6: Performance Comparison")
    print(f"{'-'*60}")
    
    # Create larger sample dataset
    large_payment_ids = [f'pi_{i:015d}abcdef' for i in range(50)]
    
    print(f"✅ Large dataset prepared: {len(large_payment_ids)} payment IDs")
    
    try:
        woo_api = WooCommerceAPI()
        
        # Test vectorized approach
        print(f"\n   Testing vectorized approach...")
        start_time = time.time()
        
        vectorized_cache = woo_api.create_payment_fees_cache(
            payment_ids=large_payment_ids,
            date_after='2025-05-01',
            date_before='2025-05-31'
        )
        
        vectorized_time = time.time() - start_time
        
        print(f"   Vectorized time: {vectorized_time:.2f} seconds")
        print(f"   Results: {len(vectorized_cache)} entries")
        print(f"   Rate: {len(large_payment_ids)/vectorized_time:.1f} payment IDs/second")
        
        # Note: We can't easily test the "old" approach without modifying the API
        # But we can estimate based on individual API calls
        estimated_individual_time = len(large_payment_ids) * 0.1  # Assume 100ms per API call
        estimated_improvement = ((estimated_individual_time - vectorized_time) / estimated_individual_time) * 100
        
        print(f"\n   Performance Analysis:")
        print(f"   - Estimated individual lookup time: {estimated_individual_time:.2f}s")
        print(f"   - Vectorized approach time: {vectorized_time:.2f}s")
        print(f"   - Estimated improvement: {estimated_improvement:.1f}%")
        
    except Exception as e:
        print(f"❌ Performance comparison failed: {e}")

def test_edge_cases():
    """Test edge cases and error handling"""
    
    print(f"\n{'-'*60}")
    print("TEST 7: Edge Cases and Error Handling")
    print(f"{'-'*60}")
    
    try:
        woo_api = WooCommerceAPI()
        
        # Test 1: Empty payment ID list
        print(f"\n   Test 1: Empty payment ID list")
        result = woo_api.create_payment_fees_cache(payment_ids=[])
        print(f"   ✅ Empty list result: {result}")
        
        # Test 2: Invalid payment IDs
        print(f"\n   Test 2: Invalid payment IDs")
        invalid_ids = ['not_stripe', 'ch_old_format', '', None]
        result = woo_api.create_payment_fees_cache(payment_ids=invalid_ids)
        print(f"   ✅ Invalid IDs result: {result}")
        
        # Test 3: Mixed valid/invalid payment IDs
        print(f"\n   Test 3: Mixed valid/invalid payment IDs")
        mixed_ids = ['pi_valid123', 'not_stripe', 'pi_valid456', '', 'pi_valid789']
        result = woo_api.create_payment_fees_cache(payment_ids=mixed_ids)
        print(f"   ✅ Mixed IDs result: {len(result)} entries")
        
        # Test 4: Future date range (should return no results)
        print(f"\n   Test 4: Future date range")
        future_ids = ['pi_future123456789']
        result = woo_api.create_payment_fees_cache(
            payment_ids=future_ids,
            date_after='2026-01-01',
            date_before='2026-01-31'
        )
        print(f"   ✅ Future date result: {result}")
        
    except Exception as e:
        print(f"❌ Edge case testing failed: {e}")

if __name__ == "__main__":
    try:
        success = test_vectorized_payment_lookup()
        
        if success:
            test_salesforce_integration()
            performance_comparison()
            test_edge_cases()
        
        print(f"\n{'='*80}")
        print("VECTORIZED WOOCOMMERCE LOOKUP TESTING COMPLETED")
        print("Review results above for performance and correctness validation")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"Test script failed: {e}")
        import traceback
        traceback.print_exc()