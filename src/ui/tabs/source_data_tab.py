"""
Source Data Tab - Contains the unified data source tree and data viewing functionality
"""
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLineEdit, QLabel, QFrame, QTabWidget, QMessageBox, QDateEdit,
    QMenu, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QAction
import qtawesome as qta

from src.ui.data_grid import InteractiveDataGrid
from src.ui.dialogs.custom_report_builder import CustomReportBuilderDialog
from src.ui.managers.metadata_cache_manager import MetadataCacheManager

logger = logging.getLogger(__name__)

class SourceDataTab(QWidget):
    """Tab containing the source data tree and viewing functionality"""
    
    # Signals
    load_data_requested = pyqtSignal(dict)  # Emitted when user wants to load data
    show_salesforce_connect_requested = pyqtSignal()  # Request to show SF connect dialog
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.metadata_cache_manager = MetadataCacheManager()
        self.report_metadata_cache = {}  # Cache for report metadata
        self.metadata_worker = None  # Worker for fetching metadata
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the source data tab UI"""
        # Main horizontal layout with splitter
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left sidebar
        self.setup_sidebar(splitter)
        
        # Right content area
        self.setup_content_area(splitter)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 0)  # Sidebar fixed
        splitter.setStretchFactor(1, 1)  # Content expandable
        splitter.setSizes([300, 900])
        
    def setup_sidebar(self, parent_splitter):
        """Setup left sidebar with data source navigation"""
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        
        # Connection status frame
        status_frame = QFrame()
        status_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        status_layout = QVBoxLayout(status_frame)
        
        status_layout.addWidget(QLabel("Connection Status:"))
        
        # Connection status for both APIs
        self.connection_status = QLabel("Connecting...")
        self.connection_status.setStyleSheet("color: orange; font-weight: bold;")
        status_layout.addWidget(self.connection_status)
        
        sidebar_layout.addWidget(status_frame)
        
        # Data source tree
        tree_frame = QFrame()
        tree_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        tree_layout = QVBoxLayout(tree_frame)
        
        tree_layout.addWidget(QLabel("Available Data Sources:"))
        
        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search data sources...")
        self.search_box.textChanged.connect(self.filter_tree)
        tree_layout.addWidget(self.search_box)
        
        # Tree widget
        self.data_tree = QTreeWidget()
        self.data_tree.setHeaderLabels(["Name", "Type", "Modified"])
        self.data_tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        # Auto-resize name column when items are expanded/collapsed
        self.data_tree.itemExpanded.connect(self.auto_resize_name_column)
        self.data_tree.itemCollapsed.connect(self.auto_resize_name_column)
        
        tree_layout.addWidget(self.data_tree)
        
        # Date range selector
        date_frame = QFrame()
        date_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        date_layout = QVBoxLayout(date_frame)
        
        date_layout.addWidget(QLabel("Date Range Filter:"))
        
        # Date field selector
        date_field_layout = QHBoxLayout()
        date_field_layout.addWidget(QLabel("Date Field:"))
        self.date_field_combo = QComboBox()
        self.date_field_combo.addItem("Select a report first...", "")
        self.date_field_combo.setEnabled(False)
        date_field_layout.addWidget(self.date_field_combo)
        date_layout.addLayout(date_field_layout)
        
        # Start date
        start_date_layout = QHBoxLayout()
        start_date_layout.addWidget(QLabel("From:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))  # Default to last month
        start_date_layout.addWidget(self.start_date)
        date_layout.addLayout(start_date_layout)
        
        # End date
        end_date_layout = QHBoxLayout()
        end_date_layout.addWidget(QLabel("To:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())  # Default to today
        end_date_layout.addWidget(self.end_date)
        date_layout.addLayout(end_date_layout)
        
        tree_layout.addWidget(date_frame)
        
        # Load data button
        self.load_btn = QPushButton("Load Selected Data")
        self.load_btn.setIcon(qta.icon('fa5s.download'))
        self.load_btn.clicked.connect(self.load_selected_data)
        self.load_btn.setEnabled(False)
        tree_layout.addWidget(self.load_btn)
        
        # Custom report builder button
        self.custom_report_btn = QPushButton("Build Custom Report")
        self.custom_report_btn.setIcon(qta.icon('fa5s.magic'))
        self.custom_report_btn.clicked.connect(self.open_custom_report_builder)
        self.custom_report_btn.setEnabled(False)  # Will be enabled when Salesforce is connected
        self.custom_report_btn.setToolTip("Create custom reports with visual query builder")
        tree_layout.addWidget(self.custom_report_btn)
        
        # Enable load button when item is selected
        self.data_tree.itemClicked.connect(self.on_tree_item_clicked)
        
        sidebar_layout.addWidget(tree_frame)
        
        parent_splitter.addWidget(sidebar_widget)
        
    def setup_content_area(self, parent_splitter):
        """Setup main content area with tabs"""
        main_content = QWidget()
        content_layout = QVBoxLayout(main_content)
        
        # Tab widget for data views
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        
        # Enable context menu for tabs
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.customContextMenuRequested.connect(self.show_tab_context_menu)
        
        content_layout.addWidget(self.tab_widget)
        
        # Welcome tab
        self.setup_welcome_tab()
        
        parent_splitter.addWidget(main_content)
        
    def setup_welcome_tab(self):
        """Setup welcome tab"""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        # Welcome message
        welcome_label = QLabel(
            "<h2>Welcome to Multi-API Data Integration</h2>"
            "<p>Select a data source from the tree on the left to begin.</p>"
            "<p>Double-click or use the 'Load Selected Data' button to load data.</p>"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setWordWrap(True)
        layout.addWidget(welcome_label)
        
        self.tab_widget.addTab(welcome_widget, "Welcome")
        
    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        # Enable load button only for actual data sources
        if data and not data.get('is_parent') and not data.get('is_folder') and not data.get('action'):
            self.load_btn.setEnabled(True)
            
            # If this is a Salesforce report, populate date fields
            if data.get('api_type') == 'salesforce' and data.get('type') == 'report':
                self.populate_date_fields_for_report(data)
            else:
                # Reset date field dropdown for non-Salesforce items
                self.reset_date_field_dropdown()
        else:
            self.load_btn.setEnabled(False)
            self.reset_date_field_dropdown()
            
    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double-click on tree item"""
        # Check if this is a special action item
        data = item.data(0, Qt.ItemDataRole.UserRole)

        if data and data.get('action') == 'connect':
            if data.get('api_type') == 'salesforce':
                self.show_salesforce_connect_requested.emit()
            return

        # Check if this is a QuickBase custom query builder
        if data and data.get('type') == 'query_builder' and data.get('api_type') == 'quickbase':
            self.open_custom_report_builder_for_quickbase()
            return

        # Otherwise, load the data
        self.load_selected_data()
    
    def populate_date_fields_for_report(self, report_data: dict):
        """Populate date field dropdown with available date fields from the report"""
        try:
            report_id = report_data.get('id', '')
            if not report_id:
                self.reset_date_field_dropdown()
                return
            
            # Check if we have cached metadata
            if report_id in self.report_metadata_cache:
                logger.info(f"[SOURCE-DATA-TAB] Using cached metadata for report: {report_data.get('name', 'Unknown')}")
                self._populate_date_fields_from_metadata(self.report_metadata_cache[report_id])
                return
            
            # Show loading state
            self.date_field_combo.clear()
            self.date_field_combo.setEnabled(False)
            self.date_field_combo.addItem("Loading date fields...", "")
            
            # Check if we have Salesforce API connection
            if not hasattr(self.main_window, 'sf_api') or not self.main_window.sf_api:
                logger.warning("[SOURCE-DATA-TAB] No Salesforce API connection available")
                self._populate_with_fallback_fields()
                return
            
            # Create worker to fetch metadata
            from src.ui.workers import SalesforceConnectionWorker
            self.metadata_worker = SalesforceConnectionWorker(
                "get_report_metadata",
                self.main_window.sf_api,
                report_id=report_id
            )
            
            # Connect signals
            self.metadata_worker.report_metadata_loaded.connect(
                lambda metadata, rid: self._on_report_metadata_loaded(metadata, rid, report_data.get('name', 'Unknown'))
            )
            self.metadata_worker.error_occurred.connect(
                lambda op, err: self._on_metadata_error(op, err)
            )
            
            # Start worker
            self.metadata_worker.start()
            logger.info(f"[SOURCE-DATA-TAB] Fetching metadata for report: {report_data.get('name', 'Unknown')}")
            
        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error populating date fields: {e}")
            self._populate_with_fallback_fields()
    
    def reset_date_field_dropdown(self):
        """Reset the date field dropdown to disabled state"""
        self.date_field_combo.clear()
        self.date_field_combo.addItem("Select a report first...", "")
        self.date_field_combo.setEnabled(False)
        
    def load_selected_data(self):
        """Load selected data source"""
        current_item = self.data_tree.currentItem()
        if not current_item:
            QMessageBox.information(self, "No Selection", "Please select a data source to load.")
            return
            
        # Get data source info
        data_source = current_item.data(0, Qt.ItemDataRole.UserRole)
        if not data_source:
            QMessageBox.information(self, "Invalid Selection", "Please select a data source.")
            return
            
        # Check if this is a parent node or folder (not loadable)
        if data_source.get('is_parent') or data_source.get('is_folder'):
            QMessageBox.information(self, "Invalid Selection", "Please select a specific data source.")
            return
            
        # Add date range to data source info
        data_source['start_date'] = self.start_date.date().toString('yyyy-MM-dd')
        data_source['end_date'] = self.end_date.date().toString('yyyy-MM-dd')
        
        # Add selected date field for Salesforce reports
        if data_source.get('api_type') == 'salesforce' and data_source.get('type') == 'report':
            selected_date_field = self.date_field_combo.currentData()
            if selected_date_field:
                data_source['date_field'] = selected_date_field
                logger.info(f"[SOURCE-DATA-TAB] Using date field: {selected_date_field} for report filtering")
        
        # Emit signal to load data
        self.load_data_requested.emit(data_source)
        
    def add_data_tab(self, dataframe, title: str):
        """Add a new tab with data grid"""
        data_grid = InteractiveDataGrid(dataframe, title)
        tab_index = self.tab_widget.addTab(data_grid, title)
        self.tab_widget.setCurrentIndex(tab_index)
        return data_grid
        
    def close_tab(self, index: int):
        """Close tab at index"""
        if index > 0:  # Don't close welcome tab
            self.tab_widget.removeTab(index)
            
    def update_connection_status(self, status_text: str, color: str):
        """Update the connection status display"""
        self.connection_status.setText(status_text)
        self.connection_status.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def auto_resize_name_column(self, item=None):
        """Auto-resize the name column to fit content when items are expanded/collapsed"""
        try:
            # Resize the first column (Name) to fit contents
            self.data_tree.resizeColumnToContents(0)
        except Exception as e:
            # Silently handle any resize errors
            pass
        
    def filter_tree(self, text: str):
        """Filter tree items based on search text"""
        search_text = text.lower()
        
        # If search is empty, collapse all and show everything
        if not search_text:
            self.data_tree.collapseAll()
            # Show all items
            for i in range(self.data_tree.topLevelItemCount()):
                api_parent = self.data_tree.topLevelItem(i)
                api_parent.setHidden(False)
                for j in range(api_parent.childCount()):
                    child_item = api_parent.child(j)
                    child_item.setHidden(False)
                    # If it's a folder, show all its children
                    for k in range(child_item.childCount()):
                        child_item.child(k).setHidden(False)
            return
        
        # Search logic for populated tree
        for i in range(self.data_tree.topLevelItemCount()):
            api_parent = self.data_tree.topLevelItem(i)
            api_visible = False
            
            for j in range(api_parent.childCount()):
                child_item = api_parent.child(j)
                child_visible = False
                
                # Check if this child is a folder (for Salesforce)
                if child_item.childCount() > 0:
                    # It's a folder with reports
                    for k in range(child_item.childCount()):
                        report_item = child_item.child(k)
                        report_name = report_item.text(0).lower()
                        
                        if search_text in report_name:
                            report_item.setHidden(False)
                            child_visible = True
                        else:
                            report_item.setHidden(True)
                    
                    child_item.setHidden(not child_visible)
                    if child_visible:
                        api_visible = True
                        child_item.setExpanded(True)
                else:
                    # It's a direct data source (for WooCommerce)
                    item_name = child_item.text(0).lower()
                    if search_text in item_name:
                        child_item.setHidden(False)
                        api_visible = True
                    else:
                        child_item.setHidden(True)
            
            # Show/hide the API parent based on visible children
            api_parent.setHidden(not api_visible)
            if api_visible:
                api_parent.setExpanded(True)
    
    def open_custom_report_builder(self):
        """Open the custom report builder dialog"""
        # Check if Salesforce API is available
        if not hasattr(self.main_window, 'sf_api') or not self.main_window.sf_api:
            QMessageBox.warning(self, "Salesforce Not Connected", 
                              "Please connect to Salesforce first to use the custom report builder.")
            return
        
        # Check if Salesforce is actually connected
        if not getattr(self.main_window, 'sf_connected', False):
            QMessageBox.warning(self, "Salesforce Not Connected", 
                              "Please ensure Salesforce connection is active before building custom reports.")
            return
        
        try:
            # Open the custom report builder dialog
            dialog = CustomReportBuilderDialog(
                self.main_window.sf_api, 
                self.metadata_cache_manager, 
                self
            )
            
            # Connect signal to handle report creation
            dialog.report_ready.connect(self.on_custom_report_ready)
            
            # Show dialog
            dialog.exec()
            
        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error opening custom report builder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open custom report builder: {str(e)}")

    def open_custom_report_builder_for_quickbase(self):
        """Open custom report builder specifically for QuickBase"""
        try:
            # Open the custom report builder dialog (it will detect QuickBase automatically)
            dialog = CustomReportBuilderDialog(
                self.main_window.sf_api if hasattr(self.main_window, 'sf_api') else None,
                self.metadata_cache_manager,
                self
            )

            # Connect signal to handle report creation
            dialog.report_ready.connect(self.on_custom_report_ready)

            # Show dialog
            dialog.exec()

        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error opening QuickBase custom report builder: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open QuickBase custom report builder: {str(e)}")

    def on_custom_report_ready(self, report_config):
        """Handle custom report configuration from the builder"""
        try:
            api_type = report_config.get('api_type', 'salesforce')
            logger.info(f"[SOURCE-DATA-TAB] Custom {api_type} report ready: {report_config.get('title', 'Unknown')}")

            if api_type == 'salesforce':
                # Create Salesforce data source
                data_source = {
                    'api_type': 'salesforce',
                    'type': 'custom_report',
                    'name': report_config.get('title', 'Custom Report'),
                    'id': report_config.get('query'),  # Use query as ID
                    'query': report_config.get('query'),
                    'object_name': report_config.get('object_name'),
                    'selected_fields': report_config.get('selected_fields', []),
                    'start_date': None,  # Custom reports don't use date filters by default
                    'end_date': None
                }
            elif api_type == 'quickbase':
                # Create QuickBase data source
                data_source = {
                    'api_type': 'quickbase',
                    'data_type': 'query',
                    'type': 'custom_query',
                    'name': report_config.get('title', 'Custom QuickBase Query'),
                    'id': f"qb_custom_{report_config.get('table_id', '')}",
                    'app_id': report_config.get('app_id'),
                    'table_id': report_config.get('table_id'),
                    'table_name': report_config.get('table_name'),
                    'select_fields': report_config.get('select_fields', []),
                    'selected_fields': report_config.get('selected_fields', []),
                    'filters': report_config.get('filters', []),
                    'query': report_config.get('filters', {}),  # Use filters as query
                    'start_date': None,
                    'end_date': None
                }
            else:
                raise ValueError(f"Unsupported API type: {api_type}")

            # Emit the load data request
            self.load_data_requested.emit(data_source)

        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error handling custom report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to process custom report: {str(e)}")
    
    def enable_custom_report_builder(self, enabled: bool):
        """Enable or disable the custom report builder button"""
        self.custom_report_btn.setEnabled(enabled)
        if enabled:
            logger.info("[SOURCE-DATA-TAB] Custom report builder enabled")
        else:
            logger.info("[SOURCE-DATA-TAB] Custom report builder disabled")
    
    def show_tab_context_menu(self, position):
        """Show context menu for tab headers"""
        # Get the tab index at the clicked position
        tab_bar = self.tab_widget.tabBar()
        tab_index = tab_bar.tabAt(position)
        
        if tab_index < 0 or tab_index == 0:  # Skip if no tab or welcome tab
            return
        
        # Get the tab widget and check if it's a data grid
        tab_widget = self.tab_widget.widget(tab_index)
        if not hasattr(tab_widget, 'get_current_data'):
            return
        
        # Create context menu
        menu = QMenu(self)
        
        # Get tab name
        tab_name = self.tab_widget.tabText(tab_index)
        
        # Visualize data action
        visualize_action = QAction(f"Visualize '{tab_name}'", self)
        visualize_action.setIcon(qta.icon('fa5s.chart-bar'))
        visualize_action.triggered.connect(lambda: self.visualize_tab_data(tab_index))
        menu.addAction(visualize_action)
        
        menu.addSeparator()
        
        # Close tab action
        close_action = QAction(f"Close '{tab_name}'", self)
        close_action.setIcon(qta.icon('fa5s.times'))
        close_action.triggered.connect(lambda: self.close_tab(tab_index))
        menu.addAction(close_action)
        
        # Show menu
        menu.exec(self.tab_widget.mapToGlobal(position))
    
    def visualize_tab_data(self, tab_index: int):
        """Send tab data to visualization"""
        if tab_index < 0 or tab_index >= self.tab_widget.count():
            return
        
        tab_widget = self.tab_widget.widget(tab_index)
        if hasattr(tab_widget, 'visualize_data'):
            tab_widget.visualize_data()
        else:
            logger.warning(f"[SOURCE-DATA-TAB] Tab at index {tab_index} doesn't support visualization")
    
    def _on_report_metadata_loaded(self, metadata: dict, report_id: str, report_name: str):
        """Handle successful metadata loading"""
        try:
            # Cache the metadata
            self.report_metadata_cache[report_id] = metadata
            logger.info(f"[SOURCE-DATA-TAB] Cached metadata for report: {report_name}")
            
            # Populate fields from metadata
            self._populate_date_fields_from_metadata(metadata)
            
            # Clean up worker
            if self.metadata_worker:
                self.metadata_worker.deleteLater()
                self.metadata_worker = None
                
        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error handling metadata: {e}")
            self._populate_with_fallback_fields()
    
    def _on_metadata_error(self, operation: str, error: str):
        """Handle metadata loading error"""
        logger.error(f"[SOURCE-DATA-TAB] Failed to load report metadata: {error}")
        self._populate_with_fallback_fields()
        
        # Clean up worker
        if self.metadata_worker:
            self.metadata_worker.deleteLater()
            self.metadata_worker = None
    
    def _populate_date_fields_from_metadata(self, metadata: dict):
        """Populate date fields from report metadata"""
        try:
            # Clear and enable dropdown
            self.date_field_combo.clear()
            self.date_field_combo.setEnabled(True)
            
            # Extract date fields from metadata
            date_fields = []
            
            # Primary location: reportExtendedMetadata.detailColumnInfo
            report_extended_metadata = metadata.get('reportExtendedMetadata', {})
            detail_column_info = report_extended_metadata.get('detailColumnInfo', {})
            
            # Find all date/datetime fields from detailColumnInfo
            for field_name, field_info in detail_column_info.items():
                data_type = field_info.get('dataType', '').lower()
                if data_type in ['date', 'datetime']:
                    label = field_info.get('label', field_name)
                    date_fields.append((label, field_name))
                    logger.debug(f"[SOURCE-DATA-TAB] Found date field: {field_name} ({label}) - type: {data_type}")
            
            # Fallback: check reportMetadata.reportType.columns if no fields found
            if not date_fields:
                logger.debug("[SOURCE-DATA-TAB] No fields in detailColumnInfo, checking reportType.columns")
                report_metadata = metadata.get('reportMetadata', {})
                report_type = report_metadata.get('reportType', {})
                columns = report_type.get('columns', {})
                
                for field_name, field_info in columns.items():
                    data_type = field_info.get('dataType', '').lower()
                    if data_type in ['date', 'datetime']:
                        label = field_info.get('label', field_name)
                        date_fields.append((label, field_name))
            
            # Sort fields alphabetically by label
            date_fields.sort(key=lambda x: x[0])
            
            # Add fields to dropdown
            if date_fields:
                # Add default option
                self.date_field_combo.addItem("Select date field...", "")
                
                # Add all date fields
                for label, api_name in date_fields:
                    self.date_field_combo.addItem(f"{label} ({api_name})", api_name)
                
                # Try to set a sensible default
                # Look for common fields in order of preference
                common_defaults = ['CreatedDate', 'CREATED_DATE', 'LastModifiedDate', 'LAST_MODIFIED_DATE', 'CloseDate', 'CLOSE_DATE']
                default_set = False
                
                for default_field in common_defaults:
                    index = self.date_field_combo.findData(default_field)
                    if index >= 0:
                        self.date_field_combo.setCurrentIndex(index)
                        default_set = True
                        break
                
                # If no common default found, select the first date field
                if not default_set and len(date_fields) > 0:
                    self.date_field_combo.setCurrentIndex(1)  # Skip "Select date field..."
                
                logger.info(f"[SOURCE-DATA-TAB] Populated {len(date_fields)} date fields from metadata")
            else:
                # No date fields found
                self.date_field_combo.addItem("No date fields available", "")
                logger.warning("[SOURCE-DATA-TAB] No date fields found in report metadata")
                
        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error parsing metadata: {e}")
            self._populate_with_fallback_fields()
    
    def _populate_with_fallback_fields(self):
        """Populate with minimal fallback fields when metadata is unavailable"""
        try:
            self.date_field_combo.clear()
            self.date_field_combo.setEnabled(True)
            
            # Minimal set of universal fields
            fallback_fields = [
                ("No date filter", ""),  # Option to disable filtering
                ("Created Date", "CreatedDate"),
                ("Last Modified Date", "LastModifiedDate")
            ]
            
            for label, api_name in fallback_fields:
                self.date_field_combo.addItem(label, api_name)
            
            # Default to no filter
            self.date_field_combo.setCurrentIndex(0)
            
            logger.info("[SOURCE-DATA-TAB] Using fallback date fields")
            
        except Exception as e:
            logger.error(f"[SOURCE-DATA-TAB] Error setting fallback fields: {e}")
            self.reset_date_field_dropdown()
    
    def clear_metadata_cache(self):
        """Clear the report metadata cache (call on API reconnection)"""
        self.report_metadata_cache.clear()
        logger.info("[SOURCE-DATA-TAB] Cleared report metadata cache")