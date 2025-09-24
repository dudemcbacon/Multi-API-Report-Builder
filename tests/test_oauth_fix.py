#!/usr/bin/env python3
"""
Test script to verify the OAuth fix works correctly
"""
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

def test_oauth_flow():
    """Test the OAuth authentication flow"""
    try:
        from services.auth_manager import SalesforceAuthManager
        
        # Create auth manager with the configured instance URL
        auth_manager = SalesforceAuthManager(instance_url="https://company.my.salesforce.com")
        
        logger.info("Testing OAuth authentication flow...")
        logger.info(f"Instance URL: {auth_manager.instance_url}")
        logger.info(f"Authorization endpoint: {auth_manager.authorization_endpoint}")
        logger.info(f"Token endpoint: {auth_manager.token_endpoint}")
        logger.info(f"Consumer Key: {auth_manager.CONSUMER_KEY[:20]}...")
        
        # Clear any existing credentials first
        auth_manager.clear_credentials()
        logger.info("Cleared existing credentials")
        
        # Test authentication
        logger.info("Starting browser authentication...")
        success = auth_manager.authenticate_with_browser()
        
        if success:
            logger.info("✅ OAuth authentication successful!")
            logger.info(f"Access token: {'Present' if auth_manager.access_token else 'Missing'}")
            logger.info(f"Refresh token: {'Present' if auth_manager.refresh_token else 'Missing'}")
            logger.info(f"Instance URL: {auth_manager.instance_url_oauth}")
            logger.info(f"Token valid: {auth_manager.is_token_valid()}")
            return True
        else:
            logger.error("❌ OAuth authentication failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        logger.error("Stack trace:", exc_info=True)
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Salesforce OAuth Fix")
    print("=" * 60)
    
    success = test_oauth_flow()
    
    print("=" * 60)
    if success:
        print("✅ Test PASSED - OAuth flow working correctly")
    else:
        print("❌ Test FAILED - OAuth flow needs more work")
    print("=" * 60)
    
    sys.exit(0 if success else 1)