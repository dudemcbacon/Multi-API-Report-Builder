#!/usr/bin/env python3
"""
Focused test to demonstrate concurrency benefits of AIOHTTP
"""
import sys
import os
import time
import asyncio
from datetime import datetime

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_sequential_vs_concurrent():
    """Test sequential vs concurrent WooCommerce API calls"""
    print("CONCURRENCY PERFORMANCE TEST")
    print("=" * 60)
    
    try:
        from test_implementations.async_woocommerce_api import AsyncWooCommerceAPI
        
        async with AsyncWooCommerceAPI() as woo_api:
            num_requests = 5
            
            # Test sequential requests
            print(f"Testing {num_requests} sequential requests...")
            start_time = time.time()
            
            sequential_results = []
            for i in range(num_requests):
                result = await woo_api.test_connection()
                sequential_results.append(result)
                print(f"  Request {i+1}: {result.get('response_time', 0):.3f}s")
            
            sequential_total = time.time() - start_time
            print(f"Sequential total: {sequential_total:.3f}s")
            
            # Test concurrent requests
            print(f"\nTesting {num_requests} concurrent requests...")
            start_time = time.time()
            
            tasks = [woo_api.test_connection() for _ in range(num_requests)]
            concurrent_results = await asyncio.gather(*tasks)
            
            concurrent_total = time.time() - start_time
            print(f"Concurrent total: {concurrent_total:.3f}s")
            
            # Calculate improvement
            improvement = sequential_total / concurrent_total
            print(f"\nIMPROVEMENT: {improvement:.1f}x faster with concurrency")
            
            # Success rates
            sequential_success = sum(1 for r in sequential_results if r.get('success', False))
            concurrent_success = sum(1 for r in concurrent_results if r.get('success', False))
            
            print(f"Sequential success rate: {sequential_success}/{num_requests}")
            print(f"Concurrent success rate: {concurrent_success}/{num_requests}")
            
            return improvement, sequential_success, concurrent_success
    
    except Exception as e:
        print(f"Error in concurrency test: {e}")
        return 0, 0, 0

async def test_batch_operations():
    """Test batch operations with different API endpoints"""
    print("\nBATCH OPERATIONS TEST")
    print("=" * 60)
    
    try:
        from test_implementations.async_woocommerce_api import AsyncWooCommerceAPI
        
        async with AsyncWooCommerceAPI() as woo_api:
            # Test multiple different endpoints concurrently
            endpoints = [
                'products?per_page=1',
                'orders?per_page=1',
                'customers?per_page=1',
                'coupons?per_page=1',
                'taxes?per_page=1'
            ]
            
            print(f"Testing {len(endpoints)} different endpoints concurrently...")
            start_time = time.time()
            
            results = await woo_api.batch_api_calls(endpoints)
            
            batch_total = time.time() - start_time
            print(f"Batch API calls: {batch_total:.3f}s")
            print(f"Successful calls: {len(results)}/{len(endpoints)}")
            
            # Test sequential calls to same endpoints
            print(f"\nTesting same endpoints sequentially...")
            start_time = time.time()
            
            sequential_results = []
            for endpoint in endpoints:
                url = f"{woo_api.api_base_url}/{endpoint}"
                result = await woo_api._make_api_call(url)
                if result:
                    sequential_results.append(result)
            
            sequential_total = time.time() - start_time
            print(f"Sequential API calls: {sequential_total:.3f}s")
            print(f"Successful calls: {len(sequential_results)}/{len(endpoints)}")
            
            if sequential_total > 0:
                batch_improvement = sequential_total / batch_total
                print(f"\nBATCH IMPROVEMENT: {batch_improvement:.1f}x faster")
                return batch_improvement
            else:
                print("\nUnable to calculate batch improvement")
                return 0
    
    except Exception as e:
        print(f"Error in batch test: {e}")
        return 0

