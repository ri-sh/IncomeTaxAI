# 🤖 Ollama on Railway Setup Guide

This guide covers deploying Ollama AI models on Railway to work with our IncomeTax AI system.

## 🎯 Overview

Since our IncomeTax AI uses **native Ollama** (not containerized), we need to deploy Ollama as a separate service on Railway that can be accessed via HTTP API.

## 🚀 Quick Setup (Recommended)

### Option 1: One-Click Railway Template

1. **Deploy Ollama Template**
   ```bash
   # Use Railway's official Ollama template
   railway add --template T9CQ5w
   ```

2. **Configure for Network Access**
   ```bash
   # Switch to Ollama service
   railway service switch ollama
   
   # Set environment variables
   railway variables set OLLAMA_HOST=0.0.0.0
   railway variables set OLLAMA_PORT=11434
   railway variables set OLLAMA_KEEP_ALIVE=5m
   railway variables set OLLAMA_NUM_PARALLEL=4
   ```

3. **Deploy Models**
   ```bash
   # Wait for service to be ready, then pull models
   railway run ollama pull qwen2.5:3b
   railway run ollama pull qwen2.5:7b  # Optional larger model
   ```

4. **Get Service URL**
   ```bash
   # Get your Ollama service URL
   OLLAMA_URL=$(railway url)
   echo "Ollama Service URL: $OLLAMA_URL"
   ```

## 🔧 Manual Railway Ollama Setup

### Step 1: Create Ollama Dockerfile

Create `Dockerfile.ollama`:

```dockerfile
FROM ollama/ollama:latest

# Set environment variables for network access
ENV OLLAMA_HOST=0.0.0.0
ENV OLLAMA_PORT=11434
ENV OLLAMA_KEEP_ALIVE=5m
ENV OLLAMA_NUM_PARALLEL=4

# Expose port
EXPOSE 11434

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/api/tags || exit 1

# Start Ollama server
CMD ["ollama", "serve"]
```

### Step 2: Deploy to Railway

```bash
# Create new Railway project for Ollama
railway init ollama-service

# Deploy using custom Dockerfile
railway up --dockerfile Dockerfile.ollama
```

### Step 3: Download Models

```bash
# Connect to your Ollama service
railway shell

# Download required models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b

# Verify models
ollama list
```

## 🌐 External Ollama Setup

### Option 1: DigitalOcean Droplet

1. **Create Droplet**
   ```bash
   # Ubuntu 22.04 LTS, 4GB RAM minimum
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Configure for Network Access**
   ```bash
   # Edit systemd service
   sudo systemctl edit ollama.service
   
   # Add override configuration:
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0"
   Environment="OLLAMA_PORT=11434"
   
   # Restart service
   sudo systemctl daemon-reload
   sudo systemctl restart ollama
   ```

3. **Security Setup**
   ```bash
   # Configure firewall
   sudo ufw allow 11434/tcp
   sudo ufw enable
   
   # Optional: Setup nginx reverse proxy with SSL
   sudo apt install nginx certbot python3-certbot-nginx
   ```

### Option 2: AWS EC2

1. **Launch EC2 Instance**
   ```bash
   # t3.medium or larger, Ubuntu 22.04
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Configure Service**
   ```bash
   # Edit /etc/systemd/system/ollama.service
   sudo nano /etc/systemd/system/ollama.service
   
   # Add Environment variables:
   Environment="OLLAMA_HOST=0.0.0.0"
   Environment="OLLAMA_PORT=11434"
   ```

3. **Security Groups**
   - Allow inbound traffic on port 11434
   - Restrict to specific IP ranges if possible

## 🔗 Connecting to IncomeTax AI

### Set Environment Variables in Main App

