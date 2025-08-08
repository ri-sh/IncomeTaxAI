"""
Document Processor for Indian Tax Documents
Extracts structured data from various tax document types
"""

import os
import re
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import json

# PDF processing
import PyPDF2
import pdfplumber

# Excel processing
import openpyxl
from openpyxl import load_workbook

# OCR for images
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

@dataclass
class ExtractedData:
    """Holds extracted data from a document"""
    document_type: str
    file_path: str
    extracted_fields: Dict[str, Any]
    confidence_score: float
    extraction_method: str
    errors: List[str]
    raw_text: Optional[str] = None

class Form16Processor:
    """Processes Form 16 documents"""
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> ExtractedData:
        """Extract data from Form 16 PDF"""
        extracted_fields = {}
        errors = []
        raw_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                # Extract text from all pages
                for page in pdf.pages:
                    raw_text += page.extract_text() or ""
                
                # Extract key fields using regex patterns
                patterns = {
                    'pan': r'PAN\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])',
                    'employee_name': r'(?:Name|Employee Name)\s*[:\-]?\s*([A-Z\s]+)',
                    'employer_name': r'(?:Name and address of the Employer|Employer)\s*[:\-]?\s*([A-Z\s&\.]+)',
                    'financial_year': r'(?:Financial Year|F\.Y\.?)\s*[:\-]?\s*(\d{4}-\d{2,4})',
                    'gross_salary': r'(?:Gross salary|Total)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'tax_deducted': r'(?:Tax deducted at source|TDS|Income tax deducted)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'taxable_income': r'(?:Total taxable income|Taxable income)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'hra_exemption': r'(?:HRA exemption|House rent allowance)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'standard_deduction': r'(?:Standard deduction|Entertainment allowance)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        # Clean numeric values
                        if field in ['gross_salary', 'tax_deducted', 'taxable_income', 'hra_exemption', 'standard_deduction']:
                            value = re.sub(r'[^\d.]', '', value)
                            try:
                                extracted_fields[field] = float(value) if value else 0.0
                            except:
                                extracted_fields[field] = 0.0
                        else:
                            extracted_fields[field] = value
                
                # Calculate confidence based on mandatory fields found (0.0-1.0 scale)
                mandatory_fields = ['pan', 'employee_name', 'gross_salary', 'tax_deducted']
                found_mandatory = sum(1 for field in mandatory_fields if field in extracted_fields)
                confidence = found_mandatory / len(mandatory_fields)  # 0.0 to 1.0
                
        except Exception as e:
            errors.append(f"Error processing Form 16: {str(e)}")
            confidence = 0.0
        
        return ExtractedData(
            document_type="Form 16",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence,
            extraction_method="PDF parsing",
            errors=errors,
            raw_text=raw_text
        )

class BankStatementProcessor:
    """Processes bank statements"""
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> ExtractedData:
        """Extract data from bank statement PDF"""
        extracted_fields = {}
        errors = []
        raw_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    raw_text += page.extract_text() or ""
                
                # Extract bank details
                patterns = {
                    'account_number': r'(?:Account No|A/c No|Account Number)\s*[:\-]?\s*(\d+)',
                    'account_holder': r'(?:Account Holder|Name)\s*[:\-]?\s*([A-Z\s]+)',
                    'bank_name': r'(HDFC|ICICI|SBI|AXIS|PNB|BOB|CANARA|UNION|INDIAN|BANK OF [A-Z]+)',
                    'statement_period': r'(?:Statement Period|From|Date)\s*[:\-]?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
                    'opening_balance': r'(?:Opening Balance|Opening Bal)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'closing_balance': r'(?:Closing Balance|Closing Bal)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field in ['opening_balance', 'closing_balance']:
                            value = re.sub(r'[^\d.]', '', value)
                            try:
                                extracted_fields[field] = float(value) if value else 0.0
                            except:
                                extracted_fields[field] = 0.0
                        else:
                            extracted_fields[field] = value
                
                # Extract interest earned (common pattern)
                interest_patterns = [
                    r'(?:Interest Paid|Int\.? Pd|Interest Earned|Int\.? Earned)\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    r'(?:Cr Interest|Credit Interest|Savings Interest)\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)'
                ]
                
                total_interest = 0.0
                for pattern in interest_patterns:
                    matches = re.findall(pattern, raw_text, re.IGNORECASE)
                    for match in matches:
                        try:
                            amount = float(re.sub(r'[^\d.]', '', match))
                            total_interest += amount
                        except:
                            continue
                
                if total_interest > 0:
                    extracted_fields['interest_earned'] = total_interest
                
                # Calculate confidence (0.0-1.0 scale)
                mandatory_fields = ['account_number', 'account_holder']
                found_mandatory = sum(1 for field in mandatory_fields if field in extracted_fields)
                confidence = found_mandatory / len(mandatory_fields)  # 0.0 to 1.0
                
        except Exception as e:
            errors.append(f"Error processing bank statement: {str(e)}")
            confidence = 0.0
        
        return ExtractedData(
            document_type="Bank Statement",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence,
            extraction_method="PDF parsing",
            errors=errors,
            raw_text=raw_text
        )
    
    @staticmethod
    def extract_from_excel(file_path: str) -> ExtractedData:
        """Extract data from bank statement Excel file"""
        extracted_fields = {}
        errors = []
        
        try:
            # Try different sheet reading methods
            df = None
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                df = pd.read_excel(file_path)
            
            if df is not None and not df.empty:
                # Look for common column patterns
                columns = [col.lower() for col in df.columns]
                
                # Find transaction amount columns
                amount_cols = [col for col in df.columns if any(term in col.lower() 
                              for term in ['amount', 'debit', 'credit', 'balance'])]
                
                if amount_cols:
                    # Calculate total credits (deposits)
                    for col in amount_cols:
                        if 'credit' in col.lower() or 'deposit' in col.lower():
                            try:
                                total_credits = df[col].sum()
                                extracted_fields['total_credits'] = float(total_credits)
                            except:
                                pass
                
                # Extract interest transactions
                if 'description' in columns or 'particulars' in columns:
                    desc_col = 'description' if 'description' in columns else 'particulars'
                    interest_rows = df[df[desc_col].str.contains('interest|int', case=False, na=False)]
                    
                    if not interest_rows.empty and amount_cols:
                        try:
                            interest_amount = interest_rows[amount_cols[0]].sum()
                            extracted_fields['interest_earned'] = float(interest_amount)
                        except:
                            pass
                
                extracted_fields['total_transactions'] = len(df)
                confidence = 0.8  # High confidence for Excel files (0.0-1.0 scale)
            else:
                confidence = 0.0
                errors.append("Could not read Excel file or file is empty")
                
        except Exception as e:
            errors.append(f"Error processing Excel bank statement: {str(e)}")
            confidence = 0.0
        
        return ExtractedData(
            document_type="Bank Statement",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence,
            extraction_method="Excel parsing",
            errors=errors
        )

class MutualFundsCapitalGainsProcessor:
    """Processes Mutual Funds Capital Gains Reports from Excel files"""
    
    @staticmethod
    def extract_from_excel(file_path: str) -> ExtractedData:
        """Extract data from Mutual Funds Capital Gains Excel report"""
        extracted_fields = {}
        errors = []
        confidence_score = 0.0
        
        try:
            # Use pandas to read Excel file
            import pandas as pd
            
            # Try reading different possible sheet names
            sheet_names = ['Sheet1', 'Capital Gains', 'Report', 'Mutual Funds']
            df = None
            
            for sheet in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    break
                except:
                    continue
            
            if df is None:
                df = pd.read_excel(file_path)  # Try default sheet
            
            # Extract key information
            total_rows = len(df)
            
            # Look for common column patterns in mutual funds reports
            potential_columns = {
                'scheme_name': ['Scheme', 'Fund Name', 'Scheme Name', 'Mutual Fund'],
                'purchase_date': ['Purchase Date', 'Buy Date', 'Date of Purchase'],
                'sale_date': ['Sale Date', 'Sell Date', 'Date of Sale', 'Redemption Date'],
                'purchase_amount': ['Purchase Amount', 'Buy Amount', 'Investment'],
                'sale_amount': ['Sale Amount', 'Sell Amount', 'Redemption Amount'],
                'gain_loss': ['Gain/Loss', 'P&L', 'Capital Gain', 'Profit/Loss', 'Gain', 'Loss'],
                'units': ['Units', 'Quantity', 'No. of Units']
            }
            
            # Map actual columns to our standard names
            column_mapping = {}
            for standard_name, possible_names in potential_columns.items():
                for col in df.columns:
                    if any(possible.lower() in str(col).lower() for possible in possible_names):
                        column_mapping[standard_name] = col
                        break
            
            # Calculate summary statistics
            if 'gain_loss' in column_mapping:
                gains_col = column_mapping['gain_loss']
                if gains_col in df.columns:
                    # Convert to numeric, handling any string values
                    gains_series = pd.to_numeric(df[gains_col], errors='coerce').fillna(0)
                    total_gains = gains_series.sum()
                    extracted_fields['total_capital_gains'] = float(total_gains)
                    
                    # Count positive and negative gains
                    positive_gains = gains_series[gains_series > 0].sum()
                    negative_gains = abs(gains_series[gains_series < 0].sum())
                    extracted_fields['total_profits'] = float(positive_gains)
                    extracted_fields['total_losses'] = float(negative_gains)
                    
                    # Separate LTCG and STCG (basic heuristic)
                    if 'purchase_date' in column_mapping and 'sale_date' in column_mapping:
                        try:
                            purchase_col = column_mapping['purchase_date']
                            sale_col = column_mapping['sale_date']
                            df['purchase_date_clean'] = pd.to_datetime(df[purchase_col], errors='coerce')
                            df['sale_date_clean'] = pd.to_datetime(df[sale_col], errors='coerce')
                            df['holding_period_days'] = (df['sale_date_clean'] - df['purchase_date_clean']).dt.days
                            df['is_ltcg'] = df['holding_period_days'] > 365
                            
                            ltcg_mask = df['is_ltcg'].fillna(False)
                            stcg_mask = ~ltcg_mask
                            
                            ltcg = gains_series[ltcg_mask].sum()
                            stcg = gains_series[stcg_mask].sum()
                            
                            extracted_fields['long_term_capital_gains'] = float(ltcg)
                            extracted_fields['short_term_capital_gains'] = float(stcg)
                            extracted_fields['ltcg_transactions'] = int(ltcg_mask.sum())
                            extracted_fields['stcg_transactions'] = int(stcg_mask.sum())
                        except Exception as e:
                            errors.append(f"Could not separate LTCG/STCG: {str(e)}")
            
            extracted_fields['total_transactions'] = total_rows
            extracted_fields['financial_year'] = '2024-25'  # Based on filename pattern
            
            # Identify unique schemes
            if 'scheme_name' in column_mapping:
                scheme_col = column_mapping['scheme_name']
                unique_schemes = df[scheme_col].nunique() if scheme_col in df.columns else 0
                extracted_fields['number_of_schemes'] = int(unique_schemes)
                
                # Get top schemes by transaction count
                if unique_schemes > 0:
                    top_schemes = df[scheme_col].value_counts().head(3).index.tolist()
                    extracted_fields['top_schemes'] = top_schemes
            
            # Calculate total investment amount
            if 'purchase_amount' in column_mapping:
                purchase_col = column_mapping['purchase_amount']
                purchase_series = pd.to_numeric(df[purchase_col], errors='coerce').fillna(0)
                total_investment = purchase_series.sum()
                extracted_fields['total_investment_amount'] = float(total_investment)
            
            # Confidence scoring
            confidence_score = 0.1  # Base score for successful Excel reading
            
            # Boost confidence based on found columns
            if column_mapping:
                confidence_score += min(len(column_mapping) * 0.1, 0.4)
            
            # Boost if we found capital gains data
            if 'total_capital_gains' in extracted_fields:
                confidence_score += 0.3
            
            # Boost if filename indicates mutual funds
            filename_lower = Path(file_path).name.lower()
            if any(keyword in filename_lower for keyword in ['mutual', 'fund', 'capital', 'gains']):
                confidence_score += 0.3
            
            # Boost if we have transaction data
            if total_rows > 0:
                confidence_score += 0.2
            
            confidence_score = min(confidence_score, 1.0)
            
        except Exception as e:
            errors.append(f"Error processing mutual funds Excel: {str(e)}")
            confidence_score = 0.1
        
        return ExtractedData(
            document_type="Mutual Funds Capital Gains Report",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence_score,
            extraction_method="Excel data analysis with pandas",
            errors=errors
        )

class StocksCapitalGainsProcessor:
    """Processes Stocks/Equity Capital Gains Reports from Excel files"""
    
    @staticmethod
    def extract_from_excel(file_path: str) -> ExtractedData:
        """Extract data from Stocks Capital Gains Excel report"""
        extracted_fields = {}
        errors = []
        confidence_score = 0.0
        
        try:
            # Use pandas to read Excel file
            import pandas as pd
            
            # Try reading different possible sheet names
            sheet_names = ['Sheet1', 'Capital Gains', 'Report', 'Stocks', 'Equity']
            df = None
            
            for sheet in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    break
                except:
                    continue
            
            if df is None:
                df = pd.read_excel(file_path)  # Try default sheet
            
            # Extract key information
            total_rows = len(df)
            
            # Look for common column patterns in stocks reports
            potential_columns = {
                'stock_name': ['Stock', 'Security', 'Company', 'Stock Name', 'Security Name', 'Scrip'],
                'purchase_date': ['Purchase Date', 'Buy Date', 'Date of Purchase', 'Bought Date'],
                'sale_date': ['Sale Date', 'Sell Date', 'Date of Sale', 'Sold Date'],
                'purchase_price': ['Purchase Price', 'Buy Price', 'Cost Price', 'Purchase Amount'],
                'sale_price': ['Sale Price', 'Sell Price', 'Sale Amount', 'Realized Amount'],
                'quantity': ['Quantity', 'Qty', 'No. of Shares', 'Units'],
                'gain_loss': ['Gain/Loss', 'P&L', 'Capital Gain', 'Profit/Loss', 'Gain', 'Loss', 'Net Gain'],
                'isin': ['ISIN', 'ISIN Code'],
                'exchange': ['Exchange', 'Market']
            }
            
            # Map actual columns to our standard names
            column_mapping = {}
            for standard_name, possible_names in potential_columns.items():
                for col in df.columns:
                    if any(possible.lower() in str(col).lower() for possible in possible_names):
                        column_mapping[standard_name] = col
                        break
            
            # Calculate summary statistics
            if 'gain_loss' in column_mapping:
                gains_col = column_mapping['gain_loss']
                if gains_col in df.columns:
                    # Convert to numeric, handling any string values
                    gains_series = pd.to_numeric(df[gains_col], errors='coerce').fillna(0)
                    total_gains = gains_series.sum()
                    extracted_fields['total_capital_gains'] = float(total_gains)
                    
                    # Count positive and negative gains
                    positive_gains = gains_series[gains_series > 0].sum()
                    negative_gains = abs(gains_series[gains_series < 0].sum())
                    extracted_fields['total_profits'] = float(positive_gains)
                    extracted_fields['total_losses'] = float(negative_gains)
                    
                    # Separate LTCG and STCG for stocks/equity
                    if 'purchase_date' in column_mapping and 'sale_date' in column_mapping:
                        try:
                            purchase_col = column_mapping['purchase_date']
                            sale_col = column_mapping['sale_date']
                            df['purchase_date_clean'] = pd.to_datetime(df[purchase_col], errors='coerce')
                            df['sale_date_clean'] = pd.to_datetime(df[sale_col], errors='coerce')
                            df['holding_period_days'] = (df['sale_date_clean'] - df['purchase_date_clean']).dt.days
                            
                            # For stocks: LTCG > 12 months (365 days)
                            df['is_ltcg'] = df['holding_period_days'] > 365
                            
                            ltcg_mask = df['is_ltcg'].fillna(False)
                            stcg_mask = ~ltcg_mask
                            
                            ltcg = gains_series[ltcg_mask].sum()
                            stcg = gains_series[stcg_mask].sum()
                            
                            extracted_fields['long_term_capital_gains'] = float(ltcg)
                            extracted_fields['short_term_capital_gains'] = float(stcg)
                            extracted_fields['ltcg_transactions'] = int(ltcg_mask.sum())
                            extracted_fields['stcg_transactions'] = int(stcg_mask.sum())
                        except Exception as e:
                            errors.append(f"Could not separate LTCG/STCG: {str(e)}")
            
            extracted_fields['total_transactions'] = total_rows
            extracted_fields['financial_year'] = '2024-25'  # Based on filename pattern
            
            # Identify unique stocks
            if 'stock_name' in column_mapping:
                stock_col = column_mapping['stock_name']
                unique_stocks = df[stock_col].nunique() if stock_col in df.columns else 0
                extracted_fields['number_of_stocks'] = int(unique_stocks)
                
                # Get top stocks by transaction count
                if unique_stocks > 0:
                    top_stocks = df[stock_col].value_counts().head(3).index.tolist()
                    extracted_fields['top_stocks'] = top_stocks
            
            # Calculate total investment value
            if 'purchase_price' in column_mapping and 'quantity' in column_mapping:
                try:
                    purchase_col = column_mapping['purchase_price']
                    qty_col = column_mapping['quantity']
                    df['investment_value'] = pd.to_numeric(df[purchase_col], errors='coerce') * pd.to_numeric(df[qty_col], errors='coerce')
                    total_investment = df['investment_value'].sum()
                    extracted_fields['total_investment_amount'] = float(total_investment)
                except:
                    pass
            
            # Confidence scoring
            confidence_score = 0.1  # Base score for successful Excel reading
            
            # Boost confidence based on found columns
            if column_mapping:
                confidence_score += min(len(column_mapping) * 0.1, 0.4)
            
            # Boost if we found capital gains data
            if 'total_capital_gains' in extracted_fields:
                confidence_score += 0.3
            
            # Boost if filename indicates stocks
            filename_lower = Path(file_path).name.lower()
            if any(keyword in filename_lower for keyword in ['stock', 'equity', 'shares', 'capital', 'gains']):
                confidence_score += 0.3
            
            # Boost if we have transaction data
            if total_rows > 0:
                confidence_score += 0.2
            
            confidence_score = min(confidence_score, 1.0)
            
        except Exception as e:
            errors.append(f"Error processing stocks Excel: {str(e)}")
            confidence_score = 0.1
        
        return ExtractedData(
            document_type="Stocks Capital Gains Report",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence_score,
            extraction_method="Excel data analysis with pandas",
            errors=errors
        )

class InvestmentDocumentProcessor:
    """Processes investment documents (LIC, ELSS, PPF, etc.)"""
    
    @staticmethod
    def extract_lic_premium(file_path: str) -> ExtractedData:
        """Extract LIC premium details"""
        extracted_fields = {}
        errors = []
        raw_text = ""
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    raw_text += page.extract_text() or ""
                
                patterns = {
                    'policy_number': r'(?:Policy No|Policy Number)\s*[:\-]?\s*(\d+)',
                    'premium_amount': r'(?:Premium|Annual Premium|Premium Amount)\s*[:\-]?\s*[\₹Rs\.]*\s*([\d,]+\.?\d*)',
                    'policy_holder': r'(?:Policy Holder|Assured Name)\s*[:\-]?\s*([A-Z\s]+)',
                    'policy_type': r'(?:Plan|Policy Type|Scheme)\s*[:\-]?\s*([A-Z\s]+)',
                    'financial_year': r'(?:Financial Year|F\.Y\.?|Year)\s*[:\-]?\s*(\d{4}-\d{2,4})'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field == 'premium_amount':
                            value = re.sub(r'[^\d.]', '', value)
                            try:
                                extracted_fields[field] = float(value) if value else 0.0
                            except:
                                extracted_fields[field] = 0.0
                        else:
                            extracted_fields[field] = value
                
                # Mark as Section 80C eligible
                extracted_fields['section_80c_eligible'] = True
                extracted_fields['max_deduction_limit'] = 150000.0
                
                mandatory_fields = ['policy_number', 'premium_amount']
                found_mandatory = sum(1 for field in mandatory_fields if field in extracted_fields)
                confidence = found_mandatory / len(mandatory_fields)  # 0.0 to 1.0
                
        except Exception as e:
            errors.append(f"Error processing LIC document: {str(e)}")
            confidence = 0.0
        
        return ExtractedData(
            document_type="LIC Premium Receipt",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence,
            extraction_method="PDF parsing",
            errors=errors,
            raw_text=raw_text
        )

class BankInterestCertificateProcessor:
    """Processes Bank Interest Certificates"""
    
    @staticmethod
    def extract_from_pdf(file_path: str) -> ExtractedData:
        """Extract data from Bank Interest Certificate PDF"""
        extracted_fields = {}
        errors = []
        raw_text = ""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    raw_text += page.extract_text() + "\n"
            
            # Patterns specific to bank interest certificates (improved)
            patterns = {
                'bank_name': r'(?:^|\b)(HDFC\s*BANK|ICICI\s*BANK|STATE\s*BANK\s*OF\s*INDIA|SBI|AXIS\s*BANK|PUNJAB\s*NATIONAL\s*BANK|PNB|BANK\s*OF\s*BARODA|BOB|CANARA\s*BANK|UNION\s*BANK|INDIAN\s*BANK|BANK\s*OF\s*INDIA|YES\s*BANK|KOTAK\s*MAHINDRA\s*BANK|INDUSIND\s*BANK)(?=\s|$)',
                'account_number': r'(?:Account\s*No\.?|A\/c\s*No\.?|Account\s*Number)[:\s]*([X\*\d\s\-]{8,20})',
                'interest_amount': r'(?:Interest\s*Paid|Interest\s*Earned|Total\s*Interest|Int\.?\s*Paid|Int\.?\s*Earned)[:\s]*[\₹Rs\.]*\s*([\d,]{1,8}\.?\d{0,2})',
                'financial_year': r'(?:FY|Financial\s*Year|F\.Y\.?)[:\s]*(20\d{2}\-\d{2}|20\d{2})',
                'assessment_year': r'(?:AY|Assessment\s*Year|A\.Y\.?)[:\s]*(20\d{2}\-\d{2}|20\d{2})',
                'pan': r'\b([A-Z]{5}\d{4}[A-Z])\b',
                'period_from': r'(?:Period|From)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'period_to': r'(?:To|Till)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'certificate_number': r'(?:Certificate\s*No\.?|Cert\.?\s*No\.?|Certificate\s*Number)[:\s]*([A-Z0-9\-\/]{3,20})',
                'tds_amount': r'(?:TDS|Tax\s*Deducted|Tax\s*Deduction)[:\s]*[\₹Rs\.]*\s*([\d,]{1,8}\.?\d{0,2})'
            }
            
            confidence_score = 0.0
            for field, pattern in patterns.items():
                matches = re.findall(pattern, raw_text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    if field in ['interest_amount', 'tds_amount']:
                        # Convert to float for numerical fields with validation
                        try:
                            amount_str = matches[0].replace(',', '').replace(' ', '')
                            amount = float(amount_str)
                            
                            # Validate reasonable ranges for bank interest and TDS
                            if field == 'interest_amount' and 0 <= amount <= 10000000:  # Max 1 crore interest
                                extracted_fields[field] = amount
                                confidence_score += 0.2
                            elif field == 'tds_amount' and 0 <= amount <= 1000000:  # Max 10 lakh TDS
                                extracted_fields[field] = amount
                                confidence_score += 0.2
                            else:
                                # Amount seems unreasonable, skip
                                errors.append(f"Unreasonable {field}: {amount}")
                                
                        except ValueError:
                            # Try to extract just the numeric part more carefully
                            clean_str = re.sub(r'[^\d.,]', '', matches[0])
                            if clean_str:
                                try:
                                    amount = float(clean_str.replace(',', ''))
                                    if (field == 'interest_amount' and 0 <= amount <= 10000000) or \
                                       (field == 'tds_amount' and 0 <= amount <= 1000000):
                                        extracted_fields[field] = amount
                                        confidence_score += 0.1
                                except:
                                    extracted_fields[field] = matches[0]
                                    confidence_score += 0.05
                    elif field == 'bank_name':
                        # Clean up bank name extraction
                        bank_name = matches[0].strip().upper()
                        # Remove extra spaces and standardize
                        bank_name = re.sub(r'\s+', ' ', bank_name)
                        extracted_fields[field] = bank_name
                        confidence_score += 0.2
                    else:
                        extracted_fields[field] = matches[0].strip()
                        confidence_score += 0.1
            
            # Fallback extraction if bank name not found with primary patterns
            if 'bank_name' not in extracted_fields:
                # Try alternative bank name patterns
                fallback_bank_patterns = [
                    r'HDFC\s*BANK',
                    r'ICICI\s*BANK', 
                    r'SBI|STATE\s*BANK',
                    r'AXIS\s*BANK',
                    r'PNB|PUNJAB\s*NATIONAL',
                    r'BOB|BANK\s*OF\s*BARODA',
                    r'CANARA\s*BANK',
                    r'YES\s*BANK',
                    r'KOTAK\s*MAHINDRA'
                ]
                
                for pattern in fallback_bank_patterns:
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        bank_name = match.group().strip().upper()
                        bank_name = re.sub(r'\s+', ' ', bank_name)
                        extracted_fields['bank_name'] = bank_name
                        confidence_score += 0.15
                        break
            
            # Fallback for amounts if not found
            if 'interest_amount' not in extracted_fields:
                # Try more generic patterns for interest
                fallback_interest_patterns = [
                    r'Interest.*?(\d{1,6}\.?\d{0,2})',
                    r'(\d{1,6}\.?\d{0,2}).*?Interest',
                    r'Total.*?(\d{1,6}\.?\d{0,2})'
                ]
                
                for pattern in fallback_interest_patterns:
                    matches = re.findall(pattern, raw_text, re.IGNORECASE)
                    if matches:
                        try:
                            amount = float(matches[0].replace(',', ''))
                            if 1 <= amount <= 1000000:  # Reasonable interest range
                                extracted_fields['interest_amount'] = amount
                                confidence_score += 0.1
                                break
                        except:
                            continue
            
            # Special check for interest certificate indicators
            certificate_indicators = [
                'interest certificate', 'interest paid certificate', 'certificate of interest',
                'interest statement', 'annual interest', 'savings account interest'
            ]
            
            for indicator in certificate_indicators:
                if indicator.lower() in raw_text.lower():
                    confidence_score += 0.3
                    break
            
            confidence_score = min(confidence_score, 1.0)
            
            # Determine ITR section based on extracted data
            itr_section = "Other Income (Interest from Savings Account)"
            if 'interest_amount' in extracted_fields:
                if extracted_fields['interest_amount'] > 10000:
                    itr_section += " - Section 80TTA applicable (up to ₹10,000 exempt)"
                else:
                    itr_section += " - Fully exempt under Section 80TTA"
        
        except Exception as e:
            errors.append(f"Error processing bank interest certificate: {str(e)}")
            confidence_score = 0.1
        
        return ExtractedData(
            document_type="Bank Interest Certificate",
            file_path=file_path,
            extracted_fields=extracted_fields,
            confidence_score=confidence_score,
            extraction_method="PDF text extraction with pattern matching",
            errors=errors,
            raw_text=raw_text
        )

class DocumentProcessor:
    """Main document processor that routes to specific processors"""
    
    def __init__(self):
        self.processors = {
            'form_16': Form16Processor(),
            'bank_statement': BankStatementProcessor(),
            'bank_interest_certificate': BankInterestCertificateProcessor(),
            'mutual_funds_capital_gains': MutualFundsCapitalGainsProcessor(),
            'stocks_capital_gains': StocksCapitalGainsProcessor(),
            'investment': InvestmentDocumentProcessor()
        }
    
    def process_document(self, file_path: str, document_type: str) -> ExtractedData:
        """Process a document based on its type"""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if document_type == 'form_16':
                if file_ext == '.pdf':
                    return self.processors['form_16'].extract_from_pdf(file_path)
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif document_type == 'bank_statement':
                if file_ext == '.pdf':
                    return self.processors['bank_statement'].extract_from_pdf(file_path)
                elif file_ext in ['.xlsx', '.xls']:
                    return self.processors['bank_statement'].extract_from_excel(file_path)
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif document_type == 'bank_interest_certificate':
                if file_ext == '.pdf':
                    return self.processors['bank_interest_certificate'].extract_from_pdf(file_path)
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif document_type == 'lic_premium':
                if file_ext == '.pdf':
                    return self.processors['investment'].extract_lic_premium(file_path)
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif document_type == 'mutual_funds_capital_gains':
                if file_ext in ['.xlsx', '.xls']:
                    return self.processors['mutual_funds_capital_gains'].extract_from_excel(file_path)
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif document_type == 'investment':
                if file_ext in ['.xlsx', '.xls']:
                    return self.processors['stocks_capital_gains'].extract_from_excel(file_path)
                elif file_ext == '.pdf':
                    return self.processors['investment'].extract_lic_premium(file_path)  # Fallback for PDF investments
                else:
                    return self._unsupported_format(file_path, document_type, file_ext)
            
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff']:
                return self._process_image_with_ocr(file_path, document_type)
            
            else:
                return self._unsupported_document_type(file_path, document_type)
                
        except Exception as e:
            return ExtractedData(
                document_type=document_type,
                file_path=file_path,
                extracted_fields={},
                confidence_score=0.0,
                extraction_method="Error",
                errors=[f"Processing error: {str(e)}"]
            )
    
    def _process_image_with_ocr(self, file_path: str, document_type: str) -> ExtractedData:
        """Process image documents using OCR"""
        if not OCR_AVAILABLE:
            return ExtractedData(
                document_type=document_type,
                file_path=file_path,
                extracted_fields={},
                confidence_score=0.0,
                extraction_method="OCR not available",
                errors=["OCR libraries not installed. Install pytesseract and PIL."]
            )
        
        try:
            # Extract text using OCR
            image = Image.open(file_path)
            raw_text = pytesseract.image_to_string(image)
            
            # Basic processing - can be enhanced for specific document types
            extracted_fields = {
                'ocr_text': raw_text,
                'text_length': len(raw_text)
            }
            
            # Simple pattern matching for common fields
            patterns = {
                'amount': r'[\₹Rs\.]\s*([\d,]+\.?\d*)',
                'date': r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
                'pan': r'([A-Z]{5}\d{4}[A-Z])'
            }
            
            for field, pattern in patterns.items():
                matches = re.findall(pattern, raw_text)
                if matches:
                    extracted_fields[field] = matches[0] if len(matches) == 1 else matches
            
            confidence = 0.3 if raw_text.strip() else 0.0  # 0.0-1.0 scale
            
            return ExtractedData(
                document_type=document_type,
                file_path=file_path,
                extracted_fields=extracted_fields,
                confidence_score=confidence,
                extraction_method="OCR",
                errors=[],
                raw_text=raw_text
            )
            
        except Exception as e:
            return ExtractedData(
                document_type=document_type,
                file_path=file_path,
                extracted_fields={},
                confidence_score=0.0,
                extraction_method="OCR failed",
                errors=[f"OCR processing error: {str(e)}"]
            )
    
    def _unsupported_format(self, file_path: str, document_type: str, file_ext: str) -> ExtractedData:
        """Handle unsupported file formats"""
        return ExtractedData(
            document_type=document_type,
            file_path=file_path,
            extracted_fields={},
            confidence_score=0.0,
            extraction_method="Unsupported format",
            errors=[f"File format {file_ext} not supported for {document_type}"]
        )
    
    def _unsupported_document_type(self, file_path: str, document_type: str) -> ExtractedData:
        """Handle unsupported document types"""
        return ExtractedData(
            document_type=document_type,
            file_path=file_path,
            extracted_fields={},
            confidence_score=0.0,
            extraction_method="Unsupported type",
            errors=[f"Document type {document_type} not yet supported"]
        )
    
    def batch_process_documents(self, documents: List[Tuple[str, str]]) -> List[ExtractedData]:
        """Process multiple documents"""
        results = []
        
        for file_path, doc_type in documents:
            print(f"Processing: {os.path.basename(file_path)} ({doc_type})")
            result = self.process_document(file_path, doc_type)
            results.append(result)
            
            if result.errors:
                print(f"  ⚠️  Errors: {', '.join(result.errors)}")
            else:
                print(f"  ✅ Extracted {len(result.extracted_fields)} fields (confidence: {result.confidence_score:.1f}%)")
        
        return results
    
    def export_results_to_json(self, results: List[ExtractedData], output_file: str):
        """Export extraction results to JSON"""
        export_data = []
        
        for result in results:
            export_data.append({
                'document_type': result.document_type,
                'file_path': result.file_path,
                'extracted_fields': result.extracted_fields,
                'confidence_score': result.confidence_score,
                'extraction_method': result.extraction_method,
                'errors': result.errors,
                'timestamp': datetime.now().isoformat()
            })
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"✅ Exported results to {output_file}")

# Example usage
if __name__ == "__main__":
    processor = DocumentProcessor()
    
    # Example processing
    sample_documents = [
        ("./sample_form16.pdf", "form_16"),
        ("./sample_bank_statement.pdf", "bank_statement"),
        ("./sample_lic_receipt.pdf", "lic_premium")
    ]
    
    results = processor.batch_process_documents(sample_documents)
    processor.export_results_to_json(results, "./extraction_results.json")