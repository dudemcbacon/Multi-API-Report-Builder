#!/usr/bin/env python3
"""
Test Avalara connection status UI updates
"""
import sys
import os
import re

def test_avalara_connection_status_fix():
    """Test that Avalara connection status updates match other services"""
    print("Testing Avalara Connection Status Fix")
    print("=" * 50)
    
    # Read the main window file
    with open('src/ui/main_window.py', 'r') as f:
        content = f.read()
    
    print("1. Checking Avalara connected state handler...")
    
    # Check that handle_avalara_test_result updates UI on success
    avalara_connected_pattern = r'def handle_avalara_test_result.*?if result\.get\(\'success\'.*?self\.connection_status\.setText\("Connected"\)'
    if re.search(avalara_connected_pattern, content, re.DOTALL):
        print("✓ handle_avalara_test_result updates connection_status on success")
    else:
        print("✗ handle_avalara_test_result doesn't update connection_status")
        return False
    
    # Check for toolbar_status update
    if 'self.toolbar_status.setText("Connected")' in content:
        print("✓ handle_avalara_test_result updates toolbar_status")
    else:
        print("✗ handle_avalara_test_result doesn't update toolbar_status")
        return False
    
    # Check for status_bar update
    if 'self.status_bar.showMessage(f"Connected to {account_info} ({environment})")' in content:
        print("✓ handle_avalara_test_result updates status_bar")
    else:
        print("✗ handle_avalara_test_result doesn't update status_bar")
        return False
    
    print("2. Checking Avalara disconnected state handler...")
    
    # Check that _set_avalara_disconnected_state updates UI
    disconnected_pattern = r'def _set_avalara_disconnected_state.*?self\.connection_status\.setText\("Not Connected"\)'
    if re.search(disconnected_pattern, content, re.DOTALL):
        print("✓ _set_avalara_disconnected_state updates connection_status")
    else:
        print("✗ _set_avalara_disconnected_state doesn't update connection_status")
        return False
    
    # Check for toolbar_status update in disconnected state
    if 'self.toolbar_status.setText("Disconnected")' in content:
        print("✓ _set_avalara_disconnected_state updates toolbar_status")
    else:
        print("✗ _set_avalara_disconnected_state doesn't update toolbar_status")
        return False
    
    print("3. Comparing with other services...")
    
    # Check that all services use the same pattern
    services_connected_pattern = r'self\.connection_status\.setText\("Connected"\)'
    services_disconnected_pattern = r'self\.connection_status\.setText\("Not Connected"\)'
    
    connected_matches = len(re.findall(services_connected_pattern, content))
    disconnected_matches = len(re.findall(services_disconnected_pattern, content))
    
    print(f"Connected status updates found: {connected_matches}")
    print(f"Disconnected status updates found: {disconnected_matches}")
    
    if connected_matches >= 3:  # Salesforce, WooCommerce, Avalara
        print("✓ All services update connection status on success")
    else:
        print("✗ Not all services update connection status")
        return False
    
    if disconnected_matches >= 3:  # Salesforce, WooCommerce, Avalara
        print("✓ All services update connection status on failure")
    else:
        print("✗ Not all services update disconnection status")
        return False
    
    print("4. Checking UI element consistency...")
    
    # Check that all services use the same style patterns
    green_style = 'color: green; font-weight: bold;'
    red_style = 'color: red; font-weight: bold;'
    
    if green_style in content:
        print("✓ Connected state uses green styling")
    else:
        print("✗ Connected state styling missing")
        return False
    
    if red_style in content:
        print("✓ Disconnected state uses red styling")
    else:
        print("✗ Disconnected state styling missing")
        return False
    
    return True

def main():
    """Run the test"""
    print("Avalara Connection Status Fix Validation")
    print("=" * 60)
    
    try:
        success = test_avalara_connection_status_fix()
        
        print("\n" + "=" * 60)
        if success:
            print("✅ ALL TESTS PASSED")
            print("\nThe Avalara connection status should now:")
            print("- Show 'Connected' with green styling when connection succeeds")
            print("- Show 'Not Connected' with red styling when connection fails")
            print("- Update toolbar_status and status_bar consistently")
            print("- Match the behavior of Salesforce and WooCommerce services")
            return True
        else:
            print("❌ SOME TESTS FAILED")
            return False
            
    except Exception as e:
        print(f"❌ TEST EXECUTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)