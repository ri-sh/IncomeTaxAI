#!/usr/bin/env python3
"""
Income Tax AI Assistant - Main Application
==========================================

A comprehensive AI-powered income tax filing assistant for India.
Supports document analysis, tax calculations, and ITR form assistance.
"""

import os
import logging
import sys
import json
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer, OllamaExtractedData
from src.core.tax_calculator import TaxCalculator
from src.core.document_processor import DocumentProcessor

class IncomeTaxAssistant:
    """Main Income Tax AI Assistant Application"""
    
    def __init__(self, financial_year: str = "2024-25"):
        """Initialize the tax assistant"""
        self._ensure_logging()
        self.document_analyzer = OllamaDocumentAnalyzer()
        self.document_processor = DocumentProcessor()
        self.financial_year = financial_year
        self.tax_calculator = TaxCalculator(financial_year)
        
        # Analysis results storage
        self.analyzed_documents: List[OllamaExtractedData] = []
        self.tax_summary: Dict[str, Any] = {}
        
        print("🚀 Income Tax AI Assistant Initialized")
        print("=" * 50)

    def _ensure_logging(self) -> None:
        """Configure application logging to write to rotating log files."""
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / "app.log"

        # Avoid duplicate handlers if reinitialized in a Streamlit session
        root_logger = logging.getLogger()
        if any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
            return

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler()
            ],
        )
    
    import concurrent.futures
from multiprocessing import Pool, cpu_count

# Top-level function for multiprocessing
def _analyze_document_wrapper(file_path: str, model_name: str) -> Optional[OllamaExtractedData]:
    """Wrapper function to analyze a single document for multiprocessing.
    OllamaDocumentAnalyzer needs to be initialized within each process.
    """
    file_name = Path(file_path).name
    print(f"🔍 Worker analyzing: {file_name}")
    try:
        analyzer = OllamaDocumentAnalyzer(model=model_name)
        result = analyzer.analyze_document(file_path)
        if result:
            print(f"✅ Worker finished {file_name}: Type={result.document_type}, Confidence={result.confidence:.2f}")
        else:
            print(f"⚠️ Worker finished {file_name}: No result returned.")
        return result
    except Exception as e:
        print(f"❌ Worker error analyzing {file_name}: {e}")
        print(traceback.format_exc())
        return None

