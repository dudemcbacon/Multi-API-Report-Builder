# Test Suite

This directory contains the comprehensive test suite for the Multi-API Report Builder application.

## Running Tests

### Run All Tests
```bash
python tests/run_all_tests.py
```

### Run Individual Tests
```bash
python tests/test_salesforce_api_functionality.py
python tests/test_woocommerce_api_functionality.py
python tests/test_quickbase_integration.py
```

## Test Categories

### API Tests
- **test_salesforce_api_functionality.py** - Salesforce API functionality tests
- **test_salesforce_jwt.py** - JWT Bearer Flow authentication tests
- **test_woocommerce_api_functionality.py** - WooCommerce REST API tests
- **test_avalara_integration.py** - Avalara tax API integration tests
- **test_avalara_transactions.py** - Avalara transaction tests
- **test_avalara_connection_status.py** - Avalara connection status tests
- **test_avalara_dotenv.py** - Avalara environment configuration tests
- **test_quickbase_integration.py** - QuickBase API integration tests
- **quickbase_api_comprehensive_test.py** - Comprehensive QuickBase API tests

### Business Logic Tests
- **test_sales_receipt_import.py** - Sales receipt import operation tests
- **test_sales_receipt_processing.py** - Sales receipt processing tests
- **test_sales_receipt_tie_out.py** - Sales receipt reconciliation tests
- **test_integration_sales_receipt.py** - Sales receipt integration tests

### Data Processing Tests
- **test_data_processing_pipeline.py** - Data processing pipeline tests
- **test_polars_operations_integration.py** - Polars dataframe operations tests
- **test_vectorized_woocommerce_lookup.py** - Vectorized data lookup tests
- **test_payment_id_matching_logic.py** - Payment ID matching logic tests

### Performance Tests
- **test_performance_baseline.py** - Performance baseline tests
- **test_payment_id_performance.py** - Payment ID matching performance tests
- **test_aiohttp_performance.py** - Async HTTP performance tests
- **test_concurrency_benefits.py** - Concurrent operations performance tests
- **test_optimized_payment_fetching.py** - Optimized API fetching tests

### UI Tests
- **test_data_grid_integration.py** - Data grid widget integration tests
- **test_ui_connection.py** - UI connection management tests
- **test_custom_report_routing.py** - Custom report builder routing tests

### Integration Tests
- **test_comprehensive.py** - Comprehensive system integration tests
- **test_complete_integration.py** - Complete application integration tests
- **test_sharefile_functionality.py** - ShareFile integration tests
- **test_multi_sheet_export.py** - Multi-sheet Excel export tests

### System Tests
- **test_event_loop_issue.py** - Event loop handling tests
- **test_session_management.py** - Session management tests
- **test_api_version_compatibility.py** - API version compatibility tests
- **test_consumer_secret.py** - Consumer secret handling tests
- **test_auto_connect_restoration.py** - Auto-connect restoration tests
- **test_soql_query.py** - SOQL query generation tests

## Test Organization

- All test files use the `test_*.py` naming convention
- Tests use environment variables for credentials (never hardcoded)
- Tests import from the `src/` package
- Integration tests may require API credentials in `.env` file

## Security

- **No hardcoded credentials** - All tests use environment variables
- **No company-specific information** - Tests use generic examples
- **No identifying file paths** - Tests use relative paths

## Adding New Tests

1. Create test file in `tests/` directory with `test_*.py` prefix
2. Import from `src/` package
3. Use pytest or unittest framework
4. Document what the test covers
5. Use environment variables for any credentials

Example:
```python
# tests/test_my_feature.py
import pytest
import os
from src.module import MyClass

def test_my_feature():
    """Test description"""
    api_key = os.getenv('API_KEY')
    obj = MyClass(api_key=api_key)
    result = obj.my_method()
    assert result == expected_value
```

## Cleanup History

See [TEST_CLEANUP_REPORT.md](TEST_CLEANUP_REPORT.md) for details on test suite cleanup and removed files.

## Test Count

Current test suite contains **36 test files** covering:
- API integrations (9 files)
- Business operations (4 files)
- Data processing (4 files)
- Performance (5 files)
- UI components (3 files)
- System integration (7 files)
- Infrastructure (4 files)
