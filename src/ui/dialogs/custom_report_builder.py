"""
Custom Report Builder Dialog for Salesforce
"""
import logging
from typing import Dict, Any, List, Optional
import polars as pl

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QTextEdit, QTabWidget, QWidget, QGroupBox, QSpinBox, QCheckBox,
    QMessageBox, QProgressBar, QFrame, QTableWidget, QTableWidgetItem,
    QScrollArea, QGridLayout, QButtonGroup, QRadioButton, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import qtawesome as qta

from src.services.async_salesforce_api import AsyncSalesforceAPI
from src.services.async_quickbase_api import AsyncQuickBaseAPI
from src.ui.managers.metadata_cache_manager import MetadataCacheManager
import os

# Import visual query builder components
try:
    from src.ui.dialogs.visual_query_builder import (
        FieldPaletteWidget, VisualQueryCanvas, VisualFilterBuilder, RelationshipExplorer
    )
    VISUAL_BUILDER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Visual query builder not available: {e}")
    VISUAL_BUILDER_AVAILABLE = False

logger = logging.getLogger(__name__)

class QuickBaseSchemaWorker(QThread):
    """Worker to load QuickBase schema data"""

    schema_loaded = pyqtSignal(dict)  # app_id -> {tables: [], fields: {}}
    error_occurred = pyqtSignal(str)

    def __init__(self, realm_hostname: str, user_token: str, app_id: str = None):
        super().__init__()
        self.realm_hostname = realm_hostname
        self.user_token = user_token
        self.app_id = app_id

    def run(self):
        """Load schema data in background"""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._load_schema_async())
        except Exception as e:
            logger.error(f"[QB-SCHEMA] Error loading schema: {e}")
            self.error_occurred.emit(str(e))
        finally:
            loop.close()

    async def _load_schema_async(self):
        """Async method to load schema"""
        try:
            async with AsyncQuickBaseAPI(
                realm_hostname=self.realm_hostname,
                user_token=self.user_token,
                app_id=self.app_id
            ) as api:

                apps = await api.get_apps()
                schema_data = {}

                for app in apps[:3]:  # Limit to first 3 apps for performance
                    app_id = app.get('id', '')
                    app_name = app.get('name', 'Unknown App')

                    tables = await api.get_tables(app_id)

                    # Load schemas for each table
                    table_schemas = {}
                    for table in tables[:5]:  # Limit to first 5 tables per app
                        table_id = table.get('id', '')
                        if table_id:
                            schema = await api.get_table_schema(table_id)
                            table_schemas[table_id] = schema

                    schema_data[app_id] = {
                        'app_name': app_name,
                        'tables': tables,
                        'schemas': table_schemas
                    }

                self.schema_loaded.emit(schema_data)

        except Exception as e:
            logger.error(f"[QB-SCHEMA] Error in async schema loading: {e}")
            self.error_occurred.emit(str(e))

class ObjectFieldsWorker(QThread):
    """Worker thread for loading object fields"""
    
    fields_loaded = pyqtSignal(str, dict)  # object_name, field_data
    error_occurred = pyqtSignal(str, str)  # object_name, error_message
    
    def __init__(self, sf_api: AsyncSalesforceAPI, cache_manager: MetadataCacheManager, object_name: str):
        super().__init__()
        self.sf_api = sf_api
        self.cache_manager = cache_manager
        self.object_name = object_name
        
    def run(self):
        """Load object fields in background"""
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(self._load_fields_async())
            if result:
                self.fields_loaded.emit(self.object_name, result)
            else:
                self.error_occurred.emit(self.object_name, "No field data returned")
        except Exception as e:
            logger.error(f"[OBJECT-FIELDS-WORKER] Error loading fields for {self.object_name}: {e}")
            self.error_occurred.emit(self.object_name, str(e))
        finally:
            loop.close()
    
    async def _load_fields_async(self):
        """Load fields using async API"""
        # Try cache first
        cached_desc = self.cache_manager.get_object_description(self.object_name)
        if cached_desc:
            logger.info(f"[OBJECT-FIELDS-WORKER] Using cached description for {self.object_name}")
            return cached_desc
        
        # Load from API
        description = await self.sf_api.describe_object(self.object_name)
        if description:
            # Save to cache
            self.cache_manager.save_object_description(self.object_name, description)
            logger.info(f"[OBJECT-FIELDS-WORKER] Loaded and cached description for {self.object_name}")
            return description
        
        return None

class FilterConditionWidget(QWidget):
    """Widget for defining a single filter condition"""
    
    condition_changed = pyqtSignal()
    
    def __init__(self, fields: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.fields = fields
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Field selector
        self.field_combo = QComboBox()
        self.field_combo.addItem("Select Field...")
        for field in self.fields:
            self.field_combo.addItem(f"{field['label']} ({field['name']})", field)
        self.field_combo.currentIndexChanged.connect(self.on_field_changed)
        layout.addWidget(self.field_combo)
        
        # Operator selector
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'NOT IN'])
        self.operator_combo.currentTextChanged.connect(self.condition_changed.emit)
        layout.addWidget(self.operator_combo)
        
        # Value input
        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Enter value...")
        self.value_edit.textChanged.connect(self.condition_changed.emit)
        layout.addWidget(self.value_edit)
        
        # Remove button
        self.remove_btn = QPushButton()
        self.remove_btn.setIcon(qta.icon('fa5s.times'))
        self.remove_btn.setMaximumWidth(30)
        self.remove_btn.clicked.connect(self.remove_self)
        layout.addWidget(self.remove_btn)
    
    def on_field_changed(self):
        """Handle field selection change"""
        field_data = self.field_combo.currentData()
        if field_data:
            # Update operators based on field type
            field_type = field_data.get('type', '').lower()
            
            if field_type in ['picklist', 'multipicklist']:
                # Show picklist values
                picklist_values = field_data.get('picklistValues', [])
                if picklist_values:
                    values = [pv.get('value', '') for pv in picklist_values]
                    self.value_edit.setPlaceholderText(f"Options: {', '.join(values[:3])}...")
            elif field_type in ['date', 'datetime']:
                self.value_edit.setPlaceholderText("YYYY-MM-DD or TODAY, LAST_WEEK, etc.")
            elif field_type in ['integer', 'double', 'currency', 'percent']:
                self.value_edit.setPlaceholderText("Enter number...")
            else:
                self.value_edit.setPlaceholderText("Enter value...")
        
        self.condition_changed.emit()
    
    def remove_self(self):
        """Remove this condition widget"""
        self.parent().layout().removeWidget(self)
        self.deleteLater()
        self.condition_changed.emit()
    
    def get_condition(self) -> Optional[Dict[str, str]]:
        """Get the current condition as a dictionary"""
        field_data = self.field_combo.currentData()
        if not field_data or not self.value_edit.text().strip():
            return None
        
        return {
            'field': field_data['name'],
            'field_label': field_data['label'],
            'operator': self.operator_combo.currentText(),
            'value': self.value_edit.text().strip()
        }

