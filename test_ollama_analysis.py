#!/usr/bin/env python3
"""
Test Ollama's ability to analyze tax documents and extract detailed information
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.ollama_document_analyzer import OllamaDocumentAnalyzer
from src.data.document_processor import DocumentProcessor

def test_ollama_document_analysis():
    """Test Ollama's document analysis capabilities"""
    
    print("🔍 Testing Ollama Document Analysis")
    print("=" * 50)
    
    # Initialize the analyzer
    try:
        analyzer = OllamaDocumentAnalyzer()
        if not analyzer.llm:
            print("❌ Ollama LLM not available")
            return False
        print("✅ Ollama LLM initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize Ollama: {e}")
        return False
    
    # Test documents from Income Tax 2024-2025 folder
    documents_path = Path("/Users/rishabh.roy/Desktop/Income Tax 2024-2025")
    
    if not documents_path.exists():
        print(f"❌ Documents folder not found: {documents_path}")
        return False
    
    # Get all documents
    documents = list(documents_path.glob("*"))
    documents = [d for d in documents if d.is_file() and d.suffix.lower() in ['.pdf', '.xlsx', '.xls']]
    
    print(f"📁 Found {len(documents)} documents to test")
    print()
    
    results = []
    
    for doc_path in documents:
        print(f"🔍 Testing: {doc_path.name}")
        print("-" * 40)
        
        try:
            # Test Ollama analysis
            ollama_result = analyzer.analyze_document(str(doc_path))
            
            # Check if it's an error result
            if ollama_result.errors and len(ollama_result.errors) > 0:
                print(f"❌ Ollama Analysis Failed: {ollama_result.errors[0]}")
                results.append({
                    "document": doc_path.name,
                    "ollama_success": False,
                    "ollama_error": ollama_result.errors[0]
                })
            else:
                print("✅ Ollama Analysis Successful!")
                print(f"📊 Confidence: {ollama_result.confidence}")
                print(f"🔧 Method: {ollama_result.extraction_method}")
                print(f"📄 Document Type: {ollama_result.document_type}")
                
                # Show key extracted fields
                key_fields = []
                
                # Check salary fields
                if ollama_result.gross_salary > 0:
                    key_fields.append(f"gross_salary: ₹{ollama_result.gross_salary:,.2f}")
                if ollama_result.employee_name:
                    key_fields.append(f"employee_name: {ollama_result.employee_name}")
                if ollama_result.pan:
                    key_fields.append(f"pan: {ollama_result.pan}")
                
                # Check bank fields
                if ollama_result.bank_name:
                    key_fields.append(f"bank_name: {ollama_result.bank_name}")
                if ollama_result.interest_amount > 0:
                    key_fields.append(f"interest_amount: ₹{ollama_result.interest_amount:,.2f}")
                
                # Check capital gains fields
                if ollama_result.total_capital_gains > 0:
                    key_fields.append(f"total_capital_gains: ₹{ollama_result.total_capital_gains:,.2f}")
                if ollama_result.long_term_capital_gains > 0:
                    key_fields.append(f"ltcg: ₹{ollama_result.long_term_capital_gains:,.2f}")
                if ollama_result.short_term_capital_gains > 0:
                    key_fields.append(f"stcg: ₹{ollama_result.short_term_capital_gains:,.2f}")
                
                # Check investment fields
                if ollama_result.epf_amount > 0:
                    key_fields.append(f"epf_amount: ₹{ollama_result.epf_amount:,.2f}")
                if ollama_result.elss_amount > 0:
                    key_fields.append(f"elss_amount: ₹{ollama_result.elss_amount:,.2f}")
                
                if key_fields:
                    print("📋 Key Extracted Data:")
                    for field in key_fields[:8]:  # Show first 8 fields
                        print(f"   • {field}")
                
                # Count non-empty fields
                extracted_fields = 0
                for field_name, field_value in ollama_result.__dict__.items():
                    if field_name not in ['document_type', 'confidence', 'extraction_method', 'errors', 'raw_text']:
                        if isinstance(field_value, (int, float)) and field_value > 0:
                            extracted_fields += 1
                        elif isinstance(field_value, str) and field_value and field_value.strip():
                            extracted_fields += 1
                
                results.append({
                    "document": doc_path.name,
                    "ollama_success": True,
                    "confidence": ollama_result.confidence,
                    "extracted_fields": extracted_fields,
                    "document_type": ollama_result.document_type
                })
                
        except Exception as e:
            print(f"❌ Error analyzing {doc_path.name}: {e}")
            results.append({
                "document": doc_path.name,
                "ollama_success": False,
                "ollama_error": str(e)
            })
        
        print()
    
    # Summary
    print("📊 ANALYSIS SUMMARY")
    print("=" * 50)
    
    successful = [r for r in results if r['ollama_success']]
    failed = [r for r in results if not r['ollama_success']]
    
    print(f"✅ Successful: {len(successful)}/{len(results)}")
    print(f"❌ Failed: {len(failed)}/{len(results)}")
    
    if successful:
        avg_confidence = sum(r['confidence'] for r in successful) / len(successful)
        avg_fields = sum(r['extracted_fields'] for r in successful) / len(successful)
        print(f"📈 Average Confidence: {avg_confidence:.2f}")
        print(f"📋 Average Fields Extracted: {avg_fields:.1f}")
        
        print("\n📄 Document Types Identified:")
        doc_types = {}
        for result in successful:
            doc_type = result.get('document_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
        
        for doc_type, count in doc_types.items():
            print(f"   • {doc_type}: {count} documents")
    
    if failed:
        print("\n❌ Failed Documents:")
        for result in failed:
            print(f"   • {result['document']}: {result['ollama_error']}")
    
    return len(successful) > 0

def test_comparison_with_regex():
    """Compare Ollama results with regex-based extraction"""
    
    print("\n🔄 Comparing Ollama vs Regex Extraction")
    print("=" * 50)
    
    # Initialize processors
    ollama_analyzer = OllamaDocumentAnalyzer()
    regex_processor = DocumentProcessor()
    
    # Test with Form16.pdf
    form16_path = "/Users/rishabh.roy/Desktop/Income Tax 2024-2025/Form16.pdf"
    
    if not os.path.exists(form16_path):
        print("❌ Form16.pdf not found")
        return
    
    print("📄 Testing Form16.pdf analysis")
    print("-" * 30)
    
    try:
        # Ollama analysis
        print("🤖 Ollama Analysis:")
        ollama_result = ollama_analyzer.analyze_document(form16_path)
        
        if not ollama_result.errors or len(ollama_result.errors) == 0:
            print("✅ Ollama extracted data successfully")
            print(f"   📄 Document Type: {ollama_result.document_type}")
            print(f"   📊 Confidence: {ollama_result.confidence}")
            
            # Count extracted fields
            extracted_fields = 0
            for field_name, field_value in ollama_result.__dict__.items():
                if field_name not in ['document_type', 'confidence', 'extraction_method', 'errors', 'raw_text']:
                    if isinstance(field_value, (int, float)) and field_value > 0:
                        extracted_fields += 1
                    elif isinstance(field_value, str) and field_value and field_value.strip():
                        extracted_fields += 1
            
            print(f"   📋 Fields extracted: {extracted_fields}")
            
            if ollama_result.gross_salary > 0:
                print(f"   💰 Gross Salary: ₹{ollama_result.gross_salary:,.2f}")
            if ollama_result.tax_deducted > 0:
                print(f"   🧾 Tax Deducted: ₹{ollama_result.tax_deducted:,.2f}")
        else:
            print(f"❌ Ollama failed: {ollama_result.errors[0]}")
        
        # Regex analysis
        print("\n🔍 Regex Analysis:")
        regex_result = regex_processor.process_document(form16_path, "form_16")
        
        if regex_result and regex_result.document_type != "Unknown":
            print("✅ Regex extracted data successfully")
            regex_fields = [k for k, v in regex_result.extracted_fields.items() if v]
            print(f"   📋 Fields extracted: {len(regex_fields)}")
            print(f"   📊 Confidence: {regex_result.confidence_score}")
            
            # Show some key fields
            if 'gross_salary' in regex_result.extracted_fields:
                print(f"   💰 Gross Salary: ₹{regex_result.extracted_fields['gross_salary']:,.2f}")
            if 'tax_deducted' in regex_result.extracted_fields:
                print(f"   🧾 Tax Deducted: ₹{regex_result.extracted_fields['tax_deducted']:,.2f}")
        else:
            print("❌ Regex failed to extract data")
            
    except Exception as e:
        print(f"❌ Comparison test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Ollama Document Analysis Test")
    print("=" * 60)
    
    # Test 1: Basic Ollama analysis
    success = test_ollama_document_analysis()
    
    # Test 2: Comparison with regex
    test_comparison_with_regex()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Ollama is working properly and can extract detailed information!")
    else:
        print("⚠️ Ollama needs attention - some documents failed analysis")
    
    print("✅ Test completed!") 