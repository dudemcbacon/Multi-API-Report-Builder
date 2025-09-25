"""
Tree Population Manager for handling tree widget population and management
"""
import logging
from typing import Dict, Any, List, Optional
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PyQt6.QtCore import Qt, QObject, pyqtSignal
import qtawesome as qta

logger = logging.getLogger(__name__)

class TreePopulationManager(QObject):
    """
    Manages tree widget population and data source management
    """
    
    # Signals for tree events
    tree_populated = pyqtSignal(str)  # api_type
    tree_error = pyqtSignal(str, str)  # api_type, error_message
    
    def __init__(self, tree_widget: QTreeWidget):
        super().__init__()
        self.tree_widget = tree_widget
        
        # Data caches
        self.salesforce_reports = []
        self.woocommerce_data_sources = []
        self.avalara_data_sources = []
        self.quickbase_data_sources = []

        # Initialize Avalara data sources
        self._initialize_avalara_data_sources()
        # Initialize QuickBase data sources
        self._initialize_quickbase_data_sources()
    
    def _initialize_avalara_data_sources(self):
        """Initialize Avalara data sources structure"""
        self.avalara_data_sources = [
            {
                'id': 'companies',
                'name': 'Companies',
                'type': 'companies',
                'icon': 'fa5s.building',
                'data_type': 'companies',
                'modified': 'Static'
            },
            {
                'id': 'transactions',
                'name': 'Transactions',
                'type': 'transactions',
                'icon': 'fa5s.receipt',
                'data_type': 'transactions',
                'modified': 'Dynamic'
            },
            {
                'id': 'tax_codes',
                'name': 'Tax Codes',
                'type': 'tax_codes',
                'icon': 'fa5s.tags',
                'data_type': 'tax_codes',
                'modified': 'Static'
            },
            {
                'id': 'jurisdictions',
                'name': 'Jurisdictions',
                'type': 'jurisdictions',
                'icon': 'fa5s.map-marker-alt',
                'data_type': 'jurisdictions',
                'modified': 'Static'
            }
        ]

    def _initialize_quickbase_data_sources(self):
        """Initialize QuickBase data sources structure"""
        # Start with empty - will be populated with actual tables when loaded
        self.quickbase_data_sources = []
        self.quickbase_tables_cache = {}  # Cache for table -> reports mapping

    def populate_unified_tree(self, connection_status: Dict[str, bool]):
        """
        Populate the unified tree with all API data sources
        
        Args:
            connection_status: Dictionary of API connection statuses
        """
        try:
            logger.info("[TREE-MANAGER] Populating unified tree")
            
            # Clear existing tree
            self.tree_widget.clear()
            
            # Create parent items for each API
            sf_parent = self._create_api_parent_item('Salesforce', 'fa5s.cloud', connection_status.get('salesforce', False))
            woo_parent = self._create_api_parent_item('WooCommerce', 'fa5b.wordpress', connection_status.get('woocommerce', False))
            avalara_parent = self._create_api_parent_item('Avalara', 'fa5s.calculator', connection_status.get('avalara', False))
            quickbase_parent = self._create_api_parent_item('QuickBase', 'fa5s.database', connection_status.get('quickbase', False))
            
            # Populate each section
            if connection_status.get('salesforce', False):
                self._populate_salesforce_section(sf_parent)
            else:
                self._create_not_connected_item(sf_parent, 'salesforce')
            
            if connection_status.get('woocommerce', False):
                self._populate_woocommerce_section(woo_parent)
            else:
                self._create_not_connected_item(woo_parent, 'woocommerce')
            
            if connection_status.get('avalara', False):
                self._populate_avalara_section(avalara_parent)
            else:
                self._create_not_connected_item(avalara_parent, 'avalara')

            if connection_status.get('quickbase', False):
                self._populate_quickbase_section(quickbase_parent)
            else:
                self._create_not_connected_item(quickbase_parent, 'quickbase')


            # Expand all parent items
            #sf_parent.setExpanded(True)
            #woo_parent.setExpanded(True)
            #avalara_parent.setExpanded(True)
            
            # Resize columns to content
            self.tree_widget.resizeColumnToContents(0)
            
            logger.info("[TREE-MANAGER] Unified tree populated successfully")
            self.tree_populated.emit('all')
            
        except Exception as e:
            logger.error(f"[TREE-MANAGER] Error populating unified tree: {e}")
            self.tree_error.emit('all', str(e))
    
    def _create_api_parent_item(self, name: str, icon: str, connected: bool) -> QTreeWidgetItem:
        """Create a parent item for an API"""
        status = "Connected" if connected else "Not Connected"
        parent_item = QTreeWidgetItem(self.tree_widget, [name, status, ""])
        parent_item.setIcon(0, qta.icon(icon))
        parent_item.setData(0, Qt.ItemDataRole.UserRole, {
            'api_type': name.lower(),
            'is_parent': True,
            'connected': connected
        })
        return parent_item
    
    def _create_not_connected_item(self, parent_item: QTreeWidgetItem, api_type: str):
        """Create a 'not connected' item under a parent"""
        not_connected_item = QTreeWidgetItem(parent_item, ["Not Connected - Double-click to connect", "Status", ""])
        not_connected_item.setIcon(0, qta.icon('fa5s.times-circle'))
        not_connected_item.setData(0, Qt.ItemDataRole.UserRole, {
            'api_type': api_type,
            'action': 'connect'
        })
    
    def _populate_salesforce_section(self, parent_item: QTreeWidgetItem):
        """Populate Salesforce section with reports"""
        try:
            if not self.salesforce_reports:
                logger.info("[TREE-MANAGER] No Salesforce reports available")
                no_data_item = QTreeWidgetItem(parent_item, ["No Reports Available", "Status", ""])
                no_data_item.setIcon(0, qta.icon('fa5s.info-circle'))
                return
            
            logger.info(f"[TREE-MANAGER] Loading {len(self.salesforce_reports)} Salesforce reports")
            
            # Group reports by folder
            folders = {}
            for report in self.salesforce_reports:
                folder_name = report.get('folder', 'Unfiled Public Reports')
                if folder_name not in folders:
                    folders[folder_name] = []
                folders[folder_name].append(report)
            
            # Add folders and reports to tree
            for folder_name, folder_reports in folders.items():
                folder_item = QTreeWidgetItem(parent_item, [folder_name, "Folder", ""])
                folder_item.setIcon(0, qta.icon('fa5s.folder'))
                folder_item.setData(0, Qt.ItemDataRole.UserRole, {
                    'api_type': 'salesforce',
                    'is_folder': True
                })
                
                for report in folder_reports:
                    report_item = QTreeWidgetItem(folder_item, [
                        report['name'],
                        report['format'],
                        report.get('modified_date', '')[:10] if report.get('modified_date') else ''
                    ])
                    report_item.setIcon(0, qta.icon('fa5s.file-alt'))
                    report_item.setData(0, Qt.ItemDataRole.UserRole, {
                        'id': report['id'],
                        'name': report['name'],
                        'api_type': 'salesforce',
                        'type': 'report'
                    })
            
            logger.info(f"[TREE-MANAGER] Successfully loaded {len(self.salesforce_reports)} Salesforce reports")
            
        except Exception as e:
            logger.error(f"[TREE-MANAGER] Error populating Salesforce section: {e}")
            error_item = QTreeWidgetItem(parent_item, ["Error Loading Reports", "Error", ""])
            error_item.setIcon(0, qta.icon('fa5s.exclamation-triangle'))
    
    def _populate_woocommerce_section(self, parent_item: QTreeWidgetItem):
        """Populate WooCommerce section with data sources"""
        try:
            if not self.woocommerce_data_sources:
                logger.info("[TREE-MANAGER] No WooCommerce data sources available")
                no_data_item = QTreeWidgetItem(parent_item, ["No Data Sources Available", "Status", ""])
                no_data_item.setIcon(0, qta.icon('fa5s.info-circle'))
                return
            
            logger.info(f"[TREE-MANAGER] Loading {len(self.woocommerce_data_sources)} WooCommerce data sources")
            
            for source in self.woocommerce_data_sources:
                source_item = QTreeWidgetItem(parent_item, [
                    source['name'],
                    source['type'].title(),
                    source.get('modified', '')
                ])
                source_item.setIcon(0, qta.icon(source['icon']))
                source_data = source.copy()
                source_data['api_type'] = 'woocommerce'
                source_item.setData(0, Qt.ItemDataRole.UserRole, source_data)
            
            logger.info(f"[TREE-MANAGER] Successfully loaded {len(self.woocommerce_data_sources)} WooCommerce data sources")
            
        except Exception as e:
            logger.error(f"[TREE-MANAGER] Error populating WooCommerce section: {e}")
            error_item = QTreeWidgetItem(parent_item, ["Error Loading Data Sources", "Error", ""])
            error_item.setIcon(0, qta.icon('fa5s.exclamation-triangle'))
    
    def _populate_avalara_section(self, parent_item: QTreeWidgetItem):
        """Populate Avalara section with data sources"""
        try:
            logger.info(f"[TREE-MANAGER] Loading {len(self.avalara_data_sources)} Avalara data sources")
            
            for source in self.avalara_data_sources:
                source_item = QTreeWidgetItem(parent_item, [
                    source['name'],
                    source['type'].title(),
                    source.get('modified', '')
                ])
                source_item.setIcon(0, qta.icon(source['icon']))
                source_data = source.copy()
                source_data['api_type'] = 'avalara'
                source_item.setData(0, Qt.ItemDataRole.UserRole, source_data)
            
            logger.info(f"[TREE-MANAGER] Successfully loaded {len(self.avalara_data_sources)} Avalara data sources")
            
        except Exception as e:
            logger.error(f"[TREE-MANAGER] Error populating Avalara section: {e}")
            error_item = QTreeWidgetItem(parent_item, ["Error Loading Data Sources", "Error", ""])
            error_item.setIcon(0, qta.icon('fa5s.exclamation-triangle'))

    def _populate_quickbase_section(self, parent_item: QTreeWidgetItem):
        """Populate QuickBase section with actual tables and reports"""
        try:
            logger.info(f"[TREE-MANAGER] Loading {len(self.quickbase_data_sources)} QuickBase tables")

            if not self.quickbase_data_sources:
                # Show loading or not configured message
                loading_item = QTreeWidgetItem(parent_item, ["Loading tables...", "Loading", ""])
                loading_item.setIcon(0, qta.icon('fa5s.spinner'))
                return

            # Populate tables with their reports
            for table in self.quickbase_data_sources:
                # Create table item
                table_item = QTreeWidgetItem(parent_item, [
                    table['name'],
                    f"Table ({table.get('pluralRecordName', 'Records')})",
                    table.get('updated', '')
                ])
                table_item.setIcon(0, qta.icon(table.get('icon', 'fa5s.table')))

                # Set table data
                table_data = table.copy()
                table_data['api_type'] = 'quickbase'
                table_item.setData(0, Qt.ItemDataRole.UserRole, table_data)

                # Add reports for this table if available
                table_id = table.get('table_id', table.get('id'))
                if table_id and table_id in self.quickbase_tables_cache:
                    reports = self.quickbase_tables_cache[table_id]
                    logger.info(f"[TREE-MANAGER] Adding {len(reports)} reports for table {table['name']}")

                    for report in reports:
                        report_item = QTreeWidgetItem(table_item, [
                            report['name'],
                            f"Report",
                            ""
                        ])
                        report_item.setIcon(0, qta.icon(report.get('icon', 'fa5s.file-alt')))

                        # Set report data
                        report_data = report.copy()
                        report_data['api_type'] = 'quickbase'
                        report_data['table_id'] = table_id
                        report_item.setData(0, Qt.ItemDataRole.UserRole, report_data)
                else:
                    # Add placeholder for reports that haven't loaded yet
                    loading_reports_item = QTreeWidgetItem(table_item, ["Loading reports...", "Loading", ""])
                    loading_reports_item.setIcon(0, qta.icon('fa5s.spinner'))

            logger.info(f"[TREE-MANAGER] Successfully loaded {len(self.quickbase_data_sources)} QuickBase tables")

        except Exception as e:
            logger.error(f"[TREE-MANAGER] Error populating QuickBase section: {e}")
            error_item = QTreeWidgetItem(parent_item, ["Error Loading Tables", "Error", ""])
            error_item.setIcon(0, qta.icon('fa5s.exclamation-triangle'))


    def update_salesforce_data(self, reports: List[Dict[str, Any]]):
        """Update Salesforce reports data"""
        logger.info(f"[TREE-MANAGER] Updating Salesforce data with {len(reports)} reports")
        self.salesforce_reports = reports
    
    def update_woocommerce_data(self, data_sources: List[Dict[str, Any]]):
        """Update WooCommerce data sources"""
        logger.info(f"[TREE-MANAGER] Updating WooCommerce data with {len(data_sources)} data sources")
        self.woocommerce_data_sources = data_sources
    
    def update_avalara_data(self, data_sources: List[Dict[str, Any]]):
        """Update Avalara data sources"""
        logger.info(f"[TREE-MANAGER] Updating Avalara data with {len(data_sources)} data sources")
        self.avalara_data_sources = data_sources

    def update_quickbase_data(self, data_sources: List[Dict[str, Any]]):
        """Update QuickBase data sources"""
        logger.info(f"[TREE-MANAGER] Updating QuickBase data with {len(data_sources)} data sources")
        self.quickbase_data_sources = data_sources

    def update_quickbase_table_reports(self, table_id: str, reports: List[Dict[str, Any]]):
        """Update reports for a specific QuickBase table"""
        logger.info(f"[TREE-MANAGER] Updating QuickBase table {table_id} with {len(reports)} reports")
        self.quickbase_tables_cache[table_id] = reports


    def get_selected_item_data(self) -> Optional[Dict[str, Any]]:
        """Get data from the currently selected tree item"""
        current_item = self.tree_widget.currentItem()
        if current_item:
            return current_item.data(0, Qt.ItemDataRole.UserRole)
        return None
    
    def refresh_tree(self, connection_status: Dict[str, bool]):
        """Refresh the entire tree with current data"""
        logger.info("[TREE-MANAGER] Refreshing tree")
        self.populate_unified_tree(connection_status)
    
    def clear_tree(self):
        """Clear all tree items"""
        logger.info("[TREE-MANAGER] Clearing tree")
        self.tree_widget.clear()
    
    def get_tree_stats(self) -> Dict[str, Any]:
        """Get statistics about the tree content"""
        return {
            'salesforce_reports': len(self.salesforce_reports),
            'woocommerce_sources': len(self.woocommerce_data_sources),
            'avalara_sources': len(self.avalara_data_sources),
            'quickbase_sources': len(self.quickbase_data_sources),
            'total_items': len(self.salesforce_reports) + len(self.woocommerce_data_sources) + len(self.avalara_data_sources) + len(self.quickbase_data_sources)
        }