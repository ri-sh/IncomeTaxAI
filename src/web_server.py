#!/usr/bin/env python3
"""
Enhanced TaxSahaj Web Server
============================

Flask web server that integrates the income tax analysis backend with
the enhanced TaxSahaj HTML interface.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import tempfile
import shutil

from flask import Flask, render_template_string, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.main import IncomeTaxAssistant
from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer
from src.core.document_processing.langextract_analyzer import LangextractDocumentAnalyzer

app = Flask(__name__)
app.secret_key = 'taxsahaj_secure_key_2024'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp(prefix='taxsahaj_uploads_')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to store analysis results
current_analysis_results = {}

ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the enhanced TaxSahaj HTML interface"""
    try:
        # Read the enhanced HTML template
        html_path = Path(__file__).parent / 'core' / 'enhanced_taxsahaj.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Add additional sections for results display
        enhanced_html = add_results_section(html_content)
        
        return enhanced_html
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return f"Error loading page: {e}", 500

def add_results_section(html_content):
    """Add comprehensive tax analysis results section to the HTML"""
    
    results_section = """
        <!-- Tax Analysis Results Section -->
        <section class="results-section" id="results" style="display: none;">
            <div class="container">
                <h2>🎯 Your Comprehensive Tax Analysis</h2>
                
                <!-- Income Breakdown -->
                <div class="income-breakdown">
                    <h3>💰 Income Analysis</h3>
                    <div class="income-cards">
                        <div class="income-card">
                            <div class="income-icon">💼</div>
                            <div class="income-details">
                                <h4>Salary Income</h4>
                                <div class="amount" id="salaryIncome">₹0</div>
                            </div>
                        </div>
                        <div class="income-card">
                            <div class="income-icon">🏦</div>
                            <div class="income-details">
                                <h4>Interest Income</h4>
                                <div class="amount" id="interestIncome">₹0</div>
                            </div>
                        </div>
                        <div class="income-card">
                            <div class="income-icon">📈</div>
                            <div class="income-details">
                                <h4>Capital Gains</h4>
                                <div class="amount" id="capitalGains">₹0</div>
                            </div>
                        </div>
                        <div class="income-card total">
                            <div class="income-icon">💸</div>
                            <div class="income-details">
                                <h4>Total Income</h4>
                                <div class="amount" id="totalIncome">₹0</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- HRA Analysis -->
                <div class="hra-analysis" id="hraSection" style="display: none;">
                    <h3>🏠 HRA Exemption Analysis</h3>
                    <div class="hra-details">
                        <div class="hra-calculation">
                            <h4>HRA Calculation Components:</h4>
                            <div class="hra-components">
                                <div class="hra-item">HRA Received: <span id="hraReceived">₹0</span></div>
                                <div class="hra-item">50% of Basic Salary: <span id="hraBasicHalf">₹0</span></div>
                                <div class="hra-item">Rent - 10% of Salary: <span id="hraRentMinus10">₹0</span></div>
                                <div class="hra-item hra-exemption">HRA Exemption (Minimum): <span id="hraExemption">₹0</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Tax Regime Comparison -->
                <div class="regime-comparison">
                    <div class="regime-card old-regime">
                        <h3>🔄 Old Tax Regime</h3>
                        <div class="tax-amount" id="oldRegimeTax">₹0</div>
                        <div class="additional-tax" id="oldRegimeAdditional">Additional: ₹0</div>
                        <div class="deductions-used">
                            <h4>Deductions Used:</h4>
                            <ul id="oldRegimeDeductions"></ul>
                        </div>
                    </div>
                    
                    <div class="regime-card new-regime">
                        <h3>🆕 New Tax Regime</h3>
                        <div class="tax-amount" id="newRegimeTax">₹0</div>
                        <div class="additional-tax" id="newRegimeAdditional">Additional: ₹0</div>
                        <div class="deductions-note">
                            <p>Limited deductions available</p>
                        </div>
                    </div>
                </div>
                
                <div class="recommendation-card" id="recommendationCard">
                    <h3 id="recommendationTitle">📊 Final Recommendation</h3>
                    <p id="recommendationText">Analyzing your best option...</p>
                    <div class="savings-highlight" id="totalSavings">Savings: ₹0</div>
                </div>

                <!-- ITR Filing Guide -->
                <div class="filing-guide">
                    <h3>📋 Step-by-Step ITR Filing Guide</h3>
                    <div class="guide-tabs">
                        <button class="tab-button active" onclick="showTab('portal-login')">1. Portal Login</button>
                        <button class="tab-button" onclick="showTab('form-selection')">2. Form Selection</button>
                        <button class="tab-button" onclick="showTab('income-entry')">3. Income Entry</button>
                        <button class="tab-button" onclick="showTab('deductions')">4. Deductions</button>
                        <button class="tab-button" onclick="showTab('verification')">5. Verification</button>
                    </div>
                    
                    <div class="tab-content">
                        <div id="portal-login" class="tab-panel active">
                            <h4>🌐 Accessing Income Tax Portal</h4>
                            <div class="step-instructions">
                                <ol>
                                    <li><strong>Visit:</strong> <a href="https://www.incometax.gov.in/iec/foportal/" target="_blank">https://www.incometax.gov.in/iec/foportal/</a></li>
                                    <li><strong>Login with:</strong> Your PAN and password</li>
                                    <li><strong>Navigate to:</strong> e-File → Income Tax Return → File ITR Online</li>
                                    <li><strong>Select Assessment Year:</strong> 2025-26 (for FY 2024-25)</li>
                                </ol>
                                <div class="portal-tip">
                                    💡 <strong>Tip:</strong> Keep your Form 16 handy - you'll need details like your employer's TAN and TDS amounts.
                                </div>
                            </div>
                        </div>
                        
                        <div id="form-selection" class="tab-panel">
                            <h4>📝 ITR Form Selection</h4>
                            <div class="step-instructions">
                                <div class="form-recommendation" id="itrFormRecommendation">
                                    <strong>Recommended Form:</strong> ITR-2 (Salary + Capital Gains + Other Income)
                                </div>
                                <ol>
                                    <li><strong>For Salary Only:</strong> Use ITR-1 (Sahaj)</li>
                                    <li><strong>For Salary + Capital Gains:</strong> Use ITR-2</li>
                                    <li><strong>For Business Income:</strong> Use ITR-3 or ITR-4</li>
                                </ol>
                                <div class="portal-tip">
                                    💡 <strong>Your Case:</strong> Based on your documents, we recommend <span id="recommendedForm">ITR-2</span>
                                </div>
                            </div>
                        </div>
                        
                        <div id="income-entry" class="tab-panel">
                            <h4>💰 Income Entry Instructions</h4>
                            <div class="step-instructions">
                                <div class="income-entry-guide">
                                    <h5>Salary Income Section:</h5>
                                    <ul>
                                        <li><strong>Employer Name:</strong> <span id="guideEmployerName">From Form 16</span></li>
                                        <li><strong>Gross Salary:</strong> ₹<span id="guideGrossSalary">0</span></li>
                                        <li><strong>Tax Deducted:</strong> ₹<span id="guideTaxDeducted">0</span></li>
                                        <li><strong>HRA Received:</strong> ₹<span id="guideHRAReceived">0</span></li>
                                        <li><strong>HRA Exemption:</strong> ₹<span id="guideHRAExemption">0</span></li>
                                    </ul>
                                    
                                    <h5>Other Income:</h5>
                                    <ul id="guideOtherIncome">
                                        <li><strong>Bank Interest:</strong> ₹<span id="guideBankInterest">0</span></li>
                                        <li><strong>Capital Gains:</strong> ₹<span id="guideCapitalGains">0</span></li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        
                        <div id="deductions" class="tab-panel">
                            <h4>📋 Deductions Entry Guide</h4>
                            <div class="step-instructions">
                                <div class="deductions-guide" id="deductionsGuide">
                                    <h5>Section 80C Deductions:</h5>
                                    <ul id="guide80C">
                                        <li>EPF Contribution: ₹<span id="guideEPF">0</span></li>
                                        <li>ELSS Mutual Funds: ₹<span id="guideELSS">0</span></li>
                                        <li>Life Insurance: ₹<span id="guideLifeInsurance">0</span></li>
                                    </ul>
                                    
                                    <h5>Other Deductions:</h5>
                                    <ul id="guideOtherDeductions">
                                        <li>80CCD(1B) - NPS: ₹<span id="guideNPS">0</span></li>
                                        <li>80D - Health Insurance: ₹<span id="guideHealthInsurance">0</span></li>
                                    </ul>
                                    
                                    <div class="deduction-tip">
                                        💡 <strong>Pro Tip:</strong> The portal may auto-populate some data from Form 16. Verify all amounts match your documents.
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="verification" class="tab-panel">
                            <h4>✅ Final Review & Submission</h4>
                            <div class="step-instructions">
                                <ol>
                                    <li><strong>Review Summary:</strong> Check all income and deduction entries</li>
                                    <li><strong>Tax Calculation:</strong> Verify computed tax matches our analysis</li>
                                    <li><strong>Expected Tax:</strong> ₹<span id="guideFinalTax">0</span></li>
                                    <li><strong>Refund/Payment:</strong> <span id="guideFinalStatus">Calculate after entry</span></li>
                                    <li><strong>Submit Return:</strong> Click "Submit" after final review</li>
                                    <li><strong>e-Verification:</strong> Verify using Aadhaar OTP, Net Banking, or Bank Account</li>
                                </ol>
                                <div class="portal-tip success">
                                    ✅ <strong>Success:</strong> Your ITR will be processed within 24-48 hours after e-verification.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="document-summary">
                    <h3>📄 Documents Analyzed</h3>
                    <div id="documentsList"></div>
                </div>
                
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="downloadReport()">📊 Download Detailed Report</button>
                    <button class="btn btn-secondary" onclick="startNewAnalysis()">🔄 Analyze New Documents</button>
                    <button class="btn btn-success" onclick="window.open('https://www.incometax.gov.in/iec/foportal/', '_blank')">🌐 Open Tax Portal</button>
                </div>
            </div>
        </section>
        
        <style>
        .results-section {
            padding: 6rem 0;
            background: rgba(26, 35, 50, 0.6);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(0, 255, 127, 0.3);
        }
        
        .results-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Income Breakdown Cards */
        .income-breakdown {
            margin-bottom: 3rem;
        }
        
        .income-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }
        
        .income-card {
            background: rgba(45, 55, 72, 0.3);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            backdrop-filter: blur(15px);
            display: flex;
            align-items: center;
            gap: 1rem;
            transition: all 0.3s ease;
        }
        
        .income-card:hover {
            border-color: #00ff7f;
            box-shadow: 0 5px 15px rgba(0, 255, 127, 0.2);
            transform: translateY(-2px);
        }
        
        .income-card.total {
            border-color: #00ff7f;
            background: rgba(0, 255, 127, 0.1);
        }
        
        .income-icon {
            font-size: 2.5rem;
            opacity: 0.8;
        }
        
        .income-details h4 {
            margin: 0 0 0.5rem 0;
            font-size: 1rem;
            color: #a0aec0;
        }
        
        .amount {
            font-size: 1.5rem;
            font-weight: 700;
            color: #00ff7f;
        }
        
        /* HRA Analysis */
        .hra-analysis {
            background: rgba(45, 55, 72, 0.3);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            margin-bottom: 3rem;
        }
        
        .hra-components {
            display: grid;
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .hra-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }
        
        .hra-item.hra-exemption {
            background: rgba(0, 255, 127, 0.1);
            border: 1px solid #00ff7f;
            font-weight: 600;
        }
        
        /* Filing Guide */
        .filing-guide {
            background: rgba(45, 55, 72, 0.3);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            margin-bottom: 3rem;
        }
        
        .guide-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        
        .tab-button {
            padding: 0.75rem 1.5rem;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 255, 127, 0.3);
            border-radius: 8px;
            color: #a0aec0;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .tab-button:hover, .tab-button.active {
            background: rgba(0, 255, 127, 0.1);
            border-color: #00ff7f;
            color: #00ff7f;
        }
        
        .tab-content {
            min-height: 300px;
        }
        
        .tab-panel {
            display: none;
        }
        
        .tab-panel.active {
            display: block;
        }
        
        .step-instructions {
            background: rgba(0, 0, 0, 0.2);
            padding: 1.5rem;
            border-radius: 10px;
        }
        
        .step-instructions ol {
            margin: 1rem 0;
            padding-left: 2rem;
        }
        
        .step-instructions li {
            margin-bottom: 1rem;
            line-height: 1.6;
        }
        
        .portal-tip, .deduction-tip {
            background: rgba(0, 255, 127, 0.1);
            padding: 1rem;
            border-left: 4px solid #00ff7f;
            margin-top: 1rem;
            border-radius: 0 8px 8px 0;
        }
        
        .portal-tip.success {
            background: rgba(34, 197, 94, 0.1);
            border-left-color: #22c55e;
        }
        
        .form-recommendation {
            background: rgba(0, 255, 127, 0.1);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid #00ff7f;
        }
        
        .income-entry-guide h5, .deductions-guide h5 {
            color: #00ff7f;
            margin: 1.5rem 0 1rem 0;
        }
        
        .income-entry-guide ul, .deductions-guide ul {
            margin: 0;
            padding-left: 0;
        }
        
        .income-entry-guide li, .deductions-guide li {
            list-style: none;
            padding: 0.5rem 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            display: flex;
            justify-content: space-between;
        }
        
        .savings-highlight {
            font-size: 1.5rem;
            font-weight: 800;
            color: #00ff7f;
            margin-top: 1rem;
        }
        
        .regime-comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .regime-card {
            background: rgba(45, 55, 72, 0.3);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            backdrop-filter: blur(15px);
            text-align: center;
        }
        
        .regime-card.recommended {
            border-color: #00ff7f;
            box-shadow: 0 0 20px rgba(0, 255, 127, 0.3);
        }
        
        .tax-amount {
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #00ff7f 0%, #00e676 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 1rem 0;
        }
        
        .additional-tax {
            font-size: 1.1rem;
            color: #a0aec0;
            margin-bottom: 1rem;
        }
        
        .recommendation-card {
            background: rgba(0, 255, 127, 0.1);
            padding: 2rem;
            border-radius: 15px;
            border: 2px solid #00ff7f;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .document-summary {
            background: rgba(45, 55, 72, 0.3);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            margin-bottom: 2rem;
        }
        
        .action-buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        @media (max-width: 768px) {
            .regime-comparison {
                grid-template-columns: 1fr;
            }
            
            .income-cards {
                grid-template-columns: 1fr;
            }
            
            .guide-tabs {
                flex-direction: column;
            }
            
            .tab-button {
                text-align: center;
            }
            
            .income-card {
                flex-direction: column;
                text-align: center;
                gap: 0.5rem;
            }
            
            .income-icon {
                font-size: 2rem;
            }
            
            .form-grid {
                grid-template-columns: 1fr;
            }
            
            .correction-actions {
                flex-direction: column;
                align-items: center;
            }
            
            .correction-actions .btn {
                width: 100%;
                max-width: 300px;
            }
            
            .quick-comparison {
                grid-template-columns: 1fr;
            }
        }
        </style>
    """
    
    # Insert results section before the footer
    footer_index = html_content.find('<footer>')
    if footer_index != -1:
        html_content = html_content[:footer_index] + results_section + html_content[footer_index:]
    
    # Add JavaScript for results handling
    results_js = """
        // Tax Results JavaScript
        let analysisResults = {};
        
        function displayResults(results) {
            analysisResults = results;
            console.log('Displaying results:', results);
            
            // Show results section
            document.getElementById('results').style.display = 'block';
            
            // Populate income breakdown cards
            document.getElementById('salaryIncome').textContent = '₹' + Math.round(results.gross_salary || 0).toLocaleString();
            document.getElementById('interestIncome').textContent = '₹' + Math.round(results.total_interest || 0).toLocaleString();
            document.getElementById('capitalGains').textContent = '₹' + Math.round(results.total_capital_gains || 0).toLocaleString();
            document.getElementById('totalIncome').textContent = '₹' + Math.round(results.total_income || 0).toLocaleString();
            
            // Show HRA section if applicable
            if (results.hra_received > 0) {
                document.getElementById('hraSection').style.display = 'block';
                document.getElementById('hraReceived').textContent = '₹' + Math.round(results.hra_received || 0).toLocaleString();
                document.getElementById('hraBasicHalf').textContent = '₹' + Math.round((results.basic_salary || 0) * 0.5).toLocaleString();
                const rentMinus10 = Math.max(0, (results.rent_paid || 0) - (results.gross_salary || 0) * 0.1);
                document.getElementById('hraRentMinus10').textContent = '₹' + Math.round(rentMinus10).toLocaleString();
                document.getElementById('hraExemption').textContent = '₹' + Math.round(results.hra_exemption || 0).toLocaleString();
            }
            
            // Populate regime comparison
            document.getElementById('oldRegimeTax').textContent = '₹' + Math.round(results.tax_liability_old_regime || 0).toLocaleString();
            document.getElementById('newRegimeTax').textContent = '₹' + Math.round(results.tax_liability_new_regime || 0).toLocaleString();
            
            // Calculate additional tax or refund
            const oldAdditional = (results.tax_liability_old_regime || 0) - (results.tax_paid || 0);
            const newAdditional = (results.tax_liability_new_regime || 0) - (results.tax_paid || 0);
            
            document.getElementById('oldRegimeAdditional').textContent = 
                oldAdditional >= 0 ? `Additional: ₹${Math.round(oldAdditional).toLocaleString()}` : 
                `Refund: ₹${Math.round(Math.abs(oldAdditional)).toLocaleString()}`;
                
            document.getElementById('newRegimeAdditional').textContent = 
                newAdditional >= 0 ? `Additional: ₹${Math.round(newAdditional).toLocaleString()}` : 
                `Refund: ₹${Math.round(Math.abs(newAdditional)).toLocaleString()}`;
            
            // Recommendation
            const savings = Math.abs((results.tax_liability_old_regime || 0) - (results.tax_liability_new_regime || 0));
            const recommended = results.recommended_regime || 'old';
            
            document.getElementById('recommendationTitle').textContent = 
                `📊 Recommendation: ${recommended.toUpperCase()} Tax Regime`;
            document.getElementById('recommendationText').textContent = 
                `Based on your financial profile, the ${recommended} tax regime will save you more money.`;
            document.getElementById('totalSavings').textContent = `Savings: ₹${Math.round(savings).toLocaleString()}`;
            
            // Highlight recommended regime
            document.querySelectorAll('.regime-card').forEach(card => card.classList.remove('recommended'));
            document.querySelector(`.${recommended}-regime`).classList.add('recommended');
            
            // Populate deductions for old regime
            const deductionsList = document.getElementById('oldRegimeDeductions');
            deductionsList.innerHTML = '';
            
            if (results.deductions_capped_80c) {
                const li = document.createElement('li');
                li.textContent = `80C Deductions: ₹${Math.round(results.deductions_capped_80c).toLocaleString()}`;
                deductionsList.appendChild(li);
            }
            
            if (results.deductions_80ccd1b) {
                const li = document.createElement('li');
                li.textContent = `80CCD(1B) - NPS: ₹${Math.round(results.deductions_80ccd1b).toLocaleString()}`;
                deductionsList.appendChild(li);
            }
            
            // Populate filing guide with user-specific data
            populateFilingGuide(results);
            
            // Documents summary
            const documentsList = document.getElementById('documentsList');
            documentsList.innerHTML = `<p>Total Documents Analyzed: ${results.documents_analyzed || 0}</p>`;
            
            // Scroll to results
            document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
        }
        
        function downloadReport() {
            fetch('/api/download_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(analysisResults)
            })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `Tax_Analysis_Report_${new Date().toISOString().split('T')[0]}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            });
        }
        
        function startNewAnalysis() {
            document.getElementById('results').style.display = 'none';
            document.getElementById('fileInput').value = '';
            document.getElementById('processingIndicator').style.display = 'none';
            document.getElementById('upload').scrollIntoView({ behavior: 'smooth' });
        }
        
        // Enhanced file processing
        async function processUploadedFiles(files) {
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            
            try {
                document.getElementById('processingIndicator').style.display = 'block';
                simulateProcessing(); // Keep the visual animation
                
                const response = await fetch('/api/analyze_documents', {
                    method: 'POST',
                    body: formData
                });
                
                const results = await response.json();
                
                if (results.error) {
                    throw new Error(results.error);
                }
                
                // Hide processing indicator after real analysis
                setTimeout(() => {
                    document.getElementById('processingIndicator').style.display = 'none';
                    displayResults(results);
                }, 6000); // Wait for animation to complete
                
            } catch (error) {
                console.error('Error processing files:', error);
                document.getElementById('processingIndicator').style.display = 'none';
                alert('Error processing documents: ' + error.message);
            }
        }
        
        // Tab functionality for filing guide
        function showTab(tabName) {
            // Hide all tab panels
            document.querySelectorAll('.tab-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });
            
            // Show selected tab panel
            document.getElementById(tabName).classList.add('active');
            
            // Add active class to clicked tab button
            event.target.classList.add('active');
        }
        
        // Populate filing guide with user-specific data
        function populateFilingGuide(results) {
            // Form recommendation
            let recommendedForm = 'ITR-1';
            if (results.total_capital_gains > 0 || results.total_interest > 0) {
                recommendedForm = 'ITR-2';
            }
            document.getElementById('recommendedForm').textContent = recommendedForm;
            
            // Income entry guide
            document.getElementById('guideEmployerName').textContent = results.employer_name || 'From Form 16';
            document.getElementById('guideGrossSalary').textContent = Math.round(results.gross_salary || 0).toLocaleString();
            document.getElementById('guideTaxDeducted').textContent = Math.round(results.tax_paid || 0).toLocaleString();
            document.getElementById('guideHRAReceived').textContent = Math.round(results.hra_received || 0).toLocaleString();
            document.getElementById('guideHRAExemption').textContent = Math.round(results.hra_exemption || 0).toLocaleString();
            document.getElementById('guideBankInterest').textContent = Math.round(results.total_interest || 0).toLocaleString();
            document.getElementById('guideCapitalGains').textContent = Math.round(results.total_capital_gains || 0).toLocaleString();
            
            // Deductions guide
            document.getElementById('guideEPF').textContent = Math.round(results.epf_employee || 0).toLocaleString();
            document.getElementById('guideELSS').textContent = Math.round(results.elss_investments || 0).toLocaleString();
            document.getElementById('guideLifeInsurance').textContent = Math.round(results.life_insurance || 0).toLocaleString();
            document.getElementById('guideNPS').textContent = Math.round(results.deductions_80ccd1b || 0).toLocaleString();
            document.getElementById('guideHealthInsurance').textContent = Math.round(results.health_insurance || 0).toLocaleString();
            
            // Final verification guide
            const recommendedRegime = results.recommended_regime || 'old';
            const finalTax = recommendedRegime === 'old' ? results.tax_liability_old_regime : results.tax_liability_new_regime;
            document.getElementById('guideFinalTax').textContent = Math.round(finalTax || 0).toLocaleString();
            
            const refundAmount = (results.tax_paid || 0) - finalTax;
            document.getElementById('guideFinalStatus').textContent = 
                refundAmount > 0 ? `Refund Expected: ₹${Math.round(refundAmount).toLocaleString()}` : 
                `Additional Payment: ₹${Math.round(Math.abs(refundAmount)).toLocaleString()}`;
        }
        
        // Override the original file input handler
        document.addEventListener('DOMContentLoaded', function() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                fileInput.addEventListener('change', function(e) {
                    const files = Array.from(e.target.files);
                    if (files.length > 0) {
                        processUploadedFiles(files);
                    }
                });
            }
        });
    """
    
    # Insert JavaScript before closing body tag
    body_end_index = html_content.rfind('</body>')
    if body_end_index != -1:
        script_tag = f"<script>{results_js}</script>"
        html_content = html_content[:body_end_index] + script_tag + html_content[body_end_index:]
    
    return html_content

