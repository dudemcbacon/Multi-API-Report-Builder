#!/usr/bin/env python3
"""
Test script for Salesforce JWT authentication
This script validates that JWT authentication is working correctly
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.async_jwt_salesforce_api import AsyncJWTSalesforceAPI


async def test_jwt_connection():
    """Test Salesforce JWT authentication and connection"""

    # Load environment variables
    load_dotenv()

    print("=" * 60)
    print("Salesforce JWT Authentication Test")
    print("=" * 60)

    # Check environment variables
    print("\n1. Checking environment variables...")
    consumer_key = os.getenv('SF_CLIENT_ID')
    jwt_subject = os.getenv('SF_JWT_SUBJECT')
    jwt_key_path = os.getenv('SF_JWT_KEY_PATH', './salesforce_private.key')
    jwt_key_id = os.getenv('SF_JWT_KEY_ID')

    print(f"   Consumer Key: {'[OK] Present' if consumer_key else '[ERROR] Missing'}")
    print(f"   JWT Subject: {jwt_subject if jwt_subject else '[ERROR] Missing'}")
    print(f"   JWT Key Path: {jwt_key_path}")
    print(f"   JWT Key ID: {'[OK] Present' if jwt_key_id else '[INFO] Missing (optional)'}")

    # Check private key file
    print("\n2. Checking private key file...")
    key_exists = Path(jwt_key_path).exists()
    print(f"   Private key at {jwt_key_path}: {'[OK] Found' if key_exists else '[ERROR] Not found'}")

    if not all([consumer_key, jwt_subject, key_exists]):
        print("\n[ERROR] Configuration incomplete. Please check your .env file and private key.")
        return False

    # Initialize API
    print("\n3. Initializing Salesforce JWT API...")
    api = AsyncJWTSalesforceAPI(
        instance_url="https://login.salesforce.com",
        consumer_key=consumer_key,
        jwt_subject=jwt_subject,
        jwt_key_path=jwt_key_path,
        jwt_key_id=jwt_key_id,
        sandbox=False,  # Production environment
        verbose_logging=True
    )

    try:
        # Test connection
        print("\n4. Testing JWT authentication...")
        result = await api.test_connection()

        if result.get('success'):
            print(f"\n[SUCCESS] Connected to Salesforce!")
            print(f"   Organization: {result.get('organization', 'Unknown')}")
            print(f"   Instance URL: {result.get('instance_url', 'Unknown')}")
            print(f"   User: {result.get('user', jwt_subject)}")
            return True
        else:
            print(f"\n[ERROR] FAILED to connect to Salesforce")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            print(f"   Details: {result.get('details', 'No details available')}")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception during connection test: {e}")
        return False

    finally:
        # Clean up
        await api.close()
        print("\n5. Connection closed")


async def test_jwt_token_generation():
    """Test just the JWT token generation"""
    from src.utils.jwt_utils import generate_jwt_token

    load_dotenv()

    print("\n" + "=" * 60)
    print("Testing JWT Token Generation Only")
    print("=" * 60)

    consumer_key = os.getenv('SF_CLIENT_ID')
    jwt_subject = os.getenv('SF_JWT_SUBJECT')
    jwt_key_path = os.getenv('SF_JWT_KEY_PATH', './salesforce_private.key')
    jwt_key_id = os.getenv('SF_JWT_KEY_ID')

    print("\nGenerating JWT token...")
    token = generate_jwt_token(
        issuer=consumer_key,
        subject=jwt_subject,
        audience="https://login.salesforce.com",
        private_key_path=jwt_key_path,
        key_id=jwt_key_id
    )

    if token:
        print(f"[OK] JWT token generated successfully")
        print(f"   Token length: {len(token)} characters")
        print(f"   Token preview: {token[:50]}...")
        return True
    else:
        print("[ERROR] Failed to generate JWT token")
        return False


def main():
    """Run all tests"""
    print("Starting Salesforce JWT Authentication Tests\n")

    # Test JWT token generation first
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Test token generation
        token_result = loop.run_until_complete(test_jwt_token_generation())

        if token_result:
            # Test full connection
            connection_result = loop.run_until_complete(test_jwt_connection())

            print("\n" + "=" * 60)
            if connection_result:
                print("[SUCCESS] All tests passed! Salesforce JWT authentication is working.")
            else:
                print("[ERROR] Connection test failed. Check the error messages above.")
            print("=" * 60)
        else:
            print("\n[ERROR] JWT token generation failed. Check your private key and configuration.")

    finally:
        loop.close()


if __name__ == "__main__":
    main()