"""
Settings dialog for configuring API connections and application preferences
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QLabel,
    QGroupBox, QMessageBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta  # type: ignore[import]
from typing import Optional

from src.models.config import (
    ConfigManager, SalesforceConfig, WooCommerceConfig, AvalaraConfig,
    AppearanceConfig, DataConfig, SalesforceEnvironment, AuthMethod
)

class SalesforceSettingsWidget(QWidget):
    """Salesforce configuration widget"""
    
    def __init__(self, config: Optional[SalesforceConfig] = None):
        super().__init__()
        self.config = config or SalesforceConfig(username="")
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup Salesforce settings UI"""
        layout = QVBoxLayout(self)
        
        # Authentication section
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout(auth_group)
        
        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("user@company.com")
        auth_layout.addRow("Username:", self.username_edit)
        
        # Environment
        self.environment_combo = QComboBox()
        self.environment_combo.addItems(["Production", "Sandbox"])
        auth_layout.addRow("Environment:", self.environment_combo)
        
        # Authentication method (JWT Bearer Flow only)
        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItems(["JWT Bearer Flow"])
        self.auth_method_combo.setEnabled(False)  # Only one option available
        auth_layout.addRow("Auth Method:", self.auth_method_combo)
        
        # Custom instance URL
        self.instance_url_edit = QLineEdit()
        self.instance_url_edit.setPlaceholderText("https://mycompany.my.salesforce.com")
        auth_layout.addRow("Custom Instance URL:", self.instance_url_edit)
        
        layout.addWidget(auth_group)
        
        # API Configuration
        api_group = QGroupBox("API Configuration")
        api_layout = QFormLayout(api_group)
        
        # API Version
        self.api_version_edit = QLineEdit()
        self.api_version_edit.setText("58.0")
        api_layout.addRow("API Version:", self.api_version_edit)
        
        layout.addWidget(api_group)
        
        # Connected App Information
        app_group = QGroupBox("Connected App Information")
        app_layout = QVBoxLayout(app_group)
        
        # Consumer Key (hardcoded)
        consumer_key_label = QLabel("Consumer Key: 3MVG9zlTNB8o8BA1YxGdhYcJEvW8Nm5i8wE..Gq8DY7xrEXCKHi3FW48drdwAVWdqRj00HX7rq3QTq4kGphNQ")
        consumer_key_label.setWordWrap(True)
        consumer_key_label.setStyleSheet("background-color: #f0f0f0; padding: 5px; border: 1px solid #ccc;")
        app_layout.addWidget(QLabel("Consumer Key (hardcoded):"))
        app_layout.addWidget(consumer_key_label)
        
        # Optional Consumer Secret
        self.consumer_secret_edit = QLineEdit()
        self.consumer_secret_edit.setPlaceholderText("Optional for enhanced security")
        self.consumer_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        app_layout.addWidget(QLabel("Consumer Secret (optional):"))
        app_layout.addWidget(self.consumer_secret_edit)
        
        layout.addWidget(app_group)
        
        # Setup Instructions
        instructions_group = QGroupBox("Setup Instructions")
        instructions_layout = QVBoxLayout(instructions_group)
        
        instructions_text = QLabel("""
        <b>To setup JWT Bearer Flow authentication in Salesforce:</b><br>
        1. Go to Setup → App Manager → New Connected App<br>
        2. Fill in basic information (Name, API Name, Contact Email)<br>
        3. Enable API (Enable OAuth Settings)<br>
        4. Enable "Use Digital Signatures" and upload your certificate/public key<br>
        5. Select OAuth Scopes: "Full access (full)" or specific scopes needed<br>
        6. Save and note the Consumer Key (Client ID)<br>
        7. In Manage Connected Apps, edit Policies:<br>
        &nbsp;&nbsp;&nbsp;- Permitted Users: "Admin approved users are pre-authorized"<br>
        &nbsp;&nbsp;&nbsp;- IP Relaxation: "Relax IP restrictions"<br>
        8. Assign the Connected App to user profiles/permission sets<br>
        9. Generate RSA key pair and configure SF_CLIENT_ID, SF_JWT_SUBJECT, SF_JWT_KEY_PATH<br>
        <br>
        <b>JWT Bearer Flow</b> - Server-to-server authentication using RSA certificates.<br>
        No browser interaction required - more secure for production environments.
        """)
        instructions_text.setWordWrap(True)
        instructions_layout.addWidget(instructions_text)
        
        layout.addWidget(instructions_group)
        
        layout.addStretch()
    
    def load_config(self):
        """Load configuration into UI"""
        if not self.config:
            return
        
        self.username_edit.setText(self.config.username)
        
        # Environment
        env_index = 0 if self.config.environment == SalesforceEnvironment.PRODUCTION else 1
        self.environment_combo.setCurrentIndex(env_index)
        
        # Auth method
        auth_index = 0 if self.config.auth_method == AuthMethod.BROWSER_OAUTH else 1
        self.auth_method_combo.setCurrentIndex(auth_index)
        
        if self.config.instance_url:
            self.instance_url_edit.setText(self.config.instance_url)
        
        self.api_version_edit.setText(self.config.api_version)
        
        if self.config.consumer_secret:
            self.consumer_secret_edit.setText(self.config.consumer_secret)
    
    def get_config(self) -> SalesforceConfig:
        """Get configuration from UI"""
        environment = SalesforceEnvironment.PRODUCTION if self.environment_combo.currentIndex() == 0 else SalesforceEnvironment.SANDBOX
        auth_method = AuthMethod.BROWSER_OAUTH if self.auth_method_combo.currentIndex() == 0 else AuthMethod.USERNAME_PASSWORD
        
        return SalesforceConfig(
            username=self.username_edit.text().strip(),
            environment=environment,
            auth_method=auth_method,
            instance_url=self.instance_url_edit.text().strip() or None,
            api_version=self.api_version_edit.text().strip(),
            consumer_secret=self.consumer_secret_edit.text().strip() or None
        )
    

