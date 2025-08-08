"""
Comprehensive Tax Analyzer - Similar to Income Tax Portal
Extracts data from documents and provides detailed tax breakdown
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
from pathlib import Path
import re

@dataclass
class IncomeBreakdown:
    """Detailed income breakdown"""
    gross_salary: float = 0.0
    basic_salary: float = 0.0
    hra_received: float = 0.0
    special_allowance: float = 0.0
    other_allowances: float = 0.0
    bonus: float = 0.0
    
    # Other income sources
    bank_interest: float = 0.0
    other_income: float = 0.0
    
    # Capital gains
    ltcg: float = 0.0
    stcg: float = 0.0
    
    # Exemptions
    hra_exemption: float = 0.0
    standard_deduction: float = 0.0
    
    # TDS and advance tax
    tds_salary: float = 0.0
    tds_other: float = 0.0
    advance_tax: float = 0.0

@dataclass
class DeductionsSummary:
    """Comprehensive deductions summary"""
    # Section 80C
    epf: float = 0.0
    ppf: float = 0.0
    life_insurance: float = 0.0
    elss: float = 0.0
    nsc: float = 0.0
    home_loan_principal: float = 0.0
    section_80c_total: float = 0.0
    section_80c_claimed: float = 0.0
    
    # Section 80D
    health_insurance_self: float = 0.0
    health_insurance_parents: float = 0.0
    section_80d_total: float = 0.0
    section_80d_claimed: float = 0.0
    
    # Other deductions
    section_80tta: float = 0.0  # Bank interest
    section_24b: float = 0.0    # Home loan interest
    section_80g: float = 0.0    # Donations
    section_80ccd1b: float = 0.0  # NPS
    
    # Total deductions
    total_deductions: float = 0.0

@dataclass
class TaxComputation:
    """Tax computation for both regimes"""
    regime_name: str
    
    # Income calculation
    gross_total_income: float = 0.0
    total_deductions: float = 0.0
    taxable_income: float = 0.0
    
    # Tax calculation
    tax_on_income: float = 0.0
    cess: float = 0.0
    total_tax: float = 0.0
    
    # TDS and payments
    total_tds: float = 0.0
    advance_tax: float = 0.0
    total_tax_paid: float = 0.0
    
    # Final result
    refund_due: float = 0.0
    balance_payable: float = 0.0

@dataclass
class HRACalculation:
    """Detailed HRA exemption calculation"""
    hra_received: float = 0.0
    basic_salary: float = 0.0
    rent_paid: float = 0.0
    is_metro: bool = False
    
    # HRA exemption components
    actual_hra_received: float = 0.0
    hra_limit_percentage: float = 0.0  # 50% for metro, 40% for non-metro
    rent_minus_basic: float = 0.0
    
    # Final exemption
    hra_exemption: float = 0.0
    hra_taxable: float = 0.0

class ComprehensiveTaxAnalyzer:
    """Comprehensive tax analyzer for detailed breakdowns"""
    
    def __init__(self):
        # FY 2024-25 tax parameters
        self.fy = "2024-25"
        self.ay = "2025-26"
        
        # Standard deduction
        self.standard_deduction_new = 75000
        self.standard_deduction_old = 50000
        
        # Section limits
        self.section_80c_limit = 150000
        self.section_80d_limit_self = 25000
        self.section_80d_limit_parents = 50000
        self.section_80tta_limit = 10000
        self.section_80ccd1b_limit = 50000
        
        # Tax slabs
        self.new_regime_slabs = [
            (300000, 0.0),
            (700000, 0.05),
            (1000000, 0.10),
            (1200000, 0.15),
            (1500000, 0.20),
            (float('inf'), 0.30)
        ]
        
        self.old_regime_slabs = [
            (250000, 0.0),
            (500000, 0.05),
            (1000000, 0.20),
            (float('inf'), 0.30)
        ]

    def analyze_documents(self, analyzed_documents: List[Any]) -> Tuple[IncomeBreakdown, DeductionsSummary]:
        """Extract comprehensive data from analyzed documents"""
        
        income = IncomeBreakdown()
        deductions = DeductionsSummary()
        
        for doc_analysis in analyzed_documents:
            if not hasattr(doc_analysis, 'extracted_data') or not doc_analysis.extracted_data:
                continue
                
            fields = doc_analysis.extracted_data.extracted_fields
            doc_type = doc_analysis.document_type.lower()
            
            # Extract from Form 16
            if 'form 16' in doc_type or 'form_16' in doc_type:
                income.gross_salary = float(fields.get('gross_salary', 0))
                income.basic_salary = float(fields.get('basic_salary', 0))
                income.hra_received = float(fields.get('hra', 0))
                income.special_allowance = float(fields.get('special_allowance', 0))
                income.tds_salary = float(fields.get('tax_deducted', 0))
                
                # Extract deductions from Form 16
                deductions.epf = float(fields.get('epf_employee', 0))
                deductions.section_80c_total = float(fields.get('section_80c', 0))
                deductions.section_80d_total = float(fields.get('section_80d', 0))
            
            # Extract from Bank Interest Certificate
            elif 'bank interest' in doc_type:
                income.bank_interest += float(fields.get('interest_amount', 0))
                income.tds_other += float(fields.get('tds_amount', 0))
            
            # Extract from Capital Gains reports
            elif 'capital gains' in doc_type or 'stocks' in doc_type or 'mutual fund' in doc_type:
                income.ltcg += float(fields.get('long_term_capital_gains', 0))
                income.stcg += float(fields.get('short_term_capital_gains', 0))
        
        # Calculate derived values
        income.other_allowances = max(0, income.gross_salary - income.basic_salary - income.hra_received - income.special_allowance)
        
        # Apply limits to deductions
        deductions.section_80c_claimed = min(deductions.section_80c_total, self.section_80c_limit)
        deductions.section_80d_claimed = min(deductions.section_80d_total, 
                                           self.section_80d_limit_self + self.section_80d_limit_parents)
        deductions.section_80tta = min(income.bank_interest, self.section_80tta_limit)
        
        deductions.total_deductions = (deductions.section_80c_claimed + 
                                     deductions.section_80d_claimed + 
                                     deductions.section_80tta + 
                                     deductions.section_24b + 
                                     deductions.section_80g + 
                                     deductions.section_80ccd1b)
        
        return income, deductions
    
    def calculate_hra_exemption(self, income: IncomeBreakdown, rent_paid: float = 0, is_metro: bool = False) -> HRACalculation:
        """Calculate HRA exemption as per IT rules"""
        
        hra_calc = HRACalculation(
            hra_received=income.hra_received,
            basic_salary=income.basic_salary,
            rent_paid=rent_paid,
            is_metro=is_metro
        )
        
        if rent_paid > 0 and income.hra_received > 0:
            # HRA exemption is minimum of:
            # 1. Actual HRA received
            # 2. 50% of basic (metro) or 40% of basic (non-metro)
            # 3. Rent paid - 10% of basic salary
            
            hra_calc.actual_hra_received = income.hra_received
            hra_calc.hra_limit_percentage = income.basic_salary * (0.50 if is_metro else 0.40)
            hra_calc.rent_minus_basic = max(0, rent_paid - (income.basic_salary * 0.10))
            
            hra_calc.hra_exemption = min(
                hra_calc.actual_hra_received,
                hra_calc.hra_limit_percentage,
                hra_calc.rent_minus_basic
            )
            
            hra_calc.hra_taxable = income.hra_received - hra_calc.hra_exemption
        else:
            hra_calc.hra_exemption = 0
            hra_calc.hra_taxable = income.hra_received
        
        return hra_calc
    
    def calculate_tax(self, income: IncomeBreakdown, deductions: DeductionsSummary, 
                     regime: str = "new", hra_exemption: float = 0) -> TaxComputation:
        """Calculate tax for specified regime"""
        
        is_new_regime = regime.lower() == "new"
        
        tax_comp = TaxComputation(regime_name=f"{regime.title()} Tax Regime")
        
        # Calculate gross total income
        tax_comp.gross_total_income = (
            income.gross_salary + 
            income.bank_interest + 
            income.other_income + 
            income.ltcg + 
            income.stcg
        )
        
        # Apply standard deduction
        standard_deduction = self.standard_deduction_new if is_new_regime else self.standard_deduction_old
        
        # Calculate total deductions
        if is_new_regime:
            # New regime - limited deductions
            tax_comp.total_deductions = standard_deduction + hra_exemption
        else:
            # Old regime - all deductions
            tax_comp.total_deductions = standard_deduction + hra_exemption + deductions.total_deductions
        
        # Calculate taxable income
        tax_comp.taxable_income = max(0, tax_comp.gross_total_income - tax_comp.total_deductions)
        
        # Calculate tax
        slabs = self.new_regime_slabs if is_new_regime else self.old_regime_slabs
        tax_comp.tax_on_income = self._calculate_tax_from_slabs(tax_comp.taxable_income, slabs)
        
        # Add cess (4%)
        tax_comp.cess = tax_comp.tax_on_income * 0.04
        tax_comp.total_tax = tax_comp.tax_on_income + tax_comp.cess
        
        # TDS and payments
        tax_comp.total_tds = income.tds_salary + income.tds_other
        tax_comp.advance_tax = income.advance_tax
        tax_comp.total_tax_paid = tax_comp.total_tds + tax_comp.advance_tax
        
        # Calculate refund or balance
        if tax_comp.total_tax_paid > tax_comp.total_tax:
            tax_comp.refund_due = tax_comp.total_tax_paid - tax_comp.total_tax
            tax_comp.balance_payable = 0
        else:
            tax_comp.refund_due = 0
            tax_comp.balance_payable = tax_comp.total_tax - tax_comp.total_tax_paid
        
        return tax_comp
    
    def _calculate_tax_from_slabs(self, taxable_income: float, slabs: List[Tuple[float, float]]) -> float:
        """Calculate tax based on slabs"""
        
        total_tax = 0
        remaining_income = taxable_income
        previous_limit = 0
        
        for limit, rate in slabs:
            if remaining_income <= 0:
                break
                
            taxable_in_slab = min(remaining_income, limit - previous_limit)
            total_tax += taxable_in_slab * rate
            remaining_income -= taxable_in_slab
            previous_limit = limit
            
            if remaining_income <= 0:
                break
        
        return total_tax
    
    def compare_regimes(self, income: IncomeBreakdown, deductions: DeductionsSummary, 
                       hra_exemption: float = 0) -> Dict[str, TaxComputation]:
        """Compare both tax regimes"""
        
        new_regime = self.calculate_tax(income, deductions, "new", hra_exemption)
        old_regime = self.calculate_tax(income, deductions, "old", hra_exemption)
        
        return {
            "new_regime": new_regime,
            "old_regime": old_regime,
            "recommended": "new" if new_regime.total_tax < old_regime.total_tax else "old",
            "savings": abs(new_regime.total_tax - old_regime.total_tax)
        }
    
    def generate_detailed_breakdown(self, analyzed_documents: List[Any], 
                                  rent_paid: float = 0, is_metro: bool = False) -> Dict[str, Any]:
        """Generate comprehensive tax analysis"""
        
        # Extract data from documents
        income, deductions = self.analyze_documents(analyzed_documents)
        
        # Calculate HRA exemption
        hra_calc = self.calculate_hra_exemption(income, rent_paid, is_metro)
        
        # Compare regimes
        regime_comparison = self.compare_regimes(income, deductions, hra_calc.hra_exemption)
        
        return {
            "income_breakdown": income,
            "deductions_summary": deductions,
            "hra_calculation": hra_calc,
            "regime_comparison": regime_comparison,
            "recommended_regime": regime_comparison["recommended"],
            "tax_savings": regime_comparison["savings"],
            "financial_year": self.fy,
            "assessment_year": self.ay
        }