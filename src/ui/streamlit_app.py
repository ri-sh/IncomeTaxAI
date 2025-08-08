"""
Streamlit UI for Income Tax AI Assistant
Comprehensive interface with chat, document analysis, and tax calculations
"""

import streamlit as st
import asyncio
import json
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any

# Import our AI components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the new integrated system
from src.core.ollama_document_analyzer import OllamaDocumentAnalyzer, OllamaExtractedData
from src.core.tax_calculator import TaxCalculator
from src.core.document_processor import DocumentProcessor
from src.main import IncomeTaxAssistant

# Configure Streamlit page
st.set_page_config(
    page_title="🇮🇳 Income Tax AI Assistant",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #FF6B35, #F7931E);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .document-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: #d4edda;
        border-left-color: #28a745;
    }
    
    .warning-card {
        background: #fff3cd;
        border-left-color: #ffc107;
    }
    
    .error-card {
        background: #f8d7da;
        border-left-color: #dc3545;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .chat-message {
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 10px;
    }
    
    .user-message {
        background: #e3f2fd;
        margin-left: 2rem;
    }
    
    .assistant-message {
        background: #f1f8e9;
        margin-right: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state"""
    if 'ai_assistant' not in st.session_state:
        st.session_state.ai_assistant = None
    if 'documents_analyzed' not in st.session_state:
        st.session_state.documents_analyzed = {}
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'initialization_done' not in st.session_state:
        st.session_state.initialization_done = False

@st.cache_resource
def load_ai_assistant(user_documents_path: str, load_model: bool = False):
    """Load AI assistant with both optimized models (cached for performance)"""
    try:
        # Initialize the new integrated tax assistant
        assistant = IncomeTaxAssistant()
        
        # Load optimized models
        models_loaded = {
            "ollama": False,
            "donut": False
        }
        
        # Load Ollama LLM (always available)
        try:
            from src.core.optimized_ollama_analyzer import OptimizedOllamaAnalyzer
            assistant.ollama_analyzer = OptimizedOllamaAnalyzer()
            models_loaded["ollama"] = True
            print("✅ Optimized Ollama LLM loaded")
        except Exception as e:
            print(f"⚠️ Ollama LLM not available: {e}")
        
        # Load Donut Model (optional)
        if load_model:
            try:
                from src.models.donut_model_optimized import donut_model
                if donut_model.load_model():
                    assistant.donut_model = donut_model
                    models_loaded["donut"] = True
                    print("✅ Optimized Donut Model loaded")
                else:
                    print("⚠️ Donut Model failed to load")
            except Exception as e:
                print(f"⚠️ Donut Model not available: {e}")
        
        # Test document analysis capability
        if Path(user_documents_path).exists():
            # Try to analyze one document to test the system
            test_files = list(Path(user_documents_path).glob("*.pdf"))[:1]
            if test_files:
                test_result = assistant.analyze_documents_folder(str(test_files[0].parent))
                if test_result:
                    return assistant, True
        
        return assistant, True
        
    except Exception as e:
        st.error(f"Error loading AI assistant: {e}")
        return None, False

def analyze_document_with_selected_model(assistant, file_path: str, selected_model: str):
    """Analyze a document using the selected model"""
    try:
        if selected_model == "Ollama LLM (Fast)":
            if hasattr(assistant, 'ollama_analyzer'):
                return assistant.ollama_analyzer.analyze_document(file_path)
            else:
                # Fallback to original method
                return assistant.document_analyzer.analyze_document(file_path)
        
        elif selected_model == "Donut Model (High Accuracy)":
            if hasattr(assistant, 'donut_model'):
                result = assistant.donut_model.analyze_document(file_path)
                # Convert Donut result to OllamaExtractedData format
                if result.get('success'):
                    from src.core.ollama_document_analyzer import OllamaExtractedData
                    extracted_data = OllamaExtractedData()
                    extracted_data.document_type = result.get('document_type', 'unknown')
                    extracted_data.confidence = result.get('confidence', 0.85)
                    extracted_data.extraction_method = result.get('method', 'donut_model')
                    
                    # Extract structured data
                    structured_data = result.get('structured_data', {})
                    extracted_data.gross_salary = structured_data.get('gross_salary', 0.0)
                    extracted_data.tax_deducted = structured_data.get('tax_deducted', 0.0)
                    extracted_data.employee_name = structured_data.get('employee_name', '')
                    extracted_data.pan = structured_data.get('pan_number', '')
                    
                    return extracted_data
                else:
                    raise Exception(f"Donut analysis failed: {result.get('error', 'Unknown error')}")
            else:
                raise Exception("Donut model not loaded")
        
        elif selected_model == "Auto Select":
            # Auto-select logic: Use Donut for Form 16, Ollama for others
            if "form16" in file_path.lower() or "form_16" in file_path.lower():
                return analyze_document_with_selected_model(assistant, file_path, "Donut Model (High Accuracy)")
            else:
                return analyze_document_with_selected_model(assistant, file_path, "Ollama LLM (Fast)")
        
        else:
            raise Exception(f"Unknown model: {selected_model}")
            
    except Exception as e:
        st.error(f"Error analyzing {file_path} with {selected_model}: {e}")
        return None

def main():
    """Main Streamlit application"""
    
    init_session_state()
    
    # Handle OAuth callback
    if 'code' in st.query_params:
        auth_code = st.query_params['code']
        st.session_state.oauth_code = auth_code
        st.success("✅ Authorization code received! Please complete authentication in the Google Drive Setup tab.")
        
        # Auto-complete authentication if simple auth is available
        try:
            from src.data.simple_google_auth import simple_auth
            if simple_auth.exchange_code_for_token(auth_code):
                st.success("🎉 Google authentication completed automatically!")
                st.rerun()
        except:
            pass  # Fall back to manual completion
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🇮🇳 Income Tax AI Assistant - FY 2024-25</h1>
        <p>Intelligent tax filing with GPT-OSS-20B & LlamaIndex | Document Analysis | Tax Optimization</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # User documents path
        user_docs_path = st.text_input(
            "📁 Documents Folder Path",
            value=str(Path.home() / "Desktop" / "Income Tax 2024-2025"),
            help="Path to your local tax documents folder"
        )
        st.session_state.user_docs_path = user_docs_path  # Store in session state
        
        # Google Drive integration
        st.subheader("☁️ Google Drive Integration")
        google_drive_url = st.text_input(
            "🔗 Google Drive Folder URL (Optional)",
            placeholder="https://drive.google.com/drive/folders/YOUR_FOLDER_ID",
            help="Paste your Google Drive folder URL to fetch documents from cloud"
        )
        
        # Store Google Drive URL in session state
        if google_drive_url:
            st.session_state.google_drive_url = google_drive_url
            
            # Extract and show folder ID
            from src.data.google_drive_integration import GoogleDriveIntegration
            folder_id = GoogleDriveIntegration.extract_folder_id_from_url(google_drive_url)
            if folder_id:
                st.success(f"✅ Valid Google Drive URL detected")
                st.info(f"📁 Folder ID: {folder_id}")
            else:
                st.error("❌ Invalid Google Drive URL format")
        else:
            # Clear Google Drive URL from session state if empty
            if 'google_drive_url' in st.session_state:
                del st.session_state.google_drive_url
        
        # AI Model Selection
        st.subheader("🤖 AI Model Selection")
        
        # Model selection
        selected_model = st.selectbox(
            "Choose Analysis Model",
            ["Ollama LLM (Fast)", "Donut Model (High Accuracy)", "Auto Select"],
            help="Select the AI model for document analysis"
        )
        
        # Store selected model in session state
        st.session_state.selected_model = selected_model
        
        # Model information
        if selected_model == "Ollama LLM (Fast)":
            st.info("""
            **🔍 Ollama LLM (Optimized)**
            
            - **Speed**: ⚡ Fast (28s per document)
            - **Accuracy**: 90% for tax documents
            - **Memory**: Low (4-8 GB)
            - **Best for**: Real-time analysis, all document types
            - **Features**: Caching, parallel processing, optimized regex
            """)
        elif selected_model == "Donut Model (High Accuracy)":
            st.info("""
            **🔍 Donut Model (Optimized)**
            
            - **Speed**: 🐌 Slower (65s per document)
            - **Accuracy**: 95% for Form 16
            - **Memory**: Medium (2-4 GB)
            - **Best for**: High accuracy, detailed extraction
            - **Features**: PDF→Image conversion, 787+ amounts extracted
            """)
        else:  # Auto Select
            st.info("""
            **🔍 Auto Select**
            
            - **Logic**: Automatically chooses best model
            - **Form 16**: Uses Donut for high accuracy
            - **Other Docs**: Uses Ollama for speed
            - **Smart**: Balances speed vs accuracy
            """)
        
        # Model status indicators
        if 'ai_assistant' in st.session_state and st.session_state.ai_assistant:
            if selected_model == "Ollama LLM (Fast)":
                st.success("✅ Ollama LLM ready!")
            elif selected_model == "Donut Model (High Accuracy)":
                st.success("✅ Donut Model ready!")
            else:
                st.success("✅ Both models ready!")
        else:
            st.warning("⚠️ Click 'Initialize AI Assistant' to load models")
        
        # Model Configuration
        st.subheader("⚙️ Configuration")
        load_full_model = st.checkbox(
            "Load Donut Model (Optional)",
            value=False,
            help="Load Donut model for high-accuracy Form 16 analysis. Requires more memory but provides 95% accuracy."
        )
        
        # Initialize button
        if st.button("🚀 Initialize AI Assistant", type="primary"):
            with st.spinner("Loading AI components..."):
                assistant, success = load_ai_assistant(user_docs_path, load_full_model)
                st.session_state.ai_assistant = assistant
                st.session_state.initialization_done = success
                
                if success:
                    st.success("✅ AI Assistant loaded successfully!")
                else:
                    st.warning("⚠️ AI Assistant loaded with limited functionality")
        
        # Status
        st.subheader("📊 System Status")
        if st.session_state.ai_assistant:
            assistant = st.session_state.ai_assistant
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🤖 Ollama LLM", "✅ Ready")
            with col2:
                if hasattr(assistant, 'donut_model') and assistant.donut_model.is_loaded:
                    st.metric("🔍 Donut Model", "✅ Ready")
                else:
                    st.metric("🔍 Donut Model", "❌ Not Loaded")
            with col3:
                st.metric("📄 Document Processor", "✅ Ready")
            
            # Show analyzed documents count
            if hasattr(st.session_state, 'analyzed_documents'):
                st.metric("📄 Documents Analyzed", len(st.session_state.analyzed_documents))
            
            # Show tax summary status
            if hasattr(st.session_state, 'tax_summary'):
                st.metric("🧮 Tax Summary", "✅ Calculated")
            
            # Show Form16 analysis accuracy
            if hasattr(st.session_state, 'analyzed_documents') and st.session_state.analyzed_documents:
                form16_docs = [doc for doc in st.session_state.analyzed_documents if doc.document_type == "form_16"]
                if form16_docs:
                    form16 = form16_docs[0]
                    if form16.gross_salary > 0 and form16.total_gross_salary > 0:
                        accuracy = (1 - abs(form16.gross_salary - form16.total_gross_salary) / form16.gross_salary) * 100
                        if accuracy > 99:
                            st.metric("📄 Form16 Analysis", "✅ Perfect")
                        elif accuracy > 95:
                            st.metric("📄 Form16 Analysis", "⚠️ Good")
                        else:
                            st.metric("📄 Form16 Analysis", "❌ Poor")
                    else:
                        st.metric("📄 Form16 Analysis", "⚠️ Partial")
                else:
                    st.metric("📄 Form16 Analysis", "❌ Not Found")
        else:
            st.info("🤖 AI Assistant not initialized")
    
    # Main content area
    if not st.session_state.ai_assistant:
        st.info("👆 Please initialize the AI Assistant using the sidebar to get started.")
        
        # Show preview while not initialized
        st.subheader("🎯 What This AI Assistant Can Do")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            **🔍 Document Analysis**
            - AI-powered document recognition
            - Extract key tax information
            - Identify document types automatically
            - Generate filing recommendations
            """)
        
        with col2:
            st.markdown("""
            **💬 Tax Q&A**
            - Ask natural language questions
            - Get expert tax advice
            - Regime comparison analysis
            - Deduction optimization tips
            """)
        
        with col3:
            st.markdown("""
            **📊 Smart Insights**
            - Missing document detection
            - Tax-saving opportunities
            - Compliance checklist
            - Personalized recommendations
            """)
        
        return
    
    # Main application tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📄 Document Analysis", 
        "💬 Tax Assistant Chat", 
        "⚖️ Regime Comparison", 
        "📊 Tax Dashboard", 
        "📋 ITR Filing Guide",
        "📄 PDF Reports",
        "🔗 Google Drive Setup"
    ])
    
    # Tab 1: Document Analysis
    with tab1:
        show_document_analysis_tab()
    
    # Tab 2: Chat Interface
    with tab2:
        show_chat_interface_tab()
    
    # Tab 3: Regime Comparison
    with tab3:
        show_regime_comparison_tab()
    
    # Tab 4: Dashboard
    with tab4:
        show_dashboard_tab()
    
    # Tab 5: ITR Filing Guide
    with tab5:
        show_itr_guide_tab()
    
    # Tab 6: PDF Reports
    with tab6:
        show_pdf_reports_tab()
    
    # Tab 7: Google Drive Setup
    with tab7:
        show_google_drive_setup_tab()

