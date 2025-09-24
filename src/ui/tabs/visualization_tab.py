"""
Visualization Tab for creating charts and visualizations from data
"""
import logging
from typing import Optional
import polars as pl

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QMessageBox, QSplitter, QGroupBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal
import qtawesome as qta

from src.ui.visualization import VisualizationManager, ChartWidget

logger = logging.getLogger(__name__)

class VisualizationTab(QWidget):
    """
    Tab for creating visualizations and charts from loaded data
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.available_datasets = {}  # Dict to store loaded datasets
        self.current_dataset = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the visualization tab UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title and instructions
        title_layout = QHBoxLayout()
        
        title = QLabel("Data Visualization")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        title_layout.addWidget(title)
        
        title_layout.addStretch()
        
        # Refresh datasets button
        refresh_btn = QPushButton("Refresh Data")
        refresh_btn.setIcon(qta.icon('fa5s.sync'))
        refresh_btn.clicked.connect(self.refresh_datasets)
        title_layout.addWidget(refresh_btn)
        
        layout.addLayout(title_layout)
        
        # Instructions
        instructions = QLabel(
            "Create charts and visualizations from your loaded data. "
            "Select a dataset below and configure your chart settings."
        )
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left panel - Dataset selection
        self.setup_dataset_panel(splitter)
        
        # Right panel - Visualization manager
        self.setup_visualization_panel(splitter)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 0)  # Dataset panel fixed
        splitter.setStretchFactor(1, 1)  # Visualization panel expandable
        splitter.setSizes([250, 950])
    
    def setup_dataset_panel(self, parent_splitter):
        """Setup the dataset selection panel"""
        dataset_widget = QWidget()
        dataset_layout = QVBoxLayout(dataset_widget)
        
        # Dataset selection
        dataset_group = QGroupBox("Available Datasets")
        dataset_group_layout = QVBoxLayout(dataset_group)
        
        # Dataset list
        self.dataset_list = QListWidget()
        self.dataset_list.itemClicked.connect(self.on_dataset_selected)
        dataset_group_layout.addWidget(self.dataset_list)
        
        # Dataset info
        self.dataset_info = QLabel("No dataset selected")
        self.dataset_info.setWordWrap(True)
        self.dataset_info.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        dataset_group_layout.addWidget(self.dataset_info)
        
        dataset_layout.addWidget(dataset_group)
        
        # Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        # Clear visualization button
        clear_btn = QPushButton("Clear Chart")
        clear_btn.setIcon(qta.icon('fa5s.times'))
        clear_btn.clicked.connect(self.clear_visualization)
        actions_layout.addWidget(clear_btn)
        
        dataset_layout.addWidget(actions_group)
        
        dataset_layout.addStretch()
        parent_splitter.addWidget(dataset_widget)
    
    def setup_visualization_panel(self, parent_splitter):
        """Setup the visualization configuration panel"""
        # Create visualization manager
        self.viz_manager = VisualizationManager()
        self.viz_manager.chart_created.connect(self.on_chart_created)
        
        parent_splitter.addWidget(self.viz_manager)
    
    def refresh_datasets(self):
        """Refresh the list of available datasets"""
        self.dataset_list.clear()
        self.available_datasets.clear()
        
        # Get datasets from main window tabs
        if hasattr(self.main_window, 'source_data_tab'):
            source_tab = self.main_window.source_data_tab
            
            # Look through all open data tabs
            for i in range(source_tab.tab_widget.tabCount()):
                tab_name = source_tab.tab_widget.tabText(i)
                widget = source_tab.tab_widget.widget(i)
                
                # Check if it's a data grid with data
                if hasattr(widget, 'get_current_data'):
                    dataframe = widget.get_current_data()
                    if dataframe is not None and not dataframe.is_empty():
                        self.available_datasets[tab_name] = {
                            'dataframe': dataframe,
                            'widget': widget,
                            'tab_index': i
                        }
                        
                        # Add to list
                        item = QListWidgetItem(tab_name)
                        item.setData(Qt.ItemDataRole.UserRole, tab_name)
                        item.setIcon(qta.icon('fa5s.table'))
                        self.dataset_list.addItem(item)
        
        logger.info(f"[VIZ-TAB] Refreshed datasets: {len(self.available_datasets)} available")
        
        if not self.available_datasets:
            self.dataset_info.setText("No datasets available. Load some data first.")
            self.viz_manager.set_dataframe(None)
        else:
            self.dataset_info.setText(f"{len(self.available_datasets)} datasets available")
    
    def on_dataset_selected(self, item: QListWidgetItem):
        """Handle dataset selection"""
        dataset_name = item.data(Qt.ItemDataRole.UserRole)
        if dataset_name not in self.available_datasets:
            return
        
        dataset = self.available_datasets[dataset_name]
        dataframe = dataset['dataframe']
        
        if dataframe is None or dataframe.is_empty():
            QMessageBox.warning(self, "No Data", "Selected dataset has no data.")
            return
        
        self.current_dataset = dataset_name
        
        # Update dataset info with enhanced metadata
        info_text = f"<b>{dataset_name}</b><br>"
        
        # Add source information if available
        if 'source_type' in dataset:
            source_type = dataset['source_type'].replace('_', ' ').title()
            info_text += f"<b>Source:</b> {source_type}<br>"
        
        info_text += f"<b>Rows:</b> {len(dataframe):,}<br>"
        info_text += f"<b>Columns:</b> {len(dataframe.columns)}<br>"
        info_text += f"<b>Size:</b> {dataframe.estimated_size('mb'):.1f} MB<br>"
        
        # Add load time if available
        if 'load_time' in dataset and dataset['load_time']:
            load_time = dataset['load_time'].strftime("%H:%M:%S")
            info_text += f"<b>Loaded:</b> {load_time}<br>"
        
        # Add column preview
        if len(dataframe.columns) <= 5:
            columns_text = ", ".join(dataframe.columns)
        else:
            columns_text = ", ".join(dataframe.columns[:5]) + f"... (+{len(dataframe.columns)-5})"
        info_text += f"<b>Columns:</b> {columns_text}"
        
        self.dataset_info.setText(info_text)
        
        # Set dataframe in visualization manager
        self.viz_manager.set_dataframe(dataframe)
        
        logger.info(f"[VIZ-TAB] Selected dataset: {dataset_name} ({len(dataframe)} rows)")
    
    def on_chart_created(self, chart_config):
        """Handle chart creation"""
        logger.info(f"[VIZ-TAB] Chart created: {chart_config.get('title', 'Unknown')}")
        
        # Could emit signal to main window or save chart configuration
        # For now, just log the success
    
    def clear_visualization(self):
        """Clear current visualization"""
        self.viz_manager.clear_visualization()
        self.current_dataset = None
        self.dataset_info.setText("No dataset selected")
        
        # Clear selection in list
        self.dataset_list.clearSelection()
        
        logger.info("[VIZ-TAB] Visualization cleared")
    
    def add_dataset(self, name: str, dataframe: pl.DataFrame):
        """
        Add a dataset programmatically
        
        Args:
            name: Name of the dataset
            dataframe: Polars DataFrame
        """
        if dataframe is None or dataframe.is_empty():
            return
        
        self.available_datasets[name] = {
            'dataframe': dataframe,
            'widget': None,
            'tab_index': -1,
            'source_type': 'custom',
            'load_time': None
        }
        
        # Add to list
        item = QListWidgetItem(name)
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setIcon(qta.icon('fa5s.chart-bar'))
        self.dataset_list.addItem(item)
        
        logger.info(f"[VIZ-TAB] Added dataset: {name} ({len(dataframe)} rows)")
        
    def add_dataset_from_grid(self, name: str, dataframe: pl.DataFrame, data_grid_widget, source_type: str = 'unknown'):
        """
        Add a dataset from a data grid with enhanced metadata
        
        Args:
            name: Name of the dataset
            dataframe: Polars DataFrame
            data_grid_widget: The InteractiveDataGrid widget
            source_type: Type of data source (salesforce, woocommerce, avalara, custom)
        """
        if dataframe is None or dataframe.is_empty():
            return
        
        from datetime import datetime
        
        # Detect source type from name if not provided
        if source_type == 'unknown':
            name_lower = name.lower()
            if 'salesforce' in name_lower or 'sf_' in name_lower:
                source_type = 'salesforce'
            elif 'woocommerce' in name_lower or 'woo_' in name_lower:
                source_type = 'woocommerce'
            elif 'avalara' in name_lower or 'tax' in name_lower:
                source_type = 'avalara'
            elif 'custom' in name_lower or 'soql' in name_lower:
                source_type = 'custom_report'
            else:
                source_type = 'data'
        
        self.available_datasets[name] = {
            'dataframe': dataframe,
            'widget': data_grid_widget,
            'tab_index': -1,
            'source_type': source_type,
            'load_time': datetime.now(),
            'row_count': len(dataframe),
            'column_count': len(dataframe.columns),
            'columns': list(dataframe.columns)
        }
        
        # Get appropriate icon based on source type
        icon_map = {
            'salesforce': 'fa5b.salesforce',
            'woocommerce': 'fa5b.wordpress',
            'avalara': 'fa5s.calculator',
            'custom_report': 'fa5s.code',
            'data': 'fa5s.table',
            'unknown': 'fa5s.question'
        }
        icon = icon_map.get(source_type, 'fa5s.table')
        
        # Add to list
        item = QListWidgetItem(f"{name}")
        item.setData(Qt.ItemDataRole.UserRole, name)
        item.setIcon(qta.icon(icon))
        
        # Add tooltip with metadata
        tooltip_text = f"Source: {source_type.replace('_', ' ').title()}\n"
        tooltip_text += f"Rows: {len(dataframe):,}\n"
        tooltip_text += f"Columns: {len(dataframe.columns)}\n"
        tooltip_text += f"Size: {dataframe.estimated_size('mb'):.1f} MB"
        item.setToolTip(tooltip_text)
        
        self.dataset_list.addItem(item)
        
        # Update dataset info if this is the first dataset
        if len(self.available_datasets) == 1:
            self.dataset_info.setText(f"1 dataset available. Click to select.")
        else:
            self.dataset_info.setText(f"{len(self.available_datasets)} datasets available")
        
        logger.info(f"[VIZ-TAB] Added dataset from grid: {name} ({len(dataframe)} rows, {source_type})")
    
    def visualize_dataset(self, dataset_name: str):
        """
        Switch to this tab and select the specified dataset for visualization
        
        Args:
            dataset_name: Name of the dataset to visualize
        """
        if dataset_name not in self.available_datasets:
            logger.warning(f"[VIZ-TAB] Dataset '{dataset_name}' not found for visualization")
            return
        
        # Find and select the dataset in the list
        for i in range(self.dataset_list.count()):
            item = self.dataset_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == dataset_name:
                self.dataset_list.setCurrentItem(item)
                self.on_dataset_selected(item)
                break
        
        logger.info(f"[VIZ-TAB] Auto-selected dataset for visualization: {dataset_name}")
    
    def get_current_chart_widget(self) -> Optional[ChartWidget]:
        """Get the current chart widget"""
        if hasattr(self.viz_manager, 'chart_widget'):
            return self.viz_manager.chart_widget
        return None