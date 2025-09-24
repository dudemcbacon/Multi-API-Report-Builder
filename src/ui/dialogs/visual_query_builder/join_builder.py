"""
Join Builder for visual relationship query construction
"""
import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QPen, QColor
import qtawesome as qta

from .drag_drop_widgets import DropZoneWidget

logger = logging.getLogger(__name__)

class RelationshipPath(QFrame):
    """Visual representation of a relationship path"""
    
    remove_requested = pyqtSignal(object)  # Emits self when remove is requested
    
    def __init__(self, path: str, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.path = path
        self.field_data = field_data
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the relationship path UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        
        # Path icon
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.route').pixmap(16, 16))
        layout.addWidget(icon_label)
        
        # Path display
        path_parts = self.path.split('.')
        for i, part in enumerate(path_parts):
            if i > 0:
                arrow = QLabel("→")
                layout.addWidget(arrow)
            
            part_label = QLabel(part)
            layout.addWidget(part_label)
        
        layout.addStretch()
        
        # Field type
        field_type = self.field_data.get('type', '')
        type_label = QLabel(field_type.upper())
        layout.addWidget(type_label)
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon('fa5s.times'))
        remove_btn.setMaximumSize(20, 20)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(remove_btn)


class SubqueryContainer(QFrame):
    """Container for parent-to-child subqueries"""
    
    fields_changed = pyqtSignal()
    remove_requested = pyqtSignal(object)
    
    def __init__(self, relationship_name: str, child_object: str, parent=None):
        super().__init__(parent)
        self.relationship_name = relationship_name
        self.child_object = child_object
        self.selected_fields = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the subquery container UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Subquery icon and title
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon('fa5s.sitemap').pixmap(20, 20))
        header_layout.addWidget(icon_label)
        
        title = QLabel(f"Subquery: {self.child_object} (via {self.relationship_name})")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon('fa5s.times'))
        remove_btn.setMaximumSize(25, 25)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(remove_btn)
        
        layout.addLayout(header_layout)
        
        # Fields drop zone
        self.fields_drop_zone = DropZoneWidget("Drop child object fields here")
        self.fields_drop_zone.field_dropped.connect(self.add_field)
        self.fields_drop_zone.setMinimumHeight(60)
        layout.addWidget(self.fields_drop_zone)
        
        # Selected fields container
        self.fields_container = QWidget()
        self.fields_layout = QVBoxLayout(self.fields_container)
        self.fields_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.fields_container)
        
        # Field count
        self.field_count_label = QLabel("0 fields selected")
        layout.addWidget(self.field_count_label)
    
    def add_field(self, field_data: Dict[str, Any], drop_widget):
        """Add a field to the subquery"""
        if field_data in self.selected_fields:
            logger.warning(f"[SUBQUERY] Field already selected: {field_data.get('name', 'Unknown')}")
            return
        
        self.selected_fields.append(field_data)
        
        # Create field widget
        field_widget = QFrame()
        
        field_layout = QHBoxLayout(field_widget)
        field_layout.setContentsMargins(3, 2, 3, 2)
        
        # Field name
        field_label = QLabel(field_data.get('label', field_data.get('name', '')))
        field_layout.addWidget(field_label)
        
        field_layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon('fa5s.times'))
        remove_btn.setMaximumSize(16, 16)
        remove_btn.clicked.connect(lambda: self.remove_field(field_data, field_widget))
        field_layout.addWidget(remove_btn)
        
        self.fields_layout.addWidget(field_widget)
        self.update_field_count()
        self.fields_changed.emit()
        
        logger.info(f"[SUBQUERY] Added field to subquery: {field_data.get('name', 'Unknown')}")
    
    def remove_field(self, field_data: Dict[str, Any], widget: QWidget):
        """Remove a field from the subquery"""
        if field_data in self.selected_fields:
            self.selected_fields.remove(field_data)
        
        widget.setParent(None)
        widget.deleteLater()
        
        self.update_field_count()
        self.fields_changed.emit()
    
    def update_field_count(self):
        """Update the field count label"""
        count = len(self.selected_fields)
        self.field_count_label.setText(f"{count} field{'s' if count != 1 else ''} selected")
    
    def get_subquery_data(self) -> Dict[str, Any]:
        """Get the subquery data"""
        return {
            'relationship_name': self.relationship_name,
            'child_object': self.child_object,
            'fields': self.selected_fields.copy()
        }


