# 🤖 AI Model Setup Guide

## Overview

Your Income Tax AI Assistant uses advanced AI models for document analysis and tax query processing. This guide helps you download and set up the required models.

---

## 🚀 **Quick Start**

### **Automatic Setup (Recommended)**
```bash
# Run the automated model setup
python setup_models.py
```

### **Alternative: Run during launch**
```bash
# Launch production system (will offer model setup)
python launch_production.py
```

---

## 🤖 **Models Used**

### **1. Main Language Model**
- **Model**: GPT-OSS-20B (`openai/gpt-oss-20b`)
- **Size**: ~40GB (quantized to ~10GB)
- **Purpose**: Tax question answering and document analysis
- **Optional**: System works with simulated responses if not available

### **2. Embedding Model**
- **Model**: SentenceTransformers (`sentence-transformers/all-MiniLM-L6-v2`)
- **Size**: ~90MB
- **Purpose**: Document similarity and RAG retrieval
- **Required**: Essential for document analysis

### **3. Alternative Models**
If GPT-OSS-20B is too large, smaller alternatives are available:
- **DialoGPT-medium** (~345MB)
- **DialoGPT-small** (~117MB)
- **GPT2-medium** (~345MB)

---

## 📦 **Model Setup Options**

### **Option 1: Full Setup (Recommended)**
Downloads all models including GPT-OSS-20B:
```bash
python setup_models.py
# Choose 'y' when asked about GPT-OSS-20B
```

**Pros:** Full AI capabilities, best performance  
**Cons:** Large download (40GB+), requires good internet and storage

### **Option 2: Lightweight Setup**
Downloads only essential models:
```bash
python setup_models.py
# Choose 's' for smaller alternative models
```

**Pros:** Fast download (~500MB), good performance  
**Cons:** Limited compared to full model

### **Option 3: Minimal Setup**
Skip main language model, use simulated responses:
```bash
python setup_models.py
# Choose 'n' to skip main model download
```

**Pros:** Very fast setup, all features except AI chat work  
**Cons:** AI responses are simulated, not real

---

## 🔧 **Technical Requirements**

### **Hardware Requirements**
- **Minimum RAM**: 8GB (for alternative models)
- **Recommended RAM**: 16GB+ (for GPT-OSS-20B)
- **Storage**: 50GB free space (for full setup)
- **GPU**: Optional (CUDA-compatible for faster performance)

### **Software Requirements**
- **Python**: 3.8+
- **PyTorch**: Automatically installed
- **Transformers**: Automatically installed
- **Internet**: Required for initial download

---

## 📁 **Model Storage Structure**

After setup, models are stored in:
```
models/
├── gpt-oss-20b/           # Main language model
├── embeddings/            # Embedding model cache
├── microsoft_DialoGPT*/   # Alternative models
└── config.json           # Model configuration

config/
└── models.json           # System model configuration
```

---

## 🔍 **Setup Process Details**

### **Step 1: Requirements Check**
- Verifies Python packages
- Installs missing dependencies
- Checks system capabilities

### **Step 2: Configuration**
- Creates model directories
- Sets up configuration files
- Initializes vector database

### **Step 3: Embedding Model**
- Downloads sentence transformer model
- Tests embedding functionality
- Configures LlamaIndex integration

### **Step 4: Main Language Model**
- Downloads chosen language model
- Applies 4-bit quantization (GPU)
- Tests model functionality

### **Step 5: Verification**
- Tests all models
- Updates configuration
- Reports setup status

---

## ⚙️ **Configuration Options**

### **Quantization (GPU Only)**
- **4-bit quantization**: Reduces memory usage by ~75%
- **Automatic**: Applied when CUDA is available
- **Benefits**: Fits larger models in limited GPU memory

### **Device Selection**
- **CUDA**: Automatic if available (fastest)
- **CPU**: Fallback option (slower but works everywhere)
- **Auto**: System automatically chooses best option

---

## 🚨 **Troubleshooting**

### **Common Issues**

#### **"Model download failed"**
- **Cause**: Network timeout or insufficient storage
- **Solution**: Check internet connection and free space
- **Alternative**: Choose smaller model option

#### **"CUDA out of memory"**
- **Cause**: GPU memory insufficient
- **Solution**: Enable quantization or use CPU
- **Alternative**: Use smaller alternative models

#### **"Permission denied"**
- **Cause**: Insufficient write permissions
- **Solution**: Check directory permissions
- **Alternative**: Run with elevated permissions

#### **"Package not found"**
- **Cause**: Missing dependencies
- **Solution**: Run `pip install -r requirements.txt`
- **Alternative**: Install packages manually

### **Error Recovery**
If setup fails:
1. Delete partial downloads: `rm -rf models/`
2. Clear configuration: `rm -rf config/models.json`
3. Restart setup: `python setup_models.py`

---

## 📊 **Performance Expectations**

### **Download Times** (typical broadband)
- **Embedding Model**: 1-2 minutes
- **Alternative Models**: 5-10 minutes
- **GPT-OSS-20B**: 30-60 minutes

### **Memory Usage**
- **Embedding Model**: ~500MB RAM
- **Alternative Models**: ~2GB RAM
- **GPT-OSS-20B (quantized)**: ~12GB RAM
- **GPT-OSS-20B (full)**: ~40GB RAM

### **Performance**
- **With GPU**: Fast inference (<1 second)
- **CPU Only**: Slower inference (5-10 seconds)
- **Alternative Models**: Good performance, shorter responses

---

## 🎯 **Model Selection Guide**

### **Choose GPT-OSS-20B if:**
- You have 16GB+ RAM
- You want best AI performance
- You can wait for large download
- You have good internet connection

### **Choose Alternative Models if:**
- You have 8-16GB RAM
- You want quick setup
- You need basic AI functionality
- You have limited internet bandwidth

### **Choose Simulated Mode if:**
- You have <8GB RAM
- You want immediate setup
- You primarily need regime comparison
- You don't need AI chat features

---

## 📞 **Support**

### **Model Issues**
- Check `MODEL_SETUP_GUIDE.md` (this file)
- Review error messages carefully
- Try alternative model options
- Clear cache and restart if needed

### **System Requirements**
- Verify hardware requirements
- Check Python version compatibility
- Ensure sufficient storage space
- Confirm internet connectivity

### **Advanced Users**
- Manual model download possible
- Custom model paths supported
- Configuration files are JSON-editable
- Docker deployment supported

---

## ✅ **Post-Setup Verification**

After successful setup:

1. **Check Status**: `python -c "import json; print(json.load(open('config/models.json')))"`
2. **Test Models**: Launch system and verify AI responses
3. **Monitor Performance**: Check response times and accuracy
4. **Review Logs**: Check for any warning messages

---

## 🚀 **Next Steps**

After model setup:
1. **Launch System**: `python launch_production.py`
2. **Test Features**: Try document analysis and tax queries
3. **Generate Reports**: Create PDF reports with AI insights
4. **Monitor Usage**: Review AI responses for accuracy

Your AI-powered Income Tax Assistant is now ready with full model support! 🇮🇳✨

---

*Generated: August 2025 | Income Tax AI Assistant | Model Setup Guide*