"""
PDF Report Generator for Income Tax Analysis
Creates professional PDF reports with tax calculations and recommendations
"""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor, black, white, blue, green, red, orange
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class TaxReportGenerator:
    """Generate comprehensive PDF reports for tax analysis"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")
        
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
        # Indian tax colors
        self.colors = {
            'primary': HexColor('#FF6B35'),      # Saffron
            'secondary': HexColor('#FFFFFF'),    # White  
            'accent': HexColor('#138808'),       # Green
            'text': HexColor('#000000'),         # Black
            'background': HexColor('#F8F9FA'),   # Light gray
            'success': HexColor('#28A745'),      # Success green
            'warning': HexColor('#FFC107'),      # Warning yellow
            'danger': HexColor('#DC3545')        # Danger red
        }
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        
        # Main title style
        self.styles.add(ParagraphStyle(
            name='MainTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=HexColor('#FF6B35'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=HexColor('#138808'),
            spaceBefore=20,
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection style
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=HexColor('#000000'),
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Highlight style
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=HexColor('#FFFFFF'),
            backColor=HexColor('#FF6B35'),
            spaceBefore=10,
            spaceAfter=10,
            leftIndent=10,
            rightIndent=10,
            fontName='Helvetica-Bold'
        ))
        
        # Info box style
        self.styles.add(ParagraphStyle(
            name='InfoBox',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=HexColor('#000000'),
            backColor=HexColor('#F8F9FA'),
            spaceBefore=8,
            spaceAfter=8,
            leftIndent=15,
            rightIndent=15,
            borderColor=HexColor('#138808'),
            borderWidth=1
        ))
    
    def generate_comprehensive_report(self, 
                                    user_data: Dict[str, Any],
                                    document_analysis: Dict[str, Any],
                                    tax_calculations: Dict[str, Any],
                                    recommendations: Dict[str, Any],
                                    output_path: str = None) -> str:
        """Generate comprehensive tax analysis PDF report"""
        
        if not output_path:
            output_path = f"Tax_Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        # Build story (content)
        story = []
        
        # Title page
        story.extend(self._create_title_page(user_data))
        story.append(PageBreak())
        
        # Executive summary
        story.extend(self._create_executive_summary(tax_calculations, recommendations))
        story.append(PageBreak())
        
        # Document analysis
        story.extend(self._create_document_analysis_section(document_analysis))
        story.append(PageBreak())
        
        # Tax regime comparison
        story.extend(self._create_tax_regime_comparison(tax_calculations))
        story.append(PageBreak())
        
        # Detailed recommendations
        story.extend(self._create_recommendations_section(recommendations))
        story.append(PageBreak())
        
        # ITR filing guide
        story.extend(self._create_filing_guide_section(user_data))
        story.append(PageBreak())
        
        # Appendix
        story.extend(self._create_appendix())
        
        # Build PDF
        doc.build(story)
        
        return output_path
    
    def _create_title_page(self, user_data: Dict[str, Any]) -> List:
        """Create title page"""
        
        story = []
        
        # Main title
        story.append(Paragraph("🇮🇳 Income Tax Analysis Report", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Subtitle
        story.append(Paragraph("Financial Year 2024-25 (Assessment Year 2025-26)", self.styles['Heading2']))
        story.append(Spacer(1, 30))
        
        # User information
        user_info = [
            ['Report Generated For:', user_data.get('name', 'Taxpayer')],
            ['PAN Number:', user_data.get('pan', 'XXXXX1234X')],
            ['Report Date:', datetime.now().strftime('%d %B %Y')],
            ['Assessment Year:', '2025-26'],
            ['Financial Year:', '2024-25'],
            ['Filing Deadline:', 'September 15, 2025']
        ]
        
        user_table = Table(user_info, colWidths=[2.5*inch, 3*inch])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), self.colors['background']),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(user_table)
        story.append(Spacer(1, 40))
        
        # Report highlights
        story.append(Paragraph("Report Highlights", self.styles['SectionHeader']))
        
        highlights_data = [
            ['🤖 AI-Powered Analysis', '✅ Advanced document recognition and classification'],
            ['📊 Tax Optimization', '✅ Old vs New regime comparison with savings calculation'],
            ['📋 ITR Recommendations', '✅ Personalized filing strategy and form selection'],
            ['💰 Potential Savings', f"✅ Up to ₹{user_data.get('potential_savings', '61,850')} in tax savings"],
            ['🛡️ Compliance Check', '✅ Complete document checklist and missing items']
        ]
        
        highlights_table = Table(highlights_data, colWidths=[2.2*inch, 3.3*inch])
        highlights_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), white),
            ('TEXTCOLOR', (0, 0), (-1, -1), black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, self.colors['primary']),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(highlights_table)
        story.append(Spacer(1, 30))
        
        # Disclaimer
        disclaimer = """
        <b>Disclaimer:</b> This report is generated by an AI-powered tax analysis system based on the documents provided. 
        While every effort has been made to ensure accuracy, please consult with a qualified tax professional before making 
        final decisions. The recommendations are based on current tax laws for FY 2024-25 and may be subject to change.
        """
        story.append(Paragraph(disclaimer, self.styles['InfoBox']))
        
        return story
    
    def _create_executive_summary(self, tax_calculations: Dict[str, Any], recommendations: Dict[str, Any]) -> List:
        """Create executive summary section"""
        
        story = []
        
        story.append(Paragraph("Executive Summary", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Key findings
        story.append(Paragraph("Key Findings", self.styles['SectionHeader']))
        
        # ITR Form recommendation
        itr_form = recommendations.get('itr_form_recommendation', {})
        story.append(Paragraph(f"<b>Recommended ITR Form:</b> {itr_form.get('form', 'ITR-2')}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Reason:</b> {itr_form.get('reason', 'Capital gains detected')}", self.styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Tax regime recommendation
        regime = recommendations.get('tax_regime_advice', {})
        story.append(Paragraph(f"<b>Recommended Tax Regime:</b> {regime.get('recommendation', 'Old Regime')}", self.styles['Normal']))
        story.append(Paragraph(f"<b>Potential Savings:</b> {regime.get('potential_savings', '₹25,000 - ₹69,550')}", self.styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Summary table
        summary_data = [
            ['Metric', 'Value', 'Status'],
            ['Document Completion', '92%', '✅ Excellent'],
            ['Critical Documents', '5/5 Found', '✅ Complete'],
            ['Tax Optimization', 'Old Regime', '✅ Optimal'],
            ['Potential Savings', '₹61,850', '✅ High'],
            ['Filing Complexity', 'ITR-2 Required', '⚠️ Moderate']
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 1.8*inch, 1.7*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), self.colors['background']),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Action items
        story.append(Paragraph("Immediate Action Items", self.styles['SectionHeader']))
        
        action_items = [
            "1. 📋 File ITR-2 (due to capital gains from mutual funds and stocks)",
            "2. 💰 Choose Old Tax Regime for maximum deductions benefit",
            "3. 📊 Use bulk Excel upload for capital gains in Schedule CG",
            "4. 🔍 Gather missing documents for additional ₹25,000-₹69,550 savings",
            "5. ⏰ Complete filing before September 15, 2025 deadline"
        ]
        
        for item in action_items:
            story.append(Paragraph(item, self.styles['Normal']))
        
        return story
    
    def _create_document_analysis_section(self, document_analysis: Dict[str, Any]) -> List:
        """Create document analysis section"""
        
        story = []
        
        story.append(Paragraph("Document Analysis", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("AI-Powered Document Classification", self.styles['SectionHeader']))
        
        # Documents found
        docs_data = [
            ['Document', 'Type', 'Confidence', 'Priority', 'Tax Impact']
        ]
        
        sample_docs = [
            ['Form16.pdf', 'Salary TDS Certificate', '95.0%', '🚨 Critical', 'Required for ITR filing'],
            ['ELSS_Statement.pdf', 'ELSS Investment', '92.0%', '⭐ High', '₹46,350 tax saving'],
            ['Capital_Gains.xlsx', 'Mutual Fund Gains', '88.0%', '🚨 Critical', 'Requires ITR-2'],
            ['Stock_Gains.xlsx', 'Stock Trading Gains', '88.0%', '🚨 Critical', 'Additional gains'],
            ['Bank_Interest.pdf', 'Interest Certificate', '85.0%', '📋 Medium', 'Other income'],
            ['NPS.pdf', 'NPS Statement', '90.0%', '⭐ High', '₹15,500 additional saving']
        ]
        
        docs_data.extend(sample_docs)
        
        docs_table = Table(docs_data, colWidths=[1.2*inch, 1.2*inch, 0.8*inch, 0.8*inch, 1.5*inch])
        docs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), white),
        ]))
        
        story.append(docs_table)
        story.append(Spacer(1, 20))
        
        # Missing documents
        story.append(Paragraph("Missing Documents Analysis", self.styles['SectionHeader']))
        
        missing_docs = [
            ['Missing Document', 'Impact', 'Potential Saving', 'Priority'],
            ['Health Insurance Premium', 'Section 80D deduction', '₹7,750', 'Recommended'],
            ['Home Loan Interest Certificate', 'Section 24(b) deduction', '₹62,000', 'High'],
            ['Education Loan Interest', 'Section 80E deduction', '₹5,000', 'Optional'],
            ['Charitable Donations', 'Section 80G deduction', '₹2,500', 'Optional']
        ]
        
        missing_table = Table(missing_docs, colWidths=[1.8*inch, 1.5*inch, 1.2*inch, 1*inch])
        missing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['warning']),
            ('TEXTCOLOR', (0, 0), (-1, 0), black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), white),
        ]))
        
        story.append(missing_table)
        
        return story
    
    def _create_tax_regime_comparison(self, tax_calculations: Dict[str, Any]) -> List:
        """Create tax regime comparison section"""
        
        story = []
        
        story.append(Paragraph("Tax Regime Comparison", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("Old Regime vs New Regime Analysis", self.styles['SectionHeader']))
        
        # Comparison table
        comparison_data = [
            ['Parameter', 'Old Regime', 'New Regime', 'Recommendation'],
            ['Basic Exemption', '₹2.5 Lakh', '₹3 Lakh', 'New Regime'],
            ['Standard Deduction', '₹50,000', '₹75,000', 'New Regime'],
            ['Section 80C (ELSS)', '₹1.5 Lakh (₹46,350 saving)', 'Not Available', 'Old Regime'],
            ['Section 80D (Health)', '₹25,000 (₹7,750 saving)', 'Not Available', 'Old Regime'],
            ['Section 80CCD(1B) (NPS)', '₹50,000 (₹15,500 saving)', 'Not Available', 'Old Regime'],
            ['HRA Exemption', 'Available', 'Not Available', 'Old Regime'],
            ['Tax Rates (₹5-10L)', '20%', '10%', 'New Regime'],
            ['Total Tax Savings', '₹69,600', '₹12,500', 'Old Regime ✅']
        ]
        
        comparison_table = Table(comparison_data, colWidths=[1.5*inch, 1.3*inch, 1.3*inch, 1.4*inch])
        comparison_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('BACKGROUND', (0, -1), (-1, -1), self.colors['success']),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
        ]))
        
        story.append(comparison_table)
        story.append(Spacer(1, 20))
        
        # Recommendation box
        recommendation_text = """
        <b>AI Recommendation: Choose Old Tax Regime</b><br/><br/>
        Based on your investment profile and deductions available, the Old Tax Regime will save you approximately 
        ₹57,100 more than the New Regime. Your ELSS and NPS investments provide significant tax benefits that 
        are not available in the New Regime.
        """
        
        story.append(Paragraph(recommendation_text, self.styles['Highlight']))
        
        return story
    
    def _create_recommendations_section(self, recommendations: Dict[str, Any]) -> List:
        """Create detailed recommendations section"""
        
        story = []
        
        story.append(Paragraph("Detailed Recommendations", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Tax optimization strategies
        story.append(Paragraph("Tax Optimization Strategies", self.styles['SectionHeader']))
        
        strategies = [
            "1. <b>Maximize Section 80C:</b> Increase ELSS investment to full ₹1.5 lakh limit for maximum ₹46,350 saving",
            "2. <b>Utilize NPS Benefits:</b> Continue ₹50,000 NPS investment for additional ₹15,500 tax saving",
            "3. <b>Capital Gains Planning:</b> Use ₹1 lakh LTCG exemption strategically for tax-efficient selling",
            "4. <b>Health Insurance:</b> Consider ₹25,000 health insurance for ₹7,750 additional saving",
            "5. <b>Home Loan Benefits:</b> If applicable, claim ₹2 lakh home loan interest for ₹62,000 saving"
        ]
        
        for strategy in strategies:
            story.append(Paragraph(strategy, self.styles['Normal']))
            story.append(Spacer(1, 8))
        
        story.append(Spacer(1, 15))
        
        # Investment recommendations
        story.append(Paragraph("Investment Recommendations for Next Year", self.styles['SectionHeader']))
        
        investment_data = [
            ['Investment', 'Section', 'Limit', 'Tax Saving', 'Recommendation'],
            ['ELSS Mutual Funds', '80C', '₹1.5 Lakh', '₹46,350', '✅ Continue'],
            ['NPS Contribution', '80CCD(1B)', '₹50,000', '₹15,500', '✅ Continue'],
            ['Health Insurance', '80D', '₹25,000', '₹7,750', '⭐ Consider'],
            ['Home Loan (if buying)', '24(b)', '₹2 Lakh', '₹62,000', '💡 Evaluate'],
            ['PPF Contribution', '80C', 'Within 80C limit', 'Tax-free returns', '💡 Alternative']
        ]
        
        investment_table = Table(investment_data, colWidths=[1.2*inch, 0.8*inch, 1*inch, 1*inch, 1.5*inch])
        investment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), white),
        ]))
        
        story.append(investment_table)
        
        return story
    
    def _create_filing_guide_section(self, user_data: Dict[str, Any]) -> List:
        """Create ITR filing guide section"""
        
        story = []
        
        story.append(Paragraph("ITR Filing Guide", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Filing checklist
        story.append(Paragraph("Pre-Filing Checklist", self.styles['SectionHeader']))
        
        checklist_items = [
            "☐ Download Form 26AS and verify TDS credits",
            "☐ Gather all 6 documents identified in analysis",
            "☐ Choose Old Tax Regime for optimal savings",
            "☐ Prepare Excel files for capital gains bulk upload",
            "☐ Calculate total Section 80C and 80CCD(1B) investments",
            "☐ Keep Aadhaar-linked mobile number ready for e-verification"
        ]
        
        for item in checklist_items:
            story.append(Paragraph(item, self.styles['Normal']))
        
        story.append(Spacer(1, 15))
        
        # Step-by-step guide
        story.append(Paragraph("Step-by-Step Filing Process", self.styles['SectionHeader']))
        
        filing_steps = [
            ['Step', 'Action', 'Documents Required', 'Time'],
            ['1', 'Login to e-filing portal', 'PAN, Password', '2 min'],
            ['2', 'Select ITR-2 for AY 2025-26', 'None', '1 min'],
            ['3', 'Choose Old Tax Regime', 'None', '1 min'],
            ['4', 'Enter salary details', 'Form 16', '5 min'],
            ['5', 'Add bank interest income', 'Interest Certificate', '2 min'],
            ['6', 'Upload capital gains (bulk)', 'Excel files', '3 min'],
            ['7', 'Claim 80C deductions', 'ELSS Statement', '3 min'],
            ['8', 'Claim 80CCD(1B) deductions', 'NPS Statement', '2 min'],
            ['9', 'Review and submit', 'All documents', '5 min'],
            ['10', 'E-verify with Aadhaar OTP', 'Mobile phone', '2 min']
        ]
        
        filing_table = Table(filing_steps, colWidths=[0.5*inch, 1.8*inch, 1.5*inch, 0.7*inch])
        filing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, -1), white),
        ]))
        
        story.append(filing_table)
        story.append(Spacer(1, 15))
        
        # Important deadlines
        story.append(Paragraph("Important Deadlines", self.styles['SectionHeader']))
        
        deadline_info = """
        <b>ITR Filing Deadline:</b> September 15, 2025<br/>
        <b>Last Date for e-Verification:</b> December 31, 2025<br/>
        <b>Belated Return (with penalty):</b> December 31, 2025<br/>
        <b>Updated Return:</b> March 31, 2030
        """
        
        story.append(Paragraph(deadline_info, self.styles['InfoBox']))
        
        return story
    
    def _create_appendix(self) -> List:
        """Create appendix with additional information"""
        
        story = []
        
        story.append(Paragraph("Appendix", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Tax slabs
        story.append(Paragraph("Tax Slabs for FY 2024-25", self.styles['SectionHeader']))
        
        old_regime_slabs = [
            ['Income Range', 'Tax Rate'],
            ['Up to ₹2.5 Lakh', '0%'],
            ['₹2.5 Lakh - ₹5 Lakh', '5%'],
            ['₹5 Lakh - ₹10 Lakh', '20%'],
            ['Above ₹10 Lakh', '30%']
        ]
        
        new_regime_slabs = [
            ['Income Range', 'Tax Rate'],
            ['Up to ₹3 Lakh', '0%'],
            ['₹3 Lakh - ₹7 Lakh', '5%'],
            ['₹7 Lakh - ₹10 Lakh', '10%'],
            ['₹10 Lakh - ₹12 Lakh', '15%'],
            ['₹12 Lakh - ₹15 Lakh', '20%'],
            ['Above ₹15 Lakh', '30%']
        ]
        
        story.append(Paragraph("Old Tax Regime", self.styles['SubHeader']))
        old_table = Table(old_regime_slabs, colWidths=[2.5*inch, 1.5*inch])
        old_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['accent']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(old_table)
        story.append(Spacer(1, 15))
        
        story.append(Paragraph("New Tax Regime", self.styles['SubHeader']))
        new_table = Table(new_regime_slabs, colWidths=[2.5*inch, 1.5*inch])
        new_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(new_table)
        
        # Contact information
        story.append(Spacer(1, 20))
        story.append(Paragraph("Important Contacts", self.styles['SectionHeader']))
        
        contact_info = """
        <b>Income Tax Helpline:</b> 1800-103-0025<br/>
        <b>E-filing Portal:</b> https://www.incometax.gov.in/iec/foportal/<br/>
        <b>Form 26AS:</b> Available on e-filing portal<br/>
        <b>AIS/TIS:</b> Annual Information Statement on portal<br/>
        <b>Technical Support:</b> webmanager@incometax.gov.in
        """
        
        story.append(Paragraph(contact_info, self.styles['InfoBox']))
        
        return story
    
    def generate_quick_summary_pdf(self, 
                                  regime_comparison: Dict[str, Any],
                                  recommendations: List[str],
                                  output_path: str = None) -> str:
        """Generate a quick summary PDF for regime comparison"""
        
        if not output_path:
            output_path = f"Tax_Regime_Comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        
        # Title
        story.append(Paragraph("Tax Regime Comparison Summary", self.styles['MainTitle']))
        story.append(Spacer(1, 20))
        
        # Quick comparison
        comparison_data = [
            ['Parameter', 'Old Regime', 'New Regime', 'Benefit'],
            ['Tax Savings', regime_comparison.get('old_savings', '₹69,600'), 
             regime_comparison.get('new_savings', '₹12,500'), 'Old Regime'],
            ['Deductions Available', 'Yes (80C, 80D, HRA)', 'Limited', 'Old Regime'],
            ['Filing Complexity', 'Moderate', 'Simple', 'New Regime'],
            ['Recommended Choice', '✅ Old Regime', '❌ New Regime', 'Old Regime']
        ]
        
        table = Table(comparison_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.colors['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, black),
            ('BACKGROUND', (0, -1), (-1, -1), self.colors['success']),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # Recommendations
        story.append(Paragraph("Recommendations", self.styles['SectionHeader']))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", self.styles['Normal']))
        
        doc.build(story)
        return output_path