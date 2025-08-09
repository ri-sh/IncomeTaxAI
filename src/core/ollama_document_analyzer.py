"""
Enhanced Ollama Document Analyzer
Uses LLM to read file contents and extract all relevant tax details directly
"""

import json
import re
from pathlib import Path
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF for PDF text extraction
import pandas as pd
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

@dataclass
class OllamaExtractedData:
    """Enhanced extracted data from Ollama analysis"""
    document_type: str
    confidence: float
    
    # Salary details (from Form 16)
    employee_name: Optional[str] = None
    pan: Optional[str] = None
    employer_name: Optional[str] = None
    gross_salary: float = 0.0
    basic_salary: float = 0.0
    perquisites: float = 0.0  # Added perquisites field
    total_gross_salary: float = 0.0  # Added total gross salary field
    hra_received: float = 0.0
    special_allowance: float = 0.0
    other_allowances: float = 0.0
    tax_deducted: float = 0.0
    
    # Bank details
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    interest_amount: float = 0.0
    tds_amount: float = 0.0
    financial_year: Optional[str] = None
    
    # Capital gains
    total_capital_gains: float = 0.0
    long_term_capital_gains: float = 0.0
    short_term_capital_gains: float = 0.0
    number_of_transactions: int = 0
    
    # Investment details
    epf_amount: float = 0.0
    ppf_amount: float = 0.0
    life_insurance: float = 0.0
    elss_amount: float = 0.0
    health_insurance: float = 0.0
    
    # Extracted text and analysis
    raw_text: str = ""
    extraction_method: str = "ollama_llm"
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class OllamaDocumentAnalyzer:
    """Enhanced document analyzer using Ollama LLM for content extraction"""
    
    def __init__(self):
        self.llm = self._setup_ollama()
        self.logger = logging.getLogger(__name__)
    
    def _setup_ollama(self) -> Optional[Ollama]:
        """Setup Ollama LLM for document analysis"""
        try:
            ollama_llm = Ollama(
                model="llama2",
                base_url="http://localhost:11434",
                request_timeout=60.0,
                temperature=0.1,  # Low temperature for consistent extraction
                context_window=8192,  # Large context for full documents
                num_predict=2048  # Allow detailed responses
            )
            
            # Test the connection
            test_response = ollama_llm.complete("Hello")
            logging.getLogger(__name__).info("Ollama LLM ready for document analysis")
            return ollama_llm
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Could not setup Ollama: {e}")
            return None
    
    def analyze_document(self, file_path: str) -> OllamaExtractedData:
        """Analyze document using Ollama LLM to extract all relevant details"""
        
        file_path = Path(file_path)
        
        if not self.llm:
            return OllamaExtractedData(
                document_type="unknown",
                confidence=0.0,
                errors=["Ollama LLM not available"]
            )
        
        try:
            # Extract text content from the document
            text_content = self._extract_text_content(file_path)
            
            if not text_content:
                return OllamaExtractedData(
                    document_type="unknown",
                    confidence=0.0,
                    errors=["Could not extract text content from document"]
                )
            
            # Analyze with Ollama
            extracted_data = self._analyze_with_ollama(file_path.name, text_content, file_path)
            
            # Add file path to the data for fallback processing
            if hasattr(extracted_data, 'raw_text'):
                # If it's an OllamaExtractedData object, we need to add the file path differently
                # For now, let's just return the data as is
                pass
            
            return extracted_data
            
        except Exception as e:
            logging.getLogger(__name__).exception(f"Document analysis error for {file_path}: {e}")
            return OllamaExtractedData(
                document_type="unknown",
                confidence=0.0,
                errors=[f"Document analysis error: {str(e)}"],
                raw_text="",
                extraction_method="ollama_llm_error"
            )
    
    def _extract_text_content(self, file_path: Path) -> str:
        """Extract text content from different file types"""
        
        file_ext = file_path.suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return self._extract_pdf_text(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                return self._extract_excel_text(file_path)
            else:
                return ""
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """Extract text from PDF using PyMuPDF"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_excel_text(self, file_path: Path) -> str:
        """Extract text representation from Excel file"""
        try:
            # For capital gains reports, we need to find the actual data section
            if any(term in file_path.name.lower() for term in ['capital', 'gains', 'profit', 'trading']):
                print("📊 Processing capital gains Excel file...")
                
                # First read without header to see the structure
                df = pd.read_excel(file_path, header=None)
                print("📊 Looking for data section...")
                
                # Find the start of data section
                data_start = None
                header_rows = []
                
                # Look for common section markers
                for idx, row in df.iterrows():
                    row_text = ' '.join(str(cell) for cell in row if pd.notna(cell))
                    print(f"   Row {idx}: {row_text[:100]}")
                    
                    # Skip empty rows
                    if not row_text.strip():
                        continue
                    
                    # Look for section headers
                    if any(marker in row_text.lower() for marker in ['summary', 'transaction details', 'trade details', 'statement']):
                        data_start = idx + 1  # Data starts after this row
                        print(f"✅ Found data section at row {data_start}")
                        
                        # Look for header rows (usually 1-2 rows after section marker)
                        for header_idx in range(data_start, min(data_start + 3, len(df))):
                            header_row = df.iloc[header_idx]
                            header_text = ' '.join(str(cell) for cell in header_row if pd.notna(cell))
                            
                            # Skip empty rows
                            if not header_text.strip():
                                continue
                            
                            # Check if this looks like a header row
                            header_text_lower = header_text.lower()
                            
                            # Primary header indicators
                            primary_indicators = ['date', 'amount', 'type', 'gain', 'loss', 'price', 'value']
                            # Secondary header indicators
                            secondary_indicators = ['symbol', 'quantity', 'shares', 'units', 'cost', 'proceeds']
                            # Transaction type indicators
                            type_indicators = ['ltcg', 'stcg', 'long term', 'short term', 'holding period']
                            
                            # Check for header indicators
                            if (any(term in header_text_lower for term in primary_indicators) or
                                any(term in header_text_lower for term in secondary_indicators) or
                                any(term in header_text_lower for term in type_indicators)):
                                header_rows.append(header_idx)
                                print(f"✅ Found header row {header_idx}: {header_text[:100]}")
                                
                                # Look for sub-headers in next row
                                if header_idx + 1 < len(df):
                                    next_row = df.iloc[header_idx + 1]
                                    next_text = ' '.join(str(cell) for cell in next_row if pd.notna(cell)).lower()
                                    if any(term in next_text for term in primary_indicators + secondary_indicators + type_indicators):
                                        header_rows.append(header_idx + 1)
                                        print(f"✅ Found sub-header row {header_idx + 1}: {next_text[:100]}")
                        
                        if header_rows:
                            data_start = max(header_rows) + 1
                            print(f"✅ Data will start at row {data_start}")
                            break
                
                if data_start is None:
                    print("⚠️ Could not find data section, using default Excel processing")
                    df = pd.read_excel(file_path)
                else:
                    # Re-read with multi-row headers if found
                    if len(header_rows) > 1:
                        print("📊 Using multi-row headers")
                        # Read without header first to handle merged cells
                        df = pd.read_excel(file_path, header=None)
                        
                        # Extract header rows
                        header_data = []
                        for idx in header_rows:
                            row = df.iloc[idx]
                            # Fill forward merged cells
                            last_valid = None
                            cleaned_row = []
                            for cell in row:
                                if pd.notna(cell) and str(cell).strip():
                                    last_valid = str(cell).strip()
                                cleaned_row.append(last_valid if last_valid else '')
                            header_data.append(cleaned_row)
                        
                        # Combine header rows
                        combined_headers = []
                        for col_idx in range(len(header_data[0])):
                            parts = []
                            for row_idx in range(len(header_data)):
                                if header_data[row_idx][col_idx]:
                                    parts.append(header_data[row_idx][col_idx])
                            combined_headers.append('_'.join(parts) if parts else f'Column_{col_idx}')
                        
                        # Apply combined headers and skip header rows
                        df.columns = combined_headers
                        df = df.iloc[max(header_rows) + 1:]
                        print("📊 Combined headers:", combined_headers)
                    else:
                        # Single header row
                        header_row = header_rows[0] if header_rows else data_start
                        df = pd.read_excel(file_path, header=None)
                        
                        # Handle merged cells in single header row
                        header = df.iloc[header_row]
                        last_valid = None
                        cleaned_header = []
                        seen_headers = {}  # Track header counts for uniqueness
                        
                        for cell in header:
                            # Get cell value
                            if pd.notna(cell) and str(cell).strip():
                                last_valid = str(cell).strip()
                            cell_value = last_valid if last_valid else f'Column_{len(cleaned_header)}'
                            
                            # Ensure unique header
                            if cell_value in seen_headers:
                                seen_headers[cell_value] += 1
                                # Try to infer purpose from next few rows
                                sample_values = df.iloc[header_row + 1:header_row + 4, len(cleaned_header)].dropna()
                                if not sample_values.empty:
                                    sample_text = ' '.join(str(val) for val in sample_values).lower()
                                    if any(term in sample_text for term in ['purchase', 'buy']):
                                        cell_value = f'purchase_{cell_value}'
                                    elif any(term in sample_text for term in ['sale', 'sell']):
                                        cell_value = f'sale_{cell_value}'
                                    elif any(term in sample_text for term in ['type', 'term']):
                                        cell_value = f'type_{cell_value}'
                                    else:
                                        cell_value = f'{cell_value}_{seen_headers[cell_value]}'
                            else:
                                seen_headers[cell_value] = 1
                            
                            cleaned_header.append(cell_value)
                        
                        # Apply cleaned header and skip header row
                        df.columns = cleaned_header
                        df = df.iloc[header_row + 1:]
                        print("📊 Cleaned header:", cleaned_header)
                    
                    # Clean up and infer column names
                    new_columns = []
                    for col_idx, col in enumerate(df.columns):
                        col_name = str(col).strip().replace('\n', ' ')
                        
                        # If unnamed or needs inference, analyze content
                        needs_inference = 'unnamed' in col_name.lower() or not col_name.strip() or col_name.startswith('Column_')
                        if needs_inference:
                            # Get sample values from different parts of the column
                            sample_values = pd.concat([
                                df.iloc[:3, col_idx].dropna(),  # First few rows
                                df.iloc[len(df)//2-1:len(df)//2+2, col_idx].dropna(),  # Middle rows
                                df.iloc[-3:, col_idx].dropna()  # Last few rows
                            ]).drop_duplicates()
                            
                            if not sample_values.empty:
                                # Convert all values to string and join
                                sample_text = ' '.join(str(val) for val in sample_values).lower()
                                print(f"\n🔍 Analyzing column {col_idx} content:")
                                print(f"   Sample values: {sample_text[:100]}")
                                
                                # Try to detect dates
                                try:
                                    # Common date formats in Indian financial documents
                                    date_formats = [
                                        '%d-%m-%Y', '%d/%m/%Y',  # DD-MM-YYYY, DD/MM/YYYY
                                        '%Y-%m-%d', '%Y/%m/%d',  # YYYY-MM-DD, YYYY/MM/DD
                                        '%d-%b-%Y', '%d-%B-%Y',  # DD-Mon-YYYY, DD-Month-YYYY
                                        '%d.%m.%Y', '%Y.%m.%d',  # DD.MM.YYYY, YYYY.MM.DD
                                    ]
                                    
                                    # Try each format
                                    dates = None
                                    for fmt in date_formats:
                                        try:
                                            dates = pd.to_datetime(sample_values, format=fmt, errors='coerce')
                                            if not dates.isna().all():
                                                print(f"   ✅ Contains valid dates (format: {fmt})")
                                                break
                                        except:
                                            continue
                                    
                                    # If no format worked, try flexible parsing
                                    if dates is None or dates.isna().all():
                                        dates = pd.to_datetime(sample_values, errors='coerce')
                                    
                                    if dates is not None and not dates.isna().all():
                                        # Check if values look like dates
                                        date_indicators = [
                                            '-', '/', '.', # Common separators
                                            'jan', 'feb', 'mar', 'apr', 'may', 'jun',
                                            'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
                                        ]
                                        sample_text = ' '.join(str(val).lower() for val in sample_values)
                                        if any(ind in sample_text for ind in date_indicators):
                                            print("   ✅ Contains date-like values")
                                            if any(term in col_name.lower() for term in ['purchase', 'buy', 'acquired']):
                                                col_name = 'Purchase Date'
                                            elif any(term in col_name.lower() for term in ['sale', 'sell', 'disposed']):
                                                col_name = 'Sale Date'
                                            else:
                                                col_name = 'Transaction Date'
                                except Exception as e:
                                    print(f"   ⚠️ Date parsing error: {str(e)}")
                                    pass
                                
                                # Try to detect numbers and analyze patterns
                                has_currency = False
                                has_stock = False
                                has_qty = False
                                has_price = False
                                
                                try:
                                    numbers = pd.to_numeric(sample_values, errors='coerce')
                                    if not numbers.isna().all():
                                        print("   ✅ Contains numeric values")
                                        
                                        # Check for currency indicators
                                        currency_indicators = ['rs', 'inr', '₹', 'rupees', 'rs.', 'amount']
                                        has_currency = any(term in sample_text for term in currency_indicators)
                                        
                                        # Check for stock market indicators
                                        stock_indicators = ['isin', 'scrip', 'symbol', 'nse', 'bse', 'shares']
                                        has_stock = any(term in sample_text for term in stock_indicators)
                                        
                                        # Check for quantity indicators
                                        qty_indicators = ['qty', 'quantity', 'units', 'shares', 'lots']
                                        has_qty = any(term in sample_text for term in qty_indicators)
                                        
                                        # Check for price indicators
                                        price_indicators = ['price', 'rate', 'value', 'cost', 'amount']
                                        has_price = any(term in sample_text for term in price_indicators)
                                        
                                        # Print findings
                                        if has_currency:
                                            print("   ✅ Contains currency indicators")
                                        if has_stock:
                                            print("   ✅ Contains stock market indicators")
                                        if has_qty:
                                            print("   ✅ Contains quantity indicators")
                                        if has_price:
                                            print("   ✅ Contains price indicators")
                                        
                                        # Analyze number patterns
                                        non_null_numbers = numbers[~numbers.isna()]
                                        if len(non_null_numbers) > 0:
                                            # Check for ISIN pattern (12 characters)
                                            isin_pattern = any(len(str(int(val))) == 12 for val in non_null_numbers if pd.notna(val))
                                            if isin_pattern:
                                                print("   ✅ Contains ISIN-like numbers")
                                            
                                            # Check for typical price ranges
                                            avg_value = non_null_numbers.mean()
                                            if 10 <= avg_value <= 10000:  # Typical stock price range
                                                print("   ✅ Contains stock price-like values")
                                            elif avg_value > 10000:  # Likely total amounts
                                                print("   ✅ Contains total amount-like values")
                                            elif avg_value < 10:  # Likely quantities or small numbers
                                                print("   ✅ Contains quantity-like values")
                                except Exception as e:
                                    print(f"   ⚠️ Number analysis error: {str(e)}")
                                    pass
                                
                                # Try to infer column type based on stock trading patterns
                                if not col_name.endswith('Date'):  # Skip if already identified as date
                                    # Stock trading specific patterns
                                    if has_stock and any(term in sample_text for term in ['stock', 'company', 'ltd', 'limited']):
                                        col_name = 'Stock Name'
                                    elif has_stock and any(term in sample_text for term in ['isin', 'code']):
                                        col_name = 'ISIN'
                                    elif has_qty or any(term in sample_text for term in ['quantity', 'units', 'shares', 'qty']):
                                        col_name = 'Quantity'
                                    elif has_price and any(term in sample_text for term in ['buy', 'purchase', 'acquisition']):
                                        col_name = 'Buy Price'
                                    elif has_price and any(term in sample_text for term in ['sell', 'sale', 'disposal']):
                                        col_name = 'Sell Price'
                                    elif has_currency and any(term in sample_text for term in ['buy', 'purchase', 'acquisition']):
                                        col_name = 'Buy Value'
                                    elif has_currency and any(term in sample_text for term in ['sell', 'sale', 'disposal']):
                                        col_name = 'Sell Value'
                                    elif any(term in sample_text for term in ['gain', 'profit', 'loss', 'p&l', 'realised']):
                                        col_name = 'Gain/Loss'
                                    elif any(term in sample_text for term in ['type', 'term', 'ltcg', 'stcg', 'long', 'short']):
                                        col_name = 'Transaction Type'
                                    elif any(term in sample_text for term in ['symbol', 'scrip']):
                                        col_name = 'Symbol'
                                    elif any(term in sample_text for term in ['cost', 'basis', 'invested']):
                                        col_name = 'Cost Basis'
                                    elif any(term in sample_text for term in ['proceed', 'value', 'amount']):
                                        col_name = 'Sale Value'
                                    elif any(term in sample_text for term in ['charges', 'brokerage', 'stt', 'gst']):
                                        col_name = 'Charges'
                                    elif any(term in sample_text for term in ['dividend', 'interest']):
                                        col_name = 'Dividend/Interest'
                                    elif any(term in sample_text for term in ['turnover', 'volume']):
                                        col_name = 'Turnover'
                                    elif any(term in sample_text for term in ['intraday', 'day']):
                                        col_name = 'Intraday'
                                    elif any(term in sample_text for term in ['realised', 'unrealised']):
                                        col_name = 'Realisation Status'
                                
                                print(f"   ✅ Inferred name: {col_name}")
                        
                        new_columns.append(col_name)
                    
                    # Normalize column names
                    normalized_columns = []
                    for col in new_columns:
                        # Convert to lowercase for normalization
                        col = str(col).lower()
                        
                        # Normalize common variations
                        if any(term in col for term in ['purchase', 'buy', 'acquisition']):
                            if any(term in col for term in ['date', 'day']):
                                col = 'purchase_date'
                            elif any(term in col for term in ['price', 'cost', 'amount', 'value']):
                                col = 'purchase_price'
                        elif any(term in col for term in ['sale', 'sell', 'disposal']):
                            if any(term in col for term in ['date', 'day']):
                                col = 'sale_date'
                            elif any(term in col for term in ['price', 'amount', 'value', 'proceed']):
                                col = 'sale_price'
                        elif any(term in col for term in ['gain', 'profit', 'loss']):
                            col = 'gain_loss'
                        elif any(term in col for term in ['type', 'category', 'term']):
                            col = 'transaction_type'
                        elif any(term in col for term in ['symbol', 'scrip', 'isin']):
                            col = 'symbol'
                        elif any(term in col for term in ['quantity', 'units', 'shares', 'qty']):
                            col = 'quantity'
                        elif any(term in col for term in ['cost', 'basis']):
                            col = 'cost_basis'
                        
                        # Convert spaces and special chars to underscores
                        col = re.sub(r'[^a-z0-9]+', '_', col)
                        # Remove leading/trailing underscores
                        col = col.strip('_')
                        # Ensure unique names
                        if col in normalized_columns:
                            col = f"{col}_{normalized_columns.count(col) + 1}"
                        
                        normalized_columns.append(col)
                    
                    # Update column names
                    df.columns = normalized_columns
                    print("\n📊 Normalized column names:")
                    for old, new in zip(new_columns, normalized_columns):
                        if old != new:
                            print(f"   • {old} → {new}")
                    
                    # Drop any fully empty rows
                    df = df.dropna(how='all')
                    print(f"✅ Loaded data with {len(df)} rows")
                    
                    # Validate column names (including stock trading specific columns)
                    required_cols = {
                        'purchase_date': False,
                        'sale_date': False,
                        'transaction_type': False,
                        'gain_loss': False
                    }
                    
                    # Stock trading specific columns
                    stock_trading_cols = {
                        'stock_name': False,
                        'isin': False,
                        'quantity': False,
                        'buy_price': False,
                        'sell_price': False,
                        'buy_value': False,
                        'sell_value': False,
                        'gain_loss': False
                    }
                    
                    alternative_cols = {
                        'purchase_date': ['buy_date', 'acquisition_date'],
                        'sale_date': ['sell_date', 'disposal_date'],
                        'transaction_type': ['holding_period', 'term'],
                        'gain_loss': ['net_profit', 'net_gain', 'profit_loss', 'realised_p&l'],
                        'stock_name': ['company_name', 'scrip_name'],
                        'isin': ['isin_code', 'security_code'],
                        'quantity': ['qty', 'shares', 'units'],
                        'buy_price': ['purchase_price', 'acquisition_price'],
                        'sell_price': ['sale_price', 'disposal_price'],
                        'buy_value': ['purchase_value', 'acquisition_value'],
                        'sell_value': ['sale_value', 'disposal_value']
                    }
                    
                    # Check for required columns (both general and stock trading specific)
                    for col in df.columns:
                        # Check general required columns
                        for req_col, found in required_cols.items():
                            if not found:  # Only check if not already found
                                if col == req_col or any(alt == col for alt in alternative_cols.get(req_col, [])):
                                    required_cols[req_col] = True
                        
                        # Check stock trading specific columns
                        for req_col, found in stock_trading_cols.items():
                            if not found:  # Only check if not already found
                                if col == req_col or any(alt == col for alt in alternative_cols.get(req_col, [])):
                                    stock_trading_cols[req_col] = True
                    
                    # Report validation results
                    print("\n📊 Column validation:")
                    missing_cols = []
                    found_stock_cols = []
                    
                    # Check general columns
                    for col, found in required_cols.items():
                        if found:
                            print(f"   ✅ Found {col}")
                        else:
                            print(f"   ❌ Missing {col}")
                            missing_cols.append(col)
                    
                    # Check stock trading columns
                    for col, found in stock_trading_cols.items():
                        if found:
                            print(f"   ✅ Found stock trading column: {col}")
                            found_stock_cols.append(col)
                        else:
                            print(f"   ❌ Missing stock trading column: {col}")
                    
                    # Determine if this is a stock trading report
                    is_stock_trading = len(found_stock_cols) >= 3  # At least 3 stock trading columns
                    
                    if is_stock_trading:
                        print(f"\n📈 Stock Trading Report Detected!")
                        print(f"   Found {len(found_stock_cols)} stock trading columns: {', '.join(found_stock_cols)}")
                    
                    if missing_cols and not is_stock_trading:
                        print("\n⚠️ Missing required columns:")
                        print("   The following columns are required for accurate capital gains calculation:")
                        for col in missing_cols:
                            print(f"   • {col} (alternatives: {', '.join(alternative_cols[col])})")
                    elif not missing_cols or is_stock_trading:
                        print("\n✅ Sufficient columns found for analysis")
            else:
                # Default Excel processing
                df = pd.read_excel(file_path)
            
            # Create a text representation of the Excel data
            text_content = f"Excel file: {file_path.name}\n\n"
            text_content += f"Columns: {', '.join(df.columns.tolist())}\n\n"
            
            # Special handling for capital gains reports
            if any(term in file_path.name.lower() for term in ['capital', 'gains', 'profit', 'trading']):
                print("📊 Processing capital gains Excel file...")
                
                # Look for sections in the data
                sections = {}
                current_section = None
                section_data = []
                
                for idx, row in df.iterrows():
                    row_text = ' '.join(str(cell) for cell in row if pd.notna(cell)).lower()
                    
                    # Check for section headers (including stock trading specific sections)
                    section_markers = [
                        'summary', 'details', 'transactions', 'statement',
                        'realised p&l', 'realised trades', 'intraday trades', 'short term trades', 'long term trades',
                        'charges', 'turnover', 'others', 'dividends', 'buyback',
                        'intraday p&l', 'short term p&l', 'long term p&l'
                    ]
                    
                    if any(marker in row_text for marker in section_markers):
                        if current_section and section_data:
                            try:
                                # Convert section_data to a proper format for DataFrame creation
                                if section_data:
                                    # If section_data contains pandas Series, convert to list of lists
                                    if hasattr(section_data[0], 'index'):
                                        # Convert pandas Series to list
                                        clean_data = []
                                        for row in section_data:
                                            if hasattr(row, 'tolist'):
                                                clean_data.append(row.tolist())
                                            else:
                                                clean_data.append(list(row))
                                        sections[current_section] = pd.DataFrame(clean_data)
                                    else:
                                        sections[current_section] = pd.DataFrame(section_data)
                                else:
                                    sections[current_section] = pd.DataFrame()
                            except Exception as e:
                                print(f"⚠️ Error creating DataFrame for section '{current_section}': {e}")
                                # Try alternative approach
                                try:
                                    # Convert to list of lists and try again
                                    clean_data = []
                                    for row in section_data:
                                        if hasattr(row, 'tolist'):
                                            clean_data.append(row.tolist())
                                        else:
                                            clean_data.append(list(row))
                                    sections[current_section] = pd.DataFrame(clean_data)
                                except Exception as e2:
                                    print(f"⚠️ Failed to create DataFrame even with clean data: {e2}")
                                    # Create empty DataFrame as fallback
                                    sections[current_section] = pd.DataFrame()
                            section_data = []
                        current_section = row_text
                        print(f"📊 Found section: {current_section}")
                        continue
                    
                    # Skip empty rows
                    if row.isna().all():
                        continue
                    
                    # Add row to current section
                    if current_section:
                        section_data.append(row)
                
                # Add last section
                if current_section and section_data:
                    try:
                        # Convert section_data to a proper format for DataFrame creation
                        if section_data:
                            # If section_data contains pandas Series, convert to list of lists
                            if hasattr(section_data[0], 'index'):
                                # Convert pandas Series to list
                                clean_data = []
                                for row in section_data:
                                    if hasattr(row, 'tolist'):
                                        clean_data.append(row.tolist())
                                    else:
                                        clean_data.append(list(row))
                                sections[current_section] = pd.DataFrame(clean_data)
                            else:
                                sections[current_section] = pd.DataFrame(section_data)
                        else:
                            sections[current_section] = pd.DataFrame()
                    except Exception as e:
                        print(f"⚠️ Error creating DataFrame for section '{current_section}': {e}")
                        # Try alternative approach
                        try:
                            # Convert to list of lists and try again
                            clean_data = []
                            for row in section_data:
                                if hasattr(row, 'tolist'):
                                    clean_data.append(row.tolist())
                                else:
                                    clean_data.append(list(row))
                            sections[current_section] = pd.DataFrame(clean_data)
                        except Exception as e2:
                            print(f"⚠️ Failed to create DataFrame even with clean data: {e2}")
                            # Create empty DataFrame as fallback
                            sections[current_section] = pd.DataFrame()
                
                # Process each section
                text_content += "CAPITAL GAINS SECTIONS:\n"
                
                # Store extracted capital gains data for post-processing
                extracted_capital_gains = {
                    'short_term_capital_gains': 0.0,
                    'long_term_capital_gains': 0.0,
                    'total_capital_gains': 0.0
                }
                
                for section_name, section_df in sections.items():
                    print(f"\n📊 Processing section: {section_name}")
                    text_content += f"\n{section_name.upper()}:\n"
                    
                    # Stock trading specific processing
                    if any(term in section_name.lower() for term in ['realised p&l', 'intraday p&l', 'short term p&l', 'long term p&l']):
                        print("📈 Processing P&L section...")
                        # Extract P&L values from this section
                        for idx, row in section_df.iterrows():
                            row_text = ' '.join(str(cell) for cell in row if pd.notna(cell))
                            if any(term in row_text.lower() for term in ['intraday', 'short term', 'long term']):
                                # Try to extract numeric values
                                numbers = re.findall(r'[-+]?\d+\.?\d*', row_text)
                                if numbers:
                                    try:
                                        value = float(numbers[0])
                                        if 'intraday' in row_text.lower():
                                            text_content += f"Intraday P&L: ₹{value:,.2f}\n"
                                        elif 'short term' in row_text.lower():
                                            text_content += f"Short Term P&L: ₹{value:,.2f}\n"
                                        elif 'long term' in row_text.lower():
                                            text_content += f"Long Term P&L: ₹{value:,.2f}\n"
                                    except:
                                        pass
                        
                        # Also extract from section name if it contains the value
                        section_lower = section_name.lower()
                        if 'short term p&l' in section_lower:
                            # Extract number from section name like "short term p&l -147459.51"
                            numbers = re.findall(r'[-+]?\d+\.?\d*', section_name)
                            if numbers:
                                try:
                                    value = float(numbers[0])
                                    text_content += f"Short Term P&L: ₹{value:,.2f}\n"
                                    extracted_capital_gains['short_term_capital_gains'] = value
                                    print(f"✅ Extracted Short Term P&L from section name: ₹{value:,.2f}")
                                except:
                                    pass
                        elif 'long term p&l' in section_lower:
                            # Extract number from section name like "long term p&l 166511.16"
                            numbers = re.findall(r'[-+]?\d+\.?\d*', section_name)
                            if numbers:
                                try:
                                    value = float(numbers[0])
                                    text_content += f"Long Term P&L: ₹{value:,.2f}\n"
                                    extracted_capital_gains['long_term_capital_gains'] = value
                                    print(f"✅ Extracted Long Term P&L from section name: ₹{value:,.2f}")
                                except:
                                    pass
                
                    elif any(term in section_name.lower() for term in ['charges', 'turnover', 'others']):
                        print("💰 Processing charges/turnover section...")
                        # Extract charges and turnover information
                        for idx, row in section_df.iterrows():
                            row_text = ' '.join(str(cell) for cell in row if pd.notna(cell))
                            if any(term in row_text.lower() for term in ['total', 'charges', 'turnover']):
                                numbers = re.findall(r'[-+]?\d+\.?\d*', row_text)
                                if numbers:
                                    try:
                                        value = float(numbers[0])
                                        if 'total' in row_text.lower():
                                            text_content += f"Total Charges: ₹{value:,.2f}\n"
                                        elif 'turnover' in row_text.lower():
                                            text_content += f"Turnover: ₹{value:,.2f}\n"
                                    except:
                                                                            pass
                
                # Calculate total capital gains after processing all sections
                stcg = extracted_capital_gains['short_term_capital_gains']
                ltcg = extracted_capital_gains['long_term_capital_gains']
                total = stcg + ltcg
                extracted_capital_gains['total_capital_gains'] = total
                
                if total != 0:
                    text_content += f"\nCALCULATED CAPITAL GAINS:\n"
                    text_content += f"Short Term Capital Gains: ₹{stcg:,.2f}\n"
                    text_content += f"Long Term Capital Gains: ₹{ltcg:,.2f}\n"
                    text_content += f"Total Capital Gains: ₹{total:,.2f}\n"
                    print(f"✅ Calculated Total Capital Gains: ₹{total:,.2f}")
                
                # Store the extracted data for post-processing
                if hasattr(self, '_extracted_capital_gains'):
                    self._extracted_capital_gains.update(extracted_capital_gains)
                else:
                    self._extracted_capital_gains = extracted_capital_gains
                
                # Clean up column names
                    section_df.columns = [str(col).strip() for col in section_df.columns]
                    
                    # Use Ollama to classify columns
                    print(f"\n🤖 Classifying columns for section: {section_name}")
                    classified_cols = self._classify_excel_columns(section_df, section_name)
                    
                    # Use classified columns
                    gain_cols = classified_cols.get('gain_cols', [])
                    date_cols = classified_cols.get('date_cols', [])
                    type_cols = classified_cols.get('type_cols', [])
                    amount_cols = classified_cols.get('amount_cols', [])
                    
                    print(f"📊 Found columns in {section_name}:")
                    print(f"   Gain columns: {gain_cols}")
                    print(f"   Date columns: {date_cols}")
                    print(f"   Type columns: {type_cols}")
                    
                    # Add section summary
                    text_content += f"Section: {section_name}\n"
                    
                    # Stock trading transaction processing
                    if any(term in section_name.lower() for term in ['intraday trades', 'short term trades', 'long term trades']):
                        print("📊 Processing stock trading transactions...")
                        
                        # Look for transaction data in this section
                        transaction_count = 0
                        total_gains = 0.0
                        total_losses = 0.0
                        
                        for idx, row in section_df.iterrows():
                            row_text = ' '.join(str(cell) for cell in row if pd.notna(cell))
                            
                            # Skip header rows
                            if any(term in row_text.lower() for term in ['stock name', 'isin', 'quantity', 'buy date']):
                                continue
                            
                            # Look for transaction data
                            if len(row) >= 9:  # Typical stock transaction has 9+ columns
                                try:
                                    # Try to extract gain/loss from the last few columns
                                    gain_loss_cols = row.iloc[-3:]  # Last 3 columns often contain P&L
                                    for col in gain_loss_cols:
                                        if pd.notna(col):
                                            try:
                                                value = float(str(col))
                                                if value > 0:
                                                    total_gains += value
                                                elif value < 0:
                                                    total_losses += abs(value)
                                                transaction_count += 1
                                                break
                                            except:
                                                continue
                                except:
                                    pass
                        
                        if transaction_count > 0:
                            net_pnl = total_gains - total_losses
                            text_content += f"Number of Transactions: {transaction_count}\n"
                            text_content += f"Total Gains: ₹{total_gains:,.2f}\n"
                            text_content += f"Total Losses: ₹{total_losses:,.2f}\n"
                            text_content += f"Net P&L: ₹{net_pnl:,.2f}\n"
                            
                            # Classify as LTCG or STCG based on section name
                            if 'long term' in section_name.lower():
                                text_content += f"Long Term Capital Gains: ₹{net_pnl:,.2f}\n"
                            elif 'short term' in section_name.lower():
                                text_content += f"Short Term Capital Gains: ₹{net_pnl:,.2f}\n"
                            elif 'intraday' in section_name.lower():
                                text_content += f"Intraday Capital Gains: ₹{net_pnl:,.2f}\n"
                
                                    # Process section if we have relevant columns
                    if any([gain_cols, type_cols, date_cols, amount_cols]):
                        print(f"\n📊 Validating capital gains data...")
                        is_valid, validation_errors, validated_data = self._validate_capital_gains_data(section_df, classified_cols)
                        
                        if validation_errors:
                            print("⚠️ Validation warnings/errors:")
                            for error in validation_errors:
                                print(f"   • {error}")
                        
                        if is_valid:
                            print("✅ Data validation passed")
                            ltcg_total = validated_data['ltcg_total']
                            stcg_total = validated_data['stcg_total']
                            total_gains = validated_data['total_gains']
                            num_transactions = validated_data['num_transactions']
                            
                            print(f"📊 Validated capital gains summary:")
                            print(f"   • LTCG: ₹{ltcg_total:,.2f}")
                            print(f"   • STCG: ₹{stcg_total:,.2f}")
                            print(f"   • Total: ₹{total_gains:,.2f}")
                            print(f"   • Valid Transactions: {num_transactions}")
                        else:
                            print("❌ Data validation failed")
                            ltcg_total = 0.0
                            stcg_total = 0.0
                            total_gains = 0.0
                
                    if type_cols and gain_cols:
                        type_col = type_cols[0]
                        gain_col = gain_cols[0]
                    
                        print(f"📊 Analyzing gains by type:")
                        print(f"   Type column: {type_col}")
                        print(f"   Gain column: {gain_col}")
                    
                        try:
                            # Clean up type values
                            section_df[type_col] = section_df[type_col].str.lower()
                            
                            # Group by type and sum gains
                            gains_by_type = section_df.groupby(type_col)[gain_col].sum()
                            
                            # Classify gains as LTCG or STCG
                            for type_name, total in gains_by_type.items():
                                if any(term in str(type_name) for term in ['long', 'ltcg', '>1y', '>12m']):
                                    ltcg_total += total
                                    print(f"   LTCG: ₹{total:,.2f} (from {type_name})")
                                elif any(term in str(type_name) for term in ['short', 'stcg', '<1y', '<12m']):
                                    stcg_total += total
                                    print(f"   STCG: ₹{total:,.2f} (from {type_name})")
                                else:
                                    print(f"   ⚠️ Unknown type '{type_name}': ₹{total:,.2f}")
                            
                            total_gains = ltcg_total + stcg_total
                            
                            # Add to text content
                            text_content += f"Long Term Capital Gains: ₹{ltcg_total:,.2f}\n"
                            text_content += f"Short Term Capital Gains: ₹{stcg_total:,.2f}\n"
                            text_content += f"Total Capital Gains: ₹{total_gains:,.2f}\n"
                            
                        except Exception as e:
                            print(f"⚠️ Error calculating gains by type: {e}")
                    else:
                        # If no type column, try to calculate total gains
                        if gain_cols:
                            try:
                                total_gains = section_df[gain_cols[0]].sum()
                                print(f"📊 Total gains (no type classification): ₹{total_gains:,.2f}")
                                text_content += f"Total Capital Gains: ₹{total_gains:,.2f}\n"
                            except Exception as e:
                                print(f"⚠️ Error calculating total gains: {e}")
                        else:
                            print("⚠️ No gain columns found")
                
                    # Count transactions
                    if date_cols:
                        num_transactions = len(section_df)
                        print(f"📊 Found {num_transactions} transactions")
                        text_content += f"Number of Transactions: {num_transactions}\n"
                    
                    # Add sample transactions if we have both date and amount columns
                    if date_cols and (gain_cols or amount_cols):
                        text_content += "\nSample Transactions:\n"
                        sample_df = section_df.head(3)
                        for _, row in sample_df.iterrows():
                            transaction = []
                            if date_cols:
                                transaction.append(f"Date: {row[date_cols[0]]}")
                            if type_cols:
                                transaction.append(f"Type: {row[type_cols[0]]}")
                            if gain_cols:
                                transaction.append(f"Gain/Loss: ₹{row[gain_cols[0]]:,.2f}")
                            elif amount_cols:
                                transaction.append(f"Amount: ₹{row[amount_cols[0]]:,.2f}")
                            text_content += "  " + ", ".join(transaction) + "\n"
                
                    else:
                        print("⚠️ No relevant columns found in this section")
                        text_content += "No relevant columns found in this section\n"
                
            else:
                # Default Excel processing
                text_content += f"Number of rows: {len(df)}\n\n"
                text_content += "Data sample (first 10 rows):\n"
                text_content += df.head(10).to_string(index=False)
                text_content += "\n\nSummary statistics:\n"
                
                # Add numerical column summaries
                numeric_cols = df.select_dtypes(include=['number']).columns
                for col in numeric_cols:
                    if col.lower() in ['amount', 'gain', 'loss', 'price', 'value', 'investment']:
                        text_content += f"{col}: Total = {df[col].sum():.2f}, Count = {df[col].count()}\n"
            
            return text_content
            
        except Exception as e:
            print(f"Error extracting Excel text: {e}")
            return ""
    
    def _analyze_with_ollama(self, filename: str, text_content: str, file_path: str = None) -> OllamaExtractedData:
        """Analyze document content with Ollama LLM"""
        try:
            # Determine document type and create specific prompt
            if "form 16" in filename.lower() or "form16" in filename.lower() or "form-16" in filename.lower():
                prompt = self._create_form16_specific_prompt(filename, text_content)
            elif "bank" in filename.lower() and "interest" in filename.lower():
                prompt = self._create_bank_interest_prompt(filename, text_content)
            elif "capital" in filename.lower() and "gains" in filename.lower():
                prompt = self._create_capital_gains_prompt(filename, text_content)
            else:
                prompt = self._create_general_prompt(filename, text_content)
            
            # Get response from Ollama
            response = self.llm.complete(prompt)
            response_text = response.text.strip()
            
            # Try to parse JSON response
            json_data = self._parse_json_response(response_text)
            
            if json_data:
                # Add file path and raw text to the data for fallback processing
                if file_path:
                    json_data['file_path'] = file_path
                json_data['raw_text'] = text_content  # Add raw text for regex fallback
                
                # Post-process Form16 data to ensure correct totals
                if json_data.get('document_type') == 'form_16':
                    # If employer name missing, try regex fallback using raw text before post-processing
                    if (not json_data.get('employer_name')) and text_content:
                        inferred_employer = self._extract_employer_name_regex(text_content)
                        if inferred_employer:
                            json_data['employer_name'] = inferred_employer
                    json_data = self._post_process_form16_data(json_data)
                
                # Post-process bank interest certificate data to ensure correct totals
                if json_data.get('document_type') == 'bank_interest_certificate':
                    json_data = self._post_process_bank_interest_data(json_data)
                
                # Post-process capital gains data to ensure correct totals
                if json_data.get('document_type') == 'capital_gains':
                    json_data = self._post_process_capital_gains_data(json_data)
                
                # Create OllamaExtractedData from JSON
                extracted_data = OllamaExtractedData(
                    document_type=json_data.get('document_type', 'unknown'),
                    confidence=float(json_data.get('confidence', 0.7)),
                    
                    employee_name=json_data.get('employee_name'),
                    pan=json_data.get('pan'),
                    employer_name=json_data.get('employer_name'),
                    gross_salary=float(json_data.get('gross_salary', 0)),
                    basic_salary=float(json_data.get('basic_salary', 0)),
                    perquisites=float(json_data.get('perquisites', 0)), # Use perquisites from JSON
                    total_gross_salary=float(json_data.get('total_gross_salary', 0)), # Use total_gross_salary from JSON
                    hra_received=float(json_data.get('hra_received', 0)),
                    special_allowance=float(json_data.get('special_allowance', 0)),
                    other_allowances=float(json_data.get('other_allowances', 0)),
                    tax_deducted=float(json_data.get('tax_deducted', 0)),
                    
                    bank_name=json_data.get('bank_name'),
                    account_number=json_data.get('account_number'),
                    interest_amount=float(json_data.get('interest_amount', 0)),
                    tds_amount=float(json_data.get('tds_amount', 0)),
                    financial_year=json_data.get('financial_year'),
                    
                    total_capital_gains=float(json_data.get('total_capital_gains', 0)),
                    long_term_capital_gains=float(json_data.get('long_term_capital_gains', 0)),
                    short_term_capital_gains=float(json_data.get('short_term_capital_gains', 0)),
                    number_of_transactions=int(json_data.get('number_of_transactions', 0)),
                    
                    epf_amount=float(json_data.get('epf_amount', 0)),
                    ppf_amount=float(json_data.get('ppf_amount', 0)),
                    life_insurance=float(json_data.get('life_insurance', 0)),
                    elss_amount=float(json_data.get('elss_amount', 0)),
                    health_insurance=float(json_data.get('health_insurance', 0)),
                    
                    raw_text=text_content[:1000],  # Store first 1000 chars
                    extraction_method="ollama_llm_full_analysis",
                    errors=[]
                )
                
                return extracted_data
            else:
                return OllamaExtractedData(
                    document_type="unknown",
                    confidence=0.0,
                    errors=["Could not parse LLM response as JSON"],
                    raw_text=text_content[:1000],
                    extraction_method="ollama_llm_failed"
                )
                
        except Exception as e:
            return OllamaExtractedData(
                document_type="unknown",
                confidence=0.0,
                errors=[f"Ollama analysis error: {str(e)}"],
                raw_text=text_content[:1000],
                extraction_method="ollama_llm_error"
            )

    def _extract_form16_perquisites_regex(self, json_data):
        """Extract perquisites and basic salary from Form12BA using regex"""
        try:
            raw_text = json_data.get('raw_text', '')
            if not raw_text:
                print("⚠️ No raw text available for perquisites extraction")
                return None
            
            print("🔍 Attempting perquisites extraction from Form12BA...")
            
            # Look for the perquisites section
            if 'Valuation of Perquisites' not in raw_text:
                print("❌ No perquisites section found in Form12BA")
                return None
            
            # Try more specific patterns based on actual structure
            # Pattern 1: Look for line 17 stock options specifically with robust number matching
            specific_perquisites_pattern = r'17\.\s*Stock options.*?(\d{6}(?:\.\d{2})?)\s*0\.00\s*(\d{6}(?:\.\d{2})?)'
            specific_match = re.search(specific_perquisites_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            
            if specific_match:
                perquisites = float(specific_match.group(2).replace(',', ''))
                print(f"✅ Found perquisites by specific pattern: ₹{perquisites:,.2f}")
                
                # Look for basic salary with exact pattern from analysis
                # Use a robust pattern that looks for the complete number (7-8 digits)
                basic_pattern = r'Income under the head Salaries.*?(\d{7,8}(?:\.\d{2})?)'
                basic_match = re.search(basic_pattern, raw_text, re.IGNORECASE | re.DOTALL)
                
                basic_salary = 0.0
                if basic_match:
                    basic_salary = float(basic_match.group(1).replace(',', ''))
                    print(f"✅ Found basic salary by specific pattern: ₹{basic_salary:,.2f}")
                
                total_gross = basic_salary + perquisites
                print(f"✅ Calculated total gross salary: ₹{total_gross:,.2f}")
                
                return {
                    'basic_salary': basic_salary,
                    'perquisites': perquisites,
                    'total_gross_salary': total_gross
                }
            
            # Try even more precise patterns
            # Look for the exact structure: "17. Stock options (non-qualified options) other than ESOP in col 16 above" followed by numbers
            precise_perquisites_pattern = r'17\.\s*Stock options \(non-qualified options\) other than ESOP in col 16\s*above\s*(\d{6}(?:\.\d{2})?)\s*0\.00\s*(\d{6}(?:\.\d{2})?)'
            precise_match = re.search(precise_perquisites_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            
            if precise_match:
                perquisites = float(precise_match.group(2).replace(',', ''))
                print(f"✅ Found perquisites by precise pattern: ₹{perquisites:,.2f}")
                
                # Look for basic salary with robust pattern
                precise_basic_pattern = r'Income under the head Salaries.*?(\d{7,8}(?:\.\d{2})?)'
                precise_basic_match = re.search(precise_basic_pattern, raw_text, re.IGNORECASE | re.DOTALL)
                
                basic_salary = 0.0
                if precise_basic_match:
                    basic_salary = float(precise_basic_match.group(1).replace(',', ''))
                    print(f"✅ Found basic salary by precise pattern: ₹{basic_salary:,.2f}")
                
                total_gross = basic_salary + perquisites
                print(f"✅ Calculated total gross salary: ₹{total_gross:,.2f}")
                
                return {
                    'basic_salary': basic_salary,
                    'perquisites': perquisites,
                    'total_gross_salary': total_gross
                }
            
            # Final attempt: Use a truly generic approach
            # Find the largest numbers in the perquisites section
            print("🔍 Using generic approach to find largest perquisites value")
            
            # Look for the perquisites section (Form12BA)
            perquisites_section_start = raw_text.find('Valuation of Perquisites')
            if perquisites_section_start != -1:
                perquisites_section = raw_text[perquisites_section_start:]
                
                # Find all numbers in the perquisites section
                numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', perquisites_section)
                
                # Convert to floats and find the largest non-zero value
                perquisites_candidates = []
                for num_str in numbers:
                    try:
                        num = float(num_str.replace(',', ''))
                        if num > 100000:  # Likely perquisites if > 1 lakh
                            perquisites_candidates.append(num)
                    except:
                        continue
                
                if perquisites_candidates:
                    perquisites = max(perquisites_candidates)
                    print(f"✅ Found perquisites by generic search: ₹{perquisites:,.2f}")
                    
                    # Look for basic salary in the main section
                    main_section = raw_text[:perquisites_section_start]
                    salary_numbers = re.findall(r'\d{1,3}(?:,\d{3})*(?:\.\d{2})?', main_section)
                    
                    basic_salary_candidates = []
                    for num_str in salary_numbers:
                        try:
                            num = float(num_str.replace(',', ''))
                            if num > 1000000:  # Likely basic salary if > 10 lakh
                                basic_salary_candidates.append(num)
                        except:
                            continue
                    
                    if basic_salary_candidates:
                        basic_salary = max(basic_salary_candidates)
                        print(f"✅ Found basic salary by generic search: ₹{basic_salary:,.2f}")
                    else:
                        basic_salary = 0.0
                    
                    total_gross = basic_salary + perquisites
                    print(f"✅ Calculated total gross salary: ₹{total_gross:,.2f}")
                    
                    return {
                        'basic_salary': basic_salary,
                        'perquisites': perquisites,
                        'total_gross_salary': total_gross
                    }
            
            # If still no perquisites found, try to find any non-zero perquisites value
            any_perquisites_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*0\.00\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            any_match = re.search(any_perquisites_pattern, raw_text)
            
            if any_match:
                # Check if the second value is significantly larger than 0 (likely perquisites)
                value1 = float(any_match.group(1).replace(',', ''))
                value2 = float(any_match.group(2).replace(',', ''))
                
                if value2 > 100000:  # Likely perquisites if > 1 lakh
                    perquisites = value2
                    print(f"✅ Found potential perquisites: ₹{perquisites:,.2f}")
                    
                    # Look for basic salary
                    basic_pattern = r'Income under the head Salaries.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
                    basic_match = re.search(basic_pattern, raw_text, re.IGNORECASE | re.DOTALL)
                    
                    basic_salary = 0.0
                    if basic_match:
                        basic_salary = float(basic_match.group(1).replace(',', ''))
                        print(f"✅ Found basic salary: ₹{basic_salary:,.2f}")
                    
                    total_gross = basic_salary + perquisites
                    print(f"✅ Calculated total gross salary: ₹{total_gross:,.2f}")
                    
                    return {
                        'basic_salary': basic_salary,
                        'perquisites': perquisites,
                        'total_gross_salary': total_gross
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Error in perquisites extraction: {str(e)}")
            return None

    def _extract_bank_interest_regex(self, json_data):
        """Extract bank interest certificate data using regex as fallback"""
        try:
            raw_text = json_data.get('raw_text', '')
            if not raw_text:
                print("⚠️ No raw text available for bank interest extraction")
                return None
            
            print("🔍 Attempting bank interest extraction with regex...")
            
            # Look for the TOTAL row pattern
            # Pattern: Total followed by numbers for Principal, Interest, Accrued, Tax
            total_pattern = r'Total\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
            total_match = re.search(total_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            
            if total_match:
                principal = float(total_match.group(1).replace(',', ''))
                interest_amount = float(total_match.group(2).replace(',', ''))
                accrued_interest = float(total_match.group(3).replace(',', ''))
                tds_amount = float(total_match.group(4).replace(',', ''))
                
                print(f"✅ Found bank interest data by regex:")
                print(f"   Principal: ₹{principal:,.2f}")
                print(f"   Interest Amount: ₹{interest_amount:,.2f}")
                print(f"   Accrued Interest: ₹{accrued_interest:,.2f}")
                print(f"   TDS Amount: ₹{tds_amount:,.2f}")
                
                # Extract bank name (usually "IT PARK" or similar)
                bank_pattern = r'Branch Name\s*\n([A-Z\s]+)'
                bank_match = re.search(bank_pattern, raw_text, re.IGNORECASE | re.DOTALL)
                bank_name = bank_match.group(1).strip() if bank_match else "Unknown"
                
                # Clean up bank name if it contains extra text
                if 'Principal' in bank_name or 'Amount' in bank_name:
                    # Look for the actual bank name in the table
                    bank_name_pattern = r'IT PARK'
                    bank_name_match = re.search(bank_name_pattern, raw_text, re.IGNORECASE)
                    if bank_name_match:
                        bank_name = bank_name_match.group(0)
                
                # Extract PAN
                pan_pattern = r'PAN:\s*([A-Z0-9]{10})'
                pan_match = re.search(pan_pattern, raw_text, re.IGNORECASE)
                pan = pan_match.group(1) if pan_match else None
                
                # Extract account number (first one found)
                account_pattern = r'(\d{12,16})'
                account_match = re.search(account_pattern, raw_text)
                account_number = account_match.group(1) if account_match else None
                
                return {
                    'bank_name': bank_name,
                    'account_number': account_number,
                    'pan': pan,
                    'interest_amount': interest_amount,
                    'tds_amount': tds_amount,
                    'principal_amount': principal,
                    'accrued_interest': accrued_interest
                }
            
            return None
            
        except Exception as e:
            print(f"❌ Error in bank interest extraction: {str(e)}")
            return None

    def _extract_capital_gains_regex(self, json_data):
        """Extract capital gains data using regex as fallback"""
        try:
            raw_text = json_data.get('raw_text', '')
            if not raw_text:
                print("⚠️ No raw text available for capital gains regex extraction")
                return None
            
            print(f"🔍 Attempting capital gains regex extraction on text length: {len(raw_text)}")
            
            # Enhanced patterns for capital gains reports (Groww format)
            patterns = {
                'short_term_capital_gains': [
                    r'Short Term P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Short Term Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'STCG[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Short Term[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'ST P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'short term p&l[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'short term[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Short Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Short Term[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Short Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Short Term[:\s]*([-+]?[\d,]+\.?\d*)'
                ],
                'long_term_capital_gains': [
                    r'Long Term P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Long Term Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'LTCG[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Long Term[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'LT P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'long term p&l[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'long term[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Long Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Long Term[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Long Term P&L[:\s]*([-+]?[\d,]+\.?\d*)',
                    r'Long Term[:\s]*([-+]?[\d,]+\.?\d*)'
                ],
                'intraday_capital_gains': [
                    r'Intraday P&L[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Intraday Capital Gains[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Intraday[:\s]*₹?([-+]?[\d,]+\.?\d*)',
                    r'Day Trading[:\s]*₹?([-+]?[\d,]+\.?\d*)'
                ],
                'dividend_income': [
                    r'Dividends[:\s]*₹?([\d,]+\.?\d*)',
                    r'Dividend Income[:\s]*₹?([\d,]+\.?\d*)',
                    r'Dividend[:\s]*₹?([\d,]+\.?\d*)'
                ],
                'total_transactions': [
                    r'Number of Transactions[:\s]*(\d+)',
                    r'Total Transactions[:\s]*(\d+)',
                    r'Transaction Count[:\s]*(\d+)',
                    r'(\d+)\s*transactions',
                    r'(\d+)\s*trades'
                ]
            }
            
            extracted_data = {}
            
            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field in ['short_term_capital_gains', 'long_term_capital_gains', 'intraday_capital_gains', 'dividend_income']:
                            try:
                                value = float(value.replace(',', ''))
                            except:
                                value = 0.0
                        elif field == 'total_transactions':
                            try:
                                value = int(value)
                            except:
                                value = 0
                        extracted_data[field] = value
                        print(f"✅ Extracted {field}: {value}")
                        break
            
            # Calculate total capital gains
            stcg = extracted_data.get('short_term_capital_gains', 0.0)
            ltcg = extracted_data.get('long_term_capital_gains', 0.0)
            intraday = extracted_data.get('intraday_capital_gains', 0.0)
            
            total_capital_gains = stcg + ltcg + intraday
            extracted_data['total_capital_gains'] = total_capital_gains
            print(f"✅ Calculated total_capital_gains: {total_capital_gains}")
            
            return extracted_data
            
        except Exception as e:
            print(f"⚠️ Error in capital gains regex extraction: {e}")
            return None

    def _post_process_form16_data(self, json_data: Dict) -> Dict:
        """Post-process Form16 data to ensure correct totals"""
        try:
            # First, try to extract perquisites from Part B
            perquisites_data = self._extract_form16_perquisites_regex(json_data)
            
            if perquisites_data:
                total_gross_salary = perquisites_data['total_gross_salary']
                perquisites = perquisites_data['perquisites']
                basic_salary = perquisites_data['basic_salary']
                
                print(f"🔄 Found perquisites data from Part B:")
                print(f"   Basic Salary: ₹{basic_salary:,.2f}")
                print(f"   Perquisites: ₹{perquisites:,.2f}")
                print(f"   Total Gross Salary: ₹{total_gross_salary:,.2f}")
                
                # Update the JSON data with perquisites information
                json_data.update(perquisites_data)
                
                # Use total_gross_salary from Part B as it includes perquisites
                current_salary = json_data.get('gross_salary', 0)
                
                if abs(current_salary - total_gross_salary) > 1000:
                    print(f"🔄 Using total_gross_salary from Part B (includes perquisites):")
                    print(f"   Quarterly total: ₹{current_salary:,.2f}")
                    print(f"   Part B total: ₹{total_gross_salary:,.2f}")
                    
                    json_data['gross_salary'] = total_gross_salary
                    json_data['extraction_method'] = 'ollama_llm_with_perquisites_correction'
            
            # Always try regex extraction for Form16 to get accurate quarterly totals
            print("🔄 Post-processing Form16: Attempting regex extraction for accuracy...")
            
            # Try regex extraction
            quarterly_data = self._extract_form16_quarterly_data_regex(json_data)
            
            if quarterly_data:
                regex_salary = quarterly_data['total_salary']
                regex_tax = quarterly_data['total_tax']
                
                # Use regex totals if they're significantly different from current totals
                current_salary = json_data.get('gross_salary', 0)
                current_tax = json_data.get('tax_deducted', 0)
                
                # If current totals are significantly off, use regex totals
                salary_diff = abs(current_salary - regex_salary)
                tax_diff = abs(current_tax - regex_tax)
                
                if salary_diff > 10000 or tax_diff > 1000:  # Significant difference threshold
                    print(f"🔄 Using regex-corrected totals:")
                    print(f"   Salary: ₹{current_salary:,.2f} → ₹{regex_salary:,.2f}")
                    print(f"   Tax: ₹{current_tax:,.2f} → ₹{regex_tax:,.2f}")
                    
                    json_data['gross_salary'] = regex_salary
                    json_data['tax_deducted'] = regex_tax
                    json_data['extraction_method'] = 'ollama_llm_with_regex_correction'
                    
                    # Also add quarterly breakdown data
                    json_data.update(quarterly_data)
                else:
                    print(f"✅ Current totals are accurate, keeping as-is")
                
                # Ensure total_gross_salary mirrors gross_salary if it's zero but quarterly total exists
                if float(json_data.get('total_gross_salary', 0) or 0) == 0 and float(json_data.get('gross_salary', 0) or 0) > 0:
                    json_data['total_gross_salary'] = float(json_data.get('gross_salary', 0) or 0)
                    json_data.setdefault('extraction_method', 'ollama_llm')
                    if not json_data['extraction_method'].endswith('_with_regex_correction'):
                        json_data['extraction_method'] += '_with_quarterly_total_fill'
            else:
                print("⚠️ Regex extraction failed, keeping current totals")
                # Still fill total_gross_salary if gross_salary is available
                if float(json_data.get('total_gross_salary', 0) or 0) == 0 and float(json_data.get('gross_salary', 0) or 0) > 0:
                    json_data['total_gross_salary'] = float(json_data.get('gross_salary', 0) or 0)
                    json_data.setdefault('extraction_method', 'ollama_llm_with_quarterly_total_fill')
            
            return json_data
            
        except Exception as e:
            print(f"⚠️ Error in post-processing: {str(e)}")
            return json_data

    def _post_process_bank_interest_data(self, json_data: Dict) -> Dict:
        """Post-process bank interest certificate data to ensure correct totals"""
        try:
            # Try regex extraction for bank interest certificate
            bank_interest_data = self._extract_bank_interest_regex(json_data)
            
            if bank_interest_data:
                regex_interest = bank_interest_data['interest_amount']
                regex_tds = bank_interest_data['tds_amount']
                
                # Use regex totals if they're significantly different from current totals
                current_interest = json_data.get('interest_amount', 0)
                current_tds = json_data.get('tds_amount', 0)
                
                # If current totals are significantly off, use regex totals
                interest_diff = abs(current_interest - regex_interest)
                tds_diff = abs(current_tds - regex_tds)
                
                if interest_diff > 100 or tds_diff > 10:  # Significant difference threshold
                    print(f"🔄 Using regex-corrected bank interest totals:")
                    print(f"   Interest: ₹{current_interest:,.2f} → ₹{regex_interest:,.2f}")
                    print(f"   TDS: ₹{current_tds:,.2f} → ₹{regex_tds:,.2f}")
                    
                    json_data['interest_amount'] = regex_interest
                    json_data['tds_amount'] = regex_tds
                    json_data['bank_name'] = bank_interest_data.get('bank_name', json_data.get('bank_name'))
                    json_data['account_number'] = bank_interest_data.get('account_number', json_data.get('account_number'))
                    json_data['pan'] = bank_interest_data.get('pan', json_data.get('pan'))
                    json_data['extraction_method'] = 'ollama_llm_with_regex_correction'
            
            return json_data
            
        except Exception as e:
            print(f"❌ Error in bank interest post-processing: {str(e)}")
            return json_data

    def _post_process_capital_gains_data(self, json_data: Dict) -> Dict:
        """Post-process capital gains data to ensure correct totals"""
        try:
            # Always try regex extraction for capital gains to get accurate totals
            print("🔄 Post-processing capital gains: Attempting regex extraction for accuracy...")
            
            capital_gains_data = self._extract_capital_gains_regex(json_data)
            
            if capital_gains_data:
                print(f"🔄 Found capital gains data from regex:")
                print(f"   Short Term Capital Gains: ₹{capital_gains_data.get('short_term_capital_gains', 0):,.2f}")
                print(f"   Long Term Capital Gains: ₹{capital_gains_data.get('long_term_capital_gains', 0):,.2f}")
                print(f"   Total Capital Gains: ₹{capital_gains_data.get('total_capital_gains', 0):,.2f}")
                print(f"   Number of Transactions: {capital_gains_data.get('total_transactions', 0)}")
                
                # Update the JSON data with regex-extracted information
                json_data.update(capital_gains_data)
                json_data['extraction_method'] = 'ollama_llm_with_capital_gains_correction'
                
                # Ensure we have the correct field names
                if 'total_transactions' in capital_gains_data:
                    json_data['number_of_transactions'] = capital_gains_data['total_transactions']
            else:
                # Try direct extraction from raw text if regex failed
                print("🔄 Regex extraction failed, trying direct text extraction...")
                raw_text = json_data.get('raw_text', '')
                if raw_text:
                    # Look for the specific patterns from your logs
                    stcg_match = re.search(r'short term p&l[:\s]*([-+]?[\d,]+\.?\d*)', raw_text, re.IGNORECASE)
                    ltcg_match = re.search(r'long term p&l[:\s]*([-+]?[\d,]+\.?\d*)', raw_text, re.IGNORECASE)
                    
                    if stcg_match:
                        try:
                            stcg_value = float(stcg_match.group(1).replace(',', ''))
                            json_data['short_term_capital_gains'] = stcg_value
                            print(f"✅ Direct extraction: Short Term Capital Gains: ₹{stcg_value:,.2f}")
                        except:
                            pass
                    
                    if ltcg_match:
                        try:
                            ltcg_value = float(ltcg_match.group(1).replace(',', ''))
                            json_data['long_term_capital_gains'] = ltcg_value
                            print(f"✅ Direct extraction: Long Term Capital Gains: ₹{ltcg_value:,.2f}")
                        except:
                            pass
                    
                    # Calculate total
                    stcg = json_data.get('short_term_capital_gains', 0.0)
                    ltcg = json_data.get('long_term_capital_gains', 0.0)
                    total = stcg + ltcg
                    json_data['total_capital_gains'] = total
                    print(f"✅ Calculated Total Capital Gains: ₹{total:,.2f}")
            
            # Also check if we have stored extracted data from section processing
            if hasattr(self, '_extracted_capital_gains'):
                stored_data = self._extracted_capital_gains
                if stored_data.get('short_term_capital_gains', 0) != 0:
                    json_data['short_term_capital_gains'] = stored_data['short_term_capital_gains']
                    print(f"✅ Using stored Short Term Capital Gains: ₹{stored_data['short_term_capital_gains']:,.2f}")
                if stored_data.get('long_term_capital_gains', 0) != 0:
                    json_data['long_term_capital_gains'] = stored_data['long_term_capital_gains']
                    print(f"✅ Using stored Long Term Capital Gains: ₹{stored_data['long_term_capital_gains']:,.2f}")
                if stored_data.get('total_capital_gains', 0) != 0:
                    json_data['total_capital_gains'] = stored_data['total_capital_gains']
                    print(f"✅ Using stored Total Capital Gains: ₹{stored_data['total_capital_gains']:,.2f}")
            
            # Add direct section name extraction as fallback
            raw_text = json_data.get('raw_text', '')
            if raw_text:
                # Look for section names with values
                stcg_section_match = re.search(r'short term p&l[:\s]*([-+]?[\d,]+\.?\d*)', raw_text, re.IGNORECASE)
                ltcg_section_match = re.search(r'long term p&l[:\s]*([-+]?[\d,]+\.?\d*)', raw_text, re.IGNORECASE)
                
                if stcg_section_match and json_data.get('short_term_capital_gains', 0) == 0:
                    try:
                        stcg_value = float(stcg_section_match.group(1).replace(',', ''))
                        json_data['short_term_capital_gains'] = stcg_value
                        print(f"✅ Section extraction: Short Term Capital Gains: ₹{stcg_value:,.2f}")
                    except:
                        pass
                
                if ltcg_section_match and json_data.get('long_term_capital_gains', 0) == 0:
                    try:
                        ltcg_value = float(ltcg_section_match.group(1).replace(',', ''))
                        json_data['long_term_capital_gains'] = ltcg_value
                        print(f"✅ Section extraction: Long Term Capital Gains: ₹{ltcg_value:,.2f}")
                    except:
                        pass
                
                # Recalculate total if we found new values
                stcg = json_data.get('short_term_capital_gains', 0.0)
                ltcg = json_data.get('long_term_capital_gains', 0.0)
                total = stcg + ltcg
                if total != 0:
                    json_data['total_capital_gains'] = total
                    print(f"✅ Final Total Capital Gains: ₹{total:,.2f}")
            
            return json_data
            
        except Exception as e:
            print(f"❌ Error in capital gains post-processing: {str(e)}")
            return json_data

    def _create_form16_specific_prompt(self, filename: str, text_content: str) -> str:
        """Create Form16-specific prompt with focus on quarterly breakdowns"""
        return f"""
You are an expert Indian Form16 analyzer. Extract ONLY the financial data from this Form16 document.

DOCUMENT: {filename}

CONTENT:
{text_content[:15000]}... (truncated if longer)

CRITICAL INSTRUCTIONS FOR FORM16:
1. Find the "Summary of amount paid/credited and tax deducted" table
2. Look for this EXACT table structure with 5 columns:
   Quarter | Receipt Number | Amount of tax deducted | Amount of tax deposited | Amount paid/credited
   Q1      | [Receipt Number] | [Tax Amount]           | [Deposited Amount]      | [Salary Amount]
   Q2      | [Receipt Number] | [Tax Amount]           | [Deposited Amount]      | [Salary Amount]
   Q3      | [Receipt Number] | [Tax Amount]           | [Deposited Amount]      | [Salary Amount]
   Q4      | [Receipt Number] | [Tax Amount]           | [Deposited Amount]      | [Salary Amount]
   Total   |                 | [Total Tax]            | [Total Deposited]       | [Total Salary]

3. Extract ALL 4 quarters (Q1, Q2, Q3, Q4) with their exact values from the document
4. SUM ALL 4 QUARTERS for total salary and total tax
5. Extract employee name, PAN, employer name

IMPORTANT - DO NOT CONFUSE SALARY WITH TAX:
- SALARY = "Amount paid/credited" (LAST COLUMN - what employee gets paid)
- TAX = "Amount of tax deducted" (3rd COLUMN - what employer deducts as TDS)
- These are DIFFERENT amounts - salary is usually much higher than tax
- Look for the actual numbers in the document, do not make up values

EXTRACT in JSON format (use exact numbers found in the document):
{{
    "document_type": "form_16",
    "confidence": 0.9,
    
    "employee_name": "EXTRACT_FROM_DOCUMENT",
    "pan": "EXTRACT_FROM_DOCUMENT", 
    "employer_name": "EXTRACT_FROM_DOCUMENT",
    "gross_salary": 0.0,  // SUM of ALL 4 quarters "Amount paid/credited" (LAST COLUMN)
    "tax_deducted": 0.0,  // SUM of ALL 4 quarters "Amount of tax deducted" (3rd COLUMN)
    
    // Quarterly breakdown (extract ALL 4 quarters with exact values from document)
    "q1_salary": 0.0,     // Q1 "Amount paid/credited" (LAST COLUMN)
    "q1_tax": 0.0,        // Q1 "Amount of tax deducted" (3rd COLUMN)
    "q2_salary": 0.0,     // Q2 "Amount paid/credited" (LAST COLUMN)
    "q2_tax": 0.0,        // Q2 "Amount of tax deducted" (3rd COLUMN)
    "q3_salary": 0.0,     // Q3 "Amount paid/credited" (LAST COLUMN)
    "q3_tax": 0.0,        // Q3 "Amount of tax deducted" (3rd COLUMN)
    "q4_salary": 0.0,     // Q4 "Amount paid/credited" (LAST COLUMN)
    "q4_tax": 0.0,        // Q4 "Amount of tax deducted" (3rd COLUMN)
    
    // Other fields (use 0 if not found)
    "basic_salary": 0.0,
    "perquisites": 0.0,
    "total_gross_salary": 0.0,
    "hra_received": 0.0,
    "special_allowance": 0.0,
    "other_allowances": 0.0,
    "espp_amount": 0.0,
    "bank_name": null,
    "interest_amount": 0.0,
    "total_capital_gains": 0.0
}}

CRITICAL RULES:
1. gross_salary = SUM of ALL 4 quarters "Amount paid/credited" (LAST COLUMN)
2. tax_deducted = SUM of ALL 4 quarters "Amount of tax deducted" (3rd COLUMN)
3. SALARY amounts are usually much larger than TAX amounts
4. Employee name is in "Name and address of the Employee" section
5. PAN is in "PAN of the Employee" section
6. Extract ONLY what you find in the document, do not use example values
7. MUST find and extract ALL 4 quarters (Q1, Q2, Q3, Q4) before calculating totals
8. Look for the exact table with Q1, Q2, Q3, Q4 rows and extract each quarter's values
9. If you cannot find the quarterly breakdown, set all quarterly values to 0

ADDITIONAL FORM16 FIELDS TO EXTRACT:
10. Look for "Basic Salary" or "Basic Pay" in the document
11. Look for "HRA" or "House Rent Allowance" in the document
12. Look for "Special Allowance" or "Special Pay" in the document
13. Look for "Other Allowances" or "Additional Allowances" in the document
14. Look for "ESPP" or "Employee Stock Purchase Plan" in the document
15. Look for "Perquisites" or "Perks" in the document
16. Extract these values with their exact amounts from the document

Respond with ONLY the JSON object, no other text or explanations.
"""

    def _extract_form16_quarterly_data_regex(self, json_data):
        """Extract quarterly data using regex as fallback"""
        try:
            raw_text = json_data.get('raw_text', '')
            file_path = json_data.get('file_path', '')
            
            if not raw_text:
                print("⚠️ No raw text available for regex extraction")
                return None
            
            print(f"🔍 Attempting regex extraction on text length: {len(raw_text)}")
            
            # Look for the quarterly table pattern
            # Pattern: Q1 QVSDURWF 334967.00 334967.00 1370780.00
            quarterly_pattern = r'Q1\s+[A-Z0-9]+\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s*Q2\s+[A-Z0-9]+\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s*Q3\s+[A-Z0-9]+\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s*Q4\s+[A-Z0-9]+\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)'
            
            match = re.search(quarterly_pattern, raw_text, re.DOTALL)
            
            if match:
                print("✅ Found quarterly data with improved pattern")
                
                # Extract values (columns are: Tax Deducted, Tax Deposited, Amount Paid/Credited)
                q1_tax = float(match.group(1).replace(',', ''))
                q1_salary = float(match.group(3).replace(',', ''))  # Amount Paid/Credited is salary
                
                q2_tax = float(match.group(4).replace(',', ''))
                q2_salary = float(match.group(6).replace(',', ''))
                
                q3_tax = float(match.group(7).replace(',', ''))
                q3_salary = float(match.group(9).replace(',', ''))
                
                q4_tax = float(match.group(10).replace(',', ''))
                q4_salary = float(match.group(12).replace(',', ''))
                
                # Validate data
                total_salary = q1_salary + q2_salary + q3_salary + q4_salary
                total_tax = q1_tax + q2_tax + q3_tax + q4_tax
                
                print(f"✅ Regex extracted quarterly data:")
                print(f"   Q1: Salary ₹{q1_salary:,.2f}, Tax ₹{q1_tax:,.2f}")
                print(f"   Q2: Salary ₹{q2_salary:,.2f}, Tax ₹{q2_tax:,.2f}")
                print(f"   Q3: Salary ₹{q3_salary:,.2f}, Tax ₹{q3_tax:,.2f}")
                print(f"   Q4: Salary ₹{q4_salary:,.2f}, Tax ₹{q4_tax:,.2f}")
                print(f"   Total: Salary ₹{total_salary:,.2f}, Tax ₹{total_tax:,.2f}")
                
                return {
                    'q1_salary': q1_salary,
                    'q1_tax': q1_tax,
                    'q2_salary': q2_salary,
                    'q2_tax': q2_tax,
                    'q3_salary': q3_salary,
                    'q3_tax': q3_tax,
                    'q4_salary': q4_salary,
                    'q4_tax': q4_tax,
                    'total_salary': total_salary,
                    'total_tax': total_tax
                }
            else:
                print("❌ No quarterly pattern found in text")
                # Try to find any Q1, Q2, Q3, Q4 patterns
                q1_match = re.search(r'Q1[^0-9]*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', raw_text)
                if q1_match:
                    print(f"Found Q1 pattern but full table not matched")
                return None
            
        except Exception as e:
            print(f"❌ Error in regex extraction: {str(e)}")
            return None

    def _create_bank_interest_prompt(self, filename: str, text_content: str) -> str:
        """Create bank interest certificate specific prompt"""
        return f"""
You are an expert Indian bank interest certificate analyzer. Extract ONLY the financial data from this document.

DOCUMENT: {filename}

CONTENT:
{text_content[:12000]}... (truncated if longer)

CRITICAL INSTRUCTIONS FOR BANK INTEREST CERTIFICATE:
1. Find the interest certificate table with columns: Deposit Number, Branch Name, Principal Amount, Interest Amount, Accrued Interest, Tax Deducted
2. Extract the TOTAL row at the bottom of the table
3. Extract bank name from "Branch Name" column
4. Extract total interest amount from "Interest Amount" column in TOTAL row
5. Extract total TDS amount from "Tax Deducted" column in TOTAL row
6. Extract PAN from the document header
7. Extract customer name from "Customer Name" field

EXTRACT in JSON format (use exact numbers found in the document):
{{
    "document_type": "bank_interest_certificate",
    "confidence": 0.85,
    
    "bank_name": "EXTRACT_FROM_BRANCH_NAME_COLUMN",
    "account_number": "EXTRACT_FROM_DEPOSIT_NUMBER_COLUMN",
    "pan": "EXTRACT_FROM_PAN_FIELD",
    "interest_amount": 0.0,  // Total from "Interest Amount" column in TOTAL row
    "tds_amount": 0.0,       // Total from "Tax Deducted" column in TOTAL row
    "financial_year": "EXTRACT_FROM_PERIOD_FIELD",
    
    // Other fields (use 0 if not found)
    "employee_name": null,
    "employer_name": null,
    "gross_salary": 0.0,
    "tax_deducted": 0.0,
    "total_capital_gains": 0.0
}}

CRITICAL RULES:
1. Extract ONLY what you find in the document
2. Do not use example values or make up numbers
3. Look for the TOTAL row at the bottom of the table
4. Interest amount is the sum of all "Interest Amount" values
5. TDS amount is the sum of all "Tax Deducted" values
6. Bank name is the "Branch Name" (usually same for all rows)
7. Account number can be any of the "Deposit Number" values

Respond with ONLY the JSON object, no other text or explanations.
"""

    def _create_capital_gains_prompt(self, filename: str, text_content: str) -> str:
        """Create capital gains specific prompt"""
        return f"""
You are an expert Indian capital gains analyzer. Extract ONLY the financial data from this document.

DOCUMENT: {filename}

CONTENT:
{text_content[:8000]}... (truncated if longer)

CRITICAL INSTRUCTIONS FOR CAPITAL GAINS:
1. Find the capital gains summary section
2. Extract total capital gains (net gains after losses)
3. Extract long-term capital gains (LTCG)
4. Extract short-term capital gains (STCG)
5. Count number of transactions
6. Extract employee name and PAN if available

EXTRACT in JSON format (use exact numbers found in the document):
{{
    "document_type": "capital_gains",
    "confidence": 0.85,
    
    "total_capital_gains": 0.0,      // Net total (gains - losses)
    "long_term_capital_gains": 0.0,  // LTCG (held > 12 months)
    "short_term_capital_gains": 0.0, // STCG (held <= 12 months)
    "number_of_transactions": 0,     // Total number of transactions
    
    "employee_name": "EXTRACT_FROM_DOCUMENT",
    "pan": "EXTRACT_FROM_DOCUMENT",
    
    // Other fields (use 0 if not found)
    "employer_name": null,
    "gross_salary": 0.0,
    "tax_deducted": 0.0,
    "bank_name": null,
    "interest_amount": 0.0
}}

CRITICAL RULES:
1. Extract ONLY what you find in the document
2. Do not use example values or make up numbers
3. Total capital gains = sum of all gains minus sum of all losses
4. LTCG = gains from assets held more than 12 months
5. STCG = gains from assets held 12 months or less
6. Count all buy/sell transactions in the period
7. Look for specific patterns like:
   - "Short Term P&L: -147459.51" → short_term_capital_gains = -147459.51
   - "Long Term P&L: 166511.16" → long_term_capital_gains = 166511.16
   - "Intraday P&L: 4" → intraday gains
   - "Dividends: 13427.85" → dividend income
8. Calculate total_capital_gains = long_term_capital_gains + short_term_capital_gains

Respond with ONLY the JSON object, no other text or explanations.
"""

    def _classify_excel_columns(self, df: pd.DataFrame, section_name: str = None) -> Dict[str, List[str]]:
        """Use Ollama to classify Excel columns based on their content"""
        try:
            # Prepare sample data for each column
            column_samples = {}
            for col in df.columns:
                # Get non-null sample values
                samples = df[col].dropna().head(5).tolist()
                if samples:
                    column_samples[str(col)] = samples
            
            # Create classification prompt
            prompt = f"""
You are an expert Indian tax document analyzer. Classify these Excel columns based on their content.

CONTEXT:
{'Section: ' + section_name if section_name else 'Excel file columns'}

COLUMNS AND SAMPLE VALUES:
{json.dumps(column_samples, indent=2)}

CLASSIFY each column into ONE of these categories:
1. GAIN_LOSS - For columns containing capital gains, profits, losses, or transaction amounts
2. DATE - For columns with dates, including purchase dates, sale dates, transaction dates
3. TYPE - For columns indicating transaction type (LTCG/STCG), holding period, or category
4. AMOUNT - For columns with monetary values like cost basis, sale proceeds
5. IDENTIFIER - For columns with names, codes, symbols, or identifiers
6. IGNORE - For columns that aren't relevant to tax calculations

CRITICAL RULES:
1. Use EXACTLY the category names listed above
2. Classify based on ACTUAL CONTENT, not column names
3. When in doubt between AMOUNT and GAIN_LOSS:
   - Use GAIN_LOSS for net gains/losses/profits
   - Use AMOUNT for raw values like purchase price, sale price
4. Dates MUST be in the sample values to classify as DATE
5. Numbers alone don't make a column AMOUNT - look for currency indicators

EXAMPLE RESPONSE:
{{
    "Purchase Date": "DATE",
    "Sale Date": "DATE",
    "Transaction Type": "TYPE",
    "Net Gain/Loss": "GAIN_LOSS",
    "Purchase Price": "AMOUNT",
    "Sale Price": "AMOUNT",
    "Symbol": "IDENTIFIER",
    "Notes": "IGNORE"
}}

RESPOND with ONLY a JSON object mapping column names to their categories. Use double quotes for all strings. No comments or explanations.
"""
            
            # Get response from Ollama
            print(f"🤖 Classifying columns using Ollama...")
            response = self.llm.complete(prompt)
            response_text = response.text.strip()
            
            # Parse JSON response
            classifications = self._parse_json_response(response_text)
            if not classifications:
                print("⚠️ Could not parse column classifications")
                return {}
            
            # Group columns by category
            categorized = {
                'gain_cols': [],
                'date_cols': [],
                'type_cols': [],
                'amount_cols': [],
                'identifier_cols': [],
            }
            
            for col, category in classifications.items():
                if category == 'GAIN_LOSS':
                    categorized['gain_cols'].append(col)
                elif category == 'DATE':
                    categorized['date_cols'].append(col)
                elif category == 'TYPE':
                    categorized['type_cols'].append(col)
                elif category == 'AMOUNT':
                    categorized['amount_cols'].append(col)
                elif category == 'IDENTIFIER':
                    categorized['identifier_cols'].append(col)
            
            print("✅ Column classification results:")
            for category, cols in categorized.items():
                if cols:
                    print(f"   {category}: {cols}")
            
            return categorized
            
        except Exception as e:
            print(f"⚠️ Error classifying columns: {str(e)}")
            return {}
    
    def _validate_capital_gains_data(self, section_df: pd.DataFrame, classified_cols: Dict[str, List[str]]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Validate capital gains data and return validation status, errors, and validated data"""
        validation_errors = []
        validated_data = {
            'ltcg_total': 0.0,
            'stcg_total': 0.0,
            'total_gains': 0.0,
            'num_transactions': 0,
            'valid_transactions': []
        }
        
        # Required columns
        gain_cols = classified_cols.get('gain_cols', [])
        date_cols = classified_cols.get('date_cols', [])
        type_cols = classified_cols.get('type_cols', [])
        amount_cols = classified_cols.get('amount_cols', [])
        
        # Basic column validation
        if not gain_cols and not amount_cols:
            validation_errors.append("No gain/amount columns found")
            return False, validation_errors, validated_data
        
        if not date_cols:
            validation_errors.append("No date columns found")
            return False, validation_errors, validated_data
        
        try:
            # Process each transaction
            for idx, row in section_df.iterrows():
                transaction = {'valid': True, 'errors': []}
                
                # Validate dates if we have purchase and sale dates
                if len(date_cols) >= 2:
                    try:
                        purchase_date = pd.to_datetime(row[date_cols[0]])
                        sale_date = pd.to_datetime(row[date_cols[1]])
                        
                        # Check date order
                        if purchase_date > sale_date:
                            transaction['errors'].append(f"Purchase date {purchase_date} is after sale date {sale_date}")
                            transaction['valid'] = False
                        
                        # Calculate holding period
                        holding_period = (sale_date - purchase_date).days
                        transaction['holding_period'] = holding_period
                        
                        # Classify as LTCG/STCG based on holding period
                        transaction['type'] = 'LTCG' if holding_period > 365 else 'STCG'
                    except Exception as e:
                        transaction['errors'].append(f"Date validation error: {str(e)}")
                        transaction['valid'] = False
                
                # Validate gain/loss amount
                if gain_cols:
                    try:
                        gain_amount = float(row[gain_cols[0]])
                        transaction['gain_amount'] = gain_amount
                        
                        # Validate against purchase and sale amounts if available
                        if len(amount_cols) >= 2:
                            purchase_amount = float(row[amount_cols[0]])
                            sale_amount = float(row[amount_cols[1]])
                            calculated_gain = sale_amount - purchase_amount
                            
                            # Check if reported gain matches calculated gain
                            if abs(calculated_gain - gain_amount) > 1:  # Allow 1 rupee difference for rounding
                                transaction['errors'].append(
                                    f"Reported gain (₹{gain_amount:,.2f}) doesn't match "
                                    f"calculated gain (₹{calculated_gain:,.2f})"
                                )
                                transaction['valid'] = False
                    except Exception as e:
                        transaction['errors'].append(f"Amount validation error: {str(e)}")
                        transaction['valid'] = False
                
                # Use explicit type if available, otherwise use holding period classification
                if type_cols:
                    try:
                        explicit_type = str(row[type_cols[0]]).lower()
                        if 'long' in explicit_type or 'ltcg' in explicit_type:
                            transaction['type'] = 'LTCG'
                        elif 'short' in explicit_type or 'stcg' in explicit_type:
                            transaction['type'] = 'STCG'
                    except Exception as e:
                        transaction['errors'].append(f"Type validation error: {str(e)}")
                        # Fall back to holding period classification if available
                
                # Add valid transaction to totals
                if transaction['valid']:
                    validated_data['num_transactions'] += 1
                    if transaction.get('gain_amount'):
                        if transaction.get('type') == 'LTCG':
                            validated_data['ltcg_total'] += transaction['gain_amount']
                        else:  # STCG
                            validated_data['stcg_total'] += transaction['gain_amount']
                else:
                    validation_errors.extend(transaction['errors'])
                
                validated_data['valid_transactions'].append(transaction)
            
            # Calculate total gains
            validated_data['total_gains'] = validated_data['ltcg_total'] + validated_data['stcg_total']
            
            # Final validation checks
            if validated_data['num_transactions'] == 0:
                validation_errors.append("No valid transactions found")
                return False, validation_errors, validated_data
            
            if validated_data['total_gains'] == 0 and validated_data['num_transactions'] > 0:
                validation_errors.append("Warning: Total gains is zero despite having transactions")
            
            return len(validation_errors) == 0, validation_errors, validated_data
            
        except Exception as e:
            validation_errors.append(f"Validation error: {str(e)}")
            return False, validation_errors, validated_data
    
    def _create_general_prompt(self, filename: str, text_content: str) -> str:
        """Create general document analysis prompt"""
        return f"""
You are an expert Indian tax document analyzer. Extract ONLY the financial data from this document.

DOCUMENT: {filename}

CONTENT:
{text_content[:8000]}... (truncated if longer)

CRITICAL INSTRUCTIONS FOR GENERAL DOCUMENT:
1. Identify the document type (investment, bank statement, etc.)
2. Extract any financial amounts found
3. Extract names, PAN, account numbers if present
4. Extract relevant dates and periods

EXTRACT in JSON format (use exact numbers found in the document):
{{
    "document_type": "investment",  // or "bank_statement", "other"
    "confidence": 0.8,
    
    "employee_name": "EXTRACT_FROM_DOCUMENT",
    "pan": "EXTRACT_FROM_DOCUMENT",
    "employer_name": "EXTRACT_FROM_DOCUMENT",
    
    // Investment related fields
    "epf_amount": 0.0,           // EPF contributions
    "ppf_amount": 0.0,           // PPF contributions
    "life_insurance": 0.0,       // Life insurance premiums
    "elss_amount": 0.0,          // ELSS investments
    "health_insurance": 0.0,     // Health insurance premiums
    
    // Other fields (use 0 if not found)
    "gross_salary": 0.0,
    "tax_deducted": 0.0,
    "bank_name": null,
    "interest_amount": 0.0,
    "total_capital_gains": 0.0
}}

CRITICAL RULES:
1. Extract ONLY what you find in the document
2. Do not use example values or make up numbers
3. Identify the document type based on content
4. Extract all relevant financial amounts
5. Look for names, PAN, account numbers in headers/footers

Respond with ONLY the JSON object, no other text or explanations.
"""
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from Ollama with improved error handling"""
        
        # Clean the response text
        response_text = response_text.strip()
        
        # Remove any leading/trailing text that's not JSON
        if response_text.startswith("I apologize") or response_text.startswith("I cannot"):
            return None
            
        # Find JSON start and end
        json_start = response_text.find('{')
        json_end = response_text.rfind('}')
        
        if json_start == -1 or json_end == -1:
            return None
            
        # Extract just the JSON part
        json_text = response_text[json_start:json_end + 1]
        
        try:
            # Parse JSON
            data = json.loads(json_text)
            
            # Clean up EXTRACT_FROM_DOCUMENT placeholders
            data = self._clean_extracted_data(data)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing error: {e}")
            print(f"📄 Response text: {response_text[:200]}...")
            
            # Try to fix common JSON issues
            try:
                # Remove comments (// ...)
                import re
                json_text = re.sub(r'//.*?$', '', json_text, flags=re.MULTILINE)
                # Remove trailing commas before closing braces/brackets
                json_text = re.sub(r',\s*([}\]])', r'\1', json_text)
                # Replace single quotes with double quotes cautiously (only in keys)
                json_text = re.sub(r"'([A-Za-z0-9_]+)'\s*:\s*", r'"\1": ', json_text)
                
                # Try parsing again
                data = json.loads(json_text)
                data = self._clean_extracted_data(data)
                return data
                
            except json.JSONDecodeError:
                # Last resort: try to extract key-value pairs manually
                return self._extract_key_value_pairs(response_text)
        
        except Exception as e:
            print(f"❌ Unexpected error parsing JSON: {e}")
            return None

    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up extracted data by converting placeholders to appropriate values"""
        cleaned = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                if value == "EXTRACT_FROM_DOCUMENT":
                    cleaned[key] = None
                else:
                    cleaned[key] = value
            elif isinstance(value, (int, float)):
                # Keep numeric values as is
                cleaned[key] = value
            else:
                cleaned[key] = value
        
        # Employer fallback from raw_text if missing
        if (not cleaned.get('employer_name')) and isinstance(cleaned.get('raw_text'), str):
            fallback = self._extract_employer_name_regex(cleaned.get('raw_text'))
            if fallback:
                cleaned['employer_name'] = fallback
        
        return cleaned

    def _extract_key_value_pairs(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract key-value pairs from text when JSON parsing fails"""
        try:
            result = {}
            
            # Look for common patterns
            patterns = [
                r'"document_type":\s*"([^"]+)"',
                r'"confidence":\s*([0-9.]+)',
                r'"employee_name":\s*"([^"]+)"',
                r'"pan":\s*"([^"]+)"',
                r'"employer_name":\s*"([^"]+)"',
                r'"gross_salary":\s*([0-9.]+)',
                r'"tax_deducted":\s*([0-9.]+)',
                r'"bank_name":\s*"([^"]+)"',
                r'"interest_amount":\s*([0-9.]+)',
                r'"total_capital_gains":\s*([0-9.]+)',
                r'"long_term_capital_gains":\s*([0-9.]+)',
                r'"short_term_capital_gains":\s*([0-9.]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    key = pattern.split('"')[1]
                    value = matches[0]
                    
                    # Convert numeric values
                    if key in ['confidence', 'gross_salary', 'tax_deducted', 'interest_amount', 
                              'total_capital_gains', 'long_term_capital_gains', 'short_term_capital_gains']:
                        try:
                            value = float(value)
                        except ValueError:
                            value = 0.0
                    
                    result[key] = value
            
            if result:
                # Set defaults for missing fields
                result.setdefault('document_type', 'unknown')
                result.setdefault('confidence', 0.7)
                return result
                
        except Exception as e:
            print(f"❌ Error in manual extraction: {e}")
        
        return None

    def _extract_employer_name_regex(self, raw_text: str) -> Optional[str]:
        """Attempt to extract employer name from raw text using regex heuristics."""
        try:
            import re
            text = raw_text or ""
            patterns = [
                r"Name\s+and\s+address\s+of\s+employer\s*[:\-]\s*(.+)",
                r"Name\s*of\s*Employer\s*[:\-]\s*(.+)",
                r"Employer\s*Name\s*[:\-]\s*(.+)",
                r"Employer\s*[:\-]\s*(.+)",
            ]
            for pat in patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    line = m.group(1).strip()
                    line = re.split(r"[\r\n]", line)[0]
                    line = re.split(r"\s{2,}|Address\s*[:\-]", line)[0].strip()
                    if 2 <= len(line) <= 200:
                        return line
            return None
        except Exception:
            return None
    
    def analyze_multiple_documents(self, file_paths: List[str]) -> List[OllamaExtractedData]:
        """Analyze multiple documents and return consolidated results"""
        
        results = []
        
        for file_path in file_paths:
            print(f"🔍 Analyzing {Path(file_path).name} with Ollama...")
            result = self.analyze_document(file_path)
            results.append(result)
            
            if result.confidence > 0.7:
                print(f"✅ Successfully extracted data from {Path(file_path).name}")
            else:
                print(f"⚠️ Low confidence extraction from {Path(file_path).name}")
        
        return results
    
    def get_summary(self, results: List[OllamaExtractedData]) -> Dict[str, Any]:
        """Generate summary of all extracted data"""
        
        summary = {
            "total_documents": len(results),
            "successful_extractions": len([r for r in results if r.confidence > 0.5]),
            "total_salary": sum(r.gross_salary for r in results),
            "total_tds": sum(r.tax_deducted + r.tds_amount for r in results),
            "total_interest": sum(r.interest_amount for r in results),
            "total_capital_gains": sum(r.total_capital_gains for r in results),
            "total_investments": sum(r.epf_amount + r.ppf_amount + r.life_insurance + r.elss_amount for r in results),
            "document_types": list(set(r.document_type for r in results if r.document_type != "unknown"))
        }
        
        return summary