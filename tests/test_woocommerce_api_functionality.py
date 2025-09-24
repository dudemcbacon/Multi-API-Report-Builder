#!/usr/bin/env python3
"""
Comprehensive tests for WooCommerce API functionality
Tests connection, authentication, and data retrieval without making changes
"""
import sys
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.woocommerce_api import WooCommerceAPI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_woocommerce_connection():
    """Test WooCommerce connection and authentication"""
    print("=" * 60)
    print("TESTING WOOCOMMERCE API CONNECTION")
    print("=" * 60)
    
    try:
        # Initialize WooCommerce API
        woo_api = WooCommerceAPI()
        print("✓ WooCommerceAPI initialized successfully")
        print(f"✓ Store URL: {woo_api.STORE_URL}")
        
        # Test connection with a simple API call
        print("\nTesting connection with system status...")
        start_time = time.time()
        
        # Test with a lightweight API call
        try:
            # Get system status (lightweight call)
            response = woo_api.wc_api.get("system_status")
            connection_time = time.time() - start_time
            
            if response.status_code == 200:
                print("✓ CONNECTION SUCCESSFUL!")
                data = response.json()
                print(f"  - WooCommerce Version: {data.get('environment', {}).get('version', 'Unknown')}")
                print(f"  - WordPress Version: {data.get('environment', {}).get('wp_version', 'Unknown')}")
                print(f"  - Server Info: {data.get('environment', {}).get('server_info', 'Unknown')}")
                return True, woo_api, connection_time
            else:
                print(f"✗ CONNECTION FAILED! Status: {response.status_code}")
                print(f"  - Response: {response.text}")
                return False, None, connection_time
                
        except Exception as api_error:
            # If system_status fails, try a simpler endpoint
            print(f"System status failed: {api_error}")
            print("Trying alternative connection test...")
            
            try:
                response = woo_api.wc_api.get("products", params={"per_page": 1})
                connection_time = time.time() - start_time
                
                if response.status_code == 200:
                    print("✓ CONNECTION SUCCESSFUL! (via products endpoint)")
                    products = response.json()
                    print(f"  - API Access: Working")
                    print(f"  - Sample Response: {len(products)} products returned")
                    return True, woo_api, connection_time
                else:
                    print(f"✗ CONNECTION FAILED! Status: {response.status_code}")
                    return False, None, connection_time
                    
            except Exception as e:
                print(f"✗ All connection tests failed: {e}")
                return False, None, time.time() - start_time
            
    except Exception as e:
        print(f"✗ Exception during connection test: {e}")
        import traceback
        traceback.print_exc()
        return False, None, 0