class CustomReportBuilderDialog(QDialog):
    """
    Dialog for building custom reports with support for multiple data sources
    """

    report_ready = pyqtSignal(dict)  # Emitted when report is ready to run

    def __init__(self, sf_api: AsyncSalesforceAPI = None, cache_manager: MetadataCacheManager = None, parent=None):
        super().__init__(parent)
        self.sf_api = sf_api
        self.cache_manager = cache_manager

        # Initialize QuickBase API if credentials available
        self.qb_api = None
        try:
            realm_hostname = os.getenv('QUICKBASE_REALM_HOSTNAME')
            user_token = os.getenv('QUICKBASE_USER_TOKEN')
            app_id = os.getenv('QUICKBASE_APP_ID')
            if realm_hostname and user_token:
                self.qb_api = AsyncQuickBaseAPI(realm_hostname, user_token, app_id)
        except Exception as e:
            logger.warning(f"QuickBase API not available: {e}")

        # Current data source
        self.current_data_source = 'salesforce'  # Default to Salesforce
        self.objects_data = []
        self.current_object_description = None
        self.selected_fields = []
        self.filter_conditions = []
        self.fields_worker = None
        
        self.setWindowTitle("Custom Report Builder - Multi-Source")
        self.setModal(True)
        self.resize(1200, 800)

        # Load initial data source
        if available_sources:
            self.current_data_source = available_sources[0][1]
            self.load_objects_for_current_source()
        
        self.setup_ui()
        self.load_objects()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Title and instructions
        title = QLabel("Custom Report Builder")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)
        
        instructions = QLabel("Build custom SOQL queries with an intuitive interface")
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Object selection
        self.setup_object_panel(splitter)
        
        # Center panel - Field selection and filters
        self.setup_field_panel(splitter)
        
        # Right panel - Query preview and settings
        self.setup_query_panel(splitter)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)  # Objects panel
        splitter.setStretchFactor(1, 2)  # Fields panel
        splitter.setStretchFactor(2, 1)  # Query panel
        splitter.setSizes([300, 600, 300])
        
        # Bottom buttons
        self.setup_bottom_buttons(layout)
    
    def setup_object_panel(self, parent_splitter):
        """Setup the object selection panel"""
        object_widget = QWidget()
        object_layout = QVBoxLayout(object_widget)
        
        # Data source selection
        source_group = QGroupBox("1. Select Data Source")
        source_layout = QVBoxLayout(source_group)

        self.data_source_combo = QComboBox()
        available_sources = []
        if self.sf_api:
            available_sources.append(('Salesforce', 'salesforce'))
        if self.qb_api:
            available_sources.append(('QuickBase', 'quickbase'))

        for name, value in available_sources:
            self.data_source_combo.addItem(name, value)

        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        source_layout.addWidget(self.data_source_combo)
        object_layout.addWidget(source_group)

        # Object/Table selection
        object_group = QGroupBox("2. Select Object/Table")
        object_group_layout = QVBoxLayout(object_group)
        
        # Search box
        self.object_search = QLineEdit()
        self.object_search.setPlaceholderText("Search objects...")
        self.object_search.textChanged.connect(self.filter_objects)
        object_group_layout.addWidget(self.object_search)
        
        # Object tree
        self.object_tree = QTreeWidget()
        self.object_tree.setHeaderLabels(["Object", "Type"])
        self.object_tree.itemClicked.connect(self.on_object_selected)
        object_group_layout.addWidget(self.object_tree)
        
        object_layout.addWidget(object_group)
        
        # Object info
        info_group = QGroupBox("Object Information")
        info_layout = QVBoxLayout(info_group)
        
        self.object_info_label = QLabel("Select an object to see details")
        self.object_info_label.setWordWrap(True)
        self.object_info_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.object_info_label)
        
        object_layout.addWidget(info_group)
        
        parent_splitter.addWidget(object_widget)
    
    def setup_field_panel(self, parent_splitter):
        """Setup the field selection and filters panel"""
        field_widget = QWidget()
        field_layout = QVBoxLayout(field_widget)
        
        # Tab widget for fields and filters
        self.field_tabs = QTabWidget()
        field_layout.addWidget(self.field_tabs)
        
        # Fields tab
        self.setup_fields_tab()
        
        # Filters tab
        self.setup_filters_tab()
        
        # Settings tab
        self.setup_settings_tab()
        
        # Visual Builder tab
        self.setup_visual_builder_tab()
        
        parent_splitter.addWidget(field_widget)
    
    def setup_fields_tab(self):
        """Setup the fields selection tab"""
        fields_tab = QWidget()
        layout = QVBoxLayout(fields_tab)
        
        # Field selection controls
        controls_layout = QHBoxLayout()
        
        self.field_search = QLineEdit()
        self.field_search.setPlaceholderText("Search fields...")
        self.field_search.textChanged.connect(self.filter_fields)
        controls_layout.addWidget(self.field_search)
        
        # Field type filter
        self.field_type_combo = QComboBox()
        self.field_type_combo.addItems(['All Types', 'Standard', 'Custom', 'Relationships'])
        self.field_type_combo.currentTextChanged.connect(self.filter_fields)
        controls_layout.addWidget(self.field_type_combo)
        
        # Quick select buttons
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_fields)
        controls_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.clicked.connect(self.clear_all_fields)
        controls_layout.addWidget(clear_all_btn)
        
        layout.addLayout(controls_layout)
        
        # Fields list
        self.fields_list = QListWidget()
        self.fields_list.itemChanged.connect(self.on_field_selection_changed)
        layout.addWidget(self.fields_list)
        
        # Selected fields count
        self.selected_fields_label = QLabel("Selected: 0 fields")
        self.selected_fields_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.selected_fields_label)
        
        self.field_tabs.addTab(fields_tab, "Fields")
    
    def setup_filters_tab(self):
        """Setup the filters tab"""
        filters_tab = QWidget()
        layout = QVBoxLayout(filters_tab)
        
        # Filter instructions
        instructions = QLabel("Add conditions to filter your results:")
        layout.addWidget(instructions)
        
        # Filters container
        self.filters_scroll = QScrollArea()
        self.filters_widget = QWidget()
        self.filters_layout = QVBoxLayout(self.filters_widget)
        self.filters_scroll.setWidget(self.filters_widget)
        self.filters_scroll.setWidgetResizable(True)
        layout.addWidget(self.filters_scroll)
        
        # Add filter button
        add_filter_btn = QPushButton("Add Condition")
        add_filter_btn.setIcon(qta.icon('fa5s.plus'))
        add_filter_btn.clicked.connect(self.add_filter_condition)
        layout.addWidget(add_filter_btn)
        
        self.field_tabs.addTab(filters_tab, "Filters")
    
    def setup_settings_tab(self):
        """Setup the query settings tab"""
        settings_tab = QWidget()
        layout = QVBoxLayout(settings_tab)
        
        # Limit settings
        limit_group = QGroupBox("Query Limits")
        limit_layout = QGridLayout(limit_group)
        
        limit_layout.addWidget(QLabel("Row Limit:"), 0, 0)
        self.row_limit_spin = QSpinBox()
        self.row_limit_spin.setRange(1, 50000)
        self.row_limit_spin.setValue(1000)
        limit_layout.addWidget(self.row_limit_spin, 0, 1)
        
        layout.addWidget(limit_group)
        
        # Sort settings
        sort_group = QGroupBox("Sorting")
        sort_layout = QGridLayout(sort_group)
        
        sort_layout.addWidget(QLabel("Sort By:"), 0, 0)
        self.sort_field_combo = QComboBox()
        self.sort_field_combo.addItem("No Sorting")
        sort_layout.addWidget(self.sort_field_combo, 0, 1)
        
        sort_layout.addWidget(QLabel("Order:"), 1, 0)
        self.sort_order_combo = QComboBox()
        self.sort_order_combo.addItems(['ASC', 'DESC'])
        sort_layout.addWidget(self.sort_order_combo, 1, 1)
        
        layout.addWidget(sort_group)
        
        layout.addStretch()
        
        self.field_tabs.addTab(settings_tab, "Settings")
    
    def setup_visual_builder_tab(self):
        """Setup the visual query builder tab"""
        if not VISUAL_BUILDER_AVAILABLE:
            # Create a placeholder tab if visual builder is not available
            placeholder_tab = QWidget()
            placeholder_layout = QVBoxLayout(placeholder_tab)
            
            placeholder_label = QLabel("Visual Query Builder not available.\nThe visual query builder components could not be loaded.")
            placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_label.setStyleSheet("color: #666; font-style: italic; padding: 50px;")
            placeholder_layout.addWidget(placeholder_label)
            
            self.field_tabs.addTab(placeholder_tab, "Visual Builder")
            return
        
        # Create visual builder tab
        visual_tab = QWidget()
        visual_layout = QVBoxLayout(visual_tab)
        visual_layout.setContentsMargins(5, 5, 5, 5)
        
        # Instructions
        instructions = QLabel("Build your query visually by dragging fields from the palette below.")
        instructions.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        visual_layout.addWidget(instructions)
        
        # Create splitter for field palette, relationships, and visual canvas
        visual_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Field palette and relationship explorer
        left_panel = QSplitter(Qt.Orientation.Vertical)
        
        # Field palette (top)
        self.field_palette = FieldPaletteWidget()
        self.field_palette.field_double_clicked.connect(self.on_visual_field_double_clicked)
        left_panel.addWidget(self.field_palette)
        
        # Relationship explorer (bottom)
        self.relationship_explorer = RelationshipExplorer()
        self.relationship_explorer.relationship_selected.connect(self.on_relationship_selected)
        left_panel.addWidget(self.relationship_explorer)
        
        # Set left panel proportions (60% palette, 40% relationships)
        left_panel.setSizes([180, 120])
        
        visual_splitter.addWidget(left_panel)
        
        # Right: Visual query canvas
        self.visual_canvas = VisualQueryCanvas()
        self.visual_canvas.query_changed.connect(self.on_visual_query_changed)
        self.visual_canvas.test_query_requested.connect(self.on_test_query_requested)
        visual_splitter.addWidget(self.visual_canvas)
        
        # Set splitter proportions (35% left panel, 65% canvas)
        visual_splitter.setSizes([210, 390])
        
        visual_layout.addWidget(visual_splitter)
        
        # Add sync button to synchronize with form-based builder
        sync_layout = QHBoxLayout()
        sync_layout.addStretch()
        
        sync_to_form_btn = QPushButton("Sync to Form Builder")
        sync_to_form_btn.setIcon(qta.icon('fa5s.sync'))
        sync_to_form_btn.clicked.connect(self.sync_visual_to_form)
        sync_to_form_btn.setToolTip("Sync visual builder selections to the form-based builder")
        sync_layout.addWidget(sync_to_form_btn)
        
        sync_from_form_btn = QPushButton("Sync from Form Builder") 
        sync_from_form_btn.setIcon(qta.icon('fa5s.sync-alt'))
        sync_from_form_btn.clicked.connect(self.sync_form_to_visual)
        sync_from_form_btn.setToolTip("Sync form-based builder selections to the visual builder")
        sync_layout.addWidget(sync_from_form_btn)
        
        visual_layout.addLayout(sync_layout)
        
        self.field_tabs.addTab(visual_tab, "Visual Builder")
        
        logger.info("[CUSTOM-REPORT-BUILDER] Visual builder tab added")
    
    def setup_query_panel(self, parent_splitter):
        """Setup the query preview panel"""
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        
        # Query preview
        query_group = QGroupBox("Query Preview")
        query_group_layout = QVBoxLayout(query_group)
        
        self.query_preview = QTextEdit()
        self.query_preview.setReadOnly(True)
        self.query_preview.setMaximumHeight(200)
        self.query_preview.setFont(QFont("Courier", 10))
        query_group_layout.addWidget(self.query_preview)
        
        query_layout.addWidget(query_group)
        
        # Preview results
        preview_group = QGroupBox("Preview Results")
        preview_layout = QVBoxLayout(preview_group)
        
        # Preview button
        self.preview_btn = QPushButton("Preview Data")
        self.preview_btn.setIcon(qta.icon('fa5s.eye'))
        self.preview_btn.clicked.connect(self.preview_query)
        self.preview_btn.setEnabled(False)
        preview_layout.addWidget(self.preview_btn)
        
        # Preview progress
        self.preview_progress = QProgressBar()
        self.preview_progress.setVisible(False)
        preview_layout.addWidget(self.preview_progress)
        
        # Preview table
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(300)
        preview_layout.addWidget(self.preview_table)
        
        query_layout.addWidget(preview_group)
        
        parent_splitter.addWidget(query_widget)
    
    def setup_bottom_buttons(self, layout):
        """Setup bottom action buttons"""
        buttons_layout = QHBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        buttons_layout.addWidget(self.progress_bar)
        
        buttons_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        # Run Report button
        self.run_report_btn = QPushButton("Create Report")
        self.run_report_btn.setIcon(qta.icon('fa5s.play'))
        self.run_report_btn.clicked.connect(self.create_report)
        self.run_report_btn.setEnabled(False)
        buttons_layout.addWidget(self.run_report_btn)
        
        layout.addLayout(buttons_layout)
    
    def load_objects_for_current_source(self):
        """Load objects/tables for the current data source"""
        if self.current_data_source == 'salesforce':
            self.load_salesforce_objects()
        elif self.current_data_source == 'quickbase':
            self.load_quickbase_tables()

    def load_salesforce_objects(self):
        """Load Salesforce objects"""
        if not self.sf_api:
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Try cache first
        if self.cache_manager:
            cached_objects = self.cache_manager.get_all_objects()
            if cached_objects:
                logger.info("[CUSTOM-REPORT-BUILDER] Using cached objects")
                self.objects_data = cached_objects
                self.populate_object_tree()
                self.progress_bar.setVisible(False)
                return

        # Load from API
        logger.info("[CUSTOM-REPORT-BUILDER] Loading objects from API")
        QTimer.singleShot(100, self.load_objects_from_api)
    
    def load_objects_from_api(self):
        """Load objects from API in background"""
        from src.ui.workers import SalesforceConnectionWorker
        
        # Create worker to load objects
        self.objects_worker = SalesforceConnectionWorker("load_objects", self.sf_api)
        self.objects_worker.connection_result.connect(self.on_objects_loaded)
        self.objects_worker.error_occurred.connect(self.on_objects_error)
        self.objects_worker.start()
    
    def on_objects_loaded(self, result):
        """Handle objects loaded from API"""
        if result.get('success') and 'objects' in result:
            self.objects_data = result['objects']
            self.cache_manager.save_all_objects(self.objects_data)
            self.populate_object_tree()
        else:
            QMessageBox.warning(self, "Error", "Failed to load Salesforce objects")
        
        self.progress_bar.setVisible(False)
    
    def on_objects_error(self, operation, error):
        """Handle error loading objects"""
        logger.error(f"[CUSTOM-REPORT-BUILDER] Objects loading error: {error}")
        self.progress_bar.setVisible(False)
        
        # Show user-friendly error message with retry option
        data_source_name = "Salesforce" if self.current_data_source == 'salesforce' else "QuickBase"
        error_message = f"Failed to load {data_source_name} objects/tables.\n\n"

        if "Event loop is closed" in error:
            error_message += "This appears to be a connection issue. The session management has been improved.\n"
        elif "authentication" in error.lower() or "unauthorized" in error.lower():
            error_message += f"Authentication failed. Please check your {data_source_name} connection.\n"
        elif "timeout" in error.lower():
            error_message += "Request timed out. Please try again.\n"
        else:
            error_message += f"Error details: {error}\n"

        error_message += "\nWould you like to retry loading the objects?"
        
        reply = QMessageBox.question(
            self, 
            "Load Objects Failed", 
            error_message,
            QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Retry
        )
        
        if reply == QMessageBox.StandardButton.Retry:
            logger.info("[CUSTOM-REPORT-BUILDER] User requested retry")
            QTimer.singleShot(1000, self.load_objects_for_current_source)  # Retry after 1 second

    def on_data_source_changed(self, data_source_name: str):
        """Handle data source selection change"""
        data_source_value = self.data_source_combo.currentData()
        if data_source_value:
            self.current_data_source = data_source_value
            logger.info(f"[CUSTOM-REPORT-BUILDER] Switched to data source: {data_source_value}")

            # Clear current data
            self.object_tree.clear()
            self.fields_list.clear()
            self.selected_fields_list.clear()
            self.query_preview.clear()

            # Load objects for new data source
            self.load_objects_for_current_source()

    def load_quickbase_tables(self):
        """Load QuickBase applications and tables"""
        if not self.qb_api:
            QMessageBox.warning(self, "QuickBase Not Available",
                              "QuickBase API is not configured. Please check your credentials.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Create worker to load QuickBase schema
        self.qb_worker = QuickBaseSchemaWorker(
            self.qb_api.realm_hostname,
            self.qb_api.user_token,
            self.qb_api.default_app_id
        )
        self.qb_worker.schema_loaded.connect(self.on_quickbase_schema_loaded)
        self.qb_worker.error_occurred.connect(self.on_quickbase_error)
        self.qb_worker.start()

    def on_quickbase_schema_loaded(self, schema_data):
        """Handle loaded QuickBase schema"""
        self.progress_bar.setVisible(False)
        self.qb_schema_data = schema_data
        self.populate_quickbase_tree()

    def on_quickbase_error(self, error_message):
        """Handle QuickBase loading error"""
        self.progress_bar.setVisible(False)
        logger.error(f"[CUSTOM-REPORT-BUILDER] QuickBase error: {error_message}")
        QMessageBox.critical(self, "QuickBase Error",
                           f"Failed to load QuickBase data:\\n{error_message}")

    def populate_quickbase_tree(self):
        """Populate tree with QuickBase apps and tables"""
        self.object_tree.clear()

        if not hasattr(self, 'qb_schema_data'):
            return

        for app_id, app_data in self.qb_schema_data.items():
            app_name = app_data.get('app_name', 'Unknown App')
            app_item = QTreeWidgetItem(self.object_tree, [app_name, f"App: {app_id}"])
            app_item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'app', 'app_id': app_id})

            # Add tables under each app
            tables = app_data.get('tables', [])
            for table in tables:
                table_name = table.get('name', 'Unknown Table')
                table_id = table.get('id', '')
                table_item = QTreeWidgetItem(app_item, [table_name, f"Table: {table_id}"])
                table_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'table',
                    'app_id': app_id,
                    'table_id': table_id,
                    'table_name': table_name,
                    'schema': app_data.get('schemas', {}).get(table_id, {})
                })

        self.object_tree.expandAll()
        logger.info(f"[CUSTOM-REPORT-BUILDER] Populated QuickBase tree with {len(self.qb_schema_data)} apps")
    
    def populate_object_tree(self):
        """Populate the object tree widget"""
        self.object_tree.clear()
        
        # Create categories
        standard_item = QTreeWidgetItem(self.object_tree, ["Standard Objects", ""])
        custom_item = QTreeWidgetItem(self.object_tree, ["Custom Objects", ""])
        
        # Add objects to categories
        for obj in self.objects_data:
            if not obj.get('queryable', False):
                continue  # Skip non-queryable objects
            
            item_data = [obj.get('label', obj.get('name')), obj.get('name')]
            
            if obj.get('custom', False):
                item = QTreeWidgetItem(custom_item, item_data)
            else:
                item = QTreeWidgetItem(standard_item, item_data)
            
            item.setData(0, Qt.ItemDataRole.UserRole, obj)
        
        # Expand categories
        self.object_tree.expandAll()
        
        logger.info(f"[CUSTOM-REPORT-BUILDER] Populated tree with {len(self.objects_data)} objects")
    
    def filter_objects(self, text):
        """Filter objects based on search text"""
        for i in range(self.object_tree.topLevelItemCount()):
            category = self.object_tree.topLevelItem(i)
            category_visible = False
            
            for j in range(category.childCount()):
                child = category.child(j)
                object_data = child.data(0, Qt.ItemDataRole.UserRole)
                
                if not text:
                    child.setHidden(False)
                    category_visible = True
                else:
                    # Search in both label and API name
                    label = object_data.get('label', '').lower()
                    name = object_data.get('name', '').lower()
                    text_lower = text.lower()
                    
                    visible = text_lower in label or text_lower in name
                    child.setHidden(not visible)
                    if visible:
                        category_visible = True
            
            category.setHidden(not category_visible)
    
    def on_object_selected(self, item, column):
        """Handle object/table selection"""
        object_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not object_data:
            return

        if self.current_data_source == 'salesforce':
            self.handle_salesforce_object_selection(object_data)
        elif self.current_data_source == 'quickbase':
            self.handle_quickbase_table_selection(object_data)

    def handle_salesforce_object_selection(self, object_data):
        """Handle Salesforce object selection"""
        object_name = object_data.get('name')
        if not object_name:
            return

        logger.info(f"[CUSTOM-REPORT-BUILDER] Selected Salesforce object: {object_name}")

        # Update object info
        info_text = f"<b>{object_data.get('label', object_name)}</b><br>"
        info_text += f"API Name: {object_name}<br>"
        info_text += f"Type: {'Custom' if object_data.get('custom') else 'Standard'}<br>"
        info_text += f"Queryable: {'Yes' if object_data.get('queryable') else 'No'}<br>"
        info_text += f"Searchable: {'Yes' if object_data.get('searchable') else 'No'}"

        self.object_info_label.setText(info_text)

        # Load fields for this object
        self.load_salesforce_object_fields(object_name)

    def handle_quickbase_table_selection(self, table_data):
        """Handle QuickBase table selection"""
        if table_data.get('type') != 'table':
            return  # Only handle table selections, not apps

        table_name = table_data.get('table_name')
        table_id = table_data.get('table_id')
        app_id = table_data.get('app_id')

        if not table_id:
            return

        logger.info(f"[CUSTOM-REPORT-BUILDER] Selected QuickBase table: {table_name}")

        # Update object info
        info_text = f"<b>{table_name}</b><br>"
        info_text += f"Table ID: {table_id}<br>"
        info_text += f"Application ID: {app_id}<br>"
        info_text += f"Type: QuickBase Table"

        self.object_info_label.setText(info_text)

        # Store current selection
        self.current_table_data = table_data

        # Load fields for this table
        self.load_quickbase_table_fields(table_data)
    
    def load_salesforce_object_fields(self, object_name):
        """Load fields for the selected Salesforce object"""
        self.fields_list.clear()
        self.selected_fields.clear()
        self.sort_field_combo.clear()
        self.sort_field_combo.addItem("No Sorting")
        
        # Show loading message
        loading_item = QListWidgetItem("Loading fields...")
        loading_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.fields_list.addItem(loading_item)
        
        # Load fields in background
        if self.fields_worker and self.fields_worker.isRunning():
            self.fields_worker.quit()
            self.fields_worker.wait()
        
        self.fields_worker = ObjectFieldsWorker(self.sf_api, self.cache_manager, object_name)
        self.fields_worker.fields_loaded.connect(self.on_fields_loaded)
        self.fields_worker.error_occurred.connect(self.on_fields_error)
        self.fields_worker.start()
    
    def on_fields_loaded(self, object_name, description):
        """Handle fields loaded for object"""
        self.current_object_description = description
        self.fields_list.clear()
        
        fields = description.get('fields', [])
        
        # Populate fields list
        for field in fields:
            item = QListWidgetItem()
            item.setText(f"{field.get('label', field.get('name'))} ({field.get('name')})")
            item.setData(Qt.ItemDataRole.UserRole, field)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            
            # Add type indicator
            field_type = field.get('type', '')
            if field.get('custom'):
                item.setText(item.text() + f" - {field_type} [Custom]")
            else:
                item.setText(item.text() + f" - {field_type}")
            
            self.fields_list.addItem(item)
            
            # Add to sort combo
            self.sort_field_combo.addItem(f"{field.get('label', field.get('name'))}", field.get('name'))
        
        # Update visual builder components only if they exist and tab is active
        self.update_visual_builder_components(object_name, description, fields)
        
        # Enable report building
        self.run_report_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        
        logger.info(f"[CUSTOM-REPORT-BUILDER] Loaded {len(fields)} fields for {object_name}")

    def load_quickbase_table_fields(self, table_data):
        """Load fields for the selected QuickBase table"""
        self.fields_list.clear()
        self.selected_fields.clear()
        self.sort_field_combo.clear()
        self.sort_field_combo.addItem("No Sorting")

        schema = table_data.get('schema', {})
        fields = schema.get('fields', [])

        if not fields:
            logger.warning("[CUSTOM-REPORT-BUILDER] No fields found in table schema")
            return

        # Populate fields list
        for field in fields:
            item = QListWidgetItem()
            field_name = field.get('label', field.get('name', 'Unknown Field'))
            field_id = field.get('id', '')
            field_type = field.get('fieldType', 'text')

            item.setText(f"{field_name} (ID: {field_id}) - {field_type}")
            item.setData(Qt.ItemDataRole.UserRole, field)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)

            self.fields_list.addItem(item)

            # Add to sort combo
            self.sort_field_combo.addItem(field_name, field_id)

        # Enable report building
        self.run_report_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)

        logger.info(f"[CUSTOM-REPORT-BUILDER] Loaded {len(fields)} fields for QuickBase table")

    def update_visual_builder_components(self, object_name: str, description: dict, fields: list):
        """Update visual builder components efficiently"""
        if not VISUAL_BUILDER_AVAILABLE or not hasattr(self, 'field_palette'):
            return
        
        # Check if we're updating the same object to avoid unnecessary work
        current_visual_object = getattr(self, '_current_visual_object', None)
        if current_visual_object == object_name:
            logger.debug(f"[CUSTOM-REPORT-BUILDER] Skipping visual builder update - same object: {object_name}")
            return
        
        try:
            # Update relationship explorer
            if hasattr(self, 'relationship_explorer'):
                self.relationship_explorer.set_object_metadata(object_name, description)
                self.relationship_explorer.set_current_object(object_name)
                logger.debug(f"[CUSTOM-REPORT-BUILDER] Updated relationship explorer for {object_name}")
            
            # Update field palette with related fields enabled
            self.field_palette.set_fields_data(fields, include_related=True)
            self.visual_canvas.set_current_object(description)
            
            # Track current visual object to prevent duplicate updates
            self._current_visual_object = object_name
            
        except Exception as e:
            logger.warning(f"[CUSTOM-REPORT-BUILDER] Failed to update visual builder components: {e}")
    
    def on_fields_error(self, object_name, error):
        """Handle error loading fields"""
        self.fields_list.clear()
        error_item = QListWidgetItem(f"Error loading fields: {error}")
        error_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.fields_list.addItem(error_item)
    
    def filter_fields(self):
        """Filter fields based on search and type"""
        search_text = self.field_search.text().lower()
        field_type_filter = self.field_type_combo.currentText()
        
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            field_data = item.data(Qt.ItemDataRole.UserRole)
            
            if not field_data:
                continue
            
            # Text filter
            text_match = True
            if search_text:
                label = field_data.get('label', '').lower()
                name = field_data.get('name', '').lower()
                text_match = search_text in label or search_text in name
            
            # Type filter
            type_match = True
            if field_type_filter != 'All Types':
                if field_type_filter == 'Custom':
                    type_match = field_data.get('custom', False)
                elif field_type_filter == 'Standard':
                    type_match = not field_data.get('custom', False)
                elif field_type_filter == 'Relationships':
                    type_match = len(field_data.get('referenceTo', [])) > 0
            
            item.setHidden(not (text_match and type_match))
    
    def select_all_fields(self):
        """Select all visible fields"""
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.CheckState.Checked)
    
    def clear_all_fields(self):
        """Clear all field selections"""
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
    
    def on_field_selection_changed(self, item):
        """Handle field selection change"""
        self.update_selected_fields()
        self.update_query_preview()
    
    def update_selected_fields(self):
        """Update the list of selected fields"""
        self.selected_fields.clear()
        selected_count = 0
        
        for i in range(self.fields_list.count()):
            item = self.fields_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                field_data = item.data(Qt.ItemDataRole.UserRole)
                if field_data:
                    self.selected_fields.append(field_data)
                    selected_count += 1
        
        self.selected_fields_label.setText(f"Selected: {selected_count} fields")
    
    def add_filter_condition(self):
        """Add a new filter condition"""
        if not self.current_object_description:
            QMessageBox.warning(self, "No Object Selected", "Please select an object first.")
            return
        
        fields = self.current_object_description.get('fields', [])
        if not fields:
            return
        
        # Create new condition widget
        condition_widget = FilterConditionWidget(fields)
        condition_widget.condition_changed.connect(self.update_query_preview)
        self.filters_layout.addWidget(condition_widget)
        
        self.update_query_preview()
    
    def update_query_preview(self):
        """Update the SOQL query preview"""
        if not self.current_object_description or not self.selected_fields:
            self.query_preview.setText("SELECT fields\nFROM object\n-- Select an object and fields to see preview")
            return
        
        # Build SOQL query
        object_name = self.current_object_description.get('name', '')
        
        # SELECT clause
        field_names = [field.get('name') for field in self.selected_fields]
        select_clause = f"SELECT {', '.join(field_names)}"
        
        # FROM clause
        from_clause = f"FROM {object_name}"
        
        # WHERE clause
        where_conditions = []
        for i in range(self.filters_layout.count()):
            widget = self.filters_layout.itemAt(i).widget()
            if isinstance(widget, FilterConditionWidget):
                condition = widget.get_condition()
                if condition:
                    field = condition['field']
                    operator = condition['operator']
                    value = condition['value']
                    
                    # Format value based on operator
                    if operator in ['IN', 'NOT IN']:
                        # Handle list values
                        values = [v.strip() for v in value.split(',')]
                        formatted_values = [f"'{v}'" for v in values]
                        where_conditions.append(f"{field} {operator} ({', '.join(formatted_values)})")
                    elif operator == 'LIKE':
                        where_conditions.append(f"{field} {operator} '%{value}%'")
                    else:
                        # Determine if value needs quotes (non-numeric)
                        try:
                            float(value)
                            where_conditions.append(f"{field} {operator} {value}")
                        except ValueError:
                            where_conditions.append(f"{field} {operator} '{value}'")
        
        where_clause = ""
        if where_conditions:
            where_clause = f"WHERE {' AND '.join(where_conditions)}"
        
        # ORDER BY clause
        order_clause = ""
        sort_field = self.sort_field_combo.currentData()
        if sort_field:
            sort_order = self.sort_order_combo.currentText()
            order_clause = f"ORDER BY {sort_field} {sort_order}"
        
        # LIMIT clause
        limit_clause = f"LIMIT {self.row_limit_spin.value()}"
        
        # Combine clauses
        query_parts = [select_clause, from_clause]
        if where_clause:
            query_parts.append(where_clause)
        if order_clause:
            query_parts.append(order_clause)
        query_parts.append(limit_clause)
        
        query = '\n'.join(query_parts)
        self.query_preview.setText(query)
    
    def preview_query(self):
        """Preview the query results"""
        query = self.query_preview.toPlainText().strip()
        if not query or "SELECT fields" in query:
            QMessageBox.warning(self, "Invalid Query", "Please build a valid query first.")
            return
        
        # Show preview of first 10 rows
        self.preview_progress.setVisible(True)
        self.preview_progress.setRange(0, 0)
        
        # TODO: Implement preview execution
        QTimer.singleShot(1000, self.on_preview_complete)
    
    def on_preview_complete(self):
        """Handle preview completion"""
        self.preview_progress.setVisible(False)
        
        # Mock preview data for now
        self.preview_table.setRowCount(3)
        self.preview_table.setColumnCount(len(self.selected_fields))
        
        headers = [field.get('label', field.get('name')) for field in self.selected_fields]
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        # Add sample data
        for row in range(3):
            for col, field in enumerate(self.selected_fields):
                sample_value = f"Sample {field.get('name')} {row + 1}"
                item = QTableWidgetItem(sample_value)
                self.preview_table.setItem(row, col, item)
        
        self.preview_table.resizeColumnsToContents()
    
    def create_report(self):
        """Create and emit the report configuration"""
        if not self.selected_fields:
            QMessageBox.warning(self, "Incomplete Configuration", "Please select fields for your report.")
            return

        if self.current_data_source == 'salesforce':
            self.create_salesforce_report()
        elif self.current_data_source == 'quickbase':
            self.create_quickbase_report()

    def create_salesforce_report(self):
        """Create Salesforce SOQL report"""
        if not self.current_object_description:
            QMessageBox.warning(self, "No Object Selected", "Please select a Salesforce object.")
            return

        query = self.query_preview.toPlainText().strip()
        if not query or "SELECT fields" in query:
            QMessageBox.warning(self, "Invalid Query", "Please build a valid SOQL query first.")
            return

        # Build Salesforce report configuration
        report_config = {
            'type': 'custom_soql',
            'api_type': 'salesforce',
            'object_name': self.current_object_description.get('name'),
            'object_label': self.current_object_description.get('label'),
            'query': query,
            'selected_fields': self.selected_fields,
            'row_limit': self.row_limit_spin.value(),
            'title': f"Custom SOQL Report - {self.current_object_description.get('label')}"
        }

        # Emit the report configuration
        self.report_ready.emit(report_config)
        self.accept()

    def create_quickbase_report(self):
        """Create QuickBase query report"""
        if not hasattr(self, 'current_table_data') or not self.current_table_data:
            QMessageBox.warning(self, "No Table Selected", "Please select a QuickBase table.")
            return

        # Build field selection
        selected_field_ids = []
        for field_data in self.selected_fields:
            field_id = field_data.get('id', '')
            if field_id:
                selected_field_ids.append(field_id)

        # Build QuickBase report configuration
        report_config = {
            'type': 'custom_query',
            'api_type': 'quickbase',
            'data_type': 'query',
            'app_id': self.current_table_data.get('app_id'),
            'table_id': self.current_table_data.get('table_id'),
            'table_name': self.current_table_data.get('table_name'),
            'select_fields': selected_field_ids,
            'selected_fields': self.selected_fields,
            'filters': self.get_quickbase_filters(),
            'row_limit': self.row_limit_spin.value(),
            'title': f"Custom QuickBase Query - {self.current_table_data.get('table_name')}"
        }

        # Emit the report configuration
        self.report_ready.emit(report_config)
        self.accept()

    def get_quickbase_filters(self):
        """Build QuickBase filters from the UI"""
        # This would extract filters from the filter conditions UI
        # For now, return empty list - can be enhanced later
        return []
    
    def test_visual_query(self, query: str):
        """Test a query from the visual builder"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QDialogButtonBox
        from PyQt6.QtCore import QTimer
        
        # Create a preview dialog
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Test Query Results")
        preview_dialog.setModal(True)
        preview_dialog.resize(600, 400)
        
        layout = QVBoxLayout(preview_dialog)
        
        # Results display
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setPlainText("Executing query...\n\n" + query)
        layout.addWidget(results_text)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(preview_dialog.accept)
        layout.addWidget(button_box)
        
        # Show dialog
        preview_dialog.show()
        
        # Execute query after a short delay to show the dialog
        QTimer.singleShot(100, lambda: self.execute_test_query(query, results_text))
    
    def execute_test_query(self, query: str, results_widget: QTextEdit):
        """Execute the test query and display results"""
        try:
            # Create and start worker using SalesforceConnectionWorker
            from src.ui.workers import SalesforceConnectionWorker
            
            self.test_query_worker = SalesforceConnectionWorker("execute_soql", self.sf_api, query=query, source_name="Test Query")
            
            # Connect signals
            self.test_query_worker.report_data_loaded.connect(
                lambda df, source: self.display_test_results(df, results_widget, query)
            )
            self.test_query_worker.error_occurred.connect(
                lambda operation, error: results_widget.setPlainText(f"Query Error:\n\n{error}\n\nQuery:\n{query}")
            )
            
            # Start worker
            self.test_query_worker.start()
            
        except Exception as e:
            logger.error(f"[VISUAL-BUILDER] Error executing test query: {e}")
            results_widget.setPlainText(f"Error: {str(e)}\n\nQuery:\n{query}")
    
    def display_test_results(self, df, results_widget: QTextEdit, query: str):
        """Display test query results"""
        try:
            if df is None or df.is_empty():
                results_widget.setPlainText(f"Query returned no results.\n\nQuery:\n{query}")
                return
            
            # Format results
            result_text = f"Query returned {len(df)} row(s)\n\n"
            
            # Show column headers
            columns = df.columns
            result_text += " | ".join(columns) + "\n"
            result_text += "-" * (len(" | ".join(columns))) + "\n"
            
            # Show first 10 rows
            for i in range(min(10, len(df))):
                row_values = []
                for col in columns:
                    val = str(df[col][i])
                    # Truncate long values
                    if len(val) > 30:
                        val = val[:27] + "..."
                    row_values.append(val)
                result_text += " | ".join(row_values) + "\n"
            
            if len(df) > 10:
                result_text += f"\n... and {len(df) - 10} more rows\n"
            
            result_text += f"\n\nQuery:\n{query}"
            results_widget.setPlainText(result_text)
            
        except Exception as e:
            logger.error(f"[VISUAL-BUILDER] Error displaying results: {e}")
            results_widget.setPlainText(f"Error displaying results: {str(e)}\n\nQuery:\n{query}")
    
    def on_visual_field_double_clicked(self, field_data: dict):
        """Handle field double-click in visual builder"""
        logger.info(f"[VISUAL-BUILDER] Field double-clicked: {field_data.get('name', 'Unknown')}")
        # For now, just log. Could open field configuration dialog in the future
    
    def on_visual_query_changed(self, query_data: dict):
        """Handle query changes from visual builder"""
        if not VISUAL_BUILDER_AVAILABLE:
            return
        
        # Update the main query preview with the visual builder's query
        soql_query = query_data.get('soql', '')
        if soql_query and soql_query != self.query_preview.toPlainText():
            self.query_preview.setPlainText(soql_query)
            logger.debug("[VISUAL-BUILDER] Updated main query preview from visual builder")
    
    def on_test_query_requested(self, query: str):
        """Handle test query request from visual builder"""
        if not VISUAL_BUILDER_AVAILABLE:
            return
        
        logger.info("[VISUAL-BUILDER] Test query requested")
        
        # Show a quick preview dialog with query results
        self.test_visual_query(query)
    
    def on_relationship_selected(self, relationship_data: dict):
        """Handle relationship selection from relationship explorer"""
        if not VISUAL_BUILDER_AVAILABLE:
            return
        
        relationship_type = relationship_data.get('type', '')
        logger.info(f"[VISUAL-BUILDER] Relationship selected: {relationship_type}")
        
        # For now, just log the relationship selection
        # Could extend to auto-populate join builder or highlight related fields
        # This provides a hook for future enhancements
    
    def sync_visual_to_form(self):
        """Sync visual builder selections to form-based builder"""
        if not VISUAL_BUILDER_AVAILABLE or not hasattr(self, 'visual_canvas'):
            return
        
        try:
            # Get visual builder data
            query_data = self.visual_canvas.get_current_query_data()
            selected_fields = query_data.get('fields', [])
            
            # Update form-based field selections
            for i in range(self.fields_list.count()):
                item = self.fields_list.item(i)
                field_data = item.data(Qt.ItemDataRole.UserRole)
                
                # Check if this field is selected in visual builder
                is_selected = any(
                    vf.get('name') == field_data.get('name') 
                    for vf in selected_fields
                )
                
                item.setCheckState(
                    Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked
                )
            
            # Update selected fields list
            self.update_selected_fields()
            
            # Update query preview
            self.update_query_preview()
            
            QMessageBox.information(self, "Sync Complete", 
                                  f"Synced {len(selected_fields)} fields from visual builder to form builder.")
            
            logger.info(f"[VISUAL-BUILDER] Synced {len(selected_fields)} fields to form builder")
            
        except Exception as e:
            logger.error(f"[VISUAL-BUILDER] Error syncing visual to form: {e}")
            QMessageBox.critical(self, "Sync Error", f"Failed to sync: {str(e)}")
    
    def sync_form_to_visual(self):
        """Sync form-based builder selections to visual builder"""
        if not VISUAL_BUILDER_AVAILABLE or not hasattr(self, 'visual_canvas'):
            return
        
        try:
            # This would be more complex - would need to:
            # 1. Clear visual canvas
            # 2. Add selected fields from form to visual canvas
            # 3. Add filter conditions from form to visual canvas
            
            # For now, just show a placeholder message
            field_count = len(self.selected_fields)
            QMessageBox.information(self, "Sync from Form", 
                                  f"Form to visual sync not yet fully implemented.\\n"
                                  f"Form currently has {field_count} selected fields.")
            
            logger.info(f"[VISUAL-BUILDER] Form to visual sync requested ({field_count} fields)")
            
        except Exception as e:
            logger.error(f"[VISUAL-BUILDER] Error syncing form to visual: {e}")
            QMessageBox.critical(self, "Sync Error", f"Failed to sync: {str(e)}")