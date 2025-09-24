# Async Migration Guide for Salesforce Report Pull

## Overview

This guide demonstrates how to migrate from QThread-based workers to modern async/await patterns using qasync or native asyncio integration.

## Installation

For the best PyQt6 async integration, install qasync:
```bash
pip install qasync
```

## Migration Examples

### 1. Test Connection Operation

**Before (QThread):**
```python
class SalesforceConnectionWorker(QThread):
    connection_result = pyqtSignal(dict)
    
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_async())
        finally:
            loop.close()
    
    async def _run_async(self):
        result = await self.sf_api.test_connection()
        self.connection_result.emit(result)

# Usage:
self.connection_worker = SalesforceConnectionWorker("test_connection", self.sf_api)
self.connection_worker.connection_result.connect(self.on_connection_result)
self.connection_worker.start()
```

**After (Async):**
```python
@async_slot
async def test_connection(self):
    try:
        self.update_status("Testing connection...")
        result = await self.sf_api.test_connection()
        
        if result['success']:
            self.update_status(f"Connected to {result['organization']}")
        else:
            self.show_error(f"Connection failed: {result['error']}")
    except Exception as e:
        self.show_error(f"Connection error: {str(e)}")

# Usage:
self.test_btn.clicked.connect(self.test_connection)
```

### 2. Load Reports Operation

**Before:**
```python
self.reports_worker = SalesforceConnectionWorker("load_reports", self.sf_api)
self.reports_worker.reports_loaded.connect(self.on_reports_loaded)
self.reports_worker.error_occurred.connect(self.on_reports_error)
self.reports_worker.finished.connect(self.on_reports_worker_finished)
self.reports_worker.start()
```

**After:**
```python
@async_slot
async def load_salesforce_reports(self):
    try:
        self.progress_bar.setVisible(True)
        reports = await self.sf_api.get_reports()
        
        if reports:
            self.populate_reports_tree(reports)
            self.status_bar.showMessage(f"Loaded {len(reports)} reports")
        else:
            self.status_bar.showMessage("No reports found")
    except Exception as e:
        QMessageBox.warning(self, "Error", f"Failed to load reports: {str(e)}")
    finally:
        self.progress_bar.setVisible(False)
```

### 3. Load Report Data

**Before:**
```python
self.data_worker = SalesforceConnectionWorker(
    "load_report_data", 
    self.sf_api,
    report_id=report_data['id'],
    report_name=report_data['name']
)
self.data_worker.report_data_loaded.connect(self.on_report_data_loaded)
self.data_worker.error_occurred.connect(self.on_data_loading_error)
self.data_worker.start()
```

**After:**
```python
@async_slot
async def load_report_data(self, report_id, report_name):
    try:
        self.update_status(f"Loading {report_name}...")
        
        # Create fresh API context for clean session
        async with AsyncSalesforceAPI(auth_manager=self.auth_manager) as api:
            dataframe = await api.get_report_data(report_id, filters=self.get_filters())
            
        if dataframe is not None:
            self.display_dataframe(dataframe, report_name)
        else:
            self.show_error(f"No data found in report: {report_name}")
            
    except Exception as e:
        self.show_error(f"Failed to load report: {str(e)}")
```

## Key Patterns

### 1. Async Context Managers
```python
# Ensures proper resource cleanup
async with AsyncSalesforceAPI() as api:
    result = await api.get_report_data(report_id)
```

### 2. Concurrent Operations
```python
@async_slot
async def load_multiple_reports(self, report_ids):
    # Load all reports concurrently
    tasks = []
    async with AsyncSalesforceAPI() as api:
        for report_id in report_ids:
            tasks.append(api.get_report_data(report_id))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    for report_id, result in zip(report_ids, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to load {report_id}: {result}")
        else:
            self.process_report(result)
```

### 3. Progress Updates
```python
@async_slot
async def long_operation_with_progress(self):
    total_steps = 10
    self.progress_bar.setMaximum(total_steps)
    
    for i in range(total_steps):
        # Do work
        await self.do_step(i)
        
        # Update progress
        self.progress_bar.setValue(i + 1)
        
        # Allow UI to update
        await asyncio.sleep(0)  # Yield to event loop
```

### 4. Cancellation Support
```python
class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._current_task = None
    
    @async_slot
    async def start_operation(self):
        # Cancel any existing operation
        if self._current_task:
            self._current_task.cancel()
        
        # Start new operation
        self._current_task = asyncio.current_task()
        try:
            result = await self.long_running_operation()
        except asyncio.CancelledError:
            self.status_label.setText("Operation cancelled")
            raise
        finally:
            self._current_task = None
```

## Setup in main_window.py

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Set up async runner
        self._async_runner = AsyncRunner(self)
        
        # Your existing initialization...
        self.init_ui()
    
    def closeEvent(self, event):
        # Clean up async resources
        self._async_runner.cleanup()
        super().closeEvent(event)
```

## Benefits Summary

1. **Simpler Code**: No worker classes, just async methods
2. **Better Error Handling**: Direct try/except in async methods
3. **Natural Concurrency**: Use asyncio.gather() for parallel operations
4. **No Thread Issues**: No more "Event loop closed" errors
5. **Better Testing**: Async functions can be tested directly

## Migration Checklist

- [ ] Install qasync: `pip install qasync`
- [ ] Add AsyncRunner to main window
- [ ] Convert simple operations first (test_connection)
- [ ] Update button connections to use async methods
- [ ] Remove QThread worker classes
- [ ] Test concurrent operations
- [ ] Update error handling patterns
- [ ] Add cancellation support where needed