"""
Operations Tab - Contains automated tasks and data processing operations
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
    QLabel, QDateEdit, QFrame, QTabWidget, QMessageBox, QProgressBar,
    QSpacerItem, QSizePolicy, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread
import qtawesome as qta
import polars as pl

from src.ui.data_grid import InteractiveDataGrid, MultiSheetExportWorker

logger = logging.getLogger(__name__)

# Operation configuration for ShareFile paths and naming
OPERATION_CONFIG = {
    "Sales Receipt Import": {
        "base_path": r"S:\Shared Folders\Operations\Financial Folders\Sales Receipt Import",
        "file_suffix": "SR Import",
        "folder_pattern": "{year}/{year}-{month:02d}"
    },
    "Sales Receipt Tie Out": {
        "base_path": r"S:\Shared Folders\Operations\Financial Folders\Sales Receipt Import",
        "file_suffix": "SR Import Tie Out SFDC to QB to Avalara",
        "folder_pattern": "{year}/{year}-{month:02d}",
        "subfolder": "TieOut"
    }
}


class ShareFileManager:
    """Manages ShareFile paths and operations"""
    
    @staticmethod
    def get_operation_config(operation_name: str) -> dict:
        """Get configuration for an operation"""
        return OPERATION_CONFIG.get(operation_name, {})
    
    @staticmethod
    def generate_folder_path(operation_name: str, start_date: QDate, end_date: QDate) -> Path:
        """Generate the folder path for saving files"""
        config = ShareFileManager.get_operation_config(operation_name)
        if not config:
            raise ValueError(f"No configuration found for operation: {operation_name}")
        
        base_path = Path(config["base_path"])
        
        # Extract year and month from start date
        year = start_date.year()
        month = start_date.month()
        
        # Format the folder pattern
        folder_pattern = config["folder_pattern"]
        folder_path = folder_pattern.format(year=year, month=month)
        
        # Add subfolder if specified in config
        full_path = base_path / folder_path
        if "subfolder" in config:
            full_path = full_path / config["subfolder"]
        
        return full_path
    
    @staticmethod
    def generate_filename(operation_name: str, start_date: QDate, end_date: QDate) -> str:
        """Generate standardized filename based on operation and date range"""
        config = ShareFileManager.get_operation_config(operation_name)
        if not config:
            raise ValueError(f"No configuration found for operation: {operation_name}")
        
        # Format dates for filename
        start_str = start_date.toString("yyyy_MM_dd")
        end_day = end_date.toString("dd")
        
        # Create filename
        file_suffix = config["file_suffix"]
        filename = f"{start_str}-{end_day} {file_suffix}.xlsx"
        
        return filename
    
    @staticmethod
    def ensure_directories_exist(path: Path) -> bool:
        """Create directories if they don't exist"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except PermissionError:
            logger.error(f"Permission denied creating directory: {path}")
            return False
        except OSError as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False


