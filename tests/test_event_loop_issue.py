#!/usr/bin/env python3
"""
Simplified test to diagnose the "Event loop is closed" error
without requiring pytest dependencies
"""
import asyncio
import sys
import os
import logging
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from src.services.async_salesforce_api import AsyncSalesforceAPI
from src.services.auth_manager import SalesforceAuthManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_auth_manager():
    """Create mock auth manager for testing"""
    mock_auth = Mock(spec=SalesforceAuthManager)
    mock_auth.is_token_valid.return_value = True
    mock_auth.access_token = "mock_access_token"
    mock_auth.get_instance_url.return_value = "https://test.salesforce.com"
    mock_auth.has_credentials.return_value = True
    return mock_auth

def test_basic_session_initialization():
    """Test basic session initialization and cleanup"""
    logger.info("=== Test 1: Basic Session Initialization ===")
    
    auth_manager = create_mock_auth_manager()
    api = AsyncSalesforceAPI(auth_manager=auth_manager)
    
    async def run_test():
        try:
            # Session should be None initially
            assert api.session is None, "Session should be None initially"
            logger.info("✓ Initial session state correct")
            
            # Initialize session
            await api._ensure_session()
            assert api.session is not None, "Session should be created"
            assert not api.session.closed, "Session should not be closed"
            logger.info("✓ Session created successfully")
            
            # Close session
            await api.close()
            assert api.session.closed, "Session should be closed"
            logger.info("✓ Session closed successfully")
            
            return True
        except Exception as e:
            logger.error(f"Basic session test failed: {e}")
            return False
    
    # Create new event loop for this test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(run_test())
        logger.info(f"Test 1 Result: {'PASSED' if result else 'FAILED'}")
        return result
    finally:
        loop.close()

def test_worker_thread_simulation():
    """Test the specific scenario that's failing in custom report builder"""
    logger.info("=== Test 2: Worker Thread Simulation ===")
    
    def simulate_worker_thread():
        """Simulate what happens in a worker thread"""
        # Create new event loop (like in worker)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = {'success': False, 'error': None}
        
        try:
            auth_manager = create_mock_auth_manager()
            api = AsyncSalesforceAPI(auth_manager=auth_manager)
            
            async def load_objects():
                try:
                    # This is where the "Event loop is closed" error occurs
                    logger.info("Attempting to get all objects...")
                    objects = await api.get_all_objects()
                    logger.info(f"Got objects: {objects is not None}")
                    return {'success': True, 'objects': objects or []}
                except Exception as e:
                    logger.error(f"load_objects error: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    if api.session:
                        await api.close()
            
            # Run the async operation
            result = loop.run_until_complete(load_objects())
            
        except Exception as e:
            logger.error(f"Worker simulation outer error: {e}")
            result = {'success': False, 'error': str(e)}
        finally:
            loop.close()
        
        return result
    
    # Run in separate thread (like actual worker)
    import threading
    import queue
    
    result_queue = queue.Queue()
    thread = threading.Thread(target=lambda: result_queue.put(simulate_worker_thread()))
    thread.start()
    thread.join()
    
    result = result_queue.get()
    
    logger.info(f"Worker simulation result: {result}")
    
    if not result['success']:
        logger.error(f"Worker simulation failed: {result['error']}")
        if 'Event loop is closed' in result['error']:
            logger.error("Confirmed: Event loop is closed error reproduced")
        return False
    else:
        logger.info("✓ Worker simulation succeeded")
        return True

def test_session_recreation():
    """Test session recreation after being closed"""
    logger.info("=== Test 3: Session Recreation ===")
    
    auth_manager = create_mock_auth_manager()
    api = AsyncSalesforceAPI(auth_manager=auth_manager)
    
    async def run_test():
        try:
            # Create and close session
            await api._ensure_session()
            session1 = api.session
            await api.close()
            
            # Create new session
            await api._ensure_session()
            session2 = api.session
            
            # Should be different sessions
            assert session1 is not session2, "Should be different sessions"
            assert session1.closed, "First session should be closed"
            assert not session2.closed, "Second session should be open"
            
            await api.close()
            logger.info("✓ Session recreation works correctly")
            return True
        except Exception as e:
            logger.error(f"Session recreation test failed: {e}")
            return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(run_test())
        logger.info(f"Test 3 Result: {'PASSED' if result else 'FAILED'}")
        return result
    finally:
        loop.close()

def test_context_manager():
    """Test session handling with context manager"""
    logger.info("=== Test 4: Context Manager ===")
    
    auth_manager = create_mock_auth_manager()
    api = AsyncSalesforceAPI(auth_manager=auth_manager)
    
    async def run_test():
        try:
            async with api:
                assert api.session is not None, "Session should exist in context"
                assert not api.session.closed, "Session should be open in context"
            
            # Session should be closed after context exit
            assert api.session.closed, "Session should be closed after context"
            
            logger.info("✓ Context manager session handling works")
            return True
        except Exception as e:
            logger.error(f"Context manager test failed: {e}")
            return False
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(run_test())
        logger.info(f"Test 4 Result: {'PASSED' if result else 'FAILED'}")
        return result
    finally:
        loop.close()

def main():
    """Run all tests"""
    logger.info("Starting Event Loop Issue Diagnostics")
    logger.info("=" * 50)
    
    tests = [
        test_basic_session_initialization,
        test_session_recreation,
        test_context_manager,
        test_worker_thread_simulation,  # This one will likely fail
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)
        logger.info("-" * 30)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 50)
    logger.info(f"Test Results: {passed}/{total} passed")
    
    if passed < total:
        logger.error("Some tests failed - this confirms the event loop issue exists")
        logger.info("The failing test(s) show where the 'Event loop is closed' error occurs")
    else:
        logger.info("All tests passed - event loop handling is working correctly")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)