class JoinBuilder(QWidget):
    """
    Visual builder for complex joins and relationships
    """
    
    query_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_relationships = []  # List of RelationshipPath widgets
        self.subqueries = []  # List of SubqueryContainer widgets
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the join builder UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("Relationship Query Builder")
        layout.addWidget(title)
        
        # Parent relationships section
        self.setup_parent_relationships_section(layout)
        
        # Subqueries section
        self.setup_subqueries_section(layout)
        
        layout.addStretch()
    
    def setup_parent_relationships_section(self, parent_layout):
        """Setup the parent relationships section"""
        section_group = QGroupBox("Parent Object Fields (Child-to-Parent)")
        
        section_layout = QVBoxLayout(section_group)
        
        # Instructions
        instructions = QLabel("Drag related parent fields here to access them via dot notation")
        section_layout.addWidget(instructions)
        
        # Drop zone for parent relationships
        self.parent_drop_zone = DropZoneWidget("Drop parent object fields here")
        self.parent_drop_zone.field_dropped.connect(self.add_parent_relationship)
        self.parent_drop_zone.setMinimumHeight(50)
        section_layout.addWidget(self.parent_drop_zone)
        
        # Container for relationship paths
        self.parent_scroll = QScrollArea()
        self.parent_scroll.setWidgetResizable(True)
        self.parent_scroll.setMaximumHeight(150)
        self.parent_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.parent_container = QWidget()
        self.parent_layout = QVBoxLayout(self.parent_container)
        self.parent_layout.setContentsMargins(0, 0, 0, 0)
        self.parent_layout.addStretch()
        
        self.parent_scroll.setWidget(self.parent_container)
        section_layout.addWidget(self.parent_scroll)
        
        parent_layout.addWidget(section_group)
    
    def setup_subqueries_section(self, parent_layout):
        """Setup the subqueries section"""
        section_group = QGroupBox("Child Object Subqueries (Parent-to-Child)")
        
        section_layout = QVBoxLayout(section_group)
        
        # Instructions
        instructions = QLabel("Drag child objects here to create subqueries")
        section_layout.addWidget(instructions)
        
        # Drop zone for child relationships
        self.child_drop_zone = DropZoneWidget("Drop child objects here to create subqueries")
        self.child_drop_zone.field_dropped.connect(self.add_child_relationship)
        self.child_drop_zone.setMinimumHeight(50)
        section_layout.addWidget(self.child_drop_zone)
        
        # Container for subqueries
        self.subquery_scroll = QScrollArea()
        self.subquery_scroll.setWidgetResizable(True)
        self.subquery_scroll.setMaximumHeight(200)
        self.subquery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.subquery_container = QWidget()
        self.subquery_layout = QVBoxLayout(self.subquery_container)
        self.subquery_layout.setContentsMargins(0, 0, 0, 0)
        self.subquery_layout.addStretch()
        
        self.subquery_scroll.setWidget(self.subquery_container)
        section_layout.addWidget(self.subquery_scroll)
        
        parent_layout.addWidget(section_group)
    
    def add_parent_relationship(self, field_data: Dict[str, Any], drop_widget):
        """Add a parent relationship field"""
        # Check if this is a relationship field with a path
        path = field_data.get('__path', field_data.get('name', ''))
        
        # Create relationship path widget
        path_widget = RelationshipPath(path, field_data)
        path_widget.remove_requested.connect(self.remove_parent_relationship)
        
        # Insert before stretch
        self.parent_layout.insertWidget(len(self.parent_relationships), path_widget)
        self.parent_relationships.append(path_widget)
        
        self.query_changed.emit()
        logger.info(f"[JOIN-BUILDER] Added parent relationship: {path}")
    
    def add_child_relationship(self, relationship_data: Dict[str, Any], drop_widget):
        """Add a child relationship (subquery)"""
        # Extract relationship info
        if relationship_data.get('type') == 'child_relationship':
            rel_name = relationship_data.get('relationship_name', '')
            child_obj = relationship_data.get('child_object', '')
        else:
            # Try to extract from field data
            rel_name = relationship_data.get('relationshipName', '')
            child_obj = relationship_data.get('referenceTo', [''])[0]
        
        if not rel_name or not child_obj:
            logger.warning("[JOIN-BUILDER] Invalid child relationship data")
            return
        
        # Check if subquery already exists
        for subquery in self.subqueries:
            if subquery.relationship_name == rel_name:
                logger.warning(f"[JOIN-BUILDER] Subquery already exists for: {rel_name}")
                return
        
        # Create subquery container
        subquery_widget = SubqueryContainer(rel_name, child_obj)
        subquery_widget.fields_changed.connect(self.query_changed.emit)
        subquery_widget.remove_requested.connect(self.remove_subquery)
        
        # Insert before stretch
        self.subquery_layout.insertWidget(len(self.subqueries), subquery_widget)
        self.subqueries.append(subquery_widget)
        
        self.query_changed.emit()
        logger.info(f"[JOIN-BUILDER] Added subquery: {rel_name} ({child_obj})")
    
    def remove_parent_relationship(self, path_widget: RelationshipPath):
        """Remove a parent relationship"""
        if path_widget in self.parent_relationships:
            self.parent_relationships.remove(path_widget)
        
        path_widget.setParent(None)
        path_widget.deleteLater()
        self.query_changed.emit()
    
    def remove_subquery(self, subquery_widget: SubqueryContainer):
        """Remove a subquery"""
        if subquery_widget in self.subqueries:
            self.subqueries.remove(subquery_widget)
        
        subquery_widget.setParent(None)
        subquery_widget.deleteLater()
        self.query_changed.emit()
    
    def get_parent_fields(self) -> List[str]:
        """Get all parent relationship field paths"""
        return [rp.path for rp in self.parent_relationships]
    
    def get_subqueries(self) -> List[Dict[str, Any]]:
        """Get all subquery data"""
        return [sq.get_subquery_data() for sq in self.subqueries]
    
    def clear_all(self):
        """Clear all relationships and subqueries"""
        # Clear parent relationships
        for widget in self.parent_relationships[:]:
            self.remove_parent_relationship(widget)
        
        # Clear subqueries
        for widget in self.subqueries[:]:
            self.remove_subquery(widget)
        
        self.query_changed.emit()