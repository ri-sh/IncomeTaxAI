#!/bin/bash

# Railway Deployment Script for IncomeTax AI
echo "🚂 Preparing IncomeTax AI for Railway deployment..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Please install it first:"
    echo "   npm install -g @railway/cli"
    echo "   or visit: https://docs.railway.app/develop/cli"
    exit 1
fi

echo "✅ Railway CLI found"

# Check if user is logged in
if ! railway whoami &> /dev/null; then
    echo "🔐 Please login to Railway:"
    railway login
fi

echo "✅ Railway authentication verified"

# Create Railway project if it doesn't exist
echo "📦 Setting up Railway project..."
if [ ! -f "railway.toml" ]; then
    echo "❌ railway.toml not found. Please run this from the project root."
    exit 1
fi

# Initialize Railway project
echo "🎯 Initializing Railway project..."
railway login

# Link to existing project or create new one
echo "🔗 Linking to Railway project..."
echo "Choose option:"
echo "1. Create new Railway project"
echo "2. Link to existing project"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "🆕 Creating new Railway project..."
        railway init
        ;;
    2)
        echo "🔗 Linking to existing project..."
        railway link
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

# Add PostgreSQL service
echo "🗄️ Adding PostgreSQL database..."
railway add postgresql

# Add Redis service  
echo "🔴 Adding Redis cache..."
railway add redis

# Set environment variables
echo "⚙️ Setting up environment variables..."

# Core Django settings
railway variables set DEBUG=False
railway variables set SECRET_KEY="$(openssl rand -base64 32)"
railway variables set ALLOWED_HOSTS="*.railway.app,*.up.railway.app"
railway variables set CSRF_TRUSTED_ORIGINS="https://*.railway.app,https://*.up.railway.app"

# Privacy Engine settings
railway variables set PRIVACY_ENGINE_ENABLED=true
railway variables set ENCRYPTION_SALT="$(openssl rand -base64 32)"

# Ollama service setup
echo "🤖 Setting up Ollama service..."
echo "Choose Ollama deployment option:"
echo "1. Deploy separate Ollama service on Railway (Recommended)"
echo "2. Use external Ollama API"
echo "3. Configure manually later"
read -p "Enter choice (1, 2, or 3): " ollama_choice

case $ollama_choice in
    1)
        echo "🚀 Deploying Ollama service on Railway..."
        # Deploy Ollama using Railway template
        railway add --template ollama
        echo "⏳ Waiting for Ollama service to deploy..."
        sleep 30
        
        # Get Ollama service URL
        OLLAMA_URL=$(railway url --service ollama 2>/dev/null || echo "")
        if [ -n "$OLLAMA_URL" ]; then
            railway variables set OLLAMA_BASE_URL="$OLLAMA_URL"
            echo "✅ Ollama service configured: $OLLAMA_URL"
        else
            echo "⚠️  Please manually set OLLAMA_BASE_URL after Ollama service is ready"
            echo "   railway variables set OLLAMA_BASE_URL=https://your-ollama-service.railway.app"
        fi
        railway variables set OLLAMA_MODEL=qwen2.5:3b
        ;;
    2)
        echo "🌐 Configuring external Ollama API..."
        read -p "Enter your Ollama API URL (e.g., https://your-server.com:11434): " external_ollama_url
        railway variables set OLLAMA_BASE_URL="$external_ollama_url"
        railway variables set OLLAMA_MODEL=qwen2.5:3b
        echo "✅ External Ollama configured: $external_ollama_url"
        ;;
    3)
        echo "⚠️  IMPORTANT: Configure Ollama manually after deployment:"
        echo "   For Railway Ollama service:"
        echo "   railway add --template ollama"
        echo "   railway variables set OLLAMA_BASE_URL=https://your-ollama-service.railway.app"
        echo "   "
        echo "   For external Ollama:"
        echo "   railway variables set OLLAMA_BASE_URL=https://your-ollama-server.com:11434"
        echo "   railway variables set OLLAMA_MODEL=qwen2.5:3b"
        ;;
    *)
        echo "❌ Invalid choice, skipping Ollama configuration"
        ;;
esac

# Security settings
railway variables set SECURE_SSL_REDIRECT=True
railway variables set SESSION_COOKIE_SECURE=True
railway variables set CSRF_COOKIE_SECURE=True

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway up

# Check deployment status
echo "🔍 Checking deployment status..."
railway status

# Get the deployment URL
echo "🌐 Getting deployment URL..."
DEPLOYMENT_URL=$(railway url)

echo ""
echo "✅ Railway deployment completed!"
echo ""
echo "📋 Deployment Summary:"
echo "   🌐 Application URL: $DEPLOYMENT_URL"
echo "   🗄️ Database: PostgreSQL (auto-configured)"
echo "   🔴 Cache: Redis (auto-configured)"
echo "   🔒 Privacy Engine: Enabled with encryption"
echo ""
echo "🔧 Next Steps:"
echo "1. Set up Ollama service (separate Railway project or external)"
echo "2. Configure OLLAMA_BASE_URL environment variable"
echo "3. Test the application at: $DEPLOYMENT_URL"
echo "4. Monitor logs: railway logs"
echo ""
echo "📊 Useful Railway Commands:"
echo "   railway logs           # View application logs"
echo "   railway status         # Check service status"
echo "   railway variables      # Manage environment variables"
echo "   railway shell          # Access application shell"
echo "   railway connect        # Connect to database"
echo ""
echo "🔍 Health Check URL: $DEPLOYMENT_URL/api/health/"