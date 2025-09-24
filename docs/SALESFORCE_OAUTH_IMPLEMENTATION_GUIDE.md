# Salesforce OAuth 2.0 + PKCE Implementation Guide

## Overview

This guide documents the complete implementation of OAuth 2.0 Authorization Code Flow with PKCE (Proof Key for Code Exchange) for Salesforce authentication. This approach provides secure, browser-based authentication without requiring client secrets.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Salesforce Connected App Setup](#salesforce-connected-app-setup)
3. [Core Dependencies](#core-dependencies)
4. [Implementation Architecture](#implementation-architecture)
5. [Key Components](#key-components)
6. [Critical Implementation Details](#critical-implementation-details)
7. [Common Issues and Solutions](#common-issues-and-solutions)
8. [Testing and Debugging](#testing-and-debugging)
9. [Security Considerations](#security-considerations)

## Prerequisites

### Python Requirements
- Python 3.8+
- PyQt6 for desktop GUI
- Required packages (see [Core Dependencies](#core-dependencies))

### Salesforce Requirements
- Salesforce Developer/Production org
- System Administrator access to create Connected Apps
- Custom domain configured (recommended)

## Salesforce Connected App Setup

### 1. Create Connected App
1. Setup → App Manager → New Connected App
2. **Basic Information:**
   - Connected App Name: `YourAppName`
   - API Name: `YourAppName`
   - Contact Email: `your-email@domain.com`

### 2. OAuth Settings
```
☑ Enable OAuth Settings
☑ Enable for Device Flow (optional)

Callback URLs:
http://localhost:8080/callback
http://localhost:8081/callback
http://localhost:8082/callback
(Add multiple ports for fallback)

Selected OAuth Scopes:
- Full access (full)
- Perform requests at any time (refresh_token, offline_access)
- Access unique user identifiers (openid)

☑ Require Proof Key for Code Exchange (PKCE) Extension for Supported Authorization Flows
☐ Require Secret for Web Server Flow (Leave UNCHECKED for PKCE)
☐ Require Secret for Refresh Token Flow (Leave UNCHECKED)
```

### 3. Important Settings
- **PKCE Required**: Must be enabled
- **Client Secret**: Not required for PKCE flow
- **IP Relaxation**: Set to "Relax IP restrictions" for development
- **Refresh Token Policy**: Set to "Refresh token is valid until revoked"

### 4. Get Consumer Key
After saving, copy the **Consumer Key** (Client ID) - this is the only credential needed for PKCE flow.

## Core Dependencies

### requirements.txt
```txt
# Core Framework
PyQt6>=6.5.0
polars>=0.20.0
pydantic>=2.0.0

# Salesforce Integration
simple-salesforce>=1.12.0
authlib>=1.3.0
requests>=2.31.0

# Security & Authentication
keyring>=24.0.0
cryptography>=41.0.0

# UI Enhancements
qtawesome>=1.2.0
qdarkstyle>=3.2.0

# Data Processing
openpyxl>=3.1.0
pandas>=2.0.0
```

## Implementation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    OAuth 2.0 + PKCE Flow                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Generate PKCE Parameters (code_verifier, code_challenge) │
│ 2. Create Authorization URL with PKCE                      │
│ 3. Open System Browser → Salesforce Login                  │
│ 4. User Authenticates                                      │
│ 5. Salesforce Redirects → Local Callback Server            │
│ 6. Extract Authorization Code                              │
│ 7. Exchange Code + PKCE Verifier → Access Token            │
│ 8. Create Salesforce API Client                           │
│ 9. Test Connection & Load Data                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Authentication Manager (`auth_manager.py`)

```python
from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7636 import create_s256_code_challenge
import secrets
import webbrowser
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SalesforceAuthManager:
    CONSUMER_KEY = "your_consumer_key_here"
    
    def __init__(self, instance_url: str = "https://login.salesforce.com"):
        self.instance_url = instance_url
        self.authorization_endpoint = f"{instance_url}/services/oauth2/authorize"
        
        # Critical: Use standard login domain for token exchange
        if "test.salesforce.com" in instance_url:
            self.token_endpoint = "https://test.salesforce.com/services/oauth2/token"
        else:
            self.token_endpoint = "https://login.salesforce.com/services/oauth2/token"
    
    def authenticate_with_browser(self) -> bool:
        # Generate PKCE parameters
        self.code_verifier = secrets.token_urlsafe(96)
        self.code_challenge = create_s256_code_challenge(self.code_verifier)
        
        # Create OAuth2 session
        oauth = OAuth2Session(
            client_id=self.CONSUMER_KEY,
            redirect_uri=self.redirect_uri
        )
        
        # Critical: PKCE parameters go in authorization URL, not session
        authorization_url, state = oauth.create_authorization_url(
            self.authorization_endpoint,
            state=secrets.token_urlsafe(32),
            code_challenge=self.code_challenge,
            code_challenge_method='S256'
        )
        
        # Start callback server and open browser
        # ... (see full implementation)
```

### 2. Callback Handler

```python
class OAuth2CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Store callback URL for processing
        self.server.callback_url = self.path
        
        # Parse parameters
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            # Success - send HTML response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(success_html.encode())
        elif 'error' in query_params:
            # Handle OAuth error
            # ... (see full implementation)
```

### 3. Token Exchange

```python
def _exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
    # Critical: Explicit parameter handling for PKCE
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': self.CONSUMER_KEY,
        'code': authorization_code,
        'redirect_uri': self.redirect_uri,
        'code_verifier': self.code_verifier  # PKCE verifier
    }
    
    # Make request to token endpoint
    response = requests.post(
        self.token_endpoint,  # Standard domain, not custom
        data=token_data,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Token exchange failed: {response.text}")
```

### 4. Salesforce API Integration

```python
from simple_salesforce import Salesforce

def _create_salesforce_client(self) -> bool:
    access_token = self.auth_manager.get_access_token()
    instance_url = self.auth_manager.get_instance_url()
    
    self.sf_client = Salesforce(
        instance_url=instance_url,
        session_id=access_token,
        version='58.0'
    )
    
    # Test connection
    org_info = self.sf_client.query("SELECT Id, Name FROM Organization LIMIT 1")
    return org_info['totalSize'] > 0
```

## Critical Implementation Details

### 1. **Token Endpoint Domain**
```python
# ❌ WRONG - Using custom domain for token exchange
self.token_endpoint = f"{self.instance_url}/services/oauth2/token"

# ✅ CORRECT - Using standard domain for token exchange
if "test.salesforce.com" in self.instance_url:
    self.token_endpoint = "https://test.salesforce.com/services/oauth2/token"
else:
    self.token_endpoint = "https://login.salesforce.com/services/oauth2/token"
```

### 2. **PKCE Parameter Placement**
```python
# ❌ WRONG - PKCE in OAuth2Session constructor
oauth = OAuth2Session(
    client_id=self.CONSUMER_KEY,
    code_challenge=self.code_challenge,  # Wrong place
    code_challenge_method='S256'         # Wrong place
)

# ✅ CORRECT - PKCE in authorization URL
oauth = OAuth2Session(client_id=self.CONSUMER_KEY)
authorization_url, state = oauth.create_authorization_url(
    self.authorization_endpoint,
    code_challenge=self.code_challenge,      # Correct place
    code_challenge_method='S256'             # Correct place
)
```

### 3. **PKCE Generation (RFC 7636 Compliant)**
```python
import secrets
from authlib.oauth2.rfc7636 import create_s256_code_challenge

# Generate verifier (43-128 characters, URL-safe)
code_verifier = secrets.token_urlsafe(96)  # 128 chars

# Generate challenge (Base64URL-encode SHA256 hash)
code_challenge = create_s256_code_challenge(code_verifier)
```

### 4. **Secure Token Storage**
```python
import keyring

def _save_tokens(self):
    try:
        # Primary: Secure keyring storage
        keyring.set_password("SalesforceApp", "access_token", self.access_token)
        keyring.set_password("SalesforceApp", "refresh_token", self.refresh_token)
    except Exception:
        # Fallback: File storage with restricted permissions
        token_file = Path.home() / '.config' / 'SalesforceApp' / 'tokens.txt'
        token_file.write_text(f"{access_token}\n{refresh_token}")
        token_file.chmod(0o600)  # Owner read/write only
```

## Common Issues and Solutions

### Issue 1: "Missing required code challenge"
**Cause**: PKCE parameters in wrong location
**Solution**: Move `code_challenge` and `code_challenge_method` from OAuth2Session constructor to `create_authorization_url()` method

### Issue 2: "Invalid client credentials"
**Cause**: Using custom domain for token exchange
**Solution**: Use standard `login.salesforce.com` or `test.salesforce.com` for token endpoint

### Issue 3: Application freezes after browser authentication
**Cause**: Blocking operations on main UI thread
**Solution**: Use QThread workers for OAuth operations

### Issue 4: ContentDoor blank page
**Cause**: Embedded browser compatibility issues
**Solution**: Use system browser with `webbrowser.open()`

### Issue 5: Port conflicts for callback server
**Cause**: Port 8080 already in use
**Solution**: Implement port scanning with fallback ports

```python
def _find_available_port(self, start_port: int = 8080) -> int:
    for port in range(start_port, start_port + 10):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port
```

## Testing and Debugging

### 1. **Comprehensive Logging**
```python
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Use prefixed log messages for flow tracking
logger.info("[STEP 1] ✓ PKCE parameters generated")
logger.info("[STEP 2] ✓ Authorization URL created")
logger.info("[STEP 3] ✓ Browser opened")
```

### 2. **Test Scripts**
Create verification scripts for each component:

```python
# test_pkce.py - Verify PKCE generation
def test_pkce_generation():
    verifier = secrets.token_urlsafe(96)
    challenge = create_s256_code_challenge(verifier)
    assert len(verifier) >= 43
    assert len(challenge) == 43
    print("✓ PKCE generation working")

# test_endpoints.py - Verify endpoint logic
def test_token_endpoints():
    test_cases = [
        ("https://company.my.salesforce.com", "https://login.salesforce.com/services/oauth2/token"),
        ("https://test.salesforce.com", "https://test.salesforce.com/services/oauth2/token")
    ]
    for instance, expected_token in test_cases:
        # Test endpoint logic
        assert get_token_endpoint(instance) == expected_token
    print("✓ Token endpoint logic working")
```

### 3. **OAuth Flow Verification**
Monitor the complete flow:

1. **Authorization URL**: Verify it contains all required parameters
2. **Callback**: Confirm authorization code is received
3. **Token Exchange**: Check HTTP 200 response with access_token
4. **API Connection**: Verify simple-salesforce client works

## Security Considerations

### 1. **PKCE Benefits**
- No client secret required
- Protection against authorization code interception
- Suitable for public clients (desktop apps)

### 2. **Token Security**
- Store tokens securely (keyring preferred)
- Implement token refresh logic
- Clear tokens on logout

### 3. **Network Security**
- Use HTTPS for all Salesforce communication
- Localhost callback server only for OAuth
- Validate callback parameters

### 4. **Error Handling**
- Don't log sensitive data (tokens, codes)
- Provide user-friendly error messages
- Implement retry logic for network issues

## Production Considerations

### 1. **Deployment**
- Package with PyInstaller/cx_Freeze
- Include all dependencies
- Test on target platforms

### 2. **User Experience**
- Clear authentication instructions
- Progress indicators during OAuth flow
- Graceful error recovery

### 3. **Maintenance**
- Monitor Salesforce API version updates
- Keep OAuth libraries updated
- Regular security audits

## Success Indicators

When implementation is working correctly:

✅ Browser opens to Salesforce login  
✅ User can authenticate successfully  
✅ Application receives authorization code  
✅ Token exchange returns access_token  
✅ Salesforce API client connects  
✅ Organization query succeeds  
✅ Reports/data loading works  

## Conclusion

This OAuth 2.0 + PKCE implementation provides secure, reliable Salesforce authentication for desktop applications. The key success factors are:

1. **Correct PKCE parameter placement**
2. **Proper token endpoint domain usage**
3. **Comprehensive error handling**
4. **Secure token storage**
5. **Thorough testing and debugging**

Following this guide ensures a robust, production-ready Salesforce integration that follows modern security best practices.