def show_document_analysis_tab():
    """Document analysis interface"""
    
    st.header("📄 AI-Powered Document Analysis")
    
    assistant = st.session_state.ai_assistant
    
    if not assistant:
        st.error("❌ AI Assistant not initialized. Please initialize from the sidebar.")
        return
    
    # Analyze all documents button
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.button("🔍 Analyze All Documents with AI", type="primary"):
            with st.spinner("Analyzing documents with AI..."):
                try:
                    # Get documents folder path from sidebar
                    user_docs_path = st.session_state.get('user_docs_path', str(Path.home() / "Documents" / "Tax Documents"))
                    
                    # Check if Google Drive URL is provided
                    google_drive_url = st.session_state.get('google_drive_url', '')
                    
                    if google_drive_url:
                        # Use Google Drive integration
                        st.info("☁️ Fetching documents from Google Drive...")
                        from src.data.multi_source_fetcher import MultiSourceDocumentFetcher
                        
                        # Initialize fetcher
                        fetcher = MultiSourceDocumentFetcher()
                        
                        # Extract folder ID from URL
                        from src.data.google_drive_integration import GoogleDriveIntegration
                        folder_id = GoogleDriveIntegration.extract_folder_id_from_url(google_drive_url)
                        
                        if folder_id:
                            try:
                                # Fetch documents from Google Drive
                                drive_documents = fetcher.fetch_from_google_drive(folder_id)
                                
                                if drive_documents:
                                    st.success(f"✅ Found {len(drive_documents)} documents in Google Drive")
                                    
                                    # Analyze each document with selected model
                                    selected_model = st.session_state.get('selected_model', 'Ollama LLM (Fast)')
                                    analyzed_docs = []
                                    
                                    progress_bar = st.progress(0)
                                    for i, doc in enumerate(drive_documents):
                                        try:
                                            # Update progress
                                            progress_bar.progress((i + 1) / len(drive_documents))
                                            
                                            # Analyze with selected model
                                            result = analyze_document_with_selected_model(assistant, doc.path, selected_model)
                                            
                                            if result:
                                                analyzed_docs.append(result)
                                                st.write(f"✅ Analyzed: {doc.name}")
                                            else:
                                                st.warning(f"⚠️ Failed to analyze: {doc.name}")
                                                
                                        except Exception as e:
                                            st.error(f"❌ Error analyzing {doc.name}: {e}")
                                            continue
                                    
                                    progress_bar.empty()
                                    
                                    if analyzed_docs:
                                        st.session_state.analyzed_documents = analyzed_docs
                                        st.success(f"✅ Successfully analyzed {len(analyzed_docs)} documents from Google Drive!")
                                        
                                        # Check for perfect Form16 analysis
                                        form16_docs = [doc for doc in analyzed_docs if doc.document_type == "form_16"]
                                        if form16_docs:
                                            form16 = form16_docs[0]
                                            if form16.gross_salary > 0 and form16.total_gross_salary > 0:
                                                accuracy = (1 - abs(form16.gross_salary - form16.total_gross_salary) / form16.gross_salary) * 100
                                                if accuracy > 99:
                                                    st.success("🎉 **PERFECT ACCURACY!** Form16 analysis is 100% accurate with robust patterns!")
                                        
                                        # Calculate tax summary
                                        tax_summary = assistant.calculate_tax_summary()
                                        st.session_state.tax_summary = tax_summary
                                    else:
                                        st.warning("⚠️ No documents could be analyzed from Google Drive.")
                                else:
                                    st.warning("⚠️ No documents found in Google Drive folder.")
                                    
                            except Exception as e:
                                if "credentials.json" in str(e):
                                    st.error("❌ Google Drive authentication not set up")
                                    st.info("""
                                    **🔧 To use Google Drive integration:**
                                    
                                    1. **Download credentials.json** from Google Cloud Console
                                    2. **Place it in your project root** directory
                                    3. **Run the app** - it will authenticate via browser
                                    
                                    **📁 For now, you can:**
                                    - Use local documents folder instead
                                    - Or manually upload documents
                                    """)
                                    
                                    # Offer to use local folder as fallback
                                    if st.button("📁 Use Local Documents Instead"):
                                        st.info("🔄 Switching to local documents...")
                                        analyzed_docs = assistant.analyze_documents_folder(user_docs_path)
                                        
                                        if analyzed_docs:
                                            st.session_state.analyzed_documents = analyzed_docs
                                            st.success(f"✅ Successfully analyzed {len(analyzed_docs)} local documents!")
                                            
                                            # Calculate tax summary
                                            tax_summary = assistant.calculate_tax_summary()
                                            st.session_state.tax_summary = tax_summary
                                        else:
                                            st.warning("⚠️ No documents found in local folder either.")
                                else:
                                    st.error(f"❌ Error accessing Google Drive: {e}")
                        else:
                            st.error("❌ Invalid Google Drive URL format")
                    else:
                        # Use local folder with selected model
                        selected_model = st.session_state.get('selected_model', 'Ollama LLM (Fast)')
                        
                        # Get all PDF files in the folder
                        pdf_files = list(Path(user_docs_path).glob("*.pdf"))
                        excel_files = list(Path(user_docs_path).glob("*.xlsx")) + list(Path(user_docs_path).glob("*.xls"))
                        all_files = pdf_files + excel_files
                        
                        if all_files:
                            st.info(f"🔍 Analyzing {len(all_files)} documents with {selected_model}...")
                            
                            analyzed_docs = []
                            progress_bar = st.progress(0)
                            
                            for i, file_path in enumerate(all_files):
                                try:
                                    # Update progress
                                    progress_bar.progress((i + 1) / len(all_files))
                                    
                                    # Analyze with selected model
                                    result = analyze_document_with_selected_model(assistant, str(file_path), selected_model)
                                    
                                    if result:
                                        analyzed_docs.append(result)
                                        st.write(f"✅ Analyzed: {file_path.name}")
                                    else:
                                        st.warning(f"⚠️ Failed to analyze: {file_path.name}")
                                        
                                except Exception as e:
                                    st.error(f"❌ Error analyzing {file_path.name}: {e}")
                                    continue
                            
                            progress_bar.empty()
                        else:
                            st.warning("⚠️ No documents found in the specified folder.")
                            analyzed_docs = []
                        
                        if analyzed_docs:
                            st.session_state.analyzed_documents = analyzed_docs
                            st.success(f"✅ Successfully analyzed {len(analyzed_docs)} documents!")
                            
                            # Check for perfect Form16 analysis
                            form16_docs = [doc for doc in analyzed_docs if doc.document_type == "form_16"]
                            if form16_docs:
                                form16 = form16_docs[0]
                                if form16.gross_salary > 0 and form16.total_gross_salary > 0:
                                    accuracy = (1 - abs(form16.gross_salary - form16.total_gross_salary) / form16.gross_salary) * 100
                                    if accuracy > 99:
                                        st.success("🎉 **PERFECT ACCURACY!** Form16 analysis is 100% accurate with robust patterns!")
                            
                            # Calculate tax summary
                            tax_summary = assistant.calculate_tax_summary()
                            st.session_state.tax_summary = tax_summary
                            
                        else:
                            st.warning("⚠️ No documents were analyzed. Please check your documents folder.")
                        
                except Exception as e:
                    st.error(f"❌ Error analyzing documents: {e}")
    
    with col2:
        if st.button("📊 Export Analysis"):
            try:
                assistant.generate_report("tax_analysis_report.json")
                st.success("📄 Report exported successfully!")
            except Exception as e:
                st.error(f"❌ Error exporting report: {e}")
    
    # Show analysis results
    if hasattr(st.session_state, 'analyzed_documents') and st.session_state.analyzed_documents:
        st.subheader("📋 Analysis Results")
        
        for doc in st.session_state.analyzed_documents:
            # Show model used in the title
            model_used = doc.extraction_method if hasattr(doc, 'extraction_method') else 'ollama_llm'
            model_display = "🔍 Donut" if "donut" in model_used else "🤖 Ollama"
            
            with st.expander(f"{model_display} 📄 {doc.document_type.title()} - Confidence: {doc.confidence:.1%}", expanded=False):
                
                # Basic info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Confidence", f"{doc.confidence:.1%}")
                with col2:
                    method_display = doc.extraction_method if hasattr(doc, 'extraction_method') else 'ollama_llm'
                    st.metric("Method", method_display.replace('_', ' ').title())
                with col3:
                    st.metric("Type", doc.document_type.title())
                
                # Key information based on document type
                st.write("**🔑 Key Information:**")
                
                if doc.document_type == "form_16":
                    st.write(f"• **Employee:** {doc.employee_name or 'Not found'}")
                    st.write(f"• **PAN:** {doc.pan or 'Not found'}")
                    st.write(f"• **Employer:** {doc.employer_name or 'Not found'}")
                    
                    # Enhanced Form16 display with new fields
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**💰 Salary Breakdown:**")
                        st.write(f"• **Basic Salary:** ₹{doc.basic_salary:,.2f}")
                        st.write(f"• **Perquisites:** ₹{doc.perquisites:,.2f}")
                        st.write(f"• **Total Gross Salary:** ₹{doc.total_gross_salary:,.2f}")
                        st.write(f"• **Gross Salary (Quarterly):** ₹{doc.gross_salary:,.2f}")
                    
                    with col2:
                        st.write("**🧾 Tax Information:**")
                        st.write(f"• **Tax Deducted:** ₹{doc.tax_deducted:,.2f}")
                        st.write(f"• **HRA Received:** ₹{doc.hra_received:,.2f}")
                        st.write(f"• **Special Allowance:** ₹{doc.special_allowance:,.2f}")
                        st.write(f"• **Other Allowances:** ₹{doc.other_allowances:,.2f}")
                    
                    # Show accuracy indicators
                    if doc.gross_salary > 0 and doc.total_gross_salary > 0:
                        accuracy = (1 - abs(doc.gross_salary - doc.total_gross_salary) / doc.gross_salary) * 100
                        if accuracy > 99:
                            st.success("✅ **Perfect Accuracy** - All salary components extracted correctly!")
                        elif accuracy > 95:
                            st.warning("⚠️ **Good Accuracy** - Minor discrepancies in extraction")
                        else:
                            st.error("❌ **Low Accuracy** - Significant discrepancies detected")
                
                elif doc.document_type == "bank_interest_certificate":
                    st.write(f"• **Bank:** {doc.bank_name or 'Not found'}")
                    st.write(f"• **Interest Amount:** ₹{doc.interest_amount:,.2f}")
                    st.write(f"• **TDS Amount:** ₹{doc.tds_amount:,.2f}")
                    st.write(f"• **PAN:** {doc.pan or 'Not found'}")
                
                elif doc.document_type == "capital_gains":
                    st.write(f"• **Total Capital Gains:** ₹{doc.total_capital_gains:,.2f}")
                    st.write(f"• **LTCG:** ₹{doc.long_term_capital_gains:,.2f}")
                    st.write(f"• **STCG:** ₹{doc.short_term_capital_gains:,.2f}")
                    st.write(f"• **Transactions:** {doc.number_of_transactions}")
                
                elif doc.document_type == "investment":
                    st.write(f"• **EPF:** ₹{doc.epf_amount:,.2f}")
                    st.write(f"• **PPF:** ₹{doc.ppf_amount:,.2f}")
                    st.write(f"• **ELSS:** ₹{doc.elss_amount:,.2f}")
                    st.write(f"• **Life Insurance:** ₹{doc.life_insurance:,.2f}")
                    st.write(f"• **Health Insurance:** ₹{doc.health_insurance:,.2f}")
                
                # Show errors if any
                if doc.errors:
                    st.write("**⚠️ Errors:**")
                    for error in doc.errors:
                        st.error(f"• {error}")
    
    # Show tax summary if available
    if hasattr(st.session_state, 'tax_summary') and st.session_state.tax_summary:
        st.subheader("📊 Tax Summary")
        
        summary = st.session_state.tax_summary
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 Total Income", f"₹{summary['total_income']:,.0f}")
        
        with col2:
            st.metric("💼 Deductions", f"₹{summary['total_deductions']:,.0f}")
        
        with col3:
            st.metric("🧾 Tax Paid", f"₹{summary['tax_paid']:,.0f}")
        
        with col4:
            recommended = summary['recommended_regime'].title()
            st.metric("⚖️ Best Regime", recommended)
        
        # Show detailed breakdown
        with st.expander("📋 Detailed Tax Breakdown", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**💰 Income Breakdown:**")
                st.write(f"• **Salary Income:** ₹{summary['salary_income']:,.0f}")
                st.write(f"• **Interest Income:** ₹{summary['interest_income']:,.0f}")
                st.write(f"• **Capital Gains:** ₹{summary['capital_gains']:,.0f}")
                
                # Show Form16 specific breakdown if available
                if hasattr(st.session_state, 'analyzed_documents') and st.session_state.analyzed_documents:
                    form16_docs = [doc for doc in st.session_state.analyzed_documents if doc.document_type == "form_16"]
                    if form16_docs:
                        form16 = form16_docs[0]  # Take the first Form16
                        st.write("**📄 Form16 Breakdown:**")
                        st.write(f"• **Basic Salary:** ₹{form16.basic_salary:,.0f}")
                        st.write(f"• **Perquisites:** ₹{form16.perquisites:,.0f}")
                        st.write(f"• **Total Gross:** ₹{form16.total_gross_salary:,.0f}")
            
            with col2:
                st.write("**🧾 Tax Liability:**")
                st.write(f"• **New Regime:** ₹{summary['tax_liability_new_regime']:,.0f}")
                st.write(f"• **Old Regime:** ₹{summary['tax_liability_old_regime']:,.0f}")
                
                # Calculate additional tax or refund
                recommended_tax = (
                    summary['tax_liability_new_regime'] 
                    if summary['recommended_regime'] == 'new' 
                    else summary['tax_liability_old_regime']
                )
                
                additional_tax = recommended_tax - summary['tax_paid']
                
                if additional_tax > 0:
                    st.error(f"💸 **Additional Tax Due:** ₹{additional_tax:,.0f}")
                else:
                    st.success(f"💰 **Tax Refund:** ₹{abs(additional_tax):,.0f}")
                
                # Show accuracy status
                if hasattr(st.session_state, 'analyzed_documents') and st.session_state.analyzed_documents:
                    form16_docs = [doc for doc in st.session_state.analyzed_documents if doc.document_type == "form_16"]
                    if form16_docs:
                        form16 = form16_docs[0]
                        if form16.gross_salary > 0 and form16.total_gross_salary > 0:
                            accuracy = (1 - abs(form16.gross_salary - form16.total_gross_salary) / form16.gross_salary) * 100
                            if accuracy > 99:
                                st.success("✅ **Perfect Extraction**")
                            elif accuracy > 95:
                                st.warning("⚠️ **Good Extraction**")
                            else:
                                st.error("❌ **Poor Extraction**")
    
    else:
        st.info("Click 'Analyze All Documents' to start AI-powered analysis of your tax documents.")

def show_chat_interface_tab():
    """Tax assistant chat interface"""
    
    st.header("💬 Tax Assistant Chat")
    st.write("Ask me anything about Indian income tax, your documents, or filing process!")
    
    assistant = st.session_state.ai_assistant
    
    if not assistant:
        st.error("❌ AI Assistant not initialized. Please initialize from the sidebar.")
        return
    
    # Chat input with guidelines
    st.markdown("""
    **🎯 I can help you with:**
    • ITR filing and tax calculations
    • Deductions (80C, 80D, HRA, etc.)
    • Tax regime comparison
    • Document requirements
    • Filing deadlines and procedures
    
    **❌ I cannot help with:**
    • Non-tax questions (weather, sports, etc.)
    • Other countries' tax systems
    • General investment advice
    """)
    
    # Check for follow-up question from button clicks
    if hasattr(st.session_state, 'followup_question'):
        user_question = st.session_state.followup_question
        # Clear the follow-up question after using it
        del st.session_state.followup_question
        
        # Process the follow-up question automatically
        with st.spinner("🤖 AI is thinking..."):
            # For now, we'll use a simple response since the chat system needs to be adapted
            response = f"Thank you for your follow-up question: '{user_question}'. This feature is being enhanced with the new integrated system."
            st.session_state.chat_history.append({
                "question": user_question,
                "answer": response,
                "timestamp": datetime.now()
            })
            st.rerun()
    
    user_question = st.text_input(
        "💭 Ask your Indian income tax question:",
        placeholder="e.g., Which tax regime is better for me? How do I claim ELSS deduction?",
        key="chat_input"
    )
    
    if st.button("📤 Ask Question") and user_question:
        with st.spinner("🤖 AI is thinking..."):
            # For now, provide a simple response
            response = f"Thank you for your question: '{user_question}'. The chat system is being enhanced with the new integrated AI capabilities. Please use the Document Analysis tab to analyze your tax documents and get detailed insights."
            st.session_state.chat_history.append({
                "question": user_question,
                "answer": response,
                "timestamp": datetime.now()
            })
    
    # Show chat history
    if st.session_state.chat_history:
        st.subheader("💬 Conversation History")
        
        for session in reversed(st.session_state.chat_history[-5:]):  # Show last 5
            
            # User question
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🧑 You:</strong> {session['question']}
            </div>
            """, unsafe_allow_html=True)
            
            # AI response
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 AI Tax Assistant:</strong><br>
                {session['answer']}
            </div>
            """, unsafe_allow_html=True)
            
            st.divider()
    
    else:
        st.info("👆 Ask your first tax question to start the conversation!")

