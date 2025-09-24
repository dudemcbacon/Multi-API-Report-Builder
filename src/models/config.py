"""
Configuration models and settings management
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
import json
import os
from pathlib import Path
import keyring
import logging

logger = logging.getLogger(__name__)

class SalesforceEnvironment(str, Enum):
    """Salesforce environment types"""
    PRODUCTION = "production"
    SANDBOX = "sandbox"

class AuthMethod(str, Enum):
    """Authentication methods"""
    BROWSER_OAUTH = "browser_oauth"
    USERNAME_PASSWORD = "username_password"

class SalesforceConfig(BaseModel):
    """Salesforce configuration"""
    model_config = ConfigDict(use_enum_values=True)
    
    username: str = Field(default="", description="Salesforce username for password authentication")
    environment: SalesforceEnvironment = Field(default=SalesforceEnvironment.PRODUCTION, description="Environment type")
    auth_method: AuthMethod = Field(default=AuthMethod.BROWSER_OAUTH, description="Authentication method")
    instance_url: Optional[str] = Field(default=None, description="Custom instance URL")
    api_version: str = Field(default="58.0", description="Salesforce API version")
    consumer_key: Optional[str] = Field(default=None, description="Consumer key for OAuth")
    consumer_secret: Optional[str] = Field(default=None, description="Consumer secret for OAuth (optional for PKCE)")
    has_stored_tokens: bool = Field(default=False, description="Whether OAuth tokens are stored securely")
    
    @property
    def login_url(self) -> str:
        """Get appropriate login URL based on environment"""
        if self.instance_url:
            # Ensure the instance URL has https scheme
            url = self.instance_url.strip()
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"
            return url
        return "https://test.salesforce.com" if self.environment == SalesforceEnvironment.SANDBOX else "https://login.salesforce.com"

class WooCommerceConfig(BaseModel):
    """WooCommerce configuration"""
    store_url: str = Field(..., description="WooCommerce store URL")
    consumer_key: str = Field(..., description="WooCommerce consumer key")
    consumer_secret: str = Field(..., description="WooCommerce consumer secret")
    api_version: str = Field(default="wc/v3", description="WooCommerce API version")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

class AvalaraConfig(BaseModel):
    """Avalara configuration"""
    account_id: str = Field(..., description="Avalara account ID")
    license_key: str = Field(..., description="Avalara license key")
    environment: str = Field(default="sandbox", description="Environment (sandbox/production)")

    @property
    def base_url(self) -> str:
        """Get Avalara API base URL"""
        return "https://rest.avatax.com" if self.environment == "production" else "https://sandbox-rest.avatax.com"


class AppearanceConfig(BaseModel):
    """Application appearance settings"""
    theme: str = Field(default="dark", description="Application theme")
    font_size: int = Field(default=10, description="Application font size")
    window_maximized: bool = Field(default=False, description="Start window maximized")
    window_width: int = Field(default=1200, description="Window width")
    window_height: int = Field(default=800, description="Window height")

class DataConfig(BaseModel):
    """Data processing configuration"""
    max_rows: int = Field(default=10000, description="Maximum rows to load")
    auto_refresh_interval: int = Field(default=300, description="Auto refresh interval in seconds")
    auto_refresh_enabled: bool = Field(default=False, description="Enable auto refresh")
    cache_enabled: bool = Field(default=True, description="Enable data caching")
    export_format: str = Field(default="xlsx", description="Default export format")

class ApplicationConfig(BaseModel):
    """Main application configuration"""
    salesforce: Optional[SalesforceConfig] = Field(default=None, description="Salesforce configuration")
    woocommerce: Optional[WooCommerceConfig] = Field(default=None, description="WooCommerce configuration")
    avalara: Optional[AvalaraConfig] = Field(default=None, description="Avalara configuration")
    appearance: AppearanceConfig = Field(default_factory=AppearanceConfig, description="Appearance settings")
    data: DataConfig = Field(default_factory=DataConfig, description="Data processing settings")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApplicationConfig':
        """Create from dictionary"""
        return cls(**data)

class ConfigManager:
    """Configuration manager with secure credential storage"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Custom configuration directory (defaults to user config dir)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default to user config directory
            if os.name == 'nt':  # Windows
                config_base = Path(os.environ.get('APPDATA', ''))
            else:  # Unix-like
                config_base = Path.home() / '.config'
            
            self.config_dir = config_base / 'SalesforceReportPull'
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = self.config_dir / 'config.json'
        self.keyring_service = 'SalesforceReportPull'
        
        # Load configuration
        self._config = self._load_config()
    
    def _load_config(self) -> ApplicationConfig:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                # Migrate old auth method values
                if 'salesforce' in config_data and config_data['salesforce']:
                    sf_config = config_data['salesforce']
                    if sf_config.get('auth_method') in ['jwt_bearer', 'jwt']:
                        sf_config['auth_method'] = 'browser_oauth'
                        logger.info("Migrated JWT auth method to Browser OAuth")
                    
                # Load sensitive data from keyring
                config_data = self._load_credentials_from_keyring(config_data)
                
                return ApplicationConfig.from_dict(config_data)
            else:
                logger.info("No configuration file found, creating default config")
                # Create default config and load from environment variables
                config_data = {}
                config_data = self._load_credentials_from_keyring(config_data)
                return ApplicationConfig.from_dict(config_data)
                
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.info("Creating new default configuration")
            # Create default config and load from environment variables
            config_data = {}
            config_data = self._load_credentials_from_keyring(config_data)
            return ApplicationConfig.from_dict(config_data)
    
    def _load_credentials_from_keyring(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load sensitive credentials from keyring"""
        try:
            # Load Salesforce credentials
            if 'salesforce' in config_data and config_data['salesforce']:
                username = config_data['salesforce'].get('username')
                if username:
                    # For OAuth, tokens are managed by AuthManager
                    # Consumer key and secret could be stored here if needed
                    consumer_key = keyring.get_password(self.keyring_service, f"sf_{username}_consumer_key")
                    consumer_secret = keyring.get_password(self.keyring_service, f"sf_{username}_consumer_secret")
                    if consumer_key:
                        config_data['salesforce']['consumer_key'] = consumer_key
                    if consumer_secret:
                        config_data['salesforce']['consumer_secret'] = consumer_secret
                
                # Load from environment variables if not in keyring
                if not config_data['salesforce'].get('consumer_key'):
                    config_data['salesforce']['consumer_key'] = os.getenv('SF_CONSUMER_KEY')
                if not config_data['salesforce'].get('consumer_secret'):
                    config_data['salesforce']['consumer_secret'] = os.getenv('SF_CONSUMER_SECRET')
            
            # Load WooCommerce credentials
            if 'woocommerce' in config_data and config_data['woocommerce']:
                store_url = config_data['woocommerce'].get('store_url')
                if store_url:
                    consumer_key = keyring.get_password(self.keyring_service, f"woo_{store_url}_key")
                    consumer_secret = keyring.get_password(self.keyring_service, f"woo_{store_url}_secret")
                    
                    if consumer_key:
                        config_data['woocommerce']['consumer_key'] = consumer_key
                    if consumer_secret:
                        config_data['woocommerce']['consumer_secret'] = consumer_secret
            
            # Load Avalara credentials
            if 'avalara' in config_data and config_data['avalara']:
                account_id = config_data['avalara'].get('account_id')
                if account_id:
                    license_key = keyring.get_password(self.keyring_service, f"avalara_{account_id}_license")
                    if license_key:
                        config_data['avalara']['license_key'] = license_key


        except Exception as e:
            logger.error(f"Error loading credentials from keyring: {e}")

        return config_data
    
    def _save_credentials_to_keyring(self, config: ApplicationConfig):
        """Save sensitive credentials to keyring"""
        try:
            # Save WooCommerce credentials
            if config.woocommerce:
                keyring.set_password(self.keyring_service, 
                                   f"woo_{config.woocommerce.store_url}_key", 
                                   config.woocommerce.consumer_key)
                keyring.set_password(self.keyring_service, 
                                   f"woo_{config.woocommerce.store_url}_secret", 
                                   config.woocommerce.consumer_secret)
            
            # Save Avalara credentials
            if config.avalara:
                keyring.set_password(self.keyring_service,
                                   f"avalara_{config.avalara.account_id}_license",
                                   config.avalara.license_key)


        except Exception as e:
            logger.error(f"Error saving credentials to keyring: {e}")
    
    def save_config(self, config: ApplicationConfig = None):
        """Save configuration to file"""
        try:
            if config:
                self._config = config
            
            # Save sensitive credentials to keyring
            self._save_credentials_to_keyring(self._config)
            
            # Create config dict without sensitive data
            config_dict = self._config.to_dict()
            
            # Remove sensitive data before saving to file
            if config_dict.get('woocommerce'):
                config_dict['woocommerce']['consumer_key'] = '***'
                config_dict['woocommerce']['consumer_secret'] = '***'
            
            if config_dict.get('avalara'):
                config_dict['avalara']['license_key'] = '***'


            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
    
    def get_config(self) -> ApplicationConfig:
        """Get current configuration"""
        return self._config
    
    def update_salesforce_config(self, config: SalesforceConfig):
        """Update Salesforce configuration"""
        self._config.salesforce = config
        self.save_config()
    
    def update_woocommerce_config(self, config: WooCommerceConfig):
        """Update WooCommerce configuration"""
        self._config.woocommerce = config
        self.save_config()
    
    def update_avalara_config(self, config: AvalaraConfig):
        """Update Avalara configuration"""
        self._config.avalara = config
        self.save_config()
    
    def update_appearance_config(self, config: AppearanceConfig):
        """Update appearance configuration"""
        self._config.appearance = config
        self.save_config()
    
    def update_data_config(self, config: DataConfig):
        """Update data configuration"""
        self._config.data = config
        self.save_config()

    
    def clear_credentials(self):
        """Clear all stored credentials"""
        try:
            # Clear keyring entries
            if self._config.woocommerce:
                try:
                    keyring.delete_password(self.keyring_service, f"woo_{self._config.woocommerce.store_url}_key")
                    keyring.delete_password(self.keyring_service, f"woo_{self._config.woocommerce.store_url}_secret")
                except keyring.errors.PasswordDeleteError:
                    pass
            
            if self._config.avalara:
                try:
                    keyring.delete_password(self.keyring_service, f"avalara_{self._config.avalara.account_id}_license")
                except keyring.errors.PasswordDeleteError:
                    pass


            logger.info("Credentials cleared from keyring")
            
        except Exception as e:
            logger.error(f"Error clearing credentials: {e}")
    
    def export_config(self, file_path: Path) -> bool:
        """Export configuration to file (without sensitive data)"""
        try:
            config_dict = self._config.to_dict()
            
            # Remove sensitive data
            if config_dict.get('woocommerce'):
                config_dict['woocommerce']['consumer_key'] = '***'
                config_dict['woocommerce']['consumer_secret'] = '***'
            
            if config_dict.get('avalara'):
                config_dict['avalara']['license_key'] = '***'


            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
            return False