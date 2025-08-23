# 🚂 Railway Deployment Guide

This guide covers deploying IncomeTax AI to Railway, a modern cloud platform that handles Docker deployments with automatic scaling and database provisioning.

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **Railway CLI**: Install the Railway CLI
   ```bash
   npm install -g @railway/cli
   # or
   curl -fsSL https://railway.app/install.sh | sh
   ```
3. **Git Repository**: Your code should be in a Git repository

## 🚀 Quick Deployment

### Option 1: Automated Deployment Script

```bash
# Run the automated deployment script
./deploy_railway.sh
```

### Option 2: Manual Deployment

1. **Login to Railway**
   ```bash
   railway login
   ```

2. **Initialize Project**
   ```bash
   railway init
   ```

3. **Add Services**
   ```bash
   # Add PostgreSQL database
   railway add postgresql
   
   # Add Redis cache
   railway add redis
   ```

4. **Set Environment Variables**
   ```bash
   # Core settings
   railway variables set DEBUG=False
   railway variables set SECRET_KEY="your-secret-key"
   railway variables set ALLOWED_HOSTS="*.railway.app,*.up.railway.app"
   
   # Privacy Engine
   railway variables set PRIVACY_ENGINE_ENABLED=true
   railway variables set ENCRYPTION_SALT="your-encryption-salt"
   
   # Security
   railway variables set SECURE_SSL_REDIRECT=True
   railway variables set SESSION_COOKIE_SECURE=True
   railway variables set CSRF_COOKIE_SECURE=True
   ```

5. **Deploy**
   ```bash
   railway up
   ```

## ⚙️ Configuration

### Environment Variables

Railway will automatically provide:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `PORT` - Application port (usually 8000)

You need to manually set:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Generate with `openssl rand -base64 32` |
| `ENCRYPTION_SALT` | Privacy engine salt | Generate with `openssl rand -base64 32` |
| `OLLAMA_BASE_URL` | Ollama service URL | `https://your-ollama.railway.app` |
| `OLLAMA_MODEL` | AI model name | `qwen2.5:3b` |
| `EMAIL_HOST_USER` | Email username | `your-email@gmail.com` |
| `EMAIL_HOST_PASSWORD` | Email password | `your-app-password` |

### Dockerfile

Railway uses `incometax_project/Dockerfile.railway` which includes:
- ✅ Optimized for Railway's environment
- ✅ Health checks
- ✅ Static file collection
- ✅ Database migration on startup
- ✅ Non-root user for security

## 🤖 Ollama Service Setup

Since our IncomeTax AI uses **native Ollama** (not containerized), you have several options for Railway deployment:

### Option 1: Separate Railway Ollama Service

Deploy Ollama as a separate Railway service using Railway's one-click template:

1. **Deploy Ollama Template**
   ```bash
   # Use Railway's official Ollama template
   railway deploy --template T9CQ5w
   ```

2. **Configure Environment Variables**
   ```bash
   # Set in your Ollama service
   railway variables set OLLAMA_HOST=0.0.0.0
   railway variables set OLLAMA_PORT=11434
   railway variables set OLLAMA_KEEP_ALIVE=5m
   railway variables set OLLAMA_NUM_PARALLEL=4
   ```

3. **Get Ollama Service URL**
   ```bash
   # Get your Ollama service URL
   OLLAMA_URL=$(railway url --service ollama)
   
   # Set in your main app
   railway variables set OLLAMA_BASE_URL=$OLLAMA_URL
   railway variables set OLLAMA_MODEL=qwen2.5:3b
   ```

### Option 2: External Ollama Service

Host Ollama on another platform (DigitalOcean, AWS, etc.) and configure the API endpoint:

1. **Setup Ollama on External Server**
   ```bash
   # On your server, configure Ollama for network access
   export OLLAMA_HOST=0.0.0.0
   export OLLAMA_PORT=11434
   ollama serve
   
   # Pull required models
   ollama pull qwen2.5:3b
   ```

2. **Configure Railway App**
   ```bash
   # Set external Ollama URL
   railway variables set OLLAMA_BASE_URL=https://your-ollama-server.com:11434
   railway variables set OLLAMA_MODEL=qwen2.5:3b
   ```

