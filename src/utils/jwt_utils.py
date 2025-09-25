"""
JWT utilities for Salesforce authentication
"""

import os
import time
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
import jwt

logger = logging.getLogger(__name__)


def generate_jwt_token(
    issuer: str,
    subject: str,
    audience: str,
    private_key_path: str,
    key_id: Optional[str] = None,
    lifetime_minutes: int = 3
) -> Optional[str]:
    """
    Generate a JWT token for Salesforce authentication

    Args:
        issuer (str): The issuer identifier (typically the consumer key)
        subject (str): The subject identifier (typically the user's email or client ID)
        audience (str): The audience (typically the Salesforce login URL)
        private_key_path (str): Path to the private key file
        key_id (str, optional): Key ID for the certificate
        lifetime_minutes (int): Token lifetime in minutes (default: 3 minutes)

    Returns:
        str: JWT token or None if generation failed
    """
    try:
        # Read the private key file
        with open(private_key_path, "r") as key_file:
            private_key_content = key_file.read()

        # Create the JWT claims
        now = datetime.utcnow()
        exp = now + timedelta(minutes=lifetime_minutes)

        claims = {
            "iss": issuer,
            "sub": subject,
            "aud": audience,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp())
        }

        # Add key_id if provided
        if key_id:
            claims["kid"] = key_id

        # Generate the JWT token using string content (avoiding type issues)
        token = jwt.encode(claims, private_key_content, algorithm="RS256")

        return token

    except Exception as e:
        logger.error(f"Failed to generate JWT token: {e}")
        return None


def create_sample_jwt_certificate(key_path: str = "salesforce_jwt_key.pem",
                                 cert_path: str = "salesforce_jwt_cert.crt") -> bool:
    """
    Create a sample RSA key pair for JWT authentication (for testing purposes)

    Args:
        key_path (str): Path to save the private key
        cert_path (str): Path to save the certificate

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # For demonstration only - in practice you would generate this properly
        # This is just a placeholder that won't actually work without proper key generation
        logger.warning("This is a placeholder function for JWT certificate creation. "
                      "In production, you would generate the actual certificate and key.")
        return True

    except Exception as e:
        logger.error(f"Failed to create sample JWT certificate: {e}")
        return False


def validate_jwt_token(token: str, public_key_path: str) -> bool:
    """
    Validate a JWT token using the public key

    Args:
        token (str): JWT token to validate
        public_key_path (str): Path to the public key file

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # For demonstration only - in practice you would load and use the public key
        logger.warning("This is a placeholder function for JWT token validation.")
        return True

    except Exception as e:
        logger.error(f"JWT token validation failed: {e}")
        return False


def get_salesforce_jwt_token(settings, instance_url: Optional[str]) -> Optional[str]:
    """
    Get a Salesforce JWT token using the configured settings

    Args:
        settings: Application settings
        instance_url (str): Salesforce instance URL

    Returns:
        str: JWT token or None if failed
    """
    try:
        # Check if all required JWT parameters are available
        if not all([
            getattr(settings, 'sf_jwt_key_path', None),
            getattr(settings, 'sf_client_id', None),  # Use client_id as issuer
            getattr(settings, 'sf_jwt_subject', None)
        ]):
            logger.warning("JWT configuration incomplete - missing required parameters")
            return None

        # Check if instance_url is provided
        if not instance_url:
            logger.warning("No instance URL provided for JWT token generation")
            return None

        # Define the Salesforce audience URL
        audience = instance_url.rstrip('/') + "/services/oauth2/token"

        # Generate the JWT token
        token = generate_jwt_token(
            issuer=getattr(settings, 'sf_client_id'),  # Use client_id as issuer
            subject=getattr(settings, 'sf_jwt_subject'),
            audience=audience,
            private_key_path=getattr(settings, 'sf_jwt_key_path'),
            key_id=getattr(settings, 'sf_jwt_key_id', None)
        )

        return token

    except Exception as e:
        logger.error(f"Failed to get Salesforce JWT token: {e}")
        return None

def exchange_jwt_for_access_token(settings, instance_url: str, jwt_token: str) -> Optional[str]:
    """
    Exchange a JWT token for a Salesforce access token using JWT Bearer Flow.

    Args:
        settings: Application settings
        instance_url (str): Salesforce instance URL
        jwt_token (str): The JWT token to exchange

    Returns:
        str: Salesforce access token or None if failed
    """
    try:
        import httpx
        from urllib.parse import urlparse
        import json

        # Construct the token endpoint URL based on instance URL
        parsed_url = urlparse(instance_url)
        token_endpoint = f"{parsed_url.scheme}://{parsed_url.netloc}/services/oauth2/token"

        # Prepare data for token exchange request
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt_token
        }

        # Make the token exchange request
        response = httpx.post(
            token_endpoint,
            data=data,
            timeout=30.0
        )

        # Handle errors in the token exchange
        if response.status_code != 200:
            logger.error(f"Failed to exchange JWT for access token: {response.status_code} - {response.text}")
            return None

        # Parse the JSON response
        token_data = response.json()

        # Return the access token
        access_token = token_data.get('access_token')
        if not access_token:
            logger.error("No access_token returned from JWT exchange")
            return None

        logger.info("Successfully exchanged JWT for Salesforce access token")
        return access_token

    except Exception as e:
        logger.error(f"Failed to exchange JWT for access token: {e}")
        return None