async def test_real_world_scenario():
    """Test a real-world scenario with multiple operations"""
    print("\nREAL-WORLD SCENARIO TEST")
    print("=" * 60)
    
    try:
        from test_implementations.async_woocommerce_api import AsyncWooCommerceAPI
        
        async with AsyncWooCommerceAPI() as woo_api:
            # Simulate a real-world scenario:
            # 1. Get recent orders
            # 2. Get payment information
            # 3. Get product details
            # 4. Get customer information
            
            print("Simulating real-world API usage scenario...")
            start_time = time.time()
            
            # Get recent orders
            end_date = datetime.now()
            start_date = datetime.now().replace(day=1)  # This month
            
            tasks = [
                woo_api.get_orders(start_date, end_date, limit=5),
                woo_api.get_payments_paginated(start_date, end_date, limit=5),
                woo_api.get_products_paginated(limit=5),
                woo_api.test_connection()  # Connection test
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            scenario_total = time.time() - start_time
            print(f"Real-world scenario: {scenario_total:.3f}s")
            
            # Count successful operations
            successful_ops = sum(1 for r in results if not isinstance(r, Exception) and r)
            print(f"Successful operations: {successful_ops}/{len(tasks)}")
            
            # Show data retrieved
            for i, result in enumerate(results):
                if isinstance(result, list):
                    print(f"  Operation {i+1}: {len(result)} items retrieved")
                elif isinstance(result, dict):
                    print(f"  Operation {i+1}: {result.get('success', 'Unknown status')}")
                elif isinstance(result, Exception):
                    print(f"  Operation {i+1}: ERROR - {result}")
                else:
                    print(f"  Operation {i+1}: {type(result)}")
            
            return scenario_total, successful_ops
    
    except Exception as e:
        print(f"Error in real-world scenario: {e}")
        return 0, 0

async def main():
    """Run all performance tests"""
    print("AIOHTTP CONCURRENCY PERFORMANCE TESTING")
    print("=" * 60)
    print("This test focuses on demonstrating the concurrency benefits of AIOHTTP")
    print("for API operations that can be performed simultaneously.")
    
    # Test 1: Sequential vs Concurrent
    improvement, seq_success, con_success = await test_sequential_vs_concurrent()
    
    # Test 2: Batch Operations
    batch_improvement = await test_batch_operations()
    
    # Test 3: Real-world Scenario
    scenario_time, scenario_success = await test_real_world_scenario()
    
    # Final Analysis
    print("\n" + "=" * 60)
    print("FINAL ANALYSIS")
    print("=" * 60)
    
    if improvement > 1:
        print(f"✓ Concurrency improvement: {improvement:.1f}x faster")
        
        if improvement > 3:
            print("  EXCELLENT: Significant concurrency benefits")
        elif improvement > 2:
            print("  GOOD: Strong concurrency benefits")
        elif improvement > 1.5:
            print("  MODERATE: Noticeable concurrency benefits")
        else:
            print("  MINIMAL: Some concurrency benefits")
    else:
        print("✗ Unable to measure concurrency improvement")
    
    if batch_improvement > 1:
        print(f"✓ Batch operations improvement: {batch_improvement:.1f}x faster")
    else:
        print("✗ Unable to measure batch improvement")
    
    print(f"\nReal-world scenario: {scenario_time:.3f}s ({scenario_success}/4 operations successful)")
    
    # Recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    
    if improvement > 2 or batch_improvement > 2:
        print("🚀 HIGHLY RECOMMENDED: Implement AIOHTTP")
        print("   - Significant performance gains for concurrent operations")
        print("   - Ideal for applications that need to make multiple API calls")
        print("   - Improved user experience with faster response times")
    elif improvement > 1.5 or batch_improvement > 1.5:
        print("✅ RECOMMENDED: Implement AIOHTTP")
        print("   - Good performance gains for concurrent operations")
        print("   - Beneficial for applications with multiple API calls")
    else:
        print("⚠️ CONSIDER: AIOHTTP provides some benefits")
        print("   - May not justify implementation complexity")
        print("   - Benefits depend on usage patterns")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())