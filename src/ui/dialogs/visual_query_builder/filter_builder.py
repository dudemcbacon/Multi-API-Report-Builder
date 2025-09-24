"""
Visual filter builder for advanced WHERE clause construction
"""
import logging
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QComboBox, QLineEdit, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

logger = logging.getLogger(__name__)

class VisualFilterCondition(QFrame):
    """
    A visual widget representing a single filter condition
    """
    
    condition_changed = pyqtSignal()
    remove_requested = pyqtSignal(object)  # Emits self when remove is requested
    
    def __init__(self, field_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.field_data = field_data
        self.operator = '='
        self.value = ''
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the condition widget UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(8)
        
        # Field name (non-editable)
        field_label = QLabel(self.field_data.get('label', self.field_data.get('name', '')))
        layout.addWidget(field_label)
        
        # Operator dropdown
        self.operator_combo = QComboBox()
        self.populate_operators()
        self.operator_combo.currentTextChanged.connect(self.on_operator_changed)
        layout.addWidget(self.operator_combo)
        
        # Value input
        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText(self.get_value_placeholder())
        self.value_input.textChanged.connect(self.on_value_changed)
        layout.addWidget(self.value_input)
        
        # Remove button
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon('fa5s.times'))
        remove_btn.setMaximumSize(25, 25)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        layout.addWidget(remove_btn)
    
    def populate_operators(self):
        """Populate operators based on field type"""
        field_type = self.field_data.get('type', '').lower()
        
        # Base operators available for all types
        operators = ['=', '!=']
        
        # Type-specific operators
        if field_type in ['integer', 'double', 'currency', 'percent', 'date', 'datetime']:
            operators.extend(['>', '<', '>=', '<='])
        
        if field_type in ['string', 'textarea', 'email', 'phone']:
            operators.extend(['LIKE', 'NOT LIKE'])
        
        if field_type in ['picklist', 'multipicklist']:
            operators.extend(['IN', 'NOT IN'])
        
        # Special operators
        operators.extend(['IS NULL', 'IS NOT NULL'])
        
        for operator in operators:
            self.operator_combo.addItem(operator)
    
    def get_value_placeholder(self) -> str:
        """Get appropriate placeholder text for the value input"""
        field_type = self.field_data.get('type', '').lower()
        
        if field_type in ['picklist', 'multipicklist']:
            if self.field_data.get('picklistValues'):
                values = [pv.get('value', '') for pv in self.field_data['picklistValues'][:3]]
                return f"e.g., {', '.join(values)}"
        elif field_type in ['date', 'datetime']:
            return "e.g., 2024-01-01 or TODAY"
        elif field_type in ['integer', 'double', 'currency', 'percent']:
            return "Enter number..."
        elif field_type == 'boolean':
            return "true or false"
        
        return "Enter value..."
    
    def on_operator_changed(self):
        """Handle operator change"""
        self.operator = self.operator_combo.currentText()
        
        # Update value input based on operator
        if self.operator in ['IS NULL', 'IS NOT NULL']:
            self.value_input.setEnabled(False)
            self.value_input.clear()
            self.value_input.setPlaceholderText("(no value needed)")
        else:
            self.value_input.setEnabled(True)
            self.value_input.setPlaceholderText(self.get_value_placeholder())
        
        self.condition_changed.emit()
    
    def on_value_changed(self):
        """Handle value change"""
        self.value = self.value_input.text()
        self.condition_changed.emit()
    
    def get_condition_data(self) -> Dict[str, Any]:
        """Get the condition data"""
        return {
            'field': self.field_data,
            'operator': self.operator,
            'value': self.value
        }
    
    def is_valid(self) -> bool:
        """Check if the condition is valid"""
        if self.operator in ['IS NULL', 'IS NOT NULL']:
            return True
        return bool(self.value.strip())


