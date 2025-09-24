"""
Shared Session Manager for optimized aiohttp connection pooling
Provides centralized session management for multiple APIs
"""
import asyncio
import aiohttp
import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SharedSessionManager:
    """
    Singleton session manager for optimized connection pooling
    Manages aiohttp sessions across multiple APIs for better resource utilization
    """
    
    _instance: Optional['SharedSessionManager'] = None
    _sessions: Dict[str, aiohttp.ClientSession] = {}
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized') or not self._initialized:
            self._sessions = {}
            self._lock = asyncio.Lock()
            self._initialized = True
            logger.info("[SESSION-MANAGER] Initialized shared session manager")
    
    async def get_session(self, base_url: str, **session_kwargs) -> aiohttp.ClientSession:
        """
        Get or create a session for a specific base URL
        
        Args:
            base_url: Base URL for the session (e.g., 'https://api.salesforce.com')
            **session_kwargs: Additional session configuration options
            
        Returns:
            Configured aiohttp ClientSession
        """
        # Extract domain from URL for session key
        parsed = urlparse(base_url)
        session_key = f"{parsed.scheme}://{parsed.netloc}"
        
        async with self._lock:
            if session_key not in self._sessions or self._sessions[session_key].closed:
                logger.info(f"[SESSION-MANAGER] Creating new session for {session_key}")
                
                # Default optimized connector settings
                connector_config = {
                    'limit': 100,  # Total connection pool size
                    'limit_per_host': 30,  # Connections per host
                    'ttl_dns_cache': 300,  # DNS cache TTL (5 minutes)
                    'use_dns_cache': True,
                    'keepalive_timeout': 60,  # Keep connections alive for 60s
                    'enable_cleanup_closed': True,
                    'force_close': False,  # Enable connection reuse
                }
                
                # Override with any custom connector settings
                if 'connector_config' in session_kwargs:
                    connector_config.update(session_kwargs.pop('connector_config'))
                
                connector = aiohttp.TCPConnector(**connector_config)
                
                # Default timeout settings
                timeout_config = aiohttp.ClientTimeout(
                    total=90,  # Total request timeout
                    connect=10,  # Connection timeout
                    sock_read=60  # Socket read timeout
                )
                
                # Override with custom timeout if provided
                if 'timeout' in session_kwargs:
                    timeout_config = session_kwargs.pop('timeout')
                
                # Default headers
                default_headers = {
                    'User-Agent': 'SalesForceReportPull-SharedSession/1.0',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive'
                }
                
                # Merge with any custom headers
                if 'headers' in session_kwargs:
                    default_headers.update(session_kwargs['headers'])
                    session_kwargs['headers'] = default_headers
                else:
                    session_kwargs['headers'] = default_headers
                
                # Create the session
                self._sessions[session_key] = aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout_config,
                    **session_kwargs
                )
                
                logger.info(f"[SESSION-MANAGER] Created session for {session_key} with {connector_config['limit']} max connections")
            
            return self._sessions[session_key]
    
    async def get_session_for_api(self, api_name: str, base_url: str) -> aiohttp.ClientSession:
        """
        Get a session optimized for a specific API
        
        Args:
            api_name: Name of the API (e.g., 'salesforce', 'woocommerce')
            base_url: Base URL for the API
            
        Returns:
            Optimized aiohttp ClientSession
        """
        # API-specific optimizations
        optimizations = {
            'salesforce': {
                'connector_config': {
                    'limit': 50,  # Salesforce rate limits
                    'limit_per_host': 20,
                    'keepalive_timeout': 90,  # Longer for Salesforce sessions
                },
                'timeout': aiohttp.ClientTimeout(total=120, connect=15, sock_read=90),
                'headers': {
                    'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            },
            'woocommerce': {
                'connector_config': {
                    'limit': 50,
                    'limit_per_host': 20,
                    'keepalive_timeout': 60,
                },
                'timeout': aiohttp.ClientTimeout(total=60, connect=5, sock_read=30),
                'headers': {
                    'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0',
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            }
        }
        
        config = optimizations.get(api_name, {})
        logger.info(f"[SESSION-MANAGER] Getting optimized session for {api_name}")
        
        return await self.get_session(base_url, **config)
    
    async def close_session(self, base_url: str):
        """
        Close a specific session
        
        Args:
            base_url: Base URL of the session to close
        """
        parsed = urlparse(base_url)
        session_key = f"{parsed.scheme}://{parsed.netloc}"
        
        async with self._lock:
            if session_key in self._sessions:
                logger.info(f"[SESSION-MANAGER] Closing session for {session_key}")
                await self._sessions[session_key].close()
                del self._sessions[session_key]
    
    async def close_all_sessions(self):
        """Close all managed sessions"""
        async with self._lock:
            logger.info(f"[SESSION-MANAGER] Closing {len(self._sessions)} sessions")
            
            close_tasks = []
            for session_key, session in self._sessions.items():
                if not session.closed:
                    close_tasks.append(session.close())
            
            if close_tasks:
                await asyncio.gather(*close_tasks, return_exceptions=True)
            
            self._sessions.clear()
            logger.info("[SESSION-MANAGER] All sessions closed")
    
    def get_session_stats(self) -> Dict[str, Dict]:
        """
        Get statistics about current sessions
        
        Returns:
            Dictionary with session statistics
        """
        stats = {}
        for session_key, session in self._sessions.items():
            if not session.closed:
                connector = session.connector
                stats[session_key] = {
                    'closed': session.closed,
                    'connections_count': len(connector._conns) if hasattr(connector, '_conns') else 0,
                    'connector_limit': connector.limit,
                    'connector_limit_per_host': connector.limit_per_host
                }
            else:
                stats[session_key] = {'closed': True}
        
        return stats
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all sessions
        
        Returns:
            Dictionary mapping session keys to health status
        """
        health = {}
        async with self._lock:
            for session_key, session in self._sessions.items():
                health[session_key] = not session.closed
        
        return health
    
    async def cleanup_closed_sessions(self):
        """Remove any closed sessions from the manager"""
        async with self._lock:
            closed_sessions = [
                session_key for session_key, session in self._sessions.items()
                if session.closed
            ]
            
            for session_key in closed_sessions:
                logger.info(f"[SESSION-MANAGER] Removing closed session: {session_key}")
                del self._sessions[session_key]
    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, '_sessions') and self._sessions:
            logger.warning("[SESSION-MANAGER] Sessions still open during destruction")

# Global instance
session_manager = SharedSessionManager()