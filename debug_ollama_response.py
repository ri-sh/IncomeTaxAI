#!/usr/bin/env python3
"""
Debug script to see exact Ollama response for Form16 analysis
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.ollama_document_analyzer import OllamaDocumentAnalyzer

def debug_form16_analysis():
    """Debug the Form16 analysis to see exact Ollama response"""
    
    print("🔍 Debugging Form16 Analysis")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = OllamaDocumentAnalyzer()
    
    # Get the raw text content first
    form16_path = "/Users/rishabh.roy/Desktop/Income Tax 2024-2025/Form16.pdf"
    text_content = analyzer._extract_text_content(Path(form16_path))
    
    print(f"📄 Document: Form16.pdf")
    print(f"📏 Text length: {len(text_content)} characters")
    print(f"📋 First 500 chars: {text_content[:500]}...")
    print()
    
    # Get the prompt that would be sent
    prompt = analyzer._create_form16_specific_prompt("Form16.pdf", text_content)
    print("🤖 PROMPT SENT TO OLLAMA:")
    print("-" * 30)
    print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
    print()
    
    # Get the raw response
    try:
        response = analyzer.llm.complete(prompt)
        print("📤 RAW OLLAMA RESPONSE:")
        print("-" * 30)
        print(response.text)
        print()
        
        # Try to parse it
        print("🔧 PARSING ATTEMPT:")
        print("-" * 30)
        parsed = analyzer._parse_json_response(response.text)
        if parsed:
            print("✅ Parsed successfully:")
            for key, value in parsed.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Failed to parse")
            
    except Exception as e:
        print(f"❌ Error getting response: {e}")

if __name__ == "__main__":
    debug_form16_analysis() 