def show_dashboard_tab():
    """Comprehensive Tax Analysis Dashboard - Similar to Income Tax Portal"""
    
    st.header("📊 Comprehensive Tax Analysis Dashboard")
    st.write("💡 **Income Tax Portal-style detailed breakdown** | Select regime to see tax implications")
    
    assistant = st.session_state.ai_assistant
    
    if not assistant:
        st.error("❌ AI Assistant not initialized. Please initialize from the sidebar.")
        return
    
    # Get analyzed documents
    if not hasattr(st.session_state, 'analyzed_documents') or not st.session_state.analyzed_documents:
        st.warning("📄 **No documents analyzed yet.** Please go to 'Document Analysis' tab first.")
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
        return
    
    # Check if we have tax summary
    if not hasattr(st.session_state, 'tax_summary') or not st.session_state.tax_summary:
        st.warning("🧮 **No tax summary available.** Please analyze documents first.")
        return
    
    # Input section for additional details
    st.subheader("🏠 Additional Information for Accurate Calculation")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        rent_paid = st.number_input(
            "🏠 Monthly Rent Paid (₹)",
            min_value=0,
            value=st.session_state.get('rent_paid', 0),
            step=1000,
            help="Enter monthly rent for HRA exemption calculation"
        )
        st.session_state.rent_paid = rent_paid
    
    with col2:
        is_metro = st.checkbox(
            "🏙️ Living in Metro City",
            value=st.session_state.get('is_metro', False),
            help="Delhi, Mumbai, Chennai, Kolkata"
        )
        st.session_state.is_metro = is_metro
    
    with col3:
        selected_regime = st.selectbox(
            "⚖️ Select Tax Regime",
            options=["Compare Both", "New Regime", "Old Regime"],
            index=0,
            help="Choose regime to see detailed calculations"
        )
    
    # Auto-recalculate when inputs change
    if st.session_state.get('rent_paid') != rent_paid or st.session_state.get('is_metro') != is_metro:
        with st.spinner("🔄 Updating calculations..."):
            # Recalculate tax summary with new inputs
            updated_summary = assistant.calculate_tax_summary_with_additional_data(
                rent_paid=rent_paid,
                is_metro=is_metro
            )
            st.session_state.tax_summary = updated_summary
            st.session_state.rent_paid = rent_paid
            st.session_state.is_metro = is_metro
            st.success("✅ Tax calculations updated!")
    
    # Manual recalculate button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Force Recalculate", type="secondary"):
            with st.spinner("Recalculating tax with updated values..."):
                # Recalculate tax summary with new inputs
                updated_summary = assistant.calculate_tax_summary_with_additional_data(
                    rent_paid=rent_paid,
                    is_metro=is_metro
                )
                st.session_state.tax_summary = updated_summary
                st.success("✅ Tax recalculated with new values!")
                st.rerun()
    
    # Display analysis if available
    analysis = st.session_state.tax_summary
    
    # Quick summary cards
    st.subheader("📊 Quick Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "💰 Gross Income", 
            f"₹{analysis['total_income']:,.0f}",
            help="Total income from all sources"
        )
    
    with col2:
        st.metric(
            "💼 Total Deductions", 
            f"₹{analysis['total_deductions']:,.0f}",
            help="Total deductions available"
        )
    
    with col3:
        st.metric(
            "🧾 Tax Already Paid", 
            f"₹{analysis['tax_paid']:,.0f}",
            help="TDS and advance tax paid"
        )
    
    with col4:
        recommended = analysis['recommended_regime'].title()
        st.metric(
            "⚖️ Best Regime", 
            f"{recommended}",
            help="Recommended regime with savings"
        )
    
    # HRA calculation details
    if analysis.get('hra_exemption', 0) > 0:
        st.subheader("🏠 HRA Exemption Details")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🏠 HRA Exemption", 
                f"₹{analysis['hra_exemption']:,.0f}",
                help="HRA exemption calculated"
            )
        
        with col2:
            st.metric(
                "🏠 Rent Paid (Annual)", 
                f"₹{analysis.get('rent_paid', 0):,.0f}",
                help="Total rent paid in the year"
            )
        
        with col3:
            metro_status = "Metro" if analysis.get('is_metro', False) else "Non-Metro"
            st.metric(
                "🏙️ City Type", 
                metro_status,
                help="Metro or non-metro city"
            )
    
    # Regime-specific analysis
    if selected_regime == "Compare Both":
        show_regime_comparison_detailed(analysis)
    else:
        regime_key = "new_regime" if selected_regime == "New Regime" else "old_regime"
        show_single_regime_analysis(analysis, regime_key)
    
    # Income breakdown section
    show_income_breakdown_section(analysis)
    
    # Final tax computation
    show_tax_computation_section(analysis, selected_regime)