class VisualFilterBuilder(QWidget):
    """
    Visual filter builder for constructing complex WHERE clauses
    """
    
    filters_changed = pyqtSignal(list)  # Emits list of filter conditions
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conditions = []
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the filter builder UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("Filter Conditions")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Logic type selector (for future enhancement)
        logic_label = QLabel("Logic:")
        header_layout.addWidget(logic_label)
        
        self.logic_combo = QComboBox()
        self.logic_combo.addItem("AND", "AND")
        self.logic_combo.addItem("OR", "OR")
        self.logic_combo.currentTextChanged.connect(self.on_logic_changed)
        header_layout.addWidget(self.logic_combo)
        
        layout.addLayout(header_layout)
        
        # Conditions scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(200)
        
        self.conditions_widget = QWidget()
        self.conditions_layout = QVBoxLayout(self.conditions_widget)
        self.conditions_layout.setContentsMargins(5, 5, 5, 5)
        self.conditions_layout.setSpacing(5)
        self.conditions_layout.addStretch()
        
        self.scroll_area.setWidget(self.conditions_widget)
        layout.addWidget(self.scroll_area)
        
        # Empty state
        self.empty_label = QLabel("No filter conditions yet.\\nDrag fields here or use the query canvas above.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.conditions_layout.insertWidget(0, self.empty_label)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        # Condition count
        self.condition_count_label = QLabel("0 conditions")
        controls_layout.addWidget(self.condition_count_label)
        
        controls_layout.addStretch()
        
        # Clear all button
        clear_btn = QPushButton("Clear All")
        clear_btn.setIcon(qta.icon('fa5s.trash'))
        clear_btn.clicked.connect(self.clear_all_conditions)
        controls_layout.addWidget(clear_btn)
        
        layout.addLayout(controls_layout)
    
    def add_condition(self, field_data: Dict[str, Any]):
        """Add a new filter condition"""
        condition_widget = VisualFilterCondition(field_data)
        condition_widget.condition_changed.connect(self.on_condition_changed)
        condition_widget.remove_requested.connect(self.remove_condition)
        
        # Hide empty label if this is the first condition
        if not self.conditions:
            self.empty_label.hide()
        
        # Insert before the stretch
        self.conditions_layout.insertWidget(len(self.conditions), condition_widget)
        self.conditions.append(condition_widget)
        
        self.update_condition_count()
        self.on_condition_changed()
        
        logger.info(f"[FILTER-BUILDER] Added condition for field: {field_data.get('name', 'Unknown')}")
    
    def remove_condition(self, condition_widget: VisualFilterCondition):
        """Remove a filter condition"""
        if condition_widget in self.conditions:
            self.conditions.remove(condition_widget)
            condition_widget.setParent(None)
            condition_widget.deleteLater()
            
            # Show empty label if no conditions left
            if not self.conditions:
                self.empty_label.show()
            
            self.update_condition_count()
            self.on_condition_changed()
            
            logger.info("[FILTER-BUILDER] Removed filter condition")
    
    def clear_all_conditions(self):
        """Clear all filter conditions"""
        for condition in self.conditions[:]:  # Copy list to avoid modification during iteration
            self.remove_condition(condition)
    
    def on_condition_changed(self):
        """Handle condition changes"""
        # Get all valid conditions
        valid_conditions = []
        for condition_widget in self.conditions:
            if condition_widget.is_valid():
                valid_conditions.append(condition_widget.get_condition_data())
        
        self.filters_changed.emit(valid_conditions)
        logger.debug(f"[FILTER-BUILDER] Conditions changed: {len(valid_conditions)} valid conditions")
    
    def on_logic_changed(self):
        """Handle logic type change"""
        # This would affect how conditions are combined
        # For now, just trigger a change event
        self.on_condition_changed()
    
    def update_condition_count(self):
        """Update the condition count label"""
        count = len(self.conditions)
        self.condition_count_label.setText(f"{count} condition{'s' if count != 1 else ''}")
    
    def get_filter_data(self) -> Dict[str, Any]:
        """Get all filter data"""
        valid_conditions = []
        for condition_widget in self.conditions:
            if condition_widget.is_valid():
                valid_conditions.append(condition_widget.get_condition_data())
        
        return {
            'logic': self.logic_combo.currentData(),
            'conditions': valid_conditions
        }
    
    def has_conditions(self) -> bool:
        """Check if there are any valid conditions"""
        return any(condition.is_valid() for condition in self.conditions)