### Option 3: Ollama Cloud Services

Use managed Ollama API services:

1. **Ollama Cloud** (when available)
2. **Third-party Ollama APIs** (Replicate, Hugging Face, etc.)
3. **Self-hosted Ollama with ngrok** for development

### Recommended: Railway Ollama Template

The easiest option is using Railway's official Ollama template which provides:
- ✅ Pre-configured Docker environment
- ✅ Persistent model storage
- ✅ Automatic scaling
- ✅ Network access configuration
- ✅ Health checks

```bash
# Quick setup using Railway CLI
railway login
railway init
railway add --template ollama  # Deploy Ollama service
railway add postgresql         # Add database
railway add redis              # Add Redis cache
railway up                     # Deploy main app
```

## 🗄️ Database Migration

Railway automatically runs migrations on deployment via the startup script:

```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

## 📊 Monitoring

### Health Checks

Railway automatically monitors your application using:
- Health check endpoint: `/api/health/`
- Automatic restarts on failure
- Resource monitoring

### Logging

View logs in real-time:
```bash
railway logs
```

### Metrics

Access Railway's built-in metrics:
- CPU usage
- Memory usage
- Request rate
- Error rate

## 🔒 Security Features

Railway deployment includes:
- ✅ HTTPS termination
- ✅ Environment variable encryption
- ✅ Network isolation
- ✅ Automatic security updates
- ✅ Privacy engine with file encryption

## 📈 Scaling

### Horizontal Scaling

Railway supports automatic horizontal scaling:
```bash
# Set replica count
railway service scale --replicas 3
```

### Vertical Scaling

Upgrade resources in Railway dashboard:
- CPU: 0.5-8 vCPUs
- Memory: 512MB-32GB
- Storage: Up to 100GB

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check database status
   railway service logs postgresql
   
   # Connect to database
   railway connect postgresql
   ```

2. **Static Files Not Loading**
   ```bash
   # Check static file collection
   railway logs | grep collectstatic
   
   # Force static file collection
   railway run python manage.py collectstatic --noinput
   ```

3. **Ollama Connection Issues**
   ```bash
   # Test Ollama connectivity
   railway run curl $OLLAMA_BASE_URL/api/tags
   
   # Check Ollama service logs
   railway logs -s ollama
   ```

### Debugging Commands

```bash
# Access application shell
railway shell

# Run Django management commands
railway run python manage.py shell

# Check environment variables
railway variables

# View service status
railway status

# Connect to database
railway connect postgresql
```

## 🎯 Production Checklist

Before going live:

- [ ] Set strong `SECRET_KEY` and `ENCRYPTION_SALT`
- [ ] Configure custom domain
- [ ] Set up email service (Gmail, SendGrid, etc.)
- [ ] Configure monitoring and alerts
- [ ] Test file upload and processing
- [ ] Verify SSL/HTTPS configuration
- [ ] Test privacy engine functionality
- [ ] Set up backup strategy
- [ ] Configure error reporting (Sentry, etc.)

## 📚 Useful Commands

```bash
# Deploy changes
railway up

# View logs
railway logs

# Access shell
railway shell

# Run migrations
railway run python manage.py migrate

# Create superuser
railway run python manage.py createsuperuser

# Check service status
railway status

# View environment variables
railway variables

# Connect to database
railway connect postgresql

# Scale service
railway service scale --replicas 2

# View metrics
railway service metrics
```

## 🌐 Access Points

After deployment, your application will be available at:
- **Main App**: `https://your-app.railway.app`
- **Admin Panel**: `https://your-app.railway.app/admin/`
- **API Health**: `https://your-app.railway.app/api/health/`
- **Tax Report**: `https://your-app.railway.app/api/tax_analysis_report/`

## 💰 Cost Optimization

Railway pricing is usage-based. To optimize costs:

1. **Resource Limits**: Set appropriate CPU/memory limits
2. **Scaling**: Use auto-scaling instead of fixed replicas
3. **Monitoring**: Monitor usage in Railway dashboard
4. **Optimization**: Optimize Docker image size and startup time

## 🆘 Support

- **Railway Docs**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [railway.app/discord](https://railway.app/discord)
- **Railway Status**: [status.railway.app](https://status.railway.app)