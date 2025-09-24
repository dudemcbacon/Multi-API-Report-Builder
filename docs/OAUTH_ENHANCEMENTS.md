# OAuth Dialog Enhancements

## Overview
Enhanced the OAuth authentication dialog to fix the blank contentDoor page issue and improve Salesforce compatibility.

## Problem Solved
The Salesforce OAuth flow was working correctly up until the contentDoor authorization page, which appeared blank in the embedded WebEngine browser due to security restrictions. This prevented users from completing the authorization process.

## Enhancements Implemented

### 1. Enhanced WebEngine Configuration
- **Comprehensive Browser Settings**: Configured 21+ WebEngine attributes for maximum Salesforce compatibility
- **Modern User Agent**: Set to Chrome 120 user agent string to ensure proper site rendering
- **Language Configuration**: Added proper Accept-Language headers
- **Security Settings**: Balanced security with functionality (enabled JavaScript, disabled insecure content)

Key configurations:
```python
profile.setHttpUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...")
profile.setHttpAcceptLanguage("en-US,en;q=0.9")
profile.settings().setAttribute(profile.settings().WebAttribute.JavascriptEnabled, True)
profile.settings().setAttribute(profile.settings().WebAttribute.LocalStorageEnabled, True)
# ... and 19 more attributes
```

### 2. Blank Page Detection
- **JavaScript Content Analysis**: Automatically detects if contentDoor page is blank by checking content length
- **3-Second Delay**: Allows page to fully load before checking for blank content
- **Threshold-Based Detection**: Pages with less than 50 characters of content are considered blank

### 3. ContentDoor URL Extraction
- **Smart URL Parsing**: Extracts real authorization URLs from contentDoor wrapper URLs
- **Nested URL Support**: Handles multiple levels of URL encoding and contentDoor nesting
- **Direct Redirect**: Automatically redirects to extracted authorization URL when possible

Features:
- Extracts `startURL` parameters from contentDoor URLs
- Handles URL-encoded nested parameters
- Reconstructs clean OAuth authorization URLs
- Supports both single and double-encoded URLs

### 4. User-Friendly Fallback Options
When contentDoor page appears blank, users get a dialog with options:
- **Refresh Page**: Retry loading the current page
- **Open in External Browser**: Launch authorization in system default browser
- **Cancel**: Exit the authentication process

### 5. External Browser Integration
- **Automatic URL Cleaning**: Extracts clean authorization URL before opening externally
- **User Instructions**: Clear guidance on completing auth in external browser
- **Seamless Return**: App continues monitoring for auth completion

## Technical Details

### Files Modified
- `src/ui/oauth_dialog.py`: Enhanced WebEngine setup and added blank page handling

### New Methods Added
- `_check_for_blank_contentdoor()`: JavaScript-based content detection
- `_handle_contentdoor_check()`: Process content analysis results
- `_extract_authorization_url_from_contentdoor()`: URL extraction logic
- `_show_blank_page_options()`: User choice dialog
- `_open_external_browser()`: External browser launcher

### Enhanced User Experience
1. **Automatic Detection**: No user action needed for most blank page cases
2. **Clear Status Messages**: Real-time feedback on authentication progress
3. **Multiple Options**: Fallback choices when embedded browser fails
4. **External Browser Support**: Seamless handoff to system browser when needed

## Testing
Created comprehensive test suite (`test_oauth_enhancements.py`) validating:
- ✅ ContentDoor URL extraction with multiple test cases
- ✅ WebEngine attribute configuration
- ✅ User agent and language settings
- ✅ All 21 WebEngine security and compatibility attributes

## Expected Outcome
These enhancements should resolve the "blank contentDoor page" issue by:

1. **Better Compatibility**: Enhanced WebEngine configuration improves rendering of Salesforce pages
2. **Automatic Recovery**: Blank page detection with automatic URL extraction and redirect
3. **User Control**: Clear options when automatic recovery isn't possible
4. **External Fallback**: Reliable external browser option for problematic cases

The OAuth flow should now work seamlessly from start to finish, with automatic handling of contentDoor issues and clear user guidance when manual intervention is needed.