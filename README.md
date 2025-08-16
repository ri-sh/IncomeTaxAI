# IncomeTax AI

AI-powered tax document analysis and calculation system for Indian income tax returns.

## 🚀 Quick Setup

### System Requirements
- **OS**: macOS, Linux, or Windows
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: 10GB free space
- **Docker**: Docker and Docker Compose
- **Internet**: For downloading AI models

### Installation

#### 1. Install Ollama and Llama3 Model
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows - Download from https://ollama.ai/download
```

Start Ollama and download the AI model:
```bash
ollama serve
ollama pull llama3:8b
```

#### 2. Clone and Run
```bash
git clone <your-repo-url>
cd incometax_project
./setup_hybrid.sh
```

## 🌐 Access Your Application

Open your browser and go to:
**http://localhost:8000**

## 📊 Monitor Processing

View background task processing at:
**http://localhost:5555**

## 🛑 Stop Services

```bash
# Stop Docker services
docker-compose -f docker-compose.cpu.yml down

# Stop Ollama (if needed)
killall ollama
```

## 🔄 Restart Docker Containers

### Restart All Services
```bash
# Stop and restart everything
docker-compose -f docker-compose.cpu.yml down
docker-compose -f docker-compose.cpu.yml up -d
```

### Restart Individual Services
```bash
# Restart specific containers
docker-compose -f docker-compose.cpu.yml restart redis
docker-compose -f docker-compose.cpu.yml restart celery
docker-compose -f docker-compose.cpu.yml restart celery2
docker-compose -f docker-compose.cpu.yml restart celery3
docker-compose -f docker-compose.cpu.yml restart flower

# Restart web application
docker-compose -f docker-compose.cpu.yml restart web
```

### Force Rebuild Containers
```bash
# Rebuild containers from scratch
docker-compose -f docker-compose.cpu.yml down
docker-compose -f docker-compose.cpu.yml build --no-cache
docker-compose -f docker-compose.cpu.yml up -d
```

## 🆘 Need Help?

If documents get stuck processing:
```bash
# Restart workers
docker-compose -f docker-compose.cpu.yml restart celery celery2 celery3
```

If Ollama connection fails:
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart if needed
ollama serve
```