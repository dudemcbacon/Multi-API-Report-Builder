#!/usr/bin/env python3
"""
Validate async version syntax without running or importing dependencies
"""
import ast
import sys
from pathlib import Path

def validate_python_syntax(file_path):
    """Validate Python syntax of a file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Parse the AST to check for syntax errors
        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error reading file: {e}"

def main():
    """Validate all async-related files"""
    print("Async Version Syntax Validation")
    print("=" * 50)
    
    files_to_check = [
        "src/ui/async_main_window.py",
        "src/ui/async_manager.py", 
        "src/ui/async_mixins.py",
        "launch_async.py"
    ]
    
    all_valid = True
    
    for file_path in files_to_check:
        full_path = Path(file_path)
        if full_path.exists():
            is_valid, error = validate_python_syntax(full_path)
            if is_valid:
                print(f"✅ {file_path}: Valid syntax")
            else:
                print(f"❌ {file_path}: {error}")
                all_valid = False
        else:
            print(f"⚠️ {file_path}: File not found")
            all_valid = False
    
    print("\n" + "=" * 50)
    if all_valid:
        print("🎉 All async files have valid syntax!")
        print("\nThe async version is syntactically correct.")
        print("UI element debugging and fixing logic has been added:")
        print("- _debug_ui_elements() method logs UI element availability")
        print("- _fix_ui_references() method attempts to fix missing UI references")
        print("- populate_reports_tree_safely() method handles tree population robustly")
        print("- Enhanced null safety throughout the UI update methods")
        print("\nNext steps:")
        print("1. Install dependencies: pip install PyQt6 qasync aiohttp")
        print("2. Test the async version: python launch_async.py")
        print("3. Compare with QThread version: python launch.py")
    else:
        print("❌ Some files have syntax errors. Please fix them before testing.")
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())