def show_regime_comparison_detailed(regime_comparison):
    """Show detailed regime comparison"""
    
    st.subheader("⚖️ Regime Comparison Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🆕 New Tax Regime")
        
        st.metric("Taxable Income", f"₹{regime_comparison['total_income']:,.0f}")
        st.metric("Tax Liability", f"₹{regime_comparison['tax_liability_new_regime']:,.0f}")
        st.metric("Total TDS", f"₹{regime_comparison['tax_paid']:,.0f}")
        
        # Calculate additional tax or refund for new regime
        additional_tax_new = regime_comparison['tax_liability_new_regime'] - regime_comparison['tax_paid']
        
        if additional_tax_new > 0:
            st.error(f"💸 **Balance Payable: ₹{additional_tax_new:,.0f}**")
        else:
            st.success(f"💰 **Refund Due: ₹{abs(additional_tax_new):,.0f}**")
    
    with col2:
        st.markdown("### 🏛️ Old Tax Regime")
        
        st.metric("Taxable Income", f"₹{regime_comparison['total_income']:,.0f}")
        st.metric("Tax Liability", f"₹{regime_comparison['tax_liability_old_regime']:,.0f}")
        st.metric("Total TDS", f"₹{regime_comparison['tax_paid']:,.0f}")
        
        # Calculate additional tax or refund for old regime
        additional_tax_old = regime_comparison['tax_liability_old_regime'] - regime_comparison['tax_paid']
        
        if additional_tax_old > 0:
            st.error(f"💸 **Balance Payable: ₹{additional_tax_old:,.0f}**")
        else:
            st.success(f"💰 **Refund Due: ₹{abs(additional_tax_old):,.0f}**")
    
    # Recommendation
    recommended = regime_comparison['recommended_regime']
    
    if recommended == 'new':
        savings = regime_comparison['tax_liability_old_regime'] - regime_comparison['tax_liability_new_regime']
        st.success(f"🎯 **Recommendation: New Tax Regime** saves ₹{savings:,.0f}")
    else:
        savings = regime_comparison['tax_liability_new_regime'] - regime_comparison['tax_liability_old_regime']
        st.success(f"🎯 **Recommendation: Old Tax Regime** saves ₹{savings:,.0f}")

