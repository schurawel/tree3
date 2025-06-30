#!/usr/bin/env python3
"""
Script to run all Python test files in ResearchGuideModule/tests directory.

This script finds all Python files in the tests directory and runs pytest
on each one, reporting the results.
"""

import os
import sys
import glob
import subprocess
import datetime

# Set up paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
TESTS_DIR = os.path.join(BASE_DIR, "ResearchGuideModule", "tests")

def print_header(text, char="="):
    """Print a header with the given text."""
    print(f"\n{char * 60}")
    print(f"{text}")
    print(f"{char * 60}")

def run_test(test_file):
    """Run pytest on a specific test file."""
    file_name = os.path.basename(test_file)
    print(f"\nRunning test: {file_name}")
    print("-" * 40)
    
    # Run the test using pytest directly
    result = subprocess.run([sys.executable, "-m", "pytest", test_file, "-v"], 
                           capture_output=True, text=True)
    
    # Print output
    print(result.stdout)
    if result.stderr:
        print("ERRORS:")
        print(result.stderr)
        
    return result.returncode == 0  # True if passed, False if failed

def main():
    """Main function to run all tests."""
    print_header(f"Running all tests - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find all Python test files
    test_files = glob.glob(os.path.join(TESTS_DIR, "*.py"))
    
    if not test_files:
        print(f"No test files found in {TESTS_DIR}")
        return
    
    # Filter to only run actual test files (those starting with "test_")
    test_files = [f for f in test_files if os.path.basename(f).startswith("test_")]
    
    if not test_files:
        print(f"No test files matching pattern 'test_*.py' found in {TESTS_DIR}")
        return
    
    print(f"Found {len(test_files)} test files to run")
    
    # Run each test and collect results
    results = {}
    for test_file in test_files:
        passed = run_test(test_file)
        results[test_file] = passed
    
    # Print summary
    print_header("Test Summary")
    total = len(results)
    passed = sum(1 for passed in results.values() if passed)
    failed = total - passed
    
    print(f"Total tests:  {total}")
    print(f"Passed tests: {passed}")
    print(f"Failed tests: {failed}")
    
    # List failed tests if any
    if failed > 0:
        print("\nFailed tests:")
        for test_file, passed in results.items():
            if not passed:
                print(f"  - {os.path.basename(test_file)}")
        sys.exit(1)
    else:
        print("\nAll tests passed! 🎉")
        sys.exit(0)

if __name__ == "__main__":
    main()
