"""
Advanced Chart Types for Business Intelligence Visualizations
Extends the basic chart types with financial, KPI, and analytical visualizations
"""
import logging
from typing import Dict, Any, Optional, List
import polars as pl

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    import plotly.express as px
    import plotly.figure_factory as ff
    from plotly.subplots import make_subplots
    import numpy as np
    PLOTLY_AVAILABLE = True
except ImportError:
    logger.warning("Plotly not available - advanced chart types will be disabled")
    PLOTLY_AVAILABLE = False
    go = None
    px = None
    ff = None
    make_subplots = None
    np = None

class AdvancedChart:
    """Base class for advanced chart types"""
    
    @staticmethod
    def _validate_columns(dataframe: pl.DataFrame, required_columns: List[str], config: Dict[str, Any]) -> bool:
        """Validate that required columns exist in the dataframe"""
        for col_key in required_columns:
            col_name = config.get(col_key)
            if not col_name or col_name not in dataframe.columns:
                logger.error(f"Required column '{col_key}' ({col_name}) not found in dataframe")
                return False
        return True
    
    @staticmethod
    def _prepare_data(dataframe: pl.DataFrame, config: Dict[str, Any]) -> pl.DataFrame:
        """Prepare and clean data for visualization"""
        # Remove null values from key columns
        key_columns = [col for col in [
            config.get('x_column'),
            config.get('y_column'), 
            config.get('values_column'),
            config.get('names_column')
        ] if col and col in dataframe.columns]
        
        if key_columns:
            return dataframe.drop_nulls(subset=key_columns)
        return dataframe

class WaterfallChart(AdvancedChart):
    """Waterfall chart for showing cumulative effects of sequential positive/negative values"""
    
    @staticmethod
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a waterfall chart
        
        Required config:
        - x_column: Categories (e.g., months, departments)  
        - y_column: Values (positive/negative changes)
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['x_column', 'y_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for waterfall chart")
            return None
        
        x_col = config['x_column']
        y_col = config['y_column']
        title = config.get('title', 'Waterfall Chart')
        
        # Convert to pandas for easier manipulation
        df_pandas = df_clean.to_pandas()
        
        # Calculate cumulative values for waterfall effect
        x_values = df_pandas[x_col].tolist()
        y_values = df_pandas[y_col].tolist()
        
        # Create cumulative sum excluding the last value
        cumulative = [0] + list(np.cumsum(y_values[:-1]))
        
        fig = go.Figure()
        
        # Add waterfall bars
        fig.add_trace(go.Waterfall(
            name="",
            orientation="v",
            measure=["relative"] * (len(x_values) - 1) + ["total"],
            x=x_values,
            y=y_values,
            text=[f"{val:,.0f}" for val in y_values],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            increasing={"marker": {"color": "green"}},
            decreasing={"marker": {"color": "red"}},
            totals={"marker": {"color": "blue"}}
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template=config.get('template', 'plotly_white'),
            height=config.get('height', 500),
            showlegend=config.get('show_legend', False)
        )
        
        return fig

class GaugeChart(AdvancedChart):
    """Gauge chart for KPI visualization"""
    
    @staticmethod
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a gauge chart for KPI display
        
        Required config:
        - values_column: The metric value
        Optional config:
        - max_value: Maximum value for gauge scale
        - target_value: Target line on gauge
        - thresholds: Dict with 'good', 'warning', 'critical' values
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['values_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for gauge chart")
            return None
        
        values_col = config['values_column']
        title = config.get('title', 'KPI Gauge')
        
        # Get the value (assume single row or aggregate)
        if len(df_clean) > 1:
            # If multiple rows, take the sum
            value = df_clean[values_col].sum()
        else:
            value = df_clean[values_col].item()
        
        # Determine max value
        max_value = config.get('max_value', value * 1.2 if value > 0 else 100)
        target_value = config.get('target_value', max_value * 0.8)
        
        # Set up thresholds
        thresholds = config.get('thresholds', {
            'good': max_value * 0.8,
            'warning': max_value * 0.6,
            'critical': max_value * 0.4
        })
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': title},
            delta={'reference': target_value, 'position': "top"},
            gauge={
                'axis': {'range': [None, max_value]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, thresholds['critical']], 'color': "lightgray"},
                    {'range': [thresholds['critical'], thresholds['warning']], 'color': "yellow"},
                    {'range': [thresholds['warning'], thresholds['good']], 'color': "orange"},
                    {'range': [thresholds['good'], max_value], 'color': "green"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': target_value
                }
            }
        ))
        
        fig.update_layout(
            height=config.get('height', 400),
            template=config.get('template', 'plotly_white')
        )
        
        return fig

