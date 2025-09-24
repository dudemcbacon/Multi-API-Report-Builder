"""
Core drag-and-drop widgets for the visual query builder
"""
import logging
from typing import Dict, Any, Optional, List
import json

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, 
    QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QSize
from PyQt6.QtGui import (
    QDrag, QPainter, QPixmap, QColor, QPen, QBrush, 
    QDragEnterEvent, QDragMoveEvent, QDropEvent, QMouseEvent
)
import qtawesome as qta

# Import the proper filter condition widget
from .filter_builder import VisualFilterCondition

logger = logging.getLogger(__name__)

# MIME type for field data
FIELD_MIME_TYPE = "application/x-salesforce-field"

class DraggableFieldWidget(QWidget):
    """
    A draggable widget representing a Salesforce field
    """
    
    field_double_clicked = pyqtSignal(dict)  # Emitted when field is double-clicked
    
    def __init__(self, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_data = field_data
        self.drag_start_position = None
        
        self.setup_ui()
        self.setToolTip(self.create_tooltip())
    
    def setup_ui(self):
        """Setup the field widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(5)
        
        # Field type icon
        field_type = self.field_data.get('type', '').lower()
        icon_name = self.get_field_type_icon(field_type)
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name).pixmap(16, 16))
        layout.addWidget(icon_label)
        
        # Field name
        name_label = QLabel(self.field_data.get('label', self.field_data.get('name', '')))
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Field type indicator
        type_label = QLabel(field_type.upper())
        layout.addWidget(type_label)
        
        self.setMinimumHeight(25)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
    
    def get_field_type_icon(self, field_type: str) -> str:
        """Get appropriate icon for field type"""
        icon_map = {
            'string': 'fa5s.font',
            'textarea': 'fa5s.align-left',
            'integer': 'fa5s.hashtag',
            'double': 'fa5s.calculator',
            'currency': 'fa5s.dollar-sign',
            'percent': 'fa5s.percentage',
            'date': 'fa5s.calendar',
            'datetime': 'fa5s.clock',
            'boolean': 'fa5s.check-square',
            'picklist': 'fa5s.list',
            'multipicklist': 'fa5s.list-ul',
            'reference': 'fa5s.link',
            'id': 'fa5s.key',
            'email': 'fa5s.envelope',
            'phone': 'fa5s.phone',
            'url': 'fa5s.globe'
        }
        return icon_map.get(field_type, 'fa5s.question')
    
    
    def create_tooltip(self) -> str:
        """Create tooltip text for the field"""
        tooltip = f"<b>{self.field_data.get('label', self.field_data.get('name', ''))}</b><br>"
        tooltip += f"<b>Type:</b> {self.field_data.get('type', 'Unknown')}<br>"
        tooltip += f"<b>API Name:</b> {self.field_data.get('name', 'Unknown')}<br>"
        
        if self.field_data.get('length'):
            tooltip += f"<b>Length:</b> {self.field_data['length']}<br>"
        
        if self.field_data.get('picklistValues'):
            values = [pv.get('value', '') for pv in self.field_data['picklistValues'][:3]]
            tooltip += f"<b>Values:</b> {', '.join(values)}{'...' if len(self.field_data['picklistValues']) > 3 else ''}<br>"
        
        if self.field_data.get('calculated'):
            tooltip += "<b>Calculated Field</b><br>"
        
        tooltip += "<br><i>Drag to add to query or double-click to configure</i>"
        return tooltip
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for drag initiation"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for drag operation"""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if not self.drag_start_position:
            return
        
        # Check if we've moved far enough to start a drag
        if ((event.position().toPoint() - self.drag_start_position).manhattanLength() < 
            QApplication.startDragDistance()):
            return
        
        self.start_drag()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.drag_start_position = None
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double-click for field configuration"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.field_double_clicked.emit(self.field_data)
    
    def start_drag(self):
        """Start the drag operation"""
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Set field data as JSON
        field_json = json.dumps(self.field_data)
        mime_data.setData(FIELD_MIME_TYPE, field_json.encode('utf-8'))
        
        # CRITICAL: Attach the mime data to the drag object
        drag.setMimeData(mime_data)
        
        # Create drag pixmap
        pixmap = self.create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        # Start drag
        logger.info(f"[DRAG-DROP] Starting drag for field: {self.field_data.get('name', 'Unknown')}")
        drop_action = drag.exec(Qt.DropAction.CopyAction)
        
        logger.info(f"[DRAG-DROP] Drag completed with action: {drop_action}")
    
    def create_drag_pixmap(self) -> QPixmap:
        """Create a pixmap for the drag operation"""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use default theme colors for the drag pixmap
        palette = self.palette()
        bg_color = palette.color(palette.ColorRole.Button)
        bg_color.setAlpha(180)  # Semi-transparent
        
        border_color = palette.color(palette.ColorRole.ButtonText)
        border_color.setAlpha(200)
        
        text_color = palette.color(palette.ColorRole.ButtonText)
        
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 2))
        painter.drawRoundedRect(self.rect(), 3, 3)
        
        # Draw text
        painter.setPen(QPen(text_color, 1))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, 
                        self.field_data.get('label', self.field_data.get('name', '')))
        
        painter.end()
        return pixmap


