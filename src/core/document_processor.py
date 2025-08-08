"""
Document Processor for Income Tax AI Assistant
=============================================

Handles document processing, text extraction, and file type detection.
"""

import os
import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
import logging

class DocumentProcessor:
    """Document processor for handling various file types"""
    
    def __init__(self):
        """Initialize document processor"""
        self.supported_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
        self.logger = logging.getLogger(__name__)
        
        print("📄 Document Processor initialized")
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            doc = fitz.open(file_path)
            text = ""
            
            for page in doc:
                text += page.get_text()
            
            doc.close()
            return text.strip()
            
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return ""
    
    def extract_text_from_excel(self, file_path: str) -> str:
        """Extract text from Excel file"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            text_parts = []
            
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # Convert DataFrame to text
                text_parts.append(f"Sheet: {sheet_name}")
                text_parts.append(df.to_string(index=False))
                text_parts.append("\n" + "="*50 + "\n")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            self.logger.error(f"Error extracting text from Excel {file_path}: {e}")
            return ""
    
    def extract_text_from_csv(self, file_path: str) -> str:
        """Extract text from CSV file"""
        try:
            df = pd.read_csv(file_path)
            return df.to_string(index=False)
            
        except Exception as e:
            self.logger.error(f"Error extracting text from CSV {file_path}: {e}")
            return ""
    
    def extract_text_content(self, file_path: str) -> str:
        """Extract text content from any supported file type"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return ""
        
        file_extension = file_path.suffix.lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(str(file_path))
        elif file_extension in ['.xlsx', '.xls']:
            return self.extract_text_from_excel(str(file_path))
        elif file_extension == '.csv':
            return self.extract_text_from_csv(str(file_path))
        else:
            self.logger.error(f"Unsupported file type: {file_extension}")
            return ""
    
    def get_document_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about a document"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"error": "File not found"}
        
        info = {
            "filename": file_path.name,
            "file_extension": file_path.suffix.lower(),
            "file_size": file_path.stat().st_size,
            "is_supported": file_path.suffix.lower() in self.supported_extensions
        }
        
        # Get additional info based on file type
        if info["is_supported"]:
            try:
                text_content = self.extract_text_content(str(file_path))
                info["text_length"] = len(text_content)
                info["has_content"] = len(text_content.strip()) > 0
                
                # Estimate document type based on content
                info["estimated_type"] = self._estimate_document_type(text_content, file_path.name)
                
            except Exception as e:
                info["error"] = str(e)
        
        return info
    
    def _estimate_document_type(self, text_content: str, filename: str) -> str:
        """Estimate document type based on content and filename"""
        text_lower = text_content.lower()
        filename_lower = filename.lower()
        
        # Form16 detection
        if "form 16" in filename_lower or "form16" in filename_lower or "form-16" in filename_lower:
            return "form_16"
        if "form 16" in text_lower or "form16" in text_lower:
            return "form_16"
        
        # Bank interest certificate detection
        if "interest" in filename_lower and ("bank" in filename_lower or "certificate" in filename_lower):
            return "bank_interest_certificate"
        if "interest certificate" in text_lower or "bank interest" in text_lower:
            return "bank_interest_certificate"
        
        # Capital gains detection
        if "capital gains" in filename_lower or "capital_gains" in filename_lower:
            return "capital_gains"
        if "capital gains" in text_lower or "ltcg" in text_lower or "stcg" in text_lower:
            return "capital_gains"
        
        # Investment detection
        if any(word in filename_lower for word in ["mutual", "fund", "investment", "elss", "ppf", "epf"]):
            return "investment"
        if any(word in text_lower for word in ["mutual fund", "investment", "elss", "ppf", "epf", "lic"]):
            return "investment"
        
        # Default to unknown
        return "unknown"
    
    def validate_document(self, file_path: str) -> Dict[str, Any]:
        """Validate if a document can be processed"""
        validation_result = {
            "is_valid": False,
            "errors": [],
            "warnings": []
        }
        
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            validation_result["errors"].append("File does not exist")
            return validation_result
        
        # Check file extension
        if file_path.suffix.lower() not in self.supported_extensions:
            validation_result["errors"].append(f"Unsupported file type: {file_path.suffix}")
            return validation_result
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            validation_result["errors"].append("File is empty")
            return validation_result
        
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            validation_result["warnings"].append("File is very large (>50MB)")
        
        # Try to extract text
        try:
            text_content = self.extract_text_content(str(file_path))
            if len(text_content.strip()) == 0:
                validation_result["errors"].append("No text content could be extracted")
                return validation_result
            
            validation_result["is_valid"] = True
            validation_result["text_length"] = len(text_content)
            validation_result["estimated_type"] = self._estimate_document_type(text_content, file_path.name)
            
        except Exception as e:
            validation_result["errors"].append(f"Error processing file: {str(e)}")
        
        return validation_result
    
    def process_documents_batch(self, folder_path: str) -> Dict[str, Any]:
        """Process all documents in a folder"""
        folder = Path(folder_path)
        
        if not folder.exists():
            return {"error": "Folder not found"}
        
        results = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "documents": []
        }
        
        # Get all supported files
        for ext in self.supported_extensions:
            for file_path in folder.glob(f"*{ext}"):
                results["total_files"] += 1
                
                # Validate document
                validation = self.validate_document(str(file_path))
                
                if validation["is_valid"]:
                    results["processed_files"] += 1
                    results["documents"].append({
                        "file_path": str(file_path),
                        "filename": file_path.name,
                        "estimated_type": validation.get("estimated_type", "unknown"),
                        "text_length": validation.get("text_length", 0),
                        "validation": validation
                    })
                else:
                    results["failed_files"] += 1
                    results["documents"].append({
                        "file_path": str(file_path),
                        "filename": file_path.name,
                        "error": validation["errors"]
                    })
        
        return results
    
    def print_processing_summary(self, results: Dict[str, Any]):
        """Print a summary of document processing results"""
        print("📄 DOCUMENT PROCESSING SUMMARY")
        print("=" * 50)
        print(f"📁 Total Files: {results['total_files']}")
        print(f"✅ Processed: {results['processed_files']}")
        print(f"❌ Failed: {results['failed_files']}")
        print()
        
        if results["documents"]:
            print("📋 DOCUMENT DETAILS:")
            for i, doc in enumerate(results["documents"], 1):
                print(f"{i}. {doc['filename']}")
                
                if "error" in doc:
                    print(f"   ❌ Error: {doc['error']}")
                else:
                    print(f"   📄 Type: {doc['estimated_type']}")
                    print(f"   📏 Text Length: {doc['text_length']:,} characters")
                
                print() 