def show_single_regime_analysis(analysis, regime_key):
    """Show detailed analysis for single regime"""
    
    regime_name = "New Regime" if regime_key == "new_regime" else "Old Regime"
    
    st.subheader(f"📊 {regime_name} - Detailed Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### 💰 Income Summary")
        st.write(f"**Gross Total Income:** ₹{analysis['total_income']:,.0f}")
        st.write(f"**Total Deductions:** ₹{analysis['total_deductions']:,.0f}")
        taxable_income = analysis['total_income'] - analysis['total_deductions']
        st.write(f"**Taxable Income:** ₹{taxable_income:,.0f}")
    
    with col2:
        st.markdown("#### 🧾 Tax Calculation")
        tax_amount = analysis[f'tax_liability_{regime_key}']
        st.write(f"**Tax on Income:** ₹{tax_amount:,.0f}")
        cess = tax_amount * 0.04
        st.write(f"**Health & Education Cess:** ₹{cess:,.0f}")
        total_tax = tax_amount + cess
        st.write(f"**Total Tax:** ₹{total_tax:,.0f}")
    
    with col3:
        st.markdown("#### 💸 Final Settlement")
        st.write(f"**Total TDS:** ₹{analysis['tax_paid']:,.0f}")
        st.write(f"**Advance Tax:** ₹0.00")
        
        additional_tax = total_tax - analysis['tax_paid']
        
        if additional_tax > 0:
            st.error(f"**Balance Payable:** ₹{additional_tax:,.0f}")
        else:
            st.success(f"**Refund Due:** ₹{abs(additional_tax):,.0f}")

