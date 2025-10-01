#!/usr/bin/env python3
"""
Comprehensive QuickBase API Test Suite
Tests various endpoints and methods to determine what works with the current credentials
"""
import asyncio
import aiohttp
import os
import logging
import json
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    print("dotenv not available - using system environment variables")

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class QuickBaseAPITester:
    """Comprehensive QuickBase API tester"""

    def __init__(self):
        self.realm_hostname = os.getenv('QUICKBASE_REALM_HOSTNAME', 'example.quickbase.com')
        self.user_token = os.getenv('QUICKBASE_USER_TOKEN')
        self.app_id = os.getenv('QUICKBASE_APP_ID', 'YOUR_APP_ID')
        self.base_url = "https://api.quickbase.com/v1"
        self.session = None

        print(f"Testing with:")
        print(f"  Realm: {self.realm_hostname}")
        print(f"  App ID: {self.app_id}")
        print(f"  Token: {self.user_token[:10]}... (truncated)")
        print("-" * 60)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def connect(self):
        """Create HTTP session with proper headers"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    'QB-Realm-Hostname': self.realm_hostname,
                    'Authorization': f'QB-USER-TOKEN {self.user_token}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'QuickBase-API-Tester/1.0'
                }
            )

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None

    async def test_endpoint(self, method: str, endpoint: str, data: dict = None, description: str = ""):
        """Generic endpoint tester with detailed logging"""
        print(f"\n🔍 Testing: {description or endpoint}")
        print(f"   Method: {method.upper()}")
        print(f"   URL: {self.base_url}{endpoint}")

        try:
            if method.upper() == 'GET':
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    return await self._handle_response(response, endpoint)
            elif method.upper() == 'POST':
                async with self.session.post(f"{self.base_url}{endpoint}", json=data) as response:
                    return await self._handle_response(response, endpoint)

        except Exception as e:
            print(f"   ❌ Exception: {e}")
            return {'success': False, 'error': str(e)}

    async def _handle_response(self, response, endpoint):
        """Handle HTTP response with detailed logging"""
        print(f"   Status: {response.status}")

        # Get response text
        try:
            response_text = await response.text()
            print(f"   Response Length: {len(response_text)} characters")
        except:
            response_text = ""

        # Try to parse JSON
        try:
            if response_text:
                response_data = json.loads(response_text)
            else:
                response_data = {}
        except:
            response_data = {'raw_response': response_text}

        if response.status == 200:
            print(f"   ✅ Success!")
            if isinstance(response_data, list):
                print(f"   📋 Returned {len(response_data)} items")
            elif isinstance(response_data, dict):
                print(f"   📋 Returned object with keys: {list(response_data.keys())}")
            return {'success': True, 'data': response_data, 'status': response.status}
        else:
            print(f"   ❌ Failed: HTTP {response.status}")
            if response_data:
                print(f"   💬 Error details: {response_data}")
            return {'success': False, 'data': response_data, 'status': response.status}

    async def run_comprehensive_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("🚀 QUICKBASE API COMPREHENSIVE TEST SUITE")
        print("=" * 60)

        tests = [
            # Test 1: Basic app info
            {
                'method': 'GET',
                'endpoint': f'/apps/{self.app_id}',
                'description': f'Get app info for {self.app_id}'
            },

            # Test 2: List tables in the app
            {
                'method': 'GET',
                'endpoint': f'/tables?appId={self.app_id}',
                'description': f'List tables in app {self.app_id}'
            },

            # Test 3: Try different app info approaches
            {
                'method': 'GET',
                'endpoint': f'/apps/{self.app_id}/variables',
                'description': 'Get app variables'
            },

            # Test 4: User info (might show what apps the token has access to)
            {
                'method': 'GET',
                'endpoint': '/auth/temporary',
                'description': 'Test auth endpoint'
            },

            # Test 5: Try to get app schema
            {
                'method': 'GET',
                'endpoint': f'/apps/{self.app_id}/schema',
                'description': 'Get app schema'
            }
        ]

        results = []

        for i, test in enumerate(tests, 1):
            print(f"\n{'='*20} TEST {i}/{len(tests)} {'='*20}")
            result = await self.test_endpoint(
                test['method'],
                test['endpoint'],
                test.get('data'),
                test['description']
            )
            results.append({
                'test': test['description'],
                'result': result
            })

            # If we got tables, test one of them
            if result['success'] and 'tables' in str(result.get('data', {})).lower():
                await self._test_tables_from_response(result['data'])

        # Summary
        print(f"\n{'='*60}")
        print("📊 TEST SUMMARY")
        print("=" * 60)

        successful_tests = [r for r in results if r['result']['success']]
        failed_tests = [r for r in results if not r['result']['success']]

        print(f"✅ Successful tests: {len(successful_tests)}/{len(results)}")
        print(f"❌ Failed tests: {len(failed_tests)}/{len(results)}")

        if successful_tests:
            print(f"\n🎉 Working endpoints:")
            for test in successful_tests:
                print(f"   - {test['test']}")

        if failed_tests:
            print(f"\n⚠️  Failed endpoints:")
            for test in failed_tests:
                status = test['result'].get('status', 'Unknown')
                print(f"   - {test['test']} (HTTP {status})")

        # Next steps recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if successful_tests:
            print("✅ Authentication is working!")
            print("✅ You have some API access - let's build on what works")
            if any('tables' in str(t['result'].get('data', '')).lower() for t in successful_tests):
                print("✅ Table access confirmed - you can browse table data")
        else:
            print("⚠️  No endpoints worked - let's troubleshoot:")
            print("   1. Verify the token is active in QuickBase")
            print("   2. Check if token is assigned to the correct app")
            print("   3. Verify app ID is correct")

        return results

    async def _test_tables_from_response(self, data):
        """If we got table data, test accessing one of the tables"""
        if isinstance(data, list) and len(data) > 0:
            first_table = data[0]
            table_id = first_table.get('id')
            table_name = first_table.get('name', 'Unknown')

            if table_id:
                print(f"\n🔍 Bonus Test: Accessing table '{table_name}' (ID: {table_id})")

                # Test getting fields for this table
                fields_result = await self.test_endpoint(
                    'GET',
                    f'/fields?tableId={table_id}',
                    description=f'Get fields for table {table_name}'
                )

                # Test getting reports for this table
                reports_result = await self.test_endpoint(
                    'GET',
                    f'/reports?tableId={table_id}',
                    description=f'Get reports for table {table_name}'
                )

                # If we got reports, try to get data from one
                if reports_result['success'] and reports_result.get('data'):
                    reports_data = reports_result['data']
                    if isinstance(reports_data, list) and len(reports_data) > 0:
                        first_report = reports_data[0]
                        report_id = first_report.get('id')
                        report_name = first_report.get('name', 'Unknown Report')

                        if report_id:
                            # Try to get data (limited to 5 records)
                            query_data = {
                                "from": table_id,
                                "select": [],  # Will get default fields
                                "options": {"top": 5}
                            }

                            await self.test_endpoint(
                                'POST',
                                '/records/query',
                                data=query_data,
                                description=f'Get 5 records from {report_name}'
                            )

async def main():
    """Main test function"""
    print("QuickBase API Comprehensive Test Starting...")
    print("This will test various endpoints to see what works with your credentials.\n")

    # Check environment variables
    if not os.getenv('QUICKBASE_USER_TOKEN'):
        print("❌ ERROR: QUICKBASE_USER_TOKEN not found in environment")
        return False

    if not os.getenv('QUICKBASE_REALM_HOSTNAME'):
        print("❌ ERROR: QUICKBASE_REALM_HOSTNAME not found in environment")
        return False

    try:
        async with QuickBaseAPITester() as tester:
            results = await tester.run_comprehensive_tests()

            # Save results to file for analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"quickbase_test_results_{timestamp}.json"

            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            print(f"\n💾 Detailed results saved to: {results_file}")

            return True

    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    print(f"\n{'='*60}")
    if success:
        print("🏁 Test completed! Check the output above for working endpoints.")
    else:
        print("💥 Test failed - check error messages above.")
    print("=" * 60)