def test_woocommerce_orders(woo_api: WooCommerceAPI):
    """Test WooCommerce orders retrieval"""
    print("\n" + "=" * 60)
    print("TESTING WOOCOMMERCE ORDERS RETRIEVAL")
    print("=" * 60)
    
    try:
        print("Retrieving recent orders...")
        start_time = time.time()
        
        # Get orders from the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        orders = woo_api.get_orders(
            start_date=start_date,
            end_date=end_date,
            limit=10  # Limit for testing
        )
        
        orders_time = time.time() - start_time
        print(f"✓ Orders retrieved in {orders_time:.2f} seconds")
        print(f"✓ Found {len(orders)} orders")
        
        if orders:
            print("\nSample orders:")
            for i, order in enumerate(orders[:3]):  # Show first 3 orders
                print(f"  {i+1}. Order #{order.get('number', 'Unknown')} (ID: {order.get('id', 'Unknown')})")
                print(f"     Status: {order.get('status', 'Unknown')}")
                print(f"     Total: {order.get('total', 'Unknown')}")
                print(f"     Date: {order.get('date_created', 'Unknown')}")
            
            if len(orders) > 3:
                print(f"     ... and {len(orders) - 3} more orders")
        
        return True, orders, orders_time
        
    except Exception as e:
        print(f"✗ Exception during orders retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, [], 0

def test_woocommerce_payments(woo_api: WooCommerceAPI):
    """Test WooCommerce payments retrieval"""
    print("\n" + "=" * 60)
    print("TESTING WOOCOMMERCE PAYMENTS RETRIEVAL")
    print("=" * 60)
    
    try:
        print("Retrieving recent payments...")
        start_time = time.time()
        
        # Get payments from the last 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        payments = woo_api.get_payments_paginated(
            start_date=start_date,
            end_date=end_date,
            limit=10  # Limit for testing
        )
        
        payments_time = time.time() - start_time
        print(f"✓ Payments retrieved in {payments_time:.2f} seconds")
        print(f"✓ Found {len(payments)} payments")
        
        if payments:
            print("\nSample payments:")
            for i, payment in enumerate(payments[:3]):  # Show first 3 payments
                print(f"  {i+1}. Payment ID: {payment.get('id', 'Unknown')}")
                print(f"     Amount: {payment.get('amount', 'Unknown')}")
                print(f"     Status: {payment.get('status', 'Unknown')}")
                print(f"     Date: {payment.get('date', 'Unknown')}")
            
            if len(payments) > 3:
                print(f"     ... and {len(payments) - 3} more payments")
        
        return True, payments, payments_time
        
    except Exception as e:
        print(f"✗ Exception during payments retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, [], 0

def test_woocommerce_order_lookup(woo_api: WooCommerceAPI, orders: List[Dict]):
    """Test WooCommerce order number lookup functionality"""
    print("\n" + "=" * 60)
    print("TESTING WOOCOMMERCE ORDER LOOKUP")
    print("=" * 60)
    
    if not orders:
        print("✗ No orders available for testing")
        return False, 0
    
    try:
        # Test order lookup with a few sample orders
        test_orders = orders[:3] if len(orders) >= 3 else orders
        order_numbers = [order.get('number', '') for order in test_orders if order.get('number')]
        
        if not order_numbers:
            print("✗ No valid order numbers found for testing")
            return False, 0
        
        print(f"Testing lookup for {len(order_numbers)} order numbers...")
        start_time = time.time()
        
        # Test the order lookup method
        lookup_results = woo_api.get_order_numbers_to_ids(order_numbers)
        
        lookup_time = time.time() - start_time
        print(f"✓ Order lookup completed in {lookup_time:.2f} seconds")
        print(f"✓ Lookup results: {len(lookup_results)} mappings")
        
        if lookup_results:
            print("\nLookup results:")
            for order_num, order_id in list(lookup_results.items())[:3]:
                print(f"  Order #{order_num} -> ID: {order_id}")
        
        return True, lookup_time
        
    except Exception as e:
        print(f"✗ Exception during order lookup: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def test_woocommerce_fee_calculation(woo_api: WooCommerceAPI, payments: List[Dict]):
    """Test WooCommerce fee calculation functionality"""
    print("\n" + "=" * 60)
    print("TESTING WOOCOMMERCE FEE CALCULATION")
    print("=" * 60)
    
    if not payments:
        print("⚠ No payments available for fee calculation testing")
        return True, 0  # Not a failure, just no data
    
    try:
        print(f"Testing fee calculation for {len(payments)} payments...")
        start_time = time.time()
        
        total_fees = 0
        payments_with_fees = 0
        
        for payment in payments:
            # Check if payment has fee information
            if 'fee' in payment or 'fees' in payment:
                fee_amount = payment.get('fee', payment.get('fees', 0))
                if fee_amount and fee_amount > 0:
                    total_fees += float(fee_amount)
                    payments_with_fees += 1
        
        calc_time = time.time() - start_time
        print(f"✓ Fee calculation completed in {calc_time:.2f} seconds")
        print(f"✓ Payments with fees: {payments_with_fees}/{len(payments)}")
        print(f"✓ Total fees calculated: ${total_fees:.2f}")
        
        return True, calc_time
        
    except Exception as e:
        print(f"✗ Exception during fee calculation: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def test_woocommerce_performance_summary(connection_time: float, orders_time: float, 
                                        payments_time: float, lookup_time: float, calc_time: float):
    """Summarize performance metrics"""
    print("\n" + "=" * 60)
    print("WOOCOMMERCE API PERFORMANCE SUMMARY")
    print("=" * 60)
    
    total_time = connection_time + orders_time + payments_time + lookup_time + calc_time
    
    print(f"Connection Time:       {connection_time:.2f} seconds")
    print(f"Orders Retrieval:      {orders_time:.2f} seconds")
    print(f"Payments Retrieval:    {payments_time:.2f} seconds")
    print(f"Order Lookup Time:     {lookup_time:.2f} seconds")
    print(f"Fee Calculation:       {calc_time:.2f} seconds")
    print(f"Total Test Time:       {total_time:.2f} seconds")
    
    # Performance assessment
    print("\nPerformance Assessment:")
    if connection_time < 3:
        print("✓ Connection speed: Good")
    elif connection_time < 8:
        print("⚠ Connection speed: Moderate")
    else:
        print("✗ Connection speed: Slow")
    
    if orders_time < 5:
        print("✓ Orders retrieval: Good")
    elif orders_time < 15:
        print("⚠ Orders retrieval: Moderate")
    else:
        print("✗ Orders retrieval: Slow")
    
    if payments_time < 10:
        print("✓ Payments retrieval: Good")
    elif payments_time < 30:
        print("⚠ Payments retrieval: Moderate")
    else:
        print("✗ Payments retrieval: Slow")

def main():
    """Run all WooCommerce API tests"""
    print("WOOCOMMERCE API FUNCTIONALITY TESTS")
    print("This will test connection, authentication, and data retrieval")
    print("No modifications will be made to your data or configuration")
    print()
    
    all_success = True
    connection_time = orders_time = payments_time = lookup_time = calc_time = 0
    
    # Test 1: Connection
    success, woo_api, connection_time = test_woocommerce_connection()
    if not success:
        print("\n✗ ABORTING TESTS - Could not establish WooCommerce connection")
        return False
    all_success &= success
    
    # Test 2: Orders
    success, orders, orders_time = test_woocommerce_orders(woo_api)
    all_success &= success
    
    # Test 3: Payments
    success, payments, payments_time = test_woocommerce_payments(woo_api)
    all_success &= success
    
    # Test 4: Order Lookup
    success, lookup_time = test_woocommerce_order_lookup(woo_api, orders)
    all_success &= success
    
    # Test 5: Fee Calculation
    success, calc_time = test_woocommerce_fee_calculation(woo_api, payments)
    all_success &= success
    
    # Performance Summary
    test_woocommerce_performance_summary(connection_time, orders_time, payments_time, lookup_time, calc_time)
    
    # Final Results
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ALL WOOCOMMERCE API TESTS PASSED!")
        print("Your WooCommerce API integration is working correctly.")
    else:
        print("❌ SOME WOOCOMMERCE API TESTS FAILED!")
        print("Please review the errors above before proceeding with optimizations.")
    print("=" * 60)
    
    return all_success

if __name__ == "__main__":
    main()