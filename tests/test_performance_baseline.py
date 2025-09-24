#!/usr/bin/env python3
"""
Performance baseline testing for API operations
Measures current performance before optimizations
"""
import sys
import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import statistics

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.salesforce_api import SalesforceAPI
from services.woocommerce_api import WooCommerceAPI

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise for performance testing
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """Track and analyze performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str, additional_data: Dict = None):
        """End timing an operation and record metrics"""
        if operation not in self.start_times:
            return
        
        duration = time.time() - self.start_times[operation]
        
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        metric = {
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        
        if additional_data:
            metric.update(additional_data)
        
        self.metrics[operation].append(metric)
        del self.start_times[operation]
        
        return duration
    
    def get_stats(self, operation: str) -> Dict:
        """Get statistics for an operation"""
        if operation not in self.metrics:
            return {}
        
        durations = [m['duration'] for m in self.metrics[operation]]
        
        return {
            'count': len(durations),
            'min': min(durations),
            'max': max(durations),
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'total': sum(durations)
        }
    
    def print_summary(self):
        """Print performance summary"""
        print("\n" + "=" * 70)
        print("PERFORMANCE BASELINE SUMMARY")
        print("=" * 70)
        
        total_time = 0
        
        for operation, metrics in self.metrics.items():
            stats = self.get_stats(operation)
            total_time += stats.get('total', 0)
            
            print(f"\n{operation.upper()}:")
            print(f"  Count:      {stats.get('count', 0)}")
            print(f"  Min Time:   {stats.get('min', 0):.3f}s")
            print(f"  Max Time:   {stats.get('max', 0):.3f}s")
            print(f"  Mean Time:  {stats.get('mean', 0):.3f}s")
            print(f"  Median:     {stats.get('median', 0):.3f}s")
            print(f"  Total Time: {stats.get('total', 0):.3f}s")
        
        print(f"\nOVERALL TOTAL TIME: {total_time:.3f}s")
    
    def save_results(self, filename: str):
        """Save results to JSON file"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics,
            'summary': {op: self.get_stats(op) for op in self.metrics.keys()}
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✓ Performance results saved to {filename}")

