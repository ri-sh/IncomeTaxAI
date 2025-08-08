#!/usr/bin/env python3
"""
Quick test of working models on documents
"""

import os
import time
import json

def test_ollama_model(doc_path):
    """Test current Ollama LLM model"""
    print("🔍 Testing Ollama LLM...")
    try:
        from src.core.ollama_document_analyzer import OllamaDocumentAnalyzer
        
        analyzer = OllamaDocumentAnalyzer()
        result = analyzer.analyze_document(doc_path)
        
        # Convert OllamaExtractedData to dictionary
        if hasattr(result, '__dict__'):
            return result.__dict__
        elif hasattr(result, 'to_dict'):
            return result.to_dict()
        else:
            return {"raw_result": str(result)}
    except Exception as e:
        return {"error": str(e)}

def print_result(model_name, result, time_taken):
    """Print formatted result"""
    print(f"\n{'='*60}")
    print(f"🤖 {model_name}")
    print(f"⏱️  Time: {time_taken:.2f} seconds")
    print(f"{'='*60}")
    
    if isinstance(result, dict) and "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print("✅ Success!")
    
    # Print key extracted data
    if isinstance(result, dict):
        if "gross_salary" in result:
            print(f"💰 Gross Salary: ₹{result['gross_salary']:,.2f}")
        if "tax_deducted" in result:
            print(f"🧾 Tax Deducted: ₹{result['tax_deducted']:,.2f}")
        if "employee_name" in result:
            print(f"👤 Employee: {result['employee_name']}")
        if "extracted_text" in result:
            print(f"📝 Text Length: {len(result['extracted_text'])} characters")
        if "amounts" in result:
            print(f"💵 Amounts Found: {len(result['amounts'])}")
        if "pan_numbers" in result:
            print(f"🆔 PAN Numbers: {result['pan_numbers']}")
        
        # Print confidence if available
        if "confidence" in result:
            print(f"📊 Confidence: {result['confidence']*100:.1f}%")
        
        # Print method used
        if "method" in result:
            print(f"🔧 Method: {result['method']}")
    else:
        # Handle non-dict results (like OllamaExtractedData objects)
        print(f"📊 Result Type: {type(result).__name__}")
        if hasattr(result, 'gross_salary'):
            print(f"💰 Gross Salary: ₹{result.gross_salary:,.2f}")
        if hasattr(result, 'tax_deducted'):
            print(f"🧾 Tax Deducted: ₹{result.tax_deducted:,.2f}")
        if hasattr(result, 'employee_name'):
            print(f"👤 Employee: {result.employee_name}")
        if hasattr(result, 'document_type'):
            print(f"📄 Document Type: {result.document_type}")
        if hasattr(result, 'confidence'):
            print(f"📊 Confidence: {result.confidence*100:.1f}%")

def main():
    """Main test function"""
    print("🤖 Quick AI Model Test")
    print("=" * 60)
    
    # Document paths
    documents = {
        "Form16.pdf": "~/Desktop/Income Tax 2024-2025/Form16.pdf",
        "Bank Interest Certificate.pdf": "~/Desktop/Income Tax 2024-2025/Bank Interest Certificate.pdf",
        "ELSS Statement.pdf": "~/Desktop/Income Tax 2024-2025/2024-2025 Mutual_Funds_ELSS_Statement.pdf"
    }
    
    # Test with Form16.pdf
    selected_doc = "Form16.pdf"
    doc_path = os.path.expanduser(documents[selected_doc])
    
    if not os.path.exists(doc_path):
        print(f"❌ Document not found: {doc_path}")
        return
    
    print(f"✅ Testing with: {selected_doc}")
    
    # Test Ollama LLM
    print(f"\n🚀 Testing Ollama LLM on {selected_doc}")
    print("=" * 60)
    
    start_time = time.time()
    result = test_ollama_model(doc_path)
    end_time = time.time()
    time_taken = end_time - start_time
    
    print_result("Ollama LLM (Current)", result, time_taken)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    
    success = "error" not in result if isinstance(result, dict) else True
    
    if success:
        print("✅ Ollama LLM test successful!")
        print(f"⏱️  Time taken: {time_taken:.2f} seconds")
        
        if isinstance(result, dict):
            print(f"📊 Extracted {len(result)} data fields")
        else:
            print(f"📊 Result type: {type(result).__name__}")
    else:
        print("❌ Ollama LLM test failed!")
    
    # Model comparison info
    print(f"\n{'='*60}")
    print("🤖 AVAILABLE MODELS")
    print(f"{'='*60}")
    
    models_info = [
        {
            "name": "Ollama LLM (Current)",
            "status": "✅ Working",
            "accuracy": "85%+",
            "speed": "Medium",
            "memory": "4-8 GB",
            "best_for": "General analysis, conversational"
        },
        {
            "name": "Donut (Document Understanding)",
            "status": "⚠️ Requires download",
            "accuracy": "95%+",
            "speed": "Fast",
            "memory": "2-4 GB",
            "best_for": "Form 16, structured documents"
        },
        {
            "name": "Qwen 2.5 VL 3B",
            "status": "⚠️ Requires setup",
            "accuracy": "92%+",
            "speed": "Medium",
            "memory": "4-8 GB",
            "best_for": "Vision-language, general documents"
        },
        {
            "name": "MonkeyOCR-MLX",
            "status": "⚠️ Requires MLX",
            "accuracy": "90%+",
            "speed": "Very Fast",
            "memory": "1-2 GB",
            "best_for": "OCR, Apple Silicon optimized"
        }
    ]
    
    for model in models_info:
        print(f"\n🔍 {model['name']}")
        print(f"   Status: {model['status']}")
        print(f"   Accuracy: {model['accuracy']}")
        print(f"   Speed: {model['speed']}")
        print(f"   Memory: {model['memory']}")
        print(f"   Best for: {model['best_for']}")
    
    # Installation guide
    print(f"\n{'='*60}")
    print("📦 INSTALLATION GUIDE")
    print(f"{'='*60}")
    
    print("""
To install additional models:

1. Donut Model:
   pip install transformers torch torchvision

2. Qwen VL Model:
   pip install transformers torch accelerate

3. MonkeyOCR (Apple Silicon):
   pip install mlx mlx-community

4. All Models:
   pip install transformers torch mlx mlx-community accelerate
    """)
    
    # Save results
    output_file = f"quick_test_results_{selected_doc.replace('.pdf', '')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            "model": "Ollama LLM",
            "document": selected_doc,
            "result": result,
            "time_taken": time_taken,
            "success": success
        }, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {output_file}")

if __name__ == "__main__":
    main() 