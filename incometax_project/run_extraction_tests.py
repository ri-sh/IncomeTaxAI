#!/usr/bin/env python3
"""
Test Runner for Document Extraction and Task Calculation
Runs both test suites to verify extraction and calculation accuracy
"""

import os
import sys
import subprocess
from pathlib import Path

def run_test_file(test_file_path, test_name):
    """Run a test file and capture output"""
    print(f"\n🚀 Running {test_name}...")
    print("=" * 60)
    
    try:
        # Change to the project directory
        project_dir = Path(test_file_path).parent
        os.chdir(project_dir)
        
        # Run the test file
        result = subprocess.run(
            [sys.executable, test_file_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        # Print output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {test_name} completed successfully")
        else:
            print(f"❌ {test_name} failed with return code {result.returncode}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {test_name} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Error running {test_name}: {e}")
        return False

def main():
    """Run all extraction tests"""
    print("🧪 COMPREHENSIVE EXTRACTION & CALCULATION TEST SUITE")
    print("=" * 80)
    print("This will test both document extraction and tax calculation logic")
    print("against the reference values from tax_analysis_report.txt")
    print("=" * 80)
    
    # Get project directory
    project_dir = Path(__file__).parent
    
    # Define test files
    test_files = [
        {
            'file': project_dir / 'test_document_extraction.py',
            'name': 'Document Extraction Tests'
        },
        {
            'file': project_dir / 'test_task_calculation.py', 
            'name': 'Task Calculation Tests'
        }
    ]
    
    # Run tests
    results = []
    for test_config in test_files:
        if test_config['file'].exists():
            success = run_test_file(str(test_config['file']), test_config['name'])
            results.append({
                'name': test_config['name'],
                'success': success
            })
        else:
            print(f"❌ Test file not found: {test_config['file']}")
            results.append({
                'name': test_config['name'],
                'success': False
            })
    
    # Print final summary
    print("\n" + "=" * 80)
    print("🏁 FINAL TEST SUITE SUMMARY")
    print("=" * 80)
    
    total_suites = len(results)
    passed_suites = sum(1 for r in results if r['success'])
    failed_suites = total_suites - passed_suites
    
    print(f"Test Suites Run: {total_suites}")
    print(f"✅ Passed: {passed_suites}")
    print(f"❌ Failed: {failed_suites}")
    
    for result in results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"  {status} {result['name']}")
    
    if failed_suites > 0:
        print(f"\n⚠️  {failed_suites} test suite(s) failed. Check the output above for details.")
        print("💡 Common issues:")
        print("   • Document files not found in expected locations")
        print("   • AI extraction returning different values than expected")
        print("   • Calculation formulas need adjustment")
        print("   • Database connection issues")
    else:
        print(f"\n🎉 All test suites passed! Document extraction and calculations are working correctly.")
    
    print("=" * 80)
    
    # Return exit code
    return 0 if failed_suites == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)