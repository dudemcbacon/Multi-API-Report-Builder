"""
Chart Widget for displaying Plotly visualizations in PyQt6
"""
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import polars as pl

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QUrl, pyqtSignal
import qtawesome as qta

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    import plotly.express as px
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    logger.warning("Plotly not available - visualization features will be disabled")
    PLOTLY_AVAILABLE = False
    go = None
    px = None
    pyo = None

class ChartWidget(QWidget):
    """
    Widget for displaying Plotly charts using QWebEngineView
    """
    
    chart_exported = pyqtSignal(str)  # Emitted when chart is exported
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_chart = None
        self.temp_file_path = None
        self.dataframe = None
        self.chart_config = {}
        
        self.setup_ui()
        
        if not PLOTLY_AVAILABLE:
            self.show_plotly_unavailable()
    
    def setup_ui(self):
        """Setup the chart widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Chart controls toolbar
        self.setup_chart_controls(layout)
        
        # Web view for displaying charts
        if PLOTLY_AVAILABLE:
            self.web_view = QWebEngineView()
            layout.addWidget(self.web_view)
        else:
            # Placeholder when Plotly is not available
            self.placeholder_label = QLabel("Plotly visualization library not available.\nInstall with: pip install plotly")
            self.placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.placeholder_label.setStyleSheet("color: #666; font-size: 14px; padding: 50px;")
            layout.addWidget(self.placeholder_label)
    
    def setup_chart_controls(self, layout):
        """Setup chart control buttons"""
        controls_layout = QHBoxLayout()
        
        # Chart title
        self.chart_title = QLabel("Chart Visualization")
        self.chart_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        controls_layout.addWidget(self.chart_title)
        
        controls_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("Export")
        export_btn.setIcon(qta.icon('fa5s.download'))
        export_btn.clicked.connect(self.export_chart)
        export_btn.setEnabled(PLOTLY_AVAILABLE)
        controls_layout.addWidget(export_btn)
        
        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setIcon(qta.icon('fa5s.sync'))
        refresh_btn.clicked.connect(self.refresh_chart)
        refresh_btn.setEnabled(PLOTLY_AVAILABLE)
        controls_layout.addWidget(refresh_btn)
        
        layout.addLayout(controls_layout)
    
    def show_plotly_unavailable(self):
        """Show message when Plotly is not available"""
        self.chart_title.setText("Plotly Not Available")
        
    def create_chart(self, dataframe: pl.DataFrame, chart_config: Dict[str, Any]) -> bool:
        """
        Create and display a chart from a Polars DataFrame
        
        Args:
            dataframe: Polars DataFrame with data
            chart_config: Chart configuration dictionary
            
        Returns:
            bool: True if chart was created successfully
        """
        if not PLOTLY_AVAILABLE:
            logger.error("[CHART-WIDGET] Plotly not available")
            return False
        
        if dataframe is None or dataframe.is_empty():
            logger.error("[CHART-WIDGET] No data provided for chart")
            return False
        
        try:
            self.dataframe = dataframe
            self.chart_config = chart_config
            
            chart_type = chart_config.get('type', 'bar')
            title = chart_config.get('title', 'Chart')
            x_column = chart_config.get('x_column')
            y_column = chart_config.get('y_column')
            color_column = chart_config.get('color_column')
            
            # Validate required columns
            if x_column and x_column not in dataframe.columns:
                raise ValueError(f"X column '{x_column}' not found in data")
            if y_column and y_column not in dataframe.columns:
                raise ValueError(f"Y column '{y_column}' not found in data")
            
            # Create chart based on type
            if chart_type == 'bar':
                fig = self._create_bar_chart(dataframe, chart_config)
            elif chart_type == 'line':
                fig = self._create_line_chart(dataframe, chart_config)
            elif chart_type == 'scatter':
                fig = self._create_scatter_chart(dataframe, chart_config)
            elif chart_type == 'pie':
                fig = self._create_pie_chart(dataframe, chart_config)
            elif chart_type == 'histogram':
                fig = self._create_histogram(dataframe, chart_config)
            elif chart_type == 'box':
                fig = self._create_box_chart(dataframe, chart_config)
            else:
                # Check if it's an advanced chart type
                fig = self._create_advanced_chart(dataframe, chart_config)
                if fig is None:
                    raise ValueError(f"Unsupported chart type: {chart_type}")
            
            # Update chart title
            self.chart_title.setText(title)
            
            # Display chart
            self._display_chart(fig)
            self.current_chart = fig
            
            logger.info(f"[CHART-WIDGET] Created {chart_type} chart with {len(dataframe)} rows")
            return True
            
        except Exception as e:
            logger.error(f"[CHART-WIDGET] Error creating chart: {e}")
            QMessageBox.critical(self, "Chart Error", f"Failed to create chart: {str(e)}")
            return False
    
    def _create_bar_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a bar chart"""
        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')
        title = config.get('title', 'Bar Chart')
        
        # Convert to pandas for Plotly Express (native Polars support coming soon)
        df_pandas = dataframe.to_pandas()
        
        fig = px.bar(
            df_pandas,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            labels=config.get('labels', {}),
            template='plotly_white'
        )
        
        fig.update_layout(
            xaxis_tickangle=-45 if len(df_pandas) > 10 else 0,
            height=500
        )
        
        return fig
    
    def _create_line_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a line chart"""
        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')
        title = config.get('title', 'Line Chart')
        
        df_pandas = dataframe.to_pandas()
        
        fig = px.line(
            df_pandas,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            labels=config.get('labels', {}),
            template='plotly_white'
        )
        
        fig.update_layout(height=500)
        return fig
    
    def _create_scatter_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a scatter chart"""
        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')
        size_col = config.get('size_column')
        title = config.get('title', 'Scatter Chart')
        
        df_pandas = dataframe.to_pandas()
        
        fig = px.scatter(
            df_pandas,
            x=x_col,
            y=y_col,
            color=color_col,
            size=size_col,
            title=title,
            labels=config.get('labels', {}),
            template='plotly_white'
        )
        
        fig.update_layout(height=500)
        return fig
    
    def _create_pie_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a pie chart"""
        values_col = config.get('values_column')
        names_col = config.get('names_column')
        title = config.get('title', 'Pie Chart')
        
        df_pandas = dataframe.to_pandas()
        
        fig = px.pie(
            df_pandas,
            values=values_col,
            names=names_col,
            title=title,
            template='plotly_white'
        )
        
        fig.update_layout(height=500)
        return fig
    
    def _create_histogram(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a histogram"""
        x_col = config.get('x_column')
        color_col = config.get('color_column')
        title = config.get('title', 'Histogram')
        
        df_pandas = dataframe.to_pandas()
        
        fig = px.histogram(
            df_pandas,
            x=x_col,
            color=color_col,
            title=title,
            labels=config.get('labels', {}),
            template='plotly_white'
        )
        
        fig.update_layout(height=500)
        return fig
    
    def _create_box_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """Create a box plot"""
        x_col = config.get('x_column')
        y_col = config.get('y_column')
        color_col = config.get('color_column')
        title = config.get('title', 'Box Plot')
        
        df_pandas = dataframe.to_pandas()
        
        fig = px.box(
            df_pandas,
            x=x_col,
            y=y_col,
            color=color_col,
            title=title,
            labels=config.get('labels', {}),
            template='plotly_white'
        )
        
        fig.update_layout(height=500)
        return fig
    
    def _display_chart(self, fig: go.Figure):
        """Display chart in web view"""
        try:
            # Create HTML content
            html_content = pyo.plot(fig, output_type='div', include_plotlyjs=True)
            
            # Create temporary HTML file
            if self.temp_file_path:
                try:
                    Path(self.temp_file_path).unlink()
                except:
                    pass
            
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False)
            temp_file.write(html_content)
            temp_file.close()
            
            self.temp_file_path = temp_file.name
            
            # Load in web view
            self.web_view.load(QUrl.fromLocalFile(self.temp_file_path))
            
            logger.info(f"[CHART-WIDGET] Chart displayed in web view: {self.temp_file_path}")
            
        except Exception as e:
            logger.error(f"[CHART-WIDGET] Error displaying chart: {e}")
            raise
    
    def refresh_chart(self):
        """Refresh the current chart"""
        if self.dataframe is not None and self.chart_config:
            self.create_chart(self.dataframe, self.chart_config)
    
    def export_chart(self):
        """Export chart to file using enhanced export manager"""
        if not self.current_chart:
            QMessageBox.information(self, "No Chart", "No chart to export.")
            return
        
        try:
            from PyQt6.QtWidgets import QFileDialog, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
            from .export_manager import ExportManager
            
            # Create export format selection dialog
            dialog = QDialog(self)
            dialog.setWindowTitle("Export Chart")
            dialog.setFixedSize(400, 200)
            
            layout = QVBoxLayout(dialog)
            
            # Format selection
            layout.addWidget(QLabel("Select export format:"))
            format_combo = QComboBox()
            
            export_manager = ExportManager(self)
            supported_formats = export_manager.get_supported_formats()
            
            for fmt in supported_formats:
                format_combo.addItem(f"{fmt['name']} (*.{fmt['extension']})", fmt['type'])
            
            layout.addWidget(format_combo)
            
            # Buttons
            button_layout = QHBoxLayout()
            export_btn = QPushButton("Export")
            cancel_btn = QPushButton("Cancel")
            
            export_btn.clicked.connect(dialog.accept)
            cancel_btn.clicked.connect(dialog.reject)
            
            button_layout.addWidget(export_btn)
            button_layout.addWidget(cancel_btn)
            layout.addLayout(button_layout)
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_format = format_combo.currentData()
                
                # Get file path based on format
                if selected_format == 'high_res_images':
                    # Directory selection for multiple images
                    output_path = QFileDialog.getExistingDirectory(
                        self,
                        "Select Output Directory for High-Res Images"
                    )
                else:
                    # File selection for single file export
                    selected_fmt_data = supported_formats[format_combo.currentIndex()]
                    extension = selected_fmt_data['extension']
                    filter_text = f"{selected_fmt_data['name']} (*.{extension})"
                    
                    output_path, _ = QFileDialog.getSaveFileName(
                        self,
                        "Export Chart",
                        f"chart.{extension}",
                        filter_text
                    )
                
                if output_path:
                    # Start export
                    success = export_manager.export_chart(
                        self.current_chart,
                        selected_format,
                        output_path
                    )
                    
                    if success:
                        self.chart_exported.emit(output_path)
                
        except ImportError:
            # Fallback to basic export if enhanced export not available
            self._basic_export()
        except Exception as e:
            logger.error(f"[CHART-WIDGET] Error in enhanced export: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export chart: {str(e)}")
    
    def _basic_export(self):
        """Basic export fallback when enhanced export is not available"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            # Get export path from user
            file_path, file_type = QFileDialog.getSaveFileName(
                self,
                "Export Chart",
                f"chart.html",
                "HTML files (*.html);;PNG files (*.png);;PDF files (*.pdf);;All files (*.*)"
            )
            
            if file_path:
                # Export based on file extension
                if file_path.endswith('.html'):
                    pyo.plot(self.current_chart, filename=file_path, auto_open=False)
                elif file_path.endswith('.png'):
                    self.current_chart.write_image(file_path, format='png')
                elif file_path.endswith('.pdf'):
                    self.current_chart.write_image(file_path, format='pdf')
                else:
                    # Default to HTML
                    pyo.plot(self.current_chart, filename=file_path + '.html', auto_open=False)
                
                self.chart_exported.emit(file_path)
                QMessageBox.information(self, "Export Complete", f"Chart exported to:\n{file_path}")
                
        except Exception as e:
            logger.error(f"[CHART-WIDGET] Error in basic export: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export chart: {str(e)}")
    
    def _create_advanced_chart(self, dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """Create an advanced chart type"""
        try:
            from .advanced_chart_types import ADVANCED_CHART_TYPES
            
            chart_type = config.get('type')
            if chart_type not in ADVANCED_CHART_TYPES:
                logger.error(f"Unknown advanced chart type: {chart_type}")
                return None
            
            # Get the creator function for this chart type
            creator_func = ADVANCED_CHART_TYPES[chart_type]['creator']
            
            # Create the chart
            fig = creator_func(dataframe, config)
            
            if fig is None:
                logger.error(f"Failed to create {chart_type} chart")
                return None
            
            return fig
            
        except ImportError:
            logger.error("Advanced chart types not available")
            return None
        except Exception as e:
            logger.error(f"Error creating advanced chart: {e}")
            return None
    
    def clear_chart(self):
        """Clear the current chart"""
        if PLOTLY_AVAILABLE and hasattr(self, 'web_view'):
            self.web_view.load(QUrl("about:blank"))
        
        self.current_chart = None
        self.dataframe = None
        self.chart_config = {}
        self.chart_title.setText("Chart Visualization")
        
        # Clean up temp file
        if self.temp_file_path:
            try:
                Path(self.temp_file_path).unlink()
                self.temp_file_path = None
            except:
                pass
    
    def closeEvent(self, event):
        """Clean up when widget is closed"""
        self.clear_chart()
        super().closeEvent(event)