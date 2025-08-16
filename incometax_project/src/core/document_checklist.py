"""
Document Checklist System for Indian Income Tax Filing
Identifies missing documents required for ITR filing
"""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path

class DocumentType(Enum):
    """Types of tax documents"""
    # Salary Documents
    FORM_16 = "form_16"
    FORM_16A = "form_16a"
    SALARY_SLIPS = "salary_slips"
    
    # Bank Documents
    BANK_STATEMENTS = "bank_statements"
    INTEREST_CERTIFICATES = "interest_certificates"
    
    # Investment Documents
    LIC_PREMIUM_RECEIPTS = "lic_premium_receipts"
    ELSS_STATEMENTS = "elss_statements"
    PPF_STATEMENTS = "ppf_statements"
    EPF_STATEMENTS = "epf_statements"
    NSC_CERTIFICATES = "nsc_certificates"
    SUKANYA_SAMRIDDHI = "sukanya_samriddhi"
    
    # Insurance
    HEALTH_INSURANCE_PREMIUM = "health_insurance_premium"
    TERM_INSURANCE_PREMIUM = "term_insurance_premium"
    
    # House Property
    HOME_LOAN_INTEREST = "home_loan_interest"
    HOME_LOAN_PRINCIPAL = "home_loan_principal"
    RENT_RECEIPTS = "rent_receipts"
    PROPERTY_TAX_RECEIPTS = "property_tax_receipts"
    
    # Other Income
    FD_INTEREST_CERTIFICATES = "fd_interest_certificates"
    RD_INTEREST_CERTIFICATES = "rd_interest_certificates"
    DIVIDEND_STATEMENTS = "dividend_statements"
    CAPITAL_GAINS_STATEMENTS = "capital_gains_statements"
    
    # Business/Professional
    BUSINESS_INCOME_STATEMENTS = "business_income_statements"
    PROFESSIONAL_RECEIPTS = "professional_receipts"
    
    # Deductions
    CHARITABLE_DONATIONS = "charitable_donations"
    EDUCATION_LOAN_INTEREST = "education_loan_interest"
    MEDICAL_TREATMENT_RECEIPTS = "medical_treatment_receipts"
    
    # Identity Documents
    PAN_CARD = "pan_card"
    AADHAAR_CARD = "aadhaar_card"

class Priority(Enum):
    """Document priority levels"""
    MANDATORY = "mandatory"
    HIGHLY_RECOMMENDED = "highly_recommended"
    OPTIONAL = "optional"

@dataclass
class DocumentRequirement:
    """Document requirement specification"""
    doc_type: DocumentType
    name: str
    description: str
    priority: Priority
    applicable_itr_forms: List[str]
    section_reference: Optional[str] = None
    max_deduction_limit: Optional[float] = None
    conditions: Optional[List[str]] = None