def test_salesforce_performance(tracker: PerformanceTracker):
    """Test Salesforce API performance"""
    print("=" * 60)
    print("SALESFORCE PERFORMANCE TESTING")
    print("=" * 60)
    
    try:
        # Initialize and connect
        tracker.start_timer('sf_init')
        sf_api = SalesforceAPI()
        tracker.end_timer('sf_init')
        
        # Test connection (multiple times for consistency)
        connection_times = []
        for i in range(3):
            tracker.start_timer('sf_connection')
            result = sf_api.test_connection()
            duration = tracker.end_timer('sf_connection', {'success': result['success']})
            connection_times.append(duration)
            
            if not result['success']:
                print(f"✗ Connection test {i+1} failed")
                return False
            
            print(f"✓ Connection test {i+1}: {duration:.3f}s")
        
        # Test reports retrieval (multiple times)
        for i in range(2):
            tracker.start_timer('sf_reports')
            reports = sf_api.get_reports()
            duration = tracker.end_timer('sf_reports', {'count': len(reports)})
            print(f"✓ Reports retrieval {i+1}: {duration:.3f}s ({len(reports)} reports)")
        
        # Test report data retrieval (if reports available)
        if reports:
            # Try to get the sales receipt report
            target_report_id = "00ORl000007JNmTMAW"
            target_report = None
            
            for report in reports:
                if report.get('id') == target_report_id:
                    target_report = report
                    break
            
            if not target_report and reports:
                target_report = reports[0]
            
            if target_report:
                for i in range(2):
                    tracker.start_timer('sf_report_data')
                    report_data = sf_api.get_report_data(target_report['id'])
                    rows = len(report_data) if report_data is not None else 0
                    cols = len(report_data.columns) if report_data is not None else 0
                    duration = tracker.end_timer('sf_report_data', {
                        'report_id': target_report['id'],
                        'rows': rows,
                        'columns': cols
                    })
                    print(f"✓ Report data {i+1}: {duration:.3f}s ({rows} rows, {cols} cols)")
        
        # Test SOQL queries (multiple times)
        test_queries = [
            "SELECT Id, Name FROM Organization LIMIT 1",
            "SELECT Id, Name FROM Account LIMIT 5",
            "SELECT Id, Subject FROM Report LIMIT 10"
        ]
        
        for query in test_queries:
            tracker.start_timer('sf_soql')
            result = sf_api.execute_soql(query)
            rows = len(result) if result is not None else 0
            duration = tracker.end_timer('sf_soql', {
                'query': query[:50],
                'rows': rows
            })
            print(f"✓ SOQL query: {duration:.3f}s ({rows} rows)")
        
        return True
        
    except Exception as e:
        print(f"✗ Salesforce performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_woocommerce_performance(tracker: PerformanceTracker):
    """Test WooCommerce API performance"""
    print("\n" + "=" * 60)
    print("WOOCOMMERCE PERFORMANCE TESTING")
    print("=" * 60)
    
    try:
        # Initialize
        tracker.start_timer('woo_init')
        woo_api = WooCommerceAPI()
        tracker.end_timer('woo_init')
        
        # Test connection (multiple times)
        for i in range(3):
            tracker.start_timer('woo_connection')
            try:
                response = woo_api.wc_api.get("products", params={"per_page": 1})
                success = response.status_code == 200
                duration = tracker.end_timer('woo_connection', {'success': success})
                print(f"✓ Connection test {i+1}: {duration:.3f}s")
            except Exception as e:
                duration = tracker.end_timer('woo_connection', {'success': False})
                print(f"✗ Connection test {i+1} failed: {duration:.3f}s")
        
        # Test orders retrieval with different date ranges
        date_ranges = [
            (datetime.now() - timedelta(days=7), datetime.now()),   # Last 7 days
            (datetime.now() - timedelta(days=30), datetime.now()),  # Last 30 days
        ]
        
        for i, (start_date, end_date) in enumerate(date_ranges):
            tracker.start_timer('woo_orders')
            orders = woo_api.get_orders(
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            duration = tracker.end_timer('woo_orders', {
                'date_range_days': (end_date - start_date).days,
                'count': len(orders)
            })
            print(f"✓ Orders retrieval {i+1}: {duration:.3f}s ({len(orders)} orders, {(end_date - start_date).days} days)")
        
        # Test payments retrieval
        for i, (start_date, end_date) in enumerate(date_ranges):
            tracker.start_timer('woo_payments')
            payments = woo_api.get_payments_paginated(
                start_date=start_date,
                end_date=end_date,
                limit=50
            )
            duration = tracker.end_timer('woo_payments', {
                'date_range_days': (end_date - start_date).days,
                'count': len(payments)
            })
            print(f"✓ Payments retrieval {i+1}: {duration:.3f}s ({len(payments)} payments)")
        
        # Test order lookup if we have orders
        if 'orders' in locals() and orders:
            order_numbers = [order.get('number', '') for order in orders[:10] if order.get('number')]
            
            if order_numbers:
                tracker.start_timer('woo_order_lookup')
                lookup_results = woo_api.get_order_numbers_to_ids(order_numbers)
                duration = tracker.end_timer('woo_order_lookup', {
                    'input_count': len(order_numbers),
                    'result_count': len(lookup_results)
                })
                print(f"✓ Order lookup: {duration:.3f}s ({len(order_numbers)} -> {len(lookup_results)})")
        
        return True
        
    except Exception as e:
        print(f"✗ WooCommerce performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_processing_performance(tracker: PerformanceTracker):
    """Test data processing performance"""
    print("\n" + "=" * 60)
    print("DATA PROCESSING PERFORMANCE TESTING")
    print("=" * 60)
    
    try:
        import polars as pl
        from ui.operations.sales_receipt_import import SalesReceiptImport
        
        # Initialize operation
        tracker.start_timer('data_proc_init')
        operation = SalesReceiptImport()
        tracker.end_timer('data_proc_init')
        
        # Create test data of varying sizes
        test_sizes = [100, 500, 1000]
        
        for size in test_sizes:
            print(f"\nTesting with {size} rows...")
            
            # Generate test data
            tracker.start_timer('data_generation')
            test_data = {
                'Account Name': [f'Test Account {i}' for i in range(size)],
                'Date Paid': ['2024-01-15'] * size,
                'Webstore Order #': [f'WOO-{i:05d}' for i in range(size)],
                'Class': ['02 - Sales'] * size,
                'SKU': [f'TEST-SKU-{i}' for i in range(size)],
                'Product Type': ['Standard Product'] * size,
                'Quantity': [1] * size,
                'Unit Price': ['100.00'] * size,
                'Tax': [8.25] * size,
                'Order Amount (Grand Total)': ['108.25'] * size,
                'Payment ID': [f'pi_test{i}' for i in range(size)],
                'Shipping Country': ['United States'] * size,
                'Billing Address Line 1': ['123 Main St'] * size,
                'Billing City': ['New York'] * size,
                'Billing State/Province (text only)': ['NY'] * size,
                'Billing Zip/Postal Code': ['10001'] * size,
                'Shipping Address Line 1': ['123 Main St'] * size,
                'Shipping City': ['New York'] * size,
                'Shipping State/Province (text only)': ['NY'] * size,
                'Shipping Zip/Postal Code': ['10001'] * size,
                'Sales Tax (Reason)': ['NY Sales Tax'] * size
            }
            
            df = pl.DataFrame(test_data)
            duration = tracker.end_timer('data_generation', {'rows': size})
            print(f"  ✓ Data generation: {duration:.3f}s")
            
            # Test validation
            tracker.start_timer('data_validation')
            errors = operation._validate_data(df)
            duration = tracker.end_timer('data_validation', {
                'rows': size,
                'errors': len(errors)
            })
            print(f"  ✓ Data validation: {duration:.3f}s ({len(errors)} errors)")
            
            # Test filtering
            tracker.start_timer('data_filtering')
            filtered_df = operation._filter_rows(df)
            duration = tracker.end_timer('data_filtering', {
                'input_rows': size,
                'output_rows': len(filtered_df)
            })
            print(f"  ✓ Data filtering: {duration:.3f}s ({size} -> {len(filtered_df)} rows)")
            
            # Test transformations
            tracker.start_timer('data_transformations')
            transformed_df = operation._apply_transformations(filtered_df)
            duration = tracker.end_timer('data_transformations', {
                'rows': len(filtered_df)
            })
            print(f"  ✓ Data transformations: {duration:.3f}s")
        
        return True
        
    except Exception as e:
        print(f"✗ Data processing performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all performance baseline tests"""
    print("PERFORMANCE BASELINE TESTING")
    print("This will measure current API and processing performance")
    print("Results will be saved for comparison after optimizations")
    print()
    
    tracker = PerformanceTracker()
    all_success = True
    
    # Test Salesforce performance
    success = test_salesforce_performance(tracker)
    all_success &= success
    
    # Test WooCommerce performance
    success = test_woocommerce_performance(tracker)
    all_success &= success
    
    # Test data processing performance
    success = test_data_processing_performance(tracker)
    all_success &= success
    
    # Print summary
    tracker.print_summary()
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"performance_baseline_{timestamp}.json"
    tracker.save_results(filename)
    
    # Final results
    print("\n" + "=" * 70)
    if all_success:
        print("🎉 PERFORMANCE BASELINE TESTING COMPLETED!")
        print("All systems are functioning correctly.")
        print("Performance metrics have been recorded for comparison.")
    else:
        print("❌ SOME PERFORMANCE TESTS FAILED!")
        print("Please review the errors above.")
    print("=" * 70)
    
    return all_success

if __name__ == "__main__":
    main()