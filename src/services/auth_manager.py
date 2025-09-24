"""
Modern Salesforce OAuth 2.0 Authentication Manager using Authlib
Handles OAuth 2.0 Authorization Code Flow with PKCE for secure authentication
"""
import time
import secrets
import webbrowser
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any
import logging
import keyring
from pathlib import Path
from datetime import datetime, timedelta
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except ImportError:
    pass  # dotenv not available, use system environment variables

from authlib.integrations.requests_client import OAuth2Session
from authlib.oauth2.rfc7636 import create_s256_code_challenge

logger = logging.getLogger(__name__)

class OAuth2CallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth2 callback"""
    
    def do_GET(self):
        """Handle GET request to callback URL"""
        logger.info("[CALLBACK] " + "=" * 50)
        logger.info("[CALLBACK] OAuth callback received!")
        logger.info(f"[CALLBACK] Path: {self.path}")
        logger.info(f"[CALLBACK] Thread: {threading.current_thread().name}")
        logger.info("[CALLBACK] " + "=" * 50)
        
        try:
            # Store the full callback URL for processing
            logger.info("[CALLBACK] Storing callback URL in server object...")
            self.server.callback_url = self.path
            logger.info(f"[CALLBACK] SUCCESS Stored: {self.server.callback_url}")
            
            # Signal that callback was received
            if hasattr(self.server, 'callback_received'):
                self.server.callback_received.set()
                logger.info("[CALLBACK] SUCCESS Callback event signaled")
            
            # Parse the callback URL
            logger.info("[CALLBACK] Parsing callback URL...")
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            logger.info(f"[CALLBACK] Parameters found: {list(query_params.keys())}")
            
            if 'code' in query_params:
                # Success - send success response
                logger.info("[CALLBACK] SUCCESS Authorization code found in parameters")
                logger.info(f"[CALLBACK] Code length: {len(query_params['code'][0])}")
                
                logger.info("[CALLBACK] Sending HTTP 200 response...")
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                logger.info("[CALLBACK] SUCCESS Response headers sent")
                
                success_html = """
                <html>
                <head><title>Authentication Successful</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: green;">SUCCESS Authentication Successful!</h2>
                    <p>You can now close this window and return to the application.</p>
                    <script>
                        setTimeout(function(){
                            window.close();
                        }, 3000);
                    </script>
                </body>
                </html>
                """
                logger.info("[CALLBACK] Writing success HTML to response...")
                self.wfile.write(success_html.encode())
                logger.info("[CALLBACK] SUCCESS Success HTML written")
                logger.info("[CALLBACK] SUCCESS Callback handler completed successfully")
                
            elif 'error' in query_params:
                # Error occurred
                error = query_params['error'][0]
                error_description = query_params.get('error_description', ['Unknown error'])[0]
                logger.error(f"[CALLBACK] ERROR OAuth error: {error} - {error_description}")
                
                logger.info("[CALLBACK] Sending HTTP 400 response...")
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: red;">ERROR Authentication Failed</h2>
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                    <p>Please close this window and try again.</p>
                </body>
                </html>
                """
                logger.info("[CALLBACK] Writing error HTML to response...")
                self.wfile.write(error_html.encode())
                logger.info("[CALLBACK] SUCCESS Error HTML written")
                
        except Exception as e:
            logger.error(f"[CALLBACK] ERROR Exception handling OAuth callback: {e}")
            logger.error(f"[CALLBACK] Exception type: {type(e).__name__}")
            logger.error("[CALLBACK] Stack trace:", exc_info=True)
            
            logger.info("[CALLBACK] Sending HTTP 500 response...")
            self.send_response(500)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            error_html = """
            <html>
            <head><title>Authentication Error</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2 style="color: red;">ERROR Authentication Error</h2>
                <p>An error occurred during authentication. Please close this window and try again.</p>
            </body>
            </html>
            """
            logger.info("[CALLBACK] Writing exception HTML to response...")
            self.wfile.write(error_html.encode())
            logger.info("[CALLBACK] SUCCESS Exception HTML written")
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass

