"""
Core Tax Calculation Engine
Handles the fundamental tax computation logic
"""

from typing import List, Tuple, Dict, Any
from .tax_models import TaxSlabs, TaxConstants, TaxRegime, CapitalGain, CapitalGainType


class TaxEngine:
    """Core tax calculation engine following SOLID principles"""
    
    @staticmethod
    def calculate_tax_by_slabs(income: float, slabs: List[Tuple[float, float]]) -> float:
        """
        Calculate tax using progressive slab system
        
        Args:
            income: Taxable income
            slabs: List of (threshold, rate) tuples
            
        Returns:
            Calculated tax amount
        """
        if income <= 0:
            return 0.0
            
        tax = 0.0
        prev_threshold = 0
        
        for threshold, rate in slabs:
            if income <= prev_threshold:
                break
                
            taxable_in_slab = min(income, threshold) - prev_threshold
            tax += taxable_in_slab * rate
            prev_threshold = threshold
            
            if income <= threshold:
                break
                
        return round(tax, 2)
    
    @classmethod
    def calculate_normal_income_tax(cls, taxable_income: float, regime: TaxRegime) -> float:
        """
        Calculate tax on normal income (excluding capital gains)
        
        Args:
            taxable_income: Normal taxable income (after deductions)
            regime: Tax regime (old/new)
            
        Returns:
            Tax amount on normal income
        """
        if regime == TaxRegime.NEW:
            slabs = TaxSlabs.NEW_REGIME_SLABS
        else:
            slabs = TaxSlabs.OLD_REGIME_SLABS
            
        return cls.calculate_tax_by_slabs(taxable_income, slabs)
    
    @staticmethod
    def calculate_rebate_87a(taxable_income: float, tax_amount: float, regime: TaxRegime) -> float:
        """
        Calculate rebate under Section 87A
        
        IMPORTANT: Apply only to normal income tax, not capital gains
        
        Args:
            taxable_income: Normal taxable income (excluding capital gains)
            tax_amount: Tax on normal income
            regime: Tax regime
            
        Returns:
            Rebate amount
        """
        if regime == TaxRegime.NEW and taxable_income <= TaxConstants.NEW_REGIME_REBATE_LIMIT:
            return min(tax_amount, TaxConstants.NEW_REGIME_REBATE_AMOUNT)
        elif regime == TaxRegime.OLD and taxable_income <= TaxConstants.OLD_REGIME_REBATE_LIMIT:
            return min(tax_amount, TaxConstants.OLD_REGIME_REBATE_AMOUNT)
        else:
            return 0.0
    
    @staticmethod
    def calculate_surcharge(tax_amount: float, total_income: float, 
                          regime: TaxRegime, is_capital_gains: bool = False) -> float:
        """
        Calculate surcharge based on total income
        
        Args:
            tax_amount: Tax amount on which surcharge is calculated
            total_income: Total income including capital gains (for determining slab)
            regime: Tax regime
            is_capital_gains: Whether this tax is from capital gains
            
        Returns:
            Surcharge amount
        """
        if tax_amount <= 0 or total_income <= 5000000:
            return 0.0
        
        # Determine surcharge rate based on total income
        surcharge_rate = 0.0
        for threshold, rate in TaxSlabs.SURCHARGE_SLABS:
            if total_income <= threshold:
                surcharge_rate = rate
                break
        
        # Apply regime-specific cap for highest bracket
        if regime == TaxRegime.NEW and surcharge_rate == 0.37:
            surcharge_rate = 0.25
        
        # Apply capital gains specific cap (max 15% for capital gains)
        if is_capital_gains and surcharge_rate > 0.15:
            surcharge_rate = 0.15
        
        return round(tax_amount * surcharge_rate, 2)
    
    @staticmethod
    def calculate_cess(tax_amount: float, surcharge_amount: float) -> float:
        """
        Calculate Health & Education Cess (4% of tax + surcharge)
        
        Args:
            tax_amount: Base tax amount
            surcharge_amount: Surcharge amount
            
        Returns:
            Cess amount
        """
        return round((tax_amount + surcharge_amount) * TaxConstants.CESS_RATE, 2)


