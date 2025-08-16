"""
ESOP/ESPP Perquisite Calculator for Indian Income Tax
==================================================

Implements ESOP/ESPP taxation under Section 17(2)(vi) of Income Tax Act, 1961
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal


class ESOPCalculator:
    """Calculator for ESOP/ESPP perquisite taxation under Section 17(2)(vi)"""
    
    def __init__(self, financial_year: str = "2024-25"):
        """Initialize ESOP calculator with FY-specific rules"""
        self.financial_year = financial_year
        self._configure_for_fy(financial_year)
    
    def _configure_for_fy(self, financial_year: str) -> None:
        """Configure ESOP rules for the given FY"""
        # FY 2024-25 specific rules
        if financial_year in ("2024-25", "2024-2025"):
            # Updated holding period rules from Budget 2024-25
            self.listed_ltcg_holding_period = 12  # months (changed from 36)
            self.unlisted_ltcg_holding_period = 24  # months
            self.startup_deferral_period = 48  # months
        else:
            # Default rules
            self.listed_ltcg_holding_period = 12
            self.unlisted_ltcg_holding_period = 24
            self.startup_deferral_period = 48
    
    def calculate_esop_perquisite(
        self,
        fmv_per_share: float,
        exercise_price_per_share: float,
        number_of_shares: int,
        exercise_date: Optional[date] = None,
        is_startup: bool = False
    ) -> Dict[str, Any]:
        """
        Calculate ESOP perquisite value under Section 17(2)(vi)
        
        Formula: Perquisite = (FMV per share - Exercise price per share) × Number of shares
        
        Args:
            fmv_per_share: Fair Market Value per share on exercise date
            exercise_price_per_share: Price paid by employee per share
            number_of_shares: Number of shares exercised
            exercise_date: Date of exercise (for startup deferral calculation)
            is_startup: Whether employer is eligible startup under Section 80-IAC
        
        Returns:
            Dictionary with perquisite calculation details
        """
        
        # Calculate perquisite per share
        perquisite_per_share = max(0, fmv_per_share - exercise_price_per_share)
        
        # Calculate total perquisite
        total_perquisite = perquisite_per_share * number_of_shares
        
        # Determine if tax deferral applies (for startups)
        tax_deferral_applicable = is_startup and self._is_tax_deferral_eligible(
            fmv_per_share, exercise_date
        )
        
        return {
            "fmv_per_share": round(fmv_per_share, 2),
            "exercise_price_per_share": round(exercise_price_per_share, 2),
            "perquisite_per_share": round(perquisite_per_share, 2),
            "number_of_shares": number_of_shares,
            "total_perquisite_value": round(total_perquisite, 2),
            "taxable_in_current_year": not tax_deferral_applicable,
            "tax_deferral_applicable": tax_deferral_applicable,
            "exercise_date": exercise_date,
            "is_startup": is_startup
        }
    
    def _is_tax_deferral_eligible(
        self, 
        fmv_per_share: float, 
        exercise_date: Optional[date]
    ) -> bool:
        """
        Check if ESOP qualifies for tax deferral under startup provisions
        
        Conditions for deferral:
        1. Employer must be eligible startup under Section 80-IAC
        2. FMV should not exceed certain limits (₹25 lakh aggregate per employee)
        """
        # Simplified check - actual implementation would need more details
        # about aggregate ESOP value per employee and startup eligibility
        return exercise_date is not None and fmv_per_share > 0
    
    def calculate_capital_gains_on_sale(
        self,
        sale_price_per_share: float,
        fmv_on_exercise_date: float,
        number_of_shares: int,
        exercise_date: date,
        sale_date: date,
        is_listed: bool = True
    ) -> Dict[str, Any]:
        """
        Calculate capital gains on sale of ESOP shares
        
        Cost basis = FMV on exercise date (already taxed as perquisite)
        Capital gains = Sale price - FMV on exercise date
        
        Args:
            sale_price_per_share: Sale price per share
            fmv_on_exercise_date: FMV per share on exercise date
            number_of_shares: Number of shares sold
            exercise_date: Date when options were exercised
            sale_date: Date of sale
            is_listed: Whether shares are listed on recognized stock exchange
        
        Returns:
            Dictionary with capital gains calculation
        """
        
        # Calculate holding period
        holding_period_days = (sale_date - exercise_date).days
        holding_period_months = holding_period_days / 30.44  # Average days per month
        
        # Determine if LTCG or STCG based on FY 2024-25 rules
        ltcg_threshold = (
            self.listed_ltcg_holding_period if is_listed 
            else self.unlisted_ltcg_holding_period
        )
        
        is_long_term = holding_period_months > ltcg_threshold
        
        # Calculate capital gains
        capital_gain_per_share = sale_price_per_share - fmv_on_exercise_date
        total_capital_gains = capital_gain_per_share * number_of_shares
        
        # Calculate tax on capital gains
        if is_long_term:
            # LTCG tax rates (as per FY 2024-25)
            if is_listed:
                # Listed equity: 10% without indexation
                tax_rate = 0.10
                exemption_limit = 100000  # ₹1 lakh exemption for LTCG
                taxable_ltcg = max(0, total_capital_gains - exemption_limit)
                tax_on_capital_gains = taxable_ltcg * tax_rate
            else:
                # Unlisted: 20% with indexation (simplified - actual would need CII)
                tax_rate = 0.20
                tax_on_capital_gains = total_capital_gains * tax_rate
        else:
            # STCG tax rates
            if is_listed:
                # Listed equity: 15%
                tax_rate = 0.15
            else:
                # Unlisted: As per slab rates (simplified as 30%)
                tax_rate = 0.30
            tax_on_capital_gains = total_capital_gains * tax_rate
        
        return {
            "sale_price_per_share": round(sale_price_per_share, 2),
            "cost_basis_per_share": round(fmv_on_exercise_date, 2),
            "capital_gain_per_share": round(capital_gain_per_share, 2),
            "number_of_shares": number_of_shares,
            "total_capital_gains": round(total_capital_gains, 2),
            "holding_period_months": round(holding_period_months, 1),
            "is_long_term": is_long_term,
            "is_listed": is_listed,
            "tax_rate": tax_rate,
            "tax_on_capital_gains": round(tax_on_capital_gains, 2),
            "exercise_date": exercise_date,
            "sale_date": sale_date
        }
    
    def calculate_comprehensive_esop_tax(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive ESOP tax for multiple transactions
        
        Args:
            transactions: List of ESOP transaction dictionaries
                Each should contain:
                - transaction_type: 'exercise' or 'sale'
                - fmv_per_share: FMV on relevant date
                - exercise_price_per_share: For exercise transactions
                - sale_price_per_share: For sale transactions  
                - number_of_shares: Number of shares
                - transaction_date: Date of transaction
                - is_startup: For exercise transactions
                - is_listed: For sale transactions
        
        Returns:
            Comprehensive tax calculation summary
        """
        
        total_perquisite = 0
        total_stcg = 0
        total_ltcg = 0
        total_tax_on_perquisite = 0
        total_tax_on_capital_gains = 0
        
        exercise_transactions = []
        sale_transactions = []
        
        for transaction in transactions:
            if transaction['transaction_type'] == 'exercise':
                esop_calc = self.calculate_esop_perquisite(
                    fmv_per_share=transaction['fmv_per_share'],
                    exercise_price_per_share=transaction['exercise_price_per_share'],
                    number_of_shares=transaction['number_of_shares'],
                    exercise_date=transaction['transaction_date'],
                    is_startup=transaction.get('is_startup', False)
                )
                
                total_perquisite += esop_calc['total_perquisite_value']
                exercise_transactions.append(esop_calc)
                
            elif transaction['transaction_type'] == 'sale':
                # Need to find corresponding exercise transaction for cost basis
                # Simplified assumption: using provided FMV as cost basis
                sale_calc = self.calculate_capital_gains_on_sale(
                    sale_price_per_share=transaction['sale_price_per_share'],
                    fmv_on_exercise_date=transaction.get('cost_basis_per_share', 
                                                       transaction['fmv_per_share']),
                    number_of_shares=transaction['number_of_shares'],
                    exercise_date=transaction.get('exercise_date', 
                                                transaction['transaction_date']),
                    sale_date=transaction['transaction_date'],
                    is_listed=transaction.get('is_listed', True)
                )
                
                if sale_calc['is_long_term']:
                    total_ltcg += sale_calc['total_capital_gains']
                else:
                    total_stcg += sale_calc['total_capital_gains']
                    
                total_tax_on_capital_gains += sale_calc['tax_on_capital_gains']
                sale_transactions.append(sale_calc)
        
        # Calculate tax on perquisite (as per salary tax rates)
        # Simplified - actual would depend on employee's tax slab
        total_tax_on_perquisite = total_perquisite * 0.30  # Assuming 30% tax bracket
        
        return {
            "financial_year": self.financial_year,
            "total_perquisite_value": round(total_perquisite, 2),
            "total_stcg": round(total_stcg, 2),
            "total_ltcg": round(total_ltcg, 2),
            "total_capital_gains": round(total_stcg + total_ltcg, 2),
            "total_tax_on_perquisite": round(total_tax_on_perquisite, 2),
            "total_tax_on_capital_gains": round(total_tax_on_capital_gains, 2),
            "total_esop_tax_liability": round(total_tax_on_perquisite + 
                                            total_tax_on_capital_gains, 2),
            "exercise_transactions": exercise_transactions,
            "sale_transactions": sale_transactions,
            "summary": {
                "total_transactions": len(transactions),
                "exercise_count": len(exercise_transactions),
                "sale_count": len(sale_transactions)
            }
        }
    
    def get_esop_tax_guide(self) -> Dict[str, str]:
        """Get ESOP taxation guide for current FY"""
        return {
            "perquisite_taxation": "Taxed as salary under Section 17(2)(vi) at exercise",
            "perquisite_formula": "(FMV on exercise date - Exercise price) × Number of shares",
            "capital_gains_basis": "Cost basis = FMV on exercise date",
            "listed_ltcg_holding": f"{self.listed_ltcg_holding_period} months",
            "unlisted_ltcg_holding": f"{self.unlisted_ltcg_holding_period} months",
            "listed_ltcg_rate": "10% (without indexation)",
            "listed_stcg_rate": "15%",
            "unlisted_ltcg_rate": "20% (with indexation)",
            "unlisted_stcg_rate": "As per slab rates",
            "startup_deferral": f"Available for eligible startups up to {self.startup_deferral_period} months",
            "tds_requirement": "Employer must deduct TDS under Section 192",
            "ltcg_exemption": "₹1 lakh exemption for listed equity LTCG"
        }


