# 🇮🇳 Income Tax AI Assistant - Complete AI Solution

An intelligent AI-powered assistant for Indian income tax filing using **GPT-OSS-20B**, **LlamaIndex RAG**, and **advanced document recognition**. This comprehensive system provides conversational tax advice, automatic document analysis, and personalized filing recommendations.

## ✨ Key Features

### 📁 **Multi-Source Document Fetching**
- **Local Folder**: Automatically scan `Desktop/Income Tax 2024-2025`
- **Google Drive**: Fetch documents from your Google Drive
- **Manual Upload**: Drag-and-drop interface
- **Smart Classification**: Auto-detect document types

### 🔍 **Missing Document Detection**
- Comprehensive checklist for ITR-1, ITR-2, ITR-3, ITR-4
- Priority-based recommendations (Mandatory → Recommended → Optional)
- Tax-saving opportunity alerts
- Completion percentage tracking

### 📄 **Document Processing**
- **Form 16/16A**: Extract salary, TDS, employer details
- **Bank Statements**: Interest income, transaction analysis
- **Investment Documents**: LIC, ELSS, PPF, EPF receipts
- **Insurance**: Health insurance, term insurance premiums
- **Property**: Home loan interest, rent receipts
- **OCR Support**: Process scanned documents and images

### 🧮 **Tax Calculation Engine**
- **Dual Tax Regime**: Compare New vs Old regime
- **Deduction Calculator**: Section 80C, 80D, HRA, LTA
- **Tax Optimization**: Recommend best tax-saving strategies
- **ITR Form Generation**: Auto-fill ITR forms with extracted data

### 🤖 **Advanced AI Capabilities**
- **GPT-OSS-20B Integration**: Natural language understanding for tax questions
- **LlamaIndex RAG**: Intelligent document retrieval and context-aware responses
- **AI Document Classification**: Automatic recognition of document types and intent
- **Conversational Interface**: Chat with your tax assistant in plain English
- **Personalized Advice**: AI generates recommendations based on your documents
- **Confidence Scoring**: Shows AI confidence in responses and classifications
- **Knowledge Base**: Pre-loaded with Indian tax laws and ITR requirements
- **Context Integration**: Combines your documents with tax law knowledge
- **🛡️ Tax-Only Behavior**: Strictly refuses non-tax questions with 100% accuracy
- **Professional Boundaries**: Maintains focus on Indian income tax matters only

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd IncomeTax.ai

# Install dependencies
pip install -r requirements.txt
```

### 1.5. Launch AI Interface

```bash
# Launch the complete AI-powered web interface
streamlit run src/ui/streamlit_app.py

# Or run the AI capabilities demo
python3 simple_ai_demo.py

# Access the web interface at:
# http://localhost:8501
```

### 2. Setup Your Documents

Create the folder structure on your Desktop:
```
Desktop/
└── Income Tax 2024-2025/
    ├── Salary Documents/
    │   ├── Form 16.pdf
    │   └── Salary Slips/
    ├── Bank Documents/
    │   ├── Bank Statements/
    │   └── Interest Certificates/
    ├── Investments/
    │   ├── LIC/
    │   ├── ELSS/
    │   ├── PPF/
    │   └── EPF/
    ├── Insurance/
    │   ├── Health Insurance/
    │   └── Term Insurance/
    └── House Property/
        ├── Home Loan/
        └── Rent Receipts/
```

### 3. Run the Demo

```bash
python demo.py
```

This will:
- Scan your documents folder
- Detect document types
- Show missing document analysis
- Process sample documents
- Provide recommendations

### 4. Google Drive Integration (Optional)

To enable Google Drive document fetching:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create OAuth 2.0 credentials for Desktop application
5. Download `credentials.json` and place in project root
6. Run the demo - it will handle authentication

### 5. Run Full Application

```bash
streamlit run src/ui/main_app.py
```

## 📋 Document Checklist

### 🚨 **Mandatory Documents**
- **Form 16** - TDS certificate from employer
- **PAN Card** - Tax identification
- **Bank Statements** - Income verification

### ⚠️ **Highly Recommended (Tax-Saving)**
- **LIC Premium Receipts** - Section 80C (up to ₹1.5L)
- **ELSS Statements** - Section 80C equity investments
- **PPF/EPF Statements** - Section 80C retirement savings
- **Health Insurance Premium** - Section 80D (up to ₹75K)
- **Home Loan Interest** - Section 24 (up to ₹2L)
- **Interest Certificates** - Bank/FD interest income

### 💡 **Optional (Additional Deductions)**
- **Education Loan Interest** - Section 80E (no limit)
- **Donation Receipts** - Section 80G charitable donations
- **Capital Gains Statements** - If you sold investments
- **Rent Receipts** - HRA exemption claim

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Layer    │    │  Document       │    │   Core Tax      │
│                 │    │  Processing     │    │   Engine        │
│ • Streamlit UI  │◄──►│ • PDF Parser    │◄──►│ • Tax Calculator│
│ • Chat Interface│    │ • Excel Reader  │    │ • ITR Forms     │
│ • Form Wizard   │    │ • OCR Engine    │    │ • Validation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │    │   AI/ML Layer   │    │ Knowledge Base  │
│                 │    │                 │    │                 │
│ • Local Folder  │    │ • GPT-OSS-20B   │    │ • Tax Laws      │
│ • Google Drive  │    │ • LlamaIndex    │    │ • ITR Forms     │
│ • Manual Upload │    │ • RAG Pipeline  │    │ • ChromaDB      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📊 Example Output

```
🇮🇳 Income Tax AI Assistant - Demo
==================================================
📋 Initializing components...
📁 Looking for documents in: /Users/username/Desktop/Income Tax 2024-2025
📥 Fetching documents from all sources...

