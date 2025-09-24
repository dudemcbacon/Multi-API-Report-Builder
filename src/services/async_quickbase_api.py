"""
Simple Async QuickBase API implementation using aiohttp only
Thread-safe implementation following Avalara/WooCommerce patterns
"""
import asyncio
import aiohttp
import logging
import os
from typing import Dict, List, Optional, Any
import polars as pl
import json

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass  # dotenv not available, use system environment variables

logger = logging.getLogger(__name__)

class AsyncQuickBaseAPI:
    """
    Simple async QuickBase API client using only aiohttp
    Thread-safe implementation for PyQt compatibility
    """

    # Secure credential management - use environment variables
    REALM_HOSTNAME = os.getenv('QUICKBASE_REALM_HOSTNAME')
    USER_TOKEN = os.getenv('QUICKBASE_USER_TOKEN')
    DEFAULT_APP_ID = os.getenv('QUICKBASE_APP_ID')

    def __init__(self, realm_hostname: str = None, user_token: str = None,
                 app_id: str = None, verbose_logging: bool = False):
        """
        Initialize Simple QuickBase API client

        Args:
            realm_hostname: QuickBase realm hostname (e.g., 'company.quickbase.com')
            user_token: QuickBase user token for authentication
            app_id: Default application ID
            verbose_logging: Enable detailed logging for debugging
        """
        self.realm_hostname = realm_hostname or self.REALM_HOSTNAME
        self.user_token = user_token or self.USER_TOKEN
        self.default_app_id = app_id or self.DEFAULT_APP_ID
        self.verbose_logging = verbose_logging

        # Only aiohttp session - no external client libraries
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Establish connection to QuickBase API using only aiohttp"""
        try:
            if not self.session:
                # Create aiohttp session with QuickBase headers
                timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
                self.session = aiohttp.ClientSession(
                    timeout=timeout,
                    headers={
                        'QB-Realm-Hostname': self.realm_hostname,
                        'Authorization': f'QB-USER-TOKEN {self.user_token}',
                        'Content-Type': 'application/json',
                        'User-Agent': 'SalesForceReportPull-AsyncAPI/1.0'
                    }
                )

            if self.verbose_logging:
                logger.info("[ASYNC-QB-API] Connected to QuickBase API")

        except Exception as e:
            logger.error(f"[ASYNC-QB-API] Connection error: {e}")
            raise

    async def close(self):
        """Close QuickBase API connection"""
        try:
            if self.session:
                await self.session.close()
                self.session = None

            if self.verbose_logging:
                logger.info("[ASYNC-QB-API] Connection closed")

        except Exception as e:
            logger.error(f"[ASYNC-QB-API] Error closing connection: {e}")

    def validate_credentials(self) -> Dict[str, Any]:
        """Validate QuickBase credentials without making HTTP requests (thread-safe)"""
        try:
            # Basic validation without network calls
            if not self.realm_hostname:
                return {
                    'success': False,
                    'error': 'QuickBase realm hostname not configured',
                    'validated': False
                }

            if not self.user_token:
                return {
                    'success': False,
                    'error': 'QuickBase user token not configured',
                    'validated': False
                }

            # Basic format validation
            if not self.realm_hostname.endswith('.quickbase.com'):
                return {
                    'success': False,
                    'error': 'Invalid QuickBase realm hostname format',
                    'validated': False
                }

            if len(self.user_token) < 20:  # QuickBase tokens are typically longer
                return {
                    'success': False,
                    'error': 'QuickBase user token appears to be invalid format',
                    'validated': False
                }

            return {
                'success': True,
                'message': 'QuickBase credentials appear valid',
                'validated': True,
                'realm_hostname': self.realm_hostname,
                'has_app_id': bool(self.default_app_id)
            }

        except Exception as e:
            logger.error(f"[ASYNC-QB-API] Error validating credentials: {e}")
            return {
                'success': False,
                'error': f'Credential validation error: {str(e)}',
                'validated': False
            }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to QuickBase API using simple HTTP request

        Returns:
            Dictionary with connection test results
        """
        try:
            logger.info("[ASYNC-QB-API] Testing QuickBase connection")

            if not self.session:
                await self.connect()

            # Simple ping to QuickBase API to test connection
            url = "https://api.quickbase.com/v1/apps"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    app_count = len(data.get('apps', []))

                    return {
                        'success': True,
                        'message': f'Successfully connected to QuickBase',
                        'details': {
                            'realm': self.realm_hostname,
                            'apps_found': app_count
                        }
                    }
                else:
                    error_text = await response.text()
                    return {
                        'success': False,
                        'message': f'QuickBase API error: {response.status}',
                        'details': error_text
                    }

        except Exception as e:
            logger.error(f"[ASYNC-QB-API] Connection test failed: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}',
                'details': None
            }

    async def get_apps(self) -> List[Dict[str, Any]]:
        """
        Get list of available QuickBase applications
        Simple implementation for basic functionality
        """
        try:
            if not self.session:
                await self.connect()

            url = "https://api.quickbase.com/v1/apps"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('apps', [])
                else:
                    logger.error(f"[ASYNC-QB-API] Failed to get apps: {response.status}")
                    return []

        except Exception as e:
            logger.error(f"[ASYNC-QB-API] Error getting apps: {e}")
            return []

    def get_static_data_sources(self) -> List[Dict[str, Any]]:
        """
        Get static data sources for tree population
        No network calls - completely thread safe
        """
        return [
            {
                'id': 'quickbase_apps',
                'name': 'Applications',
                'type': 'browse',
                'data_type': 'apps',
                'icon': 'fa5s.folder',
                'modified': ''
            },
            {
                'id': 'quickbase_query',
                'name': 'Custom Query Builder',
                'type': 'query_builder',
                'data_type': 'query',
                'icon': 'fa5s.search',
                'modified': ''
            }
        ]