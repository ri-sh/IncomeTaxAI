import dataclasses
import logging
from pathlib import Path
from typing import Any, Optional, Tuple

import re
import json
import pandas as pd

from src.models.langextract_model import LangExtractModel
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
from .prompts import _get_langextract_prompt_and_examples

@dataclasses.dataclass
class ExtractedData:
    """Enhanced extracted data from analysis"""
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
    extraction_method: str = "langextract"
    errors: Optional[list] = None
    file_path: Optional[str] = None

    def __init__(self, **kwargs):
        for field in dataclasses.fields(self):
            if field.name in kwargs:
                setattr(self, field.name, kwargs[field.name])
            elif not hasattr(self, field.name):
                setattr(self, field.name, field.default)

class LangextractDocumentAnalyzer:

    def __init__(self, model: str = "llama3"):
        self.model_name = model
        self.logger = logging.getLogger(__name__)
        self.langextract_model = LangExtractModel(model_name=self.model_name)
        self.post_processing_functions = {
            "form_16": self._post_process_form16_data,
            "payslip": self._post_process_payslip_data,
            "bank_interest_certificate": self._post_process_bank_interest_data,
            "capital_gains": self._post_process_capital_gains_data,
        }

    def analyze_document(self, file_path, doc_type: str = "unknown"):
        file_path = Path(file_path)
        plain_text_content = ""

        try:
            plain_text_content, processed_df, sections = self._extract_text_content(file_path)
            
            # Data Extraction
            prompt, examples = _get_langextract_prompt_and_examples(doc_type) # Use passed doc_type
            extractions = self.langextract_model.extract_information(
                document_text=plain_text_content,
                prompt=prompt,
                examples=examples,
            )
            print(f"Raw extractions from langextract: {extractions}")

            json_data = {item['extraction_class']: item['extraction_text'] for item in extractions} if extractions else {}
            
            if json_data:
                # Post-processing and regex fallback
                if doc_type.lower() in self.post_processing_functions:
                    if doc_type.lower() == "capital_gains":
                        json_data = self.post_processing_functions[doc_type.lower()](json_data, processed_df)
                    else:
                        json_data = self.post_processing_functions[doc_type.lower()](json_data)

                # Regex Fallback
                if not json_data or self._is_extraction_incomplete(doc_type, json_data):
                    self.logger.warning(f"Langextract extraction for {doc_type} failed or is incomplete. Attempting regex fallback.")
                    regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
                    if regex_extracted_data:
                        json_data.update(regex_extracted_data)
                        json_data["extraction_method"] = f"langextract_failed_regex_fallback_{self.model_name}"

                json_data["document_type"] = doc_type
                extracted_data = ExtractedData(**json_data)
                extracted_data.extraction_method = f"langextract_{self.model_name}"
                return extracted_data
            else:
                # Regex fallback if langextract returns nothing
                regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
                if regex_extracted_data:
                    extracted_data = ExtractedData(**regex_extracted_data)
                    extracted_data.extraction_method = f"langextract_empty_regex_fallback_{self.model_name}"
                    return extracted_data
                else:
                    return ExtractedData(document_type="unknown", confidence=0.0, errors=["Could not extract data using langextract and regex fallback failed"])

        except Exception as e:
            self.logger.exception(f"Langextract analysis error: {e}")
            # Regex fallback on exception
            regex_extracted_data = self._run_regex_fallback(doc_type, {"raw_text": plain_text_content})
            if regex_extracted_data:
                extracted_data = ExtractedData(**regex_extracted_data)
                extracted_data.extraction_method = f"langextract_exception_regex_fallback_{self.model_name}"
                return extracted_data
            else:
                return ExtractedData(document_type="unknown", confidence=0.0, errors=[f"Langextract analysis error: {str(e)} and regex fallback failed"])

    def _is_extraction_incomplete(self, doc_type, json_data):
        if doc_type == "form_16" and (json_data.get("gross_salary", 0) == 0 or json_data.get("tax_deducted", 0) == 0):
            return True
        if doc_type == "bank_interest_certificate" and (json_data.get("interest_amount", 0) == 0):
            return True
        if doc_type == "capital_gains" and (json_data.get("total_capital_gains", 0) == 0):
            return True
        return False

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
                    json_data["extraction_method"] = "langextract_llm_with_perquisites_correction"
            
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
                    json_data["extraction_method"] = "langextract_llm_with_regex_correction"
                    json_data.update(quarterly_data)
                else:
                    print(f"✅ Current totals are accurate, keeping as-is")
                
                if float(json_data.get("total_gross_salary", 0) or 0) == 0 and float(json_data.get("gross_salary", 0) or 0) > 0:
                    json_data["total_gross_salary"] = float(json_data.get("gross_salary", 0) or 0)
                    json_data.setdefault("extraction_method", "langextract_llm")
                    if not json_data["extraction_method"].endswith("_with_regex_correction"):
                        json_data["extraction_method"] += "_with_quarterly_total_fill"
            else:
                print("⚠️ Regex extraction failed, keeping current totals")
                if float(json_data.get("total_gross_salary", 0) or 0) == 0 and float(json_data.get("gross_salary", 0) or 0) > 0:
                    json_data["total_gross_salary"] = float(json_data.get("gross_salary", 0) or 0)
                    json_data.setdefault("extraction_method", "langextract_llm_with_quarterly_total_fill")
            
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
                json_data["extraction_method"] = "langextract_llm_with_regex_correction"
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
            match = re.search(r"Total amount invested in ELSS is RS ([\d,]+\.?\d*)", raw_text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',',''))
            return 0.0
        except Exception as e:
            self.logger.error(f"Error extracting ELSS investments: {e}")
            return 0.0

    def _extract_nps_investments(self, raw_text: str) -> float:
        try:
            match = re.search(r"By Voluntary Contributions\s*([\d,]+\.?\d*)", raw_text, re.IGNORECASE)
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