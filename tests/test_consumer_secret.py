#!/usr/bin/env python3
"""
Test script to verify consumer secret is being loaded and used correctly
"""
import os
import sys
import logging
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not available, using system environment variables only")

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_consumer_secret_loading():
    """Test that consumer secret is loaded correctly"""
    try:
        from services.auth_manager import SalesforceAuthManager
        
        logger.info("Testing consumer secret loading...")
        
        # Check environment variables
        consumer_key = os.getenv('SF_CONSUMER_KEY')
        consumer_secret = os.getenv('SF_CONSUMER_SECRET')
        
        logger.info(f"SF_CONSUMER_KEY: {'Present' if consumer_key else 'Missing'}")
        logger.info(f"SF_CONSUMER_SECRET: {'Present' if consumer_secret else 'Missing'}")
        
        if consumer_key:
            logger.info(f"Consumer Key (first 20 chars): {consumer_key[:20]}...")
        if consumer_secret:
            logger.info(f"Consumer Secret (first 20 chars): {consumer_secret[:20]}...")
        
        # Create auth manager
        auth_manager = SalesforceAuthManager(instance_url="https://company.my.salesforce.com")
        
        logger.info(f"Auth Manager Consumer Key: {'Present' if auth_manager.CONSUMER_KEY else 'Missing'}")
        logger.info(f"Auth Manager Consumer Secret: {'Present' if auth_manager.consumer_secret else 'Missing'}")
        
        if auth_manager.CONSUMER_KEY:
            logger.info(f"Manager Consumer Key (first 20 chars): {auth_manager.CONSUMER_KEY[:20]}...")
        if auth_manager.consumer_secret:
            logger.info(f"Manager Consumer Secret (first 20 chars): {auth_manager.consumer_secret[:20]}...")
        
        # Verify they match
        if consumer_key == auth_manager.CONSUMER_KEY:
            logger.info("✅ Consumer Key matches between environment and manager")
        else:
            logger.error("❌ Consumer Key mismatch!")
            
        if consumer_secret == auth_manager.consumer_secret:
            logger.info("✅ Consumer Secret matches between environment and manager")
        else:
            logger.error("❌ Consumer Secret mismatch!")
        
        # Check if both are present
        if auth_manager.CONSUMER_KEY and auth_manager.consumer_secret:
            logger.info("✅ Both consumer key and secret are available")
            return True
        else:
            logger.error("❌ Missing consumer key or secret")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        logger.error("Stack trace:", exc_info=True)
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Consumer Secret Loading")
    print("=" * 60)
    
    success = test_consumer_secret_loading()
    
    print("=" * 60)
    if success:
        print("✅ Consumer Secret test PASSED")
    else:
        print("❌ Consumer Secret test FAILED")
    print("=" * 60)
    
    sys.exit(0 if success else 1)