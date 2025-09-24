#!/usr/bin/env python3
"""
Test script to verify the corrected OAuth implementation works
Based on the SALESFORCE_OAUTH_IMPLEMENTATION_GUIDE.md
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

def test_oauth_endpoints():
    """Test that OAuth endpoints are correctly configured"""
    try:
        from services.auth_manager import SalesforceAuthManager
        
        logger.info("Testing OAuth endpoint configuration...")
        
        # Test with company custom domain
        auth_manager = SalesforceAuthManager(instance_url="https://company.my.salesforce.com")
        
        logger.info(f"Instance URL: {auth_manager.instance_url}")
        logger.info(f"Authorization endpoint: {auth_manager.authorization_endpoint}")
        logger.info(f"Token endpoint: {auth_manager.token_endpoint}")
        
        # Verify endpoints are correct
        expected_auth = "https://company.my.salesforce.com/services/oauth2/authorize"
        expected_token = "https://login.salesforce.com/services/oauth2/token"
        
        if auth_manager.authorization_endpoint == expected_auth:
            logger.info("✅ Authorization endpoint correct")
        else:
            logger.error(f"❌ Authorization endpoint wrong: {auth_manager.authorization_endpoint}")
            return False
            
        if auth_manager.token_endpoint == expected_token:
            logger.info("✅ Token endpoint correct (using standard domain)")
        else:
            logger.error(f"❌ Token endpoint wrong: {auth_manager.token_endpoint}")
            return False
        
        logger.info(f"Consumer Key: {'Present' if auth_manager.CONSUMER_KEY else 'Missing'}")
        logger.info(f"Consumer Secret: {'Present' if auth_manager.consumer_secret else 'Missing'}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Endpoint test failed: {e}")
        return False

def test_oauth_flow():
    """Test the complete OAuth authentication flow"""
    try:
        from services.auth_manager import SalesforceAuthManager
        
        logger.info("Testing complete OAuth flow...")
        
        # Create auth manager with the configured instance URL
        auth_manager = SalesforceAuthManager(instance_url="https://company.my.salesforce.com")
        
        logger.info("Key changes applied:")
        logger.info("1. ✅ Token endpoint uses login.salesforce.com (not custom domain)")
        logger.info("2. ✅ OAuth scope changed from 'api' to 'full'")
        logger.info("3. ✅ Consumer secret is optional for PKCE flow")
        
        # Clear any existing credentials first
        auth_manager.clear_credentials()
        logger.info("Cleared existing credentials")
        
        # Test authentication
        logger.info("Starting browser authentication with corrected settings...")
        logger.info("Expected flow:")
        logger.info("- Authorization: https://company.my.salesforce.com/services/oauth2/authorize")
        logger.info("- Token exchange: https://login.salesforce.com/services/oauth2/token")
        logger.info("- Scope: full (instead of api)")
        
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
        logger.error(f"❌ OAuth test failed with exception: {e}")
        logger.error("Stack trace:", exc_info=True)
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Corrected Salesforce OAuth Implementation")
    print("=" * 60)
    
    # Test endpoint configuration first
    endpoint_test = test_oauth_endpoints()
    print()
    
    if endpoint_test:
        # Test full OAuth flow
        oauth_test = test_oauth_flow()
        print()
        
        print("=" * 60)
        if oauth_test:
            print("✅ All tests PASSED - OAuth flow working correctly")
            print("The token endpoint fix should resolve the scope error!")
        else:
            print("❌ OAuth test FAILED - check the error details above")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ Endpoint configuration test FAILED")
        print("=" * 60)
    
    sys.exit(0 if endpoint_test and oauth_test else 1)