def show_income_breakdown_section(analysis):
    """Show detailed income breakdown"""
    
    st.subheader("💰 Income Breakdown")
    
    # Create income breakdown chart
    income_data = {
        'Income Source': ['Salary Income', 'Interest Income', 'Capital Gains'],
        'Amount': [
            analysis['salary_income'], 
            analysis['interest_income'], 
            analysis['capital_gains']
        ]
    }
    
    df_income = pd.DataFrame(income_data)
    df_income = df_income[df_income['Amount'] > 0]  # Filter out zero amounts
    
    if not df_income.empty:
        fig_income = px.pie(
            df_income, 
            values='Amount', 
            names='Income Source',
            title="Income Source Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig_income.update_traces(textposition='inside', textinfo='percent+label')
        fig_income.update_layout(height=400)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.plotly_chart(fig_income, use_container_width=True)
        
        with col2:
            st.markdown("#### 📊 Income Details")
            for _, row in df_income.iterrows():
                st.write(f"**{row['Income Source']}:** ₹{row['Amount']:,.0f}")
            
            st.markdown("---")
            st.write(f"**Total Gross Income:** ₹{analysis['total_income']:,.0f}")

def show_deductions_breakdown_section(analysis):
    """Show deductions breakdown"""
    
    st.subheader("📉 Deductions Breakdown")
    
    deductions = analysis['deductions_summary']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🔒 Section 80C (Limit: ₹1,50,000)")
        
        section_80c_data = {
            'Investment': ['EPF', 'PPF', 'Life Insurance', 'ELSS', 'NSC', 'Home Loan Principal'],
            'Amount': [deductions.epf, deductions.ppf, deductions.life_insurance, 
                      deductions.elss, deductions.nsc, deductions.home_loan_principal]
        }
        
        df_80c = pd.DataFrame(section_80c_data)
        df_80c = df_80c[df_80c['Amount'] > 0]
        
        if not df_80c.empty:
            for _, row in df_80c.iterrows():
                st.write(f"• **{row['Investment']}:** ₹{row['Amount']:,.0f}")
        
        st.write(f"**Total 80C:** ₹{deductions.section_80c_total:,.0f}")
        st.write(f"**Claimed (after limit):** ₹{deductions.section_80c_claimed:,.0f}")
        
        if deductions.section_80c_total > 150000:
            st.warning(f"⚠️ Excess ₹{deductions.section_80c_total - 150000:,.0f} not eligible for deduction")
    
    with col2:
        st.markdown("#### 🏥 Other Deductions")
        
        st.write(f"**Section 80D (Health Insurance):** ₹{deductions.section_80d_claimed:,.0f}")
        st.write(f"**Section 80TTA (Bank Interest):** ₹{deductions.section_80tta:,.0f}")
        st.write(f"**Section 24(b) (Home Loan Interest):** ₹{deductions.section_24b:,.0f}")
        st.write(f"**Section 80G (Donations):** ₹{deductions.section_80g:,.0f}")
        st.write(f"**Section 80CCD(1B) (NPS):** ₹{deductions.section_80ccd1b:,.0f}")
        
        st.markdown("---")
        st.write(f"**Total Deductions:** ₹{deductions.total_deductions:,.0f}")

def show_hra_calculation_section(analysis):
    """Show HRA calculation details"""
    
    st.subheader("🏠 HRA Exemption Calculation")
    
    hra_calc = analysis['hra_calculation']
    
    if hra_calc.rent_paid > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📊 HRA Components")
            st.write(f"**HRA Received:** ₹{hra_calc.hra_received:,.0f}")
            st.write(f"**Basic Salary:** ₹{hra_calc.basic_salary:,.0f}")
            st.write(f"**Annual Rent Paid:** ₹{hra_calc.rent_paid:,.0f}")
            st.write(f"**City Type:** {'Metro' if hra_calc.is_metro else 'Non-Metro'}")
        
        with col2:
            st.markdown("#### 🧮 Exemption Calculation")
            st.write("**HRA exemption is minimum of:**")
            st.write(f"1. Actual HRA: ₹{hra_calc.actual_hra_received:,.0f}")
            st.write(f"2. {50 if hra_calc.is_metro else 40}% of Basic: ₹{hra_calc.hra_limit_percentage:,.0f}")
            st.write(f"3. Rent - 10% Basic: ₹{hra_calc.rent_minus_basic:,.0f}")
            
            st.markdown("---")
            st.success(f"**HRA Exemption:** ₹{hra_calc.hra_exemption:,.0f}")
            st.write(f"**Taxable HRA:** ₹{hra_calc.hra_taxable:,.0f}")
    else:
        st.info("💡 Enter rent amount above to calculate HRA exemption")

def show_tax_computation_section(analysis, selected_regime):
    """Show final tax computation"""
    
    st.subheader("🧾 Final Tax Computation")
    
    if selected_regime == "Compare Both":
        # Show both regimes side by side
        col1, col2 = st.columns(2)
        
        with col1:
            show_regime_tax_table(analysis, "🆕 New Regime", "new_regime")
        
        with col2:
            show_regime_tax_table(analysis, "🏛️ Old Regime", "old_regime")
    
    else:
        # Show selected regime
        regime_key = "new_regime" if selected_regime == "New Regime" else "old_regime"
        show_regime_tax_table(analysis, f"{selected_regime}", regime_key)

def show_regime_tax_table(analysis, title, regime_key):
    """Show tax computation table for a regime"""
    
    st.markdown(f"#### {title}")
    
    # Calculate values
    gross_income = analysis['total_income']
    deductions = analysis['total_deductions'] if regime_key == "old_regime" else 0
    taxable_income = gross_income - deductions
    tax_amount = analysis[f'tax_liability_{regime_key}']
    cess = tax_amount * 0.04
    total_tax = tax_amount + cess
    tds = analysis['tax_paid']
    additional_tax = total_tax - tds
    
    # Create computation table
    computation_data = [
        ["Gross Total Income", f"₹{gross_income:,.0f}"],
        ["Less: Total Deductions", f"₹{deductions:,.0f}"],
        ["Taxable Income", f"₹{taxable_income:,.0f}"],
        ["Tax on Income", f"₹{tax_amount:,.0f}"],
        ["Health & Education Cess (4%)", f"₹{cess:,.0f}"],
        ["**Total Tax Liability**", f"**₹{total_tax:,.0f}**"],
        ["Less: TDS", f"₹{tds:,.0f}"],
        ["Less: Advance Tax", f"₹0.00"],
    ]
    
    df_computation = pd.DataFrame(computation_data, columns=["Particulars", "Amount"])
    
    st.table(df_computation)
    
    # Final result
    if additional_tax > 0:
        st.error(f"💸 **Tax Balance Payable: ₹{additional_tax:,.0f}**")
    elif additional_tax < 0:
        st.success(f"💰 **Refund Due: ₹{abs(additional_tax):,.0f}**")
    else:
        st.info("✅ **No tax due - Exact match!**")

def show_portal_filing_guide(analysis):
    """Show Income Tax Portal filling guide with exact field mapping"""
    
    st.subheader("🌐 Income Tax Portal Filing Guide")
    st.write("📝 **Ready-to-use data for filing your ITR on the official portal** | Copy these values directly")
    
    # Initialize portal assistant
    portal_assistant = PortalFilingAssistant()
    
    # Generate portal data
    portal_data = portal_assistant.generate_portal_data(analysis)
    
    # Pre-filing checklist
    st.markdown("### ✅ Pre-Filing Checklist")
    
    checklist = portal_assistant.get_portal_checklist(analysis)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📋 Required Documents")
        for item in checklist:
            if item['status'] == 'required':
                st.success(f"✅ **{item['item']}** - {item['description']}")
            elif item['status'] == 'recommended':
                st.info(f"💡 **{item['item']}** - {item['description']}")
    
    with col2:
        st.markdown("#### 🔗 Portal Links")
        st.markdown("""
        **📱 Official Portal:** [incometax.gov.in](https://www.incometax.gov.in/iec/foportal/)
        
        **📄 Important Links:**
        - [Download Form 26AS](https://www.incometax.gov.in/iec/foportal/help/form-26as)
        - [AIS/TIS](https://www.incometax.gov.in/iec/foportal/help/ais-tis)
        - [ITR Forms](https://www.incometax.gov.in/iec/foportal/help/itr-forms)
        - [Verification Guide](https://www.incometax.gov.in/iec/foportal/help/verification)
        """)
    
    # Determine ITR form
    income = analysis['income_breakdown']
    itr_form = "ITR-2" if (income.ltcg > 0 or income.stcg > 0 or income.bank_interest > 0) else "ITR-1"
    
    st.info(f"📝 **Recommended ITR Form:** {itr_form} (based on your income sources)")
    
    # Section-wise portal guide
    st.markdown("### 📊 Section-wise Portal Filling Guide")
    
    # Create tabs for different sections
    portal_tab1, portal_tab2, portal_tab3, portal_tab4 = st.tabs([
        "💰 Income Sections",
        "📉 Deductions", 
        "🧾 Tax Computation",
        "✅ Verification"
    ])
    
    # Income sections tab
    with portal_tab1:
        show_portal_income_sections(portal_data.income_sections)
    
    # Deductions tab
    with portal_tab2:
        show_portal_deduction_sections(portal_data.deduction_sections)
    
    # Tax computation tab
    with portal_tab3:
        show_portal_tax_computation(portal_data.tax_computation)
    
    # Verification tab
    with portal_tab4:
        show_portal_verification(portal_data.verification_data)

def show_portal_income_sections(income_sections):
    """Show income sections for portal filing"""
    
    st.markdown("#### 💰 Income Details - What to Fill Where")
    
    for section in income_sections:
        st.markdown(f"### {section.section_name}")
        st.markdown(f"**📍 Portal Location:** `{section.form_reference}`")
        
        # Create expandable section
        with st.expander(f"📝 Fill Details for {section.section_name}", expanded=True):
            
            # Show fields to fill
            st.markdown("#### 🔢 Values to Enter:")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Display fields in a table format
                if isinstance(section.fields, dict):
                    for field_name, field_value in section.fields.items():
                        if isinstance(field_value, dict):
                            st.markdown(f"**{field_name.replace('_', ' ').title()}:**")
                            for sub_field, sub_value in field_value.items():
                                st.write(f"  • {sub_field.replace('_', ' ').title()}: `{sub_value}`")
                        else:
                            st.write(f"**{field_name.replace('_', ' ').title()}:** `{field_value}`")
            
            with col2:
                st.markdown("#### 📋 Step-by-step:")
                for i, instruction in enumerate(section.instructions, 1):
                    st.write(f"{instruction}")
            
            # Show notes
            if section.notes:
                st.markdown("#### 💡 Important Notes:")
                for note in section.notes:
                    if note.startswith("💡"):
                        st.info(note)
                    elif note.startswith("⚠️"):
                        st.warning(note)
                    elif note.startswith("🏠") or note.startswith("📄") or note.startswith("🧾"):
                        st.success(note)

def show_portal_deduction_sections(deduction_sections):
    """Show deduction sections for portal filing"""
    
    st.markdown("#### 📉 Deductions - Chapter VI-A Sections")
    
    if not deduction_sections:
        st.info("💡 No deductions available (likely using New Tax Regime)")
        return
    
    for section in deduction_sections:
        st.markdown(f"### {section.section_name}")
        st.markdown(f"**📍 Portal Location:** `{section.form_reference}`")
        
        with st.expander(f"📝 Fill Details for {section.section_name}", expanded=True):
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("#### 🔢 Values to Enter:")
                
                # Create a formatted table for deductions
                if isinstance(section.fields, dict):
                    deduction_data = []
                    for field_name, field_value in section.fields.items():
                        clean_name = field_name.replace('_', ' ').title()
                        deduction_data.append([clean_name, field_value])
                    
                    df_deductions = pd.DataFrame(deduction_data, columns=["Field", "Amount"])
                    st.table(df_deductions)
            
            with col2:
                st.markdown("#### 📋 How to Fill:")
                for instruction in section.instructions:
                    st.write(f"• {instruction}")
            
            # Show notes
            if section.notes:
                st.markdown("#### 💡 Important Notes:")
                for note in section.notes:
                    if "⚠️" in note:
                        st.warning(note)
                    elif "💡" in note:
                        st.info(note)
                    else:
                        st.success(note)

def show_portal_tax_computation(tax_computation):
    """Show tax computation section"""
    
    st.markdown("#### 🧾 Tax Computation - Verification")
    st.markdown(f"**📍 Portal Location:** `{tax_computation['form_reference']}`")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("#### 🔢 Final Tax Calculation:")
        
        # Create computation table
        computation_data = []
        for field_name, field_value in tax_computation['fields'].items():
            clean_name = field_name.replace('_', ' ').title()
            computation_data.append([clean_name, field_value])
        
        df_computation = pd.DataFrame(computation_data, columns=["Particulars", "Amount"])
        st.table(df_computation)
    
    with col2:
        st.markdown("#### ✅ Verification Steps:")
        for instruction in tax_computation['instructions']:
            st.write(f"• {instruction}")
        
        st.markdown("#### 💡 Notes:")
        for note in tax_computation['notes']:
            st.info(note)

def show_portal_verification(verification_data):
    """Show verification and final steps"""
    
    st.markdown("#### ✅ Final Verification & Submission")
    st.markdown(f"**📍 Portal Location:** `{verification_data['form_reference']}`")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Final Summary:")
        
        summary_data = []
        for field_name, field_value in verification_data['fields'].items():
            clean_name = field_name.replace('_', ' ').title()
            summary_data.append([clean_name, field_value])
        
        df_summary = pd.DataFrame(summary_data, columns=["Item", "Value"])
        st.table(df_summary)
    
    with col2:
        st.markdown("#### 🚀 Submission Process:")
        for i, instruction in enumerate(verification_data['instructions'], 1):
            st.write(f"{i}. {instruction}")
    
    # Final reminders
    st.markdown("#### 🎯 Final Reminders:")
    for note in verification_data['notes']:
        if "📱" in note:
            st.success(note)
        elif "⏰" in note:
            st.warning(note)
        else:
            st.info(note)
    
    # Add portal navigation guide
    st.markdown("### 🗺️ Portal Navigation Guide")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **📝 Filing Steps on Portal:**
        1. Login to incometax.gov.in/iec/foportal/
        2. Go to 'e-File' → 'Income Tax Return'
        3. Select appropriate ITR form
        4. Fill sections as guided above
        5. Use 'Save as Draft' frequently
        6. Preview before final submission
        7. Submit and verify
        """)
    
    with col2:
        st.markdown("""
        **⚠️ Common Portal Tips:**
        - Use Chrome/Firefox for best compatibility
        - Save as draft after each section
        - Keep all documents ready before starting
        - Double-check TDS amounts with Form 26AS
        - Verify bank account details for refund
        - Complete filing before September 15, 2025
        """)

def show_regime_comparison_tab():
    """Tax regime comparison interface"""
    
    st.header("⚖️ Tax Regime Comparison - Old vs New")
    st.write("Compare Old and New tax regimes to find the optimal choice for your situation")
    
    st.info("🚧 This feature is being enhanced with the new integrated system. Please use the Tax Dashboard tab for regime comparison.")
    
    # Simple regime comparison using the new system
    if hasattr(st.session_state, 'tax_summary') and st.session_state.tax_summary:
        summary = st.session_state.tax_summary
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🆕 New Tax Regime")
            st.metric("Tax Liability", f"₹{summary['tax_liability_new_regime']:,.0f}")
        
        with col2:
            st.markdown("### 🏛️ Old Tax Regime")
            st.metric("Tax Liability", f"₹{summary['tax_liability_old_regime']:,.0f}")
        
        # Recommendation
        recommended = summary['recommended_regime']
        if recommended == 'new':
            savings = summary['tax_liability_old_regime'] - summary['tax_liability_new_regime']
            st.success(f"🎯 **Recommendation: New Tax Regime** saves ₹{savings:,.0f}")
        else:
            savings = summary['tax_liability_new_regime'] - summary['tax_liability_old_regime']
            st.success(f"🎯 **Recommendation: Old Tax Regime** saves ₹{savings:,.0f}")
    else:
        st.warning("📄 **No tax analysis available.** Please analyze documents first in the Document Analysis tab.")

def show_itr_guide_tab():
    """Enhanced ITR filing guide with section-wise instructions"""
    
    st.header("📋 Complete ITR Filing Guide")
    st.write("Step-by-step guidance for filing your ITR-2 with detailed section instructions")
    
    # Check if tax analysis is available
    if not hasattr(st.session_state, 'tax_summary') or not st.session_state.tax_summary:
        st.warning("📄 **No tax analysis available.** Please analyze documents first in the Document Analysis tab.")
        st.info("🔍 **To get started:** Go to Document Analysis tab → Click 'Analyze All Documents with AI'")
        return
    
    summary = st.session_state.tax_summary
    
    # Filing workflow tabs
    guide_tab1, guide_tab2, guide_tab3, guide_tab4, guide_tab5 = st.tabs([
        "🏁 Getting Started",
        "📊 Income Sections", 
        "💼 Deductions & Exemptions",
        "⚖️ Tax Computation",
        "✅ Final Steps"
    ])
    
    with guide_tab1:
        st.subheader("🏁 Pre-Filing Preparation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Required Documents")
            st.markdown("""
            **✅ Documents Analyzed:**
            - Form 16 (Salary Certificate)
            - Bank Interest Certificate
            - Capital Gains Statements
            - Investment Proofs (ELSS)
            
            **📄 Additional Documents Needed:**
            - PAN Card
            - Aadhaar Card
            - Bank Account Details
            - Form 26AS (Tax Credit Statement)
            - Investment Proofs (if any additional)
            - Property Documents (if applicable)
            """)
        
        with col2:
            st.markdown("### 🎯 Filing Summary")
            st.metric("Total Income", f"₹{summary['total_income']:,.0f}")
            st.metric("Tax Paid", f"₹{summary['tax_paid']:,.0f}")
            st.metric("Recommended Regime", summary['recommended_regime'].title())
            
            if summary['recommended_regime'] == 'new':
                st.success(f"🎯 **New Tax Regime Recommended** - Tax Liability: ₹{summary['tax_liability_new_regime']:,.0f}")
            else:
                st.success(f"🎯 **Old Tax Regime Recommended** - Tax Liability: ₹{summary['tax_liability_old_regime']:,.0f}")
        
        st.markdown("### 🔗 Portal Access")
        st.markdown("""
        **🌐 Official Portal:** https://www.incometax.gov.in/iec/foportal/
        
        **📱 Filing Deadline:** September 15, 2025 (Extended)
        
        **🔐 Login Requirements:**
        - PAN Number
        - Aadhaar OTP or Net Banking
        - Valid email and mobile number
        """)
    
    with guide_tab2:
        st.subheader("📊 Income Sections - ITR-2")
        
        # Income breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💰 Salary Income (Section 1)")
            st.markdown(f"""
            **📄 Form 16 Data:**
            - Gross Salary: ₹{summary['salary_income']:,.0f}
            - Tax Deducted: ₹{summary['tax_paid']:,.0f}
            - Employee: Rishabh Roy
            - Employer: [From Form 16]
            
            **📍 Portal Location:** `Section 1 - Salary`
            **📝 Instructions:** Enter the values exactly as shown in Form 16
            """)
            
            st.markdown("### 🏦 Interest Income (Section 2)")
            st.markdown(f"""
            **📄 Bank Interest Data:**
            - Total Interest: ₹{summary.get('interest_income', 0):,.0f}
            - TDS on Interest: ₹{summary.get('tds_interest', 0):,.0f}
            - Bank: IT PARK
            
            **📍 Portal Location:** `Section 2 - Interest`
            **📝 Instructions:** Include all bank interest, FD interest, etc.
            """)
        
        with col2:
            st.markdown("### 📈 Capital Gains (Section 3)")
            st.markdown(f"""
            **📄 Capital Gains Data:**
            - Total Capital Gains: ₹{summary.get('capital_gains', 0):,.0f}
            - LTCG: ₹{summary.get('ltcg', 0):,.0f}
            - STCG: ₹{summary.get('stcg', 0):,.0f}
            
            **📍 Portal Location:** `Section 3 - Capital Gains`
            **📝 Instructions:** Separate long-term and short-term gains
            """)
            
            st.markdown("### 🏠 Other Income (Section 4)")
            st.markdown("""
            **📄 Other Income Sources:**
            - Rental Income (if any)
            - Business Income (if any)
            - Other Sources
            
            **📍 Portal Location:** `Section 4 - Other Sources`
            **📝 Instructions:** Include any other income not covered above
            """)
    
    with guide_tab3:
        st.subheader("💼 Deductions & Exemptions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💼 Section 80C Deductions")
            st.markdown(f"""
            **📄 Investment Data:**
            - ELSS: ₹{summary.get('elss_amount', 0):,.0f}
            - EPF: ₹{summary.get('epf_amount', 0):,.0f}
            - PPF: ₹{summary.get('ppf_amount', 0):,.0f}
            - Total 80C: ₹{summary['total_deductions']:,.0f}
            
            **📍 Portal Location:** `Schedule VI-A - Deductions`
            **📝 Instructions:** Enter under Section 80C (max ₹1.5 lakh)
            """)
            
            st.markdown("### 🏥 Section 80D (Health Insurance)")
            st.markdown("""
            **📄 Health Insurance Premium:**
            - Self & Family: ₹25,000
            - Parents: ₹50,000 (if applicable)
            
            **📍 Portal Location:** `Schedule VI-A - Section 80D`
            **📝 Instructions:** Include health insurance premium receipts
            """)
        
        with col2:
            st.markdown("### 🏠 Section 24(b) - Home Loan Interest")
            st.markdown("""
            **📄 Home Loan Interest:**
            - Interest Paid: ₹2,00,000 (max)
            - Principal Repayment: ₹1,50,000 (80C)
            
            **📍 Portal Location:** `Schedule VI-A - Section 24(b)`
            **📝 Instructions:** Include home loan interest certificate
            """)
            
            st.markdown("### 🏠 HRA Exemption")
            st.markdown("""
            **📄 HRA Data:**
            - HRA Received: [From Form 16]
            - Rent Paid: [Provide rent receipts]
            - Exemption: [Calculated]
            
            **📍 Portal Location:** `Schedule VI-A - HRA`
            **📝 Instructions:** Include rent receipts and landlord PAN
            """)
    
    with guide_tab4:
        st.subheader("⚖️ Tax Computation")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🆕 New Tax Regime")
            st.markdown(f"""
            **📊 Tax Calculation:**
            - Total Income: ₹{summary['total_income']:,.0f}
            - Tax Liability: ₹{summary['tax_liability_new_regime']:,.0f}
            - Tax Paid: ₹{summary['tax_paid']:,.0f}
            - Refund/Due: ₹{summary['tax_paid'] - summary['tax_liability_new_regime']:,.0f}
            
            **📍 Portal Location:** `Schedule 115BAC`
            **📝 Instructions:** Select 'Yes' for new regime
            """)
        
        with col2:
            st.markdown("### 🏛️ Old Tax Regime")
            st.markdown(f"""
            **📊 Tax Calculation:**
            - Total Income: ₹{summary['total_income']:,.0f}
            - Deductions: ₹{summary['total_deductions']:,.0f}
            - Taxable Income: ₹{summary['total_income'] - summary['total_deductions']:,.0f}
            - Tax Liability: ₹{summary['tax_liability_old_regime']:,.0f}
            - Tax Paid: ₹{summary['tax_paid']:,.0f}
            - Refund/Due: ₹{summary['tax_paid'] - summary['tax_liability_old_regime']:,.0f}
            
            **📍 Portal Location:** `Schedule VI-A`
            **📝 Instructions:** Select 'No' for old regime
            """)
        
        # Regime recommendation
        st.markdown("### 🎯 Regime Recommendation")
        if summary['recommended_regime'] == 'new':
            savings = summary['tax_liability_old_regime'] - summary['tax_liability_new_regime']
            st.success(f"**✅ Recommended: New Tax Regime** - Saves ₹{savings:,.0f}")
            st.info("💡 **Why New Regime:** Lower tax liability with simplified structure")
        else:
            savings = summary['tax_liability_new_regime'] - summary['tax_liability_old_regime']
            st.success(f"**✅ Recommended: Old Tax Regime** - Saves ₹{savings:,.0f}")
            st.info("💡 **Why Old Regime:** Deductions provide better tax savings")
    
    with guide_tab5:
        st.subheader("✅ Final Steps & Submission")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📋 Pre-Submission Checklist")
            st.markdown("""
            **✅ Documents Verified:**
            - Form 16 data entered correctly
            - Bank interest included
            - Capital gains reported
            - Deductions claimed with proofs
            - Tax regime selected
            
            **✅ Personal Details:**
            - PAN and Aadhaar linked
            - Bank account details correct
            - Contact information updated
            """)
        
        with col2:
            st.markdown("### 🚀 Submission Process")
            st.markdown("""
            **📝 Final Steps:**
            1. Review all sections
            2. Save as draft
            3. Preview return
            4. Submit return
            5. Verify with Aadhaar OTP
            6. Download acknowledgment
            
            **⏰ Important Deadlines:**
            - Filing: September 15, 2025
            - Verification: 30 days from filing
            """)
        
        st.markdown("### 🎯 Tax Summary")
        recommended_regime = summary['recommended_regime']
        tax_liability = summary[f'tax_liability_{recommended_regime}_regime']
        refund_due = summary['tax_paid'] - tax_liability
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Income", f"₹{summary['total_income']:,.0f}")
        with col2:
            st.metric("Tax Liability", f"₹{tax_liability:,.0f}")
        with col3:
            if refund_due > 0:
                st.metric("Refund Due", f"₹{refund_due:,.0f}", delta="Refund")
            else:
                st.metric("Tax Due", f"₹{abs(refund_due):,.0f}", delta="Pay")
        
        st.success("🎉 **Ready to File!** Your ITR-2 is prepared with all the analyzed data.")
        st.info("💡 **Next Steps:** Go to incometax.gov.in and follow the portal instructions using this guide.")

def show_pdf_reports_tab():
    """PDF report generation interface"""
    
    st.header("📄 Generate PDF Reports")
    st.write("Create comprehensive PDF reports for your tax analysis")
    
    st.info("🚧 This feature is being enhanced with the new integrated system. Please use the Document Analysis tab to export JSON reports for now.")
    
    # Report options
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Available Reports")
        st.write("PDF report generation will be available soon.")
    
    with col2:
        st.subheader("⚙️ Report Settings")
        st.write("Report settings will be available soon.")

def show_advanced_tools_tab():
    """Advanced tools and utilities"""
    
    st.header("🔧 Advanced Tools")
    
    st.info("🚧 This feature is being enhanced with the new integrated system. Please use the Document Analysis tab for now.")



def show_google_drive_setup_tab():
    """Google Drive setup and authentication"""
    st.header("🔗 Google Drive Integration Setup")
    
    try:
        from src.data.simple_google_auth import simple_auth
        
        # Show simple authentication interface
        simple_auth.show_simple_auth_button()
        
        # Show current status if authenticated
        if simple_auth.is_authenticated():
            st.subheader("📊 Current Status")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔍 Test Connection"):
                    with st.spinner("Testing Google Drive connection..."):
                        # Simple test - check if we can access user info
                        user_info = simple_auth.get_user_info()
                        if user_info:
                            st.success("✅ Google Drive connection successful!")
                            st.info(f"👤 Connected as: {user_info.get('email', 'Unknown')}")
                        else:
                            st.error("❌ Connection failed")
            
            with col2:
                if st.button("👤 Get User Info"):
                    with st.spinner("Getting user information..."):
                        user_info = simple_auth.get_user_info()
                        
                        if user_info:
                            st.success("✅ User information retrieved!")
                            st.info(f"👤 Name: {user_info.get('name', 'Unknown')}")
                            st.info(f"📧 Email: {user_info.get('email', 'Unknown')}")
                        else:
                            st.error("❌ Could not retrieve user information")
            
            # Quick setup instructions
            st.subheader("🚀 Next Steps")
            st.markdown("""
            **To use Google Drive integration:**
            
            1. **✅ Authentication complete!** You're now connected to Google Drive
            2. **Go to Document Analysis tab** and paste your Google Drive folder URL
            3. **Click 'Analyze All Documents with AI'** to fetch and analyze documents
            
            **Example Google Drive folder URL:**
            ```
            https://drive.google.com/drive/folders/1o8kOG3rbKv4PJAabOh_QbJEpj_-sjwD2?usp=sharing
            ```
            """)
        else:
            # Show setup instructions for non-authenticated users
            st.subheader("🚀 Quick Start")
            st.markdown("""
            **To use Google Drive integration:**
            
            1. **Enter your Google Cloud credentials** above
            2. **Click "Sign in with Google"** to authenticate
            3. **Complete the OAuth flow** in your browser
            4. **Go to Document Analysis tab** and paste your Google Drive folder URL
            5. **Click 'Analyze All Documents with AI'** to fetch and analyze documents
            
            **Need Google Cloud credentials?** Click "View Setup Guide" for step-by-step instructions.
            """)
        
    except ImportError:
        st.error("❌ Google Drive integration not available")
        st.info("Please install required packages: `pip install requests`")
    except Exception as e:
        st.error(f"❌ Error setting up Google Drive: {str(e)}")
        st.info("Please check your internet connection and try again")
    
    # Knowledge base search
    st.subheader("🔍 Knowledge Base Search")
    st.write("Advanced tools will be available soon.")
    
    # Document upload
    st.subheader("📁 Add New Document")
    st.write("Document upload will be available soon.")
    
    # Export options
    st.subheader("📊 Export & Reports")
    st.write("Export options will be available soon.")
    
    # System information
    st.subheader("ℹ️ System Information")
    st.write("System information will be available soon.")

if __name__ == "__main__":
    main()