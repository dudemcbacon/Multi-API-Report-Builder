#!/usr/bin/env python3
"""
Comprehensive tests for Salesforce API functionality
Tests connection, authentication, and data retrieval without making changes
"""
import sys
import os
import time
import logging
from typing import Dict, Any

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.salesforce_api import SalesforceAPI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_salesforce_connection():
    """Test Salesforce connection and authentication"""
    print("=" * 60)
    print("TESTING SALESFORCE API CONNECTION")
    print("=" * 60)
    
    try:
        # Initialize Salesforce API
        sf_api = SalesforceAPI()
        print("✓ SalesforceAPI initialized successfully")
        
        # Test if credentials are available
        has_creds = sf_api.has_credentials()
        print(f"✓ Credentials available: {has_creds}")
        
        # Test connection
        print("\nTesting connection...")
        start_time = time.time()
        
        # This will use stored credentials if available, or prompt for OAuth
        connection_result = sf_api.test_connection()
        
        connection_time = time.time() - start_time
        print(f"✓ Connection test completed in {connection_time:.2f} seconds")
        
        if connection_result['success']:
            print("✓ CONNECTION SUCCESSFUL!")
            print(f"  - Organization: {connection_result.get('organization', 'Unknown')}")
            print(f"  - Instance URL: {connection_result.get('instance_url', 'Unknown')}")
            print(f"  - Account Count: {connection_result.get('account_count', 0)}")
            print(f"  - Details: {connection_result.get('details', 'No details')}")
            return True, sf_api, connection_time
        else:
            print("✗ CONNECTION FAILED!")
            print(f"  - Error: {connection_result.get('error', 'Unknown error')}")
            print(f"  - Details: {connection_result.get('details', 'No details')}")
            return False, None, connection_time
            
    except Exception as e:
        print(f"✗ Exception during connection test: {e}")
        import traceback
        traceback.print_exc()
        return False, None, 0

