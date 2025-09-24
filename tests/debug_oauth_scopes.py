#!/usr/bin/env python3
"""
Debug script to help determine the correct OAuth scopes for your Connected App
"""
import os
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
    print("Loaded environment variables from .env file")
except ImportError:
    print("python-dotenv not available, using system environment variables only")

def test_different_scopes():
    """Test different OAuth scope combinations"""
    
    consumer_key = os.getenv('SF_CONSUMER_KEY')
    instance_url = os.getenv('SF_INSTANCE_URL', 'https://company.my.salesforce.com')
    
    if not consumer_key:
        print("❌ SF_CONSUMER_KEY not found in environment variables")
        return
    
    print(f"Testing OAuth scopes for Connected App: {consumer_key[:20]}...")
    print(f"Instance URL: {instance_url}")
    print()
    
    # Different scope combinations to test
    scope_combinations = [
        ('api', 'API Only (RECOMMENDED)'),
        ('api refresh_token', 'API + Refresh Token (may cause scope error)'),
        ('refresh_token', 'Refresh Token Only'),
        ('full', 'Full Access'),
        ('web', 'Web Access'),
        ('id', 'ID Only'),
    ]
    
    print("🔍 Testing different OAuth scope combinations...")
    print("=" * 60)
    
    for i, (scopes, description) in enumerate(scope_combinations, 1):
        print(f"{i}. {description}")
        print(f"   Scopes: {scopes}")
        
        # Generate the authorization URL
        auth_url = f"{instance_url}/services/oauth2/authorize"
        params = {
            'response_type': 'code',
            'client_id': consumer_key,
            'redirect_uri': 'http://localhost:8080/callback',
            'scope': scopes,
            'state': f'test_scope_{i}'
        }
        
        # Build URL
        param_string = '&'.join([f"{k}={v.replace(' ', '+')}" for k, v in params.items()])
        full_url = f"{auth_url}?{param_string}"
        
        print(f"   URL: {full_url}")
        print()
        
        # Ask user if they want to test this combination
        response = input(f"Test scope combination {i}? (y/n/q): ").lower()
        if response == 'q':
            break
        elif response == 'y':
            print(f"Opening browser to test: {description}")
            webbrowser.open(full_url)
            print("Check the browser - does it show an error or the login page?")
            result = input("Result (success/error): ").lower()
            if result == 'success':
                print(f"✅ {description} - WORKS!")
                return scopes
            else:
                print(f"❌ {description} - Failed")
            print()
    
    print("=" * 60)
    print("💡 TROUBLESHOOTING TIPS:")
    print("1. Go to Setup → App Manager → Your Connected App → Edit")
    print("2. Check the 'Selected OAuth Scopes' section")
    print("3. Make sure these scopes are included:")
    print("   - Access and manage your data (api)")
    print("   - Perform requests on your behalf at any time (refresh_token)")
    print("4. If you're still getting errors, try removing all scopes except 'api'")
    print("5. Contact your Salesforce admin if scope restrictions are in place")

if __name__ == "__main__":
    print("=" * 60)
    print("OAuth Scope Debugging Tool")
    print("=" * 60)
    
    test_different_scopes()