def example_usage():
    """Example usage of ESOP calculator"""
    
    # Initialize calculator
    calc = ESOPCalculator("2024-25")
    
    # Example 1: Calculate perquisite on exercise
    exercise_result = calc.calculate_esop_perquisite(
        fmv_per_share=150.0,
        exercise_price_per_share=50.0,
        number_of_shares=1000,
        exercise_date=date(2024, 6, 15),
        is_startup=False
    )
    
    print("ESOP Exercise Perquisite:")
    print(f"Perquisite Value: ₹{exercise_result['total_perquisite_value']:,.2f}")
    
    # Example 2: Calculate capital gains on sale
    sale_result = calc.calculate_capital_gains_on_sale(
        sale_price_per_share=200.0,
        fmv_on_exercise_date=150.0,
        number_of_shares=500,
        exercise_date=date(2024, 6, 15),
        sale_date=date(2025, 1, 15),
        is_listed=True
    )
    
    print("\nCapital Gains on Sale:")
    print(f"Capital Gains: ₹{sale_result['total_capital_gains']:,.2f}")
    print(f"Tax on Capital Gains: ₹{sale_result['tax_on_capital_gains']:,.2f}")
    
    # Example 3: Comprehensive calculation
    transactions = [
        {
            'transaction_type': 'exercise',
            'fmv_per_share': 150.0,
            'exercise_price_per_share': 50.0,
            'number_of_shares': 1000,
            'transaction_date': date(2024, 6, 15),
            'is_startup': False
        },
        {
            'transaction_type': 'sale',
            'sale_price_per_share': 200.0,
            'cost_basis_per_share': 150.0,
            'number_of_shares': 500,
            'transaction_date': date(2025, 1, 15),
            'exercise_date': date(2024, 6, 15),
            'is_listed': True
        }
    ]
    
    comprehensive_result = calc.calculate_comprehensive_esop_tax(transactions)
    
    print("\nComprehensive ESOP Tax:")
    print(f"Total Perquisite: ₹{comprehensive_result['total_perquisite_value']:,.2f}")
    print(f"Total Capital Gains: ₹{comprehensive_result['total_capital_gains']:,.2f}")
    print(f"Total Tax Liability: ₹{comprehensive_result['total_esop_tax_liability']:,.2f}")


if __name__ == "__main__":
    example_usage()