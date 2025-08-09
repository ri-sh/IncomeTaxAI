# 🇮🇳 Income Tax AI Assistant (FY 2024-25)

AI-powered assistant for Indian income tax filing using **GPT-OSS-20B**, **LlamaIndex RAG**, and robust document processing. Provides document analysis, regime comparison, PDF reports, and a Streamlit UI.

## ✨ Key Features

### 📁 Multi-Source Document Fetching
- **Local Folder**: Auto-scan `~/Desktop/Income Tax 2024-2025`
- **Google Drive**: Fetch documents from your Drive
- **Manual Upload**: Drag-and-drop
- **Smart Classification**: Auto-detect document types

### 🔍 Missing Document Detection
- ITR-1/2/3/4 checklists with priorities
- Tax-saving opportunity alerts and completion tracking

### 📄 Document Processing
- Form 16/16A, bank statements, interest certificates
- Investments: LIC, ELSS, PPF, EPF; Insurance; Home loan
- OCR support for scanned PDFs/images

### 🧮 Tax Calculation Engine
- Old vs New regime comparison with recommendations
- Section-wise deductions (80C, 80D, HRA, LTA, 24b, etc.)
- PDF report generation

### 🤖 Advanced AI
- OLLAMA
- Tax-only, professional responses
- Confidence scoring and knowledge-base integration

## 🚀 Install & Run

### 1) Requirements
- Python 3.8+
- macOS/Linux/Windows
- Optional: `tesseract-ocr` for OCR (macOS: `brew install tesseract`)

### 2) Create a virtual environment (recommended)
```bash
python3 -m venv tax_ai_env
source tax_ai_env/bin/activate  # Windows: tax_ai_env\Scripts\activate
```

### 3) Install dependencies
```bash
pip install -r requirements.txt
```

If your system is “externally managed” (pip install blocked), follow `QUICK_MODEL_SETUP.md`.

### 4) Install Ollama (required) and pull model

The app uses Ollama locally at `http://localhost:11434` with model `llama2`.

macOS (Homebrew):
```bash
brew install ollama
ollama pull llama2
# Optional: test run (downloads if not pulled)
ollama serve

#opne new terminal and run 
ollama run llama2
```

Linux:
```bash
curl -fsSL https://ollama.com/install.sh | sh
# Start service (systemd) or run in foreground
sudo systemctl enable --now ollama || ollama serve &
ollama pull llama2
```

Verify:
```bash
ollama list
# Ensure 'llama2' is listed and server is running on :11434
```

Change model (optional): Update `model="llama2"` in `src/core/ollama_document_analyzer.py` and `src/models/llamaindex_rag.py`.

### 5) (Optional) Download Hugging Face models
```bash
# Guided setup (recommended)
python setup_models.py


```
- Full model: GPT-OSS-20B (~40GB, quantized) for best AI.
- Lightweight options available during setup. See `MODEL_SETUP_GUIDE.md`.

### 6) Start the app
```bash
# Production launcher (checks deps, sets up dirs, starts Streamlit)
python launch_production.py

# Or directly run Streamlit UI
streamlit run src/ui/streamlit_app.py
```
Open `http://localhost:8501`.

## 📂 Prepare Your Documents
Create the folder on your Desktop (auto-detected):
```
~/Desktop/
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

## 🧭 How to Use
1. Start the app (see above) and open the web UI.
2. On “Document Analysis”, select your documents folder or upload files.
3. Review detected document types and missing-document checklist.
4. Go to “Regime Comparison” to compare Old vs New and get recommendations.
5. Use “Tax Assistant Chat” for tax-only guidance.
6. Generate professional PDF reports from the “PDF Reports” tab.

## 🔑 Google Drive (optional)
1. Create OAuth credentials (Desktop app) in Google Cloud Console.
2. Download `credentials.json` and place it in the project root.
3. First launch will prompt for authorization and save `google_token.json`.
See `GOOGLE_DRIVE_OAUTH_SETUP.md` for step-by-step instructions.

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

## 🏗️ Architecture (high level)

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
Edit `config/config.py` to customize model, vector DB, and app options (title, temperature, chunk sizes, chat history). Environment vars supported: `MODEL_CACHE_DIR`, `DATA_DIR`, `LOG_LEVEL`.

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
│   ├── core/                  # Core logic (calculations, analysis)
│   ├── data/                  # Data ingestion & integrations
│   ├── models/                # LLMs and embeddings
│   └── ui/                    # Streamlit interface
├── data/
│   ├── tax_documents/         # Knowledge base docs
│   └── knowledge_base/        # Vector DB (ChromaDB)
├── config/                    # Configuration
└── tests/                     # Unit tests
```

### Adding New Document Processors
1. Add logic in `src/data/document_processor.py`
2. Update classification rules where needed
3. Extend `src/core/document_checklist.py`
4. Test with sample docs

### Extending Tax Calculations
1. Add sections in `src/core/tax_calculator.py`
2. Update knowledge base docs under `data/tax_documents/`
3. Add tests in `tests/`

## 🐛 Troubleshooting

- **Externally managed Python (pip blocked)**: Use a virtualenv. See `QUICK_MODEL_SETUP.md`.
- **No documents found**: Verify `~/Desktop/Income Tax 2024-2025` exists and contains PDFs/Excel/images.
- **OCR not working**: `pip install pytesseract` and install system `tesseract` (macOS: `brew install tesseract`).
- **Model download failed**: Ensure 20GB+ free space (full model), stable internet, or choose lightweight models in `setup_models.py`.
- **Google Drive auth**: Place `credentials.json` in project root and re-run. See `GOOGLE_DRIVE_OAUTH_SETUP.md`.

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