"""
Tax Calculator for Indian Income Tax
===================================

FY-aware calculator supporting FY 2023-24 and FY 2024-25.
"""

from typing import Dict, Any

class TaxCalculator:
    """Indian Income Tax Calculator (FY-aware)"""
    
    def __init__(self, financial_year: str = "2024-25"):
        """Initialize tax calculator with FY-specific rates.
        financial_year examples: "2023-24", "2024-25"
        """
        self.financial_year = financial_year
        self._configure_for_fy(financial_year)
        print(f"🧮 Tax Calculator initialized for FY {self.financial_year}")

    def _configure_for_fy(self, financial_year: str) -> None:
        """Configure slabs and deductions for the given FY."""
        # Defaults (FY 2024-25 as per repo rules)
        new_regime_slabs_2024_25 = [
            (0, 300000, 0),
            (300000, 600000, 5),
            (600000, 900000, 10),
            (900000, 1200000, 15),
            (1200000, 1500000, 20),
            (1500000, float('inf'), 30)
        ]
        old_regime_slabs_common = [
            (0, 250000, 0),
            (250000, 500000, 5),
            (500000, 1000000, 20),
            (1000000, float('inf'), 30)
        ]

        # FY 2023-24 configuration (AY 2024-25)
        # Budget 2023 introduced standard deduction under new regime (₹50,000)
        if financial_year in ("2023-24", "2023-2024"):
            self.new_regime_slabs = new_regime_slabs_2024_25
            self.old_regime_slabs = old_regime_slabs_common
            self.standard_deduction_new = 50000
            self.standard_deduction_old = 50000
        else:
            # FY 2024-25 (AY 2025-26)
            self.new_regime_slabs = new_regime_slabs_2024_25
            self.old_regime_slabs = old_regime_slabs_common
            self.standard_deduction_new = 75000
            self.standard_deduction_old = 50000

        # Section 80C and health insurance limits remain same across these FYs
        self.section_80c_limit = 150000
        self.health_insurance_limit = 25000
        self.health_insurance_parents_limit = 50000
    
    def calculate_new_regime_tax(self, total_income: float) -> float:
        """Calculate tax under new regime (Section 115BAC)"""
        
        # Apply standard deduction
        taxable_income = max(0, total_income - self.standard_deduction_new)
        
        if taxable_income <= 0:
            return 0.0
        
        total_tax = 0.0
        
        for i, (lower, upper, rate) in enumerate(self.new_regime_slabs):
            if taxable_income > lower:
                # Calculate income in this slab
                slab_income = min(taxable_income - lower, upper - lower)
                slab_tax = slab_income * (rate / 100)
                total_tax += slab_tax
                
                # If we've covered all income, break
                if taxable_income <= upper:
                    break
        
        # Add 4% Health and Education Cess
        total_tax += total_tax * 0.04
        
        return round(total_tax, 2)
    
    def calculate_old_regime_tax(self, total_income: float, deductions: float = 0.0) -> float:
        """Calculate tax under old regime with deductions"""
        
        # Apply standard deduction
        taxable_income = max(0, total_income - self.standard_deduction_old)
        
        # Apply other deductions (capped at section 80C limit)
        applicable_deductions = min(deductions, self.section_80c_limit)
        taxable_income = max(0, taxable_income - applicable_deductions)
        
        if taxable_income <= 0:
            return 0.0
        
        total_tax = 0.0
        
        for i, (lower, upper, rate) in enumerate(self.old_regime_slabs):
            if taxable_income > lower:
                # Calculate income in this slab
                slab_income = min(taxable_income - lower, upper - lower)
                slab_tax = slab_income * (rate / 100)
                total_tax += slab_tax
                
                # If we've covered all income, break
                if taxable_income <= upper:
                    break
        
        # Add 4% Health and Education Cess
        total_tax += total_tax * 0.04
        
        return round(total_tax, 2)
    
    def compare_regimes(self, total_income: float, deductions: float = 0.0) -> Dict[str, Any]:
        """Compare tax liability under both regimes"""
        
        new_regime_tax = self.calculate_new_regime_tax(total_income)
        old_regime_tax = self.calculate_old_regime_tax(total_income, deductions)
        
        # Determine which regime is better
        if new_regime_tax < old_regime_tax:
            better_regime = "new"
            tax_savings = old_regime_tax - new_regime_tax
        else:
            better_regime = "old"
            tax_savings = new_regime_tax - old_regime_tax
        
        return {
            "new_regime_tax": new_regime_tax,
            "old_regime_tax": old_regime_tax,
            "better_regime": better_regime,
            "tax_savings": tax_savings,
            "total_income": total_income,
            "deductions": deductions
        }
    
    def calculate_effective_tax_rate(self, total_income: float, tax_amount: float) -> float:
        """Calculate effective tax rate"""
        if total_income <= 0:
            return 0.0
        return round((tax_amount / total_income) * 100, 2)
    
    def get_tax_breakdown(self, total_income: float, regime: str = "new", deductions: float = 0.0) -> Dict[str, Any]:
        """Get detailed tax breakdown"""
        
        if regime == "new":
            tax_amount = self.calculate_new_regime_tax(total_income)
            standard_deduction = self.standard_deduction_new
            applicable_deductions = 0.0
        else:
            tax_amount = self.calculate_old_regime_tax(total_income, deductions)
            standard_deduction = self.standard_deduction_old
            applicable_deductions = min(deductions, self.section_80c_limit)
        
        effective_rate = self.calculate_effective_tax_rate(total_income, tax_amount)
        
        return {
            "regime": regime,
            "total_income": total_income,
            "standard_deduction": standard_deduction,
            "other_deductions": applicable_deductions,
            "taxable_income": max(0, total_income - standard_deduction - applicable_deductions),
            "tax_amount": tax_amount,
            "effective_tax_rate": effective_rate,
            "health_education_cess": round(tax_amount * 0.04, 2)
        }
    
    def calculate_capital_gains_tax(self, ltcg_amount: float, stcg_amount: float) -> Dict[str, float]:
        """Calculate capital gains tax"""
        
        # LTCG tax (10% without indexation for equity, 20% with indexation for others)
        ltcg_tax = ltcg_amount * 0.10  # Assuming equity LTCG
        
        # STCG tax (15% for equity, slab rate for others)
        stcg_tax = stcg_amount * 0.15  # Assuming equity STCG
        
        total_capital_gains_tax = ltcg_tax + stcg_tax
        
        return {
            "ltcg_tax": round(ltcg_tax, 2),
            "stcg_tax": round(stcg_tax, 2),
            "total_capital_gains_tax": round(total_capital_gains_tax, 2)
        }
    
    def get_tax_slabs_info(self, regime: str = "new") -> Dict[str, Any]:
        """Get information about tax slabs"""
        
        if regime == "new":
            slabs = self.new_regime_slabs
            standard_deduction = self.standard_deduction_new
        else:
            slabs = self.old_regime_slabs
            standard_deduction = self.standard_deduction_old
        
        slab_info = []
        for lower, upper, rate in slabs:
            if upper == float('inf'):
                slab_info.append({
                    "income_range": f"₹{lower:,.0f} and above",
                    "tax_rate": f"{rate}%"
                })
            else:
                slab_info.append({
                    "income_range": f"₹{lower:,.0f} - ₹{upper:,.0f}",
                    "tax_rate": f"{rate}%"
                })
        
        return {
            "regime": regime,
            "financial_year": "2024-25",
            "standard_deduction": standard_deduction,
            "slabs": slab_info
        }
    
    def print_tax_comparison(self, total_income: float, deductions: float = 0.0):
        """Print a formatted tax comparison"""
        
        comparison = self.compare_regimes(total_income, deductions)
        
        print("📊 TAX REGIME COMPARISON (FY 2024-25)")
        print("=" * 50)
        print(f"💰 Total Income: ₹{total_income:,.2f}")
        print(f"💼 Deductions: ₹{deductions:,.2f}")
        print()
        print("🆕 NEW REGIME (Default):")
        print(f"   Tax Amount: ₹{comparison['new_regime_tax']:,.2f}")
        print(f"   Effective Rate: {self.calculate_effective_tax_rate(total_income, comparison['new_regime_tax']):.2f}%")
        print()
        print("🔄 OLD REGIME:")
        print(f"   Tax Amount: ₹{comparison['old_regime_tax']:,.2f}")
        print(f"   Effective Rate: {self.calculate_effective_tax_rate(total_income, comparison['old_regime_tax']):.2f}%")
        print()
        print(f"🎯 RECOMMENDED: {comparison['better_regime'].upper()} REGIME")
        print(f"💰 Tax Savings: ₹{comparison['tax_savings']:,.2f}")
        print()
        
        # Print slab information
        print("📋 TAX SLABS:")
        new_slabs = self.get_tax_slabs_info("new")
        old_slabs = self.get_tax_slabs_info("old")
        
        print("🆕 New Regime:")
        for slab in new_slabs["slabs"]:
            print(f"   {slab['income_range']}: {slab['tax_rate']}")
        
        print("\n🔄 Old Regime:")
        for slab in old_slabs["slabs"]:
            print(f"   {slab['income_range']}: {slab['tax_rate']}")
        
        print(f"\n💡 Standard Deduction: New ₹{new_slabs['standard_deduction']:,.0f}, Old ₹{old_slabs['standard_deduction']:,.0f}") 