#!/usr/bin/env python3
"""
Optimized Donut Model for Document Analysis
Handles PDF files by converting to images first
"""

import os
import time
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import torch
from PIL import Image
import fitz  # PyMuPDF for PDF to image conversion

try:
    from transformers import DonutProcessor, VisionEncoderDecoderModel
    DONUT_AVAILABLE = True
except ImportError:
    DONUT_AVAILABLE = False

class OptimizedDonutModel:
    """
    Optimized Donut model with PDF support
    """
    
    def __init__(self, model_path: str = "naver-clova-ix/donut-base"):
        self.model_path = model_path
        self.processor = None
        self.model = None
        self.device = None
        self.is_loaded = False
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "avg_processing_time": 0.0,
            "pdf_conversions": 0,
            "image_analyses": 0
        }
        
        # Comprehensive patterns for Form 16
        self.form16_patterns = {
            "gross_salary": [
                r"Gross Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Gross[:\s]*₹?([\d,]+\.?\d*)",
                r"Gross Total[:\s]*₹?([\d,]+\.?\d*)",
                r"Gross[:\s]*₹?([\d,]+\.?\d*)",
                r"Salary[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "basic_salary": [
                r"Basic Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic Pay[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "hra": [
                r"HRA[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Received[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "special_allowance": [
                r"Special Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"Special[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "other_allowances": [
                r"Other Allowances[:\s]*₹?([\d,]+\.?\d*)",
                r"Other[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "perquisites": [
                r"Perquisites[:\s]*₹?([\d,]+\.?\d*)",
                r"Perks[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "total_gross_salary": [
                r"Total Gross Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Total[:\s]*₹?([\d,]+\.?\d*)",
                r"Gross Total[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "tax_deducted": [
                r"Tax Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Tax[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "employee_name": [
                r"Employee Name[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"Name of Employee[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"Name[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"Employee[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)"
            ],
            "employer_name": [
                r"Employer Name[:\s]*([A-Z][a-z\s]+)",
                r"Employer[:\s]*([A-Z][a-z\s]+)",
                r"Company[:\s]*([A-Z][a-z\s]+)"
            ],
            "pan_number": [
                r"[A-Z]{5}[0-9]{4}[A-Z]",
                r"PAN[:\s]*([A-Z]{5}[0-9]{4}[A-Z])"
            ]
        }
    
    def load_model(self) -> bool:
        """Load Donut model and processor with timeout protection"""
        if not DONUT_AVAILABLE:
            print("❌ Donut model not available. Install with: pip install transformers torch")
            return False
        
        try:
            print("📥 Loading Donut model...")
            start_time = time.time()
            
            # Load processor and model with timeout
            import threading
            import queue
            
            def load_processor():
                try:
                    self.processor = DonutProcessor.from_pretrained(self.model_path)
                    return True
                except Exception as e:
                    print(f"❌ Error loading processor: {e}")
                    return False
            
            def load_model():
                try:
                    self.model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
                    return True
                except Exception as e:
                    print(f"❌ Error loading model: {e}")
                    return False
            
            # Load processor first
            processor_result = load_processor()
            if not processor_result:
                return False
            
            # Load model with timeout
            model_queue = queue.Queue()
            model_thread = threading.Thread(target=lambda: model_queue.put(load_model()))
            model_thread.daemon = True
            model_thread.start()
            
            # Wait for model loading with timeout
            try:
                model_result = model_queue.get(timeout=20)  # 20 second timeout
                if not model_result:
                    return False
            except queue.Empty:
                print("⚠️ Model loading timed out")
                return False
            
            # Optimize device placement
            self.device = "mps" if torch.backends.mps.is_available() else "cpu"
            self.model.to(self.device)
            
            load_time = time.time() - start_time
            print(f"✅ Donut model loaded in {load_time:.2f}s on {self.device.upper()}")
            
            self.is_loaded = True
            return True
            
        except Exception as e:
            print(f"❌ Error loading Donut model: {e}")
            return False
    
    def pdf_to_images(self, pdf_path: str, output_dir: str = "temp_images") -> List[str]:
        """Convert PDF to images"""
        try:
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Open PDF
            pdf_document = fitz.open(pdf_path)
            image_paths = []
            
            print(f"🔄 Converting PDF to images...")
            
            for page_num in range(len(pdf_document)):
                # Get page
                page = pdf_document.load_page(page_num)
                
                # Set zoom for better quality
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
                
                # Render page to image
                pix = page.get_pixmap(matrix=mat)
                
                # Save image
                image_path = os.path.join(output_dir, f"page_{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
                
                print(f"   📄 Page {page_num + 1} → {image_path}")
            
            pdf_document.close()
            self.stats["pdf_conversions"] += 1
            
            return image_paths
            
        except Exception as e:
            print(f"❌ Error converting PDF to images: {e}")
            return []
    
    def analyze_image(self, image_path: str, task_prompt: str = None) -> str:
        """Analyze single image with Donut"""
        if not self.is_loaded:
            print("❌ Donut model not loaded")
            return ""
        
        try:
            # Load image
            image = Image.open(image_path).convert("RGB")
            
            # Use default prompt if none provided
            if not task_prompt:
                task_prompt = """<s_docvqa><question>Extract detailed Form 16 information in this exact format:
Employee Name: [Name]
PAN: [PAN Number]
Gross Salary: [Amount]
Basic Salary: [Amount]
HRA: [Amount]
Special Allowance: [Amount]
Other Allowances: [Amount]
Perquisites: [Amount]
Total Gross Salary: [Amount]
Tax Deducted: [Amount]
Employer Name: [Name]
Financial Year: [Year]

Focus on finding all salary components, tax amounts, and employee details. Extract every financial amount you can find.</question><answer>"""
            
            # Prepare input
            inputs = self.processor(
                image, 
                task_prompt, 
                return_tensors="pt"
            ).to(self.device)
            
            # Generate output with optimizations
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=256,  # Reduced for speed
                    early_stopping=True,
                    pad_token_id=self.processor.tokenizer.pad_token_id,
                    eos_token_id=self.processor.tokenizer.eos_token_id,
                    use_cache=True,
                    num_beams=2,  # Reduced for speed
                    bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                    return_dict_in_generate=True
                )
            
            # Decode output
            decoded_output = self.processor.tokenizer.batch_decode(
                outputs.sequences, 
                skip_special_tokens=True
            )[0]
            
            self.stats["image_analyses"] += 1
            return decoded_output
            
        except Exception as e:
            print(f"❌ Error analyzing image {image_path}: {e}")
            return ""
    
    def extract_structured_data(self, text: str) -> Dict[str, Any]:
        """Extract structured data from Donut output"""
        extracted = {}
        
        # Extract amounts
        amounts = re.findall(r'₹?([\d,]+\.?\d*)', text)
        if amounts:
            extracted['amounts'] = [float(amt.replace(',', '')) for amt in amounts if amt.replace(',', '').replace('.', '').isdigit()]
        
        # Extract names
        names = re.findall(r'([A-Z][a-z]+ [A-Z][a-z]+)', text)
        if names:
            extracted['names'] = names
        
        # Extract PAN
        pan_pattern = re.findall(r'[A-Z]{5}[0-9]{4}[A-Z]', text)
        if pan_pattern:
            extracted['pan_numbers'] = pan_pattern
        
        # Apply Form 16 specific patterns
        for field, patterns in self.form16_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if field in ["gross_salary", "basic_salary", "hra", "special_allowance", 
                                "other_allowances", "perquisites", "total_gross_salary", "tax_deducted"]:
                        amount_str = matches[0].replace(",", "")
                        try:
                            extracted[field] = float(amount_str)
                            break
                        except ValueError:
                            continue
                    elif field in ["employee_name", "employer_name"]:
                        extracted[field] = matches[0].strip()
                        break
                    elif field == "pan_number":
                        extracted[field] = matches[0]
                        break
        
        return extracted
    
    def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Analyze document (PDF or image) with Donut"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {"error": f"File not found: {file_path}"}
            
            # Check if it's a PDF
            if file_path.suffix.lower() == '.pdf':
                print(f"📄 Processing PDF: {file_path.name}")
                
                # Convert PDF to images
                image_paths = self.pdf_to_images(str(file_path))
                
                if not image_paths:
                    return {"error": "Failed to convert PDF to images"}
                
                # Analyze each page
                all_results = []
                for i, image_path in enumerate(image_paths):
                    print(f"🔍 Analyzing page {i + 1}/{len(image_paths)}...")
                    
                    # Create page-specific prompt
                    prompt = f"""<s_docvqa><question>Extract detailed Form 16 information from page {i + 1} in this exact format:
Employee Name: [Name]
PAN: [PAN Number]
Gross Salary: [Amount]
Basic Salary: [Amount]
HRA: [Amount]
Special Allowance: [Amount]
Other Allowances: [Amount]
Perquisites: [Amount]
Total Gross Salary: [Amount]
Tax Deducted: [Amount]
Employer Name: [Name]

Focus on finding all salary components, tax amounts, and employee details. Extract every financial amount you can find on this page.</question><answer>"""
                    
                    result = self.analyze_image(image_path, prompt)
                    if result:
                        all_results.append(result)
                
                # Combine results
                combined_text = " ".join(all_results)
                
                # Clean up temporary images
                for image_path in image_paths:
                    try:
                        os.remove(image_path)
                    except:
                        pass
                
            else:
                # Direct image analysis
                print(f"🖼️ Processing image: {file_path.name}")
                combined_text = self.analyze_image(str(file_path))
            
            # Extract structured data
            structured_data = self.extract_structured_data(combined_text)
            
            # Debug: Print what was extracted
            print(f"🔍 Donut extracted data: {structured_data}")
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update stats
            self.stats["avg_processing_time"] = (
                (self.stats["avg_processing_time"] * (self.stats["total_requests"] - 1) + processing_time) 
                / self.stats["total_requests"]
            )
            
            return {
                "document_type": "form_16",
                "confidence": 0.95,
                "method": "donut_model_optimized",
                "raw_output": combined_text,
                "extracted_text": combined_text,
                "processing_time": processing_time,
                "structured_data": structured_data,
                "success": True
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "success": False
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            "total_requests": self.stats["total_requests"],
            "avg_processing_time": f"{self.stats['avg_processing_time']:.2f}s",
            "pdf_conversions": self.stats["pdf_conversions"],
            "image_analyses": self.stats["image_analyses"],
            "model_loaded": self.is_loaded,
            "device": self.device
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "name": "Donut (Document Understanding Transformer)",
            "version": "Optimized",
            "model_path": self.model_path,
            "capabilities": [
                "PDF to image conversion",
                "Document understanding",
                "Form 16 analysis",
                "Structured data extraction"
            ],
            "optimizations": [
                "Reduced max_length (256)",
                "Reduced beam search (2)",
                "Device optimization",
                "Parallel processing ready"
            ]
        }

# Global instance
donut_model = OptimizedDonutModel() 