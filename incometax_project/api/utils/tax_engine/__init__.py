"""
Tax Engine Package
Modular tax calculation system following SOLID principles

Package Structure:
- tax_models.py: Data models and constants
- core.py: Core tax calculation engines  
- deductions.py: Deduction calculators
- calculator.py: Main tax calculator interface
"""

# Import all models and constants
from .tax_models import (
    TaxRegime, CapitalGainType, TaxSlabs, TaxConstants,
    CapitalGain, IncomeData, DeductionData, 
    TaxCalculationResult, PaymentCalculation
)

# Import core engines
from .core import TaxEngine, CapitalGainsEngine

# Import deduction calculators
from .deductions import (
    DeductionCalculator, HRACalculator, Section80CCalculator,
    Section80CCDCalculator, Section80DCalculator, Section80GCalculator,
    Section80ECalculator, Section80TTACalculator
)

# Import ESOP calculator
from .esop_calculator import ESOPCalculator, ESOPTransaction

# Import main calculator interface
from .calculator import IncomeTaxCalculator

# Export main classes for backward compatibility
__all__ = [
    # Main interface
    'IncomeTaxCalculator',
    'DeductionCalculator',
    
    # Models and enums
    'TaxRegime',
    'CapitalGainType', 
    'CapitalGain',
    'IncomeData',
    'DeductionData',
    'TaxCalculationResult',
    'PaymentCalculation',
    
    # Constants
    'TaxSlabs',
    'TaxConstants',
    
    # Core engines
    'TaxEngine',
    'CapitalGainsEngine',
    
    # Section-wise calculators
    'HRACalculator',
    'Section80CCalculator',
    'Section80CCDCalculator', 
    'Section80DCalculator',
    'Section80GCalculator',
    'Section80ECalculator',
    'Section80TTACalculator',
    
    # ESOP calculators
    'ESOPCalculator',
    'ESOPTransaction'
]