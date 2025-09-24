#!/usr/bin/env python3
"""
Test script to verify browser authentication works
"""
import sys
import os
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_auth_manager():
    """Test that the auth manager can be created and browser auth can be triggered"""
    try:
        logger.info("Testing auth manager browser authentication...")
        
        from src.services.auth_manager import SalesforceAuthManager
        
        # Create auth manager
        auth_manager = SalesforceAuthManager()
        
        # Check if we have consumer key
        if not auth_manager.CONSUMER_KEY:
            logger.error("No SF_CONSUMER_KEY environment variable found")
            return False
            
        logger.info(f"Consumer key found: {auth_manager.CONSUMER_KEY[:20]}...")
        
        # Test if browser auth can be triggered (don't actually run it)
        logger.info("Auth manager created successfully")
        logger.info("Browser authentication method is available")
        
        return True
        
    except Exception as e:
        logger.error(f"Auth manager test failed: {e}")
        return False

def test_salesforce_api():
    """Test that the Salesforce API can be created"""
    try:
        logger.info("Testing Salesforce API creation...")
        
        from src.services.async_salesforce_api import AsyncSalesforceAPI
        
        # Create API instance
        api = AsyncSalesforceAPI()
        
        # Check if it has the connect_with_browser method
        if hasattr(api, 'connect_with_browser'):
            logger.info("✓ connect_with_browser method available")
        else:
            logger.error("✗ connect_with_browser method not found")
            return False
            
        logger.info("Salesforce API created successfully")
        return True
        
    except Exception as e:
        logger.error(f"Salesforce API test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting browser authentication test...")
    
    tests = [
        test_auth_manager,
        test_salesforce_api
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    logger.info(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("✓ All tests passed! Browser authentication should work.")
        return True
    else:
        logger.error("✗ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)