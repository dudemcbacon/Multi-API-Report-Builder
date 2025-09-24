#!/usr/bin/env python3
"""
Test script to verify event loop fixes in the application
"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Basic logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_imports():
    """Test that all imports work correctly"""
    try:
        logger.info("Testing imports...")
        
        # Test individual API imports
        from src.services.async_salesforce_api import AsyncSalesforceAPI
        from src.services.async_woocommerce_api import AsyncWooCommerceAPI
        from src.services.async_avalara_api import AsyncAvalaraAPI
        
        # Test worker imports
        from src.ui.workers import AsyncAutoConnectWorker
        
        # Test manager imports
        from src.ui.managers.connection_manager import ConnectionManager
        
        logger.info("✓ All imports successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Import failed: {e}")
        return False

def test_worker_creation():
    """Test that workers can be created without event loop issues"""
    try:
        logger.info("Testing worker creation...")
        
        from src.ui.workers import AsyncAutoConnectWorker
        from src.models.config import ConfigManager
        
        # Create config manager
        config_manager = ConfigManager()
        config = config_manager.get_config()
        
        # Create worker (should not cause event loop issues)
        worker = AsyncAutoConnectWorker(config)
        
        logger.info("✓ Worker creation successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Worker creation failed: {e}")
        return False

def test_connection_manager():
    """Test that ConnectionManager can be created and initialized"""
    try:
        logger.info("Testing ConnectionManager...")
        
        from src.ui.managers.connection_manager import ConnectionManager
        from src.models.config import ConfigManager
        
        # Create config manager
        config_manager = ConfigManager()
        
        # Create connection manager
        connection_manager = ConnectionManager(config_manager)
        
        logger.info("✓ ConnectionManager creation successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ ConnectionManager creation failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("Starting event loop fixes test...")
    
    tests = [
        test_imports,
        test_worker_creation,
        test_connection_manager
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
        logger.info("✓ All tests passed! Event loop fixes appear to be working.")
        return True
    else:
        logger.error("✗ Some tests failed. Check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)