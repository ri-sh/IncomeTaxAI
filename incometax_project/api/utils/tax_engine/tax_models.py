"""
Tax Models and Data Structures
Defines all data models and constants for tax calculations
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class TaxRegime(Enum):
    """Tax regime enumeration"""
    OLD = "old"
    NEW = "new"


class CapitalGainType(Enum):
    """Types of capital gains"""
    STCG_111A = "stcg_111a"  # Short-term equity with STT
    LTCG_112A = "ltcg_112a"  # Long-term equity with STT
    OTHER_STCG = "other_stcg"  # Other short-term capital gains
    OTHER_LTCG = "other_ltcg"  # Other long-term capital gains


@dataclass
class TaxSlabs:
    """Tax slab configuration"""
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
    
    SURCHARGE_SLABS = [
        (5000000, 0.0),     # Up to ₹50L: 0%
        (10000000, 0.10),   # ₹50L to ₹1Cr: 10%
        (20000000, 0.15),   # ₹1Cr to ₹2Cr: 15%
        (50000000, 0.25),   # ₹2Cr to ₹5Cr: 25%
        (float('inf'), 0.37) # Above ₹5Cr: 37% (Old) / 25% (New)
    ]


@dataclass
class TaxConstants:
    """Tax calculation constants for FY 2024-25"""
    CESS_RATE = 0.04  # 4%
    LTCG_EXEMPTION_LIMIT = 125000  # ₹1.25L
    STCG_TAX_RATE = 0.15  # 15%
    LTCG_RATE_PRE_JULY = 0.10  # 10% before 23-Jul-2024
    LTCG_RATE_POST_JULY = 0.125  # 12.5% from 23-Jul-2024
    JULY_23_2024 = datetime(2024, 7, 23)
    
    # Rebate limits
    NEW_REGIME_REBATE_LIMIT = 700000  # ₹7L
    OLD_REGIME_REBATE_LIMIT = 500000  # ₹5L
    NEW_REGIME_REBATE_AMOUNT = 25000  # ₹25K
    OLD_REGIME_REBATE_AMOUNT = 12500  # ₹12.5K
    
    # Standard deductions
    NEW_REGIME_STANDARD_DEDUCTION = 75000  # ₹75K
    OLD_REGIME_STANDARD_DEDUCTION = 50000  # ₹50K
    
    # Section limits
    SECTION_80C_LIMIT = 150000  # ₹1.5L
    SECTION_80CCD_1B_LIMIT = 50000  # ₹50K
    SECTION_80D_NORMAL_LIMIT = 25000  # ₹25K
    SECTION_80D_SENIOR_LIMIT = 50000  # ₹50K
    SECTION_80D_MAX_LIMIT = 100000  # ₹1L
    SECTION_80TTA_LIMIT = 10000  # ₹10K
    SECTION_80TTB_LIMIT = 50000  # ₹50K


class CapitalGain:
    """Represents a capital gain transaction"""
    
    def __init__(self, amount: float, sale_date: datetime, holding_period: int, 
                 has_stt: bool = True, gain_type: CapitalGainType = None):
        self.amount = amount
        self.sale_date = sale_date
        self.holding_period = holding_period  # in months
        self.has_stt = has_stt
        self.gain_type = gain_type or self._determine_type()

    @property
    def is_long_term(self) -> bool:
        """Check if the gain is long-term (≥12 months)"""
        return self.holding_period >= 12

    @property
    def is_section_112a_applicable(self) -> bool:
        """Check if Section 112A applies (equity with STT, held ≥ 12 months)"""
        return self.is_long_term and self.has_stt and self.gain_type == CapitalGainType.LTCG_112A

    @property
    def is_section_111a_applicable(self) -> bool:
        """Check if Section 111A applies (equity with STT, held < 12 months)"""
        return not self.is_long_term and self.has_stt and self.gain_type == CapitalGainType.STCG_111A

    def _determine_type(self) -> CapitalGainType:
        """Auto-determine capital gain type based on properties"""
        if self.has_stt:
            return CapitalGainType.LTCG_112A if self.is_long_term else CapitalGainType.STCG_111A
        else:
            return CapitalGainType.OTHER_LTCG if self.is_long_term else CapitalGainType.OTHER_STCG


@dataclass
class IncomeData:
    """Structured income data"""
    salary_income: float = 0
    other_income: float = 0
    business_income: float = 0
    rental_income: float = 0
    
    # Capital gains
    stcg_111a: float = 0
    ltcg_112a: float = 0
    other_stcg: float = 0
    other_ltcg: float = 0
    
    @property
    def normal_income(self) -> float:
        """Calculate total normal income (excluding capital gains)"""
        return self.salary_income + self.other_income + self.business_income + self.rental_income
    
    @property
    def total_capital_gains(self) -> float:
        """Calculate total capital gains"""
        return self.stcg_111a + self.ltcg_112a + self.other_stcg + self.other_ltcg
    
    @property
    def total_income(self) -> float:
        """Calculate total income including capital gains"""
        return self.normal_income + self.total_capital_gains


@dataclass
class DeductionData:
    """Structured deduction data"""
    # HRA related
    hra_received: float = 0
    basic_salary: float = 0
    rent_paid: Optional[float] = None
    is_metro_city: bool = True
    
    # Section 80C
    elss_investments: float = 0
    employee_pf: float = 0
    ppf_amount: float = 0
    life_insurance: float = 0
    nsc: float = 0
    home_loan_principal: float = 0
    
    # Section 80CCD(1B)
    nps_additional: float = 0
    
    # Section 80D
    health_insurance_premium: float = 0
    parents_health_insurance: float = 0
    age_above_60: bool = False
    parents_age_above_60: bool = False
    
    # Section 80G
    charitable_donations: float = 0
    charity_type: str = '50_percent'
    
    # Section 80E
    education_loan_interest: float = 0
    loan_year: int = 1
    
    # Section 80TTA/TTB
    savings_interest: float = 0
    deposit_interest: float = 0
    
    # Other
    professional_tax: float = 0
    standard_deduction: float = 50000


@dataclass
class TaxCalculationResult:
    """Tax calculation result structure"""
    # Income breakdown
    normal_income: float
    capital_gains_income: float
    total_income: float
    normal_taxable_income: float
    
    # Deductions
    total_deductions: float
    deduction_breakdown: Dict[str, float]
    
    # Tax calculations
    normal_income_tax: float
    stcg_tax: float
    ltcg_tax: float
    other_capital_gains_tax: float
    total_tax_before_rebate: float
    
    # Rebate and final calculations
    rebate_87a: float
    tax_after_rebate: float
    surcharge: float
    cess: float
    final_tax_liability: float
    
    # Regime and summary
    regime: TaxRegime
    effective_tax_rate: float
    
    # Additional details
    ltcg_details: Dict[str, Any] = None
    stcg_details: Dict[str, Any] = None


@dataclass
class PaymentCalculation:
    """Tax payment calculation result"""
    total_tax_liability: float
    tds_paid: float
    advance_tax_paid: float = 0
    self_assessment_tax: float = 0
    
    @property
    def total_paid(self) -> float:
        return self.tds_paid + self.advance_tax_paid + self.self_assessment_tax
    
    @property
    def refund_due(self) -> float:
        return max(0, self.total_paid - self.total_tax_liability)
    
    @property
    def additional_tax_payable(self) -> float:
        return max(0, self.total_tax_liability - self.total_paid)
    
    @property
    def net_position(self) -> str:
        if self.refund_due > 0:
            return 'refund'
        elif self.additional_tax_payable > 0:
            return 'payable'
        else:
            return 'nil'