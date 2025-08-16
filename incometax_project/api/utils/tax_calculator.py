"""
Indian Income Tax Calculator for FY 2024-25 (AY 2025-26)
Official Government Rates Implementation
"""

class IncomeTaxCalculator:
    """
    Income Tax Calculator implementing official Indian tax rates for FY 2024-25
    Supports both Old Tax Regime and New Tax Regime calculations
    """
    
    # Official Tax Slabs for FY 2024-25
    OLD_REGIME_SLABS = [
        (250000, 0.0),      # Up to ₹2.5L: 0%
        (500000, 0.05),     # ₹2.5L to ₹5L: 5%
        (1000000, 0.20),    # ₹5L to ₹10L: 20%
        (float('inf'), 0.30) # Above ₹10L: 30%
    ]
    
    NEW_REGIME_SLABS = [
        (300000, 0.0),      # Up to ₹3L: 0%
        (700000, 0.05),     # ₹3L to ₹7L: 5%
        (1000000, 0.10),    # ₹7L to ₹10L: 10%
        (1200000, 0.15),    # ₹10L to ₹12L: 15%
        (1500000, 0.20),    # ₹12L to ₹15L: 20%
        (float('inf'), 0.30) # Above ₹15L: 30%
    ]
    
    # Surcharge Rates (same for both regimes, but different caps)
    SURCHARGE_SLABS = [
        (5000000, 0.0),     # Up to ₹50L: 0%
        (10000000, 0.10),   # ₹50L to ₹1Cr: 10%
        (20000000, 0.15),   # ₹1Cr to ₹2Cr: 15%
        (50000000, 0.25),   # ₹2Cr to ₹5Cr: 25%
        (float('inf'), 0.37) # Above ₹5Cr: 37% (Old) / 25% (New)
    ]
    
    # Health & Education Cess Rate
    CESS_RATE = 0.04  # 4%
    
    @classmethod
    def calculate_tax_by_slabs(cls, income, slabs):
        """
        Calculate tax using progressive slab system
        
        Args:
            income (float): Taxable income
            slabs (list): List of (threshold, rate) tuples
            
        Returns:
            float: Calculated tax amount
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
    def calculate_old_regime_tax(cls, taxable_income):
        """
        Calculate tax under Old Tax Regime
        
        Args:
            taxable_income (float): Net taxable income after deductions
            
        Returns:
            float: Tax amount (before surcharge and cess)
        """
        return cls.calculate_tax_by_slabs(taxable_income, cls.OLD_REGIME_SLABS)
    
    @classmethod
    def calculate_new_regime_tax(cls, taxable_income):
        """
        Calculate tax under New Tax Regime
        
        Args:
            taxable_income (float): Net taxable income after deductions
            
        Returns:
            float: Tax amount (before surcharge and cess)
        """
        return cls.calculate_tax_by_slabs(taxable_income, cls.NEW_REGIME_SLABS)
    
    @classmethod
    def calculate_surcharge(cls, tax_amount, taxable_income, regime='old'):
        """
        Calculate surcharge based on income level and regime
        
        Args:
            tax_amount (float): Base tax amount
            taxable_income (float): Taxable income
            regime (str): 'old' or 'new' tax regime
            
        Returns:
            float: Surcharge amount
        """
        if tax_amount <= 0 or taxable_income <= 5000000:  # No surcharge below ₹50L
            return 0.0
            
        # Determine surcharge rate based on income level
        surcharge_rate = 0.0
        for threshold, rate in cls.SURCHARGE_SLABS:
            if taxable_income <= threshold:
                surcharge_rate = rate
                break
                
        # Apply regime-specific cap for highest bracket
        if regime == 'new' and surcharge_rate == 0.37:
            surcharge_rate = 0.25  # New regime caps at 25%
            
        return round(tax_amount * surcharge_rate, 2)
    
    @classmethod
    def calculate_cess(cls, tax_amount, surcharge_amount):
        """
        Calculate Health & Education Cess
        
        Args:
            tax_amount (float): Base tax amount
            surcharge_amount (float): Surcharge amount
            
        Returns:
            float: Cess amount
        """
        return round((tax_amount + surcharge_amount) * cls.CESS_RATE, 2)
    
    @classmethod
    def calculate_total_tax_liability(cls, taxable_income, regime='old'):
        """
        Calculate complete tax liability including tax, surcharge, and cess
        
        Args:
            taxable_income (float): Net taxable income
            regime (str): 'old' or 'new' tax regime
            
        Returns:
            dict: Complete tax breakdown
        """
        # Calculate base tax
        if regime == 'old':
            base_tax = cls.calculate_old_regime_tax(taxable_income)
        else:
            base_tax = cls.calculate_new_regime_tax(taxable_income)
            
        # Calculate surcharge
        surcharge = cls.calculate_surcharge(base_tax, taxable_income, regime)
        
        # Calculate cess
        cess = cls.calculate_cess(base_tax, surcharge)
        
        # Total liability
        total_liability = base_tax + surcharge + cess
        
        return {
            'base_tax': round(base_tax, 2),
            'surcharge': round(surcharge, 2),
            'cess': round(cess, 2),
            'total_liability': round(total_liability, 2),
            'regime': regime,
            'taxable_income': round(taxable_income, 2)
        }
    
    @classmethod
    def calculate_refund_or_payable(cls, total_tax_liability, tds_paid):
        """
        Calculate refund due or additional tax payable
        
        Args:
            total_tax_liability (float): Total calculated tax liability
            tds_paid (float): TDS already deducted
            
        Returns:
            dict: Refund/payable details
        """
        difference = tds_paid - total_tax_liability
        
        return {
            'tds_paid': round(tds_paid, 2),
            'total_tax_liability': round(total_tax_liability, 2),
            'refund_due': round(difference, 2) if difference > 0 else 0.0,
            'additional_tax_payable': round(-difference, 2) if difference < 0 else 0.0,
            'net_position': 'refund' if difference > 0 else 'payable' if difference < 0 else 'nil'
        }
    
    @classmethod
    def compare_tax_regimes(cls, gross_income, old_regime_deductions, new_regime_deductions, tds_paid):
        """
        Compare Old vs New tax regimes and recommend the better option
        
        Args:
            gross_income (float): Gross total income
            old_regime_deductions (float): Total deductions under old regime
            new_regime_deductions (float): Total deductions under new regime (usually just standard deduction)
            tds_paid (float): TDS already paid
            
        Returns:
            dict: Comprehensive comparison and recommendation
        """
        # Calculate taxable income for both regimes
        old_taxable_income = gross_income - old_regime_deductions
        new_taxable_income = gross_income - new_regime_deductions
        
        # Calculate tax liability for both regimes
        old_regime_calc = cls.calculate_total_tax_liability(old_taxable_income, 'old')
        new_regime_calc = cls.calculate_total_tax_liability(new_taxable_income, 'new')
        
        # Calculate refund/payable for both
        old_regime_payment = cls.calculate_refund_or_payable(old_regime_calc['total_liability'], tds_paid)
        new_regime_payment = cls.calculate_refund_or_payable(new_regime_calc['total_liability'], tds_paid)
        
        # Determine savings and recommendation
        old_regime_net = old_regime_payment['refund_due'] - old_regime_payment['additional_tax_payable']
        new_regime_net = new_regime_payment['refund_due'] - new_regime_payment['additional_tax_payable']
        savings_by_old_regime = old_regime_net - new_regime_net
        
        recommended_regime = 'Old Regime' if savings_by_old_regime > 0 else 'New Regime'
        
        return {
            'gross_total_income': round(gross_income, 2),
            'old_regime': {
                'taxable_income': old_regime_calc['taxable_income'],
                'deductions': round(old_regime_deductions, 2),
                'tax_calculation': old_regime_calc,
                'payment_details': old_regime_payment
            },
            'new_regime': {
                'taxable_income': new_regime_calc['taxable_income'],
                'deductions': round(new_regime_deductions, 2),
                'tax_calculation': new_regime_calc,
                'payment_details': new_regime_payment
            },
            'comparison': {
                'savings_by_old_regime': round(savings_by_old_regime, 2),
                'recommended_regime': recommended_regime,
                'recommendation_reason': f"Save ₹{abs(savings_by_old_regime):,.2f} by choosing {recommended_regime}"
            }
        }


class DeductionCalculator:
    """
    Helper class for calculating various tax deductions
    """
    
    @staticmethod
    def calculate_hra_exemption(hra_received, basic_salary, rent_paid=None, is_metro_city=True):
        """
        Calculate HRA exemption according to Section 10(13A) of Income Tax Act
        
        HRA exemption is the MINIMUM of three amounts:
        1. Actual HRA received from employer
        2. 50% of (Basic + DA) for metro cities OR 40% for non-metro cities  
        3. Actual rent paid minus 10% of (Basic + DA)
        
        Args:
            hra_received (float): HRA component received from employer
            basic_salary (float): Basic salary + DA amount
            rent_paid (float): Actual rent paid (required for accurate calculation)
            is_metro_city (bool): True for metro cities (Delhi, Mumbai, Chennai, Kolkata)
            
        Returns:
            float: HRA exemption amount (minimum of the three conditions)
        """
        if not hra_received or hra_received <= 0:
            return 0.0
            
        # Calculate the three conditions for HRA exemption (Section 10(13A))
        
        # Condition 1: Actual HRA received
        condition_1 = hra_received
        
        # Condition 2: 50% (metro) or 40% (non-metro) of Basic + DA
        percentage = 0.5 if is_metro_city else 0.4
        condition_2 = basic_salary * percentage
        
        # Condition 3: Actual rent paid minus 10% of Basic + DA
        if rent_paid and rent_paid > 0:
            condition_3 = max(0, rent_paid - (basic_salary * 0.1))
        else:
            # If no rent data provided, we cannot calculate condition 3 accurately
            # According to IT rules, rent receipts are mandatory for HRA exemption
            # Without rent data, condition 3 = 0 (most conservative and legally correct approach)
            condition_3 = 0
        
        # HRA exemption is MINIMUM of all three conditions (as per Section 10(13A))
        exemption = min(condition_1, condition_2, condition_3)
        
        return round(exemption, 2)
    
    @staticmethod
    def calculate_section_80c(elss_investments, employee_pf, other_80c_investments=0):
        """
        Calculate Section 80C deduction (capped at ₹1.5L)
        
        Args:
            elss_investments (float): ELSS mutual fund investments
            employee_pf (float): Employee PF contribution
            other_80c_investments (float): Other 80C eligible investments
            
        Returns:
            float: Section 80C deduction amount
        """
        total_80c = elss_investments + employee_pf + other_80c_investments
        return min(150000, total_80c)  # Capped at ₹1.5L
    
    @staticmethod
    def calculate_section_80ccd_1b(nps_additional_contribution):
        """
        Calculate Section 80CCD(1B) deduction for NPS (capped at ₹50K)
        
        Args:
            nps_additional_contribution (float): Additional NPS contribution
            
        Returns:
            float: Section 80CCD(1B) deduction amount
        """
        return min(50000, nps_additional_contribution)  # Capped at ₹50K
    
    @staticmethod
    def calculate_old_regime_deductions(hra_received, basic_salary, elss_investments, 
                                      employee_pf, nps_additional, professional_tax, 
                                      standard_deduction=50000, rent_paid=None):
        """
        Calculate total deductions available under Old Tax Regime
        
        Returns:
            dict: Breakdown of all deductions
        """
        hra_exemption = DeductionCalculator.calculate_hra_exemption(
            hra_received, basic_salary, rent_paid
        )
        section_80c = DeductionCalculator.calculate_section_80c(
            elss_investments, employee_pf
        )
        section_80ccd_1b = DeductionCalculator.calculate_section_80ccd_1b(
            nps_additional
        )
        
        total_deductions = (
            hra_exemption + section_80c + section_80ccd_1b + 
            standard_deduction + professional_tax
        )
        
        return {
            'hra_exemption': round(hra_exemption, 2),
            'section_80c': round(section_80c, 2),
            'section_80ccd_1b': round(section_80ccd_1b, 2),
            'standard_deduction': round(standard_deduction, 2),
            'professional_tax': round(professional_tax, 2),
            'total_deductions': round(total_deductions, 2)
        }
    
    @staticmethod
    def calculate_new_regime_deductions(standard_deduction=75000):
        """
        Calculate deductions available under New Tax Regime (2024-25: ₹75K standard deduction)
        
        Returns:
            dict: New regime deduction breakdown
        """
        return {
            'standard_deduction': round(standard_deduction, 2),
            'total_deductions': round(standard_deduction, 2)
        }