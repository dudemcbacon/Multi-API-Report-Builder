#!/usr/bin/env python3
"""
Test SOQL query script to retrieve Asset data with Account Name
Uses the existing project infrastructure from CUSTOM_REPORT_ROUTING_FIX.md
"""

# Simple approach - create a SOQL query that can be executed via the UI
import sys

def create_test_query():
    """Creates and prints the SOQL query for manual execution"""
    
    # The SOQL query to get Asset data with Account Name instead of AccountId
    soql_query = """SELECT 
    Account.Name,
    Name, 
    Notes__c,
    AccountId
FROM Asset 
WHERE Account.Name != null
LIMIT 100"""
    
    print("=" * 70)
    print("SALESFORCE SOQL QUERY TEST")
    print("=" * 70)
    print("\nTo get Asset data with Account Names instead of AccountId references,")
    print("use this SOQL query in your Salesforce Report Builder:\n")
    
    print("QUERY:")
    print("-" * 50)
    print(soql_query)
    print("-" * 50)
    
    print("\nEXPLANATION:")
    print("- Account.Name: Gets the readable account name instead of the ID")
    print("- Name: Asset name")
    print("- Notes__c: Custom notes field")
    print("- AccountId: Still included for reference if needed")
    print("- WHERE Account.Name != null: Filters out assets without account names")
    print("- LIMIT 100: Limits results for testing\n")
    
    print("INSTRUCTIONS:")
    print("1. Open your SalesForce Report Pull application")
    print("2. Go to the Source Data tab")
    print("3. Select 'Custom Report Builder' for Salesforce")
    print("4. Paste the above query")
    print("5. Execute to see results in the data grid")
    print("=" * 70)
    
    return soql_query

if __name__ == "__main__":
    # Display the query for manual execution
    query = create_test_query()
    
    print("\nALTERNATIVE - Direct execution:")
    print("If you prefer to run this query programmatically:")
    print("1. Ensure dependencies are installed: pip install -r requirements.txt")
    print("2. Run: python launch.py") 
    print("3. Use the Custom Report Builder with the above query")
    print("\nThe query will return Account Names instead of AccountId numbers.")