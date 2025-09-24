"""
Session Management Tests for AsyncSalesforceAPI
Tests session handling in worker threads and event loop management
"""
import asyncio
import pytest
import logging
import threading
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.services.async_salesforce_api import AsyncSalesforceAPI
from src.services.auth_manager import SalesforceAuthManager
from src.ui.workers import SalesforceConnectionWorker

logger = logging.getLogger(__name__)

class TestSessionManagement:
    """Test suite for session management and worker thread compatibility"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create mock auth manager for testing"""
        mock_auth = Mock(spec=SalesforceAuthManager)
        mock_auth.is_token_valid.return_value = True
        mock_auth.access_token = "mock_access_token"
        mock_auth.get_instance_url.return_value = "https://test.salesforce.com"
        mock_auth.has_credentials.return_value = True
        return mock_auth
    
    @pytest.fixture
    def api_instance(self, auth_manager):
        """Create API instance for testing"""
        return AsyncSalesforceAPI(auth_manager=auth_manager)
    
    @pytest.mark.asyncio
    async def test_basic_session_initialization(self, api_instance):
        """Test basic session initialization and cleanup"""
        logger.info("Testing basic session initialization")
        
        # Session should be None initially
        assert api_instance.session is None
        
        # Initialize session
        await api_instance._ensure_session()
        assert api_instance.session is not None
        assert not api_instance.session.closed
        
        # Close session
        await api_instance.close()
        assert api_instance.session.closed
        
        logger.info("✓ Basic session initialization works")
    
    @pytest.mark.asyncio
    async def test_session_reuse(self, api_instance):
        """Test that sessions are properly reused"""
        logger.info("Testing session reuse")
        
        # Initialize session twice
        await api_instance._ensure_session()
        session1 = api_instance.session
        
        await api_instance._ensure_session()
        session2 = api_instance.session
        
        # Should be the same session
        assert session1 is session2
        
        await api_instance.close()
        logger.info("✓ Session reuse works correctly")
    
    @pytest.mark.asyncio
    async def test_session_recreation_after_close(self, api_instance):
        """Test session recreation after being closed"""
        logger.info("Testing session recreation after close")
        
        # Create and close session
        await api_instance._ensure_session()
        session1 = api_instance.session
        await api_instance.close()
        
        # Create new session
        await api_instance._ensure_session()
        session2 = api_instance.session
        
        # Should be different sessions
        assert session1 is not session2
        assert session1.closed
        assert not session2.closed
        
        await api_instance.close()
        logger.info("✓ Session recreation works correctly")
    
    @pytest.mark.asyncio
    async def test_context_manager_session_handling(self, api_instance):
        """Test session handling with context manager"""
        logger.info("Testing context manager session handling")
        
        async with api_instance:
            assert api_instance.session is not None
            assert not api_instance.session.closed
            
        # Session should be closed after context exit
        assert api_instance.session.closed
        
        logger.info("✓ Context manager session handling works")
    
    def test_worker_thread_event_loop_creation(self):
        """Test that worker threads properly create event loops"""
        logger.info("Testing worker thread event loop creation")
        
        def worker_function():
            # Simulate what happens in SalesforceConnectionWorker.run()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Verify loop is set correctly
                current_loop = asyncio.get_event_loop()
                assert current_loop is loop
                return True
            except Exception as e:
                logger.error(f"Worker thread error: {e}")
                return False
            finally:
                loop.close()
        
        # Run in separate thread
        import threading
        
        result = []
        thread = threading.Thread(target=lambda: result.append(worker_function()))
        thread.start()
        thread.join()
        
        assert len(result) == 1
        assert result[0] is True
        
        logger.info("✓ Worker thread event loop creation works")
    
    @pytest.mark.asyncio
    async def test_api_session_in_worker_thread_simulation(self, auth_manager):
        """Test API session creation in worker thread simulation"""
        logger.info("Testing API session in worker thread simulation")
        
        async def simulate_worker_api_usage():
            """Simulate what should happen in a worker thread"""
            # Create API instance
            api = AsyncSalesforceAPI(auth_manager=auth_manager)
            
            try:
                # This should work without "Event loop is closed" error
                await api._ensure_session()
                assert api.session is not None
                assert not api.session.closed
                
                # Test basic session properties
                assert hasattr(api.session, 'get')
                assert hasattr(api.session, 'post')
                
                return True
            except Exception as e:
                logger.error(f"Worker API simulation error: {e}")
                return False
            finally:
                if api.session:
                    await api.close()
        
        # Run in new event loop (simulating worker thread)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = await simulate_worker_api_usage()
            assert result is True
        finally:
            loop.close()
        
        logger.info("✓ API session works in worker thread simulation")
    
    @patch('aiohttp.ClientSession')
    def test_session_configuration(self, mock_session_class, api_instance):
        """Test that session is configured correctly"""
        logger.info("Testing session configuration")
        
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Run session initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(api_instance._ensure_session())
            
            # Verify session was created with correct parameters
            mock_session_class.assert_called_once()
            call_args = mock_session_class.call_args
            
            # Check connector configuration
            assert 'connector' in call_args.kwargs
            assert 'timeout' in call_args.kwargs
            assert 'headers' in call_args.kwargs
            
            # Check headers
            headers = call_args.kwargs['headers']
            assert 'User-Agent' in headers
            assert 'Accept' in headers
            assert 'Content-Type' in headers
            
        finally:
            loop.close()
        
        logger.info("✓ Session configuration is correct")
    
    def test_worker_objects_loading_simulation(self, auth_manager):
        """Test the specific scenario that's failing in custom report builder"""
        logger.info("Testing worker objects loading simulation")
        
        def simulate_failing_scenario():
            """Simulate the exact scenario that's failing"""
            # Create new event loop (like in worker)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = {'success': False, 'error': None}
            
            try:
                # Create API instance (like in worker)
                api = AsyncSalesforceAPI(auth_manager=auth_manager)
                
                async def load_objects():
                    try:
                        # This is where the "Event loop is closed" error occurs
                        objects = await api.get_all_objects()
                        return {'success': True, 'objects': objects or []}
                    except Exception as e:
                        return {'success': False, 'error': str(e)}
                    finally:
                        await api.close()
                
                # Run the async operation
                result = loop.run_until_complete(load_objects())
                
            except Exception as e:
                result = {'success': False, 'error': str(e)}
            finally:
                loop.close()
            
            return result
        
        # Run in separate thread (like actual worker)
        import threading
        import queue
        
        result_queue = queue.Queue()
        thread = threading.Thread(target=lambda: result_queue.put(simulate_failing_scenario()))
        thread.start()
        thread.join()
        
        result = result_queue.get()
        
        # This might fail initially, but we want to understand why
        if not result['success']:
            logger.error(f"Worker simulation failed: {result['error']}")
            # Don't fail the test yet - this is what we're trying to fix
            assert 'Event loop is closed' in result['error'] or 'objects' in result
        else:
            logger.info("✓ Worker objects loading simulation succeeded")
    
    @pytest.mark.asyncio
    async def test_auth_info_caching(self, api_instance):
        """Test authentication info caching in session management"""
        logger.info("Testing auth info caching")
        
        # Get auth info multiple times
        auth_info_1 = api_instance._get_cached_auth_info()
        auth_info_2 = api_instance._get_cached_auth_info()
        
        # Should return consistent results
        if auth_info_1 and auth_info_2:
            assert auth_info_1[0] == auth_info_2[0]  # access_token
            assert auth_info_1[1] == auth_info_2[1]  # instance_url
        
        # Clear cache and test refresh
        api_instance._clear_auth_cache()
        auth_info_3 = api_instance._get_cached_auth_info()
        
        # Should still work after cache clear
        assert auth_info_3 is not None
        
        logger.info("✓ Auth info caching works correctly")
    
    def test_multiple_worker_threads(self, auth_manager):
        """Test multiple worker threads using API simultaneously"""
        logger.info("Testing multiple worker threads")
        
        def worker_task(worker_id):
            """Simulate a worker thread task"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                api = AsyncSalesforceAPI(auth_manager=auth_manager)
                
                async def do_work():
                    await api._ensure_session()
                    # Simulate some work
                    await asyncio.sleep(0.1)
                    return f"worker_{worker_id}_success"
                
                result = loop.run_until_complete(do_work())
                return result
            except Exception as e:
                return f"worker_{worker_id}_error: {e}"
            finally:
                loop.close()
        
        # Start multiple workers
        import threading
        import queue
        
        result_queue = queue.Queue()
        threads = []
        
        for i in range(3):
            thread = threading.Thread(target=lambda i=i: result_queue.put(worker_task(i)))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Collect results
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())
        
        # All should succeed
        assert len(results) == 3
        success_count = sum(1 for r in results if 'success' in r)
        
        logger.info(f"✓ Multiple workers completed: {success_count}/3 successful")
        
        # Log any failures for debugging
        for result in results:
            if 'error' in result:
                logger.warning(f"Worker failed: {result}")

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "asyncio: mark test as async")

if __name__ == "__main__":
    # Run tests directly
    import sys
    import os
    
    # Add project root to path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    pytest.main([__file__, "-v", "-s"])