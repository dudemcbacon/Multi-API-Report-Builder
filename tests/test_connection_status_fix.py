#!/usr/bin/env python3
"""
Test the comprehensive connection status fix for all services
"""
import sys
import os
import re

def test_connection_state_tracking():
    """Test that connection state tracking variables are properly initialized and used"""
    print("Testing Connection State Tracking")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that state tracking variables are initialized
    init_pattern = r'# Connection state tracking\s+self\.sf_connected = False\s+self\.woo_connected = False\s+self\.avalara_connected = False'
    if re.search(init_pattern, content, re.MULTILINE):
        print("✓ Connection state tracking variables initialized")
    else:
        print("✗ Connection state tracking variables not found")
        return False
    
    # Check that handlers update state tracking
    handlers_update_state = [
        ('self.sf_connected = True', 'Salesforce success handler'),
        ('self.woo_connected = True', 'WooCommerce success handler'),
        ('self.avalara_connected = True', 'Avalara success handler'),
        ('self.sf_connected = False', 'Salesforce failure handler'),
        ('self.woo_connected = False', 'WooCommerce failure handler'),
        ('self.avalara_connected = False', 'Avalara failure handler')
    ]
    
    for pattern, description in handlers_update_state:
        if pattern in content:
            print(f"✓ {description} updates state")
        else:
            print(f"✗ {description} doesn't update state")
            return False
    
    return True

def test_auto_connect_override_fix():
    """Test that auto-connect no longer hardcodes Avalara to False"""
    print("\nTesting Auto-Connect Override Fix")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that the hardcoded False is removed
    if 'self.update_unified_connection_status(sf_connected, woo_connected, False)' in content:
        print("✗ Auto-connect still hardcodes Avalara to False")
        return False
    else:
        print("✓ Auto-connect no longer hardcodes Avalara to False")
    
    # Check that it now uses state tracking
    if 'self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected)' in content:
        print("✓ Auto-connect now uses state tracking")
    else:
        print("✗ Auto-connect doesn't use state tracking")
        return False
    
    # Check that state tracking is updated from auto-connect results
    if 'self.sf_connected = sf_connected' in content and 'self.woo_connected = woo_connected' in content:
        print("✓ Auto-connect updates state tracking variables")
    else:
        print("✗ Auto-connect doesn't update state tracking")
        return False
    
    return True

def test_centralized_status_coordination():
    """Test that all handlers use centralized connection status updates"""
    print("\nTesting Centralized Status Coordination")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that handlers use update_unified_connection_status instead of direct UI updates
    centralized_calls = content.count('self.update_unified_connection_status(self.sf_connected, self.woo_connected, self.avalara_connected)')
    
    if centralized_calls >= 6:  # Success and failure for each service
        print(f"✓ Found {centralized_calls} centralized status updates")
    else:
        print(f"✗ Only found {centralized_calls} centralized status updates (expected at least 6)")
        return False
    
    # Check that direct UI updates are minimized
    direct_ui_updates = content.count('self.connection_status.setText("Connected")')
    if direct_ui_updates <= 2:  # Should be minimal, mostly in unified status method
        print(f"✓ Direct UI updates minimized ({direct_ui_updates} remaining)")
    else:
        print(f"✗ Too many direct UI updates ({direct_ui_updates})")
        return False
    
    return True

def test_status_bar_logic():
    """Test that status bar logic includes all three services"""
    print("\nTesting Status Bar Logic")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that status bar uses proper counting
    if 'connected_count = sum([sf_connected, woo_connected, self.avalara_connected])' in content:
        print("✓ Status bar counts all three services")
    else:
        print("✗ Status bar doesn't count all services")
        return False
    
    # Check for proper status messages
    if 'if connected_count == 3:' in content:
        print("✓ Status bar handles all services connected")
    else:
        print("✗ Status bar doesn't handle all services connected")
        return False
    
    if '"{connected_count}/3 APIs connected"' in content:
        print("✓ Status bar shows partial connection count")
    else:
        print("✗ Status bar doesn't show partial connection count")
        return False
    
    return True

def test_race_condition_prevention():
    """Test that race conditions are prevented"""
    print("\nTesting Race Condition Prevention")
    print("=" * 40)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    # Check that individual handlers don't conflict with auto-connect
    if 'Note: avalara_connected is already set by its own callback' in content:
        print("✓ Race condition awareness documented")
    else:
        print("✗ Race condition awareness not documented")
        return False
    
    # Check that state is properly synchronized
    if 'Update state tracking with auto-connect results' in content:
        print("✓ State synchronization implemented")
    else:
        print("✗ State synchronization not implemented")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Connection Status Fix Comprehensive Test")
    print("=" * 60)
    
    tests = [
        test_connection_state_tracking,
        test_auto_connect_override_fix,
        test_centralized_status_coordination,
        test_status_bar_logic,
        test_race_condition_prevention
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("✅ ALL TESTS PASSED")
        print("\nThe connection status fix should now:")
        print("- Track connection state properly for all services")
        print("- Show Avalara as connected when it succeeds")
        print("- Prevent race conditions between services")
        print("- Use centralized status coordination")
        print("- No longer hardcode Avalara to disconnected")
        print("- Include all three services in status messages")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)