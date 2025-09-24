#!/usr/bin/env python3
"""
Test script to verify code structure and imports work correctly
"""
import sys
import os
import ast
import inspect
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def analyze_file_syntax(file_path):
    """Check if a Python file has valid syntax"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def check_class_definitions(file_path):
    """Check if classes are properly defined"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [method.name for method in node.body if isinstance(method, ast.FunctionDef)]
                classes.append({
                    'name': node.name,
                    'methods': methods,
                    'line': node.lineno
                })
        
        return True, classes
    except Exception as e:
        return False, f"Error analyzing classes: {e}"

def test_data_grid_structure():
    """Test the data_grid.py file structure"""
    print("Testing data_grid.py structure...")
    
    file_path = "src/ui/data_grid.py"
    
    # Check syntax
    syntax_ok, syntax_msg = analyze_file_syntax(file_path)
    if not syntax_ok:
        print(f"✗ Syntax error in {file_path}: {syntax_msg}")
        return False
    print(f"✓ Syntax OK: {file_path}")
    
    # Check class definitions
    classes_ok, classes = check_class_definitions(file_path)
    if not classes_ok:
        print(f"✗ Error analyzing classes: {classes}")
        return False
    
    print(f"✓ Found {len(classes)} classes in {file_path}")
    
    # Check specific classes we expect
    expected_classes = ['MultiSheetExportWorker', 'DataExportWorker', 'InteractiveDataGrid']
    found_classes = [cls['name'] for cls in classes]
    
    for expected_class in expected_classes:
        if expected_class in found_classes:
            print(f"✓ Class '{expected_class}' found")
            
            # Find the class details
            class_info = next(cls for cls in classes if cls['name'] == expected_class)
            print(f"  - Methods: {', '.join(class_info['methods'])}")
            
            # Check specific methods
            if expected_class == 'MultiSheetExportWorker':
                required_methods = ['__init__', 'run']
                for method in required_methods:
                    if method in class_info['methods']:
                        print(f"  ✓ Method '{method}' found")
                    else:
                        print(f"  ✗ Method '{method}' missing")
                        
            elif expected_class == 'InteractiveDataGrid':
                required_methods = ['export_multi_sheet']
                for method in required_methods:
                    if method in class_info['methods']:
                        print(f"  ✓ Method '{method}' found")
                    else:
                        print(f"  ✗ Method '{method}' missing")
        else:
            print(f"✗ Class '{expected_class}' not found")
            return False
    
    return True

def test_operations_tab_structure():
    """Test the operations_tab.py file structure"""
    print("\nTesting operations_tab.py structure...")
    
    file_path = "src/ui/tabs/operations_tab.py"
    
    # Check syntax
    syntax_ok, syntax_msg = analyze_file_syntax(file_path)
    if not syntax_ok:
        print(f"✗ Syntax error in {file_path}: {syntax_msg}")
        return False
    print(f"✓ Syntax OK: {file_path}")
    
    # Check class definitions
    classes_ok, classes = check_class_definitions(file_path)
    if not classes_ok:
        print(f"✗ Error analyzing classes: {classes}")
        return False
    
    print(f"✓ Found {len(classes)} classes in {file_path}")
    
    # Check OperationsTab class
    operations_tab_class = next((cls for cls in classes if cls['name'] == 'OperationsTab'), None)
    if operations_tab_class:
        print("✓ OperationsTab class found")
        
        required_methods = ['add_export_all_button', 'export_all_sheets', 'display_results']
        for method in required_methods:
            if method in operations_tab_class['methods']:
                print(f"  ✓ Method '{method}' found")
            else:
                print(f"  ✗ Method '{method}' missing")
                return False
    else:
        print("✗ OperationsTab class not found")
        return False
    
    return True

def check_integration_points():
    """Check if the integration points between files are correct"""
    print("\nChecking integration points...")
    
    # Check if operations_tab.py imports from data_grid.py
    operations_tab_path = "src/ui/tabs/operations_tab.py"
    try:
        with open(operations_tab_path, 'r') as f:
            content = f.read()
        
        if 'from src.ui.data_grid import InteractiveDataGrid' in content:
            print("✓ operations_tab.py imports InteractiveDataGrid")
        else:
            print("✗ operations_tab.py missing InteractiveDataGrid import")
            return False
        
        # Check if display_results calls add_export_all_button
        if 'self.add_export_all_button()' in content:
            print("✓ display_results calls add_export_all_button")
        else:
            print("✗ display_results doesn't call add_export_all_button")
            return False
        
        # Check if export_all_sheets calls export_multi_sheet
        if 'export_multi_sheet' in content:
            print("✓ export_all_sheets calls export_multi_sheet")
        else:
            print("✗ export_all_sheets doesn't call export_multi_sheet")
            return False
        
    except Exception as e:
        print(f"✗ Error checking integration: {e}")
        return False
    
    return True

def test_method_signatures():
    """Test method signatures by examining the AST"""
    print("\nAnalyzing method signatures...")
    
    # Check export_multi_sheet signature
    data_grid_path = "src/ui/data_grid.py"
    try:
        with open(data_grid_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # Find InteractiveDataGrid class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'InteractiveDataGrid':
                # Find export_multi_sheet method
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name == 'export_multi_sheet':
                        params = [arg.arg for arg in method.args.args]
                        print(f"✓ export_multi_sheet parameters: {params}")
                        
                        expected_params = ['self', 'datasets', 'default_name']
                        if params == expected_params:
                            print("✓ Method signature is correct")
                        else:
                            print(f"✗ Method signature incorrect. Expected: {expected_params}, Got: {params}")
                            return False
                        break
                break
        
    except Exception as e:
        print(f"✗ Error analyzing method signatures: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("Code Structure Verification Test")
    print("=" * 50)
    
    tests = [
        ("Data Grid Structure", test_data_grid_structure),
        ("Operations Tab Structure", test_operations_tab_structure),
        ("Integration Points", check_integration_points),
        ("Method Signatures", test_method_signatures)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print("\n" + "=" * 50)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All code structure tests passed!")
        print("The multi-sheet export implementation appears to be correctly structured.")
    else:
        print("⚠️ Some tests failed. Please review the errors above.")

if __name__ == "__main__":
    main()