@app.route('/api/analyze_documents', methods=['POST'])
def analyze_documents():
    """API endpoint to analyze uploaded documents"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'error': 'No files selected'}), 400
        
        # Create temporary directory for this analysis
        temp_dir = tempfile.mkdtemp(prefix='taxsahaj_analysis_')
        uploaded_files = []
        
        # Save uploaded files
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(temp_dir, filename)
                file.save(file_path)
                uploaded_files.append(file_path)
                logger.info(f"Saved file: {filename}")
        
        if not uploaded_files:
            return jsonify({'error': 'No valid files uploaded'}), 400
        
        # Initialize the analyzer (use Ollama by default, can be made configurable)
        analyzer_type = request.form.get('analyzer', 'ollama')
        if analyzer_type == 'langextract':
            analyzer = LangextractDocumentAnalyzer()
        else:
            analyzer = OllamaDocumentAnalyzer()
        
        # Create assistant and analyze documents
        assistant = IncomeTaxAssistant(analyzer=analyzer)
        
        # Analyze documents using the original method signature
        analyzed_docs = []
        for file_path in uploaded_files:
            try:
                result = analyzer.analyze_document(file_path)
                if result:
                    analyzed_docs.append(result)
                    logger.info(f"Successfully analyzed: {Path(file_path).name}")
            except Exception as e:
                logger.error(f"Error analyzing {Path(file_path).name}: {e}")
        
        # Set the analyzed documents in the assistant
        assistant.analyzed_documents = analyzed_docs
        
        # Calculate tax summary
        tax_summary = assistant.calculate_tax_summary()
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Store results globally for report download
        global current_analysis_results
        current_analysis_results = tax_summary
        
        logger.info(f"Analysis completed. Processed {len(analyzed_docs)} documents.")
        
        return jsonify(tax_summary)
        
    except Exception as e:
        logger.error(f"Error in analyze_documents: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recalculate_tax', methods=['POST'])
def recalculate_tax():
    """Recalculate tax based on user-corrected values"""
    try:
        corrected_data = request.get_json()
        if not corrected_data:
            return jsonify({'error': 'No correction data provided'}), 400
        
        logger.info(f"Recalculating tax with corrected data: {corrected_data}")
        
        # Import the tax calculator
        from src.core.tax_calculator import TaxCalculator
        
        # Initialize tax calculator
        calculator = TaxCalculator()
        
        # Calculate total income
        total_income = (
            corrected_data.get('gross_salary', 0) +
            corrected_data.get('total_interest', 0) +
            corrected_data.get('total_capital_gains', 0)
        )
        
        # Calculate 80C deductions (capped at 150,000)
        deductions_80c = min(150000, (
            corrected_data.get('epf_employee', 0) +
            corrected_data.get('ppf_amount', 0) +
            corrected_data.get('elss_investments', 0) +
            corrected_data.get('life_insurance', 0) +
            corrected_data.get('nsc_investments', 0) +
            corrected_data.get('tax_saver_fd', 0) +
            corrected_data.get('home_loan_principal', 0)
        ))
        
        # Calculate HRA exemption
        hra_exemption = 0
        if corrected_data.get('hra_received', 0) > 0 and corrected_data.get('rent_paid', 0) > 0:
            basic_salary = corrected_data.get('basic_salary', 0)
            hra_received = corrected_data.get('hra_received', 0)
            rent_paid = corrected_data.get('rent_paid', 0)
            gross_salary = corrected_data.get('gross_salary', 0)
            
            hra_exemption = min(
                hra_received,
                basic_salary * 0.5,  # 50% of basic salary
                max(0, rent_paid - (gross_salary * 0.1))  # Rent - 10% of salary
            )
        
        # Calculate additional deductions
        additional_deductions = (
            corrected_data.get('deductions_80ccd1b', 0) +  # NPS 80CCD(1B)
            corrected_data.get('health_insurance', 0) +     # 80D
            corrected_data.get('education_loan_interest', 0) +  # 80E
            corrected_data.get('donations', 0) +            # 80G
            corrected_data.get('home_loan_interest', 0)     # 24(b)
        )
        
        # Add first-time homeowner deduction
        if corrected_data.get('first_time_homeowner', False):
            additional_deductions += min(50000, corrected_data.get('home_loan_interest', 0))
        
        # Calculate taxable income for both regimes
        # Old regime: All deductions allowed
        taxable_income_old = max(0, total_income - hra_exemption - deductions_80c - additional_deductions)
        
        # New regime: Limited deductions (only standard deduction and few others)
        standard_deduction = 75000  # FY 2024-25
        taxable_income_new = max(0, total_income - standard_deduction)
        
        # Calculate tax liability for both regimes
        tax_old_regime = calculator.calculate_tax_new_slabs(taxable_income_old)  # Old regime uses new slabs
        tax_new_regime = calculator.calculate_tax_new_slabs(taxable_income_new)  # New regime
        
        # Determine recommended regime
        recommended_regime = 'old' if tax_old_regime < tax_new_regime else 'new'
        
        # Calculate savings
        savings = abs(tax_old_regime - tax_new_regime)
        
        # Prepare response with updated calculations
        recalculated_results = {
            **corrected_data,  # Include all corrected data
            'total_income': total_income,
            'taxable_income_old_regime': taxable_income_old,
            'taxable_income_new_regime': taxable_income_new,
            'tax_liability_old_regime': tax_old_regime,
            'tax_liability_new_regime': tax_new_regime,
            'recommended_regime': recommended_regime,
            'savings': savings,
            'hra_exemption': hra_exemption,
            'deductions_capped_80c': deductions_80c,
            'additional_deductions': additional_deductions,
            'recalculated': True,
            'recalculation_timestamp': datetime.now().isoformat()
        }
        
        # Store updated results globally
        global current_analysis_results
        current_analysis_results.update(recalculated_results)
        
        logger.info(f"Tax recalculation completed. Old: ₹{tax_old_regime:,.0f}, New: ₹{tax_new_regime:,.0f}, Recommended: {recommended_regime}")
        
        return jsonify(recalculated_results)
        
    except Exception as e:
        logger.error(f"Error in recalculate_tax: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download_report', methods=['POST'])
def download_report():
    """Generate and download detailed tax report"""
    try:
        data = request.get_json()
        if not data:
            data = current_analysis_results
        
        # Create a comprehensive report
        report = {
            'report_generated': datetime.now().isoformat(),
            'tax_analysis': data,
            'report_type': 'Comprehensive Income Tax Analysis',
            'recommendations': generate_recommendations(data),
            'next_steps': [
                "Review the recommended tax regime",
                "Gather any missing investment proofs",
                "Login to the Income Tax e-filing portal",
                "Fill ITR form with the calculated values",
                "Submit and e-verify your return"
            ]
        }
        
        from flask import Response
        import json
        
        response = Response(
            json.dumps(report, indent=2, ensure_ascii=False),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename=Tax_Report_{datetime.now().strftime("%Y-%m-%d")}.json'}
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500

def generate_recommendations(data: Dict[str, Any]) -> List[str]:
    """Generate personalized tax recommendations"""
    recommendations = []
    
    total_income = data.get('total_income', 0)
    old_tax = data.get('tax_liability_old_regime', 0)
    new_tax = data.get('tax_liability_new_regime', 0)
    deductions = data.get('total_deductions', 0)
    
    # Regime recommendation
    if old_tax < new_tax:
        savings = new_tax - old_tax
        recommendations.append(f"✅ File under OLD TAX REGIME to save ₹{savings:,.0f}")
        recommendations.append("📋 Ensure all 80C, 80D, and other deduction proofs are ready")
    else:
        savings = old_tax - new_tax
        recommendations.append(f"✅ File under NEW TAX REGIME to save ₹{savings:,.0f}")
        recommendations.append("⚡ New regime offers simplicity with fewer deductions needed")
    
    # Income-based recommendations
    if total_income > 1000000:
        recommendations.append("💰 Consider additional tax-saving investments like ELSS or NPS")
        recommendations.append("🏠 If planning to buy a home, factor in home loan tax benefits")
    
    # Deduction optimization
    if deductions < 150000:
        shortfall = 150000 - deductions
        recommendations.append(f"📈 You can invest ₹{shortfall:,.0f} more in 80C to maximize deductions")
    
    recommendations.append("🔍 Review HRA exemption if you pay rent")
    recommendations.append("🩺 Ensure health insurance premiums are claimed under 80D")
    
    return recommendations

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def cleanup_temp_files():
    """Clean up temporary files on startup"""
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        shutil.rmtree(app.config['UPLOAD_FOLDER'], ignore_errors=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    cleanup_temp_files()
    
    logger.info("Starting TaxSahaj Enhanced Web Server...")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Run the Flask app
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True,
        threaded=True
    )