"""
Relationship Explorer for visualizing Salesforce object relationships
"""
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFrame, QSplitter, QScrollArea, QLineEdit, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QFont, QColor, QDrag, QMouseEvent
import qtawesome as qta

# Import drag-drop functionality
from .drag_drop_widgets import DraggableFieldWidget, FIELD_MIME_TYPE

logger = logging.getLogger(__name__)

class DraggableTreeWidget(QTreeWidget):
    """Tree widget that supports dragging field items"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        
    def startDrag(self, supportedActions):
        """Start drag operation for field items"""
        item = self.currentItem()
        if not item:
            return
            
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'field':
            return
            
        # Create drag with field data
        drag = QDrag(self)
        mime_data = self.mimeData([item])
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = self.viewport().grab(self.visualRect(self.indexFromItem(item)))
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        logger.info(f"[RELATIONSHIP-DRAG] Starting drag for field: {data.get('field_data', {}).get('name', 'Unknown')}")
        drag.exec(Qt.DropAction.CopyAction)
    
    def mimeData(self, items):
        """Create MIME data for dragged items"""
        from PyQt6.QtCore import QMimeData
        
        if not items:
            return QMimeData()
            
        item = items[0]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        
        if data and data.get('type') == 'field':
            mime_data = QMimeData()
            field_data = data.get('field_data', {})
            field_json = json.dumps(field_data)
            mime_data.setData(FIELD_MIME_TYPE, field_json.encode('utf-8'))
            return mime_data
            
        return QMimeData()

class RelationshipNode:
    """Represents a node in the relationship graph"""
    
    def __init__(self, object_name: str, object_data: Dict[str, Any]):
        self.object_name = object_name
        self.object_data = object_data
        self.parent_relationships = []  # List of (field_name, parent_object_name)
        self.child_relationships = []   # List of (relationship_name, child_object_name)
        
    def add_parent_relationship(self, field_name: str, parent_object_name: str):
        """Add a parent relationship (lookup/master-detail)"""
        self.parent_relationships.append((field_name, parent_object_name))
        
    def add_child_relationship(self, relationship_name: str, child_object_name: str):
        """Add a child relationship"""
        self.child_relationships.append((relationship_name, child_object_name))


class RelationshipExplorer(QWidget):
    """
    Visual explorer for Salesforce object relationships
    """
    
    relationship_selected = pyqtSignal(dict)  # Emitted when a relationship is selected
    field_path_selected = pyqtSignal(str, dict)  # path, field_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.object_metadata = {}  # Dict of object_name -> object_description
        self.relationship_graph = {}  # Dict of object_name -> RelationshipNode
        self.current_object = None
        self.max_depth = 5  # Maximum relationship traversal depth
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the relationship explorer UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Relationship Explorer")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # View mode selector
        mode_label = QLabel("View:")
        header_layout.addWidget(mode_label)
        
        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Tree View", "Graph View"])
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        header_layout.addWidget(self.view_mode_combo)
        
        layout.addLayout(header_layout)
        
        # Search box
        search_layout = QHBoxLayout()
        search_icon = QLabel()
        search_icon.setPixmap(qta.icon('fa5s.search').pixmap(14, 14))
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search relationships...")
        self.search_input.textChanged.connect(self.filter_relationships)
        search_layout.addWidget(self.search_input)
        
        layout.addLayout(search_layout)
        
        # Main content area
        self.setup_tree_view(layout)
        
        # Info panel
        self.setup_info_panel(layout)
    
    def setup_tree_view(self, parent_layout):
        """Setup the tree view for relationships"""
        self.relationship_tree = DraggableTreeWidget()
        self.relationship_tree.setHeaderLabels(["Object / Field", "Type", "Related To"])
        self.relationship_tree.setColumnWidth(0, 200)
        self.relationship_tree.setColumnWidth(1, 100)
        self.relationship_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.relationship_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        
        # Tree uses default styling
        
        parent_layout.addWidget(self.relationship_tree)
    
    def setup_info_panel(self, parent_layout):
        """Setup the information panel"""
        info_frame = QFrame()
        info_frame.setMaximumHeight(120)
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        self.info_label = QLabel("Select a relationship to see details")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        parent_layout.addWidget(info_frame)
    
    def set_object_metadata(self, object_name: str, metadata: Dict[str, Any]):
        """Set metadata for an object"""
        self.object_metadata[object_name] = metadata
        self.build_relationship_graph()
        
        # If this is the current object, update the view
        if object_name == self.current_object:
            self.populate_relationships()
    
    def set_current_object(self, object_name: str):
        """Set the current object to explore relationships from"""
        self.current_object = object_name
        self.populate_relationships()
        
        logger.info(f"[RELATIONSHIP-EXPLORER] Set current object: {object_name}")
    
    def build_relationship_graph(self):
        """Build the relationship graph from object metadata"""
        self.relationship_graph.clear()
        
        # Create nodes for all objects
        for obj_name, metadata in self.object_metadata.items():
            node = RelationshipNode(obj_name, metadata)
            self.relationship_graph[obj_name] = node
        
        # Build relationships
        for obj_name, metadata in self.object_metadata.items():
            node = self.relationship_graph[obj_name]
            
            # Process fields for parent relationships
            fields = metadata.get('fields', [])
            for field in fields:
                if field.get('type', '').lower() in ['reference', 'lookup', 'masterdetail']:
                    reference_to = field.get('referenceTo', [])
                    relationship_name = field.get('relationshipName')
                    
                    for parent_obj in reference_to:
                        if parent_obj in self.relationship_graph:
                            node.add_parent_relationship(field['name'], parent_obj)
                            
                            # Also add child relationship to parent
                            if relationship_name:
                                parent_node = self.relationship_graph[parent_obj]
                                parent_node.add_child_relationship(relationship_name, obj_name)
            
            # Process explicit child relationships
            child_relationships = metadata.get('childRelationships', [])
            for child_rel in child_relationships:
                child_obj = child_rel.get('childSObject')
                rel_name = child_rel.get('relationshipName')
                
                if child_obj and rel_name and child_obj in self.relationship_graph:
                    node.add_child_relationship(rel_name, child_obj)
        
        logger.info(f"[RELATIONSHIP-EXPLORER] Built relationship graph with {len(self.relationship_graph)} objects")
    
    def populate_relationships(self):
        """Populate the tree with relationships for the current object"""
        self.relationship_tree.clear()
        
        if not self.current_object or self.current_object not in self.relationship_graph:
            return
        
        # Create root item for current object
        root_node = self.relationship_graph[self.current_object]
        root_item = QTreeWidgetItem(self.relationship_tree)
        root_item.setText(0, self.current_object)
        root_item.setText(1, "Current Object")
        root_item.setIcon(0, qta.icon('fa5s.database'))
        root_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'object',
            'object_name': self.current_object,
            'path': self.current_object
        })
        
        # Make root bold
        font = root_item.font(0)
        font.setBold(True)
        root_item.setFont(0, font)
        
        # Add current object's fields (first few for drag-drop)
        if self.current_object in self.object_metadata:
            current_metadata = self.object_metadata[self.current_object]
            current_fields = current_metadata.get('fields', [])
            
            if current_fields:
                fields_group = QTreeWidgetItem(root_item)
                fields_group.setText(0, "Current Object Fields")
                fields_group.setIcon(0, qta.icon('fa5s.tags'))
                
                # Add first 15 fields for drag-drop
                for field in current_fields[:15]:
                    field_item = QTreeWidgetItem(fields_group)
                    field_item.setText(0, field.get('label', field.get('name', '')))
                    field_item.setText(1, field.get('type', ''))
                    field_item.setIcon(0, qta.icon('fa5s.tag'))
                    field_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'type': 'field',
                        'field_data': field,
                        'path': field.get('name', '')
                    })
        
        # Add parent relationships
        if root_node.parent_relationships:
            parent_group = QTreeWidgetItem(root_item)
            parent_group.setText(0, "Parent Objects")
            parent_group.setIcon(0, qta.icon('fa5s.arrow-up'))
            
            for field_name, parent_obj in root_node.parent_relationships:
                self.add_parent_relationship_item(parent_group, field_name, parent_obj, 
                                                 f"{self.current_object}.{field_name}", 1)
        
        # Add child relationships
        if root_node.child_relationships:
            child_group = QTreeWidgetItem(root_item)
            child_group.setText(0, "Child Objects")
            child_group.setIcon(0, qta.icon('fa5s.arrow-down'))
            
            for rel_name, child_obj in root_node.child_relationships:
                self.add_child_relationship_item(child_group, rel_name, child_obj)
        
        # Expand root
        root_item.setExpanded(True)
    
    def add_parent_relationship_item(self, parent_item: QTreeWidgetItem, field_name: str, 
                                    parent_obj: str, path: str, depth: int):
        """Add a parent relationship item to the tree"""
        if depth > self.max_depth:
            return
        
        # Create relationship item
        rel_item = QTreeWidgetItem(parent_item)
        rel_item.setText(0, f"{field_name} ({parent_obj})")
        rel_item.setText(1, "Lookup")
        rel_item.setText(2, parent_obj)
        rel_item.setIcon(0, qta.icon('fa5s.link'))
        rel_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'parent_relationship',
            'field_name': field_name,
            'parent_object': parent_obj,
            'path': path
        })
        
        # Add fields from parent object
        if parent_obj in self.object_metadata:
            parent_metadata = self.object_metadata[parent_obj]
            fields = parent_metadata.get('fields', [])
            
            # Add some common fields
            for field in fields[:10]:  # Limit to first 10 fields for performance
                field_item = QTreeWidgetItem(rel_item)
                field_item.setText(0, field.get('label', field.get('name', '')))
                field_item.setText(1, field.get('type', ''))
                field_item.setIcon(0, qta.icon('fa5s.tag'))
                field_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'field',
                    'field_data': field,
                    'path': f"{path}.{field.get('name', '')}"
                })
            
            # Recursively add parent's parent relationships
            if parent_obj in self.relationship_graph:
                parent_node = self.relationship_graph[parent_obj]
                for pfield_name, pparent_obj in parent_node.parent_relationships[:3]:  # Limit recursion
                    self.add_parent_relationship_item(rel_item, pfield_name, pparent_obj,
                                                    f"{path}.{pfield_name}", depth + 1)
    
    def add_child_relationship_item(self, parent_item: QTreeWidgetItem, rel_name: str, child_obj: str):
        """Add a child relationship item to the tree"""
        # Create relationship item
        rel_item = QTreeWidgetItem(parent_item)
        rel_item.setText(0, f"{rel_name} ({child_obj})")
        rel_item.setText(1, "Child")
        rel_item.setText(2, child_obj)
        rel_item.setIcon(0, qta.icon('fa5s.sitemap'))
        rel_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': 'child_relationship',
            'relationship_name': rel_name,
            'child_object': child_obj,
            'path': f"({rel_name})"  # Subquery notation
        })
        
        # Add fields from child object
        if child_obj in self.object_metadata:
            child_metadata = self.object_metadata[child_obj]
            fields = child_metadata.get('fields', [])
            
            # Add some common fields
            for field in fields[:10]:  # Limit to first 10 fields
                field_item = QTreeWidgetItem(rel_item)
                field_item.setText(0, field.get('label', field.get('name', '')))
                field_item.setText(1, field.get('type', ''))
                field_item.setIcon(0, qta.icon('fa5s.tag'))
                field_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'type': 'child_field',
                    'field_data': field,
                    'relationship_name': rel_name,
                    'path': f"{rel_name}.{field.get('name', '')}"
                })
    
    def on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        # Update info panel
        self.update_info_panel(data)
        
        # Emit appropriate signal
        if data['type'] == 'field':
            self.field_path_selected.emit(data['path'], data['field_data'])
        elif data['type'] in ['parent_relationship', 'child_relationship']:
            self.relationship_selected.emit(data)
    
    def on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item double-click"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        # For objects, set as current object
        if data['type'] == 'object' and data['object_name'] != self.current_object:
            self.set_current_object(data['object_name'])
        elif data['type'] == 'parent_relationship':
            # Navigate to parent object
            self.set_current_object(data['parent_object'])
        elif data['type'] == 'child_relationship':
            # Navigate to child object
            self.set_current_object(data['child_object'])
    
    def update_info_panel(self, data: Dict[str, Any]):
        """Update the info panel with details about the selected item"""
        info_text = ""
        
        if data['type'] == 'object':
            info_text = f"<b>Object:</b> {data['object_name']}<br>"
            if data['object_name'] in self.object_metadata:
                metadata = self.object_metadata[data['object_name']]
                info_text += f"<b>Label:</b> {metadata.get('label', 'N/A')}<br>"
                info_text += f"<b>Custom:</b> {'Yes' if metadata.get('custom', False) else 'No'}<br>"
                
        elif data['type'] == 'field':
            field = data['field_data']
            info_text = f"<b>Field:</b> {field.get('label', field.get('name', ''))}<br>"
            info_text += f"<b>API Name:</b> {field.get('name', '')}<br>"
            info_text += f"<b>Type:</b> {field.get('type', '')}<br>"
            info_text += f"<b>Path:</b> <code>{data['path']}</code><br>"
            
        elif data['type'] == 'parent_relationship':
            info_text = f"<b>Parent Relationship</b><br>"
            info_text += f"<b>Field:</b> {data['field_name']}<br>"
            info_text += f"<b>Related To:</b> {data['parent_object']}<br>"
            info_text += f"<b>Path:</b> <code>{data['path']}</code><br>"
            info_text += "<i>Double-click to navigate to parent object</i>"
            
        elif data['type'] == 'child_relationship':
            info_text = f"<b>Child Relationship</b><br>"
            info_text += f"<b>Name:</b> {data['relationship_name']}<br>"
            info_text += f"<b>Child Object:</b> {data['child_object']}<br>"
            info_text += f"<b>Subquery:</b> <code>(SELECT ... FROM {data['relationship_name']})</code><br>"
            info_text += "<i>Double-click to navigate to child object</i>"
        
        self.info_label.setText(info_text)
    
    def filter_relationships(self, search_text: str):
        """Filter the relationship tree based on search text"""
        # Simple implementation - hide/show items based on text
        search_lower = search_text.lower()
        
        def filter_item(item: QTreeWidgetItem):
            """Recursively filter tree items"""
            text = item.text(0).lower()
            match = search_lower in text
            
            # Check children
            child_match = False
            for i in range(item.childCount()):
                child = item.child(i)
                if filter_item(child):
                    child_match = True
            
            # Show item if it matches or has matching children
            show = match or child_match or not search_text
            item.setHidden(not show)
            
            return show
        
        # Filter root items
        for i in range(self.relationship_tree.topLevelItemCount()):
            filter_item(self.relationship_tree.topLevelItem(i))
    
    def on_view_mode_changed(self, mode: str):
        """Handle view mode change"""
        # For now, only tree view is implemented
        # Graph view would be a future enhancement
        if mode == "Graph View":
            self.info_label.setText("<i>Graph view coming soon...</i>")
    
    def get_all_related_fields(self, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Get all fields including related object fields up to max_depth"""
        if not self.current_object or self.current_object not in self.relationship_graph:
            return []
        
        related_fields = []
        visited = set()
        
        def traverse_relationships(obj_name: str, path_prefix: str, depth: int):
            """Recursively traverse relationships"""
            if depth > max_depth or obj_name in visited:
                return
            
            visited.add(obj_name)
            
            if obj_name not in self.object_metadata:
                return
            
            metadata = self.object_metadata[obj_name]
            fields = metadata.get('fields', [])
            
            # Add fields with full path
            for field in fields:
                field_copy = field.copy()
                field_copy['__path'] = f"{path_prefix}.{field['name']}" if path_prefix else field['name']
                field_copy['__object'] = obj_name
                related_fields.append(field_copy)
            
            # Traverse parent relationships
            if obj_name in self.relationship_graph:
                node = self.relationship_graph[obj_name]
                for field_name, parent_obj in node.parent_relationships:
                    new_path = f"{path_prefix}.{field_name}" if path_prefix else field_name
                    traverse_relationships(parent_obj, new_path, depth + 1)
        
        # Start traversal from current object
        traverse_relationships(self.current_object, "", 0)
        
        return related_fields