class IncomeTaxAssistant:
    """Main Income Tax AI Assistant Application"""
    
    def __init__(self, financial_year: str = "2024-25"):
        """Initialize the tax assistant"""
        self._ensure_logging()
        self.document_analyzer = None # Will be initialized in worker processes
        self.document_processor = DocumentProcessor()
        self.financial_year = financial_year
        self.tax_calculator = TaxCalculator(financial_year)
        
        # Analysis results storage
        self.analyzed_documents: List[OllamaExtractedData] = []
        self.tax_summary: Dict[str, Any] = {}
        
        print("🚀 Income Tax AI Assistant Initialized")
        print("=" * 50)

    def _ensure_logging(self) -> None:
        """Configure application logging to write to rotating log files."""
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / "app.log"

        # Avoid duplicate handlers if reinitialized in a Streamlit session
        root_logger = logging.getLogger()
        if any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
            return

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler()
            ],
        )
    
    def analyze_documents_folder(self, folder_path: str) -> List[OllamaExtractedData]:
        """Analyze all documents in a folder using parallel processing."""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"❌ Folder not found: {folder_path}")
            return []
        
        # Get all supported document files
        supported_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
        document_files = []
        
        for ext in supported_extensions:
            document_files.extend(folder.glob(f"*{ext}"))
        
        if not document_files:
            print(f"❌ No supported documents found in: {folder_path}")
            return []
        
        print(f"📁 Found {len(document_files)} documents to analyze")
        print("-" * 50)
        
        analyzed_docs = []
        start_time = datetime.now()

        # Use multiprocessing.Pool for true parallelism
        # Max processes can be adjusted based on system resources
        num_processes = cpu_count() - 1 # Use all available CPU cores - 1
        print(f"🚀 Starting parallel analysis with {num_processes} processes...")

        # Prepare arguments for the wrapper function
        # Assuming default model 'llama3:8b' for now, can be made configurable
        tasks = [(str(doc_file), "llama3:8b") for doc_file in document_files]

        with Pool(processes=num_processes) as pool:
            # pool.starmap is used because _analyze_document_wrapper takes multiple arguments
            results = pool.starmap(_analyze_document_wrapper, tasks)

        for result in results:
            if result:
                analyzed_docs.append(result)
                print(f"✅ Finished analyzing: {result.raw_text[:50]}...") # Print partial filename or identifier
                self._print_document_summary(result)
            
        end_time = datetime.now()
        time_taken = end_time - start_time
        print(f"✅ Parallel analysis completed in {time_taken}")
        
        self.analyzed_documents = analyzed_docs
        return analyzed_docs
    
    def _print_document_summary(self, doc: OllamaExtractedData):
        """Print a summary of the analyzed document"""
        print(f"   📄 Type: {doc.document_type}")
        print(f"   📊 Confidence: {doc.confidence:.2f}")
        print(f"   🔧 Method: {doc.extraction_method}")
        
        # Print key extracted data based on document type
        if doc.document_type == "form_16":
            print(f"   💰 Gross Salary: ₹{doc.gross_salary:,.2f}")
            print(f"   🧾 Tax Deducted: ₹{doc.tax_deducted:,.2f}")
            if doc.employee_name:
                print(f"   👤 Employee: {doc.employee_name}")
        
        elif doc.document_type == "bank_interest_certificate":
            bank_name = getattr(doc, 'bank_name', None) or 'Not found'
            interest_amount = getattr(doc, 'interest_amount', 0.0)
            tds_amount = getattr(doc, 'tds_amount', 0.0)
            print(f"   🏦 Bank: {bank_name}")
            print(f"   💰 Interest: ₹{interest_amount:,.2f}")
            print(f"   🧾 TDS: ₹{tds_amount:,.2f}")
        
        elif doc.document_type == "capital_gains":
            print(f"   📈 Total Gains: ₹{doc.total_capital_gains:,.2f}")
            print(f"   📊 LTCG: ₹{doc.long_term_capital_gains:,.2f}")
            print(f"   📊 STCG: ₹{doc.short_term_capital_gains:,.2f}")
        
        elif doc.document_type == "nps_statement":
            print(f"   💰 NPS Tier 1: ₹{getattr(doc, 'nps_tier1_contribution', 0.0):,.2f}")
            print(f"   💰 NPS 80CCD(1B): ₹{getattr(doc, 'nps_80ccd1b', 0.0):,.2f}")
        
        print()
    
    def calculate_tax_summary(self) -> Dict[str, Any]:
        """Calculate comprehensive tax summary from analyzed documents (grouped by FY)"""
        print("🧮 Calculating Tax Summary")
        print("-" * 50)
        
        # Group by financial year
        by_fy: Dict[str, Dict[str, float]] = {}
        def fy_key(doc) -> str:
            fy = getattr(doc, 'financial_year', None)
            if isinstance(fy, str) and fy.strip():
                # Normalize FY to YYYY-YY format
                fy = fy.strip().replace(" ", "").replace("FY", "")
                if len(fy) == 7 and fy[4] == "-": # 2024-25
                    return fy
                if len(fy) == 9 and fy[4] == "-": # 2024-2025
                    return f"{fy[:5]}{fy[7:]}"
            return self.financial_year
        
        # Aggregate data from all documents by FY (robust to doc_type variants)
        for doc in self.analyzed_documents:
            fy = fy_key(doc)
            if fy not in by_fy:
                by_fy[fy] = {
                    "total_income": 0.0,
                    "salary_income": 0.0,
                    "interest_income": 0.0,
                    "capital_gains": 0.0,
                    "total_deductions": 0.0,
                    "tax_paid": 0.0,
                }

            doc_type_raw = getattr(doc, 'document_type', '') or ''
            doc_type = doc_type_raw.lower().strip()
            doc_type_normalized = doc_type.replace(" ", "_")

            is_form16 = any(k in doc_type_normalized for k in ["form_16", "form16"])
            is_bank_interest = any(k in doc_type_normalized for k in ["bank_interest_certificate", "interest_certificate"])
            is_capital_gains = any(k in doc_type_normalized for k in ["capital_gains", "capital_gains_report"])
            is_investment = any(k in doc_type_normalized for k in ["investment", "elss_statement", "nps_transaction_statement"])

            if is_form16:
                # Use gross_salary, falling back to total_gross_salary if needed
                form16_salary = getattr(doc, 'gross_salary', 0.0)
                if (not form16_salary or form16_salary == 0.0) and hasattr(doc, 'total_gross_salary'):
                    form16_salary = getattr(doc, 'total_gross_salary', 0.0)
                by_fy[fy]["salary_income"] += form16_salary
                by_fy[fy]["tax_paid"] += getattr(doc, 'tax_deducted', 0.0)
            elif is_bank_interest:
                by_fy[fy]["interest_income"] += getattr(doc, 'interest_amount', 0.0)
                by_fy[fy]["tax_paid"] += getattr(doc, 'tds_amount', 0.0)
            elif is_capital_gains:
                by_fy[fy]["capital_gains"] += getattr(doc, 'total_capital_gains', 0.0)
            elif is_investment:
                # Aggregate 80C-like items first; NPS handled below with proper caps
                by_fy[fy]["total_deductions"] += (
                    getattr(doc, 'epf_amount', 0.0) + 
                    getattr(doc, 'ppf_amount', 0.0) + 
                    getattr(doc, 'life_insurance', 0.0) + 
                    getattr(doc, 'elss_amount', 0.0) + 
                    getattr(doc, 'health_insurance', 0.0)
                )
                # Capture NPS fields if present
                # We'll apply caps when computing old regime tax
                by_fy[fy].setdefault('nps_tier1', 0.0)
                by_fy[fy].setdefault('nps_1b', 0.0)
                by_fy[fy].setdefault('nps_employer', 0.0)
                by_fy[fy]['nps_tier1'] += getattr(doc, 'nps_tier1_contribution', 0.0)
                # Try to detect 1B amount if labeled separately; else leave 0 (user may upload specific receipt)
                by_fy[fy]['nps_1b'] += getattr(doc, 'nps_80ccd1b', 0.0)
                by_fy[fy]['nps_employer'] += getattr(doc, 'nps_employer_contribution', 0.0)
        
        # Build per-FY summaries
        result: Dict[str, Any] = {
            "by_financial_year": {},
            "documents_analyzed": len(self.analyzed_documents),
            "analysis_date": datetime.now().isoformat()
        }
        
        # Debugging print statements
        print(f"DEBUG: Aggregated data by FY: {by_fy}")

        # Build per-FY summaries
        result: Dict[str, Any] = {
            "by_financial_year": {},
            "documents_analyzed": len(self.analyzed_documents),
            "analysis_date": datetime.now().isoformat()
        }
        
        for fy, agg in by_fy.items():
            total_income = float(agg.get("salary_income", 0.0)) + float(agg.get("interest_income", 0.0)) + float(agg.get("capital_gains", 0.0))
            print(f"DEBUG: FY {fy} - Total Income: {total_income}, Salary: {agg.get('salary_income', 0.0)}, Interest: {agg.get('interest_income', 0.0)}, Capital Gains: {agg.get('capital_gains', 0.0)}")
            
            calc = TaxCalculator(fy)
            new_tax = calc.calculate_new_regime_tax(total_income) if total_income > 0 else 0.0
            
            # Apply 80C/80CCD(1)/80CCD(1B) caps for old regime
            base_80c_like = agg.get("total_deductions", 0.0)
            nps_tier1 = agg.get('nps_tier1', 0.0)
            nps_1b = agg.get('nps_1b', 0.0)
            # 80C cap 1.5L for EPF/PPF/ELSS/life insurance + 80CCD(1)
            capped_80c = min(base_80c_like + nps_tier1, 150000.0)
            # Additional 80CCD(1B) cap 50k
            capped_1b = min(nps_1b, 50000.0)
            total_deductions_old = capped_80c + capped_1b
            
            print(f"DEBUG: FY {fy} - Total Deductions (pre-cap): {base_80c_like}, NPS Tier1: {nps_tier1}, NPS 1B: {nps_1b}")
            print(f"DEBUG: FY {fy} - Capped 80C: {capped_80c}, Capped 1B: {capped_1b}, Total Deductions (old regime): {total_deductions_old}")

            old_tax = calc.calculate_old_regime_tax(total_income, total_deductions_old) if total_income > 0 else 0.0
            
            print(f"DEBUG: FY {fy} - New Regime Tax: {new_tax}, Old Regime Tax: {old_tax}")

            recommended = "new" if new_tax < old_tax else "old"
            result["by_financial_year"][fy] = {
                **agg,
                "total_income": total_income,
                "tax_liability_new_regime": new_tax,
                "tax_liability_old_regime": old_tax,
                "recommended_regime": recommended,
                "deductions_capped_80c": capped_80c,
                "deductions_80ccd1b": capped_1b,
                "total_deductions_old_regime": total_deductions_old,
            }
        
        # Backward-compatible top-level summary for selected FY (robust defaults)
        selected = result["by_financial_year"].get(self.financial_year)
        if not selected and result["by_financial_year"]:
            # Fallback to any available FY if the configured FY has no entries
            selected = next(iter(result["by_financial_year"].values()))

        if selected:
            result.update(selected)
            # Print summary for selected FY
            self._print_tax_summary(result)
        else:
            # Ensure UI-safe defaults when no documents are analyzed
            result.update({
                "total_income": 0.0,
                "salary_income": 0.0,
                "interest_income": 0.0,
                "capital_gains": 0.0,
                "total_deductions": 0.0,
                "tax_paid": 0.0,
                "tax_liability_new_regime": 0.0,
                "tax_liability_old_regime": 0.0,
                "recommended_regime": "new",
            })
        
        self.tax_summary = result
        return result
    
    def calculate_tax_summary_with_additional_data(self, rent_paid: float = 0, is_metro: bool = False) -> Dict[str, Any]:
        """Calculate tax summary with additional user inputs like rent"""
        print("🧮 Recalculating Tax Summary with Additional Data")
        print("-" * 50)
        
        # Start with base calculation
        tax_summary = self.calculate_tax_summary()
        
        # Add HRA calculation if we have salary data
        if tax_summary["salary_income"] > 0:
            # Get HRA from any available document (Form 16 or payslips)
            hra_received = 0.0
            for doc in self.analyzed_documents:
                hra_val = 0.0
                if hasattr(doc, 'hra_received') and doc.hra_received:
                    hra_val = float(doc.hra_received)
                elif hasattr(doc, 'hra') and doc.hra:
                    hra_val = float(doc.hra)
                if hra_val > hra_received:
                    hra_received = hra_val
            
            # If HRA not found in Form 16, estimate it (typically 40-50% of basic salary)
            if hra_received == 0:
                # Get basic salary from Form 16
                basic_salary = 0
                for doc in self.analyzed_documents:
                    if doc.document_type == "form_16" and hasattr(doc, 'basic_salary'):
                        basic_salary = doc.basic_salary
                        break
                
                if basic_salary == 0:
                    # Estimate basic salary as 50% of gross salary
                    basic_salary = tax_summary["salary_income"] * 0.5
                
                # Estimate HRA as 40% of basic salary (typical for non-metro)
                hra_received = basic_salary * 0.4
                print(f"🏠 Estimated HRA: ₹{hra_received:,.2f} (40% of basic salary)")
            
            # Calculate HRA exemption
            if rent_paid > 0:
                # HRA exemption calculation
                # 1. Actual HRA received
                # 2. Rent paid - 10% of basic salary
                # 3. 50% of basic salary (metro) or 40% (non-metro)
                
                # Get basic salary from Form 16
                basic_salary = 0
                for doc in self.analyzed_documents:
                    if doc.document_type == "form_16" and hasattr(doc, 'basic_salary'):
                        basic_salary = doc.basic_salary
                        break
                
                if basic_salary == 0:
                    # Estimate basic salary as 50% of gross salary
                    basic_salary = tax_summary["salary_income"] * 0.5
                
                # Calculate HRA exemption
                rent_paid_minus_10_percent = rent_paid * 12 - (basic_salary * 0.1)
                hra_exemption_percentage = 0.5 if is_metro else 0.4
                hra_exemption_amount = basic_salary * hra_exemption_percentage
                
                # Take minimum of the three
                hra_exemption = min(
                    hra_received,
                    rent_paid_minus_10_percent,
                    hra_exemption_amount
                )
                
                # Ensure HRA exemption is not negative
                hra_exemption = max(0, hra_exemption)
                
                # Add HRA exemption to deductions (old regime only)
                tax_summary["total_deductions"] += hra_exemption
                tax_summary["hra_exemption"] = hra_exemption
                tax_summary["rent_paid"] = rent_paid * 12
                tax_summary["is_metro"] = is_metro
                
                print(f"🏠 HRA Calculation:")
                print(f"   HRA Received: ₹{hra_received:,.2f}")
                print(f"   Rent Paid: ₹{rent_paid * 12:,.2f}")
                print(f"   Basic Salary: ₹{basic_salary:,.2f}")
                print(f"   HRA Exemption: ₹{hra_exemption:,.2f}")
        
        # Recalculate old regime tax with updated deductions
        if tax_summary["total_income"] > 0:
            tax_summary["tax_liability_old_regime"] = self.tax_calculator.calculate_old_regime_tax(
                tax_summary["total_income"],
                tax_summary["total_deductions"]
            )
            
            # Update regime recommendation
            if tax_summary["tax_liability_new_regime"] < tax_summary["tax_liability_old_regime"]:
                tax_summary["recommended_regime"] = "new"
            else:
                tax_summary["recommended_regime"] = "old"
        
        # Update the stored tax summary
        self.tax_summary = tax_summary
        
        print(f"✅ Tax recalculated with HRA exemption: ₹{tax_summary.get('hra_exemption', 0):,.2f}")
        return tax_summary
    
    def _print_tax_summary(self, summary: Dict[str, Any]):
        """Print the tax summary in a formatted way"""
        print("📊 TAX SUMMARY")
        print("=" * 50)
        print(f"💰 Total Income: ₹{summary['total_income']:,.2f}")
        print(f"   📄 Salary Income: ₹{summary['salary_income']:,.2f}")
        print(f"   🏦 Interest Income: ₹{summary['interest_income']:,.2f}")
        print(f"   📈 Capital Gains: ₹{summary['capital_gains']:,.2f}")
        print()
        print(f"💼 Total Deductions: ₹{summary['total_deductions']:,.2f}")
        print(f"🧾 Tax Already Paid: ₹{summary['tax_paid']:,.2f}")
        print()
        print("📋 TAX LIABILITY COMPARISON")
        print("-" * 30)
        print(f"🆕 New Regime: ₹{summary['tax_liability_new_regime']:,.2f}")
        print(f"🔄 Old Regime: ₹{summary['tax_liability_old_regime']:,.2f}")
        print()
        print(f"🎯 Recommended: {summary['recommended_regime'].upper()} Regime")
        
        # Calculate additional tax or refund
        recommended_tax = (
            summary['tax_liability_new_regime'] 
            if summary['recommended_regime'] == 'new' 
            else summary['tax_liability_old_regime']
        )
        
        additional_tax = recommended_tax - summary['tax_paid']
        
        if additional_tax > 0:
            print(f"💸 Additional Tax Due: ₹{additional_tax:,.2f}")
        else:
            print(f"💰 Tax Refund: ₹{abs(additional_tax):,.2f}")
        
        print()
    
    def generate_report(self, output_file: Optional[str] = None):
        """Generate a comprehensive tax analysis report"""
        if not self.tax_summary:
            print("❌ No tax summary available. Run calculate_tax_summary() first.")
            return
        
        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "version": "1.0",
                "documents_analyzed": len(self.analyzed_documents)
            },
            "tax_summary": self.tax_summary,
            "document_details": [
                {
                    "filename": Path(doc.file_path).name if doc.file_path else "Unknown",
                    "document_type": doc.document_type,
                    "confidence": doc.confidence,
                    "extraction_method": doc.extraction_method,
                    "key_data": self._extract_key_data(doc)
                }
                for doc in self.analyzed_documents
            ]
        }
        
        # Save report if output_file is provided
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"📄 Report saved to: {output_file}")
        else:
            print("📄 Report generated but not saved to file (no output_file specified).")
            return report # Return the report data if not saving to file
    
    def _extract_key_data(self, doc: OllamaExtractedData) -> Dict[str, Any]:
        """Extract key data from a document for the report"""
        key_data = {}
        
        if doc.document_type == "form_16":
            key_data.update({
                "gross_salary": doc.gross_salary,
                "tax_deducted": doc.tax_deducted,
                "employee_name": doc.employee_name,
                "pan": doc.pan
            })
        
        elif doc.document_type == "bank_interest_certificate":
            key_data.update({
                "interest_amount": getattr(doc, 'interest_amount', 0.0),
                "tds_amount": getattr(doc, 'tds_amount', 0.0),
                "bank_name": getattr(doc, 'bank_name', 'Not found')
            })
        
        elif doc.document_type == "capital_gains":
            key_data.update({
                "total_capital_gains": getattr(doc, 'total_capital_gains', 0.0),
                "long_term_capital_gains": getattr(doc, 'long_term_capital_gains', 0.0),
                "short_term_capital_gains": getattr(doc, 'short_term_capital_gains', 0.0)
            })
        
        elif doc.document_type == "investment":
            key_data.update({
                "epf_amount": getattr(doc, 'epf_amount', 0.0),
                "ppf_amount": getattr(doc, 'ppf_amount', 0.0),
                "elss_amount": getattr(doc, 'elss_amount', 0.0),
                "life_insurance": getattr(doc, 'life_insurance', 0.0),
                "health_insurance": getattr(doc, 'health_insurance', 0.0)
            })
        
        return key_data
    
    def run_interactive_mode(self):
        """Run the assistant in interactive mode"""
        print("🎯 Income Tax AI Assistant - Interactive Mode")
        print("=" * 60)
        
        while True:
            print("\n📋 Available Options:")
            print("1. 📁 Analyze documents from folder")
            print("2. 🧮 Calculate tax summary")
            print("3. 📄 Generate report")
            print("4. 📊 Show current analysis")
            print("5. 🚪 Exit")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                folder_path = input("Enter folder path: ").strip()
                if folder_path:
                    self.analyze_documents_folder(folder_path)
            
            elif choice == "2":
                if self.analyzed_documents:
                    self.calculate_tax_summary()
                else:
                    print("❌ No documents analyzed. Please analyze documents first.")
            
            elif choice == "3":
                if self.tax_summary:
                    print("Generating report (will not be saved to file by default).")
                    self.generate_report()
                else:
                    print("❌ No tax summary available. Please calculate tax summary first.")
            
            elif choice == "4":
                if self.analyzed_documents:
                    print(f"\n📊 Current Analysis Status:")
                    print(f"   Documents analyzed: {len(self.analyzed_documents)}")
                    for i, doc in enumerate(self.analyzed_documents, 1):
                        print(f"   {i}. {doc.document_type} (confidence: {doc.confidence:.2f})")
                else:
                    print("❌ No documents analyzed yet.")
            
            elif choice == "5":
                print("👋 Thank you for using Income Tax AI Assistant!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-5.")


def main():
    """Main entry point"""
    assistant = IncomeTaxAssistant()
    
    # Check if running in interactive mode or with command line arguments
    if len(sys.argv) > 1:
        # Command line mode
        if sys.argv[1] == "--folder" and len(sys.argv) > 2:
            folder_path = sys.argv[2]
            assistant.analyze_documents_folder(folder_path)
            assistant.calculate_tax_summary()
            assistant.generate_report()
        else:
            print("Usage: python main.py --folder <folder_path>")
    else:
        # Interactive mode
        assistant.run_interactive_mode()


if __name__ == "__main__":
    main() 