class CapitalGainsEngine:
    """Specialized engine for capital gains calculations"""
    
    @staticmethod
    def calculate_stcg_111a_tax(stcg_amount: float) -> Dict[str, float]:
        """
        Calculate STCG tax under Section 111A (equity with STT, <12 months)
        
        Args:
            stcg_amount: Short term capital gains amount
            
        Returns:
            Dictionary with STCG tax calculation details
        """
        if stcg_amount <= 0:
            return {
                'stcg_amount': 0,
                'tax_amount': 0,
                'applicable_rate': TaxConstants.STCG_TAX_RATE
            }
        
        tax_amount = stcg_amount * TaxConstants.STCG_TAX_RATE
        
        return {
            'stcg_amount': round(stcg_amount, 2),
            'tax_amount': round(tax_amount, 2),
            'applicable_rate': TaxConstants.STCG_TAX_RATE
        }
    
    @classmethod
    def calculate_ltcg_112a_tax(cls, ltcg_transactions: List[CapitalGain]) -> Dict[str, float]:
        """
        Calculate LTCG tax under Section 112A (equity with STT, ≥12 months)
        
        Key features:
        - ₹1.25L exemption per year
        - 10% rate for sales before 23-Jul-2024
        - 12.5% rate for sales from 23-Jul-2024
        
        Args:
            ltcg_transactions: List of LTCG transactions
            
        Returns:
            Dictionary with LTCG tax calculation details
        """
        # Filter only Section 112A applicable transactions
        section_112a_gains = [
            gain for gain in ltcg_transactions 
            if gain.is_section_112a_applicable and gain.amount > 0
        ]
        
        if not section_112a_gains:
            return {
                'total_ltcg': 0,
                'exempt_amount': 0,
                'taxable_ltcg': 0,
                'tax_amount': 0,
                'applicable_rate': 0,
                'transactions_count': 0
            }
        
        # Calculate total LTCG
        total_ltcg = sum(gain.amount for gain in section_112a_gains)
        
        # Apply exemption limit (₹1.25L per year)
        exempt_amount = min(total_ltcg, TaxConstants.LTCG_EXEMPTION_LIMIT)
        taxable_ltcg = max(0, total_ltcg - TaxConstants.LTCG_EXEMPTION_LIMIT)
        
        # Calculate tax based on sale dates
        tax_amount = 0
        if taxable_ltcg > 0:
            remaining_taxable = taxable_ltcg
            
            # Sort transactions by date for FIFO application of exemption
            sorted_gains = sorted(section_112a_gains, key=lambda x: x.sale_date)
            
            for gain in sorted_gains:
                if remaining_taxable <= 0:
                    break
                
                # Determine applicable rate based on sale date
                if gain.sale_date < TaxConstants.JULY_23_2024:
                    rate = TaxConstants.LTCG_RATE_PRE_JULY
                else:
                    rate = TaxConstants.LTCG_RATE_POST_JULY
                
                # Calculate tax for this transaction's taxable portion
                gain_taxable_portion = min(gain.amount, remaining_taxable)
                if gain_taxable_portion > 0:
                    tax_amount += gain_taxable_portion * rate
                    remaining_taxable -= gain_taxable_portion
        
        # Determine average rate for display
        has_post_july = any(g.sale_date >= TaxConstants.JULY_23_2024 for g in section_112a_gains)
        avg_rate = TaxConstants.LTCG_RATE_POST_JULY if has_post_july else TaxConstants.LTCG_RATE_PRE_JULY
        
        return {
            'total_ltcg': round(total_ltcg, 2),
            'exempt_amount': round(exempt_amount, 2),
            'taxable_ltcg': round(taxable_ltcg, 2),
            'tax_amount': round(tax_amount, 2),
            'applicable_rate': avg_rate,
            'transactions_count': len(section_112a_gains)
        }
    
    @staticmethod
    def calculate_other_capital_gains_tax(stcg_amount: float, ltcg_amount: float) -> Dict[str, float]:
        """
        Calculate tax on other capital gains (non-equity, without STT)
        
        Args:
            stcg_amount: Other short-term capital gains
            ltcg_amount: Other long-term capital gains
            
        Returns:
            Dictionary with other capital gains tax details
        """
        # Other STCG taxed at normal rates (assume 30% for simplicity)
        other_stcg_tax = stcg_amount * 0.30
        
        # Other LTCG taxed at 20% with indexation (simplified to 20%)
        other_ltcg_tax = ltcg_amount * 0.20
        
        return {
            'other_stcg_amount': round(stcg_amount, 2),
            'other_ltcg_amount': round(ltcg_amount, 2),
            'other_stcg_tax': round(other_stcg_tax, 2),
            'other_ltcg_tax': round(other_ltcg_tax, 2),
            'total_other_cg_tax': round(other_stcg_tax + other_ltcg_tax, 2)
        }
    
    @classmethod
    def calculate_total_capital_gains_tax(cls, capital_gains: List[CapitalGain], 
                                        other_stcg: float = 0, other_ltcg: float = 0) -> Dict[str, Any]:
        """
        Calculate total tax on all types of capital gains
        
        Args:
            capital_gains: List of capital gain transactions
            other_stcg: Other short-term capital gains amount
            other_ltcg: Other long-term capital gains amount
            
        Returns:
            Complete capital gains tax breakdown
        """
        # Separate transactions by type
        stcg_111a_transactions = [cg for cg in capital_gains if cg.is_section_111a_applicable]
        ltcg_112a_transactions = [cg for cg in capital_gains if cg.is_section_112a_applicable]
        
        # Calculate STCG 111A tax
        stcg_111a_amount = sum(cg.amount for cg in stcg_111a_transactions)
        stcg_111a_details = cls.calculate_stcg_111a_tax(stcg_111a_amount)
        
        # Calculate LTCG 112A tax
        ltcg_112a_details = cls.calculate_ltcg_112a_tax(ltcg_112a_transactions)
        
        # Calculate other capital gains tax
        other_cg_details = cls.calculate_other_capital_gains_tax(other_stcg, other_ltcg)
        
        # Total capital gains tax
        total_cg_tax = (
            stcg_111a_details['tax_amount'] + 
            ltcg_112a_details['tax_amount'] + 
            other_cg_details['total_other_cg_tax']
        )
        
        return {
            'stcg_111a_details': stcg_111a_details,
            'ltcg_112a_details': ltcg_112a_details,
            'other_cg_details': other_cg_details,
            'total_capital_gains_tax': round(total_cg_tax, 2),
            'summary': {
                'total_stcg': round(stcg_111a_amount + other_stcg, 2),
                'total_ltcg': round(ltcg_112a_details['total_ltcg'] + other_ltcg, 2),
                'total_cg_income': round(stcg_111a_amount + ltcg_112a_details['total_ltcg'] + other_stcg + other_ltcg, 2)
            }
        }