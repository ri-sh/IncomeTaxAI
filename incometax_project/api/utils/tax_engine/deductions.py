"""
Deduction Calculator Module
Handles all tax deduction calculations following Section-wise structure
"""

from typing import Dict, Optional
from .tax_models import TaxConstants, TaxRegime, DeductionData


class HRACalculator:
    """Section 10(13A) - House Rent Allowance calculator"""
    
    @staticmethod
    def calculate_hra_exemption(hra_received: float, basic_salary: float, 
                              rent_paid: Optional[float] = None, is_metro_city: bool = True) -> float:
        """
        Calculate HRA exemption according to Section 10(13A)
        
        HRA exemption is the MINIMUM of three amounts:
        1. Actual HRA received from employer
        2. 50% of (Basic + DA) for metro cities OR 40% for non-metro cities  
        3. Actual rent paid minus 10% of (Basic + DA)
        
        Args:
            hra_received: HRA component received from employer
            basic_salary: Basic salary + DA amount
            rent_paid: Actual rent paid (if available)
            is_metro_city: True for metro cities (Delhi, Mumbai, Chennai, Kolkata)
            
        Returns:
            HRA exemption amount
        """
        if not hra_received or hra_received <= 0:
            return 0.0
        
        # Condition 1: Actual HRA received
        condition_1 = hra_received
        
        # Condition 2: 50% (metro) or 40% (non-metro) of Basic + DA
        percentage = 0.5 if is_metro_city else 0.4
        condition_2 = basic_salary * percentage
        
        # Condition 3: Actual rent paid minus 10% of Basic + DA
        if rent_paid and rent_paid > 0:
            condition_3 = max(0, rent_paid - (basic_salary * 0.1))
        else:
            # Practical approach: estimate rent as 60% of HRA (common scenario)
            estimated_rent = hra_received * 0.6
            condition_3 = max(0, estimated_rent - (basic_salary * 0.1))
        
        # HRA exemption is MINIMUM of all three conditions
        exemption = min(condition_1, condition_2, condition_3)
        return round(exemption, 2)


class Section80CCalculator:
    """Section 80C - Investment deductions calculator"""
    
    @staticmethod
    def calculate_section_80c_deduction(elss_investments: float = 0, employee_pf: float = 0, 
                                      ppf_amount: float = 0, life_insurance: float = 0,
                                      nsc: float = 0, home_loan_principal: float = 0,
                                      other_80c_investments: float = 0) -> Dict[str, float]:
        """
        Calculate Section 80C deduction (capped at ₹1.5L)
        
        Args:
            elss_investments: ELSS mutual fund investments
            employee_pf: Employee PF contribution
            ppf_amount: PPF investment
            life_insurance: Life insurance premium
            nsc: National Savings Certificate
            home_loan_principal: Home loan principal repayment
            other_80c_investments: Other 80C eligible investments
            
        Returns:
            Dictionary with 80C calculation breakdown
        """
        investments = {
            'elss_investments': elss_investments,
            'employee_pf': employee_pf,
            'ppf_amount': ppf_amount,
            'life_insurance': life_insurance,
            'nsc': nsc,
            'home_loan_principal': home_loan_principal,
            'other_80c_investments': other_80c_investments
        }
        
        total_80c = sum(investments.values())
        allowable_deduction = min(total_80c, TaxConstants.SECTION_80C_LIMIT)
        
        return {
            **investments,
            'total_80c_investments': round(total_80c, 2),
            'allowable_deduction': round(allowable_deduction, 2),
            'limit': TaxConstants.SECTION_80C_LIMIT,
            'excess_amount': round(max(0, total_80c - TaxConstants.SECTION_80C_LIMIT), 2)
        }


class Section80CCDCalculator:
    """Section 80CCD(1B) - Additional NPS deduction calculator"""
    
    @staticmethod
    def calculate_section_80ccd_1b_deduction(nps_additional_contribution: float) -> Dict[str, float]:
        """
        Calculate Section 80CCD(1B) deduction for additional NPS contribution
        
        Args:
            nps_additional_contribution: Additional NPS contribution (beyond 80C)
            
        Returns:
            Dictionary with 80CCD(1B) calculation details
        """
        allowable_deduction = min(nps_additional_contribution, TaxConstants.SECTION_80CCD_1B_LIMIT)
        
        return {
            'nps_additional_contribution': round(nps_additional_contribution, 2),
            'allowable_deduction': round(allowable_deduction, 2),
            'limit': TaxConstants.SECTION_80CCD_1B_LIMIT,
            'excess_amount': round(max(0, nps_additional_contribution - TaxConstants.SECTION_80CCD_1B_LIMIT), 2)
        }