class AppearanceSettingsWidget(QWidget):
    """Appearance configuration widget"""
    
    def __init__(self, config: Optional[AppearanceConfig] = None):
        super().__init__()
        self.config = config or AppearanceConfig()
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup appearance settings UI"""
        layout = QVBoxLayout(self)
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        theme_layout.addRow("Theme:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        theme_layout.addRow("Font Size:", self.font_size_spin)
        
        layout.addWidget(theme_group)
        
        # Window settings
        window_group = QGroupBox("Window")
        window_layout = QFormLayout(window_group)
        
        self.maximized_check = QCheckBox("Start maximized")
        window_layout.addRow(self.maximized_check)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(800, 3000)
        window_layout.addRow("Default Width:", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(600, 2000)
        window_layout.addRow("Default Height:", self.height_spin)
        
        layout.addWidget(window_group)
        
        layout.addStretch()
    
    def load_config(self):
        """Load configuration into UI"""
        self.theme_combo.setCurrentText(self.config.theme.title())
        self.font_size_spin.setValue(self.config.font_size)
        self.maximized_check.setChecked(self.config.window_maximized)
        self.width_spin.setValue(self.config.window_width)
        self.height_spin.setValue(self.config.window_height)
    
    def get_config(self) -> AppearanceConfig:
        """Get configuration from UI"""
        return AppearanceConfig(
            theme=self.theme_combo.currentText().lower(),
            font_size=self.font_size_spin.value(),
            window_maximized=self.maximized_check.isChecked(),
            window_width=self.width_spin.value(),
            window_height=self.height_spin.value()
        )

class DataSettingsWidget(QWidget):
    """Data processing configuration widget"""
    
    def __init__(self, config: Optional[DataConfig] = None):
        super().__init__()
        self.config = config or DataConfig()
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup data settings UI"""
        layout = QVBoxLayout(self)
        
        # Performance settings
        perf_group = QGroupBox("Performance")
        perf_layout = QFormLayout(perf_group)
        
        self.max_rows_spin = QSpinBox()
        self.max_rows_spin.setRange(100, 100000)
        self.max_rows_spin.setSingleStep(1000)
        perf_layout.addRow("Max Rows to Load:", self.max_rows_spin)
        
        self.cache_check = QCheckBox("Enable data caching")
        perf_layout.addRow(self.cache_check)
        
        layout.addWidget(perf_group)
        
        # Auto-refresh settings
        refresh_group = QGroupBox("Auto Refresh")
        refresh_layout = QFormLayout(refresh_group)
        
        self.auto_refresh_check = QCheckBox("Enable auto refresh")
        refresh_layout.addRow(self.auto_refresh_check)
        
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(30, 3600)
        self.refresh_interval_spin.setSuffix(" seconds")
        refresh_layout.addRow("Refresh Interval:", self.refresh_interval_spin)
        
        layout.addWidget(refresh_group)
        
        # Export settings
        export_group = QGroupBox("Export")
        export_layout = QFormLayout(export_group)
        
        self.export_format_combo = QComboBox()
        self.export_format_combo.addItems(["xlsx", "csv", "json"])
        export_layout.addRow("Default Format:", self.export_format_combo)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
    
    def load_config(self):
        """Load configuration into UI"""
        self.max_rows_spin.setValue(self.config.max_rows)
        self.cache_check.setChecked(self.config.cache_enabled)
        self.auto_refresh_check.setChecked(self.config.auto_refresh_enabled)
        self.refresh_interval_spin.setValue(self.config.auto_refresh_interval)
        self.export_format_combo.setCurrentText(self.config.export_format)
    
    def get_config(self) -> DataConfig:
        """Get configuration from UI"""
        return DataConfig(
            max_rows=self.max_rows_spin.value(),
            cache_enabled=self.cache_check.isChecked(),
            auto_refresh_enabled=self.auto_refresh_check.isChecked(),
            auto_refresh_interval=self.refresh_interval_spin.value(),
            export_format=self.export_format_combo.currentText()
        )