class OperationWorker(QThread):
    """Worker thread for running operations"""
    progress = pyqtSignal(int, str)  # Progress percentage and message
    result_ready = pyqtSignal(object)  # Result data
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, operation_name: str, start_date: QDate = None, end_date: QDate = None, 
                 sf_api=None, woo_api=None, avalara_api=None, file_paths=None):
        super().__init__()
        self.operation_name = operation_name
        self.start_date = start_date.toString("yyyy-MM-dd") if start_date else None
        self.end_date = end_date.toString("yyyy-MM-dd") if end_date else None
        self.sf_api = sf_api
        self.woo_api = woo_api
        self.avalara_api = avalara_api
        self.file_paths = file_paths or {}
        
    def run(self):
        """Execute the operation"""
        try:
            if self.operation_name == "Sales Receipt Import":
                self._run_sales_receipt_import()
            elif self.operation_name == "Sales Receipt Tie Out":
                self._run_sales_receipt_tie_out()
            else:
                self.error_occurred.emit(f"Unknown operation: {self.operation_name}")
        except Exception as e:
            logger.error(f"Operation error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))
            
    def _run_sales_receipt_import(self):
        """Run the sales receipt import operation"""
        from src.ui.operations.sales_receipt_import import SalesReceiptImport
        
        # Debug API availability
        logger.info(f"[OPERATION-WORKER] Starting Sales Receipt Import")
        logger.info(f"[OPERATION-WORKER] Salesforce API available: {self.sf_api is not None}")
        logger.info(f"[OPERATION-WORKER] WooCommerce API available: {self.woo_api is not None}")
        
        if self.sf_api is None:
            logger.error("[OPERATION-WORKER] No Salesforce API instance available")
            self.error_occurred.emit("Salesforce API not available")
            return
            
        if self.woo_api is None:
            logger.error("[OPERATION-WORKER] No WooCommerce API instance available")
            self.error_occurred.emit("WooCommerce API not available")
            return
        
        # Test WooCommerce connection
        try:
            logger.info("[OPERATION-WORKER] Testing WooCommerce connection...")
            woo_test = self.woo_api.test_connection()
            logger.info(f"[OPERATION-WORKER] WooCommerce test result: {woo_test}")
            if not woo_test.get('success'):
                logger.warning(f"[OPERATION-WORKER] WooCommerce connection test failed: {woo_test}")
        except Exception as e:
            logger.error(f"[OPERATION-WORKER] WooCommerce connection test error: {e}")
        
        # Create operation instance
        operation = SalesReceiptImport(self.sf_api, self.woo_api)
        
        # Connect progress signals
        operation.progress_callback = lambda pct, msg: self.progress.emit(pct, msg)
        
        # Run the operation
        result = operation.execute(self.start_date, self.end_date)
        
        # Emit result
        self.result_ready.emit(result)
    
    def _run_sales_receipt_tie_out(self):
        """Run the sales receipt tie out operation"""
        from src.ui.operations.sales_receipt_tie_out import SalesReceiptTieOut
        from src.ui.operations.sales_receipt_import import SalesReceiptImport
        
        logger.info(f"[OPERATION-WORKER] Starting Sales Receipt Tie Out")
        logger.info(f"[OPERATION-WORKER] File paths: {self.file_paths}")
        logger.info(f"[OPERATION-WORKER] Date range: {self.start_date} to {self.end_date}")
        
        try:
            # First, run the Sales Receipt Import to get SalesForce data
            self.progress.emit(5, "Fetching SalesForce data...")
            
            sales_import = SalesReceiptImport(self.sf_api, self.woo_api)
            sales_import.progress_callback = lambda pct, msg: self.progress.emit(int(pct * 0.3), f"SF: {msg}")
            
            # Run the import operation
            sf_result = sales_import.execute(self.start_date, self.end_date)
            
            if sf_result is None:
                self.error_occurred.emit("Failed to fetch SalesForce data")
                return
            
            # Extract the main dataframe and CM data from the result
            sf_data = None
            sf_cm_data = None
            
            if isinstance(sf_result, dict):
                # Get the main data
                if 'main' in sf_result:
                    sf_data = sf_result['main']
                
                # Get the CM Import data
                if 'credit' in sf_result and sf_result['credit'] is not None:
                    sf_cm_data = sf_result['credit']
                
                # If no main data, try to combine all available data (except errors and credit)
                if sf_data is None:
                    import polars as pl
                    dfs_to_combine = []
                    for key, df in sf_result.items():
                        if df is not None and key not in ['errors', 'credit']:
                            dfs_to_combine.append(df)
                    if dfs_to_combine:
                        sf_data = pl.concat(dfs_to_combine, how="diagonal")
            else:
                sf_data = sf_result
            
            if sf_data is None:
                self.error_occurred.emit("No SalesForce data returned")
                return
            
            # Update file paths with the SalesForce data
            self.file_paths['salesforce_data'] = sf_data
            
            # Add CM data if available
            if sf_cm_data is not None:
                self.file_paths['salesforce_cm_data'] = sf_cm_data
            
            # Fetch Avalara data if available
            if self.avalara_api is not None:
                self.progress.emit(25, "Fetching Avalara transactions...")
                logger.info("[OPERATION-WORKER] Fetching Avalara data...")
                
                try:
                    # Import necessary modules
                    import asyncio
                    from src.services.async_avalara_api import AsyncAvalaraAPI
                    
                    # Create async function to fetch Avalara data
                    async def fetch_avalara_data():
                        async with AsyncAvalaraAPI(verbose_logging=False) as api:
                            transactions = await api.get_transactions(self.start_date, self.end_date)
                            if transactions:
                                df = api.to_dataframe(transactions, "transactions")
                                return df
                            return None
                    
                    # Run async function
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        avalara_df = loop.run_until_complete(fetch_avalara_data())
                        if avalara_df is not None and not avalara_df.is_empty():
                            self.file_paths['avalara_data'] = avalara_df
                            logger.info(f"[OPERATION-WORKER] Fetched {len(avalara_df)} Avalara transactions")
                        else:
                            logger.warning("[OPERATION-WORKER] No Avalara transactions found for date range")
                    finally:
                        loop.close()
                        
                except Exception as e:
                    logger.error(f"[OPERATION-WORKER] Error fetching Avalara data: {e}")
                    # Continue without Avalara data
            else:
                logger.info("[OPERATION-WORKER] Avalara API not available, skipping Avalara data fetch")
            
            # Now run the tie out operation
            self.progress.emit(30, "Running tie-out analysis...")
            
            # Create operation instance
            operation = SalesReceiptTieOut()
            
            # Connect progress signals (offset by 30%)
            operation.progress_callback = lambda pct, msg: self.progress.emit(30 + int(pct * 0.7), msg)
            
            # Run the operation
            result = operation.execute(self.file_paths, sf_api=self.sf_api, woo_api=self.woo_api, avalara_api=self.avalara_api)
            
            # Emit result
            self.result_ready.emit(result)
            
        except Exception as e:
            logger.error(f"[OPERATION-WORKER] Sales Receipt Tie Out error: {e}", exc_info=True)
            self.error_occurred.emit(str(e))


class OperationsTab(QWidget):
    """Tab containing automated operations and tasks"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_worker = None
        self.current_results = None  # Store current operation results for multi-sheet export
        self.sharefile_export_worker = None  # Worker for ShareFile exports
        self.setup_ui()
    
    def __del__(self):
        """Ensure worker threads are properly cleaned up"""
        self.cleanup_workers()
    
    def cleanup_workers(self):
        """Clean up any running worker threads"""
        if self.sharefile_export_worker and self.sharefile_export_worker.isRunning():
            self.sharefile_export_worker.quit()
            self.sharefile_export_worker.wait(1000)
            self.sharefile_export_worker.deleteLater()
            self.sharefile_export_worker = None
        
    def setup_ui(self):
        """Setup the operations tab UI"""
        layout = QVBoxLayout(self)
        
        # Control panel
        control_frame = QFrame()
        control_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        control_layout = QVBoxLayout(control_frame)
        
        # Operation selection
        operation_layout = QHBoxLayout()
        operation_layout.addWidget(QLabel("Operation:"))
        
        self.operation_combo = QComboBox()
        self.operation_combo.addItems(["Sales Receipt Import", "Sales Receipt Tie Out"])
        self.operation_combo.setMinimumWidth(200)
        self.operation_combo.currentTextChanged.connect(self.on_operation_changed)
        operation_layout.addWidget(self.operation_combo)
        
        operation_layout.addStretch()
        control_layout.addLayout(operation_layout)
        
        # File selection for Sales Receipt Tie Out
        self.file_selection_frame = QFrame()
        self.file_selection_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        file_layout = QVBoxLayout(self.file_selection_frame)
        
        # File 1: QuickBooks Sales Receipts
        file1_layout = QHBoxLayout()
        file1_layout.addWidget(QLabel("QuickBooks Sales Receipts:"))
        self.file1_path = QLineEdit()
        self.file1_path.setPlaceholderText("Select Excel/CSV file...")
        file1_layout.addWidget(self.file1_path)
        self.file1_btn = QPushButton("Browse...")
        self.file1_btn.clicked.connect(lambda: self.browse_file(self.file1_path))
        file1_layout.addWidget(self.file1_btn)
        file_layout.addLayout(file1_layout)
        
        # File 2: QuickBooks Credit Memos
        file2_layout = QHBoxLayout()
        file2_layout.addWidget(QLabel("QuickBooks Credit Memos:"))
        self.file2_path = QLineEdit()
        self.file2_path.setPlaceholderText("Select Excel/CSV file...")
        file2_layout.addWidget(self.file2_path)
        self.file2_btn = QPushButton("Browse...")
        self.file2_btn.clicked.connect(lambda: self.browse_file(self.file2_path))
        file2_layout.addWidget(self.file2_btn)
        file_layout.addLayout(file2_layout)
        
        # Info label about SalesForce data
        info_label = QLabel("📊 SalesForce data (including CM Import) will be automatically fetched using the date range")
        info_label.setStyleSheet("QLabel { color: #0066cc; padding: 10px; }")
        file_layout.addWidget(info_label)
        
        # Initially hide file selection (only show for Sales Receipt Tie Out)
        self.file_selection_frame.setVisible(False)
        control_layout.addWidget(self.file_selection_frame)
        
        # Date range selection
        self.date_range_frame = QFrame()
        self.date_range_frame.setFrameStyle(QFrame.Shape.NoFrame)
        date_layout = QHBoxLayout(self.date_range_frame)
        date_layout.addWidget(QLabel("Date Range:"))
        
        # Start date
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-30))  # Default to last 30 days
        self.start_date.setDisplayFormat("MM/dd/yyyy")
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date)
        
        # End date
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setDisplayFormat("MM/dd/yyyy")
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date)
        
        date_layout.addStretch()
        control_layout.addWidget(self.date_range_frame)
        
        # Load button and progress
        button_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Data")
        self.load_btn.setIcon(qta.icon('fa5s.play'))
        self.load_btn.clicked.connect(self.run_operation)
        button_layout.addWidget(self.load_btn)
        
        # Save to ShareFile button
        self.sharefile_btn = QPushButton("Save to ShareFile")
        self.sharefile_btn.setIcon(qta.icon('fa5s.folder-open'))
        self.sharefile_btn.setToolTip("Save results directly to ShareFile")
        self.sharefile_btn.clicked.connect(self.save_to_sharefile)
        self.sharefile_btn.setEnabled(False)  # Initially disabled
        button_layout.addWidget(self.sharefile_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        button_layout.addWidget(self.status_label)
        
        button_layout.addStretch()
        control_layout.addLayout(button_layout)
        
        layout.addWidget(control_frame)
        
        # Results area
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabsClosable(True)
        self.results_tabs.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.results_tabs)
        
        # Add welcome message
        self.add_welcome_tab()
        
        # Initialize UI based on default selection
        self.on_operation_changed(self.operation_combo.currentText())
        
    def add_welcome_tab(self):
        """Add welcome tab to results"""
        welcome_widget = QWidget()
        layout = QVBoxLayout(welcome_widget)
        
        welcome_label = QLabel(
            "<h2>Operations Center</h2>"
            "<p>Select an operation from the dropdown above and configure the required inputs.</p>"
            "<p>Click 'Load Data' to run the operation.</p>"
            "<br>"
            "<p><b>Available Operations:</b></p>"
            "<p>• <b>Sales Receipt Import</b> - Processes Salesforce sales receipts with WooCommerce fee matching</p>"
            "<p>• <b>Sales Receipt Tie Out</b> - Combines QB files with live SFDC data for tie-out analysis</p>"
            "<p style='margin-left: 20px; color: #0066cc;'>↳ Uses date range to fetch fresh SFDC data automatically</p>"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setWordWrap(True)
        layout.addWidget(welcome_label)
        
        self.results_tabs.addTab(welcome_widget, "Welcome")
        
    def on_operation_changed(self, operation_name: str):
        """Handle operation selection change"""
        if operation_name == "Sales Receipt Tie Out":
            self.file_selection_frame.setVisible(True)
            self.date_range_frame.setVisible(True)  # Show date range for tie out as well
        else:
            self.file_selection_frame.setVisible(False)
            self.date_range_frame.setVisible(True)
    
    def browse_file(self, line_edit: QLineEdit):
        """Open file dialog and set selected file path"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)
        
    def run_operation(self):
        """Run the selected operation"""
        operation_name = self.operation_combo.currentText()
        
        # Validate inputs based on operation type
        if operation_name == "Sales Receipt Tie Out":
            # Validate file paths
            if not self.file1_path.text() or not os.path.exists(self.file1_path.text()):
                QMessageBox.warning(self, "Missing File", 
                                  "Please select a valid QuickBooks Sales Receipts file.")
                return
                
            if not self.file2_path.text() or not os.path.exists(self.file2_path.text()):
                QMessageBox.warning(self, "Missing File", 
                                  "Please select a valid QuickBooks Credit Memos file.")
                return
            
            # Check date range for tie out operation
            if self.start_date.date() > self.end_date.date():
                QMessageBox.warning(self, "Invalid Date Range", 
                                  "Start date must be before or equal to end date.")
                return
                
            # Check API connections for tie out operation (needs Salesforce and WooCommerce)
            if not hasattr(self.main_window, 'sf_api') or not self.main_window.sf_api:
                QMessageBox.warning(self, "No Connection", 
                                  "Please connect to Salesforce first.")
                return
                
            if not hasattr(self.main_window, 'woo_api') or not self.main_window.woo_api:
                QMessageBox.warning(self, "No Connection", 
                                  "Please connect to WooCommerce first.")
                return
        else:
            # Validate date range for other operations
            if self.start_date.date() > self.end_date.date():
                QMessageBox.warning(self, "Invalid Date Range", 
                                  "Start date must be before or equal to end date.")
                return
                
            # Check API connections for other operations
            if not hasattr(self.main_window, 'sf_api') or not self.main_window.sf_api:
                QMessageBox.warning(self, "No Connection", 
                                  "Please connect to Salesforce first.")
                return
                
            if not hasattr(self.main_window, 'woo_api') or not self.main_window.woo_api:
                QMessageBox.warning(self, "No Connection", 
                                  "Please connect to WooCommerce first.")
                return
            
        # Disable controls during operation
        self.load_btn.setEnabled(False)
        self.operation_combo.setEnabled(False)
        self.start_date.setEnabled(False)
        self.end_date.setEnabled(False)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting operation...")
        
        # Create and start worker
        if operation_name == "Sales Receipt Tie Out":
            file_paths = {
                'qb_sales_receipts': self.file1_path.text(),
                'qb_credit_memos': self.file2_path.text()
            }
            self.current_worker = OperationWorker(
                operation_name,
                self.start_date.date(),
                self.end_date.date(),
                self.main_window.sf_api,
                self.main_window.woo_api,
                getattr(self.main_window, 'avalara_api', None),
                file_paths
            )
        else:
            self.current_worker = OperationWorker(
                operation_name,
                self.start_date.date(),
                self.end_date.date(),
                self.main_window.sf_api,
                self.main_window.woo_api,
                getattr(self.main_window, 'avalara_api', None)
            )
        
        self.current_worker.progress.connect(self.update_progress)
        self.current_worker.result_ready.connect(self.display_results)
        self.current_worker.error_occurred.connect(self.handle_error)
        self.current_worker.finished.connect(self.operation_finished)
        
        self.current_worker.start()
        
    def update_progress(self, percentage: int, message: str):
        """Update progress display"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        
    def display_results(self, result):
        """Display operation results"""
        if result is None:
            QMessageBox.information(self, "No Results", 
                                  "The operation completed but returned no data.")
            return
            
        # Store results for multi-sheet export
        self.current_results = result
        
        # Enable ShareFile button now that we have results
        self.sharefile_btn.setEnabled(True)
        
        # Handle different result types
        if isinstance(result, dict):
            # Check if this is from Sales Receipt Import (legacy format)
            if 'main' in result or 'credit' in result or 'errors' in result:
                # Expected format: {'main': df, 'credit': df, 'errors': df}
                if 'main' in result and result['main'] is not None:
                    self.add_result_tab(result['main'], "Processed Data")
                    
                if 'credit' in result and result['credit'] is not None and len(result['credit']) > 0:
                    self.add_result_tab(result['credit'], "CM Import")
                    
                if 'errors' in result and result['errors'] is not None and len(result['errors']) > 0:
                    self.add_result_tab(result['errors'], "Change Log")
                    
                # Add Export All button for multi-sheet results
                self.add_export_all_button()
            else:
                # Handle Sales Receipt Tie Out format or other multi-sheet formats
                # Display all sheets in the result dictionary
                sheets_added = 0
                for sheet_name, dataframe in result.items():
                    if dataframe is not None:
                        try:
                            # Check if dataframe has data
                            if hasattr(dataframe, 'is_empty') and not dataframe.is_empty():
                                self.add_result_tab(dataframe, sheet_name)
                                sheets_added += 1
                            elif hasattr(dataframe, '__len__') and len(dataframe) > 0:
                                self.add_result_tab(dataframe, sheet_name)
                                sheets_added += 1
                        except Exception as e:
                            print(f"Warning: Error displaying sheet {sheet_name}: {e}")
                            # Still try to add the tab
                            self.add_result_tab(dataframe, sheet_name)
                            sheets_added += 1
                
                if sheets_added > 0:
                    # Add Export All button for multi-sheet results
                    self.add_export_all_button()
                else:
                    QMessageBox.information(self, "No Data", 
                                          "The operation completed but all result sheets appear to be empty.")
        else:
            # Single DataFrame result
            self.add_result_tab(result, f"Results - {datetime.now().strftime('%H:%M:%S')}")
            
    def add_result_tab(self, dataframe: pl.DataFrame, title: str):
        """Add a new tab with results"""
        data_grid = InteractiveDataGrid(dataframe, title)
        tab_index = self.results_tabs.addTab(data_grid, title)
        self.results_tabs.setCurrentIndex(tab_index)
        
    def add_export_all_button(self):
        """Add Export All to Excel button for multi-sheet results"""
        # Check if Export All button already exists
        if hasattr(self, 'export_all_button'):
            # Button already exists, just show it
            self.export_all_button.setVisible(True)
            return
            
        # Create Export All button
        self.export_all_button = QPushButton("📊 Export All to Excel")
        self.export_all_button.setIcon(qta.icon('fa5s.file-excel'))
        self.export_all_button.setToolTip("Export all sheets (Processed Data, CM Import, Change Log) to a single Excel workbook")
        self.export_all_button.clicked.connect(self.export_all_sheets)
        
        # Add button to the main layout before the results tabs
        main_layout = self.layout()
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.export_all_button)
        button_layout.addStretch()
        
        # Find the tabs widget position and insert button before it
        for i in range(main_layout.count()):
            if main_layout.itemAt(i).widget() == self.results_tabs:
                main_layout.insertLayout(i, button_layout)
                break
    
    def export_all_sheets(self):
        """Export all current results to a single Excel workbook"""
        if not self.current_results:
            QMessageBox.information(self, "No Data", "No data available to export.")
            return
        
        # Use the existing method to prepare datasets
        datasets = self._prepare_datasets_for_export()
        
        if not datasets:
            QMessageBox.information(self, "No Data", "No data available to export.")
            return
        
        # Create a temporary data grid to use the export functionality  
        # Use the first available dataset for the temp grid
        first_dataset = next(iter(datasets.values()))
        temp_grid = InteractiveDataGrid(first_dataset, "Export")
        
        # Generate filename with timestamp and operation name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        operation_name = self.operation_combo.currentText().replace(" ", "_")
        default_name = f"{operation_name}_{timestamp}"
        
        # Call the multi-sheet export method
        temp_grid.export_multi_sheet(datasets, default_name)
        
    def handle_error(self, error_msg: str):
        """Handle operation error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Operation failed")
        
        # Disable ShareFile button since operation failed
        self.sharefile_btn.setEnabled(False)
        
        QMessageBox.critical(self, "Operation Error", 
                           f"The operation failed with error:\n\n{error_msg}")
        
    def operation_finished(self):
        """Clean up after operation completes"""
        # Re-enable controls
        self.load_btn.setEnabled(True)
        self.operation_combo.setEnabled(True)
        self.start_date.setEnabled(True)
        self.end_date.setEnabled(True)
        
        # Hide progress if successful
        if self.progress_bar.value() >= 100:
            self.progress_bar.setVisible(False)
            self.status_label.setText("Operation completed successfully")
            
        # Clean up worker
        if self.current_worker:
            self.current_worker.deleteLater()
            self.current_worker = None
            
    def close_tab(self, index: int):
        """Close tab at index"""
        if index > 0:  # Don't close welcome tab
            self.results_tabs.removeTab(index)
    
    def save_to_sharefile(self):
        """Save current results to ShareFile"""
        if not self.current_results:
            QMessageBox.information(self, "No Data", "No data available to save to ShareFile.")
            return
        
        try:
            # Get current operation and dates
            operation_name = self.operation_combo.currentText()
            start_date = self.start_date.date()
            end_date = self.end_date.date()
            
            # Generate folder path and filename
            folder_path = ShareFileManager.generate_folder_path(operation_name, start_date, end_date)
            filename = ShareFileManager.generate_filename(operation_name, start_date, end_date)
            full_path = folder_path / filename
            
            logger.info(f"[SHAREFILE] Saving to: {full_path}")
            
            # Ensure directories exist
            if not ShareFileManager.ensure_directories_exist(folder_path):
                QMessageBox.critical(
                    self, 
                    "Directory Error", 
                    f"Could not create directory:\n{folder_path}\n\n"
                    "Please check network connectivity and permissions."
                )
                return
            
            # Prepare datasets for export
            datasets = self._prepare_datasets_for_export()
            
            if not datasets:
                QMessageBox.information(self, "No Data", "No data available to export.")
                return
            
            # Clean up any existing worker before starting new one
            if self.sharefile_export_worker and self.sharefile_export_worker.isRunning():
                self.sharefile_export_worker.quit()
                self.sharefile_export_worker.wait(1000)
                self.sharefile_export_worker.deleteLater()
            
            # Create and start export worker
            self.sharefile_export_worker = MultiSheetExportWorker(datasets, str(full_path))
            self.sharefile_export_worker.export_progress.connect(self.progress_bar.setValue, Qt.ConnectionType.QueuedConnection)
            self.sharefile_export_worker.export_complete.connect(self.on_sharefile_export_complete, Qt.ConnectionType.QueuedConnection)
            self.sharefile_export_worker.export_error.connect(self.on_sharefile_export_error, Qt.ConnectionType.QueuedConnection)
            self.sharefile_export_worker.finished.connect(self.on_sharefile_export_finished, Qt.ConnectionType.QueuedConnection)
            
            # Show progress and start export
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Saving to ShareFile...")
            
            # Disable buttons during export
            self.sharefile_btn.setEnabled(False)
            self.load_btn.setEnabled(False)
            
            self.sharefile_export_worker.start()
            
        except ValueError as e:
            QMessageBox.critical(self, "Configuration Error", str(e))
        except Exception as e:
            logger.error(f"[SHAREFILE] Unexpected error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"An unexpected error occurred:\n{str(e)}")
    
    def _prepare_datasets_for_export(self) -> dict:
        """Prepare datasets from current results for export"""
        datasets = {}
        
        if isinstance(self.current_results, dict):
            # Check if this is from Sales Receipt Import (legacy format)
            if 'main' in self.current_results or 'credit' in self.current_results or 'errors' in self.current_results:
                # Multi-sheet results (legacy format)
                if 'main' in self.current_results and self.current_results['main'] is not None:
                    datasets['Processed Data'] = self.current_results['main']
                    
                if 'credit' in self.current_results and self.current_results['credit'] is not None and len(self.current_results['credit']) > 0:
                    datasets['CM Import'] = self.current_results['credit']
                    
                if 'errors' in self.current_results and self.current_results['errors'] is not None and len(self.current_results['errors']) > 0:
                    datasets['Change Log'] = self.current_results['errors']
            else:
                # Handle Sales Receipt Tie Out format or other multi-sheet formats
                # Include all sheets from the result dictionary
                for sheet_name, dataframe in self.current_results.items():
                    if dataframe is not None:
                        try:
                            # Check if dataframe has data
                            if hasattr(dataframe, 'is_empty') and not dataframe.is_empty():
                                datasets[sheet_name] = dataframe
                            elif hasattr(dataframe, '__len__') and len(dataframe) > 0:
                                datasets[sheet_name] = dataframe
                        except Exception as e:
                            print(f"Warning: Error preparing sheet {sheet_name} for export: {e}")
                            # Still try to include the sheet
                            datasets[sheet_name] = dataframe
        else:
            # Single dataframe result
            datasets['Results'] = self.current_results
        
        return datasets
    
    def on_sharefile_export_complete(self, message: str):
        """Handle ShareFile export completion"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("ShareFile save completed")
        
        # Re-enable buttons
        self.sharefile_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        
        # Get the file path from the worker
        if self.sharefile_export_worker:
            file_path = self.sharefile_export_worker.file_path
            QMessageBox.information(
                self, 
                "ShareFile Save Complete", 
                f"File saved successfully to ShareFile:\n\n{file_path}\n\n{message}"
            )
    
    def on_sharefile_export_error(self, error: str):
        """Handle ShareFile export error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("ShareFile save failed")
        
        # Re-enable buttons
        self.sharefile_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        
        QMessageBox.critical(
            self, 
            "ShareFile Save Error", 
            f"Failed to save to ShareFile:\n\n{error}\n\n"
            "Please check network connectivity and permissions."
        )
    
    def on_sharefile_export_finished(self):
        """Handle ShareFile export thread cleanup"""
        if hasattr(self, 'sharefile_export_worker') and self.sharefile_export_worker:
            self.sharefile_export_worker.deleteLater()
            self.sharefile_export_worker = None