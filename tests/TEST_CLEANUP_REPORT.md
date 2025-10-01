# Test Suite Cleanup Report

## Files Removed (Security - Hardcoded Credentials)
1. `test_api_limits_discovery.py` - **REMOVED** - Contained hardcoded API keys and company URL
2. `test_pagination_solution.py` - **REMOVED** - Contained hardcoded API keys and company URL
3. `test_pagination_strategies.py` - **REMOVED** - Contained hardcoded API keys and company URL

## Files Sanitized
1. `test_consumer_secret.py` - Changed company-specific Salesforce URL to generic example URL

## Obsolete/Debug Files to Remove

### Debug & Temporary Files
- `debug_dataframe_issue.py` - Debug script, not a proper test
- `verify_woocommerce_fix.py` - Verification script, not a test

### Duplicate/Fixed Files (Superseded by fixes in main code)
- `test_auto_connect_fix.py` - Tested a specific fix, now in main code
- `test_avalara_fixed.py` - Tested a specific fix, now in main code
- `test_cleaned_async_woo.py` - Testing cleaned version, superseded
- `test_connection_status_fix.py` - Tested a specific fix, now in main code
- `test_dataframe_fix.py` - Tested a specific fix, now in main code
- `test_fixes.py` - Generic fix testing, superseded
- `test_fixes_logic.py` - Generic fix testing, superseded
- `test_session_fix.py` - Tested a specific fix, now in main code
- `test_woocommerce_fix.py` - Tested a specific fix, now in main code

### Simple/Diagnostic Files (Superseded by comprehensive tests)
- `test_avalara_simple.py` - Superseded by `test_avalara_integration.py`
- `quickbase_api_test_simple.py` - Superseded by `quickbase_api_comprehensive_test.py`
- `quickbase_diagnostic_test.py` - Diagnostic script, not a proper test

### Potentially Obsolete Exploratory Tests
- `test_order_numbers.py` - Exploratory analysis
- `test_pagination_with_existing_api.py` - Pagination exploration
- `test_payment_id_data_analysis.py` - Data analysis, not a test
- `test_payment_id_performance.py` - Performance analysis, may keep
- `test_payment_id_matching_logic.py` - Logic validation, may keep
- `test_vectorized_woocommerce_lookup.py` - Implementation test, may keep
- `test_polars_operations_integration.py` - May keep if testing polars usage
- `test_aiohttp_performance.py` - Performance test, may keep
- `test_concurrency_benefits.py` - Performance test, may keep

### Migration/Async Conversion Tests (Obsolete after migration complete)
- `test_async_integration.py` - Async migration test
- `test_async_api_init.py` - Async migration test
- `test_async_api_completion.py` - Async migration test
- `test_async_migration.py` - Async migration test
- `test_async_version.py` - Async version test
- `validate_async_syntax.py` - Syntax validation, migration complete

### Refactoring Tests (Obsolete after refactor complete)
- `test_manager_refactor.py` - Manager pattern refactor test
- `test_main_window_cleanup.py` - Cleanup test
- `test_code_structure.py` - Structure validation

### Other Potentially Obsolete
- `test_syntax.py` - Syntax checking, should use linter instead
- `test_env_loading.py` - Basic env test, superseded by integration tests
- `test_class_vars.py` - Class variable test, specific to old implementation
- `test_company_structure.py` - Company structure test (may contain sensitive info)
- `test_cm_data_handling.py` - Specific data handling test
- `test_result_display.py` - UI test, may be obsolete
- `test_operation_structure.py` - Structure test, may be obsolete

## Core Tests to KEEP

### API Tests
- `test_salesforce_api_functionality.py` - Core SF API tests
- `test_salesforce_jwt.py` - JWT authentication tests
- `test_woocommerce_api_functionality.py` - Core WooCommerce API tests
- `test_avalara_integration.py` - Avalara integration tests
- `test_avalara_transactions.py` - Avalara transaction tests
- `test_avalara_dotenv.py` - Avalara env config tests
- `test_avalara_connection_status.py` - Avalara connection tests
- `test_quickbase_integration.py` - QuickBase integration tests
- `quickbase_api_comprehensive_test.py` - QuickBase comprehensive tests

### Operation Tests
- `test_sales_receipt_import.py` - Core business logic
- `test_sales_receipt_processing.py` - Core business logic
- `test_sales_receipt_tie_out.py` - Core business logic
- `test_integration_sales_receipt.py` - Integration test

### Data Processing Tests
- `test_data_processing_pipeline.py` - Core data pipeline
- `test_data_grid_integration.py` - UI data grid tests
- `test_multi_sheet_export.py` - Export functionality

### System Tests
- `test_comprehensive.py` - Comprehensive system test
- `test_complete_integration.py` - Complete integration test
- `test_performance_baseline.py` - Performance baseline
- `test_sharefile_functionality.py` - ShareFile integration
- `test_ui_connection.py` - UI connection tests
- `test_custom_report_routing.py` - Custom report tests
- `test_soql_query.py` - SOQL query tests
- `test_event_loop_issue.py` - Event loop handling
- `test_session_management.py` - Session management
- `test_api_version_compatibility.py` - API version tests
- `test_consumer_secret.py` - Consumer secret handling
- `test_auto_connect_restoration.py` - Auto-connect tests
- `test_optimized_payment_fetching.py` - Optimized fetching

### Test Runner
- `run_all_tests.py` - Test runner script

## Recommendation
Remove all files listed in "Obsolete/Debug Files to Remove" sections. These are:
1. Temporary debug/fix scripts that served their purpose during development
2. Migration tests that are no longer relevant after migration is complete
3. Simple versions superseded by comprehensive tests
4. Exploratory analysis scripts that aren't proper tests
