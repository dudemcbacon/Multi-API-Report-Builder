#!/usr/bin/env python3
"""
QuickBase Permission Audit - Windows Compatible Version
Test low-level permissions and basic operations without emoji characters
"""
import asyncio
import aiohttp
import os
import json
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    print("dotenv not available - using system environment variables")

class QuickBasePermissionAudit:
    """Test different permission levels and operations"""

    def __init__(self):
        self.realm_hostname = 'example.quickbase.com'  # From diagnostic - this one works for auth
        self.user_token = os.getenv('QUICKBASE_USER_TOKEN')
        self.app_id = os.getenv('QUICKBASE_APP_ID', 'YOUR_APP_ID')
        self.base_url = "https://api.quickbase.com/v1"

        print(f"QuickBase Permission Audit")
        print(f"=========================")
        print(f"  Realm: {self.realm_hostname}")
        print(f"  App ID: {self.app_id}")
        print(f"  Token: {self.user_token[:10]}... (truncated)")
        print("-" * 50)

    async def run_permission_audit(self):
        """Run comprehensive permission audit"""

        audit_results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'realm': self.realm_hostname,
                'app_id': self.app_id
            },
            'tests': []
        }

        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'QB-Realm-Hostname': self.realm_hostname,
            'Authorization': f'QB-USER-TOKEN {self.user_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'QuickBase-Permission-Audit/1.0'
        }

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            # First, get the list of tables since we know this works
            print(f"\nStep 1: Getting list of tables from the working endpoint...")
            tables_result = await self._get_tables_list(session)

            if tables_result['success']:
                table_ids = [table['id'] for table in tables_result['data'][:3]]  # Test first 3 tables
                print(f"Found {len(tables_result['data'])} tables, testing first 3: {table_ids}")

                # Test table-specific operations
                print(f"\nStep 2: Testing table-specific operations...")
                for table_id in table_ids:
                    print(f"\n>> Testing Table ID: {table_id}")

                    # Test fields endpoint
                    fields_test = {
                        'category': 'Table Fields',
                        'operation': f'Get Fields for Table {table_id}',
                        'method': 'GET',
                        'endpoint': f'/fields?tableId={table_id}',
                        'table_id': table_id
                    }
                    result = await self._execute_test(session, fields_test)
                    fields_test['result'] = result
                    audit_results['tests'].append(fields_test)
                    self._print_test_result(fields_test, len(audit_results['tests']))

                    # Test reports endpoint
                    reports_test = {
                        'category': 'Table Reports',
                        'operation': f'Get Reports for Table {table_id}',
                        'method': 'GET',
                        'endpoint': f'/reports?tableId={table_id}',
                        'table_id': table_id
                    }
                    result = await self._execute_test(session, reports_test)
                    reports_test['result'] = result
                    audit_results['tests'].append(reports_test)
                    self._print_test_result(reports_test, len(audit_results['tests']))

                    # Test basic record query (1 record only)
                    query_test = {
                        'category': 'Basic Data Query',
                        'operation': f'Query 1 Record from Table {table_id}',
                        'method': 'POST',
                        'endpoint': '/records/query',
                        'data': {
                            "from": table_id,
                            "options": {"top": 1}
                        },
                        'table_id': table_id
                    }
                    result = await self._execute_test(session, query_test)
                    query_test['result'] = result
                    audit_results['tests'].append(query_test)
                    self._print_test_result(query_test, len(audit_results['tests']))

                    # If we found a working endpoint, test more operations on this table
                    if result['success']:
                        print(f"   >> SUCCESS! Testing more operations on this table...")
                        await self._test_additional_operations(session, table_id, audit_results)
            else:
                print("ERROR: Cannot get tables list - this should have worked!")
                return audit_results

        # Generate summary report
        await self._generate_summary_report(audit_results)
        return audit_results

    async def _get_tables_list(self, session):
        """Get the list of tables (we know this works)"""
        try:
            url = f"{self.base_url}/tables?appId={self.app_id}"
            async with session.get(url) as response:
                if response.status == 200:
                    data = json.loads(await response.text())
                    return {
                        'success': True,
                        'data': data,
                        'status_code': 200
                    }
                else:
                    return {
                        'success': False,
                        'message': f'HTTP {response.status}',
                        'status_code': response.status
                    }
        except Exception as e:
            return {
                'success': False,
                'message': f'Exception: {str(e)}',
                'status_code': 'Exception'
            }

    async def _test_additional_operations(self, session, table_id, audit_results):
        """Test additional operations on a working table"""
        additional_tests = [
            {
                'category': 'Extended Data Query',
                'operation': f'Query 5 Records with Select Fields',
                'method': 'POST',
                'endpoint': '/records/query',
                'data': {
                    "from": table_id,
                    "select": [3, 6, 7],  # Common field IDs
                    "options": {"top": 5}
                }
            },
            {
                'category': 'Table Summary',
                'operation': f'Get Table Summary Statistics',
                'method': 'POST',
                'endpoint': '/records/summarize',
                'data': {
                    "from": table_id,
                    "groupBy": [{"fieldId": 3, "grouping": "equal-values"}],
                    "summaryFields": [{"fieldId": 6, "operation": "count"}],
                    "options": {"top": 10}
                }
            }
        ]

        for test in additional_tests:
            test['table_id'] = table_id
            result = await self._execute_test(session, test)
            test['result'] = result
            audit_results['tests'].append(test)
            self._print_test_result(test, len(audit_results['tests']))

    def _print_test_result(self, test, test_num):
        """Print test result in Windows-compatible format"""
        print(f"[{test_num}] {test['category']}: {test['operation']}")

        if test['result']['success']:
            print(f"    >> SUCCESS: {test['result']['message']}")
            if test['result'].get('data_summary'):
                print(f"    >> Data: {test['result']['data_summary']}")
        else:
            status_code = test['result'].get('status_code', 'Unknown')
            print(f"    >> FAILED: HTTP {status_code} - {test['result']['message']}")

    async def _execute_test(self, session, test):
        """Execute a single permission test"""
        try:
            url = f"{self.base_url}{test['endpoint']}"

            if test['method'] == 'GET':
                async with session.get(url) as response:
                    return await self._process_response(response)
            elif test['method'] == 'POST':
                async with session.post(url, json=test.get('data')) as response:
                    return await self._process_response(response)

        except Exception as e:
            return {
                'success': False,
                'message': f'Exception: {str(e)}',
                'status_code': 'Exception'
            }

    async def _process_response(self, response):
        """Process HTTP response and extract meaningful information"""
        try:
            response_text = await response.text()

            if response.status == 200:
                # Success - try to parse and summarize data
                try:
                    data = json.loads(response_text)
                    summary = self._summarize_data(data)
                    return {
                        'success': True,
                        'message': 'API call successful',
                        'status_code': 200,
                        'data_summary': summary
                    }
                except:
                    return {
                        'success': True,
                        'message': f'API call successful, non-JSON response ({len(response_text)} chars)',
                        'status_code': 200,
                        'data_summary': f'Text response: {response_text[:100]}...'
                    }
            else:
                # Failed - extract error message
                try:
                    error_data = json.loads(response_text)
                    error_msg = error_data.get('message', 'Unknown error')
                    error_desc = error_data.get('description', '')
                    full_error = f"{error_msg} - {error_desc}".strip(' -')
                except:
                    full_error = response_text[:200] if response_text else 'No error message'

                return {
                    'success': False,
                    'message': full_error,
                    'status_code': response.status
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing response: {str(e)}',
                'status_code': response.status
            }

    def _summarize_data(self, data):
        """Create a summary of returned data"""
        if isinstance(data, list):
            if len(data) == 0:
                return "Empty list returned"
            elif len(data) == 1:
                item = data[0]
                if isinstance(item, dict):
                    return f"1 item with keys: {list(item.keys())[:5]}"
                else:
                    return f"1 item: {str(item)[:50]}"
            else:
                return f"{len(data)} items returned"
        elif isinstance(data, dict):
            keys = list(data.keys())[:10]  # First 10 keys
            return f"Object with keys: {keys}"
        else:
            return f"Data type: {type(data).__name__}, value: {str(data)[:50]}"

    async def _generate_summary_report(self, audit_results):
        """Generate a comprehensive summary report"""
        tests = audit_results['tests']
        successful_tests = [t for t in tests if t['result']['success']]
        failed_tests = [t for t in tests if not t['result']['success']]

        print(f"\n{'='*60}")
        print("PERMISSION AUDIT SUMMARY REPORT")
        print("=" * 60)

        print(f"\nOverall Results:")
        print(f"  Total tests: {len(tests)}")
        print(f"  Successful: {len(successful_tests)}")
        print(f"  Failed: {len(failed_tests)}")
        print(f"  Success rate: {len(successful_tests)/len(tests)*100:.1f}%")

        if successful_tests:
            print(f"\n*** WORKING OPERATIONS ({len(successful_tests)}):")
            for test in successful_tests:
                print(f"  [OK] {test['operation']}")
                print(f"       Category: {test['category']}")
                print(f"       Data: {test['result'].get('data_summary', 'No data summary')}")
                print()

        if failed_tests:
            print(f"\n[X] FAILED OPERATIONS ({len(failed_tests)}):")

            # Group by error type for better analysis
            error_groups = {}
            for test in failed_tests:
                status = test['result']['status_code']
                if status not in error_groups:
                    error_groups[status] = []
                error_groups[status].append(test)

            for status, group_tests in error_groups.items():
                print(f"\n    HTTP {status} Errors ({len(group_tests)}):")
                for test in group_tests:
                    print(f"      - {test['operation']}: {test['result']['message']}")

        # Recommendations
        print(f"\n*** RECOMMENDATIONS:")

        if len(successful_tests) > 0:
            print(f"  [+] GREAT NEWS: Your token HAS API access!")
            print(f"  [+] Focus on the working operations above")
            print(f"  [+] You can build functionality using successful operations")

            # Check what types of access work
            working_categories = set(t['category'] for t in successful_tests)
            print(f"  [+] Working permission categories: {', '.join(working_categories)}")

            # Check if any table had full access
            working_tables = set(t.get('table_id', 'N/A') for t in successful_tests if t.get('table_id'))
            if working_tables:
                print(f"  [+] Tables with working access: {', '.join(working_tables)}")
        else:
            print(f"  [!] No API operations worked")
            print(f"  [!] Contact the app administrator to:")
            print(f"      - Verify token is assigned to app '{self.app_id}'")
            print(f"      - Confirm your role includes API access permissions")
            print(f"      - Check app-level API access restrictions")

        # Save detailed report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"quickbase_permission_audit_{timestamp}.json"

        with open(report_file, 'w') as f:
            json.dump(audit_results, f, indent=2, default=str)

        print(f"\n[FILE] Detailed audit report saved to: {report_file}")

async def main():
    """Main audit function"""
    print("Starting QuickBase Permission Audit...")
    print("This will test various permission levels to find what works.\n")

    if not os.getenv('QUICKBASE_USER_TOKEN'):
        print("ERROR: QUICKBASE_USER_TOKEN not found in environment")
        return False

    try:
        auditor = QuickBasePermissionAudit()
        results = await auditor.run_permission_audit()
        return True

    except Exception as e:
        print(f"Audit failed: {e}")
        return False

if __name__ == '__main__':
    success = asyncio.run(main())
    print(f"\n{'='*60}")
    if success:
        print("Permission audit completed!")
    else:
        print("Permission audit failed.")
    print("=" * 60)