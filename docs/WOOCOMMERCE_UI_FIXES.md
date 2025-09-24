# WooCommerce UI Display Fixes

## Problem Identified
The WooCommerce data was loading successfully in the backend (logs showed "Successfully loaded 5 WooCommerce data sources"), but the UI was not displaying any WooCommerce items in the tree. The issue was a **tree population conflict** between Salesforce and WooCommerce data loading.

## Root Cause Analysis

### The Problem Flow
1. **Salesforce loads first** (with 0 reports due to token issues)
2. **`on_reports_loaded()`** calls `super().on_reports_loaded()` 
3. **Parent method clears the tree** and populates with only Salesforce data
4. **WooCommerce loads later** (5 data sources)
5. **`on_woocommerce_data_loaded()`** calls `populate_mixed_tree_safely()`
6. **But tree was already populated and locked** by parent method

### Key Log Evidence
```
[ASYNC-MAIN-WINDOW] Salesforce reports loaded: 0 reports
[UI-REPORTS-LOADED] Clearing data tree...          # ← Parent method clears tree
[UI-REPORTS-LOADED] SUCCESS Data tree cleared
[ASYNC-MAIN-WINDOW] WooCommerce data sources loaded: 5 sources
[POPULATE-MIXED-TREE] Populated tree: 0 SF reports, 5 WC sources  # ← Claims success but UI doesn't show it
```

## Solution Implemented

### 🔧 Primary Fix: Bypass Parent Method
**File**: `src/ui/async_main_window.py`  
**Method**: `on_reports_loaded()`

**Before**:
```python
# Call parent method for UI updates, but catch any errors
try:
    super().on_reports_loaded(reports)
except AttributeError as e:
    logger.warning(f"[ASYNC-MAIN-WINDOW] AttributeError in on_reports_loaded, handling gracefully: {e}")
    # Handle the reports loading manually if parent method fails
    self.populate_mixed_tree_safely()
```

**After**:
```python
# Don't call parent method as it will clear the tree and interfere with mixed tree population
# Instead, handle everything in our mixed tree population
logger.info("[ASYNC-MAIN-WINDOW] Skipping parent on_reports_loaded to avoid tree conflicts")
self.populate_mixed_tree_safely()
```

### 🔍 Enhanced Debug Logging
Added comprehensive logging to track the tree population process:

1. **Data Source Logging**:
   ```python
   for i, source in enumerate(data_sources):
       logger.info(f"[ASYNC-MAIN-WINDOW] WC Source {i}: {source.get('name', 'Unknown')} - {source.get('type', 'Unknown')}")
   ```

2. **Tree Population Logging**:
   ```python
   logger.info(f"[POPULATE-MIXED-TREE] Starting with {sf_count} SF reports, {wc_count} WC sources")
   logger.info(f"[POPULATE-MIXED-TREE] Adding WooCommerce parent with {len(self.woocommerce_data_sources)} sources")
   ```

3. **Individual Item Logging**:
   ```python
   for i, source in enumerate(self.woocommerce_data_sources):
       logger.info(f"[POPULATE-MIXED-TREE] Adding WC source {i}: {source.get('name', 'Unknown')}")
   ```

### 🛡️ Improved Error Handling
Added better handling for missing data scenarios:

```python
else:
    logger.info("[POPULATE-MIXED-TREE] No Salesforce reports to add")

# And for WooCommerce:
else:
    logger.warning(f"[POPULATE-MIXED-TREE] No WooCommerce data sources to add: has_attr={hasattr(self, 'woocommerce_data_sources')}, data_exists={hasattr(self, 'woocommerce_data_sources') and bool(self.woocommerce_data_sources)}")
```

## Expected Tree Structure After Fix

### With WooCommerce Data
```
📊 Salesforce Reports     (if any Salesforce data)
├── 📁 Folder 1
│   ├── 📄 Report A
│   └── 📄 Report B
└── 📁 Folder 2
    └── 📄 Report C
🛒 WooCommerce Data
├── 📦 Products
├── 🛍️ Orders  
├── 👥 Customers
├── 📊 Reports
└── 🏷️ Coupons
```

### Without Salesforce Data (Common Scenario)
```
🛒 WooCommerce Data
├── 📦 Products
├── 🛍️ Orders
├── 👥 Customers
├── 📊 Reports
└── 🏷️ Coupons
```

## Technical Details

### Async Flow Timing
The fix handles both timing scenarios:

1. **Salesforce First**: 
   - Salesforce loads (even with 0 reports) → Tree populated with SF structure
   - WooCommerce loads → Tree repopulated with both SF + WC data

2. **WooCommerce First**:
   - WooCommerce loads → Tree populated with WC data only
   - Salesforce loads → Tree repopulated with both SF + WC data

### Data Structure Verification
WooCommerce data sources include:
```python
{
    'id': 'products',
    'name': 'Products', 
    'description': 'All products in your WooCommerce store',
    'type': 'products',
    'icon': 'fa5s.box',
    'modified': ''
}
```

### UI Integration Points
- **Tree Widget**: Uses existing QTreeWidget from parent class
- **Icons**: FontAwesome icons for visual distinction
- **Data Storage**: Uses `Qt.ItemDataRole.UserRole` for click handling
- **Styling**: Maintains consistent tree appearance

## Expected Log Output After Fix

### Successful WooCommerce Display
```
[ASYNC-MAIN-WINDOW] WooCommerce data sources loaded: 5 sources
[ASYNC-MAIN-WINDOW] WC Source 0: Products - products
[ASYNC-MAIN-WINDOW] WC Source 1: Orders - orders
[ASYNC-MAIN-WINDOW] WC Source 2: Customers - customers
[ASYNC-MAIN-WINDOW] WC Source 3: Reports - reports
[ASYNC-MAIN-WINDOW] WC Source 4: Coupons - coupons
[ASYNC-MAIN-WINDOW] Stored 5 WooCommerce data sources
[POPULATE-MIXED-TREE] Starting with 0 SF reports, 5 WC sources
[POPULATE-MIXED-TREE] No Salesforce reports to add
[POPULATE-MIXED-TREE] Adding WooCommerce parent with 5 sources
[POPULATE-MIXED-TREE] Adding WC source 0: Products
[POPULATE-MIXED-TREE] Adding WC source 1: Orders
[POPULATE-MIXED-TREE] Adding WC source 2: Customers
[POPULATE-MIXED-TREE] Adding WC source 3: Reports
[POPULATE-MIXED-TREE] Adding WC source 4: Coupons
[POPULATE-MIXED-TREE] Successfully added 5 WooCommerce items
[POPULATE-MIXED-TREE] Populated tree: 0 SF reports, 5 WC sources
```

## Testing Scenarios

### ✅ WooCommerce Only (No Salesforce)
- Tree shows "WooCommerce Data" section with 5 items
- Each item clickable and functional

### ✅ Both APIs Connected
- Tree shows both "Salesforce Reports" and "WooCommerce Data" sections
- Both sections independently functional

### ✅ Salesforce Only (No WooCommerce)
- Tree shows "Salesforce Reports" section only
- WooCommerce section absent (no empty section)

### ✅ Neither API Connected
- Tree empty or shows connection prompts
- No crashes or errors

The WooCommerce UI should now display properly in all scenarios!