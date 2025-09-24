"""
Visualization Manager for chart type selection and configuration
"""
import logging
from typing import Dict, Any, List, Optional
import polars as pl

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox, QComboBox,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QSpinBox,
    QCheckBox, QLineEdit, QTextEdit, QMessageBox, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

from .chart_widget import ChartWidget
from .advanced_chart_types import ADVANCED_CHART_TYPES

logger = logging.getLogger(__name__)

class VisualizationManager(QWidget):
    """
    Widget for managing chart configuration and generation
    """
    
    chart_created = pyqtSignal(dict)  # Emitted when chart is created
    
    # Chart type configurations - basic charts
    BASIC_CHART_TYPES = {
        'bar': {
            'name': 'Bar Chart',
            'description': 'Compare values across categories',
            'required_columns': ['x_column', 'y_column'],
            'optional_columns': ['color_column'],
            'icon': 'fa5s.chart-bar',
            'category': 'basic'
        },
        'line': {
            'name': 'Line Chart',
            'description': 'Show trends over time or continuous data',
            'required_columns': ['x_column', 'y_column'],
            'optional_columns': ['color_column'],
            'icon': 'fa5s.chart-line',
            'category': 'basic'
        },
        'scatter': {
            'name': 'Scatter Plot',
            'description': 'Show relationships between two variables',
            'required_columns': ['x_column', 'y_column'],
            'optional_columns': ['color_column', 'size_column'],
            'icon': 'fa5s.braille',
            'category': 'basic'
        },
        'pie': {
            'name': 'Pie Chart',
            'description': 'Show proportions of a whole',
            'required_columns': ['values_column', 'names_column'],
            'optional_columns': [],
            'icon': 'fa5s.chart-pie',
            'category': 'basic'
        },
        'histogram': {
            'name': 'Histogram',
            'description': 'Show distribution of a single variable',
            'required_columns': ['x_column'],
            'optional_columns': ['color_column'],
            'icon': 'fa5s.chart-area',
            'category': 'basic'
        },
        'box': {
            'name': 'Box Plot',
            'description': 'Show distribution and outliers',
            'required_columns': ['y_column'],
            'optional_columns': ['x_column', 'color_column'],
            'icon': 'fa5s.square',
            'category': 'basic'
        }
    }
    
    @property
    def CHART_TYPES(self):
        """Combined chart types including basic and advanced"""
        combined = self.BASIC_CHART_TYPES.copy()
        # Mark advanced charts with category
        for chart_type, config in ADVANCED_CHART_TYPES.items():
            config_copy = config.copy()
            config_copy['category'] = 'advanced'
            combined[chart_type] = config_copy
        return combined
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_dataframe = None
        self.available_columns = []
        self.numeric_columns = []
        self.text_columns = []
        self.date_columns = []
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the visualization manager UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create splitter for configuration and chart
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Chart configuration
        self.setup_configuration_panel(splitter)
        
        # Right panel - Chart display
        self.setup_chart_panel(splitter)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)  # Configuration panel
        splitter.setStretchFactor(1, 2)  # Chart panel
        splitter.setSizes([400, 800])
    
    def setup_configuration_panel(self, parent_splitter):
        """Setup the chart configuration panel"""
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # Chart type selection
        self.setup_chart_type_selection(config_layout)
        
        # Column mapping
        self.setup_column_mapping(config_layout)
        
        # Chart options
        self.setup_chart_options(config_layout)
        
        # Action buttons
        self.setup_action_buttons(config_layout)
        
        parent_splitter.addWidget(config_widget)
    
    def setup_chart_type_selection(self, layout):
        """Setup chart type selection with categories"""
        chart_type_group = QGroupBox("Chart Type")
        chart_type_layout = QVBoxLayout(chart_type_group)
        
        # Chart category tabs or section
        category_layout = QHBoxLayout()
        
        # Category filter combo
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Charts", "all")
        self.category_combo.addItem("Basic Charts", "basic")
        self.category_combo.addItem("Advanced Charts", "advanced")
        self.category_combo.currentIndexChanged.connect(self.on_category_changed)
        category_layout.addWidget(QLabel("Category:"))
        category_layout.addWidget(self.category_combo)
        category_layout.addStretch()
        
        chart_type_layout.addLayout(category_layout)
        
        # Chart type combo box
        self.chart_type_combo = QComboBox()
        self.populate_chart_types("all")  # Start with all charts
        self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
        chart_type_layout.addWidget(self.chart_type_combo)
        
        # Chart type description
        self.chart_description = QLabel("Select a chart type to see description")
        self.chart_description.setWordWrap(True)
        self.chart_description.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        chart_type_layout.addWidget(self.chart_description)
        
        layout.addWidget(chart_type_group)
    
    def populate_chart_types(self, category_filter="all"):
        """Populate chart type combo box based on category filter"""
        self.chart_type_combo.clear()
        
        chart_types = self.CHART_TYPES
        
        # Add basic charts first
        if category_filter in ["all", "basic"]:
            for chart_type, config in self.BASIC_CHART_TYPES.items():
                icon_text = "📊" if config['category'] == 'basic' else "📈"
                self.chart_type_combo.addItem(f"{icon_text} {config['name']}", chart_type)
        
        # Add separator if showing both categories
        if category_filter == "all" and ADVANCED_CHART_TYPES:
            self.chart_type_combo.insertSeparator(self.chart_type_combo.count())
        
        # Add advanced charts
        if category_filter in ["all", "advanced"]:
            for chart_type, config in ADVANCED_CHART_TYPES.items():
                icon_text = "🔬"  # Advanced chart indicator
                self.chart_type_combo.addItem(f"{icon_text} {config['name']}", chart_type)
    
    def on_category_changed(self):
        """Handle category filter change"""
        category = self.category_combo.currentData()
        self.populate_chart_types(category)
        # Reset selection
        if self.chart_type_combo.count() > 0:
            self.chart_type_combo.setCurrentIndex(0)
            self.on_chart_type_changed()
    
    def setup_column_mapping(self, layout):
        """Setup column mapping controls"""
        self.column_group = QGroupBox("Column Mapping")
        self.column_layout = QGridLayout(self.column_group)
        
        # These will be populated when chart type is selected
        self.column_combos = {}
        
        layout.addWidget(self.column_group)
    
    def setup_chart_options(self, layout):
        """Setup chart options"""
        options_group = QGroupBox("Chart Options")
        options_layout = QGridLayout(options_group)
        
        # Chart title
        options_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter chart title...")
        options_layout.addWidget(self.title_edit, 0, 1)
        
        # Color theme
        options_layout.addWidget(QLabel("Theme:"), 1, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['plotly_white', 'plotly_dark', 'ggplot2', 'seaborn', 'simple_white'])
        options_layout.addWidget(self.theme_combo, 1, 1)
        
        # Height
        options_layout.addWidget(QLabel("Height:"), 2, 0)
        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 1000)
        self.height_spin.setValue(500)
        self.height_spin.setSuffix(" px")
        options_layout.addWidget(self.height_spin, 2, 1)
        
        # Show legend
        self.show_legend_check = QCheckBox("Show Legend")
        self.show_legend_check.setChecked(True)
        options_layout.addWidget(self.show_legend_check, 3, 0, 1, 2)
        
        layout.addWidget(options_group)
    
    def setup_action_buttons(self, layout):
        """Setup action buttons"""
        buttons_layout = QHBoxLayout()
        
        # Preview button
        self.preview_btn = QPushButton("Preview Chart")
        self.preview_btn.setIcon(qta.icon('fa5s.eye'))
        self.preview_btn.clicked.connect(self.preview_chart)
        self.preview_btn.setEnabled(False)
        buttons_layout.addWidget(self.preview_btn)
        
        # Create button
        self.create_btn = QPushButton("Create Chart")
        self.create_btn.setIcon(qta.icon('fa5s.chart-bar'))
        self.create_btn.clicked.connect(self.create_chart)
        self.create_btn.setEnabled(False)
        buttons_layout.addWidget(self.create_btn)
        
        layout.addLayout(buttons_layout)
        layout.addStretch()
    
    def setup_chart_panel(self, parent_splitter):
        """Setup the chart display panel"""
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        
        # Chart widget
        self.chart_widget = ChartWidget()
        chart_layout.addWidget(self.chart_widget)
        
        parent_splitter.addWidget(chart_widget)
    
    def set_dataframe(self, dataframe: pl.DataFrame):
        """Set the dataframe for visualization"""
        if dataframe is None or dataframe.is_empty():
            self.current_dataframe = None
            self.available_columns = []
            self.update_ui_state()
            return
        
        self.current_dataframe = dataframe
        self.available_columns = list(dataframe.columns)
        
        # Categorize columns by data type
        self.numeric_columns = []
        self.text_columns = []
        self.date_columns = []
        
        for col in dataframe.columns:
            dtype = dataframe[col].dtype
            if dtype in [pl.Int64, pl.Int32, pl.Float64, pl.Float32]:
                self.numeric_columns.append(col)
            elif dtype in [pl.Date, pl.Datetime]:
                self.date_columns.append(col)
            else:
                self.text_columns.append(col)
        
        logger.info(f"[VIZ-MANAGER] DataFrame set: {len(dataframe)} rows, {len(self.available_columns)} columns")
        logger.info(f"[VIZ-MANAGER] Numeric: {len(self.numeric_columns)}, Text: {len(self.text_columns)}, Date: {len(self.date_columns)}")
        
        self.update_ui_state()
        self.on_chart_type_changed()  # Refresh column mappings
    
    def update_ui_state(self):
        """Update UI state based on available data"""
        has_data = self.current_dataframe is not None and not self.current_dataframe.is_empty()
        
        self.chart_type_combo.setEnabled(has_data)
        self.preview_btn.setEnabled(has_data)
        self.create_btn.setEnabled(has_data)
        
        if not has_data:
            self.chart_widget.clear_chart()
    
    def on_chart_type_changed(self):
        """Handle chart type selection change"""
        if not self.available_columns:
            return
        
        chart_type = self.chart_type_combo.currentData()
        if not chart_type:
            return
        
        config = self.CHART_TYPES[chart_type]
        
        # Update description
        self.chart_description.setText(config['description'])
        
        # Clear existing column mappings
        for i in reversed(range(self.column_layout.count())):
            self.column_layout.itemAt(i).widget().setParent(None)
        
        self.column_combos.clear()
        
        # Create column mappings for required columns
        row = 0
        for col_type in config['required_columns']:
            label_text = self._get_column_label(col_type)
            label = QLabel(f"{label_text}*:")
            self.column_layout.addWidget(label, row, 0)
            
            combo = QComboBox()
            combo.addItem("Select column...")
            self._populate_column_combo(combo, col_type)
            self.column_combos[col_type] = combo
            self.column_layout.addWidget(combo, row, 1)
            
            row += 1
        
        # Create column mappings for optional columns
        for col_type in config['optional_columns']:
            label_text = self._get_column_label(col_type)
            label = QLabel(f"{label_text}:")
            self.column_layout.addWidget(label, row, 0)
            
            combo = QComboBox()
            combo.addItem("None (optional)")
            self._populate_column_combo(combo, col_type)
            self.column_combos[col_type] = combo
            self.column_layout.addWidget(combo, row, 1)
            
            row += 1
        
        # Set default title
        if not self.title_edit.text():
            self.title_edit.setText(f"{config['name']} - {self.available_columns[0] if self.available_columns else 'Data'}")
    
    def _get_column_label(self, col_type: str) -> str:
        """Get user-friendly label for column type"""
        labels = {
            'x_column': 'X Axis',
            'y_column': 'Y Axis',
            'color_column': 'Color By',
            'size_column': 'Size By',
            'values_column': 'Values',
            'names_column': 'Labels'
        }
        return labels.get(col_type, col_type.replace('_', ' ').title())
    
    def _populate_column_combo(self, combo: QComboBox, col_type: str):
        """Populate column combo box based on column type"""
        if col_type in ['y_column', 'values_column', 'size_column']:
            # Numeric columns preferred
            for col in self.numeric_columns:
                combo.addItem(col)
            # Add other columns as options
            for col in self.text_columns + self.date_columns:
                if col not in self.numeric_columns:
                    combo.addItem(f"{col} (non-numeric)")
        elif col_type in ['x_column', 'names_column']:
            # All columns
            for col in self.available_columns:
                combo.addItem(col)
        elif col_type == 'color_column':
            # Categorical columns preferred
            for col in self.text_columns:
                combo.addItem(col)
            for col in self.numeric_columns + self.date_columns:
                if col not in self.text_columns:
                    combo.addItem(f"{col} (continuous)")
        else:
            # All columns
            for col in self.available_columns:
                combo.addItem(col)
    
    def get_chart_config(self) -> Optional[Dict[str, Any]]:
        """Get current chart configuration"""
        if not self.current_dataframe:
            return None
        
        chart_type = self.chart_type_combo.currentData()
        if not chart_type:
            return None
        
        config = {
            'type': chart_type,
            'title': self.title_edit.text() or f"{self.CHART_TYPES[chart_type]['name']}",
            'template': self.theme_combo.currentText(),
            'height': self.height_spin.value(),
            'show_legend': self.show_legend_check.isChecked()
        }
        
        # Add column mappings
        for col_type, combo in self.column_combos.items():
            selected = combo.currentText()
            if selected and not selected.startswith(('Select', 'None')):
                # Clean column name (remove non-numeric indicators)
                column_name = selected.split(' (')[0]
                config[col_type] = column_name
        
        # Validate required columns
        chart_config = self.CHART_TYPES[chart_type]
        for required_col in chart_config['required_columns']:
            if required_col not in config:
                QMessageBox.warning(self, "Missing Required Column", 
                                  f"Please select a column for {self._get_column_label(required_col)}")
                return None
        
        return config
    
    def preview_chart(self):
        """Preview the chart with current configuration"""
        config = self.get_chart_config()
        if not config:
            return
        
        # Create chart in widget
        success = self.chart_widget.create_chart(self.current_dataframe, config)
        if success:
            logger.info(f"[VIZ-MANAGER] Chart preview created: {config['type']}")
    
    def create_chart(self):
        """Create and finalize the chart"""
        config = self.get_chart_config()
        if not config:
            return
        
        # Create chart in widget
        success = self.chart_widget.create_chart(self.current_dataframe, config)
        if success:
            logger.info(f"[VIZ-MANAGER] Chart created: {config['type']}")
            self.chart_created.emit(config)
    
    def clear_visualization(self):
        """Clear current visualization"""
        self.chart_widget.clear_chart()
        self.current_dataframe = None
        self.available_columns = []
        self.update_ui_state()