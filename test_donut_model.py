#!/usr/bin/env python3
"""
Test script for the optimized Donut model with PDF support
"""

import os
import time
from pathlib import Path

def test_donut_model():
    """Test the optimized Donut model"""
    print("🚀 Testing Optimized Donut Model")
    print("=" * 60)
    
    form16_path = os.path.expanduser("~/Desktop/Income Tax 2024-2025/Form16.pdf")
    
    if not os.path.exists(form16_path):
        print(f"❌ Form 16 not found at: {form16_path}")
        return
    
    print(f"✅ Testing with: {Path(form16_path).name}")
    print()
    
    try:
        from src.models.donut_model_optimized import donut_model
        
        # Test 1: Load model
        print("📥 Loading Donut model...")
        start_time = time.time()
        success = donut_model.load_model()
        load_time = time.time() - start_time
        
        if not success:
            print("❌ Failed to load Donut model")
            return
        
        print(f"✅ Model loaded in {load_time:.2f}s")
        print()
        
        # Test 2: Analyze document
        print("🔍 Analyzing Form 16 with Donut...")
        start_time = time.time()
        result = donut_model.analyze_document(form16_path)
        analysis_time = time.time() - start_time
        
        # Print results
        print(f"\n{'='*60}")
        print("📊 DONUT MODEL RESULTS")
        print(f"{'='*60}")
        
        if result.get('success'):
            print("✅ Success!")
            print(f"⏱️  Analysis Time: {analysis_time:.2f} seconds")
            print(f"📊 Confidence: {result.get('confidence', 0)*100:.1f}%")
            print(f"🔧 Method: {result.get('method', 'N/A')}")
            
            # Print structured data
            structured_data = result.get('structured_data', {})
            if structured_data:
                print(f"\n📋 Extracted Data:")
                for key, value in structured_data.items():
                    if key == 'amounts':
                        print(f"   💰 Amounts: {len(value)} found")
                    elif key == 'names':
                        print(f"   👤 Names: {value}")
                    elif key == 'pan_numbers':
                        print(f"   🆔 PAN Numbers: {value}")
                    else:
                        print(f"   {key}: {value}")
            
            # Print raw output (first 200 chars)
            raw_output = result.get('raw_output', '')
            if raw_output:
                print(f"\n📄 Raw Output (first 200 chars):")
                print(f"   {raw_output[:200]}...")
            
            # Print performance stats
            stats = donut_model.get_performance_stats()
            print(f"\n📊 Performance Stats:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
            
            # Print model info
            model_info = donut_model.get_model_info()
            print(f"\n🤖 Model Info:")
            print(f"   Name: {model_info['name']}")
            print(f"   Version: {model_info['version']}")
            print(f"   Capabilities: {', '.join(model_info['capabilities'])}")
            
        else:
            print("❌ Analysis failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Performance comparison
        print(f"\n{'='*60}")
        print("📊 PERFORMANCE COMPARISON")
        print(f"{'='*60}")
        
        print(f"🏆 Donut Model Performance:")
        print(f"   Load Time: {load_time:.2f}s")
        print(f"   Analysis Time: {analysis_time:.2f}s")
        print(f"   Total Time: {load_time + analysis_time:.2f}s")
        
        # Compare with Ollama
        print(f"\n🔄 vs Ollama LLM (from previous tests):")
        print(f"   Ollama: ~28.65s")
        print(f"   Donut: ~{load_time + analysis_time:.2f}s")
        
        if load_time + analysis_time < 28.65:
            speedup = 28.65 / (load_time + analysis_time)
            print(f"   🚀 Donut is {speedup:.1f}x faster!")
        else:
            slowdown = (load_time + analysis_time) / 28.65
            print(f"   ⏰ Donut is {slowdown:.1f}x slower")
        
        print(f"\n💡 Donut Model Benefits:")
        print(f"   • Direct PDF processing (no manual conversion)")
        print(f"   • High accuracy for document understanding")
        print(f"   • Structured data extraction")
        print(f"   • Optimized for Form 16 analysis")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Install dependencies with: pip install transformers torch PyMuPDF")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_donut_model() 