```bash
# Switch back to your main app
railway service switch incometax-ai

# Set Ollama connection
railway variables set OLLAMA_BASE_URL=https://your-ollama-service.railway.app
railway variables set OLLAMA_MODEL=qwen2.5:3b

# Test connection
railway run python -c "
import requests
response = requests.get('${OLLAMA_BASE_URL}/api/tags')
print('Ollama Status:', response.status_code)
print('Available Models:', response.json())
"
```

## 🧪 Testing Ollama Connection

### Health Check Script

Create `test_ollama.py`:

```python
import os
import requests
from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer

def test_ollama_connection():
    """Test Ollama service connection"""
    ollama_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        # Test basic connectivity
        response = requests.get(f"{ollama_url}/api/tags", timeout=30)
        print(f"✅ Ollama connected: {ollama_url}")
        print(f"Available models: {[m['name'] for m in response.json().get('models', [])]}")
        
        # Test document analyzer
        analyzer = OllamaDocumentAnalyzer()
        print(f"✅ Analyzer initialized: {analyzer.model_name}")
        
        # Test inference
        test_result = analyzer.classify_document("Test document content")
        print(f"✅ Inference test: {test_result}")
        
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

if __name__ == "__main__":
    test_ollama_connection()
```

Run the test:
```bash
railway run python test_ollama.py
```

## 📊 Monitoring & Performance

### Railway Metrics

Monitor your Ollama service:
- CPU usage (should be high during inference)
- Memory usage (8GB+ for 7B models)
- Network traffic
- Response times

### Model Performance

```bash
# Check model response times
railway run ollama run qwen2.5:3b "What is tax deduction?"

# Monitor resource usage
railway metrics
```

## 💰 Cost Optimization

### Model Size vs Performance

| Model | RAM Required | Speed | Accuracy | Cost |
|-------|-------------|-------|----------|------|
| qwen2.5:3b | 4GB | Fast | Good | Low |
| qwen2.5:7b | 8GB | Medium | Better | Medium |
| qwen2.5:14b | 16GB | Slow | Best | High |

### Railway Pricing

- **Starter Plan**: $5/month, good for 3B models
- **Pro Plan**: $20/month, suitable for 7B models
- **Team Plan**: Custom pricing for 14B+ models

## 🔒 Security Considerations

### API Security

1. **Network Restrictions**
   ```bash
   # Only allow connections from your main app
   railway variables set ALLOWED_ORIGINS=https://your-main-app.railway.app
   ```

2. **Authentication (Optional)**
   ```bash
   # Add basic auth if needed
   railway variables set OLLAMA_API_KEY=your-secret-key
   ```

### Data Privacy

- Models run on Railway infrastructure
- No data sent to external AI services
- Full privacy engine compatibility
- GDPR compliant when configured properly

## 🛠️ Troubleshooting

### Common Issues

1. **Model Not Found**
   ```bash
   # List available models
   railway run ollama list
   
   # Pull missing model
   railway run ollama pull qwen2.5:3b
   ```

2. **Connection Timeout**
   ```bash
   # Check service status
   railway status
   
   # Check logs
   railway logs
   ```

3. **Out of Memory**
   ```bash
   # Check resource usage
   railway metrics
   
   # Upgrade plan or use smaller model
   railway variables set OLLAMA_MODEL=qwen2.5:3b
   ```

## 📚 Useful Commands

```bash
# Service management
railway status
railway logs
railway metrics
railway shell

# Model management
railway run ollama list
railway run ollama pull qwen2.5:3b
railway run ollama rm old-model

# Testing
railway run curl http://localhost:11434/api/tags
railway run python test_ollama.py

# Scaling
railway service scale --replicas 2
railway service scale --memory 8GB
```

## 🎯 Production Checklist

- [ ] Ollama service deployed and accessible
- [ ] Required models downloaded (qwen2.5:3b minimum)
- [ ] Health checks passing
- [ ] Connection tested from main app
- [ ] Resource limits configured
- [ ] Monitoring set up
- [ ] Backup strategy for models
- [ ] Security settings verified