#!/usr/bin/env python3
"""
Optimized Ollama Document Analyzer
Enhanced version with caching, parallel processing, and performance optimizations
"""

import os
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
import concurrent.futures
import re
from dataclasses import dataclass
import pickle

from src.core.ollama_document_analyzer import OllamaDocumentAnalyzer, OllamaExtractedData

@dataclass
class OptimizedExtractedData:
    """Optimized extracted data structure"""
    document_type: str
    confidence: float
    method: str
    gross_salary: float = 0.0
    tax_deducted: float = 0.0
    employee_name: str = ""
    pan_number: str = ""
    basic_salary: float = 0.0
    hra: float = 0.0
    perquisites: float = 0.0
    quarterly_data: Dict[str, Any] = None
    extracted_text: str = ""
    processing_time: float = 0.0
    cache_hit: bool = False
    
    # Bank details (for bank interest certificates)
    bank_name: str = ""
    account_number: str = ""
    interest_amount: float = 0.0
    tds_amount: float = 0.0
    
    # Capital gains
    total_capital_gains: float = 0.0
    long_term_capital_gains: float = 0.0
    short_term_capital_gains: float = 0.0
    
    # Investment details
    epf_amount: float = 0.0
    ppf_amount: float = 0.0
    elss_amount: float = 0.0
    
    # Form 16 additional fields
    espp_amount: float = 0.0
    
    # Additional fields for compatibility
    pan: str = ""
    extraction_method: str = "optimized_ollama"
    total_gross_salary: float = 0.0
    hra_received: float = 0.0
    special_allowance: float = 0.0
    other_allowances: float = 0.0
    financial_year: str = ""
    number_of_transactions: int = 0
    life_insurance: float = 0.0
    health_insurance: float = 0.0
    raw_text: str = ""
    errors: List[str] = None
    employer_name: str = ""
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        # Set pan from pan_number for compatibility
        if not self.pan and self.pan_number:
            self.pan = self.pan_number

