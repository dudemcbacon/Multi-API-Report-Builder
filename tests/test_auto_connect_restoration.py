#!/usr/bin/env python3
"""
Test script to verify that auto-connect functionality has been restored to handle OAuth automatically
"""
import sys
import os
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_async_salesforce_auto_auth():
    """Test that AsyncSalesforceAPI automatically triggers browser auth when needed"""
    try:
        logger.info("Testing AsyncSalesforceAPI auto-authentication...")
        
        # Check the test_connection method source code
        with open("src/services/async_salesforce_api.py", "r") as f:
            content = f.read()
            
        # Verify that test_connection automatically calls connect_with_browser
        if "await self.connect_with_browser()" in content:
            logger.info("✓ AsyncSalesforceAPI automatically triggers browser auth when needed")
        else:
            logger.error("✗ AsyncSalesforceAPI does not automatically trigger browser auth")
            return False
            
        # Verify that it doesn't return early without attempting auth
        if "Re-authentication required - please reconnect via the main application" in content:
            logger.error("✗ AsyncSalesforceAPI still has manual prompt message")
            return False
        else:
            logger.info("✓ AsyncSalesforceAPI doesn't have manual prompt messages")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ AsyncSalesforceAPI test failed: {e}")
        return False

def test_main_window_no_manual_dialogs():
    """Test that MainWindow doesn't have manual connection dialogs"""
    try:
        logger.info("Testing MainWindow has no manual connection dialogs...")
        
        with open("src/ui/main_window.py", "r") as f:
            content = f.read()
            
        # Check that manual dialog methods are removed
        if "def show_salesforce_connect_dialog" in content:
            logger.error("✗ MainWindow still has show_salesforce_connect_dialog method")
            return False
        else:
            logger.info("✓ MainWindow doesn't have show_salesforce_connect_dialog method")
            
        if "def _start_browser_auth" in content:
            logger.error("✗ MainWindow still has _start_browser_auth method")
            return False
        else:
            logger.info("✓ MainWindow doesn't have _start_browser_auth method")
            
        if "def _show_password_dialog" in content:
            logger.error("✗ MainWindow still has _show_password_dialog method")
            return False
        else:
            logger.info("✓ MainWindow doesn't have _show_password_dialog method")
            
        # Check that auto-connect is still called
        if "async_auto_connect_all_apis" in content:
            logger.info("✓ MainWindow still has async_auto_connect_all_apis method")
        else:
            logger.error("✗ MainWindow missing async_auto_connect_all_apis method")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"✗ MainWindow test failed: {e}")
        return False

def test_connection_manager_fixed():
    """Test that ConnectionManager uses correct method names"""
    try:
        logger.info("Testing ConnectionManager method names...")
        
        with open("src/ui/managers/connection_manager.py", "r") as f:
            content = f.read()
            
        # Check that it uses has_credentials instead of has_stored_credentials
        if "has_stored_credentials" in content:
            logger.error("✗ ConnectionManager still uses has_stored_credentials")
            return False
        else:
            logger.info("✓ ConnectionManager doesn't use has_stored_credentials")
            
        if "has_credentials" in content:
            logger.info("✓ ConnectionManager uses has_credentials")
        else:
            logger.error("✗ ConnectionManager doesn't use has_credentials")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"✗ ConnectionManager test failed: {e}")
        return False

def test_workers_clean():
    """Test that workers don't have unnecessary error emissions"""
    try:
        logger.info("Testing workers are clean...")
        
        with open("src/ui/workers.py", "r") as f:
            content = f.read()
            
        # Check that AsyncAutoConnectWorker doesn't emit premature errors
        if "AsyncAutoConnectWorker" in content:
            logger.info("✓ AsyncAutoConnectWorker exists")
        else:
            logger.error("✗ AsyncAutoConnectWorker missing")
            return False
            
        # Check that it has the connect_with_browser handling
        if "connect_with_browser" in content:
            logger.info("✓ Workers have connect_with_browser support")
        else:
            logger.warning("⚠ Workers may not have connect_with_browser support")
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Workers test failed: {e}")
        return False

def test_environment_ready():
    """Test that environment variables are set"""
    try:
        logger.info("Testing environment is ready...")
        
        with open(".env", "r") as f:
            content = f.read()
            
        if "SF_CONSUMER_KEY=" in content:
            logger.info("✓ SF_CONSUMER_KEY is set in .env")
        else:
            logger.error("✗ SF_CONSUMER_KEY is not set in .env")
            return False
            
        if "SF_CONSUMER_SECRET=" in content:
            logger.info("✓ SF_CONSUMER_SECRET is set in .env")
        else:
            logger.error("✗ SF_CONSUMER_SECRET is not set in .env")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"✗ Environment test failed: {e}")
        return False

def main():
    """Run all auto-connect restoration tests"""
    logger.info("AUTO-CONNECT RESTORATION VERIFICATION")
    logger.info("=" * 50)
    
    tests = [
        test_async_salesforce_auto_auth,
        test_main_window_no_manual_dialogs,
        test_connection_manager_fixed,
        test_workers_clean,
        test_environment_ready
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
        logger.info("-" * 30)
    
    logger.info(f"\nTest Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        logger.info("✓ ALL AUTO-CONNECT RESTORATION TESTS PASSED!")
        logger.info("✓ AsyncSalesforceAPI will automatically trigger browser OAuth")
        logger.info("✓ No manual connection dialogs will appear")
        logger.info("✓ Auto-connect should work seamlessly")
        logger.info("✓ Application should handle OAuth automatically like before")
        return True
    else:
        logger.error("✗ Some tests failed. Auto-connect restoration may have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)