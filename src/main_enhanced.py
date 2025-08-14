#!/usr/bin/env python3
"""
Enhanced Income Tax AI Assistant - Main Application with Web Support
===================================================================

A comprehensive AI-powered income tax filing assistant for India.
Supports both CLI and web interface modes with JSON output.
"""

import os
import logging
import sys
import json
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from multiprocessing import Pool, cpu_count
import concurrent.futures

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer, OllamaExtractedData
from src.core.document_processing.langextract_analyzer import LangextractDocumentAnalyzer
from src.core.tax_calculator import TaxCalculator
from src.core.document_processor import DocumentProcessor

class EnhancedIncomeTaxAssistant:
    """Enhanced Income Tax AI Assistant with Web Support"""
    
    def __init__(self, financial_year: str = "2024-25", analyzer=None, output_format="cli"):
        """Initialize the tax assistant"""
        self._ensure_logging()
        self.document_analyzer = analyzer
        self.document_processor = DocumentProcessor()
        self.financial_year = financial_year
        self.tax_calculator = TaxCalculator(financial_year)
        self.output_format = output_format
        
        # Analysis results storage
        self.analyzed_documents: List[Any] = []
        self.tax_summary: Dict[str, Any] = {}
        
        if output_format == "cli":
            print("🚀 Enhanced Income Tax AI Assistant Initialized")
            print("=" * 50)

    def _ensure_logging(self) -> None:
        """Configure application logging to write to rotating log files."""
        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        log_file = logs_dir / "app.log"

        # Avoid duplicate handlers if reinitialized
        root_logger = logging.getLogger()
        if any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
            return

        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        logging.basicConfig(
            level=getattr(logging, log_level, logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.FileHandler(log_file, encoding="utf-8"),
                logging.StreamHandler() if self.output_format == "cli" else logging.NullHandler()
            ],
        )
    
    def analyze_documents_folder(self, folder_path: str) -> List[Any]:
        """Analyze all documents in a folder using the selected analyzer."""
        folder = Path(folder_path)
        
        if not folder.exists():
            if self.output_format == "cli":
                print(f"❌ Folder not found: {folder_path}")
            return []
        
        supported_extensions = ['.pdf', '.xlsx', '.xls', '.csv']
        document_files = []
        
        for ext in supported_extensions:
            document_files.extend(folder.glob(f"*{ext}"))
        
        if not document_files:
            if self.output_format == "cli":
                print(f"❌ No supported documents found in: {folder_path}")
            return []
        
        if self.output_format == "cli":
            print(f"📁 Found {len(document_files)} documents to analyze")
            print("-" * 50)
        
        analyzed_docs = []
        start_time = datetime.now()

        for doc_file in document_files:
            try:
                # Estimate document type
                file_content = self.document_processor.extract_text_content(str(doc_file))
                estimated_doc_type = self.document_processor._estimate_document_type(file_content, doc_file.name)

                result = self.document_analyzer.analyze_document(str(doc_file), doc_type=estimated_doc_type)
                if result:
                    analyzed_docs.append(result)
                    if self.output_format == "cli":
                        self._print_document_summary(result)
            except Exception as e:
                logging.error(f"Error analyzing {doc_file.name}: {e}")
                if self.output_format == "cli":
                    print(f"⚠️ Error analyzing {doc_file.name}: {e}")
            
        end_time = datetime.now()
        time_taken = end_time - start_time
        
        if self.output_format == "cli":
            print(f"✅ Analysis completed in {time_taken}")
        
        self.analyzed_documents = analyzed_docs
        return analyzed_docs
    
    def _print_document_summary(self, doc):
        """Print a summary of the analyzed document (CLI mode only)"""
        if self.output_format != "cli":
            return
            
        print(f"   📄 Type: {doc.document_type}")
        print(f"   📊 Confidence: {getattr(doc, 'confidence', 0.0):.2f}")
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
    
    def calculate_enhanced_tax_summary(self) -> Dict[str, Any]:
        """Calculate comprehensive tax summary with enhanced web-friendly output"""
        if self.output_format == "cli":
            print("🧮 Calculating Enhanced Tax Summary")
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
        
        # Enhanced data aggregation with detailed breakdown
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
                    "hra_received": 0.0,
                    "hra_exemption": 0.0,
                }

            doc_type_raw = getattr(doc, 'document_type', '') or ''
            doc_type = doc_type_raw.lower().strip()
            doc_type_normalized = doc_type.replace(" ", "_")

            # Enhanced classification
            is_form16 = any(k in doc_type_normalized for k in ["form_16", "form16"])
            is_bank_interest = any(k in doc_type_normalized for k in ["bank_interest_certificate", "interest_certificate"])
            is_capital_gains = any(k in doc_type_normalized for k in ["capital_gains", "capital_gains_report"])
            is_investment = any(k in doc_type_normalized for k in ["investment", "elss_statement", "nps_transaction_statement"])

            if is_form16:
                # Extract more detailed salary information
                form16_salary = getattr(doc, 'gross_salary', 0.0)
                if (not form16_salary or form16_salary == 0.0) and hasattr(doc, 'total_gross_salary'):
                    form16_salary = getattr(doc, 'total_gross_salary', 0.0)
                
                by_fy[fy]["salary_income"] += form16_salary
                by_fy[fy]["tax_paid"] += getattr(doc, 'tax_deducted', 0.0)
                
                # Extract HRA information if available
                hra_received = getattr(doc, 'hra_received', 0.0)
                hra_exemption = getattr(doc, 'hra_exemption', 0.0)
                by_fy[fy]["hra_received"] += hra_received
                by_fy[fy]["hra_exemption"] += hra_exemption
                
            elif is_bank_interest:
                by_fy[fy]["interest_income"] += getattr(doc, 'interest_amount', 0.0)
                by_fy[fy]["tax_paid"] += getattr(doc, 'tds_amount', 0.0)
                
            elif is_capital_gains:
                by_fy[fy]["capital_gains"] += getattr(doc, 'total_capital_gains', 0.0)
                
            elif is_investment:
                # Enhanced investment tracking
                by_fy[fy]["total_deductions"] += (
                    getattr(doc, 'epf_amount', 0.0) + 
                    getattr(doc, 'ppf_amount', 0.0) + 
                    getattr(doc, 'life_insurance', 0.0) + 
                    getattr(doc, 'elss_amount', 0.0) + 
                    getattr(doc, 'health_insurance', 0.0)
                )
                
                # Enhanced NPS tracking
                by_fy[fy].setdefault('nps_tier1', 0.0)
                by_fy[fy].setdefault('nps_1b', 0.0)
                by_fy[fy].setdefault('nps_employer', 0.0)
                by_fy[fy]['nps_tier1'] += getattr(doc, 'nps_tier1_contribution', 0.0)
                by_fy[fy]['nps_1b'] += getattr(doc, 'nps_80ccd1b', 0.0)
                by_fy[fy]['nps_employer'] += getattr(doc, 'nps_employer_contribution', 0.0)
        
        # Build comprehensive results
        result: Dict[str, Any] = {
            "by_financial_year": {},
            "documents_analyzed": len(self.analyzed_documents),
            "analysis_date": datetime.now().isoformat(),
            "enhanced_features": {
                "hra_analysis": True,
                "regime_comparison": True,
                "deduction_optimization": True,
                "savings_projection": True
            }
        }
        
        for fy, agg in by_fy.items():
            # Enhanced income calculation with HRA considerations
            gross_income = float(agg.get("salary_income", 0.0)) + float(agg.get("interest_income", 0.0)) + float(agg.get("capital_gains", 0.0))
            hra_exemption = float(agg.get("hra_exemption", 0.0))
            net_income_after_hra = gross_income - hra_exemption
            
            calc = TaxCalculator(fy)
            
            # Enhanced tax calculations
            new_tax = calc.calculate_new_regime_tax(net_income_after_hra) if net_income_after_hra > 0 else 0.0
            
            # Apply caps for old regime with enhanced deductions
            base_80c_like = agg.get("total_deductions", 0.0)
            nps_tier1 = agg.get('nps_tier1', 0.0)
            nps_1b = agg.get('nps_1b', 0.0)
            
            capped_80c = min(base_80c_like + nps_tier1, 150000.0)
            capped_1b = min(nps_1b, 50000.0)
            total_deductions_old = capped_80c + capped_1b
            
            old_tax = calc.calculate_old_regime_tax(net_income_after_hra, total_deductions_old) if net_income_after_hra > 0 else 0.0
            
            # Enhanced recommendation logic
            recommended = "new" if new_tax < old_tax else "old"
            savings = abs(old_tax - new_tax)
            
            # Additional tax or refund calculation
            tax_paid = agg.get("tax_paid", 0.0)
            old_additional = old_tax - tax_paid
            new_additional = new_tax - tax_paid
            
            result["by_financial_year"][fy] = {
                **agg,
                "gross_total_income": gross_income,
                "hra_exemption_applied": hra_exemption,
                "net_income_after_hra": net_income_after_hra,
                "tax_liability_new_regime": new_tax,
                "tax_liability_old_regime": old_tax,
                "recommended_regime": recommended,
                "potential_savings": savings,
                "deductions_capped_80c": capped_80c,
                "deductions_80ccd1b": capped_1b,
                "total_deductions_old_regime": total_deductions_old,
                "additional_tax_old_regime": old_additional,
                "additional_tax_new_regime": new_additional,
                "optimization_score": self._calculate_optimization_score(agg, total_deductions_old, gross_income),
                "next_steps": self._generate_next_steps(recommended, old_additional, new_additional)
            }
        
        # Select current FY data for top-level summary
        selected = result["by_financial_year"].get(self.financial_year)
        if not selected and result["by_financial_year"]:
            selected = next(iter(result["by_financial_year"].values()))

        if selected:
            result.update(selected)
            if self.output_format == "cli":
                self._print_enhanced_tax_summary(result)
        else:
            # UI-safe defaults
            result.update({
                "gross_total_income": 0.0,
                "salary_income": 0.0,
                "interest_income": 0.0,
                "capital_gains": 0.0,
                "total_deductions": 0.0,
                "tax_paid": 0.0,
                "tax_liability_new_regime": 0.0,
                "tax_liability_old_regime": 0.0,
                "recommended_regime": "new",
                "potential_savings": 0.0,
            })
        
        self.tax_summary = result
        return result
    
    def _calculate_optimization_score(self, agg: Dict[str, float], total_deductions: float, gross_income: float) -> float:
        """Calculate tax optimization score (0-100)"""
        score = 0.0
        
        # Deduction utilization (max 40 points)
        max_deductions = 200000.0  # 150k + 50k NPS
        deduction_ratio = min(total_deductions / max_deductions, 1.0)
        score += deduction_ratio * 40
        
        # HRA utilization (max 20 points)
        hra_exemption = agg.get('hra_exemption', 0.0)
        if hra_exemption > 0:
            score += 20
        
        # Investment diversity (max 20 points)
        investment_types = 0
        if agg.get('epf_amount', 0) > 0: investment_types += 1
        if agg.get('ppf_amount', 0) > 0: investment_types += 1
        if agg.get('elss_amount', 0) > 0: investment_types += 1
        if agg.get('nps_tier1', 0) > 0: investment_types += 1
        if agg.get('health_insurance', 0) > 0: investment_types += 1
        
        score += (investment_types / 5.0) * 20
        
        # Income management (max 20 points)
        if gross_income > 0:
            tax_efficiency = (total_deductions + hra_exemption) / gross_income
            score += min(tax_efficiency * 20, 20)
        
        return min(score, 100.0)
    
    def _generate_next_steps(self, recommended_regime: str, old_additional: float, new_additional: float) -> List[str]:
        """Generate personalized next steps"""
        steps = []
        
        if recommended_regime == "old":
            if old_additional > 0:
                steps.append(f"💸 Prepare to pay additional tax of ₹{old_additional:,.0f}")
            else:
                steps.append(f"💰 You'll get a refund of ₹{abs(old_additional):,.0f}")
            steps.append("📋 Gather all investment proofs for 80C, 80D deductions")
            steps.append("🏠 Submit HRA proofs if you pay rent")
        else:
            if new_additional > 0:
                steps.append(f"💸 Prepare to pay additional tax of ₹{new_additional:,.0f}")
            else:
                steps.append(f"💰 You'll get a refund of ₹{abs(new_additional):,.0f}")
            steps.append("⚡ New regime - minimal documentation needed")
        
        steps.extend([
            "🌐 Login to Income Tax e-filing portal",
            "📝 Fill appropriate ITR form",
            "✅ Review and submit your return",
            "🔐 Complete e-verification"
        ])
        
        return steps
    
    def _print_enhanced_tax_summary(self, summary: Dict[str, Any]):
        """Print enhanced tax summary (CLI mode only)"""
        if self.output_format != "cli":
            return
            
        print("🎯 ENHANCED TAX ANALYSIS RESULTS")
        print("=" * 60)
        print(f"💰 Gross Total Income: ₹{summary.get('gross_total_income', 0):,.2f}")
        print(f"   📄 Salary Income: ₹{summary.get('salary_income', 0):,.2f}")
        print(f"   🏦 Interest Income: ₹{summary.get('interest_income', 0):,.2f}")
        print(f"   📈 Capital Gains: ₹{summary.get('capital_gains', 0):,.2f}")
        
        hra_exemption = summary.get('hra_exemption_applied', 0)
        if hra_exemption > 0:
            print(f"🏠 HRA Exemption Applied: ₹{hra_exemption:,.2f}")
            print(f"💡 Net Income after HRA: ₹{summary.get('net_income_after_hra', 0):,.2f}")
        
        print()
        print(f"💼 Total Deductions: ₹{summary.get('total_deductions', 0):,.2f}")
        print(f"🧾 Tax Already Paid (TDS): ₹{summary.get('tax_paid', 0):,.2f}")
        print()
        
        print("📊 TAX REGIME COMPARISON")
        print("-" * 40)
        print(f"🔄 Old Regime Tax: ₹{summary.get('tax_liability_old_regime', 0):,.2f}")
        print(f"🆕 New Regime Tax: ₹{summary.get('tax_liability_new_regime', 0):,.2f}")
        print(f"💡 Potential Savings: ₹{summary.get('potential_savings', 0):,.2f}")
        print()
        
        recommended = summary.get('recommended_regime', 'old').upper()
        print(f"🎯 RECOMMENDATION: {recommended} TAX REGIME")
        
        # Show additional tax or refund
        if recommended.lower() == 'old':
            additional = summary.get('additional_tax_old_regime', 0)
        else:
            additional = summary.get('additional_tax_new_regime', 0)
        
        if additional > 0:
            print(f"💸 Additional Tax Due: ₹{additional:,.2f}")
        else:
            print(f"💰 Tax Refund Expected: ₹{abs(additional):,.2f}")
        
        # Optimization score
        opt_score = summary.get('optimization_score', 0)
        print(f"📈 Tax Optimization Score: {opt_score:.1f}/100")
        
        print("\n📋 NEXT STEPS:")
        for i, step in enumerate(summary.get('next_steps', []), 1):
            print(f"   {i}. {step}")
        
        print()
    
    def export_results(self, output_file: str, format_type: str = "json") -> bool:
        """Export analysis results to file"""
        try:
            if format_type.lower() == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(self.tax_summary, f, indent=2, ensure_ascii=False, default=str)
                
                if self.output_format == "cli":
                    print(f"✅ Results exported to: {output_file}")
                return True
        except Exception as e:
            if self.output_format == "cli":
                print(f"❌ Error exporting results: {e}")
            return False

