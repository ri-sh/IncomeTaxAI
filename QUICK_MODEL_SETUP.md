# 🚀 Quick Model Setup - Virtual Environment

## **Problem Solved: External Environment Management**

Your system requires a virtual environment for package installation. Here's the complete setup:

---

## **Step 1: Create Virtual Environment**

```bash
# Create virtual environment
python3 -m venv tax_ai_env

# Activate it (you'll need to do this each time)
source tax_ai_env/bin/activate

# Your prompt should now show (tax_ai_env)
```

---

## **Step 2: Install All Dependencies**

```bash
# Install all required packages
pip install -r requirements.txt

# This will install:
# - transformers (Hugging Face models)
# - torch (PyTorch for AI)
# - accelerate (model optimization)
# - sentence-transformers (embeddings)
# - streamlit (web interface)
# - chromadb (vector database)
# - reportlab (PDF generation)
# - and all other dependencies
```

---

## **Step 3: Download AI Models**

```bash
# Now run the model setup
python setup_models.py

# Choose your option:
# 'y' - Download full GPT-OSS-20B model (~40GB)
# 's' - Download smaller alternative models (~500MB)
# 'n' - Skip model download (simulated responses)
```

---

## **Step 4: Launch Production System**

```bash
# Launch the enhanced system
python launch_production.py

# Access at: http://localhost:8501
```

---

## **Alternative: Quick Start Script**

Here's a complete setup script:

```bash
# One-command setup
echo "🚀 Setting up Income Tax AI Assistant..."

# Create and activate virtual environment
python3 -m venv tax_ai_env
source tax_ai_env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup models (you'll be prompted for choices)
python setup_models.py

# Launch system
python launch_production.py
```

---

## **What Models Will Be Downloaded:**

### **Essential (Always Downloaded):**
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (~90MB)
  - Used for document similarity and RAG retrieval
  - Required for document analysis features

### **Main Language Model (Choose One):**

#### **Option A: Full Power**
- **GPT-OSS-20B**: `openai/gpt-oss-20b` (~40GB, quantized to ~10GB)
- Best AI performance for tax queries
- Requires good internet and storage

#### **Option B: Lightweight**
- **DialoGPT-medium**: `microsoft/DialoGPT-medium` (~345MB)
- Good performance, faster download
- Recommended for most users

#### **Option C: Minimal**
- **No download**: Uses simulated responses
- All features work except real AI chat
- Instant setup

---

## **Next Session Commands:**

For future sessions, just remember:

```bash
# Activate environment
source tax_ai_env/bin/activate

# Launch system
python launch_production.py
```

---

## **What You'll Get After Setup:**

✅ **Real AI Models** from Hugging Face  
✅ **Document Classification** with confidence scores  
✅ **Tax Query Processing** with actual AI responses  
✅ **Embedding-based Retrieval** for document analysis  
✅ **Vector Database** with ChromaDB  
✅ **Professional PDF Reports** with AI insights  
✅ **Regime Comparison** with real calculations  
✅ **Section-wise Filing Guide** with AI enhancement  

Your system will transform from simulated to **real AI-powered tax assistance**! 🤖✨

---

**Ready to set up the real AI models?** 
Run the commands above to get your production-grade tax assistant with actual Hugging Face models!