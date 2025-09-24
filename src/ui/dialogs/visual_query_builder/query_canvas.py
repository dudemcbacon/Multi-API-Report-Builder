"""
Visual query canvas for the query builder
"""
import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QSplitter, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

from .drag_drop_widgets import QueryCanvasWidget
from .join_builder import JoinBuilder

logger = logging.getLogger(__name__)

class VisualQueryCanvas(QWidget):
    """
    Main visual query canvas that combines the drag-drop canvas with query preview
    """
    
    query_changed = pyqtSignal(dict)  # Emitted when query structure changes
    test_query_requested = pyqtSignal(str)  # Emitted when test query is requested
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_object = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the visual query canvas UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header with current object
        self.setup_header(layout)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Top: Visual query builder with relationships
        self.setup_visual_builder(splitter)
        
        # Bottom: Query preview and controls
        self.setup_query_preview(splitter)
        
        # Set splitter proportions (70% visual, 30% preview)
        splitter.setSizes([420, 180])
    
    def setup_header(self, parent_layout):
        """Setup the header section"""
        header_frame = QFrame()
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10, 8, 10, 8)
        
        # Object icon
        object_icon = QLabel()
        object_icon.setPixmap(qta.icon('fa5s.database').pixmap(20, 20))
        header_layout.addWidget(object_icon)
        
        # Object name
        self.object_label = QLabel("No object selected")
        header_layout.addWidget(self.object_label)
        
        header_layout.addStretch()
        
        # Clear all button
        clear_btn = QPushButton("Clear All")
        clear_btn.setIcon(qta.icon('fa5s.trash'))
        clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(clear_btn)
        
        parent_layout.addWidget(header_frame)
    
    def setup_visual_builder(self, parent_splitter):
        """Setup the visual query builder section"""
        builder_frame = QGroupBox("Visual Query Builder")
        
        builder_layout = QVBoxLayout(builder_frame)
        builder_layout.setContentsMargins(10, 15, 10, 10)
        
        # Create horizontal splitter for canvas and joins
        canvas_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Basic drag-drop canvas
        self.query_canvas = QueryCanvasWidget()
        self.query_canvas.query_changed.connect(self.on_query_changed)
        canvas_splitter.addWidget(self.query_canvas)
        
        # Right: Join builder for relationships
        self.join_builder = JoinBuilder()
        self.join_builder.query_changed.connect(self.on_query_changed)
        canvas_splitter.addWidget(self.join_builder)
        
        # Set proportions (60% canvas, 40% joins)
        canvas_splitter.setSizes([360, 240])
        
        builder_layout.addWidget(canvas_splitter)
        parent_splitter.addWidget(builder_frame)
    
    def setup_query_preview(self, parent_splitter):
        """Setup the query preview section"""
        preview_frame = QGroupBox("Generated SOQL Query")
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(10, 15, 10, 10)
        
        # Query text area
        self.query_preview = QTextEdit()
        self.query_preview.setReadOnly(True)
        self.query_preview.setMinimumHeight(120)
        self.query_preview.setPlainText("SELECT fields\\nFROM object\\n-- Build your query using drag and drop above")
        
        preview_layout.addWidget(self.query_preview)
        
        # Preview controls
        controls_layout = QHBoxLayout()
        
        # Query stats
        self.query_stats = QLabel("0 fields selected, 0 conditions")
        controls_layout.addWidget(self.query_stats)
        
        controls_layout.addStretch()
        
        # Copy query button
        copy_btn = QPushButton("Copy Query")
        copy_btn.setIcon(qta.icon('fa5s.copy'))
        copy_btn.clicked.connect(self.copy_query)
        controls_layout.addWidget(copy_btn)
        
        # Test query button
        test_btn = QPushButton("Test Query")
        test_btn.setIcon(qta.icon('fa5s.play'))
        test_btn.clicked.connect(self.test_query)
        controls_layout.addWidget(test_btn)
        
        preview_layout.addLayout(controls_layout)
        parent_splitter.addWidget(preview_frame)
    
    def set_current_object(self, object_data: Dict[str, Any]):
        """Set the current Salesforce object"""
        self.current_object = object_data
        object_name = object_data.get('name', 'Unknown Object')
        object_label = object_data.get('label', object_name)
        
        self.object_label.setText(f"Building query for: {object_label} ({object_name})")
        
        # Clear existing query
        self.query_canvas.clear_all()
        
        logger.info(f"[VISUAL-CANVAS] Set current object: {object_name}")
    
    def on_query_changed(self):
        """Handle query structure changes"""
        if not self.current_object:
            return
        
        # Get current query components
        selected_fields = self.query_canvas.get_selected_fields()
        filter_conditions = self.query_canvas.get_filter_conditions()
        parent_fields = self.join_builder.get_parent_fields()
        subqueries = self.join_builder.get_subqueries()
        
        # Generate SOQL query
        query = self.generate_soql_query(selected_fields, filter_conditions, parent_fields, subqueries)
        
        # Update preview
        self.query_preview.setPlainText(query)
        
        # Update stats
        field_count = len(selected_fields)
        condition_count = len(filter_conditions)
        self.query_stats.setText(f"{field_count} fields selected, {condition_count} conditions")
        
        # Emit query change signal
        query_data = {
            'object': self.current_object,
            'fields': selected_fields,
            'conditions': filter_conditions,
            'soql': query
        }
        self.query_changed.emit(query_data)
        
        logger.debug(f"[VISUAL-CANVAS] Query changed: {field_count} fields, {condition_count} conditions")
    
    def generate_soql_query(self, fields: List[Dict[str, Any]], conditions: List[Dict[str, Any]], 
                           parent_fields: List[str] = None, subqueries: List[Dict[str, Any]] = None) -> str:
        """Generate SOQL query from visual components including relationships"""
        if not self.current_object:
            return "-- No object selected"
        
        object_name = self.current_object.get('name', '')
        parent_fields = parent_fields or []
        subqueries = subqueries or []
        
        # Build SELECT clause with all field types
        select_items = []
        
        # Basic fields from current object
        basic_field_names = [field.get('name', '') for field in fields if field.get('name')]
        select_items.extend(basic_field_names)
        
        # Parent relationship fields (dot notation)
        select_items.extend(parent_fields)
        
        # Subqueries for child relationships
        for subquery in subqueries:
            if subquery.get('fields'):
                child_field_names = [f.get('name', '') for f in subquery['fields'] if f.get('name')]
                if child_field_names:
                    subquery_clause = f"(SELECT {', '.join(child_field_names)} FROM {subquery['relationship_name']})"
                    select_items.append(subquery_clause)
        
        # Ensure we have at least one field
        if not select_items:
            return f"-- Select fields to query from {object_name}"
        
        select_clause = f"SELECT {', '.join(select_items)}"
        
        # FROM clause
        from_clause = f"FROM {object_name}"
        
        # WHERE clause (simplified for now)
        where_clause = ""
        if conditions:
            condition_strings = []
            for condition in conditions:
                field_data = condition.get('field', {})
                field_name = field_data.get('name', '')
                operator = condition.get('operator', '=')
                value = condition.get('value', '')
                
                if field_name:
                    # Handle operators that don't need values
                    if operator in ['IS NULL', 'IS NOT NULL']:
                        condition_strings.append(f"{field_name} {operator}")
                    elif value:  # Other operators need values
                        # Simple value formatting (this could be enhanced)
                        if operator in ['IN', 'NOT IN']:
                            formatted_value = f"({value})"
                        elif field_data.get('type', '').lower() in ['string', 'textarea', 'email', 'phone']:
                            formatted_value = f"'{value}'"
                        else:
                            formatted_value = str(value)
                        
                        condition_strings.append(f"{field_name} {operator} {formatted_value}")
            
            if condition_strings:
                where_clause = f"WHERE {' AND '.join(condition_strings)}"
        
        # Combine clauses
        query_parts = [select_clause, from_clause]
        if where_clause:
            query_parts.append(where_clause)
        
        query_parts.append("LIMIT 1000")  # Default limit
        
        return '\n'.join(query_parts)
    
    def copy_query(self):
        """Copy the current query to clipboard"""
        from PyQt6.QtGui import QGuiApplication
        
        query_text = self.query_preview.toPlainText()
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(query_text)
        
        logger.info("[VISUAL-CANVAS] Query copied to clipboard")
    
    def test_query(self):
        """Test the current query"""
        query_text = self.query_preview.toPlainText()
        logger.info(f"[VISUAL-CANVAS] Test query requested: {query_text}")
        
        # Emit signal to request query execution
        if query_text and not query_text.startswith("--"):
            self.test_query_requested.emit(query_text)
        else:
            logger.warning("[VISUAL-CANVAS] No valid query to test")
    
    def clear_all(self):
        """Clear all query components"""
        self.query_canvas.clear_all()
        self.join_builder.clear_all()
        logger.info("[VISUAL-CANVAS] Cleared all query components")
    
    def get_current_query_data(self) -> Dict[str, Any]:
        """Get the current query data"""
        if not self.current_object:
            return {}
        
        return {
            'object': self.current_object,
            'fields': self.query_canvas.get_selected_fields(),
            'conditions': self.query_canvas.get_filter_conditions(),
            'parent_fields': self.join_builder.get_parent_fields(),
            'subqueries': self.join_builder.get_subqueries(),
            'soql': self.query_preview.toPlainText()
        }
    
    def load_query_data(self, query_data: Dict[str, Any]):
        """Load query data into the visual builder (for future enhancement)"""
        # This would be used to load saved queries or templates
        logger.info("[VISUAL-CANVAS] Load query data (not yet implemented)")