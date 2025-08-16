#!/usr/bin/env python3
"""
Test Runner for Tax Calculator Unit Tests
Run this script to verify the tax calculation logic
"""

import os
import sys
import django
from pathlib import Path

# Setup Django environment
PROJECT_ROOT = Path(__file__).parent
sys.path.append(str(PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()

import unittest
from tests.test_tax_calculator import TestIncomeTaxCalculator, TestDeductionCalculator, TestCalculationAccuracy

def run_tests():
    """Run all tax calculator tests"""
    print("=" * 80)
    print("🧪 TAX CALCULATOR UNIT TESTS")
    print("=" * 80)
    print("Testing Income Tax Calculator and Deduction Calculator utilities")
    print("These tests verify the mathematical accuracy of tax calculations")
    print("=" * 80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestIncomeTaxCalculator,
        TestDeductionCalculator, 
        TestCalculationAccuracy
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(test_suite)
    
    # Print summary
    print("=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    print(f"Tests Run: {result.testsRun}")
    print(f"✅ Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failures: {len(result.failures)}")
    print(f"🚨 Errors: {len(result.errors)}")
    
    if result.failures:
        print(f"\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback.splitlines()[-1]}")
    
    if result.errors:
        print(f"\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback.splitlines()[-1]}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    if result.wasSuccessful():
        print("🎉 All tests passed! Tax calculation logic is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please review the calculation logic.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)