class DocumentChecklist:
    """Manages document requirements and missing document detection"""
    
    def __init__(self):
        self.requirements = self._initialize_requirements()
        self.detected_documents: Set[DocumentType] = set()
        
    def _initialize_requirements(self) -> List[DocumentRequirement]:
        """Initialize comprehensive document requirements for Indian tax filing"""
        return [
            # Mandatory Documents
            DocumentRequirement(
                DocumentType.FORM_16, 
                "Form 16 - TDS Certificate",
                "Annual TDS certificate from employer showing salary and tax deducted",
                Priority.MANDATORY,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 192"
            ),
            
            DocumentRequirement(
                DocumentType.PAN_CARD,
                "PAN Card",
                "Permanent Account Number card for tax identification",
                Priority.MANDATORY,
                ["ITR-1", "ITR-2", "ITR-3", "ITR-4"],
                conditions=["Required for all tax filings"]
            ),
            
            # Salary Related
            DocumentRequirement(
                DocumentType.SALARY_SLIPS,
                "Salary Slips",
                "Monthly salary slips for the financial year",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                conditions=["To verify Form 16 details"]
            ),
            
            # Investment Documents (Section 80C)
            DocumentRequirement(
                DocumentType.LIC_PREMIUM_RECEIPTS,
                "LIC Premium Receipts",
                "Life Insurance premium payment receipts",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80C",
                150000.0,
                ["Part of ₹1.5L limit under Section 80C"]
            ),
            
            DocumentRequirement(
                DocumentType.ELSS_STATEMENTS,
                "ELSS Investment Statements",
                "Equity Linked Savings Scheme investment statements",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80C",
                150000.0
            ),
            
            DocumentRequirement(
                DocumentType.PPF_STATEMENTS,
                "PPF Account Statements",
                "Public Provident Fund account statements",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80C",
                150000.0
            ),
            
            DocumentRequirement(
                DocumentType.EPF_STATEMENTS,
                "EPF Statements",
                "Employee Provident Fund statements",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80C",
                150000.0
            ),
            
            # Bank Documents
            DocumentRequirement(
                DocumentType.BANK_STATEMENTS,
                "Bank Statements",
                "Bank account statements showing all transactions",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3", "ITR-4"],
                conditions=["Required for income verification"]
            ),
            
            DocumentRequirement(
                DocumentType.INTEREST_CERTIFICATES,
                "Bank Interest Certificates",
                "Certificates showing interest earned on savings/FD accounts",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Income from Other Sources",
                conditions=["Required if interest > ₹10,000"]
            ),
            
            DocumentRequirement(
                DocumentType.FD_INTEREST_CERTIFICATES,
                "Fixed Deposit Interest Certificates",
                "Interest certificates from fixed deposits",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Income from Other Sources"
            ),
            
            # Insurance (Section 80D)
            DocumentRequirement(
                DocumentType.HEALTH_INSURANCE_PREMIUM,
                "Health Insurance Premium Receipts",
                "Medical/health insurance premium payment receipts",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80D",
                75000.0,
                ["₹25K for self/family, ₹50K additional for parents"]
            ),
            
            # House Property
            DocumentRequirement(
                DocumentType.HOME_LOAN_INTEREST,
                "Home Loan Interest Certificate",
                "Certificate showing interest paid on home loan",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 24",
                200000.0,
                ["₹2L limit for self-occupied property"]
            ),
            
            DocumentRequirement(
                DocumentType.HOME_LOAN_PRINCIPAL,
                "Home Loan Principal Repayment",
                "Certificate showing principal amount repaid",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80C",
                150000.0
            ),
            
            DocumentRequirement(
                DocumentType.RENT_RECEIPTS,
                "House Rent Receipts",
                "Rent receipts for HRA exemption claim",
                Priority.HIGHLY_RECOMMENDED,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 10(13A)",
                conditions=["Required for HRA claim if rent > ₹1L/year"]
            ),
            
            # Other Deductions
            DocumentRequirement(
                DocumentType.EDUCATION_LOAN_INTEREST,
                "Education Loan Interest Certificate",
                "Interest paid on education loan",
                Priority.OPTIONAL,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80E",
                conditions=["No upper limit"]
            ),
            
            DocumentRequirement(
                DocumentType.CHARITABLE_DONATIONS,
                "Donation Receipts",
                "Receipts for donations to charitable organizations",
                Priority.OPTIONAL,
                ["ITR-1", "ITR-2", "ITR-3"],
                "Section 80G"
            ),
            
            # Capital Gains
            DocumentRequirement(
                DocumentType.CAPITAL_GAINS_STATEMENTS,
                "Capital Gains Statements",
                "Statements showing capital gains/losses from investments",
                Priority.OPTIONAL,
                ["ITR-2", "ITR-3"],
                "Capital Gains",
                conditions=["Required if you sold investments/property"]
            ),
            
            # Form 16A
            DocumentRequirement(
                DocumentType.FORM_16A,
                "Form 16A - TDS on Non-Salary Income",
                "TDS certificates for non-salary income",
                Priority.OPTIONAL,
                ["ITR-1", "ITR-2", "ITR-3"],
                "TDS on Other Income",
                conditions=["If TDS deducted on bank interest, rent, etc."]
            )
        ]
    
    def mark_document_found(self, doc_type: DocumentType):
        """Mark a document as found/available"""
        self.detected_documents.add(doc_type)
    
    def get_missing_documents(self, itr_form: str = "ITR-1") -> Dict[Priority, List[DocumentRequirement]]:
        """Get missing documents categorized by priority"""
        missing = {
            Priority.MANDATORY: [],
            Priority.HIGHLY_RECOMMENDED: [],
            Priority.OPTIONAL: []
        }
        
        for req in self.requirements:
            if (itr_form in req.applicable_itr_forms and 
                req.doc_type not in self.detected_documents):
                missing[req.priority].append(req)
        
        return missing
    
    def get_completion_percentage(self, itr_form: str = "ITR-1") -> float:
        """Calculate document completion percentage"""
        applicable_docs = [req for req in self.requirements 
                          if itr_form in req.applicable_itr_forms]
        
        if not applicable_docs:
            return 100.0
        
        found_count = sum(1 for req in applicable_docs 
                         if req.doc_type in self.detected_documents)
        
        return (found_count / len(applicable_docs)) * 100
    
    def get_missing_document_suggestions(self, itr_form: str = "ITR-1") -> List[str]:
        """Get AI-friendly suggestions for missing documents"""
        missing = self.get_missing_documents(itr_form)
        suggestions = []
        
        # Priority-based suggestions
        if missing[Priority.MANDATORY]:
            suggestions.append("🚨 URGENT: You're missing mandatory documents:")
            for req in missing[Priority.MANDATORY]:
                suggestions.append(f"   • {req.name}: {req.description}")
        
        if missing[Priority.HIGHLY_RECOMMENDED]:
            suggestions.append("⚠️  Important documents that could save you tax:")
            for req in missing[Priority.HIGHLY_RECOMMENDED]:
                deduction_info = f" (Save up to ₹{req.max_deduction_limit:,.0f})" if req.max_deduction_limit else ""
                suggestions.append(f"   • {req.name}{deduction_info}: {req.description}")
        
        if missing[Priority.OPTIONAL]:
            suggestions.append("💡 Optional documents for additional deductions:")
            for req in missing[Priority.OPTIONAL]:
                suggestions.append(f"   • {req.name}: {req.description}")
        
        return suggestions
    
    def get_document_checklist_summary(self, itr_form: str = "ITR-1") -> Dict:
        """Get complete checklist summary"""
        missing = self.get_missing_documents(itr_form)
        completion = self.get_completion_percentage(itr_form)
        
        return {
            "completion_percentage": completion,
            "total_documents": len([req for req in self.requirements 
                                  if itr_form in req.applicable_itr_forms]),
            "found_documents": len(self.detected_documents),
            "missing_mandatory": len(missing[Priority.MANDATORY]),
            "missing_recommended": len(missing[Priority.HIGHLY_RECOMMENDED]),
            "missing_optional": len(missing[Priority.OPTIONAL]),
            "missing_documents": missing,
            "suggestions": self.get_missing_document_suggestions(itr_form)
        }

# Example usage and testing
if __name__ == "__main__":
    checker = DocumentChecklist()
    
    # Simulate some found documents
    checker.mark_document_found(DocumentType.FORM_16)
    checker.mark_document_found(DocumentType.PAN_CARD)
    checker.mark_document_found(DocumentType.BANK_STATEMENTS)
    
    # Get summary
    summary = checker.get_document_checklist_summary("ITR-1")
    print(f"Completion: {summary['completion_percentage']:.1f}%")
    print(f"Missing mandatory: {summary['missing_mandatory']}")
    
    for suggestion in summary['suggestions']:
        print(suggestion)