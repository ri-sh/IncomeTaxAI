"""
Tax Regime Calculator
Comprehensive calculator for Old vs New tax regime comparison
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import json

@dataclass
class TaxCalculationResult:
    """Result of tax calculation for a regime"""
    gross_income: float
    deductions: float
    taxable_income: float
    tax_before_cess: float
    cess: float
    total_tax: float
    tax_savings: float
    effective_rate: float
    regime_name: str

@dataclass
class DeductionBreakdown:
    """Breakdown of deductions available"""
    section_80c: float = 0.0
    section_80d: float = 0.0
    section_80ccd_1b: float = 0.0
    hra_exemption: float = 0.0
    standard_deduction: float = 0.0
    professional_tax: float = 0.0
    other_deductions: float = 0.0

class TaxRegimeCalculator:
    """Calculate and compare Old vs New tax regimes"""
    
    def __init__(self):
        # Tax slabs for FY 2024-25
        self.old_regime_slabs = [
            (250000, 0.0),      # Up to 2.5L - 0%
            (500000, 0.05),     # 2.5L to 5L - 5%
            (1000000, 0.20),    # 5L to 10L - 20%
            (float('inf'), 0.30) # Above 10L - 30%
        ]
        
        self.new_regime_slabs = [
            (300000, 0.0),      # Up to 3L - 0%
            (700000, 0.05),     # 3L to 7L - 5%
            (1000000, 0.10),    # 7L to 10L - 10%
            (1200000, 0.15),    # 10L to 12L - 15%
            (1500000, 0.20),    # 12L to 15L - 20%
            (float('inf'), 0.30) # Above 15L - 30%
        ]
        
        # Standard deductions
        self.old_regime_standard_deduction = 50000
        self.new_regime_standard_deduction = 75000
        
        # Cess rate
        self.cess_rate = 0.04  # 4% health and education cess
    
    def calculate_tax_slab_wise(self, taxable_income: float, regime: str) -> Tuple[float, List[Dict]]:
        """Calculate tax slab-wise and return breakdown"""
        
        slabs = self.old_regime_slabs if regime == 'old' else self.new_regime_slabs
        
        tax = 0.0
        breakdown = []
        remaining_income = taxable_income
        prev_limit = 0
        
        for limit, rate in slabs:
            if remaining_income <= 0:
                break
            
            slab_income = min(remaining_income, limit - prev_limit)
            slab_tax = slab_income * rate
            tax += slab_tax
            
            if slab_income > 0:
                breakdown.append({
                    'range': f"₹{prev_limit:,.0f} - ₹{min(limit, prev_limit + slab_income):,.0f}",
                    'rate': f"{rate:.0%}",
                    'income': slab_income,
                    'tax': slab_tax
                })
            
            remaining_income -= slab_income
            prev_limit = limit
            
            if limit == float('inf'):
                break
        
        return tax, breakdown
    
    def calculate_old_regime(self, 
                           gross_income: float,
                           deductions: DeductionBreakdown) -> TaxCalculationResult:
        """Calculate tax under old regime"""
        
        # Total deductions
        total_deductions = (
            deductions.section_80c +
            deductions.section_80d +
            deductions.section_80ccd_1b +
            deductions.hra_exemption +
            deductions.standard_deduction +
            deductions.professional_tax +
            deductions.other_deductions
        )
        
        # Taxable income
        taxable_income = max(0, gross_income - total_deductions)
        
        # Calculate tax
        tax_before_cess, _ = self.calculate_tax_slab_wise(taxable_income, 'old')
        cess = tax_before_cess * self.cess_rate
        total_tax = tax_before_cess + cess
        
        # Calculate effective rate
        effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0
        
        return TaxCalculationResult(
            gross_income=gross_income,
            deductions=total_deductions,
            taxable_income=taxable_income,
            tax_before_cess=tax_before_cess,
            cess=cess,
            total_tax=total_tax,
            tax_savings=total_deductions * 0.31,  # Approximate savings
            effective_rate=effective_rate,
            regime_name="Old Regime"
        )
    
    def calculate_new_regime(self, 
                           gross_income: float,
                           standard_deduction: float = None,
                           professional_tax: float = 0.0) -> TaxCalculationResult:
        """Calculate tax under new regime"""
        
        # Only standard deduction and professional tax allowed
        if standard_deduction is None:
            standard_deduction = self.new_regime_standard_deduction
        
        total_deductions = standard_deduction + professional_tax
        
        # Taxable income
        taxable_income = max(0, gross_income - total_deductions)
        
        # Calculate tax
        tax_before_cess, _ = self.calculate_tax_slab_wise(taxable_income, 'new')
        cess = tax_before_cess * self.cess_rate
        total_tax = tax_before_cess + cess
        
        # Calculate effective rate
        effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0
        
        return TaxCalculationResult(
            gross_income=gross_income,
            deductions=total_deductions,
            taxable_income=taxable_income,
            tax_before_cess=tax_before_cess,
            cess=cess,
            total_tax=total_tax,
            tax_savings=0,  # No additional savings in new regime
            effective_rate=effective_rate,
            regime_name="New Regime"
        )
    
    def compare_regimes(self, 
                       gross_income: float,
                       deductions: DeductionBreakdown) -> Dict[str, Any]:
        """Compare both tax regimes and provide recommendation"""
        
        # Calculate for both regimes
        old_result = self.calculate_old_regime(gross_income, deductions)
        new_result = self.calculate_new_regime(gross_income, 
                                              deductions.professional_tax)
        
        # Determine better regime
        savings_with_old = new_result.total_tax - old_result.total_tax
        better_regime = "Old Regime" if savings_with_old > 0 else "New Regime"
        
        # Create detailed comparison
        comparison = {
            'old_regime': old_result,
            'new_regime': new_result,
            'savings_with_old': savings_with_old,
            'savings_percentage': (savings_with_old / new_result.total_tax * 100) if new_result.total_tax > 0 else 0,
            'recommended_regime': better_regime,
            'recommendation_reason': self._get_recommendation_reason(old_result, new_result, deductions),
            'deduction_impact': self._calculate_deduction_impact(deductions),
            'breakeven_analysis': self._calculate_breakeven_income(deductions)
        }
        
        return comparison
    
    def _get_recommendation_reason(self, 
                                 old_result: TaxCalculationResult,
                                 new_result: TaxCalculationResult,
                                 deductions: DeductionBreakdown) -> str:
        """Get detailed reason for regime recommendation"""
        
        if old_result.total_tax < new_result.total_tax:
            # Old regime is better
            savings = new_result.total_tax - old_result.total_tax
            reasons = []
            
            if deductions.section_80c > 0:
                reasons.append(f"Section 80C deductions (₹{deductions.section_80c:,.0f})")
            if deductions.section_80d > 0:
                reasons.append(f"Section 80D deductions (₹{deductions.section_80d:,.0f})")
            if deductions.section_80ccd_1b > 0:
                reasons.append(f"NPS deductions (₹{deductions.section_80ccd_1b:,.0f})")
            if deductions.hra_exemption > 0:
                reasons.append(f"HRA exemption (₹{deductions.hra_exemption:,.0f})")
            
            reason = f"Old regime saves ₹{savings:,.0f} due to deductions: {', '.join(reasons)}"
            
        else:
            # New regime is better
            savings = old_result.total_tax - new_result.total_tax
            reason = f"New regime saves ₹{savings:,.0f} due to lower tax rates and higher standard deduction"
        
        return reason
    
    def _calculate_deduction_impact(self, deductions: DeductionBreakdown) -> Dict[str, float]:
        """Calculate impact of each deduction"""
        
        # Assuming 31% tax bracket for impact calculation
        tax_rate = 0.31
        
        impact = {
            'section_80c_impact': deductions.section_80c * tax_rate,
            'section_80d_impact': deductions.section_80d * tax_rate,
            'section_80ccd_1b_impact': deductions.section_80ccd_1b * tax_rate,
            'hra_impact': deductions.hra_exemption * tax_rate,
            'total_deduction_benefit': (
                deductions.section_80c + 
                deductions.section_80d + 
                deductions.section_80ccd_1b + 
                deductions.hra_exemption
            ) * tax_rate
        }
        
        return impact
    
    def _calculate_breakeven_income(self, deductions: DeductionBreakdown) -> Dict[str, Any]:
        """Calculate breakeven income where both regimes have equal tax"""
        
        # This is a simplified calculation
        # In practice, this would require iterative calculation
        
        total_deductions = (
            deductions.section_80c + 
            deductions.section_80d + 
            deductions.section_80ccd_1b + 
            deductions.hra_exemption
        )
        
        # Rough estimate: breakeven around 8-12 lakh range
        # depending on deductions
        estimated_breakeven = 800000 + (total_deductions * 2)
        
        return {
            'estimated_breakeven_income': estimated_breakeven,
            'note': 'Approximate value. Actual breakeven may vary based on specific tax calculations.'
        }
    
    def generate_tax_planning_suggestions(self, 
                                        gross_income: float,
                                        current_deductions: DeductionBreakdown) -> List[Dict[str, Any]]:
        """Generate tax planning suggestions"""
        
        suggestions = []
        
        # Section 80C suggestions
        if current_deductions.section_80c < 150000:
            remaining_80c = 150000 - current_deductions.section_80c
            potential_saving = remaining_80c * 0.31
            suggestions.append({
                'category': 'Section 80C Optimization',
                'suggestion': f'Increase Section 80C investments by ₹{remaining_80c:,.0f}',
                'potential_saving': potential_saving,
                'investment_options': ['ELSS Mutual Funds', 'PPF', 'NSC', 'Tax Saving FD', 'LIC Premium'],
                'priority': 'High'
            })
        
        # Section 80D suggestions
        if current_deductions.section_80d < 25000:
            remaining_80d = 25000 - current_deductions.section_80d
            potential_saving = remaining_80d * 0.31
            suggestions.append({
                'category': 'Health Insurance (80D)',
                'suggestion': f'Get health insurance worth ₹{remaining_80d:,.0f}',
                'potential_saving': potential_saving,
                'investment_options': ['Health Insurance Premium', 'Parents Health Insurance'],
                'priority': 'High'
            })
        
        # NPS suggestions
        if current_deductions.section_80ccd_1b < 50000:
            remaining_nps = 50000 - current_deductions.section_80ccd_1b
            potential_saving = remaining_nps * 0.31
            suggestions.append({
                'category': 'NPS Investment (80CCD(1B))',
                'suggestion': f'Invest ₹{remaining_nps:,.0f} in NPS for additional deduction',
                'potential_saving': potential_saving,
                'investment_options': ['National Pension System'],
                'priority': 'Medium'
            })
        
        # Regime-specific suggestions
        comparison = self.compare_regimes(gross_income, current_deductions)
        if comparison['recommended_regime'] == 'Old Regime':
            suggestions.append({
                'category': 'Regime Selection',
                'suggestion': 'Choose Old Tax Regime and maximize deductions',
                'potential_saving': comparison['savings_with_old'],
                'investment_options': ['Maximize all available deductions'],
                'priority': 'Critical'
            })
        
        return suggestions
    
    def create_detailed_breakdown(self, 
                                gross_income: float,
                                deductions: DeductionBreakdown) -> Dict[str, Any]:
        """Create detailed breakdown for both regimes"""
        
        old_tax, old_breakdown = self.calculate_tax_slab_wise(
            max(0, gross_income - (
                deductions.section_80c + deductions.section_80d + 
                deductions.section_80ccd_1b + deductions.hra_exemption + 
                deductions.standard_deduction + deductions.professional_tax + 
                deductions.other_deductions
            )), 'old'
        )
        
        new_tax, new_breakdown = self.calculate_tax_slab_wise(
            max(0, gross_income - self.new_regime_standard_deduction - deductions.professional_tax), 'new'
        )
        
        return {
            'old_regime_breakdown': {
                'slabs': old_breakdown,
                'total_tax': old_tax,
                'cess': old_tax * self.cess_rate,
                'final_tax': old_tax * (1 + self.cess_rate)
            },
            'new_regime_breakdown': {
                'slabs': new_breakdown,
                'total_tax': new_tax,
                'cess': new_tax * self.cess_rate,
                'final_tax': new_tax * (1 + self.cess_rate)
            }
        }