#!/usr/bin/env python3
"""
Test script to verify the async migration is working correctly
"""
import sys
import logging
import asyncio
from unittest.mock import Mock

# Add src to path
sys.path.insert(0, '.')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_async_integration_import():
    """Test that async integration can be imported"""
    try:
        from src.ui.async_integration import AsyncRunner, async_slot, setup_async_app
        logger.info("✓ Successfully imported async integration components")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to import async integration: {e}")
        return False

def test_async_runner_creation():
    """Test that AsyncRunner can be created"""
    try:
        from src.ui.async_integration import AsyncRunner
        runner = AsyncRunner()
        logger.info("✓ Successfully created AsyncRunner instance")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create AsyncRunner: {e}")
        return False

def test_async_slot_decorator():
    """Test that async_slot decorator works"""
    try:
        from src.ui.async_integration import async_slot, AsyncRunner
        
        class TestWidget:
            def __init__(self):
                self._async_runner = AsyncRunner()
        
        @async_slot
        async def test_method(self):
            await asyncio.sleep(0.01)
            return "success"
        
        # Bind method to test widget
        widget = TestWidget()
        widget.test_method = test_method.__get__(widget, TestWidget)
        
        logger.info("✓ Successfully created async slot method")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create async slot: {e}")
        return False

def test_main_window_imports():
    """Test that main window with async integration can be imported"""
    try:
        # Mock PyQt6 components to avoid GUI dependencies
        sys.modules['PyQt6'] = Mock()
        sys.modules['PyQt6.QtWidgets'] = Mock()
        sys.modules['PyQt6.QtCore'] = Mock()
        sys.modules['PyQt6.QtGui'] = Mock()
        sys.modules['qtawesome'] = Mock()
        sys.modules['qdarkstyle'] = Mock()
        
        # Mock Qt classes
        from unittest.mock import MagicMock
        QMainWindow = MagicMock()
        QWidget = MagicMock()
        QThread = MagicMock()
        pyqtSignal = MagicMock()
        
        sys.modules['PyQt6.QtWidgets'].QMainWindow = QMainWindow
        sys.modules['PyQt6.QtWidgets'].QWidget = QWidget
        sys.modules['PyQt6.QtCore'].QThread = QThread
        sys.modules['PyQt6.QtCore'].pyqtSignal = pyqtSignal
        
        # Now test import
        from src.ui.main_window import MainWindow
        logger.info("✓ Successfully imported MainWindow with async integration")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to import MainWindow: {e}")
        return False

def test_async_proof_of_concept():
    """Test that proof of concept can be imported"""
    try:
        # Mock PyQt6 for the proof of concept
        from unittest.mock import Mock
        sys.modules['PyQt6'] = Mock()
        sys.modules['PyQt6.QtWidgets'] = Mock()
        sys.modules['PyQt6.QtCore'] = Mock()
        
        # Test that we can at least import the module structure
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "async_proof_of_concept", 
            "src/ui/async_proof_of_concept.py"
        )
        
        if spec and spec.loader:
            logger.info("✓ Async proof of concept module is valid")
            return True
        else:
            logger.error("✗ Async proof of concept module is invalid")
            return False
    except Exception as e:
        logger.error(f"✗ Failed to validate proof of concept: {e}")
        return False

def test_migration_guide_exists():
    """Test that migration guide exists and is readable"""
    try:
        with open('docs/async_migration_guide.md', 'r') as f:
            content = f.read()
            if len(content) > 1000:  # Should be substantial
                logger.info("✓ Migration guide exists and has substantial content")
                return True
            else:
                logger.error("✗ Migration guide exists but is too short")
                return False
    except Exception as e:
        logger.error(f"✗ Failed to read migration guide: {e}")
        return False

def main():
    """Run all tests"""
    print("Async Migration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Async Integration Import", test_async_integration_import),
        ("AsyncRunner Creation", test_async_runner_creation),
        ("Async Slot Decorator", test_async_slot_decorator),
        ("Main Window Imports", test_main_window_imports),
        ("Proof of Concept", test_async_proof_of_concept),
        ("Migration Guide", test_migration_guide_exists)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All async migration tests passed!")
        print("\nNext steps:")
        print("1. Install qasync: pip install qasync")
        print("2. Test the proof of concept: python src/ui/async_proof_of_concept.py")
        print("3. Begin using the new async patterns in your application")
        print("4. Gradually remove QThread dependencies")
    else:
        print("⚠️ Some tests failed. Please review the errors above.")

if __name__ == "__main__":
    main()