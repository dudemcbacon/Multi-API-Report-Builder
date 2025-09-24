#!/usr/bin/env python3
"""
Test script to verify that order numbers are being fetched correctly
"""
import logging
from src.services.woocommerce_api import WooCommerceAPI

# Set up logging to see debug output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_order_numbers():
    print("Testing WooCommerce order number fetching...")
    print("-" * 50)
    
    # Initialize API
    api = WooCommerceAPI()
    
    # Test connection first
    print("Testing connection...")
    result = api.test_connection()
    if not result.get('success'):
        print(f"Connection failed: {result.get('error')}")
        return
    
    print(f"Connected to: {result.get('store_name')}")
    print("-" * 50)
    
    # Test with order numbers (default)
    print("Fetching transactions WITH order numbers...")
    import time
    start_time = time.time()
    transactions_df = api.get_transactions(per_page=10, fetch_order_numbers=True)
    with_orders_time = time.time() - start_time
    
    # Test without order numbers for comparison
    print("\nFetching transactions WITHOUT order numbers...")
    start_time = time.time()
    transactions_no_orders_df = api.get_transactions(per_page=10, fetch_order_numbers=False)
    without_orders_time = time.time() - start_time
    
    print(f"\nPerformance comparison:")
    print(f"  With order numbers: {with_orders_time:.2f} seconds")
    print(f"  Without order numbers: {without_orders_time:.2f} seconds")
    print(f"  Time saved by skipping: {with_orders_time - without_orders_time:.2f} seconds")
    
    if transactions_df is None or len(transactions_df) == 0:
        print("No transactions found")
        return
    
    print(f"\nFound {len(transactions_df)} transactions")
    print("\nColumns in DataFrame:")
    print(list(transactions_df.columns))
    
    # Display first few transactions with order info
    print("\nFirst 5 transactions with order information:")
    print("-" * 80)
    
    # Select relevant columns for display
    display_columns = ['transaction_id', 'order_id', 'order_number', 'date', 'amount', 'payment_method']
    available_columns = [col for col in display_columns if col in transactions_df.columns]
    
    subset_df = transactions_df.select(available_columns).head(5)
    
    for row in subset_df.iter_rows(named=True):
        print(f"Transaction ID: {row.get('transaction_id', 'N/A')}")
        print(f"  Order ID: {row.get('order_id', 'N/A')}")
        print(f"  Order Number: {row.get('order_number', 'N/A')}")
        print(f"  Date: {row.get('date', 'N/A')}")
        print(f"  Amount: ${row.get('amount', 0):.2f}")
        print(f"  Payment Method: {row.get('payment_method', 'N/A')}")
        print("-" * 40)
    
    # Check how many transactions have order numbers
    if 'order_number' in transactions_df.columns:
        with_order_nums = len(transactions_df.filter(transactions_df['order_number'] != ''))
        print(f"\nTransactions with order numbers: {with_order_nums}/{len(transactions_df)}")

if __name__ == "__main__":
    test_order_numbers()