#!/usr/bin/env python3
"""
Enhanced TaxSahaj Web Server - Multi-Page Version
=================================================

Flask web server with clean multi-page navigation:
- Page 1: Document Upload
- Page 2: Tax Analysis & Reports  
- Page 3: ITR Filing Guide
"""

import os
import json
import logging
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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

# Global variables to store analysis results and progress
current_analysis_results = {}
current_progress = {
    'stage': 'idle',
    'progress': 0,
    'current_file': '',
    'files_processed': 0,
    'total_files': 0,
    'step': 'waiting'
}

ALLOWED_EXTENSIONS = {'pdf', 'xlsx', 'xls', 'csv', 'jpg', 'jpeg', 'png', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Serve the multi-page TaxSahaj HTML interface"""
    try:
        # Read the enhanced HTML template
        html_path = Path(__file__).parent / 'core' / 'enhanced_taxsahaj.html'
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Add multi-page structure
        enhanced_html = add_multipage_structure(html_content)
        
        return enhanced_html
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return f"Error loading page: {e}", 500

def add_multipage_structure(html_content):
    """Add multi-page navigation structure to the HTML"""
    
    # Remove onclick from upload-zone and add specific clickable area + file list outside
    # First, remove onclick from upload-zone
    html_content = html_content.replace(
        'onclick="triggerFileUpload()"', 
        ''
    )
    
    # Find the upload-zone and modify its content to add a specific clickable button
    upload_zone_start = html_content.find('<div class="upload-zone"')
    if upload_zone_start != -1:
        # Find the tip paragraph and add clickable button after it
        tip_end = html_content.find('Hold Ctrl/Cmd to select multiple files at once</p>', upload_zone_start)
        if tip_end != -1:
            tip_end += len('Hold Ctrl/Cmd to select multiple files at once</p>')
            
            clickable_button = """
                        
                        <!-- Small Clickable Upload Button -->
                        <div class="upload-button-area" id="uploadButtonArea" style="margin: 2rem auto 1rem auto; padding: 1rem 2rem; background: rgba(72, 187, 120, 0.2); border: 2px dashed #48bb78; border-radius: 10px; cursor: pointer; display: inline-block; transition: all 0.3s ease; z-index: 1000; position: relative;">
                            <span style="color: #48bb78; font-weight: 600; pointer-events: none;">📁 Click to Browse Files</span>
                        </div>
            """
            html_content = html_content[:tip_end] + clickable_button + html_content[tip_end:]
    
    # Add file list and process button OUTSIDE the upload section entirely
    upload_section_end = html_content.find('</section>', html_content.find('class="upload-section"'))
    if upload_section_end != -1:
        external_additions = """
        
        <!-- File List and Process Button - Completely Outside Upload Section -->
        <section class="file-management-section" style="padding: 3rem 0; background: rgba(45, 55, 72, 0.1);">
            <div class="container">
                <!-- Selected Files Display -->
                <div class="selected-files-container" id="fileListContainer" style="display: none; margin-bottom: 3rem;">
                    <h4 style="margin-bottom: 1.5rem; color: #48bb78; text-align: center;">📄 Selected Documents Ready for Analysis</h4>
                    <div class="file-list" id="selectedFilesList"></div>
                </div>
                
                <!-- Process Button - Separate Section -->
                <div class="process-section" id="processButtonContainer" style="display: none; text-align: center; padding: 2rem; background: rgba(26, 35, 50, 0.8); border-radius: 15px; border: 1px solid rgba(72, 187, 120, 0.3);">
                    <h3 style="color: #48bb78; margin-bottom: 1rem;">🚀 Ready to Analyze</h3>
                    <p style="color: #a0aec0; margin-bottom: 2rem;">Click below to start AI analysis of your tax documents</p>
                    <button class="btn btn-primary btn-large" id="processDocumentsBtn" onclick="processDocuments(event)" onmousedown="event.stopPropagation()" onmouseup="event.stopPropagation()">
                        📊 Process Documents & View Analysis
                    </button>
                </div>
            </div>
        </section>
        
        """
        html_content = html_content[:upload_section_end] + external_additions + html_content[upload_section_end:]
    
    # Add the multi-page sections before footer
    multipage_sections = """
        <!-- Multi-Page Container -->
        <div class="page-container">
            <!-- Page 2: Tax Analysis Results -->
            <div class="page" id="page2" style="display: none;">
                <header>
                    <div class="wrap">
                        <div>
                            <h1>Your Tax Analysis Report</h1>
                            <div class="subtle">Edit assumptions, compare regimes, and follow the guided journey to file on the Income Tax portal.</div>
                        </div>
                        <div class="badges">
                            <span class="badge">Secure & Encrypted</span>
                            <span class="badge">FY 2024–25 Rules</span>
                            <span class="badge">Data Deleted After Processing</span>
                        </div>
                    </div>
                </header>

                <div class="container">
                    <div class="grid">
                        <!-- LEFT: Income + Editors -->
                        <section class="card" id="income-card">
                            <h2>💰 Income Breakdown</h2>
                            <div class="subtle">Numbers below are editable. Bars reflect actual values (not placeholders).</div>

                            <div class="bars" id="bars"></div>

                            <div style="margin-top:12px; overflow:auto;">
                                <table id="income-table">
                                    <thead>
                                        <tr>
                                            <th>Category</th>
                                            <th>Sub-Component</th>
                                            <th class="amount">Amount (₹)</th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>

                            <div class="statgrid" style="margin-top:12px;">
                                <div class="stat">
                                    <div class="subtle">Gross Total Income</div>
                                    <div class="big" id="grossTotal">₹0</div>
                                </div>
                                <div class="stat">
                                    <div class="subtle">Total Deductions</div>
                                    <div class="big" id="totalDeductions">₹0</div>
                                </div>
                                <div class="stat">
                                    <div class="subtle">Taxable Income</div>
                                    <div class="big" id="taxableIncome">₹0</div>
                                </div>
                            </div>
                        </section>

                        <!-- RIGHT: HRA + Deductions + Regime Compare -->
                        <aside class="card">
                            <h2>🏠 Edit HRA & Deductions</h2>
                            <div class="row">
                                <div class="field"><label>Basic Salary (annual) <input id="basic" type="number" value="500000" min="0" /></label></div>
                                <div class="field"><label>Dearness Allowance (DA) <input id="da" type="number" value="0" min="0" /></label></div>
                            </div>
                            <div class="row">
                                <div class="field"><label>HRA Received <input id="hraReceived" type="number" value="150000" min="0" /></label></div>
                                <div class="field"><label>Rent Per Month <input id="rentPerMonth" type="number" value="15000" min="0" /></label></div>
                            </div>
                            <div class="row">
                                <div class="field"><label>Total Rent Paid (Annual) <input id="rentPaid" type="number" value="180000" min="0" /></label></div>
                                <div class="field" style="display: flex; align-items: end;"><button class="btn ghost" id="autoCalculateRent" type="button">Auto Calculate from Monthly</button></div>
                            </div>
                            <div class="row">
                                <div class="field"><label>Commission (if applicable) <input id="commission" type="number" value="0" min="0" /></label></div>
                                <div class="switch"><input id="metro" type="checkbox" checked /> <label for="metro">Metro City (50% cap)</label></div>
                            </div>

                            <div class="statgrid" style="margin-top:10px;">
                                <div class="stat"><div class="subtle">Max HRA Exemption</div><div class="big" id="maxHRA">₹0</div></div>
                                <div class="stat"><div class="subtle">Current HRA</div><div class="big" id="curHRA">₹0</div></div>
                                <div class="stat"><div class="subtle">Delta</div><div class="big" id="hraDelta" class="delta">₹0</div></div>
                            </div>

                            <div class="row" style="margin-top:10px;">
                                <button class="btn" id="applyHRA">Apply to Analysis</button>
                                <button class="btn ghost" id="resetHRA">Reset</button>
                            </div>

                            <hr style="margin:14px 0; border:none; border-top:1px solid var(--soft)" />

                            <h2>🧾 Common Deductions</h2>
                            <div class="row">
                                <div class="field"><label>80C <input id="d80c" type="number" value="120000" min="0" /></label></div>
                                <div class="field"><label>80D <input id="d80d" type="number" value="25000" min="0" /></label></div>
                            </div>
                            <div class="row">
                                <div class="field"><label>80CCD(1B) <input id="d80ccd1b" type="number" value="0" min="0" /></label></div>
                                <div class="field"><label>80TTA <input id="d80tta" type="number" value="0" min="0" /></label></div>
                            </div>
                        </aside>
                    </div>

                    <!-- Regime Comparison -->
                    <section class="card">
                        <h2>📊 Regime Comparison (Illustrative)</h2>
                        <div class="subtle">This is a simplified illustration to help you decide. Verify exact tax on the portal.</div>
                        <div class="statgrid" style="margin-top:10px; grid-template-columns: repeat(4,1fr);">
                            <div class="stat"><div class="subtle">Old Regime (est.)</div><div class="big" id="oldTax">₹0</div></div>
                            <div class="stat"><div class="subtle">New Regime (est.)</div><div class="big" id="newTax">₹0</div></div>
                            <div class="stat"><div class="subtle">You Save With</div><div class="big" id="saveWith">–</div></div>
                            <div class="stat"><div class="subtle">Savings Amount</div><div class="big" id="saveAmt">₹0</div></div>
                        </div>
                    </section>

                    <!-- Guided Filing Journey -->
                    <section class="card">
                        <h2>🧭 Guided Filing Journey</h2>
                        <div class="subtle">Follow each step. At the end, open the official portal and transcribe values confidently.</div>
                        <div class="stepper" style="margin-top:10px;">
                            <nav class="steps" id="steps"></nav>
                            <article class="stepcontent" id="stepcontent"></article>
                        </div>
                        <div class="footer-cta" style="margin-top:12px;">
                            <div class="checklist" id="precheck"></div>
                            <div style="flex:1"></div>
                            <a class="portal" href="https://www.incometax.gov.in" target="_blank" rel="noopener"><button class="btn secondary">Open Income Tax Portal</button></a>
                        </div>
                    </section>
                </div>
            </div>
            
            <!-- Page 3: Filing Guide -->
            <div class="page" id="page3" style="display: none;">
                <div class="page-header">
                    <button class="btn btn-secondary btn-back" onclick="showPage('page2')">
                        ← Back to Analysis
                    </button>
                    <h1>📋 Step-by-Step ITR Filing Guide</h1>
                </div>
                
                <div class="guide-container">
                    <div class="guide-tabs">
                        <button class="tab-button active" onclick="showGuideTab('portal-login')">1. Portal Access</button>
                        <button class="tab-button" onclick="showGuideTab('form-selection')">2. Form Selection</button>
                        <button class="tab-button" onclick="showGuideTab('income-entry')">3. Income Entry</button>
                        <button class="tab-button" onclick="showGuideTab('deductions')">4. Deductions</button>
                        <button class="tab-button" onclick="showGuideTab('verification')">5. Submit & Verify</button>
                    </div>
                    
                    <div class="guide-content">
                        <div id="portal-login" class="guide-panel active">
                            <h4>🌐 Accessing Income Tax Portal</h4>
                            <div class="step-instructions">
                                <ol>
                                    <li><strong>Visit:</strong> <a href="https://www.incometax.gov.in/iec/foportal/" target="_blank">https://www.incometax.gov.in/iec/foportal/</a></li>
                                    <li><strong>Login with:</strong> Your PAN and password</li>
                                    <li><strong>Navigate to:</strong> e-File → Income Tax Return → File ITR Online</li>
                                    <li><strong>Select Assessment Year:</strong> 2025-26 (for FY 2024-25)</li>
                                </ol>
                                <div class="guide-tip">
                                    💡 <strong>Tip:</strong> Keep your Form 16 ready - you'll need your employer's TAN and TDS amounts.
                                </div>
                            </div>
                        </div>
                        
                        <div id="form-selection" class="guide-panel">
                            <h4>📝 ITR Form Selection</h4>
                            <div class="step-instructions">
                                <div class="form-recommendation" id="itrFormRecommendation">
                                    <strong>Recommended for You:</strong> <span id="recommendedForm">ITR-2</span>
                                </div>
                                <div class="form-options">
                                    <div class="form-option">
                                        <strong>ITR-1 (Sahaj):</strong> For salary income only (up to ₹50 lakh)
                                    </div>
                                    <div class="form-option">
                                        <strong>ITR-2:</strong> For salary + capital gains + other income
                                    </div>
                                    <div class="form-option">
                                        <strong>ITR-3:</strong> For business/professional income
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="income-entry" class="guide-panel">
                            <h4>💰 Income Entry - Your Specific Values</h4>
                            <div class="step-instructions">
                                <div class="income-guide">
                                    <div class="guide-section">
                                        <h5>Salary Income Section:</h5>
                                        <div class="value-grid">
                                            <div class="value-item">Employer: <span id="guideEmployerName">From Form 16</span></div>
                                            <div class="value-item">Gross Salary: ₹<span id="guideGrossSalary">0</span></div>
                                            <div class="value-item">Tax Deducted: ₹<span id="guideTaxDeducted">0</span></div>
                                            <div class="value-item">HRA Received: ₹<span id="guideHRAReceived">0</span></div>
                                            <div class="value-item highlight">HRA Exemption: ₹<span id="guideHRAExemption">0</span></div>
                                        </div>
                                    </div>
                                    
                                    <div class="guide-section">
                                        <h5>Other Income:</h5>
                                        <div class="value-grid">
                                            <div class="value-item">Bank Interest: ₹<span id="guideBankInterest">0</span></div>
                                            <div class="value-item">Capital Gains: ₹<span id="guideCapitalGains">0</span></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="deductions" class="guide-panel">
                            <h4>📋 Deductions - Your Investment Details</h4>
                            <div class="step-instructions">
                                <div class="deductions-guide">
                                    <div class="guide-section">
                                        <h5>Section 80C Investments (Max: ₹1,50,000):</h5>
                                        <div class="value-grid">
                                            <div class="value-item">EPF Contribution: ₹<span id="guideEPF">0</span></div>
                                            <div class="value-item">ELSS Mutual Funds: ₹<span id="guideELSS">0</span></div>
                                            <div class="value-item">Life Insurance: ₹<span id="guideLifeInsurance">0</span></div>
                                            <div class="value-item">PPF Investment: ₹<span id="guidePPF">0</span></div>
                                        </div>
                                    </div>
                                    
                                    <div class="guide-section">
                                        <h5>Additional Deductions:</h5>
                                        <div class="value-grid">
                                            <div class="value-item">NPS 80CCD(1B): ₹<span id="guideNPS">0</span></div>
                                            <div class="value-item">Health Insurance 80D: ₹<span id="guideHealthInsurance">0</span></div>
                                            <div class="value-item">Home Loan Interest: ₹<span id="guideHomeLoanInterest">0</span></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div id="verification" class="guide-panel">
                            <h4>✅ Final Review & Submission</h4>
                            <div class="step-instructions">
                                <div class="final-summary">
                                    <div class="summary-item">Expected Tax Liability: ₹<span id="guideFinalTax">0</span></div>
                                    <div class="summary-item final-status">Final Status: <span id="guideFinalStatus">Calculate after entry</span></div>
                                </div>
                                <ol>
                                    <li><strong>Review Summary:</strong> Verify all income and deduction entries match our analysis</li>
                                    <li><strong>Tax Calculation:</strong> Portal will auto-calculate - should match our numbers</li>
                                    <li><strong>Submit Return:</strong> Click "Submit" after final review</li>
                                    <li><strong>e-Verification:</strong> Use Aadhaar OTP, Net Banking, or Bank Account</li>
                                </ol>
                                <div class="guide-tip success">
                                    ✅ <strong>Success:</strong> Your ITR will be processed within 24-48 hours after e-verification.
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Correction Modal -->
        <div class="correction-modal" id="correctionModal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>✏️ Review & Correct Your Details</h3>
                    <button class="modal-close" onclick="closeCorrectionModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Correction form content will be added here -->
                    <p>Correction form will be loaded here...</p>
                </div>
            </div>
        </div>
        
        <style>
        /* Multi-Page Navigation Styles */
        .page-container {
            min-height: 100vh;
        }
        
        .page {
            display: none;
            min-height: 100vh;
            padding: 1rem 0 2rem 0; /* Reduced top padding since page-header has margin-top */
        }
        
        .page.active {
            display: block;
        }
        
        .page-header {
            background: rgba(26, 35, 50, 0.8);
            backdrop-filter: blur(20px);
            padding: 2rem;
            margin-top: 6rem; /* Add top margin to avoid header overlap */
            margin-bottom: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 1rem;
            position: relative;
            z-index: 10; /* Ensure it's above background elements but below modals */
        }
        
        .page-header h1 {
            color: #00ff7f;
            margin: 0;
            font-size: 2rem;
            text-align: center;
            flex: 1;
        }
        
        .header-actions {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        .btn-back {
            min-width: 150px;
        }
        
        .btn-large {
            font-size: 1.2rem;
            padding: 1rem 2rem;
            min-width: 300px;
            margin-top: 1rem;
        }
        
        /* Upload Actions - Completely Separate */
        .upload-actions {
            text-align: center;
            margin: 2rem auto;
            max-width: 600px;
        }
        
        /* Upload section enhancements */
        .upload-section {
            position: relative;
            background: rgba(26, 35, 50, 0.8);
            backdrop-filter: blur(20px);
            border-radius: 15px;
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        /* Upload Zone - Higher Opacity */
        .upload-zone {
            background: rgba(45, 55, 72, 0.7) !important;
            border: 2px dashed rgba(72, 187, 120, 0.6) !important;
            backdrop-filter: blur(15px);
        }
        
        /* Upload Container - Higher Opacity */
        .upload-container {
            background: rgba(26, 35, 50, 0.8);
            backdrop-filter: blur(20px);
            border-radius: 15px;
            padding: 2rem;
        }
        
        /* File Management Section */
        .file-management-section {
            backdrop-filter: blur(20px);
        }
        
        /* Selected Files Container - Completely Outside */
        .selected-files-container {
            background: rgba(26, 35, 50, 0.8);
            border-radius: 15px;
            border: 1px solid rgba(72, 187, 120, 0.3);
            padding: 2rem;
            margin: 0 auto;
            backdrop-filter: blur(10px);
            max-width: 900px;
        }
        
        /* File List Styles */
        .file-list {
            background: rgba(30, 41, 59, 0.6);
            border-radius: 10px;
            border: 1px solid rgba(100, 116, 139, 0.2);
            backdrop-filter: blur(10px);
            max-height: 300px;
            overflow-y: auto;
            padding: 1.5rem;
        }
        
        /* Upload Button Area - Small Clickable Zone */
        .upload-button-area:hover {
            background: rgba(72, 187, 120, 0.3) !important;
            border-color: #48bb78 !important;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(72, 187, 120, 0.3);
        }
        
        /* Process Section */
        .process-section {
            max-width: 600px;
            margin: 0 auto;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 0.75rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin-bottom: 0.5rem;
            color: #e2e8f0;
        }
        
        .file-item:last-child {
            margin-bottom: 0;
        }
        
        .file-icon {
            font-size: 1.5rem;
        }
        
        .file-name {
            font-weight: 600;
            color: #f8fafc;
            font-size: 1rem;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            max-width: 300px;
        }
        
        .file-name-container {
            display: flex;
            align-items: center;
            min-width: 0;
            flex: 1;
        }
        
        .file-extension {
            font-weight: 600;
            color: #00ff7f;
            margin-left: 0.25rem;
            flex-shrink: 0;
        }
        
        .file-size {
            color: #a0aec0;
            font-size: 0.9rem;
        }
        
        /* Report Container */
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        
        .metric-card {
            background: rgba(45, 55, 72, 0.8);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            backdrop-filter: blur(15px);
            display: flex;
            align-items: center;
            gap: 1rem;
            transition: all 0.3s ease;
        }
        
        .metric-card:hover {
            border-color: #00ff7f;
            box-shadow: 0 5px 20px rgba(0, 255, 127, 0.2);
            transform: translateY(-3px);
        }
        
        .metric-card.highlight {
            border-color: #00ff7f;
            background: rgba(0, 255, 127, 0.1);
        }
        
        .metric-card.savings {
            border-color: #22c55e;
            background: rgba(34, 197, 94, 0.1);
        }
        
        .metric-card.refund {
            border-color: #3b82f6;
            background: rgba(59, 130, 246, 0.1);
        }
        
        .metric-card.regime {
            border-color: #f59e0b;
            background: rgba(245, 158, 11, 0.1);
        }
        
        .metric-icon {
            font-size: 2.5rem;
            opacity: 0.8;
        }
        
        .metric-content h3 {
            margin: 0 0 0.5rem 0;
            color: #a0aec0;
            font-size: 1rem;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #00ff7f;
        }
        
        /* Chart Section */
        .chart-section {
            background: rgba(45, 55, 72, 0.8);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            margin-bottom: 3rem;
        }
        
        .income-chart {
            margin-top: 2rem;
        }
        
        .income-bar-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 1rem;
            overflow: hidden;
        }
        
        .income-bar {
            display: flex;
            height: 60px;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .bar-segment {
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            transition: all 0.3s ease;
            min-width: 100px;
        }
        
        .bar-segment.salary {
            background: linear-gradient(135deg, #00ff7f 0%, #00e676 100%);
        }
        
        .bar-segment.interest {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        }
        
        .bar-segment.capital {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        }
        
        .bar-label {
            font-size: 0.9rem;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
        }
        
        /* Detailed Income Breakdown Styles */
        .income-breakdown-section {
            background: rgba(45, 55, 72, 0.6);
            border-radius: 12px;
            margin-bottom: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .income-breakdown-section:hover {
            border-color: rgba(0, 255, 127, 0.3);
        }
        
        .income-breakdown-section.gross-total {
            background: rgba(0, 255, 127, 0.1);
            border-color: rgba(0, 255, 127, 0.3);
        }
        
        .breakdown-header {
            padding: 1.2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .breakdown-header:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        
        .breakdown-header h4 {
            margin: 0;
            color: #e2e8f0;
            font-size: 1.1rem;
            flex: 1;
        }
        
        .breakdown-total {
            font-size: 1.2rem;
            font-weight: 700;
            color: #00ff7f;
            margin-right: 1rem;
        }
        
        .breakdown-total.highlight {
            font-size: 1.4rem;
            background: linear-gradient(45deg, #00ff7f, #00e676);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0 0 20px rgba(0, 255, 127, 0.3);
        }
        
        .toggle-icon {
            font-size: 1rem;
            color: #a0aec0;
            transition: transform 0.3s ease;
        }
        
        .toggle-icon.rotated {
            transform: rotate(-90deg);
        }
        
        .breakdown-details {
            padding: 0 1.2rem 1.2rem 1.2rem;
            display: none;
            animation: slideDown 0.3s ease-out;
        }
        
        .breakdown-details.open {
            display: block;
        }
        
        .breakdown-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            color: #e2e8f0;
        }
        
        .breakdown-item:last-child:not(.total) {
            border-bottom: none;
        }
        
        .breakdown-item.total {
            border-bottom: none;
            font-size: 1.1rem;
            color: #00ff7f;
            background: rgba(0, 255, 127, 0.05);
            margin: 0.5rem -1rem -1rem -1rem;
            padding: 1rem 1rem;
            border-radius: 0 0 12px 12px;
        }
        
        .breakdown-item.total.highlight {
            background: rgba(0, 255, 127, 0.15);
            box-shadow: 0 0 20px rgba(0, 255, 127, 0.2);
        }
        
        .breakdown-divider {
            height: 2px;
            background: linear-gradient(90deg, transparent, rgba(0, 255, 127, 0.5), transparent);
            margin: 0.8rem 0;
            border-radius: 2px;
        }
        
        .income-visual-chart {
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .income-visual-chart h4 {
            color: #e2e8f0;
            margin-bottom: 1.5rem;
            text-align: center;
        }
        
        @keyframes slideDown {
            from {
                opacity: 0;
                max-height: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                max-height: 300px;
                transform: translateY(0);
            }
        }
        
        /* Regime Comparison */
        .comparison-section {
            margin-bottom: 3rem;
        }
        
        .regime-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-top: 2rem;
        }
        
        .regime-card {
            background: rgba(45, 55, 72, 0.8);
            padding: 2rem;
            border-radius: 15px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(15px);
            transition: all 0.3s ease;
        }
        
        .regime-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .regime-card.recommended {
            border-color: #00ff7f;
            box-shadow: 0 0 30px rgba(0, 255, 127, 0.3);
        }
        
        .regime-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .regime-header h4 {
            margin: 0;
            color: #e2e8f0;
        }
        
        .regime-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }
        
        .regime-badge.recommended {
            background: #00ff7f;
            color: #000;
        }
        
        .regime-badge.alternative {
            background: rgba(255, 255, 255, 0.2);
            color: #a0aec0;
        }
        
        .regime-amount {
            font-size: 2.5rem;
            font-weight: 800;
            color: #00ff7f;
            margin-bottom: 1rem;
        }
        
        .regime-details {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .detail-item {
            display: flex;
            justify-content: space-between;
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            color: #a0aec0;
        }
        
        .detail-item:last-child {
            border-bottom: none;
        }
        
        .detail-item.status {
            font-weight: 600;
            color: #00ff7f;
        }
        
        .detail-item span {
            color: #e2e8f0;
        }
        
        /* HRA Section */
        .hra-section {
            background: rgba(45, 55, 72, 0.8);
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
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            color: #e2e8f0;
        }
        
        .hra-item.highlight {
            background: rgba(0, 255, 127, 0.1);
            border: 1px solid #00ff7f;
            font-weight: 600;
            color: #00ff7f;
        }
        
        /* Guide Container */
        .guide-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        .guide-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }
        
        .tab-button {
            padding: 1rem 1.5rem;
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
        
        .guide-content {
            background: rgba(45, 55, 72, 0.8);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            min-height: 400px;
        }
        
        .guide-panel {
            display: none;
        }
        
        .guide-panel.active {
            display: block;
        }
        
        .step-instructions {
            background: rgba(0, 0, 0, 0.2);
            padding: 1.5rem;
            border-radius: 10px;
            margin-top: 1rem;
        }
        
        .step-instructions ol {
            margin: 1rem 0;
            padding-left: 2rem;
        }
        
        .step-instructions li {
            margin-bottom: 1rem;
            line-height: 1.6;
            color: #e2e8f0;
        }
        
        .form-recommendation {
            background: rgba(0, 255, 127, 0.1);
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid #00ff7f;
        }
        
        .form-options {
            display: grid;
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .form-option {
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            color: #e2e8f0;
        }
        
        .value-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        
        .value-item {
            display: flex;
            justify-content: space-between;
            padding: 0.75rem 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            color: #e2e8f0;
        }
        
        .value-item.highlight {
            background: rgba(0, 255, 127, 0.1);
            border: 1px solid #00ff7f;
            font-weight: 600;
        }
        
        .guide-section {
            margin-bottom: 2rem;
        }
        
        .guide-section h5 {
            color: #00ff7f;
            margin: 1.5rem 0 1rem 0;
        }
        
        .guide-tip {
            background: rgba(0, 255, 127, 0.1);
            padding: 1rem;
            border-left: 4px solid #00ff7f;
            margin-top: 1rem;
            border-radius: 0 8px 8px 0;
        }
        
        .guide-tip.success {
            background: rgba(34, 197, 94, 0.1);
            border-left-color: #22c55e;
        }
        
        .final-summary {
            background: rgba(0, 255, 127, 0.1);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border: 1px solid #00ff7f;
        }
        
        .summary-item {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
            color: #e2e8f0;
        }
        
        .summary-item.final-status {
            font-weight: 600;
            color: #00ff7f;
        }
        
        /* Page Actions */
        .page-actions {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin-top: 3rem;
            flex-wrap: wrap;
        }
        
        /* Modal Styles */
        .correction-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .modal-content {
            background: rgba(26, 35, 50, 0.95);
            padding: 2rem;
            border-radius: 15px;
            border: 1px solid rgba(0, 255, 127, 0.3);
            max-width: 80%;
            max-height: 80%;
            overflow-y: auto;
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .modal-close {
            background: none;
            border: none;
            color: #00ff7f;
            font-size: 2rem;
            cursor: pointer;
            padding: 0;
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* Mobile Responsive */
        @media (max-width: 768px) {
            .page-header {
                flex-direction: column;
                text-align: center;
            }
            
            .page-header h1 {
                font-size: 1.5rem;
            }
            
            .header-actions {
                width: 100%;
                justify-content: center;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
            }
            
            .regime-cards {
                grid-template-columns: 1fr;
            }
            
            .guide-tabs {
                flex-direction: column;
            }
            
            .tab-button {
                text-align: center;
            }
            
            .value-grid {
                grid-template-columns: 1fr;
            }
            
            .page-actions {
                flex-direction: column;
                align-items: center;
            }
            
            .page-actions .btn {
                width: 100%;
                max-width: 300px;
            }
            
            .modal-content {
                max-width: 95%;
                margin: 1rem;
            }
        }
        
        /* Fix header z-index to ensure proper layering */
        header {
            z-index: 1000 !important; /* Ensure header stays above page content */
        }
        
        /* Enhanced AI Processing Animation Styles with Background Blur */
        .upload-animation {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(15px);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: modalFadeIn 0.5s ease-out;
        }
        
        .processing-modal {
            background: rgba(13, 17, 23, 0.95);
            border-radius: 20px;
            padding: 3rem;
            width: 90%;
            max-width: 700px;
            box-shadow: 0 25px 50px rgba(0, 255, 127, 0.4);
            border: 2px solid rgba(0, 255, 127, 0.6);
            color: #e2e8f0;
            text-align: center;
            position: relative;
            animation: modalSlideIn 0.6s ease-out;
        }
        
        .ai-processing-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2rem;
        }
        
        .ai-brain-animation {
            width: 120px;
            height: 120px;
            position: relative;
            margin-bottom: 1rem;
        }
        
        .neural-network {
            width: 100%;
            height: 100%;
            border: 3px solid #00ff7f;
            border-radius: 50%;
            position: relative;
            animation: neuralPulse 2s ease-in-out infinite;
        }
        
        .neural-network::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60%;
            height: 60%;
            border: 2px solid #00ff7f;
            border-radius: 50%;
            animation: innerNeuralRotate 3s linear infinite;
            opacity: 0.7;
        }
        
        .neural-network::after {
            content: '🧠';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 2.5rem;
            animation: brainPulse 1.5s ease-in-out infinite alternate;
        }
        
        .processing-stage {
            font-size: 1.4rem;
            font-weight: 600;
            color: #00ff7f;
            margin-bottom: 1rem;
            min-height: 2rem;
            animation: textGlow 2s ease-in-out infinite alternate;
        }
        
        .processing-progress {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 1.5rem;
        }
        
        .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #00ff7f, #00bfa5);
            border-radius: 10px;
            width: 0%;
            transition: width 0.5s ease;
            animation: progressGlow 2s ease-in-out infinite alternate;
        }
        
        .processing-steps-detailed {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 100%;
            margin: 2rem 0;
            position: relative;
            gap: 1rem;
        }
        
        .processing-steps-container {
            display: flex;
            align-items: center;
            position: relative;
        }
        
        .step-connector {
            width: 40px;
            height: 3px;
            background: rgba(255, 255, 255, 0.2);
            position: relative;
            margin: 0 -5px;
            border-radius: 2px;
            overflow: hidden;
        }
        
        .step-connector-progress {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #00ff7f, #4ade80);
            border-radius: 2px;
            transition: width 1s ease-in-out;
            box-shadow: 0 0 8px rgba(0, 255, 127, 0.6);
        }
        
        .main-progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            margin: 1.5rem 0;
            overflow: hidden;
            position: relative;
        }
        
        .main-progress-fill {
            width: 0%;
            height: 100%;
            background: linear-gradient(90deg, #00ff7f, #4ade80, #22d3ee);
            border-radius: 10px;
            transition: width 0.8s ease-out;
            position: relative;
            overflow: hidden;
        }
        
        .progress-shine {
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
            animation: progressShine 2s infinite;
        }
        
        .processing-step {
            min-width: 70px;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 1rem 0.75rem;
            background: rgba(0, 0, 0, 0.4);
            border-radius: 15px;
            border: 2px solid rgba(255, 255, 255, 0.1);
            transition: all 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            z-index: 1;
        }
        
        .processing-step.pending {
            opacity: 0.5;
            transform: scale(0.9);
        }
        
        .processing-step.active {
            background: rgba(0, 255, 127, 0.15);
            border-color: #00ff7f;
            transform: scale(1.05);
            box-shadow: 0 8px 25px rgba(0, 255, 127, 0.4);
            animation: activeStepGlow 2s ease-in-out infinite alternate;
        }
        
        .processing-step.completed {
            background: rgba(0, 255, 127, 0.25);
            border-color: #00ff7f;
            box-shadow: 0 5px 15px rgba(0, 255, 127, 0.3);
        }
        
        .file-processing-list {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 1rem;
            margin: 1rem 0;
            max-height: 120px;
            overflow-y: auto;
        }
        
        .file-processing-item {
            display: flex;
            align-items: center;
            padding: 0.5rem;
            margin-bottom: 0.5rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .file-processing-item.active {
            background: rgba(0, 255, 127, 0.1);
            border: 1px solid #00ff7f;
            animation: fileGlow 1.5s ease-in-out infinite alternate;
        }
        
        .file-processing-item.completed {
            background: rgba(0, 255, 127, 0.2);
            border: 1px solid #00ff7f;
        }
        
        .file-status-icon {
            margin-right: 0.75rem;
            font-size: 1.2rem;
        }
        
        .step-icon {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            opacity: 0.5;
            transition: all 0.5s ease;
        }
        
        .processing-step.active .step-icon {
            opacity: 1;
            animation: iconBounce 1s ease-in-out infinite alternate;
        }
        
        .processing-step.completed .step-icon {
            opacity: 1;
            transform: scale(1.2);
        }
        
        .step-text {
            font-size: 0.75rem;
            text-align: center;
            opacity: 0.7;
            font-weight: 500;
            line-height: 1.2;
        }
        
        .processing-step.active .step-text {
            opacity: 1;
            color: #00ff7f;
            font-weight: 600;
        }
        
        .processing-step.completed .step-text {
            opacity: 1;
            color: #00ff7f;
        }
        
        .privacy-notice {
            font-size: 0.9rem;
            color: #a0aec0;
            margin-top: 1.5rem;
            padding: 1rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 4px solid #00ff7f;
        }
        
        /* Keyframe Animations */
        @keyframes modalFadeIn {
            from {
                opacity: 0;
                backdrop-filter: blur(0px);
            }
            to {
                opacity: 1;
                backdrop-filter: blur(15px);
            }
        }
        
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: scale(0.8) translateY(-20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        @keyframes neuralPulse {
            0%, 100% {
                border-color: #00ff7f;
                box-shadow: 0 0 20px rgba(0, 255, 127, 0.5);
            }
            50% {
                border-color: #00bfa5;
                box-shadow: 0 0 30px rgba(0, 191, 165, 0.7);
            }
        }
        
        @keyframes innerNeuralRotate {
            from {
                transform: translate(-50%, -50%) rotate(0deg);
            }
            to {
                transform: translate(-50%, -50%) rotate(360deg);
            }
        }
        
        @keyframes brainPulse {
            from {
                transform: translate(-50%, -50%) scale(1);
                filter: hue-rotate(0deg);
            }
            to {
                transform: translate(-50%, -50%) scale(1.1);
                filter: hue-rotate(20deg);
            }
        }
        
        @keyframes textGlow {
            from {
                text-shadow: 0 0 10px rgba(0, 255, 127, 0.5);
            }
            to {
                text-shadow: 0 0 20px rgba(0, 255, 127, 0.8);
            }
        }
        
        @keyframes progressGlow {
            from {
                box-shadow: 0 0 5px rgba(0, 255, 127, 0.5);
            }
            to {
                box-shadow: 0 0 15px rgba(0, 255, 127, 0.8);
            }
        }
        
        @keyframes iconBounce {
            from {
                transform: translateY(0);
            }
            to {
                transform: translateY(-5px);
            }
        }
        
        @keyframes activeStepGlow {
            from {
                box-shadow: 0 8px 25px rgba(0, 255, 127, 0.4);
                border-color: #00ff7f;
            }
            to {
                box-shadow: 0 12px 35px rgba(0, 255, 127, 0.6);
                border-color: #4ade80;
            }
        }
        
        @keyframes fileGlow {
            from {
                box-shadow: 0 2px 10px rgba(0, 255, 127, 0.3);
            }
            to {
                box-shadow: 0 4px 20px rgba(0, 255, 127, 0.5);
            }
        }
        
        @keyframes progressShine {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        /* Mobile responsiveness for processing animation */
        @media (max-width: 640px) {
            .upload-animation {
                width: 95%;
                padding: 2rem 1.5rem;
            }
            
            .ai-brain-animation {
                width: 80px;
                height: 80px;
            }
            
            .neural-network::after {
                font-size: 2rem;
            }
            
            .processing-stage {
                font-size: 1.1rem;
            }
            
            .processing-steps-detailed {
                flex-direction: column;
                gap: 1rem;
            }
            
            .processing-step {
                flex-direction: row;
                justify-content: flex-start;
                padding: 0.75rem;
            }
            
            .step-icon {
                margin-right: 1rem;
                margin-bottom: 0;
                font-size: 1.25rem;
            }
            
            .step-text {
                font-size: 0.85rem;
                text-align: left;
            }
        }
        
        /* Page 2 styles - match reference design exactly */
        #page2 {
            background: #f7f9fc;
            color: #0f172a;
            min-height: 100vh;
            position: relative;
            z-index: 1000;
            font-family: ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial;
            --bg:#f7f9fc; 
            --card:#fff; 
            --ink:#0f172a; 
            --muted:#475569; 
            --brand:#2563eb; 
            --ok:#16a34a; 
            --warn:#b45309; 
            --soft:#e2e8f0;
            padding-top: 0 !important;
            margin-top: 0 !important;
        }

        /* Hide any existing fixed headers when page 2 is active */
        #page2 ~ header,
        #page2 + header,
        body:has(#page2[style*="block"]) header:not(#page2 header) {
            display: none !important;
        }
        
        #page2::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #f7f9fc;
            z-index: -1;
        }

        /* Page 2 header styling - override any existing header */
        #page2 header {
            background: linear-gradient(135deg, #1e40af, #2563eb) !important;
            color: #fff !important;
            padding: 28px 16px !important;
            position: static !important;
            z-index: 10;
            width: 100% !important;
            margin: 0 !important;
            top: auto !important;
            left: auto !important;
            transform: none !important;
        }

        #page2 header .wrap {
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: center;
            justify-content: space-between;
        }

        #page2 h1 {
            margin: 0;
            font-size: clamp(22px, 3.2vw, 32px);
        }

        #page2 .badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        #page2 .badge {
            background: rgba(255,255,255,.18);
            border: 1px solid rgba(255,255,255,.25);
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
        }

        #page2 .subtle {
            color: var(--muted);
            font-size: 14px;
        }

        /* Container and grid layout - ensure no overlap with header */
        #page2 .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 24px 16px 32px;
            position: relative;
            z-index: 1;
            clear: both;
        }

        #page2 .grid {
            display: grid;
            grid-template-columns: 1.8fr 1fr;
            gap: 18px;
        }

        #page2 .card {
            background: var(--card);
            border: 1px solid var(--soft);
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 6px 20px rgba(2,6,23,.04);
        }

        #page2 .card h2 {
            margin: 4px 0 10px;
            font-size: 18px;
        }

        /* Bars styling */
        #page2 .bars {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        #page2 .bar {
            background: #eef2ff;
            border-radius: 999px;
            overflow: hidden;
            position: relative;
            height: 12px;
            border: 1px solid #e2e8f0;
        }

        #page2 .bar > span {
            position: absolute;
            inset: 0;
            width: 0%;
            background: linear-gradient(90deg, #60a5fa, #2563eb);
            transition: width .4s ease;
        }

        #page2 .bar label {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            color: #0f172a;
            mix-blend-mode: overlay;
        }

        /* Table styling */
        #page2 table {
            width: 100%;
            border-collapse: collapse;
        }

        #page2 th, #page2 td {
            padding: 10px 8px;
            border-bottom: 1px solid var(--soft);
            text-align: left;
            font-size: 14px;
        }

        #page2 th {
            background: #f8fafc;
        }

        #page2 td.amount {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        /* Statistics grid */
        #page2 .statgrid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }

        #page2 .stat {
            background: #f8fafc;
            border: 1px solid var(--soft);
            border-radius: 12px;
            padding: 10px;
        }

        #page2 .stat .big {
            font-size: 18px;
            font-weight: 700;
        }

        #page2 .delta.ok {
            color: var(--ok);
        }

        #page2 .delta.warn {
            color: var(--warn);
        }

        /* Form elements */
        #page2 .row {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        #page2 .row > * {
            flex: 1;
        }

        #page2 .field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        #page2 .field input[type="number"], 
        #page2 .field input[type="text"], 
        #page2 .field select {
            border: 1px solid var(--soft);
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 14px;
        }

        #page2 .btn {
            background: var(--brand);
            color: #fff;
            border: 0;
            padding: 10px 14px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
        }

        #page2 .btn.secondary {
            background: #0ea5e9;
        }

        #page2 .btn.ghost {
            background: #fff;
            color: var(--brand);
            border: 1px solid var(--soft);
        }

        #page2 .btn:disabled {
            opacity: .6;
            cursor: not-allowed;
        }

        #page2 .switch {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* Stepper styling */
        #page2 .stepper {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 14px;
        }

        #page2 .steps {
            background: #f8fafc;
            border: 1px solid var(--soft);
            border-radius: 12px;
            padding: 8px;
            max-height: 520px;
            overflow: auto;
            display: flex;
            justify-content: flex-start;
            flex-direction: column;
            gap: 4px;
        }

        #page2 .stepbtn {
            width: 100%;
            text-align: left;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid transparent;
            background: transparent;
            cursor: pointer;
            font-weight: 600;
            color: #0f172a;
        }

        #page2 .stepbtn:hover {
            background: #eef2ff;
        }

        #page2 .stepbtn[aria-current="step"] {
            background: #e0e7ff;
            border-color: #c7d2fe;
        }

        #page2 .stepcontent {
            border: 1px solid var(--soft);
            border-radius: 12px;
            padding: 14px;
            background: var(--card);
        }

        #page2 .tip {
            background: #ecfeff;
            border: 1px dashed #67e8f9;
            padding: 8px 10px;
            border-radius: 10px;
            font-size: 13px;
        }

        #page2 .checklist {
            display: grid;
            gap: 8px;
        }

        #page2 .check {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        #page2 .footer-cta {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            align-items: center;
            flex-wrap: wrap;
        }

        #page2 a.portal {
            text-decoration: none;
        }

        #page2 .muted {
            color: var(--muted);
        }
        
        /* Hide WebGL canvas on page 2 */
        #page2 ~ #webgl-canvas {
            display: none;
        }
        
        /* New Analysis Page Styles */
        .analysis-header {
            background: linear-gradient(135deg, #1e40af, #2563eb);
            color: #fff;
            padding: 28px 16px;
            position: relative;
            z-index: 1001;
        }
        
        .header-wrap {
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: center;
            justify-content: space-between;
        }
        
        .analysis-header h1 {
            margin: 0;
            font-size: clamp(22px, 3.2vw, 32px);
        }
        
        .header-subtitle {
            color: rgba(255, 255, 255, 0.9);
            font-size: 14px;
            margin-top: 4px;
        }
        
        .header-badges {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .badge {
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.25);
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 12px;
        }
        
        .analysis-container {
            max-width: 1100px;
            margin: 24px auto;
            padding: 0 16px 32px;
        }
        
        .analysis-grid {
            display: grid;
            grid-template-columns: 1.8fr 1fr;
            gap: 18px;
            margin-bottom: 18px;
        }
        
        .analysis-card {
            background: #fff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 16px;
            box-shadow: 0 6px 20px rgba(2, 6, 23, 0.04);
        }
        
        .analysis-card h2 {
            margin: 4px 0 10px;
            font-size: 18px;
            color: #0f172a;
        }
        
        .card-subtitle {
            color: #475569;
            font-size: 14px;
            margin-bottom: 16px;
        }
        
        .form-row {
            display: flex;
            gap: 10px;
            align-items: flex-end;
            margin-bottom: 12px;
        }
        
        .form-row > * {
            flex: 1;
        }
        
        .form-field {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .form-field label {
            font-size: 13px;
            font-weight: 500;
            color: #374151;
        }
        
        .form-field input[type="number"], .form-field input[type="text"], .form-field select {
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 10px 12px;
            font-size: 14px;
            transition: border-color 0.2s;
        }
        
        .form-field input:focus {
            outline: none;
            border-color: #2563eb;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }
        
        .form-switch {
            display: flex;
            align-items: center;
            gap: 8px;
            padding-top: 20px;
        }
        
        .form-switch input[type="checkbox"] {
            width: 16px;
            height: 16px;
        }
        
        .btn {
            background: #2563eb;
            color: #fff;
            border: 0;
            padding: 10px 14px;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .btn:hover {
            background: #1d4ed8;
        }
        
        .btn.btn-secondary {
            background: #0ea5e9;
        }
        
        .btn.btn-secondary:hover {
            background: #0284c7;
        }
        
        .btn.btn-ghost {
            background: #fff;
            color: #2563eb;
            border: 1px solid #e2e8f0;
        }
        
        .btn.btn-ghost:hover {
            background: #f8fafc;
        }
        
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .section-divider {
            margin: 14px 0;
            border: none;
            border-top: 1px solid #e2e8f0;
        }
        
        /* Income Table and Bars */
        .income-bars {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 16px;
        }
        
        .income-table-container {
            margin-top: 12px;
            overflow: auto;
        }
        
        .income-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .income-table th, .income-table td {
            padding: 10px 8px;
            border-bottom: 1px solid #e2e8f0;
            text-align: left;
            font-size: 14px;
        }
        
        .income-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
        }
        
        .amount-col, .income-table .amount-col {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }
        
        .income-table input {
            width: 120px;
            text-align: right;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px 8px;
            font-size: 14px;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-top: 12px;
        }
        
        .regime-comparison-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 10px;
        }
        
        .stat-item {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 10px;
        }
        
        .stat-label {
            color: #475569;
            font-size: 12px;
            margin-bottom: 4px;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: #0f172a;
        }
        
        .delta.ok {
            color: #16a34a;
        }
        
        .delta.warn {
            color: #b45309;
        }
        
        /* Progress bars for income visualization */
        .income-bar {
            background: #eef2ff;
            border-radius: 999px;
            overflow: hidden;
            position: relative;
            height: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 4px;
        }
        
        .income-bar > span {
            position: absolute;
            inset: 0;
            width: 0%;
            background: linear-gradient(90deg, #60a5fa, #2563eb);
            transition: width 0.4s ease;
        }
        
        .income-bar label {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            color: #0f172a;
            mix-blend-mode: overlay;
        }
        
        /* Stepper */
        .stepper {
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 14px;
            margin-top: 10px;
        }
        
        .filing-steps {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 8px;
            max-height: 520px;
            overflow: auto;
        }
        
        .filing-steps button {
            width: 100%;
            text-align: left;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid transparent;
            background: transparent;
            cursor: pointer;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 4px;
        }
        
        .filing-steps button:hover {
            background: #eef2ff;
        }
        
        .filing-steps button[aria-current="step"] {
            background: #e0e7ff;
            border-color: #c7d2fe;
        }
        
        .step-content {
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 14px;
            background: #fff;
        }
        
        .filing-footer {
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            align-items: center;
            flex-wrap: wrap;
            margin-top: 12px;
        }
        
        .portal-link {
            text-decoration: none;
        }
        
        .pre-checklist {
            display: grid;
            gap: 8px;
        }
        
        .check {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .analysis-grid {
                grid-template-columns: 1fr;
            }
            
            .regime-comparison-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .stepper {
                grid-template-columns: 1fr;
            }
        }
        
        </style>
        
        <script>
        // Multi-Page Navigation - Enhanced with debugging
        function showPage(pageId) {
            // Hide WebGL canvas for page 2 (clean background)
            const canvas = document.getElementById('webgl-canvas');
            if (canvas) {
                canvas.style.display = pageId === 'page2' ? 'none' : 'block';
            }
            console.log('showPage called with:', pageId);
            
            // Hide all pages
            document.querySelectorAll('.page').forEach(page => {
                page.style.display = 'none';
                page.classList.remove('active');
            });
            
            // Show selected page
            const targetPage = document.getElementById(pageId);
            console.log('Target page found:', targetPage);
            
            if (targetPage) {
                targetPage.style.display = 'block';
                targetPage.classList.add('active');
                console.log('Page', pageId, 'is now visible');
                
                // Initialize reference design functions for page 2
                if (pageId === 'page2') {
                    initPage2();
                }
            } else {
                console.error('Page not found:', pageId);
                return;
            }
            
            // Special handling for page1 (show upload section)
            if (pageId === 'page1') {
                const mainSection = document.querySelector('main');
                if (mainSection) {
                    mainSection.style.display = 'block';
                }
                // Hide file management section when on page1
                const fileManagementSection = document.querySelector('.file-management-section');
                if (fileManagementSection) {
                    fileManagementSection.style.display = 'block';
                }
            } else {
                const mainSection = document.querySelector('main');
                if (mainSection) {
                    mainSection.style.display = 'none';
                }
                // Show file management section for other pages
                const fileManagementSection = document.querySelector('.file-management-section');
                if (fileManagementSection) {
                    fileManagementSection.style.display = 'none';
                }
            }
            
            // Scroll to top
            window.scrollTo(0, 0);
        }
        
        // Process Documents and Navigate - Fixed with proper event handling
        async function processDocuments(event) {
            console.log('processDocuments called');
            
            // CRITICAL: Stop all event propagation immediately
            if (event) {
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
            }
            
            const files = document.getElementById('fileInput').files;
            console.log('Files found:', files.length);
            
            if (files.length === 0) {
                alert('Please select documents to process first.');
                return false;
            }
            
            // Keep button visible and disable it during processing
            const processBtn = document.getElementById('processDocumentsBtn');
            const processBtnContainer = document.getElementById('processButtonContainer');
            
            if (processBtn) {
                processBtn.disabled = true;
                processBtn.textContent = '🔄 Processing...';
                processBtn.style.opacity = '0.6';
            }
            
            // Ensure button container stays visible
            if (processBtnContainer) {
                processBtnContainer.style.display = 'block';
            }
            
            // Process files (reuse existing logic)
            console.log('Calling processUploadedFiles with', files.length, 'files');
            console.log('About to convert files to array...');
            const filesArray = Array.from(files);
            console.log('Files array created:', filesArray.length, 'files');
            console.log('About to call processUploadedFiles...');
            console.log('processUploadedFiles function exists:', typeof processUploadedFiles);
            
            try {
                console.log('Calling processUploadedFiles now...');
                
                // Simple direct processing instead of calling the function
                console.log('Creating FormData directly...');
                const formData = new FormData();
                for (let file of filesArray) {
                    formData.append('files', file);
                }
                console.log('FormData created with', filesArray.length, 'files');
                
                // Show processing animation with file list
                showProcessingAnimation(filesArray);
                
                // Start progress polling
                const progressInterval = startProgressPolling();
                
                // Make API request
                console.log('Making API request...');
                const response = await fetch('/api/analyze_documents', {
                    method: 'POST',
                    body: formData
                });
                
                // Stop progress polling
                clearInterval(progressInterval);
                
                console.log('Response received:', response.status);
                const results = await response.json();
                console.log('Results:', results);
                
                // Hide processing animation
                hideProcessingAnimation();
                
                // Navigate to page 2
                console.log('Navigating to page 2...');
                showPage('page2');
                populateAnalysisResults(results);
                
                console.log('Process completed successfully!');
            } catch (error) {
                console.error('ERROR in processing:', error);
                console.error('Error stack:', error.stack);
                hideProcessingAnimation();
                alert('Error during processing: ' + error.message);
            }
            return false;
        }
        
        // Enhanced file processing that navigates to page 2
        async function processUploadedFiles(files) {
            try {
                console.log('=== processUploadedFiles called with files:', files);
                console.log('Files length:', files ? files.length : 'files is null/undefined');
            } catch (err) {
                console.error('Error in processUploadedFiles start:', err);
                throw err;
            }
            
            try {
                const formData = new FormData();
                console.log('FormData created successfully');
                
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    console.log(`Processing file ${i + 1}:`, file.name, file.size, 'bytes');
                    formData.append('files', file);
                }
                console.log('All files added to FormData');
                
                console.log('Starting document processing...');
                
                // Show processing animation
                showProcessingAnimation();
                
                console.log('Making API request to /api/analyze_documents...');
                const response = await fetch('/api/analyze_documents', {
                    method: 'POST',
                    body: formData
                });
                
                console.log('Response received - Status:', response.status);
                console.log('Response headers:', Object.fromEntries(response.headers));
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                console.log('Parsing response as JSON...');
                const results = await response.json();
                console.log('JSON parsing successful. Results:', results);
                
                if (results.error) {
                    throw new Error(results.error);
                }
                
                // Store results globally
                window.analysisResults = results;
                console.log('Analysis results received:', results);
                
                // Hide processing animation
                hideProcessingAnimation();
                
                // Navigate to page 2 and populate results
                setTimeout(() => {
                    console.log('Attempting to navigate to page2');
                    
                    // Ensure page exists before navigation
                    const page2 = document.getElementById('page2');
                    if (!page2) {
                        console.error('Page 2 not found in DOM');
                        alert('Navigation error: Page 2 not found. Please refresh and try again.');
                        return;
                    }
                    
                    showPage('page2');
                    populateAnalysisResults(results);
                }, 1000); // Increased timeout to ensure DOM is ready
                
            } catch (error) {
                console.error('Error processing files:', error);
                hideProcessingAnimation();
                alert('Error processing documents: ' + error.message);
            }
        }
        
        // Progress polling system
        function startProgressPolling() {
            console.log('Starting progress polling...');
            return setInterval(async () => {
                try {
                    const response = await fetch('/api/progress');
                    const progress = await response.json();
                    updateProgressVisualization(progress);
                } catch (error) {
                    console.error('Error polling progress:', error);
                }
            }, 500); // Poll every 500ms
        }
        
        function updateProgressVisualization(progress) {
            // Update main progress bar
            const mainProgressFill = document.getElementById('mainProgressFill');
            if (mainProgressFill) {
                mainProgressFill.style.width = `${progress.progress}%`;
            }
            
            // Update current stage text
            const currentStage = document.getElementById('currentStage');
            if (currentStage) {
                currentStage.textContent = progress.stage;
            }
            
            // Update step visualization
            updateStepVisualization(progress.step, progress.progress);
        }
        
        function updateStepVisualization(currentStep, overallProgress) {
            const steps = ['init', 'ocr', 'extract', 'classify', 'calculate', 'finalize'];
            const stepElements = steps.map(step => document.getElementById(`step-${step}`));
            const connectors = steps.slice(0, -1).map((_, i) => document.getElementById(`connector-${i}`));
            
            // Reset all steps
            stepElements.forEach(el => {
                if (el) {
                    el.classList.remove('active', 'completed');
                    el.classList.add('pending');
                }
            });
            
            // Reset all connectors
            connectors.forEach(connector => {
                if (connector) connector.style.width = '0%';
            });
            
            // Activate steps based on current progress
            const currentStepIndex = steps.indexOf(currentStep);
            
            stepElements.forEach((el, index) => {
                if (el) {
                    if (index < currentStepIndex) {
                        el.classList.remove('pending', 'active');
                        el.classList.add('completed');
                    } else if (index === currentStepIndex) {
                        el.classList.remove('pending', 'completed');
                        el.classList.add('active');
                    }
                }
            });
            
            // Animate connectors
            connectors.forEach((connector, index) => {
                if (connector && index < currentStepIndex) {
                    connector.style.width = '100%';
                } else if (connector && index === currentStepIndex && overallProgress > 0) {
                    // Partial progress on current connector
                    const stepProgress = Math.min(100, (overallProgress % (100 / steps.length)) * (steps.length / 100) * 100);
                    connector.style.width = `${stepProgress}%`;
                }
            });
        }
        
        // Enhanced Processing animation with multiple AI steps
        function showProcessingAnimation(files) {
            let processingAnimation = document.getElementById('processingAnimation');
            if (!processingAnimation) {
                processingAnimation = document.createElement('div');
                processingAnimation.className = 'upload-animation';
                processingAnimation.id = 'processingAnimation';
                processingAnimation.innerHTML = `
                    <div class="processing-modal">
                        <div class="ai-processing-container">
                        <div class="ai-brain-animation">
                            <div class="brain-core"></div>
                            <div class="neural-network">
                                <div class="neuron"></div>
                                <div class="neuron"></div>
                                <div class="neuron"></div>
                                <div class="neuron"></div>
                                <div class="neuron"></div>
                                <div class="neuron"></div>
                            </div>
                        </div>
                        
                        <h3 class="ai-title">🧠 AI Tax Analysis Engine</h3>
                        
                        <!-- Main Progress Bar -->
                        <div class="main-progress-bar">
                            <div class="main-progress-fill" id="mainProgressFill">
                                <div class="progress-shine"></div>
                            </div>
                        </div>
                        
                        <div class="processing-stage" id="currentStage">Initializing AI Models...</div>
                        
                        <!-- Processing Steps with Connectors -->
                        <div class="processing-steps-detailed">
                            <div class="processing-steps-container">
                                <div class="processing-step pending" id="step-init">
                                    <div class="step-icon">⚡</div>
                                    <div class="step-text">Initialize</div>
                                </div>
                                
                                <div class="step-connector">
                                    <div class="step-connector-progress" id="connector-0"></div>
                                </div>
                                
                                <div class="processing-step pending" id="step-ocr">
                                    <div class="step-icon">👁️</div>
                                    <div class="step-text">OCR Scan</div>
                                </div>
                                
                                <div class="step-connector">
                                    <div class="step-connector-progress" id="connector-1"></div>
                                </div>
                                
                                <div class="processing-step pending" id="step-extract">
                                    <div class="step-icon">📊</div>
                                    <div class="step-text">Extract</div>
                                </div>
                                
                                <div class="step-connector">
                                    <div class="step-connector-progress" id="connector-2"></div>
                                </div>
                                
                                <div class="processing-step pending" id="step-classify">
                                    <div class="step-icon">🏷️</div>
                                    <div class="step-text">Classify</div>
                                </div>
                                
                                <div class="step-connector">
                                    <div class="step-connector-progress" id="connector-3"></div>
                                </div>
                                
                                <div class="processing-step pending" id="step-calculate">
                                    <div class="step-icon">🧮</div>
                                    <div class="step-text">Calculate</div>
                                </div>
                                
                                <div class="step-connector">
                                    <div class="step-connector-progress" id="connector-4"></div>
                                </div>
                                
                                <div class="processing-step pending" id="step-finalize">
                                    <div class="step-icon">✨</div>
                                    <div class="step-text">Generate</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="ai-privacy-note">
                            🔒 All processing happens locally on your device<br>
                            Your data never leaves your computer
                        </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(processingAnimation);
            }
            processingAnimation.style.display = 'flex';
            
            // Start the step-by-step animation
            startDetailedProcessingSteps();
        }
        
        // Detailed AI processing steps animation
        function startDetailedProcessingSteps() {
            const steps = [
                { id: 'step-init', text: 'Loading AI Models...', duration: 1500 },
                { id: 'step-ocr', text: 'Scanning Documents with OCR...', duration: 2000 },
                { id: 'step-extract', text: 'Extracting Financial Data...', duration: 2500 },
                { id: 'step-classify', text: 'Classifying Document Types...', duration: 1800 },
                { id: 'step-calculate', text: 'Optimizing Tax Calculations...', duration: 2200 },
                { id: 'step-finalize', text: 'Generating Report & Recommendations...', duration: 1000 }
            ];
            
            let currentStep = 0;
            
            function processNextStep() {
                if (currentStep < steps.length) {
                    const step = steps[currentStep];
                    const stepElement = document.getElementById(step.id);
                    const stageElement = document.getElementById('currentStage');
                    
                    // Update current stage text
                    if (stageElement) {
                        stageElement.textContent = step.text;
                    }
                    
                    // Activate current step
                    if (stepElement) {
                        stepElement.classList.add('active');
                        const progressBar = stepElement.querySelector('.progress-bar');
                        if (progressBar) {
                            progressBar.style.width = '100%';
                        }
                    }
                    
                    // Mark previous steps as complete
                    for (let i = 0; i < currentStep; i++) {
                        const prevStep = document.getElementById(steps[i].id);
                        if (prevStep) {
                            prevStep.classList.add('completed');
                        }
                    }
                    
                    currentStep++;
                    setTimeout(processNextStep, step.duration);
                }
            }
            
            processNextStep();
        }
        
        function hideProcessingAnimation() {
            const processingAnimation = document.getElementById('processingAnimation');
            if (processingAnimation) {
                processingAnimation.style.opacity = '0';
                processingAnimation.style.transform = 'translate(-50%, -50%) scale(0.8)';
                setTimeout(() => {
                    processingAnimation.style.display = 'none';
                    processingAnimation.style.opacity = '1';
                    processingAnimation.style.transform = 'translate(-50%, -50%) scale(1)';
                }, 300);
            }
            
            // Re-enable the process button but keep it visible
            const processBtn = document.getElementById('processDocumentsBtn');
            const processBtnContainer = document.getElementById('processButtonContainer');
            
            if (processBtn) {
                processBtn.disabled = false;
                processBtn.textContent = '✅ Analysis Complete';
                processBtn.style.opacity = '1';
                processBtn.style.cursor = 'pointer';
                processBtn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
            }
            
            // Keep button container visible
            if (processBtnContainer) {
                processBtnContainer.style.display = 'block';
            }
        }
        
        // Mock data model for reference design functionality
        const taxModel = {
            incomes: [
                { category: 'Salary', sub: 'Basic', amount: 0 },
                { category: 'Salary', sub: 'HRA', amount: 0 },
                { category: 'Salary', sub: 'Special Allowances', amount: 0 },
                { category: 'Interest', sub: 'Savings Interest', amount: 0 },
                { category: 'Capital Gains', sub: 'LTCG (Equity)', amount: 0 },
                { category: 'Other', sub: 'Freelance', amount: 0 },
            ],
            deductions: { d80c: 120000, d80d: 25000, d80ccd1b: 0, d80tta: 0 },
            hraInput: { basic: 500000, da: 0, hraReceived: 150000, rentPaid: 180000, commission: 0, metro: true }
        };

        // Format currency helper
        const fmt = n => `₹${Math.max(0, Math.round(n)).toLocaleString('en-IN')}`;

        // Render income bars and table
        function renderIncomeInterface() {
            const barsEl = document.getElementById('income-bars');
            const tableBody = document.getElementById('income-tbody');
            
            if (!barsEl || !tableBody) return;
            
            const total = taxModel.incomes.reduce((a, b) => a + (Number(b.amount) || 0), 0);
            
            // Bars by category totals
            const cats = [...new Set(taxModel.incomes.map(i => i.category))];
            const totals = cats.map(c => taxModel.incomes.filter(i => i.category === c).reduce((a, b) => a + Number(b.amount || 0), 0));
            const max = Math.max(...totals, 1);
            
            barsEl.innerHTML = cats.map((c, idx) => {
                const pct = Math.round((totals[idx] / max) * 100);
                return `<div><div style="display:flex; justify-content:space-between; margin-bottom:4px; font-weight:600;"><span>${c}</span><span style="color:#475569;">${fmt(totals[idx])}</span></div><div class="income-bar"><span style="width:${pct}%"></span><label>${pct}%</label></div></div>`;
            }).join('');
            
            // Table rows (editable amounts)
            tableBody.innerHTML = taxModel.incomes.map((r, idx) => `
                <tr>
                    <td>${r.category}</td>
                    <td>${r.sub}</td>
                    <td class="amount-col"><input type="number" min="0" value="${r.amount}" data-row="${idx}" /></td>
                </tr>
            `).join('');
            
            // Stats
            const gross = total;
            const ded = Number(taxModel.deductions.d80c || 0) + Number(taxModel.deductions.d80d || 0) + Number(taxModel.deductions.d80ccd1b || 0) + Number(taxModel.deductions.d80tta || 0);
            const taxable = Math.max(0, gross - ded);
            
            const grossEl = document.getElementById('grossTotal');
            const dedEl = document.getElementById('totalDeductions');
            const taxableEl = document.getElementById('taxableIncome');
            
            if (grossEl) grossEl.textContent = fmt(gross);
            if (dedEl) dedEl.textContent = fmt(ded);
            if (taxableEl) taxableEl.textContent = fmt(taxable);
            
            // Recompute regimes
            computeRegimes(taxable);
        }
        
        // HRA Calculation
        function calcHRA({basic, da, hraReceived, rentPaid, commission, metro}) {
            const salary = Number(basic || 0) + Number(da || 0) + Number(commission || 0);
            const percent = metro ? 0.5 : 0.4;
            const ex1 = Number(hraReceived || 0);
            const ex2 = percent * salary;
            const ex3 = Number(rentPaid || 0) - 0.1 * salary;
            const exemption = Math.max(0, Math.min(ex1, ex2, ex3));
            const taxableHRA = Math.max(0, Number(hraReceived || 0) - exemption);
            return { exemption, taxableHRA };
        }
        
        function renderHRA() {
            const hi = taxModel.hraInput;
            const basicEl = document.getElementById('basic');
            const daEl = document.getElementById('da');
            const hraReceivedEl = document.getElementById('hraReceived');
            const rentPaidEl = document.getElementById('rentPaid');
            const commissionEl = document.getElementById('commission');
            const metroEl = document.getElementById('metro');
            
            if (basicEl) basicEl.value = hi.basic;
            if (daEl) daEl.value = hi.da;
            if (hraReceivedEl) hraReceivedEl.value = hi.hraReceived;
            if (rentPaidEl) rentPaidEl.value = hi.rentPaid;
            if (commissionEl) commissionEl.value = hi.commission;
            if (metroEl) metroEl.checked = !!hi.metro;
            
            const { exemption } = calcHRA(hi);
            const maxHRAEl = document.getElementById('maxHRA');
            const curHRAEl = document.getElementById('curHRA');
            const hraDeltaEl = document.getElementById('hraDelta');
            
            if (maxHRAEl) maxHRAEl.textContent = fmt(exemption);
            if (curHRAEl) curHRAEl.textContent = fmt(hi.hraReceived);
            
            const delta = Math.max(0, exemption - hi.hraReceived);
            if (hraDeltaEl) {
                hraDeltaEl.textContent = fmt(delta);
                hraDeltaEl.className = 'stat-value delta ' + (delta > 0 ? 'ok' : 'warn');
            }
        }
        
        // Simplified tax calculations (illustrative)
        function oldRegimeTax(taxable) {
            let tax = 0;
            const slabs = [
                { upto: 250000, rate: 0 },
                { upto: 500000, rate: 0.05 },
                { upto: 1000000, rate: 0.20 },
                { upto: Infinity, rate: 0.30 }
            ];
            let prev = 0;
            for (const s of slabs) {
                const amt = Math.max(0, Math.min(taxable, s.upto) - prev);
                tax += amt * s.rate;
                prev = s.upto;
                if (s.upto === Infinity) break;
            }
            return Math.round(tax * 1.04); // add 4% cess approx
        }
        
        function newRegimeTax(taxable) {
            const slabs = [
                { upto: 300000, rate: 0 },
                { upto: 700000, rate: 0.05 },
                { upto: 1000000, rate: 0.10 },
                { upto: 1200000, rate: 0.15 },
                { upto: 1500000, rate: 0.20 },
                { upto: Infinity, rate: 0.30 },
            ];
            let tax = 0, prev = 0;
            for (const s of slabs) {
                const amt = Math.max(0, Math.min(taxable, s.upto) - prev);
                tax += amt * s.rate;
                prev = s.upto;
                if (s.upto === Infinity) break;
            }
            return Math.round(tax * 1.04);
        }
        
        function computeRegimes(taxable) {
            const oldT = oldRegimeTax(taxable);
            const newT = newRegimeTax(taxable);
            
            const oldTaxEl = document.getElementById('oldTax');
            const newTaxEl = document.getElementById('newTax');
            const saveWithEl = document.getElementById('saveWith');
            const saveAmtEl = document.getElementById('saveAmt');
            
            if (oldTaxEl) oldTaxEl.textContent = fmt(oldT);
            if (newTaxEl) newTaxEl.textContent = fmt(newT);
            
            const saveWith = oldT < newT ? 'Old Regime' : (newT < oldT ? 'New Regime' : 'Either');
            const saveAmt = Math.abs(oldT - newT);
            
            if (saveWithEl) saveWithEl.textContent = saveWith;
            if (saveAmtEl) saveAmtEl.textContent = fmt(saveAmt);
        }
        
        // Guided Filing Journey Implementation
        const stepList = [
            {
                id: 'prep', 
                title: 'Preparation Checklist', 
                portalPath: 'Before Portal',
                description: 'Collect proofs and ensure figures match AIS/TIS & Form 26AS.',
                inputs: ['Form 16', 'Form 26AS', 'AIS/TIS', 'Bank Interest Cert', 'Rent Receipts', 'Investment Proofs (80C/80D/NPS)'],
                tips: ['Cross-check TDS in Form 26AS vs Form 16', 'Have landlord PAN if claiming HRA > ₹1 lakh/year']
            },
            {
                id: 'login', 
                title: 'Login & Start Filing', 
                portalPath: 'e-File → Income Tax Return',
                description: 'Login on the Income Tax portal and choose File ITR for AY 2025–26.',
                inputs: ['PAN + Password', 'Select AY 2025–26', 'Choose ITR-1/ITR-2 as applicable'],
                tips: ['If salary + one house property + no capital gains → ITR-1. Otherwise ITR-2.']
            },
            {
                id: 'income', 
                title: 'Enter Income Details', 
                portalPath: 'Income Details',
                description: 'Transcribe values exactly as shown in your breakdown.',
                inputs: ['Salary: Basic, HRA (taxable portion), Allowances', 'Interest Income', 'Capital Gains (LTCG/STCG)'],
                tips: ['Use our HRA calculator result for "Exempt" vs "Taxable" HRA.']
            },
            {
                id: 'deductions', 
                title: 'Enter Deductions', 
                portalPath: 'Deductions → 80C/80D etc.',
                description: 'Fill eligible deductions and upload proofs when prompted.',
                inputs: ['80C (PF/ELSS/LIC)', '80D (Health Insurance)', '80CCD(1B) (NPS)', '80TTA/TTB'],
                tips: ['Keep receipt numbers and dates handy for insurance/NPS.']
            },
            {
                id: 'review', 
                title: 'Review, Compute & E-Verify', 
                portalPath: 'Preview → Submit → e-Verify',
                description: 'Review tax computation, pay any dues/refund, then e-verify to complete filing.',
                inputs: ['Payment/Refund details', 'Preferred e-Verification (OTP/EVC/Net Banking/DSC)'],
                tips: ['You must e-verify to finish filing. Save ITR-V acknowledgement.']
            }
        ];
        
        function renderFilingSteps(activeId = stepList[0].id) {
            const stepsNav = document.getElementById('filing-steps');
            const stepContent = document.getElementById('step-content');
            
            if (!stepsNav || !stepContent) return;
            
            stepsNav.innerHTML = stepList.map(s => 
                `<button class="stepbtn" data-id="${s.id}" aria-current="${s.id === activeId ? 'step' : 'false'}">${s.title}</button>`
            ).join('');
            
            const s = stepList.find(x => x.id === activeId);
            stepContent.innerHTML = `
                <div style="color:#475569; font-size:13px; margin-bottom:8px;">${s.portalPath}</div>
                <h3 style="margin:6px 0 8px; color:#0f172a;">${s.title}</h3>
                <p style="color:#475569; margin-bottom:16px;">${s.description}</p>
                <h4 style="margin:10px 0 6px; color:#374151;">What you need here</h4>
                <ul style="margin:0 0 16px 0; padding-left:20px;">${s.inputs.map(i => `<li style="margin-bottom:4px;">• ${i}</li>`).join('')}</ul>
                <div style="background:#ecfeff; border:1px dashed #67e8f9; padding:8px 10px; border-radius:10px; font-size:13px; margin-bottom:16px;">
                    💡 ${s.tips.join(' • ')}
                </div>
                <div style="display:flex; gap:8px;">
                    <a href="https://www.incometax.gov.in" target="_blank" rel="noopener" style="text-decoration:none;">
                        <button class="btn btn-primary">Open Portal</button>
                    </a>
                    <button class="btn btn-ghost" onclick="markStepDone('${s.id}')">Mark Step Done</button>
                </div>
            `;
            
            // Add event listeners for step navigation
            stepsNav.addEventListener('click', (e) => {
                const btn = e.target.closest('.stepbtn');
                if (!btn) return;
                renderFilingSteps(btn.dataset.id);
            });
        }
        
        function renderPreChecklist() {
            const precheck = document.getElementById('pre-checklist');
            if (!precheck) return;
            
            precheck.innerHTML = `
                <div class="check">
                    <input type="checkbox" id="chk_docs" style="margin-right:8px;" />
                    <label for="chk_docs" style="font-size:13px;">I have Form 16 / 26AS / AIS / proofs ready</label>
                </div>
                <div class="check">
                    <input type="checkbox" id="chk_calc" style="margin-right:8px;" />
                    <label for="chk_calc" style="font-size:13px;">I reviewed taxable vs exempt HRA</label>
                </div>
                <div class="check">
                    <input type="checkbox" id="chk_compare" style="margin-right:8px;" />
                    <label for="chk_compare" style="font-size:13px;">I compared Old vs New regime</label>
                </div>
            `;
        }
        
        function markStepDone(stepId) {
            // Find the step button and mark it as completed
            const stepBtn = document.querySelector(`[data-id="${stepId}"]`);
            if (stepBtn) {
                stepBtn.style.background = '#e0e7ff';
                stepBtn.style.borderColor = '#c7d2fe';
                stepBtn.innerHTML += ' ✓';
            }
            
            // Move to next step if available
            const currentIndex = stepList.findIndex(s => s.id === stepId);
            if (currentIndex < stepList.length - 1) {
                const nextStep = stepList[currentIndex + 1];
                setTimeout(() => renderFilingSteps(nextStep.id), 500);
            } else {
                // All steps completed
                alert('🎉 Congratulations! You have completed all filing steps. Now file your ITR on the portal.');
            }
        }

        // Initialize the new analysis interface with real data
        function initializeAnalysisInterface(results) {
            // Update the model with actual data
            if (results) {
                taxModel.incomes = [
                    { category: 'Salary', sub: 'Basic', amount: Math.round((results.salary_income || 0) * 0.8) },
                    { category: 'Salary', sub: 'HRA', amount: 0 }, // Will be calculated from HRA data
                    { category: 'Salary', sub: 'Special Allowances', amount: Math.round((results.salary_income || 0) * 0.2) },
                    { category: 'Interest', sub: 'Savings Interest', amount: results.interest_income || 0 },
                    { category: 'Capital Gains', sub: 'LTCG (Equity)', amount: results.capital_gains || 0 },
                    { category: 'Other', sub: 'Freelance', amount: 0 },
                ];
                
                // Update deductions based on actual data
                taxModel.deductions.d80c = results.total_deductions || 120000;
            }
            
            // Render all interface components
            renderIncomeInterface();
            renderHRA();
            
            // Add event listeners for real-time updates
            setupEventListeners();
            renderFilingSteps();
            renderPreChecklist();
        }
        
        function setupEventListeners() {
            // Income table editing
            const tableBody = document.getElementById('income-tbody');
            if (tableBody) {
                tableBody.addEventListener('input', (e) => {
                    if (e.target && e.target.matches('input[type="number"]')) {
                        const idx = Number(e.target.dataset.row);
                        taxModel.incomes[idx].amount = Number(e.target.value || 0);
                        renderIncomeInterface();
                    }
                });
            }
            
            // HRA form inputs
            const hraInputs = ['basic', 'da', 'hraReceived', 'rentPaid', 'commission'];
            hraInputs.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', () => {
                        taxModel.hraInput[id] = Number(el.value || 0);
                        renderHRA();
                    });
                }
            });
            
            const metroEl = document.getElementById('metro');
            if (metroEl) {
                metroEl.addEventListener('change', () => {
                    taxModel.hraInput.metro = metroEl.checked;
                    renderHRA();
                });
            }
            
            // Deduction inputs
            const deductionInputs = ['d80c', 'd80d', 'd80ccd1b', 'd80tta'];
            deductionInputs.forEach(id => {
                const el = document.getElementById(id);
                if (el) {
                    el.addEventListener('input', () => {
                        taxModel.deductions[id] = Number(el.value || 0);
                        renderIncomeInterface();
                    });
                }
            });
            
            // HRA buttons
            const applyHRABtn = document.getElementById('applyHRA');
            if (applyHRABtn) {
                applyHRABtn.addEventListener('click', () => {
                    const { taxableHRA, exemption } = calcHRA(taxModel.hraInput);
                    const idx = taxModel.incomes.findIndex(i => i.category === 'Salary' && i.sub === 'HRA');
                    if (idx >= 0) {
                        taxModel.incomes[idx].amount = taxableHRA;
                    }
                    if (exemption > taxModel.hraInput.hraReceived) {
                        alert('Tip: You could claim more HRA exemption on the portal. Our calc shows ' + fmt(exemption) + '.');
                    }
                    renderIncomeInterface();
                });
            }
            
            const resetHRABtn = document.getElementById('resetHRA');
            if (resetHRABtn) {
                resetHRABtn.addEventListener('click', () => {
                    taxModel.hraInput = { basic: 500000, da: 0, hraReceived: 150000, rentPaid: 180000, commission: 0, metro: true };
                    const idx = taxModel.incomes.findIndex(i => i.category === 'Salary' && i.sub === 'HRA');
                    if (idx >= 0) {
                        taxModel.incomes[idx].amount = taxModel.hraInput.hraReceived;
                    }
                    renderHRA();
                    renderIncomeInterface();
                });
            }
        }

        // Populate analysis results in page 2 (enhanced for new design)
        function populateAnalysisResults(results) {
            // Initialize the new analysis interface
            initializeAnalysisInterface(results);
            
            // Legacy support for old elements (if they exist)
            const totalIncomeMetric = document.getElementById('totalIncomeMetric');
            if (totalIncomeMetric) {
                totalIncomeMetric.textContent = '₹' + Math.round(results.total_income || 0).toLocaleString();
            }
            
            const taxSavingsMetric = document.getElementById('taxSavingsMetric');
            if (taxSavingsMetric) {
                const savings = Math.abs((results.tax_liability_old_regime || 0) - (results.tax_liability_new_regime || 0));
                taxSavingsMetric.textContent = '₹' + Math.round(savings).toLocaleString();
            }
            
            const recommendedRegimeMetric = document.getElementById('recommendedRegimeMetric');
            if (recommendedRegimeMetric) {
                const recommended = results.recommended_regime || 'old';
                recommendedRegimeMetric.textContent = recommended.toUpperCase();
            }
            
            const refundStatusMetric = document.getElementById('refundStatusMetric');
            if (refundStatusMetric) {
                const recommended = results.recommended_regime || 'old';
                const finalTax = recommended === 'old' ? results.tax_liability_old_regime : results.tax_liability_new_regime;
                const refundAmount = (results.tax_paid || 0) - finalTax;
                
                refundStatusMetric.textContent = 
                    refundAmount > 0 ? '₹' + Math.round(refundAmount).toLocaleString() + ' Refund' : 
                    '₹' + Math.round(Math.abs(refundAmount)).toLocaleString() + ' Additional';
            }
            
            // Legacy chart updates
            const totalIncome = results.total_income || 1;
            const salaryPercent = ((results.salary_income || 0) / totalIncome * 100);
            const otherIncomePercent = (((results.interest_income || 0) + (results.capital_gains || 0)) / totalIncome * 100);
            
            const salaryBar = document.getElementById('salaryBar');
            const interestBar = document.getElementById('interestBar');
            
            if (salaryBar) salaryBar.style.width = salaryPercent + '%';
            if (interestBar) interestBar.style.width = otherIncomePercent + '%';
            
            const salaryAmount = document.getElementById('salaryAmount');
            const interestAmount = document.getElementById('interestAmount');
            
            if (salaryAmount) salaryAmount.textContent = Math.round(results.salary_income || 0).toLocaleString();
            if (interestAmount) interestAmount.textContent = Math.round((results.interest_income || 0) + (results.capital_gains || 0)).toLocaleString();
            
            // Legacy regime comparison elements
            const oldTaxEl = document.getElementById('oldRegimeTax');
            const newTaxEl = document.getElementById('newRegimeTax');
            const oldTaxLiability = document.getElementById('oldTaxLiability');
            const newTaxLiability = document.getElementById('newTaxLiability');
            const oldDeductionsUsed = document.getElementById('oldDeductionsUsed');
            
            if (oldTaxEl) oldTaxEl.textContent = '₹' + Math.round(results.tax_liability_old_regime || 0).toLocaleString();
            if (newTaxEl) newTaxEl.textContent = '₹' + Math.round(results.tax_liability_new_regime || 0).toLocaleString();
            if (oldTaxLiability) oldTaxLiability.textContent = '₹' + Math.round(results.tax_liability_old_regime || 0).toLocaleString();
            if (newTaxLiability) newTaxLiability.textContent = '₹' + Math.round(results.tax_liability_new_regime || 0).toLocaleString();
            if (oldDeductionsUsed) oldDeductionsUsed.textContent = '₹' + Math.round(results.total_deductions || 0).toLocaleString();
            
            // Legacy HRA Analysis
            if (results.hra_received > 0) {
                const hraAnalysis = document.getElementById('hraAnalysis');
                if (hraAnalysis) hraAnalysis.style.display = 'block';
                
                const hraReceived = document.getElementById('hraReceived');
                const hraBasicHalf = document.getElementById('hraBasicHalf');
                const hraRentMinus10 = document.getElementById('hraRentMinus10');
                const hraExemption = document.getElementById('hraExemption');
                
                if (hraReceived) hraReceived.textContent = '₹' + Math.round(results.hra_received || 0).toLocaleString();
                if (hraBasicHalf) hraBasicHalf.textContent = '₹' + Math.round((results.basic_salary || 0) * 0.5).toLocaleString();
                if (hraRentMinus10) {
                    const rentMinus10 = Math.max(0, (results.rent_paid || 0) - (results.gross_salary || 0) * 0.1);
                    hraRentMinus10.textContent = '₹' + Math.round(rentMinus10).toLocaleString();
                }
                if (hraExemption) hraExemption.textContent = '₹' + Math.round(results.hra_exemption || 0).toLocaleString();
            }
            
            // Legacy detailed income breakdown
            populateDetailedIncomeBreakdown(results);
            
            // Legacy filing guide
            populateFilingGuide(results);
        }
        
        // Guide tab navigation
        function showGuideTab(tabId) {
            // Hide all guide panels
            document.querySelectorAll('.guide-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            
            // Remove active class from all tab buttons
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });
            
            // Show selected panel
            document.getElementById(tabId).classList.add('active');
            
            // Add active class to clicked tab button
            event.target.classList.add('active');
        }
        
        // Toggle breakdown section visibility
        function toggleBreakdownSection(sectionId) {
            const details = document.getElementById(sectionId);
            const toggle = document.getElementById(sectionId.replace('Breakdown', 'Toggle'));
            
            if (details.classList.contains('open')) {
                details.classList.remove('open');
                toggle.classList.remove('rotated');
            } else {
                details.classList.add('open');
                toggle.classList.add('rotated');
            }
        }
        
        // Populate detailed income breakdown data
        function populateDetailedIncomeBreakdown(results) {
            // Calculate breakdown values from available data
            const salaryIncome = results.salary_income || 0;
            const interestIncome = results.interest_income || 0;
            const capitalGains = results.capital_gains || 0;
            const totalIncome = results.total_income || 0;
            
            // For salary breakdown - split into basic and perquisites (80-20 ratio as fallback)
            const basicSalary = Math.round(salaryIncome * 0.8);
            const perquisites = salaryIncome - basicSalary;
            
            // For other income - split interest and divide capital gains if we have dividend data
            const bankInterest = interestIncome;
            const dividendIncome = 0; // This would come from document analysis if available
            const otherTotal = interestIncome + capitalGains;
            
            // Helper function to safely update element text content
            function safeUpdateElement(id, value) {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = Math.round(value).toLocaleString();
                }
            }
            
            // A. Salary Income Section
            safeUpdateElement('totalSalaryIncome', salaryIncome);
            safeUpdateElement('basicSalaryAmount', basicSalary);
            safeUpdateElement('perquisitesAmount', perquisites);
            safeUpdateElement('calculatedSalaryTotal', salaryIncome);
            
            // B. Income from Other Sources Section  
            safeUpdateElement('totalOtherIncome', otherTotal);
            safeUpdateElement('bankInterestAmount', bankInterest);
            safeUpdateElement('dividendIncomeAmount', dividendIncome);
            safeUpdateElement('capitalGainsAmount', capitalGains);
            safeUpdateElement('calculatedOtherTotal', otherTotal);
            
            // C. Gross Total Income Section
            safeUpdateElement('grossTotalIncome', totalIncome);
            safeUpdateElement('grossSalaryComponent', salaryIncome);
            safeUpdateElement('grossOtherComponent', otherTotal);
            safeUpdateElement('calculatedGrossTotal', totalIncome);
        }
        
        // Populate filing guide with user data
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
            document.getElementById('guidePPF').textContent = Math.round(results.ppf_amount || 0).toLocaleString();
            document.getElementById('guideNPS').textContent = Math.round(results.deductions_80ccd1b || 0).toLocaleString();
            document.getElementById('guideHealthInsurance').textContent = Math.round(results.health_insurance || 0).toLocaleString();
            document.getElementById('guideHomeLoanInterest').textContent = Math.round(results.home_loan_interest || 0).toLocaleString();
            
            // Final verification guide
            const recommendedRegime = results.recommended_regime || 'old';
            const finalTax = recommendedRegime === 'old' ? results.tax_liability_old_regime : results.tax_liability_new_regime;
            document.getElementById('guideFinalTax').textContent = Math.round(finalTax || 0).toLocaleString();
            
            const refundAmount = (results.tax_paid || 0) - finalTax;
            document.getElementById('guideFinalStatus').textContent = 
                refundAmount > 0 ? `Refund Expected: ₹${Math.round(refundAmount).toLocaleString()}` : 
                `Additional Payment: ₹${Math.round(Math.abs(refundAmount)).toLocaleString()}`;
        }
        
        // Modal functions
        function openCorrectionModal() {
            document.getElementById('correctionModal').style.display = 'flex';
        }
        
        function closeCorrectionModal() {
            document.getElementById('correctionModal').style.display = 'none';
        }
        
        // Other existing functions
        function downloadReport() {
            fetch('/api/download_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(window.analysisResults || {})
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
            showPage('page1');
            document.getElementById('fileInput').value = '';
            document.getElementById('processDocumentsBtn').style.display = 'none';
        }
        
        // Show process button when files are selected and override original handlers
        document.addEventListener('DOMContentLoaded', function() {
            const fileInput = document.getElementById('fileInput');
            if (fileInput) {
                // Remove existing event listeners by cloning the element
                const newFileInput = fileInput.cloneNode(true);
                fileInput.parentNode.replaceChild(newFileInput, fileInput);
                
                // Add our new event listener
                newFileInput.addEventListener('change', function(e) {
                    const processBtn = document.getElementById('processDocumentsBtn');
                    const processBtnContainer = document.getElementById('processButtonContainer');
                    
                    if (e.target.files.length > 0) {
                        // Show process button container
                        if (processBtnContainer) {
                            processBtnContainer.style.display = 'block';
                        }
                        // Show file list
                        updateFileList(Array.from(e.target.files));
                        // Stop any automatic processing
                        const processingIndicator = document.getElementById('processingIndicator');
                        if (processingIndicator) {
                            processingIndicator.style.display = 'none';
                        }
                    } else {
                        if (processBtnContainer) {
                            processBtnContainer.style.display = 'none';
                        }
                    }
                });
            }
            
            // Override addFilesToSelection if it exists
            window.addFilesToSelection = function(files) {
                updateFileList(files);
                const processBtnContainer = document.getElementById('processButtonContainer');
                if (processBtnContainer && files.length > 0) {
                    processBtnContainer.style.display = 'block';
                }
            };
            
            // Prevent the entire upload section from being clickable
            // Only the upload-zone should be clickable
            const uploadSection = document.querySelector('.upload-section');
            if (uploadSection) {
                uploadSection.style.cursor = 'default';
            }
            
            // Override the triggerFileUpload function with debugging
            window.originalTriggerFileUpload = window.triggerFileUpload;
            window.triggerFileUpload = function(event) {
                console.log('triggerFileUpload called with event:', event);
                console.log('Event target:', event ? event.target : 'no target');
                
                // Allow clicks from upload-zone or upload-button-area
                if (event && event.target) {
                    const uploadZone = document.querySelector('.upload-zone');
                    const uploadButtonArea = document.querySelector('.upload-button-area');
                    const isInUploadZone = uploadZone && uploadZone.contains(event.target);
                    const isInUploadButton = uploadButtonArea && uploadButtonArea.contains(event.target);
                    
                    console.log('Upload zone found:', !!uploadZone);
                    console.log('Upload button area found:', !!uploadButtonArea);
                    console.log('Is in upload zone:', isInUploadZone);
                    console.log('Is in upload button:', isInUploadButton);
                    
                    if (!isInUploadZone && !isInUploadButton) {
                        console.log('Click rejected - not in allowed areas');
                        return; // Don't trigger if clicked outside allowed areas
                    }
                }
                
                console.log('Proceeding with file input trigger');
                const fileInput = document.getElementById('fileInput');
                console.log('File input element:', fileInput);
                
                if (window.originalTriggerFileUpload) {
                    console.log('Using original triggerFileUpload function');
                    window.originalTriggerFileUpload(event);
                } else {
                    console.log('Using direct file input click');
                    if (fileInput) {
                        fileInput.click();
                    } else {
                        console.error('File input element not found!');
                    }
                }
            };
            
            // Override simulateProcessing to do nothing automatically
            window.simulateProcessing = function() {
                // Do nothing - processing should only happen when button is clicked
            };
            
            // Add direct event listeners to upload button area with multiple approaches
            console.log('Setting up file upload button listeners...');
            
            // Method 1: By ID
            const uploadButtonById = document.getElementById('uploadButtonArea');
            if (uploadButtonById) {
                console.log('Found upload button by ID, adding listener');
                uploadButtonById.addEventListener('click', function(e) {
                    console.log('CLICK DETECTED on upload button (by ID)');
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const fileInput = document.getElementById('fileInput');
                    if (fileInput) {
                        console.log('File input found, triggering click');
                        fileInput.click();
                    } else {
                        console.error('File input not found!');
                    }
                });
            }
            
            // Method 2: By class (backup)
            const uploadButtonByClass = document.querySelector('.upload-button-area');
            if (uploadButtonByClass && uploadButtonByClass !== uploadButtonById) {
                console.log('Found additional upload button by class, adding listener');
                uploadButtonByClass.addEventListener('click', function(e) {
                    console.log('CLICK DETECTED on upload button (by class)');
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const fileInput = document.getElementById('fileInput');
                    if (fileInput) {
                        console.log('File input found, triggering click');
                        fileInput.click();
                    } else {
                        console.error('File input not found!');
                    }
                });
            }
            
            // Method 3: Test if button is actually clickable
            setTimeout(() => {
                const testButton = document.getElementById('uploadButtonArea');
                if (testButton) {
                    console.log('Upload button element:', testButton);
                    console.log('Button computed style:', window.getComputedStyle(testButton));
                    console.log('Button visibility:', testButton.offsetWidth > 0 && testButton.offsetHeight > 0);
                } else {
                    console.error('Upload button not found in DOM after timeout');
                }
            }, 1000);
        });
        
        // Update file list display with animations
        function updateFileList(files) {
            const fileListContainer = document.getElementById('fileListContainer');
            const selectedFilesList = document.getElementById('selectedFilesList');
            
            if (files.length > 0) {
                fileListContainer.style.display = 'block';
                selectedFilesList.innerHTML = '';
                
                // Show upload animation
                showUploadAnimation();
                
                files.forEach((file, index) => {
                    setTimeout(() => {
                        const fileItem = document.createElement('div');
                        fileItem.className = 'file-item uploading';
                        fileItem.style.animationDelay = `${index * 0.1}s`;
                        
                        // Get file type icon and color
                        let fileIcon = '📄';
                        let statusColor = '#3b82f6';
                        const ext = file.name.split('.').pop().toLowerCase();
                        
                        if (ext === 'pdf') {
                            fileIcon = '📃';
                            statusColor = '#dc2626';
                        } else if (ext === 'xlsx' || ext === 'xls') {
                            fileIcon = '📈';
                            statusColor = '#059669';
                        } else if (ext === 'csv') {
                            fileIcon = '📋';
                            statusColor = '#d97706';
                        } else if (['jpg', 'jpeg', 'png'].includes(ext)) {
                            fileIcon = '🖼️';
                            statusColor = '#7c3aed';
                        } else if (['doc', 'docx'].includes(ext)) {
                            fileIcon = '📄';
                            statusColor = '#1d4ed8';
                        }
                        
                        // Split filename and extension for proper ellipsis handling
                        const fileName = file.name;
                        const lastDotIndex = fileName.lastIndexOf('.');
                        const nameWithoutExt = lastDotIndex > 0 ? fileName.substring(0, lastDotIndex) : fileName;
                        const extension = lastDotIndex > 0 ? fileName.substring(lastDotIndex) : '';
                        
                        fileItem.innerHTML = `
                            <span class="file-icon">${fileIcon}</span>
                            <div class="file-content">
                                <div class="file-name-container">
                                    <span class="file-name" title="${fileName}">${nameWithoutExt}</span>
                                    <span class="file-extension">${extension}</span>
                                </div>
                                <div class="file-details">
                                    <span class="file-size">${(file.size / 1024 / 1024).toFixed(2)} MB</span>
                                    <span class="file-status uploading" style="color: ${statusColor}">Uploading...</span>
                                </div>
                                <div class="upload-progress">
                                    <div class="upload-progress-bar"></div>
                                </div>
                            </div>
                        `;
                        
                        selectedFilesList.appendChild(fileItem);
                        
                        // Simulate upload progress
                        const progressBar = fileItem.querySelector('.upload-progress-bar');
                        const statusElement = fileItem.querySelector('.file-status');
                        
                        let progress = 0;
                        const progressInterval = setInterval(() => {
                            progress += Math.random() * 30;
                            if (progress >= 100) {
                                progress = 100;
                                progressBar.style.width = '100%';
                                statusElement.textContent = 'Uploaded ✓';
                                statusElement.className = 'file-status success';
                                statusElement.style.color = '#10b981';
                                fileItem.classList.remove('uploading');
                                clearInterval(progressInterval);
                            } else {
                                progressBar.style.width = progress + '%';
                            }
                        }, 150);
                        
                    }, index * 150);
                });
                
                // Hide upload animation after files are processed
                setTimeout(() => {
                    hideUploadAnimation();
                }, (files.length * 150) + 2000);
                
            } else {
                fileListContainer.style.display = 'none';
            }
        }
        
        // Upload animation functions
        function showUploadAnimation() {
            let uploadAnimation = document.getElementById('uploadAnimation');
            if (!uploadAnimation) {
                uploadAnimation = document.createElement('div');
                uploadAnimation.className = 'upload-animation';
                uploadAnimation.id = 'uploadAnimation';
                uploadAnimation.innerHTML = `
                    <div class="upload-spinner"></div>
                    <div class="upload-text">Preparing Your Documents</div>
                    <div class="upload-subtext">Please wait while we process your files...</div>
                `;
                document.body.appendChild(uploadAnimation);
            }
            uploadAnimation.style.display = 'block';
        }
        
        function hideUploadAnimation() {
            const uploadAnimation = document.getElementById('uploadAnimation');
            if (uploadAnimation) {
                uploadAnimation.style.opacity = '0';
                uploadAnimation.style.transform = 'translate(-50%, -50%) scale(0.8)';
                setTimeout(() => {
                    uploadAnimation.style.display = 'none';
                    uploadAnimation.style.opacity = '1';
                    uploadAnimation.style.transform = 'translate(-50%, -50%) scale(1)';
                }, 300);
            }
        }

        // Initialize reference design functions for page 2
        function initPage2() {
            setTimeout(() => {
                console.log('Page 2 initialized with reference design styling and functionality');
                // Trigger reference design population if results exist
                const existingResults = window.lastAnalysisResults;
                if (existingResults) {
                    populateReferenceDesignElements(existingResults);
                }
            }, 100);
        }

        // ========== NEW REFERENCE DESIGN FUNCTIONS ==========
        function populateReferenceDesignElements(results) {
            console.log('populateReferenceDesignElements called with:', results);
            
            // Store results globally for page switches
            window.lastAnalysisResults = results;
            
            // Create a working model from the analysis results
            const workingModel = {
                incomes: [
                    { category: 'Salary', sub: 'Basic', amount: Math.round((results.salary_income || 500000) * 0.6) },
                    { category: 'Salary', sub: 'HRA', amount: Math.round((results.salary_income || 500000) * 0.3) },
                    { category: 'Salary', sub: 'Special Allowances', amount: Math.round((results.salary_income || 500000) * 0.1) },
                    { category: 'Interest', sub: 'Savings Interest', amount: results.interest_income || 20000 },
                    { category: 'Capital Gains', sub: 'LTCG (Equity)', amount: results.capital_gains || 50000 },
                    { category: 'Other', sub: 'Freelance', amount: 0 },
                ],
                deductions: { 
                    d80c: Math.min(results.total_deductions || 120000, 150000), 
                    d80d: 25000, 
                    d80ccd1b: 0, 
                    d80tta: 0 
                },
                hraInput: { 
                    basic: Math.round((results.salary_income || 500000) * 0.6), 
                    da: 0, 
                    hraReceived: Math.round((results.salary_income || 500000) * 0.3), 
                    rentPaid: Math.round((results.salary_income || 500000) * 0.36), 
                    commission: 0, 
                    metro: true 
                }
            };

            // Populate income breakdown bars with detailed breakdowns
            const barsEl = document.getElementById('bars');
            if (barsEl) {
                const total = workingModel.incomes.reduce((a,b) => a + (Number(b.amount)||0), 0);
                const cats = [...new Set(workingModel.incomes.map(i => i.category))];
                const totals = cats.map(c => workingModel.incomes.filter(i => i.category===c).reduce((a,b) => a+Number(b.amount||0), 0));
                const max = Math.max(...totals, 1);
                
                barsEl.innerHTML = cats.map((c,idx) => {
                    const pct = Math.round((totals[idx]/max)*100);
                    const categoryItems = workingModel.incomes.filter(i => i.category === c);
                    const breakdown = categoryItems.map(item => `${item.sub}: ${fmt(item.amount)}`).join('<br>');
                    
                    return `
                        <div style="margin-bottom:16px;">
                            <div class="row" style="justify-content:space-between; margin-bottom:4px">
                                <strong>${c}</strong>
                                <span class="subtle">${fmt(totals[idx])}</span>
                            </div>
                            <div class="bar"><span style="width:${pct}%"></span><label>${pct}%</label></div>
                            <div style="font-size:12px; color:var(--muted); margin-top:4px; padding-left:8px;">
                                ${breakdown}
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // Populate income table
            const tableBody = document.querySelector('#income-table tbody');
            if (tableBody) {
                tableBody.innerHTML = workingModel.incomes.map((r,idx) => `
                    <tr>
                        <td>${r.category}</td>
                        <td>${r.sub}</td>
                        <td class="amount"><input type="number" min="0" value="${r.amount}" style="width:120px; text-align:right; border:1px solid var(--soft); border-radius:8px; padding:6px 8px" data-row="${idx}" /></td>
                    </tr>
                `).join('');

                // Add event listener for table edits
                tableBody.addEventListener('input', (e) => {
                    if(e.target && e.target.matches('input[type="number"]')){
                        const idx = Number(e.target.dataset.row);
                        workingModel.incomes[idx].amount = Number(e.target.value||0);
                        updateCalculations(workingModel);
                    }
                });
            }

            // Calculate and populate statistics
            updateCalculations(workingModel);

            // Populate HRA calculator
            populateHRACalculatorNew(workingModel.hraInput);

            // Populate deduction inputs
            Object.keys(workingModel.deductions).forEach(key => {
                const el = document.getElementById(key);
                if (el) {
                    el.value = workingModel.deductions[key];
                    el.addEventListener('input', (e) => {
                        workingModel.deductions[key] = Number(e.target.value||0);
                        updateCalculations(workingModel);
                    });
                }
            });

            // Initialize guided filing journey with actual data
            initializeGuidedJourneyNew(results, workingModel);

            console.log('Reference design elements populated successfully');
        }

        function updateCalculations(workingModel) {
            const total = workingModel.incomes.reduce((a,b) => a + (Number(b.amount)||0), 0);
            const deductions = Object.values(workingModel.deductions).reduce((a,b) => a + Number(b||0), 0);
            const standardDeduction = 50000; // Standard deduction for both regimes
            const taxableOld = Math.max(0, total - deductions - standardDeduction);
            const taxableNew = Math.max(0, total - standardDeduction); // New regime has no other deductions

            const grossEl = document.getElementById('grossTotal');
            if (grossEl) grossEl.textContent = fmt(total);

            const deductionsEl = document.getElementById('totalDeductions');
            if (deductionsEl) deductionsEl.textContent = fmt(deductions + standardDeduction);

            const taxableEl = document.getElementById('taxableIncome');
            if (taxableEl) taxableEl.textContent = fmt(taxableOld);

            // Calculate detailed regime comparison
            const oldTaxCalc = calculateDetailedTax(taxableOld, 'old');
            const newTaxCalc = calculateDetailedTax(taxableNew, 'new');
            
            const oldTaxEl = document.getElementById('oldTax');
            if (oldTaxEl) {
                oldTaxEl.innerHTML = `
                    <div style="font-size:18px; font-weight:700;">${fmt(oldTaxCalc.totalTax)}</div>
                    <div style="font-size:12px; color:var(--muted); margin-top:4px;">
                        Base Tax: ${fmt(oldTaxCalc.baseTax)}<br>
                        ${oldTaxCalc.surcharge > 0 ? `Surcharge: ${fmt(oldTaxCalc.surcharge)}<br>` : ''}
                        Cess (4%): ${fmt(oldTaxCalc.cess)}<br>
                        Taxable: ${fmt(taxableOld)}
                    </div>
                `;
            }
            
            const newTaxEl = document.getElementById('newTax');
            if (newTaxEl) {
                newTaxEl.innerHTML = `
                    <div style="font-size:18px; font-weight:700;">${fmt(newTaxCalc.totalTax)}</div>
                    <div style="font-size:12px; color:var(--muted); margin-top:4px;">
                        Base Tax: ${fmt(newTaxCalc.baseTax)}<br>
                        ${newTaxCalc.surcharge > 0 ? `Surcharge: ${fmt(newTaxCalc.surcharge)}<br>` : ''}
                        Cess (4%): ${fmt(newTaxCalc.cess)}<br>
                        Taxable: ${fmt(taxableNew)}
                    </div>
                `;
            }
            
            const saveWith = oldTaxCalc.totalTax < newTaxCalc.totalTax ? 'Old Regime' : (newTaxCalc.totalTax < oldTaxCalc.totalTax ? 'New Regime' : 'Either');
            const saveAmt = Math.abs(oldTaxCalc.totalTax - newTaxCalc.totalTax);
            
            const saveWithEl = document.getElementById('saveWith');
            if (saveWithEl) saveWithEl.textContent = saveWith;
            
            const saveAmtEl = document.getElementById('saveAmt');
            if (saveAmtEl) saveAmtEl.textContent = fmt(saveAmt);
        }

        function calculateDetailedTax(taxableIncome, regime) {
            let baseTax = 0;
            let slabs = [];

            if (regime === 'old') {
                slabs = [
                    { upto: 250000, rate: 0 },
                    { upto: 500000, rate: 0.05 },
                    { upto: 1000000, rate: 0.20 },
                    { upto: Infinity, rate: 0.30 }
                ];
            } else {
                slabs = [
                    { upto: 300000, rate: 0 },
                    { upto: 700000, rate: 0.05 },
                    { upto: 1000000, rate: 0.10 },
                    { upto: 1200000, rate: 0.15 },
                    { upto: 1500000, rate: 0.20 },
                    { upto: Infinity, rate: 0.30 }
                ];
            }

            let prev = 0;
            for (const slab of slabs) {
                const amt = Math.max(0, Math.min(taxableIncome, slab.upto) - prev);
                baseTax += amt * slab.rate;
                prev = slab.upto;
                if (slab.upto === Infinity) break;
            }

            // Calculate surcharge
            let surcharge = 0;
            if (taxableIncome > 5000000) {
                surcharge = baseTax * 0.10; // 10% for income above 50 lakhs
            }

            // Calculate cess (4% of tax + surcharge)
            const cess = (baseTax + surcharge) * 0.04;
            const totalTax = Math.round(baseTax + surcharge + cess);

            return {
                baseTax: Math.round(baseTax),
                surcharge: Math.round(surcharge),
                cess: Math.round(cess),
                totalTax: totalTax
            };
        }

        function populateHRACalculatorNew(hraInput) {
            const inputs = {
                basic: document.getElementById('basic'),
                da: document.getElementById('da'),
                hraReceived: document.getElementById('hraReceived'),
                rentPaid: document.getElementById('rentPaid'),
                rentPerMonth: document.getElementById('rentPerMonth'),
                commission: document.getElementById('commission'),
                metro: document.getElementById('metro'),
            };

            if (inputs.basic) inputs.basic.value = hraInput.basic;
            if (inputs.da) inputs.da.value = hraInput.da;
            if (inputs.hraReceived) inputs.hraReceived.value = hraInput.hraReceived;
            if (inputs.rentPaid) inputs.rentPaid.value = hraInput.rentPaid;
            if (inputs.rentPerMonth) inputs.rentPerMonth.value = Math.round((hraInput.rentPaid || 180000) / 12);
            if (inputs.commission) inputs.commission.value = hraInput.commission;
            if (inputs.metro) inputs.metro.checked = hraInput.metro;

            // Add auto-calculation functionality
            const autoCalculateBtn = document.getElementById('autoCalculateRent');
            if (autoCalculateBtn && !autoCalculateBtn.dataset.listenerAdded) {
                autoCalculateBtn.dataset.listenerAdded = 'true';
                autoCalculateBtn.addEventListener('click', () => {
                    const monthlyRent = Number(inputs.rentPerMonth.value || 0);
                    const annualRent = monthlyRent * 12;
                    inputs.rentPaid.value = annualRent;
                    hraInput.rentPaid = annualRent;
                    populateHRACalculatorNew(hraInput);
                    alert(`✅ Annual rent calculated: ₹${annualRent.toLocaleString()} (₹${monthlyRent.toLocaleString()} × 12 months)`);
                });
            }

            // Auto-calculate when monthly rent changes
            if (inputs.rentPerMonth && !inputs.rentPerMonth.dataset.listenerAdded) {
                inputs.rentPerMonth.dataset.listenerAdded = 'true';
                inputs.rentPerMonth.addEventListener('input', () => {
                    const monthlyRent = Number(inputs.rentPerMonth.value || 0);
                    if (monthlyRent > 0) {
                        const annualRent = monthlyRent * 12;
                        inputs.rentPaid.value = annualRent;
                        hraInput.rentPaid = annualRent;
                    }
                });
            }

            // Calculate HRA exemption
            const { exemption } = calcHRA(hraInput);
            const maxHRAEl = document.getElementById('maxHRA');
            if (maxHRAEl) maxHRAEl.textContent = fmt(exemption);
            
            const curHRAEl = document.getElementById('curHRA');
            if (curHRAEl) curHRAEl.textContent = fmt(hraInput.hraReceived);
            
            const delta = Math.max(0, exemption - hraInput.hraReceived);
            const hraDeltaEl = document.getElementById('hraDelta');
            if (hraDeltaEl) {
                hraDeltaEl.textContent = fmt(delta);
                hraDeltaEl.className = 'big delta ' + (delta > 0 ? 'ok' : 'warn');
            }
        }

        function initializeGuidedJourneyNew(results, workingModel) {
            // Initialize guided filing steps with actual user data
            const stepsNav = document.getElementById('steps');
            const stepContent = document.getElementById('stepcontent');
            
            if (!stepsNav || !stepContent) return;
            
            // Render steps navigation
            stepsNav.innerHTML = stepList.map(s => `<button class="stepbtn" data-id="${s.id}" aria-current="${s.id===stepList[0].id?'step':'false'}">${s.title}</button>`).join('');
            
            // Render first step content with user data
            renderStepContentNew(stepList[0], results, workingModel);
            
            // Add event listeners for step navigation
            if (!stepsNav.dataset.listenerAdded) {
                stepsNav.dataset.listenerAdded = 'true';
                stepsNav.addEventListener('click', (e) => {
                    const btn = e.target.closest('.stepbtn');
                    if (!btn) return;
                    
                    const step = stepList.find(s => s.id === btn.dataset.id);
                    if (step) {
                        // Update active step
                        stepsNav.querySelectorAll('.stepbtn').forEach(b => b.setAttribute('aria-current', 'false'));
                        btn.setAttribute('aria-current', 'step');
                        
                        // Render step content with user data
                        renderStepContentNew(step, results, workingModel);
                    }
                });
            }
            
            // Initialize pre-check list
            renderPrecheckListNew();
        }

        function renderStepContentNew(step, results, workingModel) {
            const stepContent = document.getElementById('stepcontent');
            if (!stepContent) return;
            
            let customContent = '';
            
            // Customize content based on step and user data
            if (step.id === 'prep') {
                customContent = `
                    <h4 style="margin:10px 0 6px;">📋 Your Documents Required</h4>
                    <ul>
                        <li><strong>Form 16</strong> (showing salary of ₹${fmt(results.salary_income || 500000)})</li>
                        <li><strong>Form 26AS</strong> (TDS: ₹${fmt(results.tax_paid || 0)})</li>
                        <li><strong>AIS/TIS</strong> verification from portal</li>
                        <li><strong>Bank Interest Certificate</strong> (₹${fmt(results.interest_income || 20000)})</li>
                        <li><strong>Rent Receipts</strong> (for HRA of ₹${fmt(workingModel?.hraInput?.hraReceived || 150000)})</li>
                        <li><strong>Investment Proofs</strong> (80C: ₹${fmt(results.total_deductions || 120000)})</li>
                    </ul>
                `;
            } else if (step.id === 'income') {
                const total = workingModel?.incomes?.reduce((a,b) => a + (Number(b.amount)||0), 0) || 0;
                customContent = `
                    <h4 style="margin:10px 0 6px;">💰 Your Income to Enter on Portal</h4>
                    <div style="background:#f0f9ff; border:1px solid #0ea5e9; border-radius:8px; padding:12px; margin:8px 0;">
                        <div style="font-weight:600; color:#0369a1; margin-bottom:8px;">Copy these exact amounts:</div>
                        <ul style="margin:0;">
                            <li><strong>Salary Income:</strong> ₹${fmt(results.salary_income || 500000)}</li>
                            <li><strong>Interest Income:</strong> ₹${fmt(results.interest_income || 20000)}</li>
                            <li><strong>Capital Gains:</strong> ₹${fmt(results.capital_gains || 50000)}</li>
                            <li style="border-top:1px solid #0ea5e9; padding-top:8px; margin-top:8px;"><strong>Total Income: ₹${fmt(total)}</strong></li>
                        </ul>
                    </div>
                `;
            } else if (step.id === 'deductions') {
                customContent = `
                    <h4 style="margin:10px 0 6px;">🧾 Your Deductions to Claim</h4>
                    <div style="background:#f0fdf4; border:1px solid #16a34a; border-radius:8px; padding:12px; margin:8px 0;">
                        <div style="font-weight:600; color:#15803d; margin-bottom:8px;">Enter these amounts in respective sections:</div>
                        <ul style="margin:0;">
                            <li><strong>80C:</strong> ₹${fmt(results.total_deductions || 120000)} (PF/ELSS/LIC)</li>
                            <li><strong>80D:</strong> ₹25,000 (Health Insurance)</li>
                            <li><strong>80CCD(1B):</strong> ₹0 (Additional NPS)</li>
                            <li><strong>80TTA:</strong> ₹0 (Savings Interest exemption)</li>
                        </ul>
                    </div>
                `;
            } else {
                customContent = `
                    <h4 style="margin:10px 0 6px;">📝 What you need here</h4>
                    <ul>${step.inputs.map(i => `<li>${i}</li>`).join('')}</ul>
                `;
            }
            
            stepContent.innerHTML = `
                <div class="subtle">${step.portalPath}</div>
                <h3 style="margin:6px 0 8px;">${step.title}</h3>
                <p class="muted">${step.description}</p>
                ${customContent}
                <div class="tip" style="margin-top:10px;"><strong>💡 Pro Tips:</strong> ${step.tips.join(' • ')}</div>
                <div style="margin-top:12px; display:flex; gap:8px;">
                    <a class="portal" href="https://www.incometax.gov.in" target="_blank" rel="noopener"><button class="btn">🌐 Open Income Tax Portal</button></a>
                    <button class="btn ghost" onclick="markStepCompleteNew('${step.id}')">✓ Mark Step Done</button>
                </div>
            `;
        }

        function renderPrecheckListNew() {
            const precheck = document.getElementById('precheck');
            if (!precheck) return;
            
            precheck.innerHTML = `
                <div class="check"><input type="checkbox" id="chk_docs"/> <label for="chk_docs">I have Form 16 / 26AS / AIS / proofs ready</label></div>
                <div class="check"><input type="checkbox" id="chk_calc"/> <label for="chk_calc">I reviewed taxable vs exempt HRA</label></div>
                <div class="check"><input type="checkbox" id="chk_compare"/> <label for="chk_compare">I compared Old vs New regime</label></div>
            `;
        }

        window.markStepCompleteNew = function(stepId) {
            const btn = document.querySelector(`[data-id="${stepId}"]`);
            if (btn && !btn.classList.contains('completed')) {
                btn.style.background = '#16a34a';
                btn.style.color = '#fff';
                btn.innerHTML = '✓ ' + btn.innerHTML.replace('✓ ', '');
                btn.classList.add('completed');
                alert('✅ Step marked as complete! Continue to the next step.');
            }
        }

        // Update the main populateAnalysisResults to call new functions
        const originalPopulateAnalysisResults = window.populateAnalysisResults;
        window.populateAnalysisResults = function(results) {
            if (originalPopulateAnalysisResults) {
                originalPopulateAnalysisResults.call(this, results);
            }
            // Also populate reference design elements
            populateReferenceDesignElements(results);
        }

        </script>
    """
    
    # Insert multipage sections before the footer
    footer_index = html_content.find('<footer>')
    if footer_index != -1:
        html_content = html_content[:footer_index] + multipage_sections + html_content[footer_index:]
    
    return html_content

# Keep all existing API endpoints
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
        
        # Update progress: Initializing
        total_files = len(uploaded_files)
        update_progress('Initializing AI Models', 5, step='init', total_files=total_files)
        
        # Initialize the analyzer
        analyzer_type = request.form.get('analyzer', 'ollama')
        if analyzer_type == 'langextract':
            analyzer = LangextractDocumentAnalyzer()
        else:
            analyzer = OllamaDocumentAnalyzer()
        
        # Create assistant and analyze documents
        assistant = IncomeTaxAssistant(analyzer=analyzer)
        
        # Update progress: OCR and Analysis starting
        update_progress('OCR Document Scanning', 15, step='ocr', total_files=total_files)
        
        # Analyze documents
        analyzed_docs = []
        files_processed = 0
        
        for i, file_path in enumerate(uploaded_files):
            filename = Path(file_path).name
            
            # Update progress for current file
            progress = 15 + (i * 60 // total_files)  # 15-75% for file processing
            update_progress(f'Analyzing: {filename}', progress, filename, 'extract', files_processed, total_files)
            
            try:
                result = analyzer.analyze_document(file_path)
                if result:
                    analyzed_docs.append(result)
                    logger.info(f"Successfully analyzed: {filename}")
                files_processed += 1
                
                # Update progress after each file
                progress = 15 + ((i + 1) * 60 // total_files)
                update_progress(f'Processed: {filename}', progress, filename, 'classify', files_processed, total_files)
                
            except Exception as e:
                logger.error(f"Error analyzing {filename}: {e}")
                files_processed += 1
        
        # Update progress: Tax calculations
        update_progress('Tax Optimization Analysis', 80, step='calculate', files_processed=files_processed, total_files=total_files)
        
        # Set the analyzed documents in the assistant
        assistant.analyzed_documents = analyzed_docs
        
        # Calculate tax summary
        tax_summary = assistant.calculate_tax_summary()
        
        # Update progress: Finalizing
        update_progress('Generating Report & Recommendations', 95, step='finalize', files_processed=files_processed, total_files=total_files)
        
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Store results globally for report download
        global current_analysis_results
        current_analysis_results = tax_summary
        
        # Update progress: Complete
        update_progress('Analysis Complete', 100, step='complete', files_processed=files_processed, total_files=total_files)
        
        logger.info(f"Analysis completed. Processed {len(analyzed_docs)} documents.")
        
        return jsonify(tax_summary)
        
    except Exception as e:
        logger.error(f"Error in analyze_documents: {e}")
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

def update_progress(stage, progress, current_file='', step='processing', files_processed=0, total_files=0):
    """Update global progress state"""
    global current_progress
    current_progress.update({
        'stage': stage,
        'progress': progress,
        'current_file': current_file,
        'files_processed': files_processed,
        'total_files': total_files,
        'step': step,
        'timestamp': datetime.now().isoformat()
    })
    logger.info(f"Progress: {stage} - {progress}% - {current_file}")

@app.route('/api/progress')
def get_progress():
    """Get current processing progress"""
    return jsonify(current_progress)

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
    
    logger.info("Starting TaxSahaj Multi-Page Web Server...")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    
    # Run the Flask app
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=True,
        threaded=True
    )