"""
Enhanced Ollama Document Analyzer
Uses LLM to read file contents and extract all relevant tax details directly
"""

import json
import re
from pathlib import Path
import logging
from typing import Any, Optional, Tuple
import dataclasses
import fitz  # PyMuPDF for PDF text extraction
import pandas as pd
import camelot # Import camelot for table extraction
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

@dataclasses.dataclass
class OllamaExtractedData:
    """Enhanced extracted data from Ollama analysis"""
    document_type: str = "unknown"
    confidence: float = 0.0
    employee_name: Optional[str] = None
    pan: Optional[str] = None
    employer_name: Optional[str] = None
    gross_salary: float = 0.0
    basic_salary: float = 0.0
    perquisites: float = 0.0
    total_gross_salary: float = 0.0
    hra_received: float = 0.0
    special_allowance: float = 0.0
    other_allowances: float = 0.0
    tax_deducted: float = 0.0
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    interest_amount: float = 0.0
    tds_amount: float = 0.0
    financial_year: Optional[str] = None
    total_capital_gains: float = 0.0
    long_term_capital_gains: float = 0.0
    short_term_capital_gains: float = 0.0
    number_of_transactions: int = 0
    epf_amount: float = 0.0
    ppf_amount: float = 0.0
    life_insurance: float = 0.0
    elss_amount: float = 0.0
    health_insurance: float = 0.0
    raw_text: str = ""
    extraction_method: str = "ollama_llm"
    errors: Optional[list] = None
    def __init__(self, **kwargs):
        for field in dataclasses.fields(self):
            if field.name in kwargs:
                setattr(self, field.name, kwargs[field.name])
            else:
                setattr(self, field.name, field.default)