class DropZoneWidget(QFrame):
    """
    A widget that accepts dropped fields and provides visual feedback
    """
    
    field_dropped = pyqtSignal(dict, object)  # field_data, drop_widget
    
    def __init__(self, drop_text: str = "Drop fields here", parent=None):
        super().__init__(parent)
        self.drop_text = drop_text
        self.is_drag_over = False
        self.accepted_field_types = None  # None means accept all types
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the drop zone UI"""
        self.setAcceptDrops(True)
        self.setMinimumHeight(50)
        
        layout = QVBoxLayout(self)
        
        # Drop text label
        self.drop_label = QLabel(self.drop_text)
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.drop_label)
    
    def set_accepted_field_types(self, field_types: List[str]):
        """Set which field types this drop zone accepts"""
        self.accepted_field_types = field_types
    
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasFormat(FIELD_MIME_TYPE):
            # Check if field type is accepted
            field_data = self.get_field_data_from_event(event)
            if self.is_field_accepted(field_data):
                event.acceptProposedAction()
                self.is_drag_over = True
                logger.debug(f"[DROP-ZONE] Drag enter accepted for field: {field_data.get('name', 'Unknown')}")
            else:
                event.ignore()
                logger.debug(f"[DROP-ZONE] Drag enter rejected - field type not accepted")
        else:
            event.ignore()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """Handle drag move event"""
        if event.mimeData().hasFormat(FIELD_MIME_TYPE):
            field_data = self.get_field_data_from_event(event)
            if self.is_field_accepted(field_data):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """Handle drag leave event"""
        self.is_drag_over = False
        logger.debug("[DROP-ZONE] Drag leave")
    
    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasFormat(FIELD_MIME_TYPE):
            field_data = self.get_field_data_from_event(event)
            if self.is_field_accepted(field_data):
                event.acceptProposedAction()
                self.is_drag_over = False
                
                logger.info(f"[DROP-ZONE] Field dropped: {field_data.get('name', 'Unknown')}")
                self.field_dropped.emit(field_data, self)
            else:
                event.ignore()
        else:
            event.ignore()
    
    def get_field_data_from_event(self, event) -> Dict[str, Any]:
        """Extract field data from drag event"""
        try:
            field_json = event.mimeData().data(FIELD_MIME_TYPE).data().decode('utf-8')
            return json.loads(field_json)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"[DROP-ZONE] Error parsing field data: {e}")
            return {}
    
    def is_field_accepted(self, field_data: Dict[str, Any]) -> bool:
        """Check if the field type is accepted by this drop zone"""
        if not self.accepted_field_types:
            return True  # Accept all types
        
        field_type = field_data.get('type', '').lower()
        return field_type in self.accepted_field_types


class QueryCanvasWidget(QWidget):
    """
    Main canvas widget for building queries visually
    """
    
    query_changed = pyqtSignal()  # Emitted when query structure changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_fields = []
        self.filter_conditions = []
        self.condition_widgets = []  # Track actual condition widgets
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the query canvas UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Canvas title
        title = QLabel("Visual Query Builder")
        layout.addWidget(title)
        
        # SELECT section
        self.setup_select_section(layout)
        
        # WHERE section
        self.setup_where_section(layout)
        
        layout.addStretch()
    
    def setup_select_section(self, parent_layout):
        """Setup the SELECT fields section"""
        # Section header
        select_header = QLabel("SELECT Fields")
        parent_layout.addWidget(select_header)
        
        # SELECT drop zone
        self.select_drop_zone = DropZoneWidget("Drop fields here to add to SELECT clause")
        self.select_drop_zone.field_dropped.connect(self.add_select_field)
        parent_layout.addWidget(self.select_drop_zone)
        
        # Selected fields container
        self.selected_fields_widget = QWidget()
        self.selected_fields_layout = QVBoxLayout(self.selected_fields_widget)
        self.selected_fields_layout.setContentsMargins(0, 0, 0, 0)
        parent_layout.addWidget(self.selected_fields_widget)
    
    def setup_where_section(self, parent_layout):
        """Setup the WHERE conditions section"""
        # Section header
        where_header = QLabel("WHERE Conditions")
        parent_layout.addWidget(where_header)
        
        # WHERE drop zone
        self.where_drop_zone = DropZoneWidget("Drop fields here to create filter conditions")
        self.where_drop_zone.field_dropped.connect(self.add_where_condition)
        parent_layout.addWidget(self.where_drop_zone)
        
        # Filter conditions container
        self.conditions_widget = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_widget)
        self.conditions_layout.setContentsMargins(0, 0, 0, 0)
        parent_layout.addWidget(self.conditions_widget)
    
    def add_select_field(self, field_data: Dict[str, Any], drop_widget):
        """Add a field to the SELECT clause"""
        if field_data in self.selected_fields:
            logger.warning(f"[QUERY-CANVAS] Field already selected: {field_data.get('name', 'Unknown')}")
            return
        
        self.selected_fields.append(field_data)
        self.create_selected_field_widget(field_data)
        self.query_changed.emit()
        
        logger.info(f"[QUERY-CANVAS] Added field to SELECT: {field_data.get('name', 'Unknown')}")
    
    def add_where_condition(self, field_data: Dict[str, Any], drop_widget):
        """Add a field as a WHERE condition"""
        # Create a proper visual filter condition widget
        condition_widget = VisualFilterCondition(field_data)
        condition_widget.condition_changed.connect(self.query_changed.emit)
        condition_widget.remove_requested.connect(self.remove_where_condition_widget)
        
        # Add to layout and track
        self.conditions_layout.addWidget(condition_widget)
        self.condition_widgets.append(condition_widget)
        
        self.query_changed.emit()
        
        logger.info(f"[QUERY-CANVAS] Added WHERE condition for: {field_data.get('name', 'Unknown')}")
    
    def create_selected_field_widget(self, field_data: Dict[str, Any]):
        """Create a widget for a selected field"""
        field_widget = QFrame()
        
        layout = QHBoxLayout(field_widget)
        layout.setContentsMargins(5, 3, 5, 3)
        
        # Field icon and name
        field_type = field_data.get('type', '').lower()
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(
            DraggableFieldWidget(field_data).get_field_type_icon(field_type)
        ).pixmap(16, 16))
        layout.addWidget(icon_label)
        
        name_label = QLabel(field_data.get('label', field_data.get('name', '')))
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon('fa5s.times'))
        remove_btn.setMaximumSize(20, 20)
        remove_btn.clicked.connect(lambda: self.remove_select_field(field_data, field_widget))
        layout.addWidget(remove_btn)
        
        self.selected_fields_layout.addWidget(field_widget)
    
    def remove_where_condition_widget(self, condition_widget: VisualFilterCondition):
        """Remove a WHERE condition widget"""
        if condition_widget in self.condition_widgets:
            self.condition_widgets.remove(condition_widget)
        
        condition_widget.setParent(None)
        condition_widget.deleteLater()
        self.query_changed.emit()
        
        logger.info(f"[QUERY-CANVAS] Removed WHERE condition")
    
    def remove_select_field(self, field_data: Dict[str, Any], widget: QWidget):
        """Remove a field from SELECT clause"""
        if field_data in self.selected_fields:
            self.selected_fields.remove(field_data)
        
        widget.setParent(None)
        widget.deleteLater()
        self.query_changed.emit()
        
        logger.info(f"[QUERY-CANVAS] Removed field from SELECT: {field_data.get('name', 'Unknown')}")
    
    
    def get_selected_fields(self) -> List[Dict[str, Any]]:
        """Get the list of selected fields"""
        return self.selected_fields.copy()
    
    def get_filter_conditions(self) -> List[Dict[str, Any]]:
        """Get the list of filter conditions from the actual widgets"""
        conditions = []
        for widget in self.condition_widgets:
            if widget.is_valid():
                conditions.append(widget.get_condition_data())
        return conditions
    
    def clear_all(self):
        """Clear all fields and conditions"""
        self.selected_fields.clear()
        
        # Clear field widgets
        for i in reversed(range(self.selected_fields_layout.count())):
            widget = self.selected_fields_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Clear condition widgets
        for widget in self.condition_widgets[:]:
            self.remove_where_condition_widget(widget)
        
        self.query_changed.emit()
        logger.info("[QUERY-CANVAS] Cleared all fields and conditions")