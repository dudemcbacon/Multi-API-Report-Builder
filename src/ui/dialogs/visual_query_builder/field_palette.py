"""
Field palette widget for the visual query builder
"""
import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QScrollArea, QFrame, QPushButton, QComboBox, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
import qtawesome as qta

from .drag_drop_widgets import DraggableFieldWidget

logger = logging.getLogger(__name__)

class FieldPaletteWidget(QWidget):
    """
    Enhanced field palette with search, filtering, and drag-drop capabilities
    """
    
    field_double_clicked = pyqtSignal(dict)  # Emitted when field is double-clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fields_data = []
        self.filtered_fields = []
        self.field_widgets = []
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the field palette UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Field Palette")
        layout.addWidget(header)
        
        # Search and filter controls
        self.setup_controls(layout)
        
        # Fields scroll area
        self.setup_fields_area(layout)
        
        # Field count
        self.field_count_label = QLabel("0 fields")
        layout.addWidget(self.field_count_label)
    
    def setup_controls(self, parent_layout):
        """Setup search and filter controls"""
        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        search_icon = QLabel()
        search_icon.setPixmap(qta.icon('fa5s.search').pixmap(14, 14))
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search fields...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)
        
        controls_layout.addLayout(search_layout)
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Field type filter
        type_label = QLabel("Type:")
        filter_layout.addWidget(type_label)
        
        self.type_filter = QComboBox()
        self.type_filter.addItem("All Types", "")
        self.type_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.type_filter)
        
        filter_layout.addStretch()
        
        # Show only updateable checkbox
        self.updateable_only = QCheckBox("Updateable")
        self.updateable_only.toggled.connect(self.on_filter_changed)
        filter_layout.addWidget(self.updateable_only)
        
        controls_layout.addLayout(filter_layout)
        
        
        parent_layout.addWidget(controls_frame)
    
    def setup_fields_area(self, parent_layout):
        """Setup scrollable fields area"""
        self.fields_scroll = QScrollArea()
        self.fields_scroll.setWidgetResizable(True)
        self.fields_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(5, 5, 5, 5)
        self.fields_layout.setSpacing(2)
        self.fields_layout.addStretch()
        
        self.fields_scroll.setWidget(self.fields_container)
        parent_layout.addWidget(self.fields_scroll)
    
    
    def set_fields_data(self, fields_data: List[Dict[str, Any]], include_related: bool = True):
        """Set the fields data and populate the palette"""
        self.fields_data = fields_data
        
        # Block signals to prevent cascading updates during setup
        self.type_filter.blockSignals(True)
        self.updateable_only.blockSignals(True)
        
        try:
            # If include_related is True, add related object fields
            if include_related and hasattr(self.parent(), 'relationship_explorer'):
                try:
                    related_fields = self.parent().relationship_explorer.get_all_related_fields(max_depth=2)
                    self.fields_data.extend(related_fields)
                    logger.info(f"[FIELD-PALETTE] Added {len(related_fields)} related fields")
                except Exception as e:
                    logger.warning(f"[FIELD-PALETTE] Could not load related fields: {e}")
            
            self.populate_type_filter()
            
        finally:
            # Restore signals
            self.type_filter.blockSignals(False)
            self.updateable_only.blockSignals(False)
        
        # Single filter application after all setup is complete
        self.apply_filters()
        
        logger.info(f"[FIELD-PALETTE] Loaded {len(self.fields_data)} total fields")
    
    def populate_type_filter(self):
        """Populate the type filter dropdown with available types"""
        # Get unique field types
        field_types = set()
        for field in self.fields_data:
            field_type = field.get('type', '').lower()
            if field_type:
                field_types.add(field_type)
        
        # Clear and repopulate
        self.type_filter.clear()
        self.type_filter.addItem("All Types", "")
        
        for field_type in sorted(field_types):
            display_name = field_type.title()
            self.type_filter.addItem(display_name, field_type)
    
    def on_search_changed(self):
        """Handle search text change with debouncing"""
        self.search_timer.stop()
        self.search_timer.start(300)  # 300ms delay
    
    def on_filter_changed(self):
        """Handle filter change"""
        self.apply_filters()
    
    def set_type_filter(self, field_type: str):
        """Set the type filter to a specific type"""
        for i in range(self.type_filter.count()):
            if self.type_filter.itemData(i) == field_type:
                self.type_filter.setCurrentIndex(i)
                break
    
    def apply_filters(self):
        """Apply search and filter criteria to fields"""
        search_text = self.search_input.text().lower()
        selected_type = self.type_filter.currentData()
        updateable_only = self.updateable_only.isChecked()
        
        # Filter fields
        self.filtered_fields = []
        for field in self.fields_data:
            # Search filter
            if search_text:
                searchable_text = ' '.join([
                    field.get('label', ''),
                    field.get('name', ''),
                    field.get('type', '')
                ]).lower()
                if search_text not in searchable_text:
                    continue
            
            # Type filter
            if selected_type and field.get('type', '').lower() != selected_type:
                continue
            
            # Updateable filter
            if updateable_only and not field.get('updateable', False):
                continue
            
            self.filtered_fields.append(field)
        
        self.populate_fields()
        
        logger.debug(f"[FIELD-PALETTE] Filtered to {len(self.filtered_fields)} fields")
    
    def populate_fields(self):
        """Populate the fields container with filtered fields"""
        # Clear existing widgets
        self.clear_field_widgets()
        
        # Add filtered fields
        for field in self.filtered_fields:
            field_widget = DraggableFieldWidget(field)
            field_widget.field_double_clicked.connect(self.field_double_clicked.emit)
            
            self.fields_layout.insertWidget(self.fields_layout.count() - 1, field_widget)
            self.field_widgets.append(field_widget)
        
        # Update count
        self.field_count_label.setText(f"{len(self.filtered_fields)} fields")
        
        # Show empty state if no fields
        if not self.filtered_fields:
            empty_label = QLabel("No fields match the current filters")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.fields_layout.insertWidget(self.fields_layout.count() - 1, empty_label)
            self.field_widgets.append(empty_label)
    
    def clear_field_widgets(self):
        """Clear all field widgets"""
        for widget in self.field_widgets:
            widget.setParent(None)
            widget.deleteLater()
        self.field_widgets.clear()
    
    def get_field_by_name(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get field data by field name"""
        for field in self.fields_data:
            if field.get('name') == field_name:
                return field
        return None
    
    def highlight_field(self, field_name: str):
        """Highlight a specific field in the palette"""
        for widget in self.field_widgets:
            if (isinstance(widget, DraggableFieldWidget) and 
                widget.field_data.get('name') == field_name):
                
                # Scroll to the widget
                self.fields_scroll.ensureWidgetVisible(widget)
                break
    
    def clear_highlights(self):
        """Clear all field highlights"""
        for widget in self.field_widgets:
            if isinstance(widget, DraggableFieldWidget):
                # Reset to original styling
                widget.setup_ui()  # This will reset the styling