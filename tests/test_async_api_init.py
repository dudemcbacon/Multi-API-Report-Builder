#!/usr/bin/env python3
"""
Simple test to understand the async API initialization issue
"""
import asyncio
import logging
import sys

# Add src to path
sys.path.insert(0, '.')

from src.services.salesforce_api import SalesforceAPI
from src.services.async_salesforce_api import AsyncSalesforceAPI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_async_api_init():
    """Test async API initialization process"""
    try:
        logger.info("Creating regular Salesforce API...")
        sf_api = SalesforceAPI()
        
        logger.info(f"Regular API auth manager: {sf_api.auth_manager}")
        logger.info(f"Instance URL: {sf_api.auth_manager.instance_url}")
        logger.info(f"Consumer secret present: {bool(sf_api.auth_manager.consumer_secret)}")
        logger.info(f"Has access token: {bool(sf_api.auth_manager.access_token)}")
        
        logger.info("\n--- Creating Async API with default params ---")
        async_api1 = AsyncSalesforceAPI()
        logger.info(f"Async API 1 auth manager: {async_api1.auth_manager}")
        logger.info(f"Instance URL: {async_api1.auth_manager.instance_url}")
        logger.info(f"Has access token: {bool(async_api1.auth_manager.access_token)}")
        
        logger.info("\n--- Creating Async API with explicit params ---")
        instance_url = sf_api.auth_manager.instance_url
        consumer_secret = sf_api.auth_manager.consumer_secret
        logger.info(f"Passing instance_url: {instance_url}")
        logger.info(f"Passing consumer_secret: {consumer_secret[:10]}..." if consumer_secret else "No consumer secret")
        
        async_api2 = AsyncSalesforceAPI(instance_url, consumer_secret)
        logger.info(f"Async API 2 auth manager: {async_api2.auth_manager}")
        logger.info(f"Instance URL: {async_api2.auth_manager.instance_url}")
        logger.info(f"Has access token: {bool(async_api2.auth_manager.access_token)}")
        
        # Test if tokens are loaded
        logger.info("\n--- Testing token access ---")
        logger.info(f"Regular API token: {sf_api.auth_manager.access_token[:20]}..." if sf_api.auth_manager.access_token else "No token")
        logger.info(f"Async API 1 token: {async_api1.auth_manager.access_token[:20]}..." if async_api1.auth_manager.access_token else "No token")
        logger.info(f"Async API 2 token: {async_api2.auth_manager.access_token[:20]}..." if async_api2.auth_manager.access_token else "No token")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    asyncio.run(test_async_api_init())