#!/usr/bin/env python3
"""
Test script to compare optimized vs original Ollama model performance
"""

import os
import time
from pathlib import Path

def test_original_model():
    """Test original Ollama model"""
    print("🔍 Testing Original Ollama Model...")
    try:
        from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer
        
        start_time = time.time()
        analyzer = OllamaDocumentAnalyzer()
        result = analyzer.analyze_document(form16_path)
        end_time = time.time()
        
        return {
            "name": "Original Ollama LLM",
            "time": end_time - start_time,
            "result": result,
            "success": True
        }
    except Exception as e:
        return {
            "name": "Original Ollama LLM",
            "time": 0,
            "error": str(e),
            "success": False
        }

def test_optimized_model():
    """Test optimized Ollama model"""
    print("🔍 Testing Optimized Ollama Model...")
    try:
        from src.core.optimized_ollama_analyzer import OptimizedOllamaAnalyzer
        
        start_time = time.time()
        analyzer = OptimizedOllamaAnalyzer()
        result = analyzer.analyze_document(form16_path)
        end_time = time.time()
        
        return {
            "name": "Optimized Ollama LLM",
            "time": end_time - start_time,
            "result": result,
            "success": True,
            "stats": analyzer.get_performance_stats()
        }
    except Exception as e:
        return {
            "name": "Optimized Ollama LLM",
            "time": 0,
            "error": str(e),
            "success": False
        }

def test_optimized_model_cached():
    """Test optimized model with cache hit"""
    print("🔍 Testing Optimized Model (Cached)...")
    try:
        from src.core.optimized_ollama_analyzer import OptimizedOllamaAnalyzer
        
        analyzer = OptimizedOllamaAnalyzer()
        
        # First run to populate cache
        print("   📥 First run (cache miss)...")
        start_time = time.time()
        result1 = analyzer.analyze_document(form16_path)
        end_time = time.time()
        first_run_time = end_time - start_time
        
        # Second run to test cache hit
        print("   📤 Second run (cache hit)...")
        start_time = time.time()
        result2 = analyzer.analyze_document(form16_path)
        end_time = time.time()
        second_run_time = end_time - start_time
        
        return {
            "name": "Optimized Ollama LLM (Cached)",
            "first_run_time": first_run_time,
            "cached_run_time": second_run_time,
            "speedup": first_run_time / second_run_time if second_run_time > 0 else 0,
            "result": result2,
            "success": True,
            "stats": analyzer.get_performance_stats()
        }
    except Exception as e:
        return {
            "name": "Optimized Ollama LLM (Cached)",
            "time": 0,
            "error": str(e),
            "success": False
        }

def print_result(test_name, result):
    """Print formatted test result"""
    print(f"\n{'='*60}")
    print(f"🤖 {test_name}")
    print(f"{'='*60}")
    
    if not result['success']:
        print(f"❌ Error: {result['error']}")
        return
    
    print("✅ Success!")
    
    if 'time' in result:
        print(f"⏱️  Time: {result['time']:.2f} seconds")
    elif 'first_run_time' in result:
        print(f"⏱️  First Run: {result['first_run_time']:.2f} seconds")
        print(f"⏱️  Cached Run: {result['cached_run_time']:.2f} seconds")
        print(f"🚀 Speedup: {result['speedup']:.1f}x faster")
    
    # Print extracted data
    if hasattr(result['result'], 'gross_salary'):
        print(f"💰 Gross Salary: ₹{result['result'].gross_salary:,.2f}")
    if hasattr(result['result'], 'tax_deducted'):
        print(f"🧾 Tax Deducted: ₹{result['result'].tax_deducted:,.2f}")
    if hasattr(result['result'], 'employee_name'):
        print(f"👤 Employee: {result['result'].employee_name}")
    if hasattr(result['result'], 'confidence'):
        print(f"📊 Confidence: {result['result'].confidence*100:.1f}%")
    if hasattr(result['result'], 'method'):
        print(f"🔧 Method: {result['result'].method}")
    
    # Print performance stats if available
    if 'stats' in result:
        print(f"\n📊 Performance Stats:")
        for key, value in result['stats'].items():
            print(f"   {key}: {value}")

def main():
    """Main test function"""
    global form16_path
    
    print("🚀 Ollama Model Optimization Test")
    print("=" * 60)
    
    form16_path = os.path.expanduser("~/Desktop/Income Tax 2024-2025/Form16.pdf")
    
    if not os.path.exists(form16_path):
        print(f"❌ Form 16 not found at: {form16_path}")
        return
    
    print(f"✅ Testing with: {Path(form16_path).name}")
    print()
    
    # Run tests
    results = []
    
    # Test 1: Original model
    results.append(test_original_model())
    
    # Test 2: Optimized model (first run)
    results.append(test_optimized_model())
    
    # Test 3: Optimized model with caching
    results.append(test_optimized_model_cached())
    
    # Print all results
    for result in results:
        print_result(result['name'], result)
    
    # Performance comparison
    print(f"\n{'='*60}")
    print("📊 PERFORMANCE COMPARISON")
    print(f"{'='*60}")
    
    successful_tests = [r for r in results if r['success']]
    
    if len(successful_tests) >= 2:
        original_time = successful_tests[0]['time']
        optimized_time = successful_tests[1]['time']
        
        if 'cached_run_time' in successful_tests[2]:
            cached_time = successful_tests[2]['cached_run_time']
            
            print(f"🏆 Performance Summary:")
            print(f"   Original: {original_time:.2f}s")
            print(f"   Optimized: {optimized_time:.2f}s")
            print(f"   Cached: {cached_time:.2f}s")
            print(f"   🚀 Speedup (vs original): {original_time/optimized_time:.1f}x")
            print(f"   🚀 Speedup (cached): {original_time/cached_time:.1f}x")
            
            if optimized_time < original_time:
                improvement = ((original_time - optimized_time) / original_time) * 100
                print(f"   📈 Improvement: {improvement:.1f}% faster")
    
    print(f"\n💡 Optimization Benefits:")
    print(f"   • Result caching for instant re-analysis")
    print(f"   • Parallel quarterly data processing")
    print(f"   • Optimized regex patterns")
    print(f"   • Performance monitoring and stats")
    print(f"   • Memory-efficient processing")

if __name__ == "__main__":
    main() 