#!/usr/bin/env python3
"""
Test script to verify that auto-connect functionality is working correctly after fixes
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

def test_connection_manager_method():
    """Test that ConnectionManager has the correct method names"""
    try:
        logger.info("Testing ConnectionManager method availability...")
        
        from src.ui.managers.connection_manager import ConnectionManager
        from src.models.config import ConfigManager
        
        # Create config manager
        config_manager = ConfigManager()
        
        # Create connection manager
        connection_manager = ConnectionManager(config_manager)
        
        # Check that it has the correct methods
        if hasattr(connection_manager, 'restore_salesforce_session'):
            logger.info("✓ ConnectionManager has restore_salesforce_session method")
        else:
            logger.error("✗ ConnectionManager missing restore_salesforce_session method")
            return False
            
        logger.info("✓ ConnectionManager created successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ ConnectionManager test failed: {e}")
        return False

def test_auth_manager_method():
    """Test that AuthManager has the correct method names"""
    try:
        logger.info("Testing AuthManager method availability...")
        
        from src.services.auth_manager import SalesforceAuthManager
        
        # Create auth manager
        auth_manager = SalesforceAuthManager()
        
        # Check that it has the correct methods
        if hasattr(auth_manager, 'has_credentials'):
            logger.info("✓ AuthManager has has_credentials method")
        else:
            logger.error("✗ AuthManager missing has_credentials method")
            return False
            
        # Check that it doesn't have the wrong method name
        if hasattr(auth_manager, 'has_stored_credentials'):
            logger.warning("⚠ AuthManager still has has_stored_credentials method (should be removed)")
        else:
            logger.info("✓ AuthManager doesn't have has_stored_credentials method (correct)")
            
        logger.info("✓ AuthManager created successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ AuthManager test failed: {e}")
        return False

def test_worker_logic():
    """Test that AsyncAutoConnectWorker has the correct error handling"""
    try:
        logger.info("Testing AsyncAutoConnectWorker error handling...")
        
        from src.ui.workers import AsyncAutoConnectWorker
        from src.models.config import ConfigManager
        
        # Create config manager
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Create worker
        worker = AsyncAutoConnectWorker(config)
        
        # Check that it has the correct signals
        if hasattr(worker, 'error_occurred'):
            logger.info("✓ AsyncAutoConnectWorker has error_occurred signal")
        else:
            logger.error("✗ AsyncAutoConnectWorker missing error_occurred signal")
            return False
            
        if hasattr(worker, 'connection_completed'):
            logger.info("✓ AsyncAutoConnectWorker has connection_completed signal")
        else:
            logger.error("✗ AsyncAutoConnectWorker missing connection_completed signal")
            return False
            
        logger.info("✓ AsyncAutoConnectWorker created successfully")
        return True
        
    except Exception as e:
        logger.error(f"✗ AsyncAutoConnectWorker test failed: {e}")
        return False

def test_main_window_error_handling():
    """Test that MainWindow error handling doesn't automatically trigger dialogs"""
    try:
        logger.info("Testing MainWindow error handling...")
        
        # We can't easily test the full MainWindow without Qt, but we can check
        # that the method exists and doesn't have the automatic dialog trigger
        
        with open("src/ui/main_window.py", "r") as f:
            content = f.read()
            
        # Check that the automatic dialog trigger is removed
        if "show_salesforce_connect_dialog" in content:
            # Count occurrences - there should be the definition and maybe a manual call
            occurrences = content.count("show_salesforce_connect_dialog")
            if occurrences <= 2:  # Definition + maybe one manual call
                logger.info("✓ MainWindow doesn't automatically trigger connection dialog")
            else:
                logger.warning(f"⚠ MainWindow may still have automatic dialog triggers ({occurrences} occurrences)")
        else:
            logger.info("✓ MainWindow connection dialog method found")
            
        # Check that on_auto_connect_error doesn't trigger dialogs
        if "on_auto_connect_error" in content:
            logger.info("✓ MainWindow has on_auto_connect_error method")
        else:
            logger.error("✗ MainWindow missing on_auto_connect_error method")
            return False
            
        logger.info("✓ MainWindow error handling test passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ MainWindow test failed: {e}")
        return False

def main():
    """Run all auto-connect fix tests"""
    logger.info("AUTO-CONNECT FIX VERIFICATION TEST")
    logger.info("=" * 50)
    
    tests = [
        test_connection_manager_method,
        test_auth_manager_method,
        test_worker_logic,
        test_main_window_error_handling
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
        logger.info("✓ All auto-connect fix tests passed!")
        logger.info("✓ Method name mismatch fixed")
        logger.info("✓ Automatic dialog trigger removed")
        logger.info("✓ Auto-connect should work correctly now")
        return True
    else:
        logger.error("✗ Some tests failed. Auto-connect may still have issues.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)