class HeatmapChart(AdvancedChart):
    """Heatmap for correlation and matrix visualization"""
    
    @staticmethod
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a heatmap chart
        
        Required config:
        - x_column: X-axis categories
        - y_column: Y-axis categories  
        - values_column: Values for color intensity
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['x_column', 'y_column', 'values_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for heatmap")
            return None
        
        x_col = config['x_column']
        y_col = config['y_column']
        values_col = config['values_column']
        title = config.get('title', 'Heatmap')
        
        # Create pivot table for heatmap
        df_pandas = df_clean.to_pandas()
        pivot_table = df_pandas.pivot_table(
            values=values_col,
            index=y_col,
            columns=x_col,
            aggfunc='mean',  # Use mean for aggregation
            fill_value=0
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=pivot_table.columns,
            y=pivot_table.index,
            colorscale=config.get('colorscale', 'RdYlBu'),
            showscale=True,
            text=pivot_table.values,
            texttemplate="%{text:.2f}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=title,
            xaxis_title=x_col,
            yaxis_title=y_col,
            template=config.get('template', 'plotly_white'),
            height=config.get('height', 500)
        )
        
        return fig

class TreemapChart(AdvancedChart):
    """Treemap for hierarchical data visualization"""
    
    @staticmethod
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a treemap chart
        
        Required config:
        - names_column: Labels for segments
        - values_column: Values for segment sizes
        Optional config:
        - parents_column: Parent categories for hierarchy
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['names_column', 'values_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for treemap")
            return None
        
        names_col = config['names_column']
        values_col = config['values_column']
        parents_col = config.get('parents_column')
        title = config.get('title', 'Treemap')
        
        df_pandas = df_clean.to_pandas()
        
        # Create treemap
        if parents_col and parents_col in df_pandas.columns:
            # Hierarchical treemap
            fig = go.Figure(go.Treemap(
                labels=df_pandas[names_col],
                values=df_pandas[values_col],
                parents=df_pandas[parents_col],
                textinfo="label+value+percent parent",
                texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentParent}",
                pathbar={"visible": True}
            ))
        else:
            # Simple treemap
            fig = go.Figure(go.Treemap(
                labels=df_pandas[names_col],
                values=df_pandas[values_col],
                textinfo="label+value+percent root",
                texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentRoot}",
                pathbar={"visible": False}
            ))
        
        fig.update_layout(
            title=title,
            template=config.get('template', 'plotly_white'),
            height=config.get('height', 500)
        )
        
        return fig

class FunnelChart(AdvancedChart):
    """Funnel chart for conversion process visualization"""
    
    @staticmethod
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a funnel chart
        
        Required config:
        - names_column: Stage names
        - values_column: Values for each stage
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['names_column', 'values_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for funnel chart")
            return None
        
        names_col = config['names_column']
        values_col = config['values_column']
        title = config.get('title', 'Funnel Chart')
        
        df_pandas = df_clean.to_pandas().sort_values(values_col, ascending=False)
        
        fig = go.Figure(go.Funnel(
            y=df_pandas[names_col],
            x=df_pandas[values_col],
            textposition="inside",
            textinfo="value+percent initial",
            opacity=0.65,
            marker={
                "color": ["deepskyblue", "lightsalmon", "tan", "teal", "silver"],
                "line": {"width": 2, "color": "wheat"}
            },
            connector={"line": {"color": "royalblue", "dash": "dot", "width": 3}}
        ))
        
        fig.update_layout(
            title=title,
            template=config.get('template', 'plotly_white'),
            height=config.get('height', 500)
        )
        
        return fig

class SunburstChart(AdvancedChart):
    """Sunburst chart for hierarchical data with multiple levels"""
    
    @staticmethod  
    def create(dataframe: pl.DataFrame, config: Dict[str, Any]) -> Optional[go.Figure]:
        """
        Create a sunburst chart
        
        Required config:
        - names_column: Labels for segments
        - values_column: Values for segment sizes
        - parents_column: Parent categories for hierarchy
        """
        if not PLOTLY_AVAILABLE:
            return None
            
        if not AdvancedChart._validate_columns(dataframe, ['names_column', 'values_column', 'parents_column'], config):
            return None
        
        df_clean = AdvancedChart._prepare_data(dataframe, config)
        if df_clean.is_empty():
            logger.error("No valid data for sunburst chart")
            return None
        
        names_col = config['names_column']
        values_col = config['values_column']
        parents_col = config['parents_column']
        title = config.get('title', 'Sunburst Chart')
        
        df_pandas = df_clean.to_pandas()
        
        fig = go.Figure(go.Sunburst(
            labels=df_pandas[names_col],
            parents=df_pandas[parents_col],
            values=df_pandas[values_col],
            branchvalues="total",
            hovertemplate='<b>%{label}</b><br>Value: %{value:,.0f}<br>Percentage: %{percentParent}<extra></extra>',
            maxdepth=3
        ))
        
        fig.update_layout(
            title=title,
            template=config.get('template', 'plotly_white'),
            height=config.get('height', 500)
        )
        
        return fig

# Registry of advanced chart types
ADVANCED_CHART_TYPES = {
    'waterfall': {
        'name': 'Waterfall Chart',
        'description': 'Show cumulative effect of sequential positive/negative values',
        'required_columns': ['x_column', 'y_column'],
        'optional_columns': [],
        'icon': 'fa5s.chart-bar',
        'creator': WaterfallChart.create
    },
    'gauge': {
        'name': 'Gauge Chart',
        'description': 'Display KPI metrics with target ranges',
        'required_columns': ['values_column'],
        'optional_columns': [],
        'icon': 'fa5s.tachometer-alt',
        'creator': GaugeChart.create
    },
    'heatmap': {
        'name': 'Heatmap',
        'description': 'Show correlations and patterns in matrix format',
        'required_columns': ['x_column', 'y_column', 'values_column'],
        'optional_columns': [],
        'icon': 'fa5s.th',
        'creator': HeatmapChart.create
    },
    'treemap': {
        'name': 'Treemap',
        'description': 'Display hierarchical data as nested rectangles',
        'required_columns': ['names_column', 'values_column'],
        'optional_columns': ['parents_column'],
        'icon': 'fa5s.th-large',
        'creator': TreemapChart.create
    },
    'funnel': {
        'name': 'Funnel Chart',
        'description': 'Show conversion rates through process stages',
        'required_columns': ['names_column', 'values_column'],
        'optional_columns': [],
        'icon': 'fa5s.filter',
        'creator': FunnelChart.create
    },
    'sunburst': {
        'name': 'Sunburst Chart',
        'description': 'Display hierarchical data in radial format',
        'required_columns': ['names_column', 'values_column', 'parents_column'],
        'optional_columns': [],
        'icon': 'fa5s.sun',
        'creator': SunburstChart.create
    }
}