# IncomeTax AI - Production Deployment Guide

## 🚀 Quick Start (Recommended: Hybrid Mode)

### Prerequisites
- Docker and Docker Compose installed
- At least 8GB RAM available (Llama3 requires significant memory)
- Ollama installed locally (for better AI performance)
- Internet connection (for downloading Llama3 model on first run)

### 1. Clone and Setup
```bash
git clone <your-repo>
cd incometax_project
cp .env.example .env
# Edit .env with your production values
```

### 2. Hybrid Deployment (Recommended)
**Native Ollama + Docker Services for optimal performance**

```bash
# Complete setup with Ollama installation and model download
./setup_hybrid.sh

# OR if Ollama is already installed and running:
./deploy_hybrid.sh
```

### 3. Alternative: Full Docker Deployment
**All services in Docker (may have performance limitations)**

```bash
./deploy.sh
```

### 3. Access Your Application
- **Web Application**: http://localhost:8000
- **Celery Monitoring**: http://localhost:5555
- **Tax Analysis Report**: http://localhost:8000/api/tax_analysis_report/

## 🏗️ Architecture

### Hybrid Mode (Recommended)
- **Native Ollama**: Llama3 AI service running natively on host for optimal performance
- **web**: Django application (Gunicorn + 2 workers) in Docker
- **celery**: Primary Celery worker for document processing in Docker
- **celery2**: Secondary worker for parallel processing in Docker
- **celery3**: Tertiary worker for high throughput in Docker
- **redis**: Task queue and caching in Docker
- **flower**: Celery monitoring in Docker

### Full Docker Mode (Alternative)
- **ollama**: Llama3 AI service in Docker (may have performance limitations)
- **web**: Django application (Gunicorn + 2 workers) in Docker
- **celery**: Celery workers in Docker
- **redis**: Task queue and caching in Docker

### Key Features
- ✅ **Distributed AI Processing**: Multiple Celery workers handle concurrent document analysis
- ✅ **Real-time Tax Calculations**: Old vs New regime comparison with live editing
- ✅ **Production Database**: PostgreSQL with connection pooling
- ✅ **Scalable Architecture**: Easy to scale workers horizontally
- ✅ **Monitoring**: Flower dashboard for task monitoring
- ✅ **Security**: Production-ready security settings

## 📊 Performance Optimizations

### Hybrid Architecture Benefits
- **Native Ollama Performance**: 50-90% CPU usage reduction vs Docker (1097% → 2.6%)
- **Full CPU/GPU Access**: Direct hardware access for AI processing
- **Parallel Document Processing**: 3 Celery workers for concurrent analysis
- **Timeout Protection**: Multi-layer timeouts prevent hanging documents

### AI Document Processing
- **Solo Pool**: Prevents SIGSEGV crashes during AI processing
- **Memory Limits**: 2-4GB per worker optimized for AI workloads
- **Task Timeouts**: 10-minute limit with granular timeouts (60s classification, 120s extraction)
- **Distributed Processing**: Multiple workers for concurrent sessions

### Database
- **Connection Pooling**: Optimized database connections
- **Health Checks**: Automatic connection recovery
- **Migrations**: Automatic on deployment

## 🤖 AI Model Setup

### Hybrid Mode (Recommended)
The `setup_hybrid.sh` script automatically:
- Installs Ollama locally if not present
- Downloads and runs native Ollama service
- Pulls Llama3:8b model (3.8GB download)
- Configures Docker containers to connect to native Ollama
- Tests connectivity between services

### Manual Model Management (Hybrid)
```bash
# List available models (native)
ollama list

# Pull different model version
ollama pull llama3:70b

# Remove unused models
ollama rm llama3:8b

# Check Ollama status
curl http://localhost:11434/api/tags
```

### Full Docker Mode Management
```bash
# List available models (Docker)
docker-compose -f docker-compose.cpu.yml exec ollama ollama list

# Pull different model version
docker-compose -f docker-compose.cpu.yml exec ollama ollama pull llama3:70b
```

### Performance Comparison
- **Hybrid Mode**: ~30-90 seconds per document, 2.6% CPU usage
- **Docker Mode**: ~2-8 minutes per document, 1097% CPU usage
- **Memory Usage**: 4-8GB for Llama3:8b model

## 🔧 Configuration

### Environment Variables
Copy `.env.example` to `.env` and configure:

```bash
# Core Settings
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@db:5432/dbname

# Redis/Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Security (for HTTPS in production)
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Scaling Workers
```bash
# Add more Celery workers
docker-compose up -d --scale celery=3 --scale celery2=2
```

## 📈 Monitoring

### Celery Tasks
- Monitor at: http://localhost:5555
- View active tasks, worker status, and performance metrics

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f web
docker-compose logs -f celery
```

### Health Checks
```bash
# Check service status
docker-compose ps

# Test API endpoint
curl http://localhost:8000/api/health/
```

## 🔒 Security Considerations

### Production Checklist
- [ ] Change `SECRET_KEY` in environment variables
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Enable HTTPS and update security settings
- [ ] Configure firewall rules
- [ ] Set up SSL certificates
- [ ] Configure backup strategy
- [ ] Set up monitoring and alerting

### Database Security
- [ ] Change default PostgreSQL credentials
- [ ] Enable SSL for database connections
- [ ] Regular backups
- [ ] Access control and user permissions

## 🛠️ Maintenance

### Updates
```bash
# Pull latest code
git pull origin main

# Rebuild and deploy
./deploy.sh
```

### Backup
```bash
# Backup database
docker-compose exec db pg_dump -U incometax_user incometax_db > backup.sql

# Backup media files
tar -czf media_backup.tar.gz media/
```

### Restore
```bash
# Restore database
docker-compose exec -T db psql -U incometax_user incometax_db < backup.sql

# Restore media files
tar -xzf media_backup.tar.gz
```

## 🚨 Troubleshooting

### Hybrid Mode Issues

#### Ollama Connectivity Issues
```bash
# Check if Ollama is running natively
curl http://localhost:11434/api/tags

# Check Docker container connectivity to host
docker-compose -f docker-compose.cpu.yml exec web curl http://host.docker.internal:11434/api/tags

# Restart Ollama if needed
killall ollama
ollama serve
```

#### Documents Stuck in Processing
```bash
# Check Celery worker logs
docker-compose -f docker-compose.cpu.yml logs -f celery

# Restart all workers to clear stuck tasks
docker-compose -f docker-compose.cpu.yml restart celery celery2 celery3

# Manual cleanup of stuck documents
docker-compose -f docker-compose.cpu.yml exec web python cleanup_now.py
```

### Common Issues

#### Celery Workers Not Starting
```bash
# Check Redis connection
docker-compose -f docker-compose.cpu.yml exec redis redis-cli ping

# Restart Celery workers
docker-compose -f docker-compose.cpu.yml restart celery celery2 celery3
```

#### Memory Issues
```bash
# Check memory usage
docker stats

# Reduce worker concurrency if needed
# Edit docker-compose.cpu.yml: --concurrency=1
```

### Support
For technical support, check the application logs and refer to the Django and Celery documentation.

## 📝 API Endpoints

- `GET /` - Main application interface
- `POST /api/sessions/` - Create new document processing session
- `POST /api/sessions/{id}/upload_document/` - Upload documents
- `POST /api/sessions/{id}/analyze/` - Start AI analysis
- `GET /api/sessions/{id}/analysis_results/` - Get detailed results
- `GET /api/tax_analysis_report/` - Tax comparison interface
- `GET /api/health/` - Health check endpoint