def main():
    """Enhanced main entry point"""
    parser = argparse.ArgumentParser(description="Enhanced Income Tax AI Assistant")
    parser.add_argument("--folder", help="Path to the folder containing tax documents.")
    parser.add_argument("--analyzer", default="ollama", choices=["ollama", "langextract"], 
                       help="The document analyzer to use.")
    parser.add_argument("--output-format", default="cli", choices=["cli", "json", "web"],
                       help="Output format: cli for console, json for JSON output, web for web mode")
    parser.add_argument("--export", help="Export results to file (JSON format)")
    parser.add_argument("--financial-year", default="2024-25", help="Financial year for analysis")
    
    args = parser.parse_args()

    # Initialize analyzer
    if args.analyzer == "langextract":
        analyzer = LangextractDocumentAnalyzer()
    else:
        analyzer = OllamaDocumentAnalyzer()

    # Initialize enhanced assistant
    assistant = EnhancedIncomeTaxAssistant(
        financial_year=args.financial_year,
        analyzer=analyzer,
        output_format=args.output_format
    )

    if args.folder:
        # Analyze documents
        analyzed_docs = assistant.analyze_documents_folder(args.folder)
        
        if analyzed_docs:
            # Calculate enhanced tax summary
            tax_summary = assistant.calculate_enhanced_tax_summary()
            
            # Handle different output formats
            if args.output_format == "json":
                print(json.dumps(tax_summary, indent=2, ensure_ascii=False, default=str))
            elif args.output_format == "web":
                # Return results for web interface
                return tax_summary
            
            # Export if requested
            if args.export:
                assistant.export_results(args.export, "json")
        else:
            if args.output_format == "cli":
                print("❌ No documents were successfully analyzed.")
            elif args.output_format == "json":
                print('{"error": "No documents analyzed"}')
    else:
        if args.output_format == "cli":
            print("Usage: python src/main_enhanced.py --folder <folder_path> [options]")
            print("\nOptions:")
            print("  --analyzer        ollama|langextract (default: ollama)")
            print("  --output-format   cli|json|web (default: cli)")
            print("  --export          Export results to JSON file")
            print("  --financial-year  Financial year (default: 2024-25)")

if __name__ == "__main__":
    main()