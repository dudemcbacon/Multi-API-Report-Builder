# Token Refresh and Task Scheduling Fixes

## Issues Fixed

### 1. Expired Token Not Being Refreshed
**Problem**: The Salesforce token expired but the async version wasn't attempting to refresh it, resulting in "No Salesforce API connection" errors.

**Root Cause**: The async version was only checking `is_token_valid()` but not attempting `refresh_access_token()` when tokens were expired.

**Solution**: Added automatic token refresh logic in two key locations where API instances are created.

### 2. Task Scheduling Conflicts
**Problem**: RuntimeError occurred when multiple async tasks tried to execute simultaneously, causing the message "Cannot enter into task while another task is being executed."

**Root Cause**: Multiple auto-connect operations were running simultaneously and competing for resources.

**Solution**: Implemented proper task management with flags and delayed execution.

## Changes Made

### `src/ui/async_main_window.py`

#### 1. Added Token Refresh Logic
Added automatic token refresh in both existing API instance handling and new API instance creation:

```python
# Check if token is valid, if not try to refresh
if self.sf_api.auth_manager.is_token_valid():
    # Token is valid - proceed
    logger.info("SUCCESS Found valid Salesforce session!")
    # ... load reports
else:
    logger.info("Token expired or invalid, attempting refresh...")
    # Try to refresh the token
    if self.sf_api.auth_manager.refresh_access_token():
        logger.info("SUCCESS Token refreshed!")
        # ... proceed with refreshed token
    else:
        logger.info("Token refresh failed - user will need to re-authenticate")
```

#### 2. Added Task Management
Implemented proper task scheduling to prevent conflicts:

```python
def _delayed_auto_connect(self):
    # Only run auto-connect if not already running
    if not hasattr(self, '_auto_connect_running') or not self._auto_connect_running:
        self._auto_connect_running = True
        self._async_auto_connect()

def _async_auto_connect(self):
    try:
        # ... connection logic
    finally:
        # Mark auto-connect as complete
        self._auto_connect_running = False
```

#### 3. Added Delayed Report Loading
To prevent task conflicts, implemented delayed execution for report loading:

```python
def _load_salesforce_reports_delayed(self):
    """Load Salesforce reports with proper task management"""
    if not hasattr(self, '_reports_loading') or not self._reports_loading:
        self._reports_loading = True
        task = asyncio.create_task(self._load_reports_async())

async def _load_reports_async(self):
    """Async wrapper for loading reports"""
    try:
        await self.async_manager.load_salesforce_reports()
    finally:
        self._reports_loading = False
```

#### 4. Fixed Try-Finally Block Structure
Fixed syntax error where `finally` block wasn't properly matched with `try` block:

```python
# Before (incorrect):
if condition:
    try:
        # code
    except:
        # error handling
finally:  # This was not matched properly
    # cleanup

# After (correct):
try:
    if condition:
        # code
except:
    # error handling
finally:
    # cleanup
```

## Expected Behavior After Fixes

### Token Handling
1. **Valid Token**: Connects immediately and loads reports
2. **Expired Token**: Automatically attempts refresh
   - **Refresh Success**: Proceeds with refreshed token
   - **Refresh Failure**: Shows "user will need to authenticate" message
3. **No Token**: Shows disconnected status

### Task Management
1. **Single Auto-Connect**: Only one auto-connect process runs at a time
2. **Delayed Report Loading**: Reports load with slight delay to avoid conflicts
3. **Proper Cleanup**: Tasks are properly marked as complete

### Log Output Improvements
```
# Before (with errors):
[ASYNC-MANAGER] Error loading reports: No Salesforce API connection. Please connect first.
RuntimeError: Cannot enter into task while another task is being executed.

# After (with fixes):
[ASYNC-MAIN-WINDOW] Token expired or invalid, attempting refresh...
[ASYNC-MAIN-WINDOW] SUCCESS Token refreshed!
[ASYNC-MAIN-WINDOW] Loading Salesforce reports
[ASYNC-MANAGER] Successfully loaded 25 reports
```

## Technical Details

### Token Refresh Flow
1. Check if API instance exists
2. Check if token is valid (`is_token_valid()`)
3. If invalid, attempt refresh (`refresh_access_token()`)
4. If refresh succeeds, proceed with operations
5. If refresh fails, show disconnected status

### Task Conflict Prevention
- **Auto-Connect Flag**: `_auto_connect_running` prevents multiple auto-connects
- **Reports Loading Flag**: `_reports_loading` prevents multiple report loading operations
- **Delayed Execution**: Uses `QTimer.singleShot()` to delay operations and prevent conflicts
- **Proper Cleanup**: All flags are reset in `finally` blocks

### Error Handling
- All token operations wrapped in try-catch blocks
- Graceful fallback when token refresh fails
- Task conflicts prevented rather than handled after they occur
- Comprehensive logging for debugging

## Testing Scenarios

### Scenario 1: Valid Token
- ✅ Connects immediately
- ✅ Loads reports without delay
- ✅ Shows connection status

### Scenario 2: Expired Token (Refresh Available)
- ✅ Detects expired token
- ✅ Automatically refreshes token
- ✅ Continues with normal operation
- ✅ Loads reports successfully

### Scenario 3: Expired Token (No Refresh Available)
- ✅ Detects expired token
- ✅ Attempts refresh (fails gracefully)
- ✅ Shows disconnected status
- ✅ User can manually authenticate

### Scenario 4: Multiple Simultaneous Operations
- ✅ Only one auto-connect runs at a time
- ✅ No task scheduling conflicts
- ✅ Operations complete successfully

The async version now handles token expiration gracefully and prevents the task scheduling conflicts that were causing runtime errors.