📊 Document Summary:
   Total documents found: 12
   Local folder: 12
   Google Drive: 0
   Manual upload: 0

📋 Detected document types:
   • form_16: 1
   • bank_statements: 3
   • lic_premium_receipts: 2
   • interest_certificates: 2

📈 Document Checklist Analysis:
   Completion: 68.2%
   Missing mandatory: 0
   Missing recommended: 5
   Missing optional: 8

💡 Missing Document Suggestions:
   ⚠️  Important documents that could save you tax:
   • ELSS Investment Statements (Save up to ₹150,000): Equity Linked Savings Scheme
   • PPF Account Statements (Save up to ₹150,000): Public Provident Fund statements
   • Health Insurance Premium Receipts (Save up to ₹75,000): Medical insurance premiums

🎯 Recommendations:
   👍 Good progress! 68% complete. Add recommended documents to maximize tax savings.
   🔍 Please verify these documents manually: unclear_receipt.jpg
```

## 🔧 Configuration

Edit `config/config.py` to customize:

```python
# Model settings
model_config.reasoning_level = "medium"  # low, medium, high
model_config.temperature = 0.1  # For consistent tax calculations

# Document processing
vectordb_config.chunk_size = 512
vectordb_config.chunk_overlap = 50

# Application settings
app_config.max_chat_history = 20
```

## 🎯 Tax Features

### **New vs Old Tax Regime Comparison**
- Automatically calculates both regimes
- Recommends optimal choice
- Shows potential savings

### **Section-wise Deductions**
- **80C**: LIC, ELSS, PPF, EPF (₹1.5L limit)
- **80D**: Health insurance (₹25K + ₹50K for parents)
- **24**: Home loan interest (₹2L for self-occupied)
- **HRA**: House rent allowance exemption
- **80E**: Education loan interest (no limit)
- **80G**: Charitable donations

### **ITR Form Support**
- **ITR-1 (Sahaj)**: Salary + house property + other sources
- **ITR-2**: Multiple income sources + capital gains
- **ITR-3**: Business/professional income
- **ITR-4 (Sugam)**: Presumptive taxation

## 🤖 AI Chat Examples

```
User: "How much can I save under Section 80C?"
AI: "Under Section 80C, you can claim deductions up to ₹1.5 lakh per financial year. 
    Based on your documents, I found:
    • LIC premiums: ₹24,000
    • EPF contribution: ₹45,000
    • ELSS investments: ₹0 (Missing - consider investing ₹81,000 more)
    
    Potential additional tax savings: ₹24,840 (if in 30.9% tax bracket)"

User: "Should I choose new or old tax regime?"
AI: "Based on your income and deductions:
    • Old Regime Tax: ₹1,45,800
    • New Regime Tax: ₹1,89,000
    
    Recommendation: Choose Old Regime and save ₹43,200
    This is mainly due to your Section 80C deductions and HRA exemption."
```

## 🛠️ Development

### Project Structure
```
IncomeTax.ai/
├── src/
│   ├── core/               # Core business logic
│   │   ├── document_checklist.py    # Missing document detection
│   │   └── tax_calculator.py        # Tax calculation engine
│   ├── models/             # AI/ML models
│   │   ├── llm_integration.py       # GPT-OSS-20B integration
│   │   └── embeddings.py            # Vector embeddings
│   ├── data/               # Data processing
│   │   ├── document_processor.py    # Document parsing
│   │   ├── google_drive_integration.py  # Cloud storage
│   │   └── multi_source_fetcher.py  # Unified document fetching
│   └── ui/                 # User interface
│       └── streamlit_app.py         # Web interface
├── data/
│   ├── tax_documents/      # Knowledge base documents
│   └── knowledge_base/     # Vector database
├── config/                 # Configuration files
├── tests/                  # Unit tests
└── demo.py                 # Demo application
```

### Adding New Document Processors
1. Create processor in `src/data/document_processor.py`
2. Add patterns to `DocumentClassifier`
3. Update `document_checklist.py` with new document types
4. Test with sample documents

### Extending Tax Calculations
1. Add new sections in `tax_calculator.py`
2. Update knowledge base with latest tax laws
3. Test calculations with sample data

## 🐛 Troubleshooting

### Common Issues

1. **"Google Drive authentication failed"**
   ```bash
   # Download credentials.json from Google Cloud Console
   # Place in project root and run demo again
   ```

2. **"No documents found"**
   ```bash
   # Check folder exists: ~/Desktop/Income Tax 2024-2025
   # Verify supported file formats: PDF, Excel, images
   ```

3. **"OCR not working"**
   ```bash
   pip install pytesseract
   # On macOS: brew install tesseract
   # On Ubuntu: sudo apt-get install tesseract-ocr
   ```

4. **"Model download failed"**
   ```bash
   # Ensure sufficient disk space (20GB+)
   # Check internet connection
   # Try running with --model-cache-dir flag
   ```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your changes
4. Write tests
5. Submit a pull request

## 💬 Support

- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions in GitHub Discussions
- **Email**: Contact the maintainers

---

**Disclaimer**: This tool is for assistance only. Please verify all tax calculations with a qualified CA or tax advisor before filing your returns. Tax laws may change, and this tool may not reflect the latest updates.

**Privacy**: All document processing happens locally on your machine. No sensitive data is sent to external servers.