class OptimizedOllamaAnalyzer:
    """
    Optimized version of Ollama Document Analyzer with:
    - Result caching
    - Parallel processing
    - Improved regex patterns
    - Performance monitoring
    """
    
    def __init__(self, cache_dir: str = "cache"):
        self.base_analyzer = OllamaDocumentAnalyzer()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Performance tracking
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_processing_time": 0.0
        }
        
        # Optimized regex patterns for Form 16
        self.optimized_patterns = {
            "gross_salary": [
                r"Gross Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Gross[:\s]*₹?([\d,]+\.?\d*)",
                r"Gross Total[:\s]*₹?([\d,]+\.?\d*)",
                r"Gross[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "tax_deducted": [
                r"Tax Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Tax[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Deducted at Source[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "basic_salary": [
                r"Basic Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic Pay[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "hra": [
                r"HRA[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Received[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent Allowance Received[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Component[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Value[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Total[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "perquisites": [
                r"Perquisites[:\s]*₹?([\d,]+\.?\d*)",
                r"Perks[:\s]*₹?([\d,]+\.?\d*)",
                r"Perquisites Value[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "espp_amount": [
                r"ESPP[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase Plan[:\s]*₹?([\d,]+\.?\d*)",
                r"Stock Purchase Plan[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Value[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Total[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase[:\s]*₹?([\d,]+\.?\d*)",
                r"Stock Purchase[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Component[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Deduction[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase Plan Amount[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "special_allowance": [
                r"Special Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"Special[:\s]*₹?([\d,]+\.?\d*)",
                r"Special Pay[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "other_allowances": [
                r"Other Allowances[:\s]*₹?([\d,]+\.?\d*)",
                r"Other[:\s]*₹?([\d,]+\.?\d*)",
                r"Additional Allowances[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "employee_name": [
                r"Employee Name[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"Name of Employee[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)",
                r"Name[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)"
            ],
            "pan_number": [
                r"[A-Z]{5}[0-9]{4}[A-Z]",
                r"PAN[:\s]*([A-Z]{5}[0-9]{4}[A-Z])"
            ],
            # Bank interest certificate patterns
            "bank_name": [
                r"Bank Name[:\s]*([A-Z][A-Z\s&]+?)(?:\s|$)",
                r"Bank[:\s]*([A-Z][A-Z\s&]+?)(?:\s|$)",
                r"([A-Z][A-Z\s&]+?)\s*Bank",
                r"([A-Z][A-Z\s&]+?)\s*Limited",
                r"([A-Z][A-Z\s&]+?)\s*Ltd",
                r"([A-Z][A-Z\s&]+?)\s*Co-operative",
                r"([A-Z][A-Z\s&]+?)\s*Co-op"
            ],
            "account_number": [
                r"Account Number[:\s]*([0-9]+)",
                r"Account No[:\s]*([0-9]+)",
                r"A/C No[:\s]*([0-9]+)",
                r"Account[:\s]*([0-9]+)",
                r"Acc[:\s]*([0-9]+)"
            ],
            "interest_amount": [
                r"Interest Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Interest[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Earned[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Paid[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Credited[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Income[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "tds_amount": [
                r"TDS Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Deducted at Source[:\s]*₹?([\d,]+\.?\d*)"
            ]
        }
    
    def _get_cache_key(self, file_path: str) -> str:
        """Generate cache key based on file path and modification time"""
        stat = os.stat(file_path)
        file_hash = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(file_hash.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path"""
        return self.cache_dir / f"{cache_key}.pkl"
    
    def _load_from_cache(self, cache_key: str) -> Optional[OptimizedExtractedData]:
        """Load result from cache"""
        cache_path = self._get_cache_path(cache_key)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    self.stats["cache_hits"] += 1
                    cached_data.cache_hit = True
                    return cached_data
            except Exception as e:
                print(f"⚠️ Cache load error: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, data: OptimizedExtractedData):
        """Save result to cache"""
        try:
            cache_path = self._get_cache_path(cache_key)
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"⚠️ Cache save error: {e}")
    
    def _extract_with_optimized_regex(self, text: str) -> Dict[str, Any]:
        """Extract data using optimized regex patterns"""
        extracted = {}
        
        for field, patterns in self.optimized_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if field in ["gross_salary", "tax_deducted", "basic_salary", "hra", "perquisites", "interest_amount", "tds_amount", "espp_amount", "special_allowance", "other_allowances"]:
                        # Convert amount strings to float
                        amount_str = matches[0].replace(",", "")
                        try:
                            extracted[field] = float(amount_str)
                            break
                        except ValueError:
                            continue
                    elif field in ["employee_name", "bank_name", "account_number"]:
                        extracted[field] = matches[0].strip()
                        break
                    elif field in ["pan_number"]:
                        extracted[field] = matches[0].strip()
                        break
        
        return extracted
    
    def _extract_bank_interest_data(self, text: str) -> Dict[str, Any]:
        """Extract bank interest certificate data with enhanced patterns"""
        bank_data = {}
        
        # Enhanced bank interest patterns
        bank_interest_patterns = {
            "bank_name": [
                r"Bank Name[:\s]*([A-Z][A-Z\s&]+?)(?:\s|$)",
                r"Bank[:\s]*([A-Z][A-Z\s&]+?)(?:\s|$)",
                r"([A-Z][A-Z\s&]+?)\s*Bank",
                r"([A-Z][A-Z\s&]+?)\s*Limited",
                r"([A-Z][A-Z\s&]+?)\s*Ltd",
                r"([A-Z][A-Z\s&]+?)\s*Co-operative",
                r"([A-Z][A-Z\s&]+?)\s*Co-op"
            ],
            "account_number": [
                r"Account Number[:\s]*([0-9]+)",
                r"Account No[:\s]*([0-9]+)",
                r"A/C No[:\s]*([0-9]+)",
                r"Account[:\s]*([0-9]+)",
                r"Acc[:\s]*([0-9]+)"
            ],
            "interest_amount": [
                r"Interest Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Interest[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Earned[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Paid[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Credited[:\s]*₹?([\d,]+\.?\d*)",
                r"Interest Income[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "tds_amount": [
                r"TDS Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"TDS Deducted[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Deducted at Source[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "pan": [
                r"PAN[:\s]*([A-Z]{5}[0-9]{4}[A-Z])",
                r"Permanent Account Number[:\s]*([A-Z]{5}[0-9]{4}[A-Z])",
                r"[A-Z]{5}[0-9]{4}[A-Z]"
            ]
        }
        
        for field, patterns in bank_interest_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if field in ["interest_amount", "tds_amount"]:
                        # Convert amount strings to float
                        amount_str = matches[0].replace(",", "")
                        try:
                            bank_data[field] = float(amount_str)
                            break
                        except ValueError:
                            continue
                    elif field in ["bank_name", "account_number", "pan"]:
                        bank_data[field] = matches[0].strip()
                        break
        
        return bank_data
    
    def _extract_investment_data(self, text: str) -> Dict[str, Any]:
        """Extract investment document data with enhanced patterns"""
        investment_data = {}
        
        # Enhanced investment patterns
        investment_patterns = {
            "epf_amount": [
                r"EPF[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Provident Fund[:\s]*₹?([\d,]+\.?\d*)",
                r"Provident Fund[:\s]*₹?([\d,]+\.?\d*)",
                r"PF[:\s]*₹?([\d,]+\.?\d*)",
                r"EPF Contribution[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee PF[:\s]*₹?([\d,]+\.?\d*)",
                r"Total EPF[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "ppf_amount": [
                r"PPF[:\s]*₹?([\d,]+\.?\d*)",
                r"Public Provident Fund[:\s]*₹?([\d,]+\.?\d*)",
                r"PPF Contribution[:\s]*₹?([\d,]+\.?\d*)",
                r"Total PPF[:\s]*₹?([\d,]+\.?\d*)",
                r"PPF Balance[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "elss_amount": [
                r"ELSS[:\s]*₹?([\d,]+\.?\d*)",
                r"Equity Linked Savings Scheme[:\s]*₹?([\d,]+\.?\d*)",
                r"ELSS Investment[:\s]*₹?([\d,]+\.?\d*)",
                r"Total ELSS[:\s]*₹?([\d,]+\.?\d*)",
                r"ELSS Fund[:\s]*₹?([\d,]+\.?\d*)",
                r"Mutual Fund ELSS[:\s]*₹?([\d,]+\.?\d*)",
                r"Tax Saving Fund[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "life_insurance": [
                r"Life Insurance[:\s]*₹?([\d,]+\.?\d*)",
                r"LIC[:\s]*₹?([\d,]+\.?\d*)",
                r"Life Insurance Premium[:\s]*₹?([\d,]+\.?\d*)",
                r"Insurance Premium[:\s]*₹?([\d,]+\.?\d*)",
                r"Life Cover[:\s]*₹?([\d,]+\.?\d*)",
                r"Term Insurance[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "health_insurance": [
                r"Health Insurance[:\s]*₹?([\d,]+\.?\d*)",
                r"Medical Insurance[:\s]*₹?([\d,]+\.?\d*)",
                r"Health Premium[:\s]*₹?([\d,]+\.?\d*)",
                r"Medical Premium[:\s]*₹?([\d,]+\.?\d*)",
                r"Health Cover[:\s]*₹?([\d,]+\.?\d*)",
                r"Family Floater[:\s]*₹?([\d,]+\.?\d*)"
            ],
            "mutual_fund_amount": [
                r"Mutual Fund[:\s]*₹?([\d,]+\.?\d*)",
                r"MF[:\s]*₹?([\d,]+\.?\d*)",
                r"Fund Investment[:\s]*₹?([\d,]+\.?\d*)",
                r"Total Investment[:\s]*₹?([\d,]+\.?\d*)",
                r"Investment Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"Fund Value[:\s]*₹?([\d,]+\.?\d*)"
            ]
        }
        
        for field, patterns in investment_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Convert amount strings to float
                    amount_str = matches[0].replace(",", "")
                    try:
                        investment_data[field] = float(amount_str)
                        break
                    except ValueError:
                        continue
        
        return investment_data
    
    def _extract_form16_data(self, text: str) -> Dict[str, Any]:
        """Extract Form 16 specific data with enhanced patterns"""
        form16_data = {}
        
        # Enhanced Form 16 patterns
        form16_patterns = {
            "hra": [
                r"HRA[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Received[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"House Rent Allowance Received[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Component[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Value[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA Total[:\s]*₹?([\d,]+\.?\d*)",
                r"HRA[:\s]*([\d,]+\.?\d*)",
                r"House Rent Allowance[:\s]*([\d,]+\.?\d*)"
            ],
            "espp_amount": [
                r"ESPP[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase Plan[:\s]*₹?([\d,]+\.?\d*)",
                r"Stock Purchase Plan[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Value[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Total[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase[:\s]*₹?([\d,]+\.?\d*)",
                r"Stock Purchase[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Component[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP Deduction[:\s]*₹?([\d,]+\.?\d*)",
                r"Employee Stock Purchase Plan Amount[:\s]*₹?([\d,]+\.?\d*)",
                r"ESPP[:\s]*([\d,]+\.?\d*)",
                r"Employee Stock Purchase Plan[:\s]*([\d,]+\.?\d*)"
            ],
            "basic_salary": [
                r"Basic Salary[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic Pay[:\s]*₹?([\d,]+\.?\d*)",
                r"Basic Salary[:\s]*([\d,]+\.?\d*)",
                r"Basic[:\s]*([\d,]+\.?\d*)"
            ],
            "special_allowance": [
                r"Special Allowance[:\s]*₹?([\d,]+\.?\d*)",
                r"Special[:\s]*₹?([\d,]+\.?\d*)",
                r"Special Pay[:\s]*₹?([\d,]+\.?\d*)",
                r"Special Allowance[:\s]*([\d,]+\.?\d*)",
                r"Special[:\s]*([\d,]+\.?\d*)"
            ],
            "other_allowances": [
                r"Other Allowances[:\s]*₹?([\d,]+\.?\d*)",
                r"Other[:\s]*₹?([\d,]+\.?\d*)",
                r"Additional Allowances[:\s]*₹?([\d,]+\.?\d*)",
                r"Other Allowances[:\s]*([\d,]+\.?\d*)",
                r"Other[:\s]*([\d,]+\.?\d*)"
            ],
            "perquisites": [
                r"Perquisites[:\s]*₹?([\d,]+\.?\d*)",
                r"Perks[:\s]*₹?([\d,]+\.?\d*)",
                r"Perquisites Value[:\s]*₹?([\d,]+\.?\d*)",
                r"Perquisites[:\s]*([\d,]+\.?\d*)",
                r"Perks[:\s]*([\d,]+\.?\d*)"
            ]
        }
        
        for field, patterns in form16_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # Convert amount strings to float
                    amount_str = matches[0].replace(",", "")
                    try:
                        form16_data[field] = float(amount_str)
                        print(f"📋 Form 16 extracted {field}: {form16_data[field]}")
                        break
                    except ValueError:
                        continue
        
        return form16_data
    
    def _process_quarterly_data_parallel(self, text: str) -> Dict[str, Any]:
        """Process quarterly data in parallel"""
        quarterly_patterns = [
            r"Q1[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            r"Q2[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            r"Q3[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            r"Q4[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)"
        ]
        
        quarterly_data = {}
        
        def process_quarter(pattern, quarter_name):
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                salary_str = matches[0][0].replace(",", "")
                tax_str = matches[0][1].replace(",", "")
                try:
                    return quarter_name, {
                        "salary": float(salary_str),
                        "tax": float(tax_str)
                    }
                except ValueError:
                    return quarter_name, None
            return quarter_name, None
        
        # Process quarters in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(process_quarter, pattern, f"Q{i+1}")
                for i, pattern in enumerate(quarterly_patterns)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                quarter_name, data = future.result()
                if data:
                    quarterly_data[quarter_name] = data
        
        return quarterly_data
    
    def analyze_document(self, file_path: str) -> OptimizedExtractedData:
        """Analyze document with optimizations"""
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        # Check cache first
        cache_key = self._get_cache_key(file_path)
        cached_result = self._load_from_cache(cache_key)
        
        if cached_result:
            print(f"✅ Cache hit! Loading cached result for {Path(file_path).name}")
            return cached_result
        
        print(f"🔄 Cache miss. Processing {Path(file_path).name}...")
        self.stats["cache_misses"] += 1
        
        # Use base analyzer for initial extraction
        base_result = self.base_analyzer.analyze_document(file_path)
        
        # Convert base result to dict
        if hasattr(base_result, '__dict__'):
            base_data = base_result.__dict__
        elif hasattr(base_result, 'to_dict'):
            base_data = base_result.to_dict()
        else:
            base_data = {"raw_result": str(base_result)}
        
        # Extract text for optimized processing
        extracted_text = base_data.get('extracted_text', '')
        
        # Apply optimized regex extraction
        optimized_data = self._extract_with_optimized_regex(extracted_text)
        
        # Apply enhanced bank interest extraction for bank interest certificates
        if "bank" in base_data.get('document_type', '').lower() and "interest" in base_data.get('document_type', '').lower():
            print("🏦 Processing bank interest certificate with enhanced extraction...")
            bank_data = self._extract_bank_interest_data(extracted_text)
            print(f"🏦 Enhanced bank data extracted: {bank_data}")
            # Merge bank data with optimized data, preferring bank data
            for key, value in bank_data.items():
                if value:  # Only override if we found a value
                    optimized_data[key] = value
                    print(f"🏦 Updated {key}: {value}")
        
        # Apply enhanced Form 16 extraction for Form 16 documents
        if "form16" in base_data.get('document_type', '').lower() or "form 16" in base_data.get('document_type', '').lower() or "form_16" in base_data.get('document_type', '').lower() or "salary" in base_data.get('document_type', '').lower():
            print("📋 Processing Form 16 document with enhanced extraction...")
            form16_data = self._extract_form16_data(extracted_text)
            print(f"📋 Enhanced Form 16 data extracted: {form16_data}")
            # Merge Form 16 data with optimized data, preferring Form 16 data
            for key, value in form16_data.items():
                if value:  # Only override if we found a value
                    optimized_data[key] = value
                    print(f"📋 Updated {key}: {value}")
        
        # Apply enhanced investment extraction for investment documents
        if "investment" in base_data.get('document_type', '').lower() or "mutual" in base_data.get('document_type', '').lower() or "elss" in base_data.get('document_type', '').lower():
            print("💰 Processing investment document with enhanced extraction...")
            investment_data = self._extract_investment_data(extracted_text)
            print(f"💰 Enhanced investment data extracted: {investment_data}")
            # Merge investment data with optimized data, preferring investment data
            for key, value in investment_data.items():
                if value:  # Only override if we found a value
                    optimized_data[key] = value
                    print(f"💰 Updated {key}: {value}")
        
        # Process quarterly data in parallel
        quarterly_data = self._process_quarterly_data_parallel(extracted_text)
        
        # Create optimized result
        optimized_result = OptimizedExtractedData(
            document_type=base_data.get('document_type', 'unknown'),
            confidence=base_data.get('confidence', 0.85),
            method="optimized_ollama_llm",
            gross_salary=optimized_data.get('gross_salary', base_data.get('gross_salary', 0.0)),
            tax_deducted=optimized_data.get('tax_deducted', base_data.get('tax_deducted', 0.0)),
            employee_name=optimized_data.get('employee_name', base_data.get('employee_name', '')),
            pan_number=optimized_data.get('pan_number', ''),
            basic_salary=optimized_data.get('basic_salary', 0.0),
            hra=optimized_data.get('hra', 0.0),
            perquisites=optimized_data.get('perquisites', 0.0),
            quarterly_data=quarterly_data,
            extracted_text=extracted_text,
            processing_time=time.time() - start_time,
            cache_hit=False,
            # Form 16 additional fields
            espp_amount=optimized_data.get('espp_amount', base_data.get('espp_amount', 0.0)),
            special_allowance=optimized_data.get('special_allowance', base_data.get('special_allowance', 0.0)),
            other_allowances=optimized_data.get('other_allowances', base_data.get('other_allowances', 0.0)),
            hra_received=optimized_data.get('hra', base_data.get('hra_received', 0.0)),  # Map HRA to hra_received for compatibility
            # Bank interest certificate fields
            bank_name=optimized_data.get('bank_name', base_data.get('bank_name', '')),
            account_number=optimized_data.get('account_number', base_data.get('account_number', '')),
            interest_amount=optimized_data.get('interest_amount', base_data.get('interest_amount', 0.0)),
            tds_amount=optimized_data.get('tds_amount', base_data.get('tds_amount', 0.0)),
            # Investment fields
            epf_amount=optimized_data.get('epf_amount', base_data.get('epf_amount', 0.0)),
            ppf_amount=optimized_data.get('ppf_amount', base_data.get('ppf_amount', 0.0)),
            elss_amount=optimized_data.get('elss_amount', base_data.get('elss_amount', 0.0)),
            life_insurance=optimized_data.get('life_insurance', base_data.get('life_insurance', 0.0)),
            health_insurance=optimized_data.get('health_insurance', base_data.get('health_insurance', 0.0)),
            # Additional compatibility fields
            pan=optimized_data.get('pan_number', base_data.get('pan', '')),
            raw_text=extracted_text,
            errors=base_data.get('errors', [])
        )
        
        # Save to cache
        self._save_to_cache(cache_key, optimized_result)
        
        # Update stats
        self.stats["avg_processing_time"] = (
            (self.stats["avg_processing_time"] * (self.stats["total_requests"] - 1) + optimized_result.processing_time) 
            / self.stats["total_requests"]
        )
        
        return optimized_result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        cache_hit_rate = (
            self.stats["cache_hits"] / self.stats["total_requests"] * 100 
            if self.stats["total_requests"] > 0 else 0
        )
        
        return {
            "total_requests": self.stats["total_requests"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": f"{cache_hit_rate:.1f}%",
            "avg_processing_time": f"{self.stats['avg_processing_time']:.2f}s",
            "cache_dir": str(self.cache_dir)
        }
    
    def clear_cache(self):
        """Clear all cached results"""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
        print(f"🗑️ Cleared {len(list(self.cache_dir.glob('*.pkl')))} cached results")
    
    def analyze_multiple_documents(self, file_paths: List[str]) -> List[OptimizedExtractedData]:
        """Analyze multiple documents in parallel"""
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_path = {
                executor.submit(self.analyze_document, path): path 
                for path in file_paths
            }
            
            for future in concurrent.futures.as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"✅ Completed: {Path(path).name}")
                except Exception as e:
                    print(f"❌ Error processing {Path(path).name}: {e}")
        
        return results 