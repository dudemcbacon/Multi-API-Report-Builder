#!/usr/bin/env python3
"""
Performance testing framework for AIOHTTP vs current API implementations
Tests both Salesforce and WooCommerce APIs for performance comparison
"""
import sys
import os
import time
import asyncio
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise during testing
logger = logging.getLogger(__name__)

class PerformanceMetrics:
    """Collect and analyze performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def record_metric(self, test_name: str, duration: float, success: bool, 
                     additional_data: Dict = None):
        """Record a performance metric"""
        if test_name not in self.metrics:
            self.metrics[test_name] = []
        
        metric = {
            'duration': duration,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        if additional_data:
            metric.update(additional_data)
        
        self.metrics[test_name].append(metric)
    
    def get_stats(self, test_name: str) -> Dict:
        """Get statistics for a test"""
        if test_name not in self.metrics:
            return {}
        
        durations = [m['duration'] for m in self.metrics[test_name] if m['success']]
        successes = [m['success'] for m in self.metrics[test_name]]
        
        if not durations:
            return {'success_rate': 0, 'count': len(self.metrics[test_name])}
        
        return {
            'count': len(durations),
            'success_rate': sum(successes) / len(successes),
            'min_time': min(durations),
            'max_time': max(durations),
            'avg_time': statistics.mean(durations),
            'median_time': statistics.median(durations),
            'total_time': sum(durations)
        }
    
    def compare_tests(self, test1: str, test2: str) -> Dict:
        """Compare two tests and return improvement metrics"""
        stats1 = self.get_stats(test1)
        stats2 = self.get_stats(test2)
        
        if not stats1 or not stats2:
            return {}
        
        return {
            'speed_improvement': stats1['avg_time'] / stats2['avg_time'],
            'time_saved': stats1['avg_time'] - stats2['avg_time'],
            'reliability_change': stats2['success_rate'] - stats1['success_rate']
        }

class CurrentAPITester:
    """Test current API implementations"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
    
    def test_salesforce_current(self, num_tests: int = 5) -> Dict:
        """Test current Salesforce API performance"""
        print(f"Testing current Salesforce API ({num_tests} tests)...")
        
        try:
            from services.salesforce_api import SalesforceAPI
            
            sf_api = SalesforceAPI()
            
            # Test connection
            for i in range(num_tests):
                start_time = time.time()
                try:
                    result = sf_api.test_connection()
                    duration = time.time() - start_time
                    success = result.get('success', False)
                    
                    self.metrics.record_metric('sf_connection_current', duration, success)
                    print(f"  Connection test {i+1}: {duration:.3f}s {'✓' if success else '✗'}")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('sf_connection_current', duration, False)
                    print(f"  Connection test {i+1}: {duration:.3f}s ✗ ({e})")
            
            # Test reports retrieval
            for i in range(min(num_tests, 3)):  # Fewer tests for expensive operations
                start_time = time.time()
                try:
                    reports = sf_api.get_reports()
                    duration = time.time() - start_time
                    success = isinstance(reports, list) and len(reports) > 0
                    
                    self.metrics.record_metric('sf_reports_current', duration, success, 
                                             {'report_count': len(reports) if reports else 0})
                    print(f"  Reports test {i+1}: {duration:.3f}s {'✓' if success else '✗'} ({len(reports) if reports else 0} reports)")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('sf_reports_current', duration, False)
                    print(f"  Reports test {i+1}: {duration:.3f}s ✗ ({e})")
            
            return self.metrics.get_stats('sf_connection_current')
            
        except Exception as e:
            print(f"Error testing current Salesforce API: {e}")
            return {}
    
    def test_woocommerce_current(self, num_tests: int = 5) -> Dict:
        """Test current WooCommerce API performance"""
        print(f"Testing current WooCommerce API ({num_tests} tests)...")
        
        try:
            from services.woocommerce_api import WooCommerceAPI
            
            woo_api = WooCommerceAPI()
            
            # Test connection
            for i in range(num_tests):
                start_time = time.time()
                try:
                    response = woo_api.wc_api.get("products", params={"per_page": 1})
                    duration = time.time() - start_time
                    success = response.status_code == 200
                    
                    self.metrics.record_metric('woo_connection_current', duration, success)
                    print(f"  Connection test {i+1}: {duration:.3f}s {'✓' if success else '✗'}")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('woo_connection_current', duration, False)
                    print(f"  Connection test {i+1}: {duration:.3f}s ✗ ({e})")
            
            # Test orders retrieval
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            for i in range(min(num_tests, 3)):  # Fewer tests for expensive operations
                start_time = time.time()
                try:
                    orders = woo_api.get_orders(start_date=start_date, end_date=end_date, limit=10)
                    duration = time.time() - start_time
                    success = isinstance(orders, list)
                    
                    self.metrics.record_metric('woo_orders_current', duration, success,
                                             {'order_count': len(orders) if orders else 0})
                    print(f"  Orders test {i+1}: {duration:.3f}s {'✓' if success else '✗'} ({len(orders) if orders else 0} orders)")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('woo_orders_current', duration, False)
                    print(f"  Orders test {i+1}: {duration:.3f}s ✗ ({e})")
            
            return self.metrics.get_stats('woo_connection_current')
            
        except Exception as e:
            print(f"Error testing current WooCommerce API: {e}")
            return {}

