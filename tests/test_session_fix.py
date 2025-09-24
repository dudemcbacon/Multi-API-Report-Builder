#!/usr/bin/env python3
"""
Test script to verify the event loop session management fix
"""
import asyncio
import sys
import os
import logging
import threading
import queue
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_auth_manager():
    """Create mock auth manager for testing"""
    try:
        from src.services.auth_manager import SalesforceAuthManager
        mock_auth = Mock(spec=SalesforceAuthManager)
    except ImportError:
        # If import fails, create a basic mock
        mock_auth = Mock()
    
    mock_auth.is_token_valid.return_value = True
    mock_auth.access_token = "mock_access_token"
    mock_auth.get_instance_url.return_value = "https://test.salesforce.com"
    mock_auth.has_credentials.return_value = True
    return mock_auth

def test_worker_thread_simulation():
    """Test the specific scenario that was failing in custom report builder"""
    logger.info("=== Testing Worker Thread Session Management Fix ===")
    
    def simulate_worker_thread():
        """Simulate what happens in a worker thread"""
        # Create new event loop (like in worker)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = {'success': False, 'error': None}
        
        try:
            auth_manager = create_mock_auth_manager()
            
            # Try to import the API class
            try:
                from src.services.async_salesforce_api import AsyncSalesforceAPI
            except ImportError as e:
                return {'success': False, 'error': f'Import failed: {e}'}
            
            api = AsyncSalesforceAPI(auth_manager=auth_manager)
            
            async def test_session_management():
                try:
                    # Test that session creation works in this event loop
                    await api._ensure_session()
                    logger.info("✓ Session created successfully in worker thread")
                    
                    # Test session properties
                    assert api.session is not None, "Session should exist"
                    assert not api.session.closed, "Session should not be closed"
                    
                    # Test that the session belongs to current loop
                    current_loop = asyncio.get_event_loop()
                    session_loop = getattr(api.session, '_loop', None)
                    logger.info(f"Current loop: {id(current_loop)}")
                    logger.info(f"Session loop: {id(session_loop) if session_loop else 'None'}")
                    
                    # Test session reuse - second call should use same session
                    old_session = api.session
                    await api._ensure_session()
                    assert api.session is old_session, "Session should be reused"
                    logger.info("✓ Session reuse works correctly")
                    
                    return {'success': True, 'message': 'Session management test passed'}
                except Exception as e:
                    logger.error(f"Session management test error: {e}")
                    return {'success': False, 'error': str(e)}
                finally:
                    # Clean up
                    if api.session:
                        await api.close()
            
            # Run the async operation
            result = loop.run_until_complete(test_session_management())
            
        except Exception as e:
            logger.error(f"Worker simulation outer error: {e}")
            result = {'success': False, 'error': str(e)}
        finally:
            loop.close()
        
        return result
    
    # Run in separate thread (like actual worker)
    result_queue = queue.Queue()
    thread = threading.Thread(target=lambda: result_queue.put(simulate_worker_thread()))
    thread.start()
    thread.join()
    
    result = result_queue.get()
    
    logger.info(f"Worker simulation result: {result}")
    
    if not result['success']:
        logger.error(f"Worker simulation failed: {result['error']}")
        return False
    else:
        logger.info("✓ Worker simulation succeeded - Event loop issue is FIXED!")
        return True

def test_multiple_event_loops():
    """Test that the API can work across multiple event loops"""
    logger.info("=== Testing Multiple Event Loops ===")
    
    def run_in_event_loop(loop_id):
        """Run API operations in a specific event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            auth_manager = create_mock_auth_manager()
            
            try:
                from src.services.async_salesforce_api import AsyncSalesforceAPI
            except ImportError:
                return {'success': False, 'error': 'Import failed'}
            
            api = AsyncSalesforceAPI(auth_manager=auth_manager)
            
            async def test_operations():
                # Test session creation
                await api._ensure_session()
                current_loop = asyncio.get_event_loop()
                session_loop = getattr(api.session, '_loop', None)
                
                logger.info(f"Loop {loop_id}: Created session for loop {id(current_loop)}")
                
                # Test that session is valid for this loop
                assert session_loop == current_loop, f"Session loop mismatch in loop {loop_id}"
                
                await api.close()
                return {'success': True, 'loop_id': loop_id}
            
            return loop.run_until_complete(test_operations())
        except Exception as e:
            return {'success': False, 'error': str(e), 'loop_id': loop_id}
        finally:
            loop.close()
    
    # Test with multiple event loops
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(run_in_event_loop, i) for i in range(3)]
        results = [future.result() for future in futures]
    
    success_count = sum(1 for r in results if r['success'])
    logger.info(f"Multiple event loops test: {success_count}/3 succeeded")
    
    for result in results:
        if not result['success']:
            logger.error(f"Loop {result.get('loop_id', '?')} failed: {result['error']}")
    
    return success_count == 3

def main():
    """Run all tests"""
    logger.info("Testing AsyncSalesforceAPI Session Management Fix")
    logger.info("=" * 60)
    
    tests = [
        test_worker_thread_simulation,
        test_multiple_event_loops,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)
        logger.info("-" * 40)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    logger.info("=" * 60)
    logger.info(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED! Event loop issue is fixed!")
    else:
        logger.error("❌ Some tests failed - more work needed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)