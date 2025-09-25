"""
Simple AsyncQuickBaseAPI wrapper using the quickbase-client library
Replaces 549 lines of complex HTTP code with ~50 lines using proper library
"""
import asyncio
import logging
import os
import polars as pl
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

try:
    from quickbase_client import QuickBaseApiClient
except ImportError:
    raise ImportError("quickbase-client library not found. Install with: pip install quickbase-client")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass

logger = logging.getLogger(__name__)

class AsyncQuickBaseAPI:
    """
    Simple async wrapper around QuickBaseApiClient
    Provides async interface for PyQt compatibility
    """

    def __init__(self, realm_hostname: str = None, user_token: str = None,
                 app_id: str = None, verbose_logging: bool = False):
        # Get credentials from environment if not provided
        self.realm_hostname = realm_hostname or os.getenv('QUICKBASE_REALM_HOSTNAME')
        self.user_token = user_token or os.getenv('QUICKBASE_USER_TOKEN')
        self.default_app_id = app_id or os.getenv('QUICKBASE_APP_ID')

        if not self.realm_hostname or not self.user_token:
            raise ValueError("QuickBase realm_hostname and user_token are required")

        # Create thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._client = None

        if verbose_logging:
            logging.getLogger('quickbase_client').setLevel(logging.DEBUG)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Initialize the QuickBase client"""
        def _create_client():
            return QuickBaseApiClient(
                user_token=self.user_token,
                realm_hostname=self.realm_hostname
            )

        self._client = await asyncio.get_event_loop().run_in_executor(
            self.executor, _create_client
        )
        logger.info(f"[QB-API] Connected to QuickBase realm: {self.realm_hostname}")

    async def close(self):
        """Close the client and executor"""
        if self.executor:
            self.executor.shutdown(wait=False)
        logger.info("[QB-API] Connection closed")

    async def test_connection(self) -> Dict[str, Any]:
        """Test the connection by fetching tables"""
        try:
            if not self._client:
                await self.connect()

            def _test():
                response = self._client.get_tables_for_app(self.default_app_id)
                if response.ok:
                    tables_data = response.json()
                    return len(tables_data)
                else:
                    raise Exception(f"QuickBase API error: {response.status_code} - {response.text}")

            table_count = await asyncio.get_event_loop().run_in_executor(
                self.executor, _test
            )

            return {
                'success': True,
                'message': f'Connected successfully. Found {table_count} tables.',
                'table_count': table_count
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def get_apps(self) -> List[Dict[str, Any]]:
        """Get tables (we use tables as apps in the tree)"""
        if not self._client:
            await self.connect()

        def _get_tables():
            response = self._client.get_tables_for_app(self.default_app_id)
            if response.ok:
                tables_data = response.json()
                return [
                    {
                        'id': table['id'],
                        'table_id': table['id'],
                        'name': table['name'],
                        'icon': 'fa5s.table',
                        'data_type': 'quickbase_table',
                        'pluralRecordName': table.get('pluralRecordName', 'Records'),
                        'updated': table.get('updated', '')
                    }
                    for table in tables_data
                ]
            else:
                raise Exception(f"QuickBase API error: {response.status_code} - {response.text}")

        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _get_tables
        )

    async def get_reports(self, table_id: str) -> List[Dict[str, Any]]:
        """Get reports for a table"""
        if not self._client:
            await self.connect()

        def _get_reports():
            response = self._client.get_reports_for_table(table_id)
            if response.ok:
                reports_data = response.json()
                return [
                    {
                        'id': report['id'],
                        'report_id': report['id'],
                        'name': report['name'],
                        'icon': 'fa5s.file-alt',
                        'data_type': 'quickbase_report',
                        'table_id': table_id
                    }
                    for report in reports_data
                ]
            else:
                raise Exception(f"QuickBase API error: {response.status_code} - {response.text}")

        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _get_reports
        )

    async def get_report_data(self, table_id: str, report_id: str = None) -> pl.DataFrame:
        """Get data from a report or table"""
        if not self._client:
            await self.connect()

        def _get_data():
            if report_id:
                # Get report data
                response = self._client.run_report(report_id, table_id)
            else:
                # Get table data (query all records)
                response = self._client.query(table_id=table_id)

            if not response.ok:
                raise Exception(f"QuickBase API error: {response.status_code} - {response.text}")

            # Convert response to JSON
            result = response.json()

            # Convert to Polars DataFrame
            if result and 'data' in result:
                records = result['data']
                if records:
                    # Build field ID to label mapping
                    field_map = {}
                    if 'fields' in result:
                        for field in result['fields']:
                            field_map[str(field['id'])] = field['label']

                    # Extract field data into flat dictionary with descriptive column names
                    flattened_records = []
                    for record in records:
                        flat_record = {}
                        for field_id, field_data in record.items():
                            # Use field label if available, otherwise fall back to field ID
                            column_name = field_map.get(field_id, field_id)
                            if isinstance(field_data, dict) and 'value' in field_data:
                                flat_record[column_name] = field_data['value']
                            else:
                                flat_record[column_name] = field_data
                        flattened_records.append(flat_record)

                    return pl.DataFrame(flattened_records)

            return pl.DataFrame()  # Empty DataFrame if no data

        return await asyncio.get_event_loop().run_in_executor(
            self.executor, _get_data
        )

    # Keep these methods for compatibility with existing code
    async def get_tables(self, app_id: str) -> List[Dict[str, Any]]:
        """Compatibility method - same as get_apps"""
        return await self.get_apps()