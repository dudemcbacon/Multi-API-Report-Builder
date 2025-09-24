#!/usr/bin/env python3
"""
Master test runner - executes all tests in sequence
Provides comprehensive verification before making any optimizations
"""
import sys
import os
import time
import subprocess
from datetime import datetime

def run_test_script(script_name: str, description: str):
    """Run a test script and capture results"""
    print(f"\n{'='*80}")
    print(f"RUNNING: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    try:
        # Use the virtual environment Python
        python_exe = ".venv/Scripts/python.exe"
        
        result = subprocess.run(
            [python_exe, script_name],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        duration = time.time() - start_time
        
        print(f"Exit Code: {result.returncode}")
        print(f"Duration: {duration:.2f} seconds")
        
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        
        if success:
            print(f"✓ {description} PASSED")
        else:
            print(f"✗ {description} FAILED")
        
        return success, duration, result.stdout, result.stderr
        
    except Exception as e:
        duration = time.time() - start_time
        print(f"✗ Exception running {script_name}: {e}")
        return False, duration, "", str(e)

def main():
    """Run all test scripts in sequence"""
    print("COMPREHENSIVE TESTING SUITE")
    print("Running all tests to verify system functionality")
    print("This will confirm everything works before making optimizations")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Define test scripts in order of execution
    tests = [
        ("test_fixes_simple.py", "Boolean Expression Fixes Verification"),
        ("test_salesforce_api_functionality.py", "Salesforce API Functionality"),
        ("test_woocommerce_api_functionality.py", "WooCommerce API Functionality"),
        ("test_performance_baseline.py", "Performance Baseline Measurement"),
        ("test_integration_sales_receipt.py", "Sales Receipt Import Integration"),
    ]
    
    results = []
    total_start_time = time.time()
    
    print(f"\nRunning {len(tests)} test suites...\n")
    
    # Run each test
    for script, description in tests:
        success, duration, stdout, stderr = run_test_script(script, description)
        
        results.append({
            'script': script,
            'description': description,
            'success': success,
            'duration': duration,
            'stdout': stdout,
            'stderr': stderr
        })
        
        # If a critical test fails, ask if we should continue
        if not success and script in ["test_fixes_simple.py", "test_salesforce_api_functionality.py"]:
            print(f"\n⚠️  CRITICAL TEST FAILED: {description}")
            response = input("Continue with remaining tests? (y/n): ").strip().lower()
            if response != 'y':
                print("Testing aborted by user.")
                break
    
    total_duration = time.time() - total_start_time
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUITE SUMMARY")
    print(f"{'='*80}")
    
    passed = sum(1 for r in results if r['success'])
    failed = len(results) - passed
    
    print(f"Total Tests Run: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total Duration: {total_duration:.2f} seconds")
    
    print(f"\nDetailed Results:")
    for result in results:
        status = "✓ PASSED" if result['success'] else "✗ FAILED"
        print(f"  {status:10} {result['description']:40} ({result['duration']:.2f}s)")
    
    # Provide recommendations
    print(f"\n{'='*80}")
    print("RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED!")
        print("\n✅ System Status: HEALTHY")
        print("✅ Boolean Expression Fixes: WORKING")
        print("✅ API Connections: FUNCTIONAL")
        print("✅ Data Processing: OPERATIONAL")
        print("\n🚀 READY FOR PERFORMANCE OPTIMIZATIONS!")
        print("\nNext steps:")
        print("1. Review performance baseline results")
        print("2. Implement httpx upgrade for HTTP/2 support")
        print("3. Add async/concurrent processing")
        print("4. Implement connection pooling")
    else:
        print("❌ SOME TESTS FAILED!")
        print("\n⚠️  System Status: NEEDS ATTENTION")
        print("\n🛑 DO NOT PROCEED WITH OPTIMIZATIONS YET!")
        print("\nRequired actions:")
        print("1. Fix all failing tests")
        print("2. Re-run test suite")
        print("3. Confirm all tests pass")
        print("4. Then proceed with optimizations")
        
        print(f"\nFailed Tests:")
        for result in results:
            if not result['success']:
                print(f"  ❌ {result['description']}")
    
    print(f"\n{'='*80}")
    print(f"Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)