class AIOHTTPTester:
    """Test AIOHTTP implementations"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
    
    async def test_salesforce_aiohttp(self, num_tests: int = 5) -> Dict:
        """Test AIOHTTP Salesforce API performance"""
        print(f"Testing AIOHTTP Salesforce API ({num_tests} tests)...")
        
        try:
            from test_implementations.async_salesforce_api import AsyncSalesforceAPI
            
            sf_api = AsyncSalesforceAPI()
            
            # Test connection
            for i in range(num_tests):
                start_time = time.time()
                try:
                    result = await sf_api.test_connection()
                    duration = time.time() - start_time
                    success = result.get('success', False)
                    
                    self.metrics.record_metric('sf_connection_aiohttp', duration, success)
                    print(f"  Connection test {i+1}: {duration:.3f}s {'✓' if success else '✗'}")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('sf_connection_aiohttp', duration, False)
                    print(f"  Connection test {i+1}: {duration:.3f}s ✗ ({e})")
            
            # Test concurrent connections
            start_time = time.time()
            try:
                tasks = [sf_api.test_connection() for _ in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                duration = time.time() - start_time
                
                successes = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
                success_rate = successes / len(results)
                
                self.metrics.record_metric('sf_concurrent_aiohttp', duration, success_rate > 0.5,
                                         {'concurrent_requests': len(results), 'success_rate': success_rate})
                print(f"  Concurrent test: {duration:.3f}s {'✓' if success_rate > 0.5 else '✗'} ({successes}/{len(results)} succeeded)")
                
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_metric('sf_concurrent_aiohttp', duration, False)
                print(f"  Concurrent test: {duration:.3f}s ✗ ({e})")
            
            await sf_api.close()
            return self.metrics.get_stats('sf_connection_aiohttp')
            
        except Exception as e:
            print(f"Error testing AIOHTTP Salesforce API: {e}")
            return {}
    
    async def test_woocommerce_aiohttp(self, num_tests: int = 5) -> Dict:
        """Test AIOHTTP WooCommerce API performance"""
        print(f"Testing AIOHTTP WooCommerce API ({num_tests} tests)...")
        
        try:
            from test_implementations.async_woocommerce_api import AsyncWooCommerceAPI
            
            woo_api = AsyncWooCommerceAPI()
            
            # Test connection
            for i in range(num_tests):
                start_time = time.time()
                try:
                    result = await woo_api.test_connection()
                    duration = time.time() - start_time
                    success = result.get('success', False)
                    
                    self.metrics.record_metric('woo_connection_aiohttp', duration, success)
                    print(f"  Connection test {i+1}: {duration:.3f}s {'✓' if success else '✗'}")
                    
                except Exception as e:
                    duration = time.time() - start_time
                    self.metrics.record_metric('woo_connection_aiohttp', duration, False)
                    print(f"  Connection test {i+1}: {duration:.3f}s ✗ ({e})")
            
            # Test concurrent connections
            start_time = time.time()
            try:
                tasks = [woo_api.test_connection() for _ in range(5)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                duration = time.time() - start_time
                
                successes = sum(1 for r in results if isinstance(r, dict) and r.get('success', False))
                success_rate = successes / len(results)
                
                self.metrics.record_metric('woo_concurrent_aiohttp', duration, success_rate > 0.5,
                                         {'concurrent_requests': len(results), 'success_rate': success_rate})
                print(f"  Concurrent test: {duration:.3f}s {'✓' if success_rate > 0.5 else '✗'} ({successes}/{len(results)} succeeded)")
                
            except Exception as e:
                duration = time.time() - start_time
                self.metrics.record_metric('woo_concurrent_aiohttp', duration, False)
                print(f"  Concurrent test: {duration:.3f}s ✗ ({e})")
            
            await woo_api.close()
            return self.metrics.get_stats('woo_connection_aiohttp')
            
        except Exception as e:
            print(f"Error testing AIOHTTP WooCommerce API: {e}")
            return {}

def print_performance_summary(current_tester: CurrentAPITester, aiohttp_tester: AIOHTTPTester):
    """Print comprehensive performance summary"""
    print("\n" + "="*80)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("="*80)
    
    # Salesforce comparison
    sf_current = current_tester.metrics.get_stats('sf_connection_current')
    sf_aiohttp = aiohttp_tester.metrics.get_stats('sf_connection_aiohttp')
    
    print(f"\nSALESFORCE API COMPARISON:")
    if sf_current and sf_aiohttp:
        improvement = sf_current['avg_time'] / sf_aiohttp['avg_time']
        print(f"  Current API:  {sf_current['avg_time']:.3f}s average")
        print(f"  AIOHTTP API:  {sf_aiohttp['avg_time']:.3f}s average")
        print(f"  Improvement:  {improvement:.1f}x faster")
        
        if improvement > 1.5:
            print(f"  ✓ SIGNIFICANT IMPROVEMENT")
        elif improvement > 1.1:
            print(f"  ✓ Moderate improvement")
        else:
            print(f"  ⚠ Minimal improvement")
    else:
        print("  Unable to compare - insufficient data")
    
    # WooCommerce comparison
    woo_current = current_tester.metrics.get_stats('woo_connection_current')
    woo_aiohttp = aiohttp_tester.metrics.get_stats('woo_connection_aiohttp')
    
    print(f"\nWOOCOMMERCE API COMPARISON:")
    if woo_current and woo_aiohttp:
        improvement = woo_current['avg_time'] / woo_aiohttp['avg_time']
        print(f"  Current API:  {woo_current['avg_time']:.3f}s average")
        print(f"  AIOHTTP API:  {woo_aiohttp['avg_time']:.3f}s average")
        print(f"  Improvement:  {improvement:.1f}x faster")
        
        if improvement > 1.5:
            print(f"  ✓ SIGNIFICANT IMPROVEMENT")
        elif improvement > 1.1:
            print(f"  ✓ Moderate improvement")
        else:
            print(f"  ⚠ Minimal improvement")
    else:
        print("  Unable to compare - insufficient data")
    
    # Concurrency benefits
    sf_concurrent = aiohttp_tester.metrics.get_stats('sf_concurrent_aiohttp')
    woo_concurrent = aiohttp_tester.metrics.get_stats('woo_concurrent_aiohttp')
    
    print(f"\nCONCURRENCY BENEFITS:")
    if sf_concurrent:
        print(f"  Salesforce concurrent (5 requests): {sf_concurrent['avg_time']:.3f}s")
    if woo_concurrent:
        print(f"  WooCommerce concurrent (5 requests): {woo_concurrent['avg_time']:.3f}s")

def main():
    """Run performance comparison tests"""
    print("AIOHTTP PERFORMANCE TESTING")
    print("="*80)
    print("This will test AIOHTTP performance against current implementations")
    print("for both Salesforce and WooCommerce APIs")
    
    current_tester = CurrentAPITester()
    aiohttp_tester = AIOHTTPTester()
    
    print("\n" + "="*80)
    print("PHASE 1: TESTING CURRENT API IMPLEMENTATIONS")
    print("="*80)
    
    # Test current implementations
    current_tester.test_salesforce_current(num_tests=3)
    current_tester.test_woocommerce_current(num_tests=3)
    
    print("\n" + "="*80)
    print("PHASE 2: TESTING AIOHTTP IMPLEMENTATIONS")
    print("="*80)
    
    # Test AIOHTTP implementations
    asyncio.run(aiohttp_tester.test_salesforce_aiohttp(num_tests=3))
    asyncio.run(aiohttp_tester.test_woocommerce_aiohttp(num_tests=3))
    
    # Print results
    print_performance_summary(current_tester, aiohttp_tester)
    
    # Save results
    results = {
        'timestamp': datetime.now().isoformat(),
        'current_metrics': current_tester.metrics.metrics,
        'aiohttp_metrics': aiohttp_tester.metrics.metrics
    }
    
    with open('aiohttp_performance_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📊 Detailed results saved to aiohttp_performance_results.json")
    
    print("\n" + "="*80)
    print("RECOMMENDATION:")
    
    # Analyze results and provide recommendation
    sf_current = current_tester.metrics.get_stats('sf_connection_current')
    sf_aiohttp = aiohttp_tester.metrics.get_stats('sf_connection_aiohttp')
    woo_current = current_tester.metrics.get_stats('woo_connection_current')
    woo_aiohttp = aiohttp_tester.metrics.get_stats('woo_connection_aiohttp')
    
    total_improvement = 0
    valid_comparisons = 0
    
    if sf_current and sf_aiohttp:
        total_improvement += sf_current['avg_time'] / sf_aiohttp['avg_time']
        valid_comparisons += 1
    
    if woo_current and woo_aiohttp:
        total_improvement += woo_current['avg_time'] / woo_aiohttp['avg_time']
        valid_comparisons += 1
    
    if valid_comparisons > 0:
        avg_improvement = total_improvement / valid_comparisons
        
        if avg_improvement > 2.0:
            print("🚀 HIGHLY RECOMMENDED: Implement AIOHTTP")
            print(f"   Average improvement: {avg_improvement:.1f}x faster")
            print("   Significant performance gains justify implementation")
        elif avg_improvement > 1.5:
            print("✅ RECOMMENDED: Implement AIOHTTP")
            print(f"   Average improvement: {avg_improvement:.1f}x faster")
            print("   Good performance gains justify implementation")
        elif avg_improvement > 1.2:
            print("⚠️  CONSIDER: AIOHTTP provides moderate improvement")
            print(f"   Average improvement: {avg_improvement:.1f}x faster")
            print("   Implementation depends on performance requirements")
        else:
            print("❌ NOT RECOMMENDED: Minimal improvement")
            print(f"   Average improvement: {avg_improvement:.1f}x faster")
            print("   Implementation overhead not justified")
    else:
        print("❓ INCONCLUSIVE: Unable to compare performance")
        print("   Check test failures and retry")
    
    print("="*80)

if __name__ == "__main__":
    main()