class SettingsDialog(QDialog):
    """Main settings dialog"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
        self.setup_ui()
        self.setModal(True)
        self.setWindowTitle("Settings")
        self.setMinimumSize(600, 500)
    
    def setup_ui(self):
        """Setup settings dialog UI"""
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Salesforce tab
        self.salesforce_widget = SalesforceSettingsWidget(self.config.salesforce)
        self.tab_widget.addTab(self.salesforce_widget, qta.icon('fa5b.salesforce'), "Salesforce")  # type: ignore[arg-type]
        
        # WooCommerce tab (placeholder)
        woo_widget = QLabel("WooCommerce settings not yet implemented")
        woo_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tab_widget.addTab(woo_widget, qta.icon('fa5b.wordpress'), "WooCommerce")  # type: ignore[arg-type]
        
        # Avalara tab (placeholder)
        avalara_widget = QLabel("Avalara settings not yet implemented")
        avalara_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tab_widget.addTab(avalara_widget, qta.icon('fa5s.calculator'), "Avalara")  # type: ignore[arg-type]
        
        # Appearance tab
        self.appearance_widget = AppearanceSettingsWidget(self.config.appearance)
        self.tab_widget.addTab(self.appearance_widget, qta.icon('fa5s.palette'), "Appearance")  # type: ignore[arg-type]
        
        # Data tab
        self.data_widget = DataSettingsWidget(self.config.data)
        self.tab_widget.addTab(self.data_widget, qta.icon('fa5s.database'), "Data")  # type: ignore[arg-type]
        
        layout.addWidget(self.tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply
        )
        
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        apply_button = button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self.apply_settings)
        
        layout.addWidget(button_box)
    
    def apply_settings(self):
        """Apply settings without closing dialog"""
        try:
            # Get configurations from widgets
            salesforce_config = self.salesforce_widget.get_config()
            appearance_config = self.appearance_widget.get_config()
            data_config = self.data_widget.get_config()
            
            # Validate Salesforce config
            if not salesforce_config.username:
                QMessageBox.warning(self, "Validation Error", "Salesforce username is required.")
                self.tab_widget.setCurrentIndex(0)
                return
            
            # Update configuration
            self.config.salesforce = salesforce_config
            self.config.appearance = appearance_config
            self.config.data = data_config
            
            # Save configuration
            self.config_manager.save_config(self.config)
            
            # Emit signal
            self.settings_changed.emit()
            
            QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error applying settings:\n{str(e)}")
    
    def accept(self):
        """Accept dialog and save settings"""
        self.apply_settings()
        super().accept()

