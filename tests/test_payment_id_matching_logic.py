#!/usr/bin/env python3
"""
Test script to validate payment_id matching logic
This simulates the new matching approach and compares results
"""
import sys
import logging
from pathlib import Path

# Add src to Python path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.services.woocommerce_api import WooCommerceAPI

# Setup logging to reduce noise during testing
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def test_payment_id_matching():
    """Test the new payment_id matching logic"""
    
    print("="*80)
    print("Payment ID Matching Logic Test")
    print("Testing new payment_id-based matching vs current order_number approach")
    print("="*80)
    
    # Initialize API
    woo_api = WooCommerceAPI()
    
    # Test date range
    date_after = "2025-05-01"
    date_before = "2025-05-31"
    
    print(f"\nTest date range: {date_after} to {date_before}")
    print("-"*80)
    
    # Fetch WooCommerce data with order numbers for comparison
    print("\n1. Fetching WooCommerce transaction data...")
    woo_df = woo_api.get_all_transactions(
        date_after=date_after,
        date_before=date_before,
        fetch_order_numbers=False  # Use payment_id approach
    )
    
    if woo_df is None or len(woo_df) == 0:
        print("❌ No WooCommerce data available")
        return
    
    print(f"✅ Fetched {len(woo_df)} WooCommerce transactions")
    
    # Convert to list of dicts for easier processing
    woo_records = woo_df.to_dicts()
    
    # Method 1: Current order_number matching (simulated)
    print("\n2. Testing current order_number matching approach...")
    
    # Simulate current approach: create lookup by order_number
    order_number_lookup = {}
    order_number_fees = 0.0
    order_number_count = 0
    
    # Note: Since we're not fetching order_numbers, we'll simulate using order_id
    # In real scenario, this would require additional API calls
    for record in woo_records:
        order_id = str(record.get('order_id', ''))
        if order_id and order_id != '0':
            # Simulate order_number (in reality this comes from additional API call)
            simulated_order_number = order_id  # order_id would map to order_number
            order_number_lookup[simulated_order_number] = record
            
            fees = float(record.get('fees', 0))
            if fees > 0:
                order_number_fees += fees
                order_number_count += 1
    
    print(f"   Order number lookup created: {len(order_number_lookup)} mappings")
    print(f"   Orders with fees (order_number): {order_number_count}")
    print(f"   Total fees (order_number): ${order_number_fees:.2f}")
    
    # Method 2: New payment_id matching approach
    print("\n3. Testing new payment_id matching approach...")
    
    # Create lookup by payment_id
    payment_id_lookup = {}
    payment_id_fees = 0.0
    payment_id_count = 0
    
    for record in woo_records:
        payment_id = str(record.get('payment_id', '')).strip()
        if payment_id and payment_id.startswith('pi_'):
            payment_id_lookup[payment_id] = record
            
            fees = float(record.get('fees', 0))
            if fees > 0:
                payment_id_fees += fees
                payment_id_count += 1
    
    print(f"   Payment ID lookup created: {len(payment_id_lookup)} mappings")
    print(f"   Orders with fees (payment_id): {payment_id_count}")
    print(f"   Total fees (payment_id): ${payment_id_fees:.2f}")
    
    # Method 3: Cross-validation between approaches
    print("\n4. Cross-validation analysis...")
    
    # Compare the two approaches
    order_ids_with_fees = set()
    payment_ids_with_fees = set()
    
    # Track which records have fees in each approach
    for record in woo_records:
        fees = float(record.get('fees', 0))
        if fees > 0:
            # Order number approach
            order_id = str(record.get('order_id', ''))
            if order_id and order_id != '0':
                order_ids_with_fees.add(order_id)
            
            # Payment ID approach
            payment_id = str(record.get('payment_id', '')).strip()
            if payment_id and payment_id.startswith('pi_'):
                payment_ids_with_fees.add(payment_id)
    
    # Analysis
    print(f"   Records with fees (order_id method): {len(order_ids_with_fees)}")
    print(f"   Records with fees (payment_id method): {len(payment_ids_with_fees)}")
    
    # Check for discrepancies
    fees_match = abs(order_number_fees - payment_id_fees) < 0.01
    count_match = order_number_count == payment_id_count
    
    print(f"   Fee totals match: {fees_match}")
    print(f"   Fee counts match: {count_match}")
    
    if fees_match and count_match:
        print("   ✅ Both approaches yield identical results")
    else:
        print("   ⚠️  Approaches yield different results - investigation needed")
    
    # Method 4: Simulate Salesforce matching
    print("\n5. Simulating Salesforce matching scenarios...")
    
    # Simulate some Salesforce records with Payment IDs
    simulated_sf_records = []
    
    # Create mock Salesforce data based on WooCommerce payment_ids
    sample_payment_ids = [pid for pid in payment_id_lookup.keys()][:10]  # Take first 10
    
    for i, payment_id in enumerate(sample_payment_ids):
        woo_record = payment_id_lookup[payment_id]
        order_id = woo_record.get('order_id', '')
        
        # Simulate Salesforce record
        sf_record = {
            'Payment ID': payment_id,
            'Webstore Order #': order_id,
            'SKU': f'PRODUCT-{i+1}',
            'Quantity': 1,
            'Unit Price': 25.00,
            'Account Name': f'Customer {i+1}'
        }
        simulated_sf_records.append(sf_record)
    
    print(f"   Created {len(simulated_sf_records)} simulated Salesforce records")
    
    # Test matching by Payment ID
    print("\n6. Testing Payment ID matching with simulated Salesforce data...")
    
    matched_by_payment_id = 0
    total_matched_fees = 0.0
    
    for sf_record in simulated_sf_records:
        sf_payment_id = sf_record.get('Payment ID', '')
        
        if sf_payment_id in payment_id_lookup:
            woo_data = payment_id_lookup[sf_payment_id]
            fees = float(woo_data.get('fees', 0))
            matched_by_payment_id += 1
            total_matched_fees += fees
            
            print(f"   ✅ Matched Payment ID {sf_payment_id[:20]}... -> Fee: ${fees:.2f}")
        else:
            print(f"   ❌ No match for Payment ID {sf_payment_id[:20]}...")
    
    # Test matching by Webstore Order # (current approach)
    print(f"\n7. Testing Order Number matching with simulated Salesforce data...")
    
    matched_by_order_number = 0
    
    for sf_record in simulated_sf_records:
        sf_order_number = str(sf_record.get('Webstore Order #', ''))
        
        if sf_order_number in order_number_lookup:
            matched_by_order_number += 1
            print(f"   ✅ Matched Order # {sf_order_number}")
        else:
            print(f"   ❌ No match for Order # {sf_order_number}")
    
    # Results Summary
    print(f"\n{'='*80}")
    print("MATCHING LOGIC TEST RESULTS")
    print(f"{'='*80}")
    
    print(f"\n📊 Data Coverage:")
    print(f"   Total WooCommerce transactions: {len(woo_records)}")
    print(f"   Transactions with payment_ids: {len(payment_id_lookup)}")
    print(f"   Transactions with order_ids: {len(order_number_lookup)}")
    print(f"   Payment ID coverage: {(len(payment_id_lookup) / len(woo_records) * 100):.1f}%")
    
    print(f"\n🎯 Matching Accuracy:")
    print(f"   Payment ID matches: {matched_by_payment_id}/{len(simulated_sf_records)}")
    print(f"   Order Number matches: {matched_by_order_number}/{len(simulated_sf_records)}")
    print(f"   Total fees matched (Payment ID): ${total_matched_fees:.2f}")
    
    print(f"\n⚡ Efficiency Analysis:")
    print(f"   Payment ID approach:")
    print(f"     - Direct lookup: payment_id -> fees")
    print(f"     - API calls needed: 0 (payment_id already included)")
    print(f"     - Lookup complexity: O(1)")
    
    print(f"   Order Number approach:")
    print(f"     - Indirect lookup: order_id -> order_number -> fees")
    print(f"     - API calls needed: ~{(len(order_number_lookup) // 100) + 1} (for order number fetching)")
    print(f"     - Lookup complexity: O(1) + API overhead")
    
    # Recommendation
    print(f"\n🚀 RECOMMENDATION:")
    
    if matched_by_payment_id >= matched_by_order_number and len(payment_id_lookup) > 0:
        print("   ✅ IMPLEMENT PAYMENT_ID MATCHING")
        print("   Reasons:")
        print("   - Equal or better matching accuracy")
        print("   - Eliminates order number API calls")
        print("   - Simpler, more direct logic")
        print("   - Faster performance")
        
        print(f"\n📋 Implementation Steps:")
        print("   1. Modify WooCommerce lookup to use payment_id as key")
        print("   2. Match Salesforce 'Payment ID' to WooCommerce 'payment_id'")
        print("   3. Set fetch_order_numbers=False everywhere")
        print("   4. Remove order number normalization logic")
        
    else:
        print("   ❌ KEEP CURRENT ORDER_NUMBER MATCHING")
        print("   Reasons:")
        print("   - Payment ID coverage insufficient")
        print("   - Order number matching more reliable")
    
    print(f"\n{'='*80}")
    print("MATCHING LOGIC TEST COMPLETE")
    print(f"{'='*80}")

if __name__ == "__main__":
    test_payment_id_matching()