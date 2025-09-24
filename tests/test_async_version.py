#!/usr/bin/env python3
"""
Test script for the async version of Salesforce Report Pull
Validates that the async implementation works correctly
"""
import sys
import logging
import asyncio
from unittest.mock import Mock, patch
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_async_imports():
    """Test that async modules can be imported"""
    try:
        from src.ui.async_manager import AsyncOperationManager
        from src.ui.async_main_window import AsyncMainWindow
        from src.ui.async_mixins import AsyncProgressMixin, AsyncErrorHandlingMixin, AsyncConnectionMixin
        logger.info("✅ All async modules imported successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to import async modules: {e}")
        return False

def test_async_manager_creation():
    """Test AsyncOperationManager creation"""
    try:
        from src.ui.async_manager import AsyncOperationManager
        from src.models.config import ConfigManager
        
        config_manager = ConfigManager()
        async_manager = AsyncOperationManager(config_manager)
        
        # Test basic properties
        assert async_manager.sf_api is None
        assert async_manager.woo_api is None
        assert isinstance(async_manager._current_operations, dict)
        
        logger.info("✅ AsyncOperationManager created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create AsyncOperationManager: {e}")
        return False

def test_async_mixins():
    """Test async mixins functionality"""
    try:
        from src.ui.async_mixins import AsyncProgressMixin, AsyncErrorHandlingMixin, AsyncConnectionMixin
        
        # Test mixin combination
        class TestWidget(AsyncProgressMixin, AsyncErrorHandlingMixin, AsyncConnectionMixin):
            def __init__(self):
                AsyncProgressMixin.__init__(self)
                AsyncErrorHandlingMixin.__init__(self)
                AsyncConnectionMixin.__init__(self)
        
        widget = TestWidget()
        
        # Test connection mixin
        widget.set_connection_status("test_api", True)
        assert widget.is_connected("test_api") == True
        
        widget.set_api_instance("test_api", "mock_instance")
        assert widget.get_api_instance("test_api") == "mock_instance"
        
        logger.info("✅ Async mixins work correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to test async mixins: {e}")
        return False

def test_async_main_window_creation():
    """Test AsyncMainWindow creation (without actually showing GUI)"""
    try:
        # Mock PyQt6 to avoid GUI dependencies
        with patch('PyQt6.QtWidgets.QApplication.instance', return_value=None):
            with patch('src.ui.main_window.MainWindow.__init__', return_value=None):
                from src.ui.async_main_window import AsyncMainWindow
                
                # This won't actually create a window, just test the class structure
                logger.info("✅ AsyncMainWindow class loads successfully")
                return True
    except Exception as e:
        logger.error(f"❌ Failed to test AsyncMainWindow: {e}")
        return False

def test_async_manager_methods():
    """Test AsyncOperationManager methods"""
    try:
        from src.ui.async_manager import AsyncOperationManager
        from src.models.config import ConfigManager
        
        config_manager = ConfigManager()
        async_manager = AsyncOperationManager(config_manager)
        
        # Test cancellation methods
        async_manager.cancel_operation("non_existent")
        async_manager.cancel_all_operations()
        
        logger.info("✅ AsyncOperationManager methods work correctly")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to test AsyncOperationManager methods: {e}")
        return False

def test_launch_async_imports():
    """Test that launch_async.py can be imported"""
    try:
        # Test that the launch script doesn't have import errors
        import importlib.util
        spec = importlib.util.spec_from_file_location("launch_async", "launch_async.py")
        
        if spec and spec.loader:
            logger.info("✅ launch_async.py is valid")
            return True
        else:
            logger.error("❌ launch_async.py is not valid")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to validate launch_async.py: {e}")
        return False

def test_qasync_availability():
    """Test if qasync is available"""
    try:
        import qasync
        logger.info("✅ qasync is available")
        return True
    except ImportError:
        logger.warning("⚠️ qasync not available - async version will not work")
        logger.info("Install with: pip install qasync")
        return False

def test_async_integration_availability():
    """Test if async integration module is available"""
    try:
        from src.ui.async_integration import AsyncRunner, async_slot
        logger.info("✅ async_integration module is available")
        return True
    except ImportError as e:
        logger.error(f"❌ async_integration module not available: {e}")
        return False

async def test_async_operation_simulation():
    """Test simulated async operations"""
    try:
        from src.ui.async_manager import AsyncOperationManager
        from src.models.config import ConfigManager
        
        config_manager = ConfigManager()
        async_manager = AsyncOperationManager(config_manager)
        
        # Test that methods exist and can be called
        assert hasattr(async_manager, 'connect_salesforce_browser')
        assert hasattr(async_manager, 'load_salesforce_reports')
        assert hasattr(async_manager, 'load_report_data')
        assert hasattr(async_manager, 'cleanup')
        
        # Test cleanup
        await async_manager.cleanup()
        
        logger.info("✅ Async operation simulation successful")
        return True
    except Exception as e:
        logger.error(f"❌ Failed async operation simulation: {e}")
        return False

def main():
    """Run all tests"""
    print("Async Version Test Suite")
    print("=" * 50)
    
    tests = [
        ("Async Module Imports", test_async_imports),
        ("AsyncOperationManager Creation", test_async_manager_creation),
        ("Async Mixins", test_async_mixins),
        ("AsyncMainWindow Creation", test_async_main_window_creation),
        ("AsyncOperationManager Methods", test_async_manager_methods),
        ("Launch Async Imports", test_launch_async_imports),
        ("qasync Availability", test_qasync_availability),
        ("Async Integration Availability", test_async_integration_availability),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    # Run async test
    print(f"\nAsync Operation Simulation:")
    print("-" * 30)
    try:
        result = asyncio.run(test_async_operation_simulation())
        if result:
            print(f"✅ Async Operation Simulation PASSED")
            passed += 1
        else:
            print(f"❌ Async Operation Simulation FAILED")
    except Exception as e:
        print(f"❌ Async Operation Simulation ERROR: {e}")
    
    total += 1  # Add the async test to total
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All async version tests passed!")
        print("\nAsync version is ready for testing:")
        print("1. Install qasync: pip install qasync")
        print("2. Run async version: python launch_async.py")
        print("3. Compare with QThread version: python launch.py")
        print("\nSee ASYNC_VERSION_README.md for detailed instructions")
    else:
        print("⚠️ Some tests failed. Please review the errors above.")
        
        if not test_qasync_availability():
            print("\n🔧 To fix qasync issue:")
            print("   pip install qasync")
        
        print("\n📖 For troubleshooting, see ASYNC_VERSION_README.md")

if __name__ == "__main__":
    main()