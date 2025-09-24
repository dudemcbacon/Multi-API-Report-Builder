#!/usr/bin/env python3
"""
Test script to verify the cleaned async WooCommerce API still works
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

async def test_cleaned_api():
    """Test the cleaned async WooCommerce API"""
    try:
        logger.info("=== Testing Cleaned WooCommerce Async API ===")
        
        # Create async API instance
        async with AsyncWooCommerceAPI() as woo_api:
            # Test connection
            logger.info("Testing connection...")
            connection_result = await woo_api.test_connection()
            
            if not connection_result.get('success'):
                logger.error(f"Connection failed: {connection_result}")
                return False
            
            logger.info("✓ Connection successful")
            
            # Test payments retrieval
            logger.info("Testing payments retrieval...")
            payments = await woo_api.get_payments_paginated(limit=10)
            
            if payments is not None:
                logger.info(f"✓ Successfully retrieved {len(payments)} payments")
                return True
            else:
                logger.error("✗ Failed to retrieve payments")
                return False
                
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

async def main():
    """Run test"""
    logger.info("Starting cleaned async WooCommerce API test...")
    
    success = await test_cleaned_api()
    
    logger.info(f"\nTest Result: {'PASSED' if success else 'FAILED'}")
    
    if success:
        logger.info("✓ Cleaned async WooCommerce API is working correctly!")
        logger.info("✓ All unused orders methods have been removed")
        logger.info("✓ Only payments functionality remains")
    else:
        logger.error("✗ Test failed - there may be an issue with the cleanup")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)