class OllamaDocumentAnalyzer:

    def __init__(self, model: str = "llama3:8b"):
        self.model_name = model
        self.logger = logging.getLogger(__name__)
        self.llm = self._setup_ollama(model_name=self.model_name)
        self.post_processing_functions = {
            "form_16": self._post_process_form16_data,
            "payslip": self._post_process_payslip_data,
            "bank_interest_certificate": self._post_process_bank_interest_data,
            "capital_gains": self._post_process_capital_gains_data,
        }

    def _post_process_payslip_data(self, json_data):
        """Post-process payslip data to ensure correct totals"""
        try:
            payslip_data = self._extract_payslip_regex(json_data)
            if payslip_data:
                json_data.update(payslip_data)
                json_data['extraction_method'] = 'ollama_llm_with_payslip_regex_correction'
            return json_data
        except Exception as e:
            print(f"⚠️ Error in post-processing: {str(e)}")
            return json_data


    def _setup_ollama(self, model_name: str):
        """Setup Ollama LLM for document analysis"""
        try:
            ollama_llm = Ollama(
                model=model_name,
                base_url="http://localhost:11434",
                request_timeout=120.0,  # Increased timeout for larger models
                temperature=0.0,  # Set to 0 for deterministic JSON output
                context_window=8192,
                num_predict=2048
            )
            # Test the connection
            test_response = ollama_llm.complete("Hello")
            self.logger.info(f"Ollama LLM ({model_name}) ready for document analysis.")
            return ollama_llm
        except Exception as e:
            self.logger.warning(f"Could not setup Ollama with model {model_name}: {e}")
            return None
    
    def analyze_document(self, file_path):
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
            extracted_content = self._extract_text_content(file_path)
            
            structured_text_content = ""
            plain_text_content = ""

            if isinstance(extracted_content, tuple):
                structured_text_content = extracted_content[0]
                plain_text_content = extracted_content[1]
            else:
                structured_text_content = extracted_content
                plain_text_content = extracted_content # For non-PDFs, structured and plain are the same

            if not structured_text_content:
                return OllamaExtractedData(
                    document_type="unknown",
                    confidence=0.0,
                    errors=["Could not extract text content from document"]
                )
            
            # Analyze with Ollama
            extracted_data = self._analyze_with_ollama(file_path.name, structured_text_content, plain_text_content, file_path)
            
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
    
    def _extract_text_content(self, file_path):
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
    
    def _extract_pdf_text(self, file_path):
        """Extract text from PDF using PyMuPDF and tables using Camelot, preserving some layout information"""
        full_text = []
        camelot_tables_text = []

        # Set Ghostscript path for Camelot

        try:
            # Attempt to extract tables using Camelot
            # flavors: 'lattice' for tables with lines, 'stream' for tables without lines
            # pages: 'all' to extract from all pages
            # suppress_stdout: True to prevent Camelot from printing to console
            print(f"📊 Attempting Camelot table extraction from {file_path.name}...")
            tables = camelot.read_pdf(str(file_path), pages='all', flavor='lattice', suppress_stdout=True)
            if not tables:
                tables = camelot.read_pdf(str(file_path), pages='all', flavor='stream', suppress_stdout=True)

            if tables:
                print(f"✅ Camelot extracted {len(tables)} table(s).")
                for i, table in enumerate(tables):
                    # Convert table to a string format (e.g., CSV or Markdown)
                    # Using CSV for simplicity, can be changed to Markdown if preferred by LLM
                    camelot_tables_text.append(f"\n--- TABLE {i+1} ---")
                    camelot_tables_text.append(table.df.to_csv(index=False))
                    camelot_tables_text.append("\n--- END TABLE ---")
            else:
                print("❌ Camelot found no tables or failed to extract.")

        except Exception as e:
            print(f"⚠️ Error during Camelot table extraction: {e}")
            # Continue with PyMuPDF even if Camelot fails
            pass

        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc):
                full_text.append(f"\n--- Page {page_num + 1} ---")

                # Get text blocks with coordinates
                blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

                # Sort blocks by y-coordinate (top to bottom) and then by x-coordinate (left to right)
                blocks.sort(key=lambda block: (block[1], block[0]))

                current_y = -1
                for block in blocks:
                    x0, y0, x1, y1, text, block_no, block_type = block

                    if not text.strip():
                        continue

                    # Add a newline if there's a significant vertical jump (new paragraph/line)
                    if current_y == -1 or (y0 - current_y) > 15:  # Threshold for new line/paragraph
                        full_text.append("\n")

                    # Add indentation based on x-coordinate
                    indentation = " " * int(x0 / 10)  # Roughly 1 space per 10 units
                    full_text.append(f"{indentation}{text.strip()}")
                    current_y = y1
                full_text.append("\n")
            doc.close()

            # Combine PyMuPDF text and Camelot tables
            combined_text = "\n".join(full_text)
            if camelot_tables_text:
                combined_text = combined_text + "\n\n--- EXTRACTED TABLES ---" + "\n".join(camelot_tables_text)

            return combined_text

        except Exception as e:
            print(f"Error extracting PDF text with layout (PyMuPDF): {e}")
            # If PyMuPDF also fails, return only Camelot tables if any, or empty string
            if camelot_tables_text:
                return "\n".join(camelot_tables_text)
            return ""
    
    def _extract_excel_text(self, file_path):
        """Extract text representation from Excel file"""
        try:
            # For capital gains reports, we need to find the actual data section
            if any(term in file_path.name.lower() for term in ['capital', 'gains', 'profit', 'trading']):
                print("📊 Processing capital gains Excel file...")
                
                # First read without header to see the structure
                df = pd.read_excel(file_path, header=None)
                print(f"DEBUG: Raw Excel DataFrame (header=None):\n{df.to_string()}") # Add this line
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
                    
                    # Use classified columns
                    gain_cols = []
                    date_cols = []
                    type_cols = []
                    amount_cols = []
                    
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
    
    def _analyze_with_ollama(self, filename: str, structured_text_content: str, plain_text_content: str, file_path: str = None):
        """Analyze document content with Ollama LLM using structured JSON output."""
        try:
            # Determine document type and create specific prompt
            doc_type_prompt, response_schema = self._get_prompt_and_schema(filename, structured_text_content)

            if not doc_type_prompt:
                prompt = self._create_general_prompt(filename, structured_text_content)
            else:
                prompt = doc_type_prompt

            # Get response from Ollama in JSON format
            response = self.llm.complete(prompt, format="json")
            response_text = response.text.strip()
            print(f"DEBUG: Raw LLM response: {response_text}")

            # Parse the JSON response
            json_data = self._parse_json_response(response_text)

            if json_data:
                
                # Convert known numeric fields from string to float if they are strings
                numeric_fields = [
                    "gross_salary", "basic_salary", "perquisites", "total_gross_salary",
                    "hra_received", "special_allowance", "other_allowances", "tax_deducted",
                    "interest_amount", "tds_amount", "total_capital_gains",
                    "long_term_capital_gains", "short_term_capital_gains",
                    "epf_amount", "ppf_amount", "life_insurance", "elss_amount", "health_insurance",
                    "nps_tier1", "nps_1b", "nps_employer"
                ]
                for field in numeric_fields:
                    if field in json_data and isinstance(json_data[field], str):
                        try:
                            json_data[field] = float(json_data[field].replace(",", ""))
                        except ValueError:
                            self.logger.warning(f"Could not convert {field} '{json_data[field]}' to float.")
                            json_data[field] = 0.0 # Default to 0.0 on conversion error

                # Ensure document_type is set correctly based on filename if LLM fails to provide it
                if json_data.get('document_type') in [None, ""]:
                    filename_lower = filename.lower()
                    if "form 16" in filename_lower or "form16" in filename_lower:
                        json_data['document_type'] = "form_16"
                    elif "payslip" in filename_lower:
                        json_data['document_type'] = "form_16" # Treat payslips as form_16 for aggregation
                    elif "bank" in filename_lower and "interest" in filename_lower:
                        json_data['document_type'] = "bank_interest_certificate"
                    elif "capital" in filename_lower and "gains" in filename_lower:
                        json_data['document_type'] = "capital_gains"
                    elif "nps" in filename_lower or "investment" in filename_lower:
                        json_data['document_type'] = "investment"
                    else:
                        json_data['document_type'] = "unknown"

                # Add file path and raw text for fallback processing
                if file_path:
                    json_data['file_path'] = str(file_path)
                json_data['raw_text'] = plain_text_content # Use plain text for raw_text

                # Post-process data if necessary
                doc_type = json_data.get('document_type', 'unknown')
                if doc_type == 'form_16':
                    json_data = self._post_process_form16_data(json_data)
                elif doc_type == 'bank_interest_certificate':
                    json_data = self._post_process_bank_interest_data(json_data)
                elif doc_type == 'capital_gains':
                    json_data = self._post_process_capital_gains_data(json_data)

                extracted_data = OllamaExtractedData(**json_data)
                extracted_data.extraction_method = f"ollama_llm_json_{self.model_name}"
                return extracted_data

            else:
                return OllamaExtractedData(
                    document_type="unknown",
                    confidence=0.0,
                    errors=["Could not parse LLM response as JSON"],
                    raw_text=plain_text_content[:1000],
                    extraction_method=f"ollama_llm_failed_{self.model_name}"
                )

        except Exception as e:
            self.logger.exception(f"Ollama analysis error: {e}")
            return OllamaExtractedData(
                document_type="unknown",
                confidence=0.0,
                errors=[f"Ollama analysis error: {str(e)}"],
                raw_text=plain_text_content[:1000],
                extraction_method=f"ollama_llm_error_{self.model_name}"
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
            specific_perquisites_pattern = r'17\.\s*Stock options.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*0\.00\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            specific_match = re.search(specific_perquisites_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            
            if specific_match:
                perquisites = float(specific_match.group(2).replace(',', ''))
                print(f"✅ Found perquisites by specific pattern: ₹{perquisites:,.2f}")
                
                # Look for basic salary with exact pattern from analysis
                # Use a robust pattern that looks for the complete number (7-8 digits)
                basic_pattern = r'Income under the head Salaries.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
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
            precise_perquisites_pattern = r'17\.\s*Stock options \(non-qualified options\) other than ESOP in col 16\s*above\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*0\.00\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
            precise_match = re.search(precise_perquisites_pattern, raw_text, re.IGNORECASE | re.DOTALL)
            
            if precise_match:
                perquisites = float(precise_match.group(2).replace(',', ''))
                print(f"✅ Found perquisites by precise pattern: ₹{perquisites:,.2f}")
                
                # Look for basic salary with robust pattern
                precise_basic_pattern = r'Income under the head Salaries.*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
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
                        if num > 1000:  # Likely perquisites if > 1000
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
                            if num > 100000:  # Likely basic salary if > 1 lakh
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
                
                if value2 > 1000:  # Likely perquisites if > 1000
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

    def _extract_form16_quarterly_data_regex(self, json_data):
        """Extract Form16 quarterly data using regex."""
        raw_text = json_data.get('raw_text', '')
        if not raw_text:
            print("⚠️ No raw text available for quarterly data extraction")
            return None

        print("🔍 Attempting Form16 quarterly data extraction with regex...")
        quarterly_data = {}
        total_salary = 0.0
        total_tax = 0.0

        # Patterns for quarterly salary and tax (assuming Q1, Q2, Q3, Q4 structure)
        # Example: "Q1 Salary: 100000.00, Tax: 10000.00" or "Q1: Salary 100000.00 Tax 10000.00"
        quarter_patterns = {
            "Q1": r"(?:Q1|Quarter 1|1st Quarter|first quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            "Q2": r"(?:Q2|Quarter 2|2nd Quarter|second quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            "Q3": r"(?:Q3|Quarter 3|3rd Quarter|third quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
            "Q4": r"(?:Q4|Quarter 4|4th Quarter|fourth quarter)[:\s]*Salary[:\s]*₹?([\d,]+\.?\d*)[,\s]*Tax[:\s]*₹?([\d,]+\.?\d*)",
        }

        for quarter, pattern in quarter_patterns.items():
            match = re.search(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            if match:
                try:
                    salary = float(match.group(1).replace(',', ''))
                    tax = float(match.group(2).replace(',', ''))
                    quarterly_data[quarter] = {"salary": salary, "tax": tax}
                    total_salary += salary
                    total_tax += tax
                    print(f"✅ Extracted {quarter}: Salary ₹{salary:,.2f}, Tax ₹{tax:,.2f}")
                except ValueError:
                    print(f"⚠️ Could not parse numeric values for {quarter}")
                    continue

        if quarterly_data:
            print(f"✅ Total Salary from Quarterly Data: ₹{total_salary:,.2f}")
            print(f"✅ Total Tax from Quarterly Data: ₹{total_tax:,.2f}")
            return {
                'total_salary': total_salary,
                'total_tax': total_tax,
                'quarterly_breakdown': quarterly_data
            }
        else:
            print("❌ No quarterly data found using regex patterns.")
            return None

    def _extract_payslip_regex(self, json_data):
        """Extract payslip data using regex as fallback"""
        try:
            raw_text = json_data.get('raw_text', '')
            if not raw_text:
                print("⚠️ No raw text available for payslip regex extraction")
                return None

            print("🔍 Attempting payslip extraction with regex...")

            # Patterns for payslip data
            patterns = {
                'employee_name': [r'Employee Name[:\s]*([A-Za-z\s]+)'],
                'gross_salary': [r'Gross Salary[:\s]*₹?([\d,]+\.?\d*)'],
                'tax_deducted': [r'Tax Deduction[:\s]*₹?([\d,]+\.?\d*)', r'Income Tax[:\s]*₹?([\d,]+\.?\d*)'],
                'pan': [r'PAN[:\s]*([A-Z0-9]{10})'],
                'epf_amount': [r'EPF Contribution[:\s]*₹?([\d,]+\.?\d*)', r'EPF[:\s]*₹?([\d,]+\.?\d*)'],
            }

            extracted_data = {}

            for field, pattern_list in patterns.items():
                for pattern in pattern_list:
                    match = re.search(pattern, raw_text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        if field in ['gross_salary', 'tax_deducted', 'epf_amount']:
                            try:
                                value = float(value.replace(',', ''))
                            except:
                                value = 0.0
                        extracted_data[field] = value
                        print(f"✅ Extracted {field}: {value}")
                        break
            
            return extracted_data

        except Exception as e:
            print(f"❌ Error in payslip regex extraction: {str(e)}")
            return None

    def _post_process_form16_data(self, json_data):
        """Post-process Form16 data to ensure correct totals"""
        try:
            # If this is a payslip, use the payslip regex extractor
            if "payslip" in json_data.get('file_path', '').lower():
                payslip_data = self._extract_payslip_regex(json_data)
                if payslip_data:
                    json_data.update(payslip_data)
                    json_data['extraction_method'] = 'ollama_llm_with_payslip_regex_correction'
                return json_data

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

    def _post_process_bank_interest_data(self, json_data):
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

    def _post_process_capital_gains_data(self, json_data):
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

    def _get_prompt_and_schema(self, filename: str, text_content: str):
        """Determines the prompt and response schema based on the filename."""
        filename_lower = filename.lower()
        prompt = None
        schema = None

        # Base schema for all documents
        base_schema = {
            "document_type": "string",
            "confidence": "float",
            "pan": "string",
            "employee_name": "string",
        }

        if "form 16" in filename_lower or "form16" in filename_lower:
            schema = {
                **base_schema,
                "document_type": "form_16",
                "employer_name": "string",
                "gross_salary": "float",
                "tax_deducted": "float",
                "basic_salary": "float",
                "hra_received": "float",
                "special_allowance": "float",
                "other_allowances": "float",
                "perquisites": "float",
            }
            
            # Few-shot example for Form 16
            example_text = """
            PART A
            TAN of Deductor: ABCDE12345F
            Name and Address of Deductor: XYZ Corp, 123 Main St, Anytown
            PAN of Deductee: BYHPR6078P
            Name of Deductee: Rishabh Roy

            PART B
            DETAILS OF SALARY PAID AND ANY OTHER INCOME AND TAX DEDUCTED THEREON
            1. Gross Salary: 1500000.00
            2. Less: Allowances to the extent exempt u/s 10
               (a) House Rent Allowance: 100000.00
               (b) Special Allowance: 50000.00
               (c) Other Allowances: 20000.00
            3. Income chargeable under the head 'Salaries': 1330000.00
            4. Tax deducted at source: 150000.00
            """
            example_json = {
                "document_type": "form_16",
                "confidence": 0.9,
                "pan": "BYHPR6078P",
                "employee_name": "Rishabh Roy",
                "employer_name": "XYZ Corp",
                "gross_salary": 1500000.00,
                "tax_deducted": 150000.00,
                "basic_salary": 1330000.00, # Assuming this is the basic salary after allowances
                "hra_received": 100000.00,
                "special_allowance": 50000.00,
                "other_allowances": 20000.00,
                "perquisites": 0.0
            }
            
            prompt = self._create_structured_prompt_with_example(
                "Form 16", schema, text_content, example_text, json.dumps(example_json, indent=2)
            )

        elif "payslip" in filename_lower:
            schema = {
                **base_schema,
                "document_type": "form_16", # Treat payslips as form_16 for data aggregation
                "employer_name": "string",
                "gross_salary": "float",
                "tax_deducted": "float",
                "basic_salary": "float",
                "hra_received": "float",
                "special_allowance": "float",
                "other_allowances": "float",
                "perquisites": "float",
            }
            prompt = self._create_structured_prompt("Payslip", schema, text_content)

        elif "bank" in filename_lower and "interest" in filename_lower:
            schema = {
                **base_schema,
                "document_type": "bank_interest_certificate",
                "bank_name": "string",
                "account_number": "string",
                "interest_amount": "float",
                "tds_amount": "float",
                "financial_year": "string",
            }
            prompt = self._create_structured_prompt("Bank Interest Certificate", schema, text_content)

        elif "capital" in filename_lower and "gains" in filename_lower:
            schema = {
                **base_schema,
                "document_type": "capital_gains",
                "total_capital_gains": "float",
                "long_term_capital_gains": "float",
                "short_term_capital_gains": "float",
                "number_of_transactions": "integer",
            }
            prompt = self._create_structured_prompt("Capital Gains Statement", schema, text_content)

        return prompt, schema

    def _create_structured_prompt(self, doc_type: str, schema, text_content: str):
        """Creates a standardized prompt for structured JSON extraction."""
        json_schema_str = json.dumps(schema, indent=2)
        
        specific_instructions = ""
        if doc_type == "Form 16":
            specific_instructions = f"""
        For Form 16 documents, pay close attention to:
        - **PART A:** Look for TAN of Deductor, Name and Address of Deductor, PAN of Deductee, Name of Deductee.
        - **PART B:** Look for 'Details of Salary Paid' section. Extract Gross Salary, Perquisites, HRA, Special Allowance, Other Allowances.
        - Ensure to extract the correct 'Tax Deducted' amount.
        - If 'Perquisites' are not explicitly mentioned, assume 0.0.
        - Prioritize values from 'Income chargeable under the head 'Salaries'' for basic_salary if available.
        """

        return f"""
        You are an expert document analyzer for Indian financial documents.
        Your task is to extract information from the following {doc_type} document.
        Please analyze the text and respond with ONLY a valid JSON object that strictly adheres to the following schema.
        Do not include any explanations or apologies.

        TEXT TO ANALYZE:
        """
        {text_content[:15000]}  # Truncate for performance
        """

        JSON SCHEMA:
        ```json
        {json_schema_str}
        ```

        CRITICAL RULES:
        1.  Provide only the JSON object as the output.
        2.  All string values must be enclosed in double quotes.
        3.  All numerical values should be numbers (int or float), not strings. Use 0.0 or 0 if a value is not found.
        4.  If a string value (like a name or PAN) is not found, use an empty string "".
        5.  STRICTLY adhere to the provided JSON SCHEMA, including exact field names and data types.
        6.  Map extracted data to the following exact field names: `gross_salary`, `tax_deducted`, `employee_name`, `pan`, `employer_name`, `interest_amount`, `tds_amount`, `total_capital_gains`, `long_term_capital_gains`, `short_term_capital_gains`, `number_of_transactions`, `epf_amount`, `ppf_amount`, `life_insurance`, `elss_amount`, `health_insurance`.
        {specific_instructions}
        """

    def _create_structured_prompt_with_example(self, doc_type: str, schema, text_content: str, example_text: str, example_json: str):
        """Creates a standardized prompt for structured JSON extraction with a few-shot example."""
        json_schema_str = json.dumps(schema, indent=2)
        
        specific_instructions = ""
        if doc_type == "Form 16":
            specific_instructions = f"""
        For Form 16 documents, pay close attention to:
        - **PART A:** Look for TAN of Deductor, Name and Address of Deductor, PAN of Deductee, Name of Deductee.
        - **PART B:** Look for 'Details of Salary Paid' section. Extract Gross Salary, Perquisites, HRA, Special Allowance, Other Allowances.
        - Ensure to extract the correct 'Tax Deducted' amount.
        - If 'Perquisites' are not explicitly mentioned, assume 0.0.
        - Prioritize values from 'Income chargeable under the head 'Salaries'' for basic_salary if available.
        """

        return f"""
        You are an expert document analyzer for Indian financial documents.
        Your task is to extract information from the following {doc_type} document.
        Please analyze the text and respond with ONLY a valid JSON object that strictly adheres to the following schema.
        Do not include any explanations or apologies.

        HERE IS AN EXAMPLE:
        TEXT:
        """
        {example_text}
        """
        JSON:
        ```json
        {example_json}
        ```

        TEXT TO ANALYZE:
        """
        {text_content[:15000]}  # Truncate for performance
        """

        JSON SCHEMA:
        ```json
        {json_schema_str}
        ```

        CRITICAL RULES:
        1.  Provide only the JSON object as the output.
        2.  All string values must be enclosed in double quotes.
        3.  All numerical values should be numbers (int or float), not strings. Use 0.0 or 0 if a value is not found.
        4.  If a string value (like a name or PAN) is not found, use an empty string "".
        5.  STRICTLY adhere to the provided JSON SCHEMA, including exact field names and data types.
        6.  Map extracted data to the following exact field names: `gross_salary`, `tax_deducted`, `employee_name`, `pan`, `employer_name`, `interest_amount`, `tds_amount`, `total_capital_gains`, `long_term_capital_gains`, `short_term_capital_gains`, `number_of_transactions`, `epf_amount`, `ppf_amount`, `life_insurance`, `elss_amount`, `health_insurance`.
        {specific_instructions}
        """

    def _parse_json_response(self, response_text: str):
        """Parses the JSON response from the LLM."""
        try:
            # Llama3 with format='json' should return a valid JSON string.
            return json.loads(response_text)
        except json.JSONDecodeError:
            self.logger.error(f"Failed to decode JSON from LLM response: {response_text}")
            # Fallback for cases where the model might still add markdown backticks
            match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    self.logger.error("Failed to decode JSON even after stripping markdown.")
                    return None
            return None
            for category, cols in categorized.items():
                if cols:
                    print(f"   {category}: {cols}")
            
            return categorized
            
        except Exception as e:
            print(f"⚠️ Error classifying columns: {str(e)}")
            return {}
    
    
    
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
    
    def _parse_json_response(self, response_text: str):
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

    def _clean_extracted_data(self, data):
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

    def _extract_key_value_pairs(self, text: str):
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
    
    def analyze_multiple_documents(self, file_paths):
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
    
    def get_summary(self, results):
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