def test_salesforce_reports(sf_api: SalesforceAPI):
    """Test Salesforce reports retrieval"""
    print("\n" + "=" * 60)
    print("TESTING SALESFORCE REPORTS RETRIEVAL")
    print("=" * 60)
    
    try:
        print("Retrieving reports list...")
        start_time = time.time()
        
        reports = sf_api.get_reports()
        
        reports_time = time.time() - start_time
        print(f"✓ Reports retrieved in {reports_time:.2f} seconds")
        print(f"✓ Found {len(reports)} reports")
        
        if reports:
            print("\nSample reports:")
            for i, report in enumerate(reports[:5]):  # Show first 5 reports
                print(f"  {i+1}. {report.get('name', 'Unknown')} (ID: {report.get('id', 'Unknown')})")
                print(f"     Folder: {report.get('folder', 'Unknown')}")
                print(f"     Format: {report.get('format', 'Unknown')}")
            
            if len(reports) > 5:
                print(f"     ... and {len(reports) - 5} more reports")
        
        return True, reports, reports_time
        
    except Exception as e:
        print(f"✗ Exception during reports retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, [], 0

def test_salesforce_report_data(sf_api: SalesforceAPI, reports: list):
    """Test Salesforce report data retrieval"""
    print("\n" + "=" * 60)
    print("TESTING SALESFORCE REPORT DATA RETRIEVAL")
    print("=" * 60)
    
    if not reports:
        print("✗ No reports available for testing")
        return False, None, 0
    
    # Try to find a sales receipt report or use the first available report
    target_report = None
    
    # Look for sales receipt import report
    sales_receipt_report_id = "00ORl000007JNmTMAW"  # From your config
    for report in reports:
        if report.get('id') == sales_receipt_report_id:
            target_report = report
            print(f"✓ Found target sales receipt report: {report.get('name')}")
            break
    
    # If not found, use the first report
    if not target_report and reports:
        target_report = reports[0]
        print(f"✓ Using first available report: {target_report.get('name')}")
    
    if not target_report:
        print("✗ No suitable report found for testing")
        return False, None, 0
    
    try:
        print(f"Retrieving data for report: {target_report.get('name')}")
        print(f"Report ID: {target_report.get('id')}")
        
        start_time = time.time()
        
        # Get report data
        report_data = sf_api.get_report_data(target_report['id'])
        
        data_time = time.time() - start_time
        print(f"✓ Report data retrieved in {data_time:.2f} seconds")
        
        if report_data is not None and len(report_data) > 0:
            print(f"✓ Report contains {len(report_data)} rows and {len(report_data.columns)} columns")
            print("✓ Column names:")
            for i, col in enumerate(report_data.columns):
                print(f"     {i+1}. {col}")
                if i >= 9:  # Show first 10 columns
                    print(f"     ... and {len(report_data.columns) - 10} more columns")
                    break
            
            # Show a sample of data (first row)
            if len(report_data) > 0:
                print("\n✓ Sample data (first row):")
                first_row = report_data.head(1).to_dicts()[0]
                for key, value in list(first_row.items())[:5]:  # Show first 5 fields
                    print(f"     {key}: {value}")
                if len(first_row) > 5:
                    print(f"     ... and {len(first_row) - 5} more fields")
        else:
            print("⚠ Report data is empty or None")
            
        return True, report_data, data_time
        
    except Exception as e:
        print(f"✗ Exception during report data retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False, None, 0

def test_salesforce_soql(sf_api: SalesforceAPI):
    """Test Salesforce SOQL query execution"""
    print("\n" + "=" * 60)
    print("TESTING SALESFORCE SOQL QUERIES")
    print("=" * 60)
    
    try:
        # Test simple SOQL query
        test_query = "SELECT Id, Name FROM Organization LIMIT 1"
        print(f"Executing SOQL: {test_query}")
        
        start_time = time.time()
        
        result = sf_api.execute_soql(test_query)
        
        soql_time = time.time() - start_time
        print(f"✓ SOQL executed in {soql_time:.2f} seconds")
        
        if result is not None and len(result) > 0:
            print(f"✓ Query returned {len(result)} rows and {len(result.columns)} columns")
            print("✓ Result data:")
            for row in result.to_dicts():
                for key, value in row.items():
                    print(f"     {key}: {value}")
        else:
            print("⚠ SOQL query returned empty result")
            
        return True, soql_time
        
    except Exception as e:
        print(f"✗ Exception during SOQL execution: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def test_salesforce_performance_summary(connection_time: float, reports_time: float, 
                                       data_time: float, soql_time: float):
    """Summarize performance metrics"""
    print("\n" + "=" * 60)
    print("SALESFORCE API PERFORMANCE SUMMARY")
    print("=" * 60)
    
    total_time = connection_time + reports_time + data_time + soql_time
    
    print(f"Connection Time:      {connection_time:.2f} seconds")
    print(f"Reports List Time:    {reports_time:.2f} seconds")
    print(f"Report Data Time:     {data_time:.2f} seconds")
    print(f"SOQL Query Time:      {soql_time:.2f} seconds")
    print(f"Total Test Time:      {total_time:.2f} seconds")
    
    # Performance assessment
    print("\nPerformance Assessment:")
    if connection_time < 5:
        print("✓ Connection speed: Good")
    elif connection_time < 10:
        print("⚠ Connection speed: Moderate")
    else:
        print("✗ Connection speed: Slow")
    
    if reports_time < 3:
        print("✓ Reports retrieval: Good")
    elif reports_time < 8:
        print("⚠ Reports retrieval: Moderate")
    else:
        print("✗ Reports retrieval: Slow")
    
    if data_time < 10:
        print("✓ Report data retrieval: Good")
    elif data_time < 30:
        print("⚠ Report data retrieval: Moderate")
    else:
        print("✗ Report data retrieval: Slow")

def main():
    """Run all Salesforce API tests"""
    print("SALESFORCE API FUNCTIONALITY TESTS")
    print("This will test connection, authentication, and data retrieval")
    print("No modifications will be made to your data or configuration")
    print()
    
    all_success = True
    connection_time = reports_time = data_time = soql_time = 0
    
    # Test 1: Connection
    success, sf_api, connection_time = test_salesforce_connection()
    if not success:
        print("\n✗ ABORTING TESTS - Could not establish Salesforce connection")
        return False
    all_success &= success
    
    # Test 2: Reports
    success, reports, reports_time = test_salesforce_reports(sf_api)
    all_success &= success
    
    # Test 3: Report Data
    success, report_data, data_time = test_salesforce_report_data(sf_api, reports)
    all_success &= success
    
    # Test 4: SOQL
    success, soql_time = test_salesforce_soql(sf_api)
    all_success &= success
    
    # Performance Summary
    test_salesforce_performance_summary(connection_time, reports_time, data_time, soql_time)
    
    # Final Results
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ALL SALESFORCE API TESTS PASSED!")
        print("Your Salesforce API integration is working correctly.")
    else:
        print("❌ SOME SALESFORCE API TESTS FAILED!")
        print("Please review the errors above before proceeding with optimizations.")
    print("=" * 60)
    
    return all_success

if __name__ == "__main__":
    main()