class Section80DCalculator:
    """Section 80D - Health insurance premium deduction calculator"""
    
    @staticmethod
    def calculate_section_80d_deduction(health_insurance_premium: float = 0, 
                                      parents_health_insurance: float = 0,
                                      age_above_60: bool = False, 
                                      parents_age_above_60: bool = False) -> Dict[str, float]:
        """
        Calculate Section 80D deduction for health insurance premiums
        
        Limits for FY 2024-25:
        - Normal individuals: ₹25K (self/family), ₹25K (parents)
        - Senior citizens (>60): ₹50K (self/family), ₹50K (parents)
        - Overall cap: ₹1L if anyone is senior citizen, else ₹50K
        
        Args:
            health_insurance_premium: Premium for self/family
            parents_health_insurance: Premium for parents
            age_above_60: Whether individual/spouse is above 60
            parents_age_above_60: Whether parents are above 60
            
        Returns:
            Dictionary with 80D calculation breakdown
        """
        # Determine limits based on age
        self_limit = TaxConstants.SECTION_80D_SENIOR_LIMIT if age_above_60 else TaxConstants.SECTION_80D_NORMAL_LIMIT
        parents_limit = TaxConstants.SECTION_80D_SENIOR_LIMIT if parents_age_above_60 else TaxConstants.SECTION_80D_NORMAL_LIMIT
        
        # Calculate deductions within individual limits
        self_deduction = min(health_insurance_premium, self_limit)
        parents_deduction = min(parents_health_insurance, parents_limit)
        
        # Total before overall cap
        total_before_cap = self_deduction + parents_deduction
        
        # Apply overall cap
        is_senior_citizen_case = age_above_60 or parents_age_above_60
        overall_limit = TaxConstants.SECTION_80D_MAX_LIMIT if is_senior_citizen_case else TaxConstants.SECTION_80D_NORMAL_LIMIT * 2
        
        total_allowable = min(total_before_cap, overall_limit)
        
        return {
            'health_insurance_premium': round(health_insurance_premium, 2),
            'parents_health_insurance': round(parents_health_insurance, 2),
            'self_limit': self_limit,
            'parents_limit': parents_limit,
            'self_deduction': round(self_deduction, 2),
            'parents_deduction': round(parents_deduction, 2),
            'total_before_cap': round(total_before_cap, 2),
            'overall_limit': overall_limit,
            'allowable_deduction': round(total_allowable, 2),
            'is_senior_citizen_case': is_senior_citizen_case
        }


class Section80GCalculator:
    """Section 80G - Charitable donations deduction calculator"""
    
    @staticmethod
    def calculate_section_80g_deduction(donation_amount: float, 
                                      charity_type: str = '50_percent',
                                      certificate_available: bool = True) -> Dict[str, float]:
        """
        Calculate Section 80G deduction for charitable donations
        
        Args:
            donation_amount: Total donation amount
            charity_type: Type of charity ('50_percent', '100_percent_with_limit', '100_percent_no_limit')
            certificate_available: Whether valid 80G certificate is available
            
        Returns:
            Dictionary with 80G calculation breakdown
        """
        if not certificate_available or donation_amount <= 0:
            return {
                'donation_amount': round(donation_amount, 2),
                'deduction_amount': 0.0,
                'qualifying_donation': 0.0,
                'deduction_percentage': 0,
                'note': 'Valid 80G certificate required for deduction'
            }
        
        # Determine deduction based on charity type
        if charity_type == '100_percent_no_limit':
            # Prime Minister's National Relief Fund, National Defence Fund, etc.
            deduction_amount = donation_amount
            deduction_percentage = 100
            
        elif charity_type == '100_percent_with_limit':
            # Certain government funds with 10% income limit
            deduction_amount = donation_amount
            deduction_percentage = 100
            
        else:  # '50_percent' - most common case
            # 50% deduction for most charitable institutions
            deduction_amount = donation_amount * 0.5
            deduction_percentage = 50
        
        return {
            'donation_amount': round(donation_amount, 2),
            'deduction_amount': round(deduction_amount, 2),
            'qualifying_donation': round(donation_amount, 2),
            'deduction_percentage': deduction_percentage,
            'charity_type': charity_type,
            'note': f'{deduction_percentage}% deduction on charitable donation'
        }


