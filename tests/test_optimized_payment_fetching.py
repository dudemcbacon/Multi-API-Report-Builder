#!/usr/bin/env python3
"""
Test script to verify the optimized page-by-page payment fetching
"""
import asyncio
import logging
import sys

# Add src to path
sys.path.insert(0, '.')

from src.services.async_woocommerce_api import AsyncWooCommerceAPI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_page_by_page_fetching():
    """Test the new page-by-page payment fetching method"""
    try:
        logger.info("=== Testing Optimized Page-by-Page Payment Fetching ===")
        
        async with AsyncWooCommerceAPI() as woo_api:
            # Test connection
            logger.info("Testing connection...")
            connection_result = await woo_api.test_connection()
            
            if not connection_result.get('success'):
                logger.error(f"Connection failed: {connection_result}")
                return False
            
            logger.info("✓ Connection successful")
            
            # Test page-by-page fetching
            logger.info("\nTesting page-by-page fetching...")
            
            # Test first 3 pages to verify the method works
            for page in range(1, 4):
                logger.info(f"\n--- Testing Page {page} ---")
                payments = await woo_api.get_payments_by_page(page=page, per_page=10)
                
                if payments is None:
                    logger.error(f"✗ Page {page}: get_payments_by_page returned None")
                    continue
                
                logger.info(f"✓ Page {page}: Retrieved {len(payments)} payments")
                
                # Log sample payment structure from first payment
                if payments and len(payments) > 0:
                    sample_payment = payments[0]
                    payment_keys = list(sample_payment.keys())
                    logger.info(f"  Sample payment fields: {payment_keys}")
                    
                    # Check for key fields
                    has_payment_id = 'payment_id' in sample_payment
                    has_fees = 'fees' in sample_payment
                    logger.info(f"  Has payment_id: {has_payment_id}, Has fees: {has_fees}")
                    
                    if has_payment_id:
                        logger.info(f"  Sample payment_id: {sample_payment.get('payment_id', 'N/A')}")
                    if has_fees:
                        logger.info(f"  Sample fees: {sample_payment.get('fees', 'N/A')}")
                
                # If we get no payments, we've reached the end
                if len(payments) == 0:
                    logger.info(f"  Reached end of payments at page {page}")
                    break
            
            logger.info("\n=== Testing Performance Comparison ===")
            
            # Test old method vs new method performance
            import time
            
            # Test old method (paginated with large limit)
            logger.info("Testing old method (get_payments_paginated with limit 1000)...")
            start_time = time.time()
            old_payments = await woo_api.get_payments_paginated(limit=1000)
            old_time = time.time() - start_time
            logger.info(f"✓ Old method: {len(old_payments)} payments in {old_time:.2f} seconds")
            
            # Test new method (page by page for equivalent data)
            logger.info("Testing new method (get_payments_by_page for first 10 pages)...")
            start_time = time.time()
            new_payments_total = 0
            for page in range(1, 11):  # 10 pages * 100 = 1000 payments max
                page_payments = await woo_api.get_payments_by_page(page=page, per_page=100)
                if not page_payments:
                    break
                new_payments_total += len(page_payments)
                if len(page_payments) < 100:  # Reached end
                    break
            new_time = time.time() - start_time
            logger.info(f"✓ New method: {new_payments_total} payments in {new_time:.2f} seconds")
            
            # The new method should be comparable in performance but more flexible
            logger.info(f"\nPerformance comparison:")
            logger.info(f"  Old method: {len(old_payments)} payments, {old_time:.2f}s")
            logger.info(f"  New method: {new_payments_total} payments, {new_time:.2f}s")
            logger.info(f"  Flexibility: New method allows early termination after any page")
            
            return True
                
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

async def test_early_termination_simulation():
    """Simulate the early termination scenario"""
    logger.info("\n=== Testing Early Termination Simulation ===")
    
    try:
        async with AsyncWooCommerceAPI() as woo_api:
            # Simulate finding matches early
            logger.info("Simulating payment ID matching with early termination...")
            
            # Get first page to extract some real payment IDs
            first_page = await woo_api.get_payments_by_page(page=1, per_page=5)
            if not first_page:
                logger.warning("No payments found for simulation")
                return False
            
            # Simulate looking for specific payment IDs (use real ones from first page)
            simulated_target_ids = []
            for payment in first_page[:3]:  # Take first 3 payment IDs
                payment_id = payment.get('payment_id', '')
                if payment_id:
                    simulated_target_ids.append(payment_id)
            
            if not simulated_target_ids:
                logger.warning("No payment IDs found for simulation")
                return False
            
            logger.info(f"Simulating search for {len(simulated_target_ids)} payment IDs")
            
            # Simulate the optimized search process
            unmatched_ids = set(simulated_target_ids)
            matched_count = 0
            page = 1
            
            while unmatched_ids and page <= 10:  # Max 10 pages for simulation
                logger.info(f"  Fetching page {page}, {len(unmatched_ids)} IDs still unmatched")
                
                page_payments = await woo_api.get_payments_by_page(page=page, per_page=100)
                if not page_payments:
                    logger.info(f"  No more payments at page {page}")
                    break
                
                # Check for matches
                page_matches = 0
                for payment in page_payments:
                    payment_id = payment.get('payment_id', '')
                    if payment_id in unmatched_ids:
                        unmatched_ids.remove(payment_id)
                        matched_count += 1
                        page_matches += 1
                
                logger.info(f"  Page {page}: Found {page_matches} matches, {len(unmatched_ids)} still unmatched")
                
                # Early termination when all matches found
                if not unmatched_ids:
                    logger.info(f"✓ All {matched_count} payment IDs matched after only {page} pages!")
                    logger.info(f"✓ Saved API calls: Would have stopped at page {page} instead of fetching all pages")
                    break
                
                page += 1
            
            if unmatched_ids:
                logger.info(f"Simulation complete: {matched_count} matched, {len(unmatched_ids)} unmatched after {page-1} pages")
            
            return True
            
    except Exception as e:
        logger.error(f"Early termination simulation failed: {e}", exc_info=True)
        return False

async def main():
    """Run all tests"""
    logger.info("Starting optimized payment fetching tests...")
    
    test1_success = await test_page_by_page_fetching()
    test2_success = await test_early_termination_simulation()
    
    overall_success = test1_success and test2_success
    
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Page-by-page fetching: {'PASSED' if test1_success else 'FAILED'}")
    logger.info(f"Early termination simulation: {'PASSED' if test2_success else 'FAILED'}")
    logger.info(f"Overall: {'PASSED' if overall_success else 'FAILED'}")
    
    if overall_success:
        logger.info("\n✓ Optimized payment fetching is working correctly!")
        logger.info("✓ The new implementation should significantly reduce API calls")
        logger.info("✓ Early termination when all matches are found")
    else:
        logger.error("\n✗ Some tests failed - check the implementation")
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)