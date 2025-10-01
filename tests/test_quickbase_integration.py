#!/usr/bin/env python3
"""
Quick test script for QuickBase API integration
"""
import asyncio
import sys
import os
import logging

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.async_quickbase_api import AsyncQuickBaseAPI
from src.ui.managers.connection_manager import ConnectionManager
from src.models.config import ConfigManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_quickbase_connection():
    """Test QuickBase API connection"""
    print("=" * 60)
    print("QuickBase Integration Test")
    print("=" * 60)

    try:
        # Test 1: Direct API connection
        print("\n1. Testing direct QuickBase API connection...")
        async with AsyncQuickBaseAPI() as qb_api:
            # Test credential validation
            cred_result = qb_api.validate_credentials()
            print(f"   Credential validation: {cred_result['success']}")
            if not cred_result['success']:
                print(f"   Error: {cred_result['error']}")
                return False

            # Test connection
            connection_result = await qb_api.test_connection()
            print(f"   Connection test: {connection_result['success']}")
            if connection_result['success']:
                details = connection_result.get('details', {})
                print(f"   Realm: {details.get('realm', 'Unknown')}")
                print(f"   Apps found: {details.get('apps_found', 0)}")

                # Test getting apps if connection successful
                print("\n2. Testing app retrieval...")
                apps = await qb_api.get_apps()
                print(f"   Retrieved {len(apps)} applications")

                if apps:
                    print("   First few apps:")
                    for app in apps[:3]:  # Show first 3 apps
                        print(f"     - {app.get('name', 'Unnamed')} (ID: {app.get('id', 'Unknown')})")

                    # Test getting tables for first app
                    first_app_id = apps[0].get('id')
                    if first_app_id:
                        print(f"\n3. Testing table retrieval for app {first_app_id}...")
                        tables = await qb_api.get_tables(first_app_id)
                        print(f"   Retrieved {len(tables)} tables")

                        if tables:
                            print("   First few tables:")
                            for table in tables[:3]:  # Show first 3 tables
                                print(f"     - {table.get('name', 'Unnamed')} (ID: {table.get('id', 'Unknown')})")

                            # Test getting reports for first table
                            first_table_id = tables[0].get('id')
                            if first_table_id:
                                print(f"\n4. Testing report retrieval for table {first_table_id}...")
                                reports = await qb_api.get_reports(first_table_id)
                                print(f"   Retrieved {len(reports)} reports")

                                if reports:
                                    print("   First few reports:")
                                    for report in reports[:3]:  # Show first 3 reports
                                        print(f"     - {report.get('name', 'Unnamed')} (ID: {report.get('id', 'Unknown')})")

                                    # Test getting data from first report (limited to 5 records)
                                    first_report_id = reports[0].get('id')
                                    if first_report_id:
                                        print(f"\n5. Testing data retrieval from report {first_report_id} (max 5 records)...")
                                        try:
                                            df = await qb_api.get_report_data(first_table_id, first_report_id, limit=5)
                                            if df is not None and not df.is_empty():
                                                print(f"   Retrieved {len(df)} records with {len(df.columns)} columns")
                                                print(f"   Columns: {df.columns}")
                                                if len(df) > 0:
                                                    print("   Sample data (first row):")
                                                    first_row = df.row(0)
                                                    for i, col in enumerate(df.columns):
                                                        value = first_row[i] if i < len(first_row) else "N/A"
                                                        print(f"     {col}: {value}")
                                            else:
                                                print("   No data returned")
                                        except Exception as e:
                                            print(f"   Error retrieving data: {e}")
            else:
                print(f"   Connection failed: {connection_result.get('message', 'Unknown error')}")
                return False

        # Test 2: Connection Manager integration
        print(f"\n6. Testing Connection Manager integration...")
        config_manager = ConfigManager()
        connection_manager = ConnectionManager(config_manager)

        conn_result = await connection_manager.test_connection('quickbase')
        print(f"   Connection Manager test: {conn_result['success']}")

        if conn_result['success']:
            print(f"   Message: {conn_result['message']}")
        else:
            print(f"   Error: {conn_result.get('error', 'Unknown')}")

        # Test 3: Static data sources
        print(f"\n7. Testing static data sources...")
        static_sources = AsyncQuickBaseAPI().get_static_data_sources()
        print(f"   Retrieved {len(static_sources)} static data sources")
        for source in static_sources:
            print(f"     - {source.get('name', 'Unnamed')} ({source.get('type', 'unknown')})")

        print("\n" + "=" * 60)
        print("QuickBase integration test completed successfully!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        logger.error("Test error", exc_info=True)
        return False

def main():
    """Main test function"""
    # Check if .env file exists
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.exists(env_file):
        print("ERROR: .env file not found!")
        print("Please ensure your .env file contains:")
        print("QUICKBASE_REALM_HOSTNAME=your_realm.quickbase.com")
        print("QUICKBASE_USER_TOKEN=your_user_token")
        print("QUICKBASE_APP_ID=your_default_app_id")
        return False

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        print("dotenv not available - using system environment variables")

    # Check required environment variables
    required_vars = ['QUICKBASE_REALM_HOSTNAME', 'QUICKBASE_USER_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"ERROR: Missing required environment variables: {missing_vars}")
        print("Please set them in your .env file")
        return False

    # Run the test
    try:
        result = asyncio.run(test_quickbase_connection())
        return result
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return False
    except Exception as e:
        print(f"Test failed with unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)