class Section80ECalculator:
    """Section 80E - Education loan interest deduction calculator"""
    
    @staticmethod
    def calculate_section_80e_deduction(education_loan_interest: float, 
                                      loan_year: int = 1) -> Dict[str, float]:
        """
        Calculate Section 80E deduction for education loan interest
        
        Features:
        - Full interest amount deductible (no upper limit)
        - Available for 8 consecutive years
        - Starts from the year interest payment begins
        
        Args:
            education_loan_interest: Interest paid on education loan
            loan_year: Which year of the loan (1-8)
            
        Returns:
            Dictionary with 80E calculation breakdown
        """
        if education_loan_interest <= 0:
            return {
                'education_loan_interest': 0.0,
                'deduction_amount': 0.0,
                'eligible_interest': 0.0,
                'loan_year': loan_year,
                'years_remaining': 0,
                'note': 'No education loan interest to claim'
            }
        
        # Section 80E allows full deduction for 8 consecutive years
        if loan_year <= 8:
            deduction_amount = education_loan_interest
            years_remaining = 8 - loan_year
            note = f'Full interest deductible (Year {loan_year} of 8)'
        else:
            deduction_amount = 0.0
            years_remaining = 0
            note = 'Deduction period expired (8 years completed)'
        
        return {
            'education_loan_interest': round(education_loan_interest, 2),
            'deduction_amount': round(deduction_amount, 2),
            'eligible_interest': round(education_loan_interest, 2),
            'loan_year': loan_year,
            'years_remaining': years_remaining,
            'note': note
        }


class Section80TTACalculator:
    """Section 80TTA/80TTB - Interest on savings deduction calculator"""
    
    @staticmethod
    def calculate_section_80tta_ttb_deduction(savings_interest: float = 0, 
                                            deposit_interest: float = 0,
                                            age_above_60: bool = False) -> Dict[str, float]:
        """
        Calculate Section 80TTA/TTB deduction for interest on savings/deposits
        
        Rules:
        - 80TTA (below 60): Up to ₹10K on savings account interest only
        - 80TTB (above 60): Up to ₹50K on all deposit interest (savings + FD + others)
        
        Args:
            savings_interest: Interest on savings accounts
            deposit_interest: Interest on deposits (FD, etc.)
            age_above_60: Whether individual is senior citizen
            
        Returns:
            Dictionary with 80TTA/TTB calculation breakdown
        """
        total_interest = savings_interest + deposit_interest
        
        if total_interest <= 0:
            return {
                'savings_interest': 0.0,
                'deposit_interest': 0.0,
                'total_interest': 0.0,
                'deduction_amount': 0.0,
                'section': 'None',
                'limit': 0,
                'note': 'No interest income to claim'
            }
        
        if age_above_60:
            # Section 80TTB for senior citizens
            # Deduction up to ₹50K on all deposit interest
            limit = TaxConstants.SECTION_80TTB_LIMIT
            section = '80TTB'
            eligible_interest = total_interest  # All interest eligible
            deduction_amount = min(eligible_interest, limit)
            note = f'Senior citizen: Up to ₹{limit:,} deduction on all deposit interest'
        else:
            # Section 80TTA for others
            # Deduction up to ₹10K on savings account interest only
            limit = TaxConstants.SECTION_80TTA_LIMIT
            section = '80TTA'
            eligible_interest = savings_interest  # Only savings interest eligible
            deduction_amount = min(eligible_interest, limit)
            note = f'Non-senior citizen: Up to ₹{limit:,} on savings account interest only'
        
        return {
            'savings_interest': round(savings_interest, 2),
            'deposit_interest': round(deposit_interest, 2),
            'total_interest': round(total_interest, 2),
            'eligible_interest': round(eligible_interest, 2),
            'deduction_amount': round(deduction_amount, 2),
            'section': section,
            'limit': limit,
            'note': note
        }


