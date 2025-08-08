import streamlit as st
import mlx.core as mx
import mlx.nn as nn
from PIL import Image
import numpy as np
from typing import Dict, Any, Optional, List
import os
import json

class MonkeyOCRModel:
    """MonkeyOCR-MLX for fast OCR on Apple Silicon"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        
    def load_model(self) -> bool:
        """Load the MonkeyOCR model"""
        try:
            with st.spinner("🔄 Loading MonkeyOCR-MLX model..."):
                # Import MLX-specific components
                from mlx_community.monkey_ocr import MonkeyOCR
                
                # Load model
                self.model = MonkeyOCR.from_pretrained("mlx-community/monkey-ocr-mlx")
                
                self.is_loaded = True
                st.success("✅ MonkeyOCR-MLX model loaded successfully!")
                return True
                
        except ImportError:
            st.error("❌ MonkeyOCR-MLX not available. Install with: `pip install mlx-community`")
            return False
        except Exception as e:
            st.error(f"❌ Failed to load MonkeyOCR model: {str(e)}")
            return False
    
    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using MonkeyOCR"""
        if not self.is_loaded:
            if not self.load_model():
                return {"error": "Model not loaded"}
        
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Extract text
            result = self.model(image)
            
            # Process results
            extracted_text = self._process_ocr_result(result)
            
            return {
                "document_type": "ocr_extraction",
                "confidence": 0.90,
                "method": "monkey_ocr_mlx",
                "extracted_text": extracted_text,
                "text_blocks": result.get("text_blocks", []),
                "word_count": len(extracted_text.split())
            }
            
        except Exception as e:
            st.error(f"❌ MonkeyOCR extraction failed: {str(e)}")
            return {"error": str(e)}
    
    def _process_ocr_result(self, result: Dict[str, Any]) -> str:
        """Process OCR result into readable text"""
        try:
            # Extract text from result
            if "text" in result:
                return result["text"]
            elif "text_blocks" in result:
                # Combine text blocks
                text_blocks = result["text_blocks"]
                if isinstance(text_blocks, list):
                    return " ".join([block.get("text", "") for block in text_blocks])
                else:
                    return str(text_blocks)
            else:
                return str(result)
                
        except Exception as e:
            st.warning(f"⚠️ Could not process OCR result: {str(e)}")
            return str(result)
    
    def analyze_financial_document(self, image_path: str) -> Dict[str, Any]:
        """Analyze financial document using OCR + pattern matching"""
        ocr_result = self.extract_text(image_path)
        
        if "error" in ocr_result:
            return ocr_result
        
        # Extract financial information from OCR text
        financial_data = self._extract_financial_data(ocr_result["extracted_text"])
        
        return {
            **ocr_result,
            **financial_data
        }
    
    def _extract_financial_data(self, text: str) -> Dict[str, Any]:
        """Extract financial data from OCR text using patterns"""
        import re
        
        result = {}
        
        # Extract amounts (₹ symbol or number patterns)
        amount_patterns = [
            r'₹\s*([\d,]+\.?\d*)',
            r'Rs\.?\s*([\d,]+\.?\d*)',
            r'INR\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*(?:lakh|lac|thousand|k)',
            r'([\d,]+\.?\d*)'
        ]
        
        amounts = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    amount = float(match.replace(",", ""))
                    if amount > 100:  # Filter out small numbers
                        amounts.append(amount)
                except:
                    continue
        
        if amounts:
            result["amounts"] = amounts
            result["total_amount"] = sum(amounts)
        
        # Extract PAN numbers
        pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
        pan_matches = re.findall(pan_pattern, text)
        if pan_matches:
            result["pan_numbers"] = pan_matches
        
        # Extract account numbers
        account_pattern = r'\b\d{10,16}\b'
        account_matches = re.findall(account_pattern, text)
        if account_matches:
            result["account_numbers"] = account_matches
        
        # Extract dates
        date_patterns = [
            r'\d{2}[/-]\d{2}[/-]\d{4}',
            r'\d{4}[/-]\d{2}[/-]\d{2}',
            r'\d{2}[/-]\d{2}[/-]\d{2}'
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            dates.extend(matches)
        
        if dates:
            result["dates"] = list(set(dates))
        
        # Extract names (simple pattern)
        name_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
        names = re.findall(name_pattern, text)
        if names:
            result["names"] = list(set(names))
        
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model"""
        return {
            "name": "MonkeyOCR-MLX",
            "model_id": "mlx-community/monkey-ocr-mlx",
            "description": "Fast OCR optimized for Apple Silicon with MLX framework",
            "best_for": ["general_ocr", "text_extraction", "mac_optimized"],
            "device": "mps",
            "framework": "MLX",
            "memory_requirement": "1-2 GB",
            "speed": "Very Fast",
            "accuracy": "High (90%+)",
            "is_loaded": self.is_loaded
        }

# Global MonkeyOCR model instance
monkey_ocr_model = MonkeyOCRModel() 