class SalesforceAuthManager:
    """Modern Salesforce OAuth 2.0 Authentication Manager using Authlib"""
    
    # Secure credential management - use environment variables
    CONSUMER_KEY = os.getenv('SF_CONSUMER_KEY')
    
    def __init__(self, instance_url: str = "https://login.salesforce.com", consumer_secret: Optional[str] = None):
        """
        Initialize Salesforce OAuth Auth Manager
        
        Args:
            instance_url: Salesforce instance URL (login.salesforce.com or test.salesforce.com)
            consumer_secret: Consumer secret (not needed for PKCE flow)
        """
        self.instance_url = instance_url
        self.consumer_secret = consumer_secret or os.getenv('SF_CONSUMER_SECRET')
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.instance_url_oauth: Optional[str] = None
        self.token_expires_at: Optional[float] = None
        
        # OAuth endpoints
        self.authorization_endpoint = f"{self.instance_url}/services/oauth2/authorize"
        
        # Token endpoint: Critical - Use standard login domain for token exchange
        # Custom domains often require token exchange through standard endpoints
        if "test.salesforce.com" in self.instance_url:
            self.token_endpoint = "https://test.salesforce.com/services/oauth2/token"
        else:
            self.token_endpoint = "https://login.salesforce.com/services/oauth2/token"
        
        # PKCE parameters
        self.code_verifier: Optional[str] = None
        self.code_challenge: Optional[str] = None
        
        # Callback server settings
        self.callback_port: int = 8080
        self.redirect_uri: str = f"http://localhost:{self.callback_port}/callback"
        
        # Service name for keyring storage
        self.keyring_service = "SalesforceReportPull"
        
        # Try to load stored tokens
        self._load_stored_tokens()
    
    def _find_available_port(self, start_port: int = 8080) -> int:
        """Find an available port for the callback server"""
        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return start_port  # Fallback to original port
    
    def _load_stored_tokens(self):
        """Load stored OAuth tokens from keyring or file"""
        try:
            # Try to get tokens from keyring
            stored_access_token = keyring.get_password(self.keyring_service, "access_token")
            stored_refresh_token = keyring.get_password(self.keyring_service, "refresh_token")
            stored_instance_url = keyring.get_password(self.keyring_service, "instance_url")
            stored_expires_at = keyring.get_password(self.keyring_service, "token_expires_at")
            
            if stored_access_token:
                self.access_token = stored_access_token
                logger.info("Loaded access token from secure storage")
            
            if stored_refresh_token:
                self.refresh_token = stored_refresh_token
                logger.info("Loaded refresh token from secure storage")
                
            if stored_instance_url:
                self.instance_url_oauth = stored_instance_url
                logger.info("Loaded instance URL from secure storage")
                
            if stored_expires_at:
                try:
                    self.token_expires_at = float(stored_expires_at)
                    logger.info(f"Loaded token expiration time from secure storage: {datetime.fromtimestamp(self.token_expires_at)}")
                    
                    # Clear expired tokens immediately to prevent hanging
                    if not self.is_token_valid():
                        logger.warning("Stored token is expired, clearing credentials to force fresh authentication")
                        self.clear_credentials()
                        
                except ValueError:
                    logger.warning("Invalid token expiration time in storage")
                    self.token_expires_at = None
                
        except Exception as e:
            logger.warning(f"Could not load stored tokens: {e}")
            # Try file-based fallback
            try:
                config_dir = Path.home() / '.config' / 'SalesforceReportPull'
                config_dir.mkdir(parents=True, exist_ok=True)
                
                token_file = config_dir / 'oauth_tokens.txt'
                if token_file.exists():
                    tokens = token_file.read_text().strip().split('\n')
                    if len(tokens) >= 2:
                        self.access_token = tokens[0]
                        self.refresh_token = tokens[1]
                        if len(tokens) >= 3:
                            self.instance_url_oauth = tokens[2]
                        if len(tokens) >= 4:
                            try:
                                self.token_expires_at = float(tokens[3])
                                logger.info(f"Loaded token expiration time from file: {datetime.fromtimestamp(self.token_expires_at)}")
                            except ValueError:
                                logger.warning("Invalid token expiration time in file")
                                self.token_expires_at = None
                        logger.info("Loaded tokens from file storage")
                    
            except Exception as e2:
                logger.warning(f"Could not load tokens from file: {e2}")
    
    def _save_tokens(self):
        """Save OAuth tokens securely using keyring with file fallback"""
        try:
            if self.access_token:
                keyring.set_password(self.keyring_service, "access_token", self.access_token)
            if self.refresh_token:
                keyring.set_password(self.keyring_service, "refresh_token", self.refresh_token)
            if self.instance_url_oauth:
                keyring.set_password(self.keyring_service, "instance_url", self.instance_url_oauth)
            if self.token_expires_at:
                keyring.set_password(self.keyring_service, "token_expires_at", str(self.token_expires_at))
            logger.info("OAuth tokens saved to secure storage")
        except Exception as e:
            logger.warning(f"Could not save to keyring: {e}")
            # File-based fallback
            try:
                config_dir = Path.home() / '.config' / 'SalesforceReportPull'
                config_dir.mkdir(parents=True, exist_ok=True)
                
                token_file = config_dir / 'oauth_tokens.txt'
                tokens_content = f"{self.access_token or ''}\n{self.refresh_token or ''}\n{self.instance_url_oauth or ''}\n{self.token_expires_at or ''}"
                token_file.write_text(tokens_content)
                token_file.chmod(0o600)  # Read only for owner
                
                logger.info("OAuth tokens saved to file storage")
            except Exception as e2:
                logger.error(f"Could not save tokens: {e2}")
    
    def authenticate_with_browser(self) -> bool:
        """
        Authenticate using system browser OAuth flow with Authlib
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        logger.info("=" * 60)
        logger.info("STARTING BROWSER AUTHENTICATION FLOW")
        logger.info("=" * 60)
        logger.info(f"Current thread: {threading.current_thread().name}")
        logger.info(f"Process ID: {os.getpid()}")
        logger.info(f"Consumer Key: {'Present' if self.CONSUMER_KEY else 'Missing'}")
        logger.info(f"Consumer Secret: {'Present' if self.consumer_secret else 'Missing'}")
        if self.CONSUMER_KEY:
            logger.info(f"Consumer Key (first 20 chars): {self.CONSUMER_KEY[:20]}...")
        if self.consumer_secret:
            logger.info(f"Consumer Secret (first 20 chars): {self.consumer_secret[:20]}...")
        
        # Validate required credentials before starting
        if not self.CONSUMER_KEY:
            logger.error("❌ Consumer Key is missing! Please check SF_CONSUMER_KEY environment variable.")
            return False
        
        # Consumer secret is optional for PKCE flow but recommended
        if not self.consumer_secret:
            logger.warning("⚠️ Consumer Secret is missing - using PKCE-only flow (may work but not recommended)")
        else:
            logger.info("✅ Consumer Secret available - using enhanced security flow")
        
        try:
            # Find available port for callback server
            logger.info("[STEP 1] Finding available port for callback server...")
            self.callback_port = self._find_available_port()
            self.redirect_uri = f"http://localhost:{self.callback_port}/callback"
            logger.info(f"[STEP 1] SUCCESS Using port {self.callback_port}, redirect URI: {self.redirect_uri}")
            
            # Generate PKCE parameters
            logger.info("[STEP 2] Generating PKCE parameters...")
            self.code_verifier = secrets.token_urlsafe(96)
            self.code_challenge = create_s256_code_challenge(self.code_verifier)
            logger.info(f"[STEP 2] SUCCESS Code verifier length: {len(self.code_verifier)}, challenge length: {len(self.code_challenge)}")
            logger.debug(f"[STEP 2] Code verifier (first 20 chars): {self.code_verifier[:20]}...")
            logger.debug(f"[STEP 2] Code challenge (first 20 chars): {self.code_challenge[:20]}...")
            
            # Create OAuth2 session
            logger.info("[STEP 3] Creating OAuth2 session...")
            oauth = OAuth2Session(
                client_id=self.CONSUMER_KEY,
                redirect_uri=self.redirect_uri
            )
            logger.info(f"[STEP 3] SUCCESS OAuth2Session created with client_id: {self.CONSUMER_KEY[:20]}...")
            
            # Generate authorization URL with PKCE parameters
            logger.info("[STEP 4] Generating authorization URL with PKCE...")
            logger.info(f"[STEP 4] Authorization endpoint: {self.authorization_endpoint}")
            
            state_value = secrets.token_urlsafe(32)
            logger.debug(f"[STEP 4] State value: {state_value}")
            
            authorization_url, state = oauth.create_authorization_url(
                self.authorization_endpoint,
                state=state_value,
                code_challenge=self.code_challenge,
                code_challenge_method='S256',
                scope='full'
            )
            
            logger.info(f"[STEP 4] SUCCESS Authorization URL generated")
            logger.debug(f"[STEP 4] Full URL: {authorization_url}")
            
            # Parse and log URL parameters
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(authorization_url)
            params = parse_qs(parsed.query)
            logger.debug("[STEP 4] URL Parameters:")
            for key, value in params.items():
                if key in ['code_challenge', 'state']:
                    logger.debug(f"  - {key}: {value[0][:20]}... (truncated)")
                else:
                    logger.debug(f"  - {key}: {value[0]}")
            
            # Start local callback server
            logger.info("[STEP 5] Creating HTTP callback server...")
            server = HTTPServer(('localhost', self.callback_port), OAuth2CallbackHandler)
            server.timeout = 300  # 5 minute timeout
            server.callback_url = None
            server.callback_received = threading.Event()
            logger.info(f"[STEP 5] SUCCESS HTTP server created on localhost:{self.callback_port} with 5 minute timeout")
            
            # Start server in separate thread
            logger.info("[STEP 6] Starting callback server in separate thread...")
            server_thread = threading.Thread(
                target=self._run_callback_server, 
                args=(server,), 
                daemon=True,
                name="OAuth-Callback-Server"
            )
            logger.info(f"[STEP 6] Thread created: {server_thread.name}, daemon: {server_thread.daemon}")
            server_thread.start()
            logger.info(f"[STEP 6] SUCCESS Thread started, is_alive: {server_thread.is_alive()}")
            
            # Open authorization URL in system browser
            logger.info("[STEP 7] Opening authorization URL in system browser...")
            browser_result = webbrowser.open(authorization_url)
            logger.info(f"[STEP 7] SUCCESS Browser open result: {browser_result}")
            if not browser_result:
                logger.error("[STEP 7] ERROR Failed to open browser")
                return False
            logger.info("[STEP 7] SUCCESS Browser opened successfully")
            
            # Wait for callback using threading.Event
            logger.info("[STEP 8] Waiting for OAuth callback...")
            logger.info(f"[STEP 8] Main thread: {threading.current_thread().name}")
            logger.info(f"[STEP 8] Server thread alive: {server_thread.is_alive()}")
            
            # Wait for callback with timeout
            callback_received = server.callback_received.wait(timeout=300)  # 5 minute timeout
            
            if not callback_received:
                logger.error("[STEP 8] ERROR Timeout waiting for OAuth callback")
                return False
            
            logger.info("[STEP 8] SUCCESS Callback received")
            logger.info(f"[STEP 8] Callback URL received: {server.callback_url is not None}")
            
            # Process callback
            logger.info("[STEP 9] Processing callback...")
            if server.callback_url:
                logger.info(f"[STEP 9] Callback URL received: {server.callback_url}")
                
                # Extract authorization code from callback
                parsed_url = urlparse(server.callback_url)
                query_params = parse_qs(parsed_url.query)
                
                logger.debug("[STEP 9] Callback parameters:")
                for key, value in query_params.items():
                    if key == 'code':
                        logger.debug(f"  - {key}: {value[0][:20]}... (truncated)")
                    else:
                        logger.debug(f"  - {key}: {value}")
                
                if 'code' in query_params:
                    authorization_code = query_params['code'][0]
                    logger.info(f"[STEP 9] SUCCESS Authorization code received (length: {len(authorization_code)})")
                    logger.debug(f"[STEP 9] Code (first 20 chars): {authorization_code[:20]}...")
                    
                    # Exchange code for token with explicit PKCE parameters
                    logger.info("[STEP 10] Starting token exchange...")
                    token = self._exchange_code_for_token(authorization_code)
                    logger.info(f"[STEP 10] Token exchange returned: {token is not None}")
                    
                    if not token:
                        logger.error("[STEP 10] ERROR Token exchange returned empty result")
                        return False
                    
                    logger.info("[STEP 11] Processing token response...")
                    logger.debug(f"[STEP 11] Token keys: {list(token.keys())}")
                    
                    # Store token information
                    self.access_token = token.get('access_token')
                    self.refresh_token = token.get('refresh_token')
                    self.instance_url_oauth = token.get('instance_url')
                    
                    logger.info(f"[STEP 11] SUCCESS Access token: {'Present' if self.access_token else 'Missing'}")
                    logger.info(f"[STEP 11] SUCCESS Refresh token: {'Present' if self.refresh_token else 'Missing'}")
                    logger.info(f"[STEP 11] SUCCESS Instance URL: {self.instance_url_oauth}")
                    
                    # Calculate token expiration
                    logger.info("[STEP 12] Calculating token expiration...")
                    expires_in = token.get('expires_in', 3600)
                    self.token_expires_at = time.time() + expires_in
                    expiry_time = datetime.fromtimestamp(self.token_expires_at).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"[STEP 12] SUCCESS Token expires in {expires_in} seconds (at {expiry_time})")
                    
                    # Save tokens securely
                    logger.info("[STEP 13] Saving tokens securely...")
                    self._save_tokens()
                    logger.info("[STEP 13] SUCCESS Tokens saved")
                    
                    logger.info("=" * 60)
                    logger.info(f"AUTHENTICATION SUCCESSFUL")
                    logger.info(f"Instance: {self.instance_url_oauth}")
                    logger.info("=" * 60)
                    return True
                    
                elif 'error' in query_params:
                    error = query_params['error'][0]
                    error_description = query_params.get('error_description', ['Unknown error'])[0]
                    logger.error(f"[STEP 9] ERROR OAuth error: {error} - {error_description}")
                    logger.error("=" * 60)
                    logger.error("AUTHENTICATION FAILED - OAuth Error")
                    logger.error("=" * 60)
                    return False
            
            logger.error("[STEP 9] ERROR No callback received or callback was invalid")
            logger.error(f"[STEP 9] Server callback_url: {server.callback_url}")
            logger.error(f"[STEP 9] Thread alive: {server_thread.is_alive()}")
            logger.error("=" * 60)
            logger.error("AUTHENTICATION FAILED - No Callback")
            logger.error("=" * 60)
            return False
            
        except Exception as e:
            logger.error(f"[ERROR] Browser authentication error: {e}")
            logger.error(f"[ERROR] Exception type: {type(e).__name__}")
            logger.error(f"[ERROR] Stack trace:", exc_info=True)
            logger.error("=" * 60)
            logger.error("AUTHENTICATION FAILED - Exception")
            logger.error("=" * 60)
            return False
        finally:
            logger.info("[CLEANUP] Closing server...")
            try:
                server.server_close()
                logger.info("[CLEANUP] SUCCESS Server closed")
            except Exception as e:
                logger.warning(f"[CLEANUP] Error closing server: {e}")
    
    def _exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token with explicit PKCE parameters
        
        Args:
            authorization_code: The authorization code received from callback
            
        Returns:
            Dict containing token information
            
        Raises:
            Exception: If token exchange fails
        """
        import requests
        
        logger.info("[TOKEN-EXCHANGE] " + "=" * 40)
        logger.info("[TOKEN-EXCHANGE] Starting token exchange")
        logger.info("[TOKEN-EXCHANGE] " + "=" * 40)
        
        try:
            logger.info(f"[TOKEN-EXCHANGE] Token endpoint: {self.token_endpoint}")
            logger.info(f"[TOKEN-EXCHANGE] Authorization code length: {len(authorization_code)}")
            logger.debug(f"[TOKEN-EXCHANGE] Code (first 20 chars): {authorization_code[:20]}...")
            
            # Prepare token request parameters
            logger.info("[TOKEN-EXCHANGE] Preparing token request parameters...")
            token_data = {
                'grant_type': 'authorization_code',
                'client_id': self.CONSUMER_KEY,
                'code': authorization_code,
                'redirect_uri': self.redirect_uri,
                'code_verifier': self.code_verifier
            }
            logger.info("[TOKEN-EXCHANGE] SUCCESS Base parameters prepared")
            
            # Add client_secret if available (some connected apps require it)
            if self.consumer_secret:
                token_data['client_secret'] = self.consumer_secret
                logger.info("[TOKEN-EXCHANGE] SUCCESS Including client_secret in token request")
            else:
                logger.info("[TOKEN-EXCHANGE] ℹ Using PKCE-only authentication (no client_secret)")
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            # Log request details (without sensitive data)
            logger.info("[TOKEN-EXCHANGE] Request parameters:")
            logger.info(f"  - grant_type: {token_data['grant_type']}")
            logger.info(f"  - client_id: {token_data['client_id'][:20]}...")
            logger.info(f"  - redirect_uri: {token_data['redirect_uri']}")
            logger.info(f"  - has_code_verifier: {bool(token_data['code_verifier'])}")
            logger.info(f"  - code_verifier length: {len(token_data['code_verifier'])}")
            logger.info(f"  - has_client_secret: {bool(token_data.get('client_secret'))}")
            
            # Make token request
            logger.info("[TOKEN-EXCHANGE] Sending POST request to token endpoint...")
            logger.info(f"[TOKEN-EXCHANGE] URL: {self.token_endpoint}")
            logger.info(f"[TOKEN-EXCHANGE] Headers: {headers}")
            logger.info("[TOKEN-EXCHANGE] Timeout: 30 seconds")
            
            start_time = time.time()
            response = requests.post(
                self.token_endpoint,
                data=token_data,
                headers=headers,
                timeout=30
            )
            elapsed_time = time.time() - start_time
            
            logger.info(f"[TOKEN-EXCHANGE] SUCCESS Response received in {elapsed_time:.2f} seconds")
            logger.info(f"[TOKEN-EXCHANGE] Response status: {response.status_code}")
            logger.info(f"[TOKEN-EXCHANGE] Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                logger.info("[TOKEN-EXCHANGE] SUCCESS HTTP 200 - Success!")
                logger.info("[TOKEN-EXCHANGE] Parsing JSON response...")
                
                token_result = response.json()
                logger.info("[TOKEN-EXCHANGE] SUCCESS JSON parsed successfully")
                logger.info(f"[TOKEN-EXCHANGE] Response keys: {list(token_result.keys())}")
                
                # Log token info (safely)
                if 'access_token' in token_result:
                    logger.info(f"[TOKEN-EXCHANGE] SUCCESS Access token present (length: {len(token_result['access_token'])})")
                if 'refresh_token' in token_result:
                    logger.info(f"[TOKEN-EXCHANGE] SUCCESS Refresh token present (length: {len(token_result['refresh_token'])})")
                if 'instance_url' in token_result:
                    logger.info(f"[TOKEN-EXCHANGE] SUCCESS Instance URL: {token_result['instance_url']}")
                if 'expires_in' in token_result:
                    logger.info(f"[TOKEN-EXCHANGE] SUCCESS Expires in: {token_result['expires_in']} seconds")
                
                logger.info("[TOKEN-EXCHANGE] " + "=" * 40)
                logger.info("[TOKEN-EXCHANGE] SUCCESS Token exchange completed successfully")
                logger.info("[TOKEN-EXCHANGE] " + "=" * 40)
                
                return token_result
            else:
                logger.error(f"[TOKEN-EXCHANGE] ERROR HTTP {response.status_code} - Error!")
                logger.error(f"[TOKEN-EXCHANGE] Response body: {response.text[:500]}...")
                
                # Log error details
                try:
                    error_data = response.json()
                    error_msg = f"{error_data.get('error', 'unknown_error')}: {error_data.get('error_description', 'No description')}"
                    logger.error(f"[TOKEN-EXCHANGE] Error details: {error_data}")
                    
                    # Provide more specific error guidance
                    if error_data.get('error') == 'invalid_client':
                        logger.error("[TOKEN-EXCHANGE] TROUBLESHOOTING: Invalid client error usually means:")
                        logger.error("[TOKEN-EXCHANGE] 1. Client ID (Consumer Key) is incorrect")
                        logger.error("[TOKEN-EXCHANGE] 2. Connected App is not properly configured")
                        logger.error("[TOKEN-EXCHANGE] 3. 'Require Secret for Web Server Flow' must be ENABLED in Connected App")
                        logger.error("[TOKEN-EXCHANGE] 4. Redirect URI mismatch in Connected App settings")
                        logger.error("[TOKEN-EXCHANGE] 5. OAuth scopes not properly configured")
                        logger.error(f"[TOKEN-EXCHANGE] Current client_id: {self.CONSUMER_KEY[:20]}...")
                        logger.error(f"[TOKEN-EXCHANGE] Current redirect_uri: {self.redirect_uri}")
                        logger.error("[TOKEN-EXCHANGE] Required Connected App settings:")
                        logger.error("[TOKEN-EXCHANGE] - Enable OAuth Settings: YES")
                        logger.error("[TOKEN-EXCHANGE] - Require Secret for Web Server Flow: YES (IMPORTANT!)")
                        logger.error("[TOKEN-EXCHANGE] - Callback URL: http://localhost:8080/callback")
                        logger.error("[TOKEN-EXCHANGE] - Selected OAuth Scopes: full access (full), refresh_token")
                        logger.error("[TOKEN-EXCHANGE] - Note: Application requests 'full' scope for maximum compatibility")
                        logger.error("[TOKEN-EXCHANGE] - Important: Token endpoint must use standard domain (login.salesforce.com)")
                    
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error("[TOKEN-EXCHANGE] Could not parse error response as JSON")
                
                logger.error(f"[TOKEN-EXCHANGE] ERROR Token exchange failed: {error_msg}")
                logger.error("[TOKEN-EXCHANGE] " + "=" * 40)
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[TOKEN-EXCHANGE] ERROR Network error during token exchange: {e}")
            logger.error(f"[TOKEN-EXCHANGE] Exception type: {type(e).__name__}")
            logger.error("[TOKEN-EXCHANGE] Stack trace:", exc_info=True)
            logger.error("[TOKEN-EXCHANGE] " + "=" * 40)
            raise Exception(f"Network error: {e}")
        except Exception as e:
            logger.error(f"[TOKEN-EXCHANGE] ERROR Token exchange error: {e}")
            logger.error(f"[TOKEN-EXCHANGE] Exception type: {type(e).__name__}")
            logger.error("[TOKEN-EXCHANGE] Stack trace:", exc_info=True)
            logger.error("[TOKEN-EXCHANGE] " + "=" * 40)
            raise
    
    def _run_callback_server(self, server):
        """Run the callback server"""
        logger.info(f"[CALLBACK-THREAD] Starting callback server thread: {threading.current_thread().name}")
        logger.info(f"[CALLBACK-THREAD] Server address: {server.server_address}")
        logger.info(f"[CALLBACK-THREAD] Server timeout: {server.timeout}s")
        
        try:
            # Handle one request - this is sufficient for OAuth callback
            logger.info("[CALLBACK-THREAD] Waiting for OAuth callback request...")
            server.handle_request()
            logger.info("[CALLBACK-THREAD] Request handled")
            
            if server.callback_url:
                logger.info("[CALLBACK-THREAD] SUCCESS Callback URL received")
                server.callback_received.set()  # Signal that callback was received
            else:
                logger.warning("[CALLBACK-THREAD] Request handled but no callback URL set")
            
            logger.info("[CALLBACK-THREAD] Exiting callback server thread")
            
        except Exception as e:
            logger.error(f"[CALLBACK-THREAD] ERROR Callback server error: {e}")
            logger.error(f"[CALLBACK-THREAD] Exception type: {type(e).__name__}")
            logger.error("[CALLBACK-THREAD] Stack trace:", exc_info=True)
        finally:
            # Always signal completion, even on error
            server.callback_received.set()
    
    def is_token_valid(self) -> bool:
        """Check if current access token is still valid"""
        if not self.access_token:
            logger.debug("[TOKEN-VALID] No access token available")
            return False
            
        if not self.token_expires_at:
            logger.debug("[TOKEN-VALID] No token expiration time available")
            return False
        
        current_time = time.time()
        expires_with_buffer = self.token_expires_at - 300  # 5 minute buffer
        
        logger.debug(f"[TOKEN-VALID] Current time: {datetime.fromtimestamp(current_time)}")
        logger.debug(f"[TOKEN-VALID] Token expires at: {datetime.fromtimestamp(self.token_expires_at)}")
        logger.debug(f"[TOKEN-VALID] Expires with buffer: {datetime.fromtimestamp(expires_with_buffer)}")
        
        is_valid = current_time < expires_with_buffer
        logger.debug(f"[TOKEN-VALID] Token is valid: {is_valid}")
        
        return is_valid
    
    def refresh_access_token(self) -> bool:
        """Refresh access token using refresh token"""
        if not self.refresh_token:
            logger.warning("[TOKEN-REFRESH] No refresh token available")
            return False
        
        try:
            logger.info("[TOKEN-REFRESH] Starting token refresh...")
            
            # Create OAuth2 session for token refresh
            oauth = OAuth2Session(client_id=self.CONSUMER_KEY)
            
            token = oauth.refresh_token(
                self.token_endpoint,
                refresh_token=self.refresh_token
            )
            
            # Update token information
            self.access_token = token.get('access_token')
            self.instance_url_oauth = token.get('instance_url', self.instance_url_oauth)
            
            # Calculate token expiration
            expires_in = token.get('expires_in', 3600)
            self.token_expires_at = time.time() + expires_in
            
            logger.info(f"[TOKEN-REFRESH] New token expires in {expires_in} seconds")
            logger.info(f"[TOKEN-REFRESH] New expiration time: {datetime.fromtimestamp(self.token_expires_at)}")
            
            # Save updated tokens
            self._save_tokens()
            
            logger.info("[TOKEN-REFRESH] Access token refreshed successfully")
            return True
            
        except Exception as e:
            logger.error(f"[TOKEN-REFRESH] Token refresh error: {e}")
            return False
    
    def get_access_token(self) -> Optional[str]:
        """Get current access token, refreshing if necessary"""
        logger.debug(f"[GET-ACCESS-TOKEN] Checking token validity...")
        
        if not self.is_token_valid():
            logger.info(f"[GET-ACCESS-TOKEN] Token is invalid or expired, attempting refresh...")
            if not self.refresh_access_token():
                logger.warning("Could not refresh token - re-authentication required")
                return None
            logger.info(f"[GET-ACCESS-TOKEN] Token refreshed successfully")
        else:
            logger.debug(f"[GET-ACCESS-TOKEN] Token is valid")
        
        return self.access_token
    
    def get_instance_url(self) -> Optional[str]:
        """Get current instance URL"""
        return self.instance_url_oauth or self.instance_url
    
    def clear_credentials(self):
        """Clear authentication state and stored tokens"""
        self.access_token = None
        self.refresh_token = None
        self.instance_url_oauth = None
        self.token_expires_at = None
        
        # Clear stored tokens
        try:
            keyring.delete_password(self.keyring_service, "access_token")
            keyring.delete_password(self.keyring_service, "refresh_token") 
            keyring.delete_password(self.keyring_service, "instance_url")
            keyring.delete_password(self.keyring_service, "token_expires_at")
        except:
            pass
        
        # Clear file-based tokens
        try:
            config_dir = Path.home() / '.config' / 'SalesforceReportPull'
            token_file = config_dir / 'oauth_tokens.txt'
            if token_file.exists():
                token_file.unlink()
        except:
            pass
        
        logger.info("Cleared authentication credentials")
    
    def has_credentials(self) -> bool:
        """Check if OAuth tokens are available"""
        # First check in-memory tokens - access_token is sufficient to indicate stored credentials
        if self.access_token:
            return True
        
        # If not in memory, try to load from storage
        logger.info("No credentials in memory, checking stored credentials...")
        self._load_stored_tokens()
        
        # Check again after loading - access_token is sufficient (even if expired)
        has_tokens = bool(self.access_token)
        logger.info(f"After loading from storage - access_token: {'Present' if self.access_token else 'Missing'}, refresh_token: {'Present' if self.refresh_token else 'Missing'}")
        return has_tokens