class DeductionCalculator:
    """
    Main deduction calculator that orchestrates all section-wise calculations
    
    This class maintains backward compatibility while providing enhanced accuracy
    """
    
    @staticmethod
    def calculate_new_regime_deductions(standard_deduction: float = None) -> Dict[str, float]:
        """
        Calculate deductions available under New Tax Regime (very limited)
        
        Args:
            standard_deduction: Standard deduction amount (₹75K for FY 2024-25)
            
        Returns:
            Dictionary with new regime deduction breakdown
        """
        if standard_deduction is None:
            standard_deduction = TaxConstants.NEW_REGIME_STANDARD_DEDUCTION
        
        return {
            'standard_deduction': round(standard_deduction, 2),
            'total_deductions': round(standard_deduction, 2),
            'note': 'New regime allows very limited deductions'
        }
    
    @staticmethod
    def calculate_old_regime_deductions(deduction_data: DeductionData = None, **kwargs) -> Dict[str, float]:
        """
        Calculate comprehensive deductions under Old Tax Regime
        
        Args:
            deduction_data: Structured deduction data
            **kwargs: Individual deduction parameters (for backward compatibility)
            
        Returns:
            Dictionary with complete old regime deduction breakdown
        """
        # Handle both new structured input and legacy kwargs
        if deduction_data is None:
            deduction_data = DeductionData(
                hra_received=kwargs.get('hra_received', 0),
                basic_salary=kwargs.get('basic_salary', 0),
                rent_paid=kwargs.get('rent_paid'),
                is_metro_city=kwargs.get('is_metro_city', True),
                elss_investments=kwargs.get('elss_investments', 0),
                employee_pf=kwargs.get('employee_pf', 0),
                ppf_amount=kwargs.get('ppf_amount', 0),
                life_insurance=kwargs.get('life_insurance', 0),
                nps_additional=kwargs.get('nps_additional', 0),
                health_insurance_premium=kwargs.get('health_insurance_premium', 0),
                parents_health_insurance=kwargs.get('parents_health_insurance', 0),
                age_above_60=kwargs.get('age_above_60', False),
                parents_age_above_60=kwargs.get('parents_age_above_60', False),
                charitable_donations=kwargs.get('charitable_donations', 0),
                charity_type=kwargs.get('charity_type', '50_percent'),
                education_loan_interest=kwargs.get('education_loan_interest', 0),
                loan_year=kwargs.get('loan_year', 1),
                savings_interest=kwargs.get('savings_interest', 0),
                deposit_interest=kwargs.get('deposit_interest', 0),
                professional_tax=kwargs.get('professional_tax', 0)
            )
        
        # Calculate individual deductions
        hra_details = HRACalculator.calculate_hra_exemption(
            deduction_data.hra_received, 
            deduction_data.basic_salary, 
            deduction_data.rent_paid, 
            deduction_data.is_metro_city
        )
        
        section_80c_details = Section80CCalculator.calculate_section_80c_deduction(
            deduction_data.elss_investments,
            deduction_data.employee_pf,
            deduction_data.ppf_amount,
            deduction_data.life_insurance,
            deduction_data.nsc,
            deduction_data.home_loan_principal
        )
        
        section_80ccd_1b_details = Section80CCDCalculator.calculate_section_80ccd_1b_deduction(
            deduction_data.nps_additional
        )
        
        section_80d_details = Section80DCalculator.calculate_section_80d_deduction(
            deduction_data.health_insurance_premium,
            deduction_data.parents_health_insurance,
            deduction_data.age_above_60,
            deduction_data.parents_age_above_60
        )
        
        section_80g_details = Section80GCalculator.calculate_section_80g_deduction(
            deduction_data.charitable_donations,
            deduction_data.charity_type,
            certificate_available=True
        )
        
        section_80e_details = Section80ECalculator.calculate_section_80e_deduction(
            deduction_data.education_loan_interest,
            deduction_data.loan_year
        )
        
        section_80tta_ttb_details = Section80TTACalculator.calculate_section_80tta_ttb_deduction(
            deduction_data.savings_interest,
            deduction_data.deposit_interest,
            deduction_data.age_above_60
        )
        
        # Standard deduction and professional tax
        standard_deduction = TaxConstants.OLD_REGIME_STANDARD_DEDUCTION
        professional_tax = deduction_data.professional_tax
        
        # Calculate total deductions
        total_deductions = (
            hra_details +
            section_80c_details['allowable_deduction'] +
            section_80ccd_1b_details['allowable_deduction'] +
            section_80d_details['allowable_deduction'] +
            section_80g_details['deduction_amount'] +
            section_80e_details['deduction_amount'] +
            section_80tta_ttb_details['deduction_amount'] +
            standard_deduction +
            professional_tax
        )
        
        return {
            'hra_exemption': round(hra_details, 2),
            'section_80c': section_80c_details['allowable_deduction'],
            'section_80c_details': section_80c_details,
            'section_80ccd_1b': section_80ccd_1b_details['allowable_deduction'],
            'section_80ccd_1b_details': section_80ccd_1b_details,
            'section_80d': section_80d_details['allowable_deduction'],
            'section_80d_details': section_80d_details,
            'section_80g': section_80g_details['deduction_amount'],
            'section_80g_details': section_80g_details,
            'section_80e': section_80e_details['deduction_amount'],
            'section_80e_details': section_80e_details,
            'section_80tta_ttb': section_80tta_ttb_details['deduction_amount'],
            'section_80tta_ttb_details': section_80tta_ttb_details,
            'standard_deduction': round(standard_deduction, 2),
            'professional_tax': round(professional_tax, 2),
            'total_deductions': round(total_deductions, 2)
        }
    
    # Backward compatibility methods (delegating to section-specific calculators)
    
    @staticmethod
    def calculate_hra_exemption(hra_received: float, basic_salary: float, 
                              rent_paid: Optional[float] = None, is_metro_city: bool = True) -> float:
        """Backward compatible HRA calculation"""
        return HRACalculator.calculate_hra_exemption(hra_received, basic_salary, rent_paid, is_metro_city)
    
    @staticmethod
    def calculate_section_80c(elss_investments: float, employee_pf: float, 
                            other_80c_investments: float = 0) -> float:
        """Backward compatible Section 80C calculation"""
        details = Section80CCalculator.calculate_section_80c_deduction(
            elss_investments, employee_pf, other_80c_investments=other_80c_investments
        )
        return details['allowable_deduction']
    
    @staticmethod
    def calculate_section_80ccd_1b(nps_additional_contribution: float) -> float:
        """Backward compatible Section 80CCD(1B) calculation"""
        details = Section80CCDCalculator.calculate_section_80ccd_1b_deduction(nps_additional_contribution)
        return details['allowable_deduction']
    
    @staticmethod
    def calculate_section_80d(health_insurance_premium: float, parents_health_insurance: float = 0,
                            age_above_60: bool = False, parents_age_above_60: bool = False) -> float:
        """Backward compatible Section 80D calculation"""
        details = Section80DCalculator.calculate_section_80d_deduction(
            health_insurance_premium, parents_health_insurance, age_above_60, parents_age_above_60
        )
        return details['allowable_deduction']
    
    @staticmethod
    def calculate_section_80g(donation_amount: float, charity_type: str = '50_percent',
                            certificate_available: bool = True) -> Dict[str, float]:
        """Backward compatible Section 80G calculation"""
        return Section80GCalculator.calculate_section_80g_deduction(donation_amount, charity_type, certificate_available)
    
    @staticmethod
    def calculate_section_80e(education_loan_interest: float, loan_year: int = 1) -> Dict[str, float]:
        """Backward compatible Section 80E calculation"""
        return Section80ECalculator.calculate_section_80e_deduction(education_loan_interest, loan_year)
    
    @staticmethod
    def calculate_section_80tta_ttb(savings_interest: float, age_above_60: bool = False) -> Dict[str, float]:
        """Backward compatible Section 80TTA/TTB calculation"""
        return Section80TTACalculator.calculate_section_80tta_ttb_deduction(
            savings_interest, 0, age_above_60
        )