import dataclasses
import logging
import os
from pathlib import Path
from typing import Any, Optional, Tuple
import signal
import time
from contextlib import contextmanager

import re
import json
import pandas as pd

from llama_index.llms.ollama import Ollama

from .pdf_extractor import extract_pdf_text
from .excel_extractor import extract_excel_text
from .regex_extractor import (
    extract_form16_perquisites_regex,
    extract_bank_interest_regex,
    extract_capital_gains_regex,
    extract_form16_quarterly_data_regex,
    extract_payslip_regex,
    preprocess_bank_interest_certificate_text,
)
from .prompts import _get_prompt_and_schema

@contextmanager
def timeout_context(seconds):
    """Context manager for setting timeouts using signals"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set up the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    
    try:
        yield
    finally:
        # Restore the old signal handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

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
    accrued_interest: float = 0.0
    raw_text: str = ""
    extraction_method: str = "ollama_llm"
    errors: Optional[list] = None
    file_path: Optional[str] = None

    def __init__(self, **kwargs):
        if kwargs.get("document_type") == "Interest Certificate":
            self.interest_amount = kwargs.get("interest_amount", 0.0)
            self.accrued_interest = kwargs.get("accrued_interest", 0.0)
            self.tds_amount = kwargs.get("tds_amount", 0.0)
        elif kwargs.get("document_type") == "nps_statement":
            self.nps_tier1_contribution = kwargs.get("nps_tier1_contribution", 0.0)
            self.nps_80ccd1b = kwargs.get("nps_80ccd1b", 0.0)
            self.nps_employer_contribution = kwargs.get("nps_employer_contribution", 0.0)

        for field in dataclasses.fields(self):
            if field.name in kwargs:
                setattr(self, field.name, kwargs[field.name])
            elif not hasattr(self, field.name):
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

    def _setup_ollama(self, model_name: str):
        for i in range(3):
            try:
                # Try host.docker.internal first (for Docker), then localhost (for native)
                base_urls = [
                    os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
                    "http://localhost:11434"
                ]
                
                ollama_llm = None
                for base_url in base_urls:
                    try:
                        ollama_llm = Ollama(
                            model=model_name,
                            base_url=base_url,
                            request_timeout=90.0,  # Reduced to 90 seconds to prevent hanging
                            temperature=0.0,
                            context_window=8192,
                            num_predict=2048
                        )
                        # Test the connection
                        ollama_llm.complete("test")
                        self.logger.info(f"Connected to Ollama at {base_url}")
                        break
                    except Exception as e:
                        self.logger.warning(f"Failed to connect to Ollama at {base_url}: {e}")
                        continue
                
                if not ollama_llm:
                    raise Exception("Could not connect to Ollama at any URL")
                
                self.logger.info(f"Ollama LLM ({model_name}) ready for document analysis.")
                return ollama_llm
                    
            except Exception as e:
                self.logger.warning(f"Could not setup Ollama with model {model_name} on attempt {i+1}: {e}")
                if i < 2:
                    time.sleep(5)  # Reduced wait time
        return None
    
    def analyze_document(self, file_path):
        """Analyze document with comprehensive timeout protection"""
        file_path = Path(file_path)
        start_time = time.time()
        
        try:
            with timeout_context(300):  # 5-minute overall timeout for entire analysis
                return self._analyze_document_internal(file_path)
        except TimeoutError as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Document analysis timed out after {elapsed:.1f}s: {file_path.name}")
            return OllamaExtractedData(
                document_type="unknown", 
                confidence=0.0, 
                errors=[f"Analysis timed out after {elapsed:.1f} seconds"],
                file_path=str(file_path)
            )
        except Exception as e:
            elapsed = time.time() - start_time
            self.logger.error(f"Document analysis failed after {elapsed:.1f}s: {e}")
            return OllamaExtractedData(
                document_type="unknown", 
                confidence=0.0, 
                errors=[f"Analysis failed: {str(e)}"],
                file_path=str(file_path)
            )

    def _analyze_document_internal(self, file_path):
        """Internal document analysis method without timeout wrapper"""
        # Don't reinitialize LLM if already available
        if not self.llm:
            self.llm = self._setup_ollama(self.model_name)
        doc_type = "unknown"
        plain_text_content = ""

        if not self.llm:
            return OllamaExtractedData(document_type="unknown", confidence=0.0, errors=["Ollama LLM not available"])
        
        # NEW: Prioritize filename-based classification for Form 16
        if "form16" in file_path.name.lower():
            doc_type = "form_16"
            print(f"DEBUG: Classified as form_16 based on filename: {file_path.name}")
        
        try:
            plain_text_content, processed_df, sections = self._extract_text_content(file_path)
            structured_text_content = plain_text_content

            # Only run Ollama for doc_type classification if not already determined by filename
            if doc_type == "unknown":
                doc_type_prompt, _ = _get_prompt_and_schema("unknown", structured_text_content)
                try:
                    with timeout_context(60):  # 60-second timeout for doc type classification
                        response = self.llm.complete(doc_type_prompt, format="json")
                    json_data_doc_type = self._parse_json_response(response.text.strip())
                    doc_type = json_data_doc_type.get("type", json_data_doc_type.get("document_type", "unknown"))
                except TimeoutError:
                    self.logger.warning(f"Document type classification timed out for {file_path.name}")
                    doc_type = "unknown"
            
            # Normalize doc_type to match internal schema keys (still useful for other types)
            if doc_type.lower() == "interest certificate":
                doc_type = "bank_interest_certificate"
            elif doc_type.lower() == "tax investment confirmation":
                doc_type = "investment"
            elif doc_type.lower() == "nps transaction statement":
                doc_type = "nps_statement"
            elif doc_type.lower() == "pay slip":
                doc_type = "payslip"
            elif doc_type.lower() == "excel file":
                # For Excel files, try to infer more specifically if it's capital gains
                if "capital_gains" in file_path.name.lower():
                    doc_type = "capital_gains"
                else:
                    doc_type = "unknown" # Fallback if not specifically capital gains
            elif doc_type.lower() == "form 16":
                doc_type = "form_16"
            elif doc_type.lower() == "document" and "form16" in file_path.name.lower():
                doc_type = "form_16" # This line becomes redundant but harmless

            prompt, schema = _get_prompt_and_schema(doc_type, structured_text_content)
            try:
                with timeout_context(120):  # 2-minute timeout for data extraction
                    response = self.llm.complete(prompt, format="json")
                self.logger.debug(f"Raw Ollama response: {response.text.strip()}")
                json_data = self._parse_json_response(response.text.strip())
                self.logger.info(f"DEBUG: Raw LLM response for data extraction: {json_data}")
            except TimeoutError:
                self.logger.error(f"Data extraction timed out for {file_path.name}")
                json_data = None
            except Exception as e:
                self.logger.error(f"Error during Ollama completion or JSON parsing: {e}", exc_info=True)
                json_data = None

            if json_data:
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
                        if json_data[field].strip() == "":
                            json_data[field] = 0.0
                        else:
                            try:
                                json_data[field] = float(json_data[field].replace(",", ""))
                            except ValueError:
                                self.logger.warning(f"Could not convert {field} '{json_data[field]}' to float.")
                                json_data[field] = 0.0

                json_data["file_path"] = str(file_path)
                json_data["raw_text"] = plain_text_content

                if doc_type.lower() in self.post_processing_functions:
                    if doc_type.lower() == "capital_gains":
                        json_data = self.post_processing_functions[doc_type.lower()](json_data, processed_df)
                    else:
                        json_data = self.post_processing_functions[doc_type.lower()](json_data)

                if doc_type == "unknown" or not json_data or (
                    (doc_type == "form_16" and (json_data.get("gross_salary", 0) == 0 and json_data.get("tax_deducted", 0) == 0)) or
                    (doc_type == "payslip" and (json_data.get("gross_salary", 0) == 0 and json_data.get("tax_deducted", 0) == 0)) or
                    (doc_type == "bank_interest_certificate" and (json_data.get("interest_amount", 0) == 0 and json_data.get("tds_amount", 0) == 0)) or
                    (doc_type == "capital_gains" and json_data.get("total_capital_gains", 0) == 0)
                ):
                    self.logger.warning(f"Ollama extraction for {doc_type} failed to get key data. Attempting regex fallback.")
                    regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
                    if regex_extracted_data:
                        json_data.update(regex_extracted_data)
                        json_data["extraction_method"] = f"ollama_llm_failed_regex_fallback_{self.model_name}"
                
                json_data["document_type"] = doc_type 
                extracted_data = OllamaExtractedData(**json_data)
                extracted_data.extraction_method = f"ollama_llm_json_{self.model_name}"
                return extracted_data

            else:
                self.logger.warning(f"Ollama returned empty JSON for {doc_type}. Attempting regex fallback.")
                regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
                if regex_extracted_data:
                    extracted_data = OllamaExtractedData(**regex_extracted_data)
                    extracted_data.extraction_method = f"ollama_llm_empty_json_regex_fallback_{self.model_name}"
                    return extracted_data
                else:
                    return OllamaExtractedData(
                        document_type="unknown", confidence=0.0, errors=["Could not parse LLM response as JSON and regex fallback failed"],
                        raw_text=plain_text_content[:1000], extraction_method=f"ollama_llm_failed_no_fallback_{self.model_name}"
                    )

        except Exception as e:
            self.logger.exception(f"Ollama analysis error: {e}. Attempting regex fallback.")
            regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
            if regex_extracted_data:
                extracted_data = OllamaExtractedData(**regex_extracted_data)
                extracted_data.extraction_method = f"ollama_llm_exception_regex_fallback_{self.model_name}"
                return extracted_data
            else:
                return OllamaExtractedData(
                    document_type="unknown", confidence=0.0, errors=[f"Ollama analysis error: {str(e)} and regex fallback failed"],
                    raw_text=plain_text_content[:1000], extraction_method=f"ollama_llm_error_no_fallback_{self.model_name}"
                )

    def _extract_text_content(self, file_path):
        file_ext = file_path.suffix.lower()
        try:
            if file_ext == ".pdf":
                combined_text, page_text = extract_pdf_text(file_path)
                return combined_text, None, page_text
            elif file_ext in [".xlsx", ".xls"]:
                text_content, processed_df, sections = extract_excel_text(file_path)
                return text_content, processed_df, sections
            else:
                return "", None, None
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return "", None, None

    def _run_regex_fallback(self, doc_type: str, json_data: dict) -> Optional[dict]:
        if doc_type == "form_16":
            return extract_form16_perquisites_regex(json_data)
        elif doc_type == "payslip":
            return extract_payslip_regex(json_data)
        elif doc_type == "bank_interest_certificate":
            return extract_bank_interest_regex(json_data)
        elif doc_type == "capital_gains":
            return extract_capital_gains_regex(json_data)
        return None

    def _post_process_form16_data(self, json_data):
        try:
            perquisites_data = extract_form16_perquisites_regex(json_data)
            if perquisites_data:
                total_gross_salary = perquisites_data["total_gross_salary"]
                perquisites = perquisites_data["perquisites"]
                basic_salary = perquisites_data["basic_salary"]
                print(f"🔄 Found perquisites data from Part B:")
                print(f"   Basic Salary: ₹{basic_salary:,.2f}")
                print(f"   Perquisites: ₹{perquisites:,.2f}")
                print(f"   Total Gross Salary: ₹{total_gross_salary:,.2f}")
                json_data.update(perquisites_data)
                current_salary = json_data.get("gross_salary", 0)
                if abs(current_salary - total_gross_salary) > 1000:
                    print(f"🔄 Using total_gross_salary from Part B (includes perquisites):")
                    print(f"   Quarterly total: ₹{current_salary:,.2f}")
                    print(f"   Part B total: ₹{total_gross_salary:,.2f}")
                    json_data["gross_salary"] = total_gross_salary
                    json_data["extraction_method"] = "ollama_llm_with_perquisites_correction"
            
            print("🔄 Post-processing Form16: Attempting regex extraction for accuracy...")
            quarterly_data = extract_form16_quarterly_data_regex(json_data)
            if quarterly_data:
                regex_salary = quarterly_data["total_salary"]
                regex_tax = quarterly_data["total_tax"]
                current_salary = json_data.get("gross_salary", 0)
                current_tax = json_data.get("tax_deducted", 0)
                salary_diff = abs(current_salary - regex_salary)
                tax_diff = abs(current_tax - regex_tax)
                if salary_diff > 10000 or tax_diff > 1000:
                    print(f"🔄 Using regex-corrected totals:")
                    print(f"   Salary: ₹{current_salary:,.2f} → ₹{regex_salary:,.2f}")
                    print(f"   Tax: ₹{current_tax:,.2f} → ₹{regex_tax:,.2f}")
                    json_data["gross_salary"] = regex_salary
                    json_data["tax_deducted"] = regex_tax
                    json_data["extraction_method"] = "ollama_llm_with_regex_correction"
                    json_data.update(quarterly_data)
                else:
                    print(f"✅ Current totals are accurate, keeping as-is")
                
                if float(json_data.get("total_gross_salary", 0) or 0) == 0 and float(json_data.get("gross_salary", 0) or 0) > 0:
                    json_data["total_gross_salary"] = float(json_data.get("gross_salary", 0) or 0)
                    json_data.setdefault("extraction_method", "ollama_llm")
                    if not json_data["extraction_method"].endswith("_with_regex_correction"):
                        json_data["extraction_method"] += "_with_quarterly_total_fill"
            else:
                print("⚠️ Regex extraction failed, keeping current totals")
                if float(json_data.get("total_gross_salary", 0) or 0) == 0 and float(json_data.get("gross_salary", 0) or 0) > 0:
                    json_data["total_gross_salary"] = float(json_data.get("gross_salary", 0) or 0)
                    json_data.setdefault("extraction_method", "ollama_llm_with_quarterly_total_fill")
            
            return json_data
        except Exception as e:
            print(f"⚠️ Error in post-processing: {str(e)}")
            return json_data

    def _post_process_payslip_data(self, json_data):
        try:
            return json_data
        except Exception as e:
            print(f"⚠️ Error in post-processing: {str(e)}")
            return json_data

    def _post_process_bank_interest_data(self, json_data):
        try:
            print("🔄 Post-processing Bank Interest data: Attempting regex extraction for accuracy...")
            bank_interest_data = extract_bank_interest_regex(json_data)
            if bank_interest_data:
                print(f"✅ Regex extracted bank interest data: {bank_interest_data}")
                # Overwrite the json_data with the more accurate regex data
                json_data.update(bank_interest_data)
                json_data["extraction_method"] = "ollama_llm_with_regex_correction"
            else:
                print("⚠️ Regex extraction for bank interest failed, keeping Ollama totals")
            return json_data
        except Exception as e:
            print(f"❌ Error in bank interest post-processing: {str(e)}")
            return json_data

    def _post_process_capital_gains_data(self, json_data, processed_df: Optional[pd.DataFrame] = None):
        try:
            if processed_df is not None and not processed_df.empty:
                stcg = 0.0
                ltcg = 0.0
                
                for col in processed_df.columns:
                    col_lower = str(col).lower()
                    # Exact matching for cleaned column names from excel_extractor
                    if 'short_term_capital_gain' == col_lower: # Corrected: added underscore # Corrected: added underscore
                        stcg += pd.to_numeric(processed_df[col], errors='coerce').sum()
                    if 'long_term_capital_gain' == col_lower: # Corrected: added underscore
                        ltcg += pd.to_numeric(processed_df[col], errors='coerce').sum()
                    # For 'realised_pl' from stocks
                    if 'realised_pl' == col_lower: # Exact match for stocks
                        # Add Realised_PL to LTCG as a general capital gain
                        ltcg += pd.to_numeric(processed_df[col], errors='coerce').sum()

                # If values were extracted from specific columns, use them
                # Prioritize values from DataFrame if extracted, otherwise use Ollama's
                if stcg == 0.0 and 'short_term_capital_gains' in json_data:
                    stcg = json_data['short_term_capital_gains']
                if ltcg == 0.0 and 'long_term_capital_gains' in json_data:
                    ltcg = json_data['long_term_capital_gains']

                json_data['short_term_capital_gains'] = stcg
                json_data['long_term_capital_gains'] = ltcg
                json_data['total_capital_gains'] = stcg + ltcg # Recalculate total based on extracted STCG/LTCG
                print(f"✅ Post-processed Capital Gains from DataFrame: STCG={stcg}, LTCG={ltcg}, Total={stcg + ltcg}")

            return json_data
        except Exception as e:
            print(f"❌ Error in capital gains post-processing: {str(e)}")
            return json_data

    def _extract_elss_investments(self, raw_text: str) -> float:
        try:
            match = re.search(r"Total amount invested in ELSS is RS ([\\d,]+\\.?\\d*)", raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',',''))
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting ELSS investments: {e}")
            return 0.0

    def _extract_nps_investments(self, raw_text: str) -> float:
        try:
            match = re.search(r"By Voluntary Contributions\s*([\\d,]+\.?\\d*)", raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',',''))
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting NPS investments: {e}")
            return 0.0

    def _parse_json_response(self, response_text: str):
        try:
            response_text = re.sub(r'^```json\n', '', response_text)
            response_text = re.sub(r'\n```$', '', response_text)
            response_text = response_text.strip()
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            self.logger.error(f"Raw response text: {response_text}")
            return None
