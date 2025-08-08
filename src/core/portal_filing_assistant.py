"""
Portal Filing Assistant - Maps analyzed data to Income Tax Portal fields
Provides section-wise data for direct entry into official ITR forms
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import json

@dataclass
class PortalSection:
    """Represents a section in the income tax portal"""
    section_name: str
    form_reference: str
    fields: Dict[str, Any]
    instructions: List[str]
    notes: List[str]

@dataclass
class PortalFormData:
    """Complete portal form data ready for filing"""
    taxpayer_info: Dict[str, Any]
    income_sections: List[PortalSection]
    deduction_sections: List[PortalSection]
    tax_computation: Dict[str, Any]
    verification_data: Dict[str, Any]

class PortalFilingAssistant:
    """Converts analyzed tax data into portal-ready format"""
    
    def __init__(self):
        self.form_mapping = {
            "ITR-1": "For salary and one house property",
            "ITR-2": "For salary, house property, capital gains, other sources",
            "ITR-3": "For business/profession income",
            "ITR-4": "For presumptive business income"
        }
    
    def generate_portal_data(self, analysis: Dict[str, Any], taxpayer_info: Dict[str, Any] = None) -> PortalFormData:
        """Generate complete portal-ready data"""
        
        income = analysis['income_breakdown']
        deductions = analysis['deductions_summary']
        regime_comparison = analysis['regime_comparison']
        hra_calc = analysis['hra_calculation']
        
        # Determine ITR form
        itr_form = self._determine_itr_form(income)
        
        # Taxpayer information
        taxpayer_data = taxpayer_info or {}
        
        # Generate income sections
        income_sections = self._generate_income_sections(income, hra_calc)
        
        # Generate deduction sections
        deduction_sections = self._generate_deduction_sections(deductions, regime_comparison['recommended'])
        
        # Generate tax computation
        recommended_regime = regime_comparison[f"{regime_comparison['recommended']}_regime"]
        tax_computation = self._generate_tax_computation(recommended_regime)
        
        # Generate verification data
        verification_data = self._generate_verification_data(income, recommended_regime)
        
        return PortalFormData(
            taxpayer_info=taxpayer_data,
            income_sections=income_sections,
            deduction_sections=deduction_sections,
            tax_computation=tax_computation,
            verification_data=verification_data
        )
    
    def _determine_itr_form(self, income) -> str:
        """Determine appropriate ITR form"""
        
        has_capital_gains = (income.ltcg > 0 or income.stcg > 0)
        has_other_income = income.bank_interest > 0
        
        if has_capital_gains:
            return "ITR-2"
        elif has_other_income:
            return "ITR-2"  # Bank interest requires ITR-2
        else:
            return "ITR-1"
    
    def _generate_income_sections(self, income, hra_calc) -> List[PortalSection]:
        """Generate income sections for portal"""
        
        sections = []
        
        # Section A: Salary Income
        if income.gross_salary > 0:
            salary_section = PortalSection(
                section_name="Income from Salary",
                form_reference="Schedule S (ITR-2) / Part A (ITR-1)",
                fields={
                    "gross_salary": f"₹{income.gross_salary:,.0f}",
                    "allowances": {
                        "basic_salary": f"₹{income.basic_salary:,.0f}",
                        "hra_received": f"₹{income.hra_received:,.0f}",
                        "special_allowance": f"₹{income.special_allowance:,.0f}",
                        "other_allowances": f"₹{income.other_allowances:,.0f}"
                    },
                    "exemptions": {
                        "hra_exemption": f"₹{hra_calc.hra_exemption:,.0f}",
                        "standard_deduction": "Automatically calculated by portal"
                    },
                    "tds_deducted": f"₹{income.tds_salary:,.0f}"
                },
                instructions=[
                    "1. Go to 'Income Details' → 'Salary'",
                    "2. Enter Gross Salary amount",
                    "3. Fill allowance breakdown in respective fields",
                    "4. HRA exemption will be calculated automatically if you enter rent details",
                    "5. TDS amount should match your Form 16"
                ],
                notes=[
                    "💡 Standard deduction is automatically applied by the portal",
                    "⚠️ Ensure TDS amount matches Form 26AS",
                    "🏠 Enter rent details for HRA exemption calculation"
                ]
            )
            sections.append(salary_section)
        
        # Section B: Income from Other Sources
        if income.bank_interest > 0 or income.other_income > 0:
            other_income_section = PortalSection(
                section_name="Income from Other Sources",
                form_reference="Schedule OS (ITR-2)",
                fields={
                    "bank_interest": f"₹{income.bank_interest:,.0f}",
                    "tds_on_interest": f"₹{income.tds_other:,.0f}",
                    "other_income": f"₹{income.other_income:,.0f}",
                    "exemption_80tta": f"₹{min(income.bank_interest, 10000):,.0f}"
                },
                instructions=[
                    "1. Go to 'Income Details' → 'Income from Other Sources'",
                    "2. Enter 'Interest from Banks' amount",
                    "3. Enter corresponding TDS amount",
                    "4. Section 80TTA exemption (up to ₹10,000) will be applied"
                ],
                notes=[
                    "💡 Section 80TTA provides exemption up to ₹10,000 on bank interest",
                    "📄 Use bank interest certificates for accurate amounts",
                    "🧾 TDS should match bank certificates and 26AS"
                ]
            )
            sections.append(other_income_section)
        
        # Section C: Capital Gains
        if income.ltcg > 0 or income.stcg > 0:
            capital_gains_section = PortalSection(
                section_name="Capital Gains",
                form_reference="Schedule CG (ITR-2)",
                fields={
                    "long_term_capital_gains": f"₹{income.ltcg:,.0f}",
                    "short_term_capital_gains": f"₹{income.stcg:,.0f}",
                    "ltcg_exemption": f"₹{min(income.ltcg, 100000):,.0f}",
                    "ltcg_taxable": f"₹{max(0, income.ltcg - 100000):,.0f}",
                    "stcg_tax_rate": "15% (for securities)",
                    "stcg_taxable": f"₹{income.stcg:,.0f}"
                },
                instructions=[
                    "1. Go to 'Income Details' → 'Capital Gains'",
                    "2. Select 'Long Term' or 'Short Term' as applicable",
                    "3. Enter sale consideration and cost of acquisition",
                    "4. Portal will calculate gains automatically",
                    "5. LTCG exemption up to ₹1 lakh is automatically applied"
                ],
                notes=[
                    "💡 LTCG on equity/mutual funds exempt up to ₹1 lakh",
                    "⚡ STCG on equity taxed at 15%",
                    "📊 Use broker statements for accurate figures",
                    "🎯 Portal auto-calculates exemptions and tax rates"
                ]
            )
            sections.append(capital_gains_section)
        
        return sections
    
    def _generate_deduction_sections(self, deductions, recommended_regime) -> List[PortalSection]:
        """Generate deduction sections for portal"""
        
        sections = []
        
        if recommended_regime == "old":
            # Section 80C Deductions
            if deductions.section_80c_total > 0:
                section_80c = PortalSection(
                    section_name="Deductions under Section 80C",
                    form_reference="Schedule VI-A (ITR-2)",
                    fields={
                        "employee_pf": f"₹{deductions.epf:,.0f}",
                        "ppf": f"₹{deductions.ppf:,.0f}",
                        "life_insurance": f"₹{deductions.life_insurance:,.0f}",
                        "elss_mutual_funds": f"₹{deductions.elss:,.0f}",
                        "nsc": f"₹{deductions.nsc:,.0f}",
                        "home_loan_principal": f"₹{deductions.home_loan_principal:,.0f}",
                        "total_80c": f"₹{deductions.section_80c_total:,.0f}",
                        "eligible_amount": f"₹{deductions.section_80c_claimed:,.0f}",
                        "limit": "₹1,50,000"
                    },
                    instructions=[
                        "1. Go to 'Deductions' → 'Chapter VI-A' → '80C'",
                        "2. Enter each investment type in respective fields",
                        "3. Portal will automatically apply ₹1.5 lakh limit",
                        "4. Upload investment proofs if required"
                    ],
                    notes=[
                        f"⚠️ Total limit: ₹1,50,000 (you claimed ₹{deductions.section_80c_claimed:,.0f})",
                        "📄 Keep investment receipts ready for verification",
                        "💡 Portal auto-calculates eligible amount"
                    ]
                )
                sections.append(section_80c)
            
            # Section 80D Deductions
            if deductions.section_80d_total > 0:
                section_80d = PortalSection(
                    section_name="Deductions under Section 80D",
                    form_reference="Schedule VI-A (ITR-2)",
                    fields={
                        "health_insurance_self": f"₹{deductions.health_insurance_self:,.0f}",
                        "health_insurance_parents": f"₹{deductions.health_insurance_parents:,.0f}",
                        "total_80d": f"₹{deductions.section_80d_total:,.0f}",
                        "eligible_amount": f"₹{deductions.section_80d_claimed:,.0f}",
                        "limit_self": "₹25,000",
                        "limit_parents": "₹50,000"
                    },
                    instructions=[
                        "1. Go to 'Deductions' → 'Chapter VI-A' → '80D'",
                        "2. Enter health insurance premiums for self and family",
                        "3. Enter parents' health insurance separately",
                        "4. Portal applies respective limits automatically"
                    ],
                    notes=[
                        "💡 Self/Family limit: ₹25,000, Parents: ₹50,000",
                        "🏥 Additional ₹25,000 for parents above 60 years",
                        "📄 Keep insurance premium receipts ready"
                    ]
                )
                sections.append(section_80d)
            
            # Other Deductions
            other_deductions = PortalSection(
                section_name="Other Deductions",
                form_reference="Schedule VI-A (ITR-2)",
                fields={
                    "section_80tta": f"₹{deductions.section_80tta:,.0f}",
                    "section_24b": f"₹{deductions.section_24b:,.0f}",
                    "section_80g": f"₹{deductions.section_80g:,.0f}",
                    "section_80ccd1b": f"₹{deductions.section_80ccd1b:,.0f}"
                },
                instructions=[
                    "1. 80TTA: Enter in 'Interest on Savings Account'",
                    "2. 24(b): Enter in 'House Property' → 'Interest on borrowed capital'",
                    "3. 80G: Enter in 'Donations' with 80G certificate details",
                    "4. 80CCD(1B): Enter NPS contributions separately"
                ],
                notes=[
                    "💰 80TTA: Bank interest exemption up to ₹10,000",
                    "🏠 24(b): Home loan interest up to ₹2,00,000",
                    "❤️ 80G: Donations to approved institutions",
                    "🏦 80CCD(1B): NPS additional deduction up to ₹50,000"
                ]
            )
            sections.append(other_deductions)
        
        else:
            # New Regime - Limited Deductions
            new_regime_info = PortalSection(
                section_name="New Tax Regime - No Deductions",
                form_reference="ITR-2 (New Regime)",
                fields={
                    "regime_selected": "New Tax Regime (115BAC)",
                    "standard_deduction": "₹75,000 (automatically applied)",
                    "other_deductions": "Not applicable in new regime"
                },
                instructions=[
                    "1. Select 'New Tax Regime' option in portal",
                    "2. Most deductions under Chapter VI-A are not available",
                    "3. Standard deduction of ₹75,000 is automatically applied",
                    "4. Only specific deductions like employer NPS contribution allowed"
                ],
                notes=[
                    "🆕 New regime offers lower tax rates with fewer deductions",
                    "💡 Standard deduction increased to ₹75,000",
                    "⚠️ Cannot claim 80C, 80D, HRA exemption, etc."
                ]
            )
            sections.append(new_regime_info)
        
        return sections
    
    def _generate_tax_computation(self, regime) -> Dict[str, Any]:
        """Generate tax computation section"""
        
        return {
            "section_name": "Tax Computation",
            "form_reference": "Part B-TTI (ITR-2)",
            "fields": {
                "gross_total_income": f"₹{regime.gross_total_income:,.0f}",
                "total_deductions": f"₹{regime.total_deductions:,.0f}",
                "taxable_income": f"₹{regime.taxable_income:,.0f}",
                "tax_on_income": f"₹{regime.tax_on_income:,.0f}",
                "cess": f"₹{regime.cess:,.0f}",
                "total_tax_liability": f"₹{regime.total_tax:,.0f}",
                "tds_paid": f"₹{regime.total_tds:,.0f}",
                "advance_tax": f"₹{regime.advance_tax:,.0f}",
                "balance_payable": f"₹{regime.balance_payable:,.0f}" if regime.balance_payable > 0 else "₹0",
                "refund_due": f"₹{regime.refund_due:,.0f}" if regime.refund_due > 0 else "₹0"
            },
            "instructions": [
                "1. Portal automatically calculates tax based on income and deductions",
                "2. Verify TDS amounts match Form 26AS",
                "3. Check if advance tax payments are correctly reflected",
                "4. Review final refund/balance payable amount"
            ],
            "notes": [
                "🎯 Tax computation is auto-calculated by portal",
                "📊 Verify all TDS entries with Form 26AS",
                "💰 Refund will be processed to linked bank account"
            ]
        }
    
    def _generate_verification_data(self, income, regime) -> Dict[str, Any]:
        """Generate verification and final data"""
        
        return {
            "section_name": "Verification & Final Steps",
            "form_reference": "Verification (ITR-2)",
            "fields": {
                "total_income": f"₹{regime.gross_total_income:,.0f}",
                "total_tax": f"₹{regime.total_tax:,.0f}",
                "refund_amount": f"₹{regime.refund_due:,.0f}" if regime.refund_due > 0 else "No refund",
                "balance_tax": f"₹{regime.balance_payable:,.0f}" if regime.balance_payable > 0 else "No balance due",
                "verification_method": "Aadhaar OTP / Net Banking / Bank Account EVC"
            },
            "instructions": [
                "1. Review all sections before final submission",
                "2. Use 'Preview' to check ITR before submission",
                "3. Verify using Aadhaar OTP, Net Banking, or Bank EVC",
                "4. Download acknowledgment after successful submission",
                "5. E-verify within 120 days if not verified immediately"
            ],
            "notes": [
                "📱 Aadhaar OTP is the fastest verification method",
                "🏦 Ensure bank account is linked for refund processing",
                "⏰ File before due date: September 15, 2025",
                "✅ Keep acknowledgment receipt for records"
            ]
        }

    def get_portal_checklist(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate pre-filing checklist"""
        
        income = analysis['income_breakdown']
        
        checklist = [
            {
                "item": "PAN-Aadhaar Linking",
                "status": "required",
                "description": "Ensure PAN is linked with Aadhaar",
                "portal_section": "Login/Profile"
            },
            {
                "item": "Form 16 from Employer",
                "status": "required" if income.gross_salary > 0 else "not_applicable",
                "description": "Salary certificate with TDS details",
                "portal_section": "Income from Salary"
            },
            {
                "item": "Form 26AS Verification",
                "status": "required",
                "description": "Verify TDS credits match your records",
                "portal_section": "Tax Credits"
            },
            {
                "item": "Bank Interest Certificates",
                "status": "required" if income.bank_interest > 0 else "not_applicable",
                "description": "Interest earned and TDS deducted by banks",
                "portal_section": "Income from Other Sources"
            },
            {
                "item": "Capital Gains Statements",
                "status": "required" if (income.ltcg > 0 or income.stcg > 0) else "not_applicable",
                "description": "Mutual fund/stock transaction statements",
                "portal_section": "Capital Gains"
            },
            {
                "item": "Investment Proofs",
                "status": "recommended",
                "description": "80C, 80D investment receipts (for old regime)",
                "portal_section": "Deductions"
            },
            {
                "item": "Bank Account Details",
                "status": "required",
                "description": "For refund processing (if applicable)",
                "portal_section": "Bank Details"
            }
        ]
        
        return checklist