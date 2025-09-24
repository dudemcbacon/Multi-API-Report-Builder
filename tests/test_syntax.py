#!/usr/bin/env python3
"""
Test syntax of the modified files
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_syntax():
    """Test that our modified files have valid syntax"""
    print("Testing syntax of modified files...")
    
    files_to_test = [
        'src/services/async_avalara_api.py',
        'src/services/async_woocommerce_api.py', 
        'src/services/auth_manager.py'
    ]
    
    for file_path in files_to_test:
        print(f"\nTesting {file_path}...")
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            
            # Try to compile the code to check for syntax errors
            compile(code, file_path, 'exec')
            print(f"✓ {file_path} syntax is valid")
            
        except SyntaxError as e:
            print(f"✗ Syntax error in {file_path}: {e}")
            return False
        except FileNotFoundError:
            print(f"⚠ File not found: {file_path}")
        except Exception as e:
            print(f"✗ Error testing {file_path}: {e}")
            return False
    
    return True

def test_imports():
    """Test that we can import our modules without dependency errors"""
    print("\nTesting imports (may fail due to missing dependencies)...")
    
    try:
        # Test the auth manager (should work)
        import services.auth_manager
        print("✓ auth_manager import successful")
    except ImportError as e:
        print(f"⚠ auth_manager import failed (expected due to dependencies): {e}")
    except Exception as e:
        print(f"✗ auth_manager import error: {e}")
        return False
    
    # The async APIs will likely fail due to missing aiohttp, but syntax should be OK
    return True

def main():
    """Run syntax tests"""
    print("Testing Modified File Syntax")
    print("=" * 40)
    
    syntax_ok = test_syntax()
    import_ok = test_imports()
    
    print("\n" + "=" * 40)
    if syntax_ok:
        print("✓ All syntax tests passed")
        return True
    else:
        print("✗ Syntax errors found")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)