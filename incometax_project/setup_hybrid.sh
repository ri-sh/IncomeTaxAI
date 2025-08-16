#!/bin/bash

# Source environment variables
if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

# Hybrid setup script - Ollama native, Docker for web services
# This gives us the best of both worlds: native AI performance + containerized web app

echo "🚀 Setting up hybrid IncomeTax AI (Native Ollama + Docker Services)"
echo "=================================================================="

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama not found. Please install Ollama first:"
    echo "   macOS: brew install ollama"
    echo "   Linux: curl -fsSL https://ollama.ai/install.sh | sh"
    echo "   Or visit: https://ollama.ai/download"
    exit 1
fi

echo "✅ Ollama found at $(which ollama)"

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "🤖 Starting Ollama server..."
    ollama serve &
    OLLAMA_PID=$!
    echo "   Ollama PID: $OLLAMA_PID"
    
    # Wait for Ollama to start
    echo "⏳ Waiting for Ollama to start..."
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "✅ Ollama server is running"
            break
        fi
        sleep 1
        echo -n "."
    done
    
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "❌ Failed to start Ollama server"
        exit 1
    fi
else
    echo "✅ Ollama server is already running"
fi

# Pull required model
echo "📦 Ensuring $OLLAMA_MODEL model is available..."
if ollama list | grep -q "$OLLAMA_MODEL"; then
    echo "✅ $OLLAMA_MODEL model already available"
else
    echo "⬇️ Pulling $OLLAMA_MODEL model (this may take a while)..."
    ollama pull $OLLAMA_MODEL
    if [ $? -eq 0 ]; then
        echo "✅ $OLLAMA_MODEL model downloaded successfully"
    else
        echo "❌ Failed to download $OLLAMA_MODEL model"
        exit 1
    fi
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose found"

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.cpu.yml down 2>/dev/null || true

# Build and start services (without Ollama)
echo "🏗️ Building and starting Docker services..."
docker-compose -f docker-compose.cpu.yml build --no-cache
docker-compose -f docker-compose.cpu.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Test connectivity
echo "🔍 Testing connectivity between Docker containers and native Ollama..."
if docker-compose -f docker-compose.cpu.yml exec web curl -s http://host.docker.internal:11434/api/tags >/dev/null 2>&1; then
    echo "✅ Docker containers can reach native Ollama"
else
    echo "⚠️ Testing host.docker.internal connectivity..."
    # Alternative connectivity test
    docker-compose -f docker-compose.cpu.yml exec web ping -c 1 host.docker.internal >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ host.docker.internal is reachable"
    else
        echo "❌ Docker containers cannot reach host. You may need to:"
        echo "   - Enable Docker Desktop's 'Allow the default Docker socket to be used'"
        echo "   - Check firewall settings"
        echo "   - On Linux, use --add-host=host.docker.internal:host-gateway"
    fi
fi

# Run migrations and setup
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.cpu.yml exec web python manage.py migrate

echo "📁 Collecting static files..."
docker-compose -f docker-compose.cpu.yml exec web python manage.py collectstatic --noinput

# Test Ollama from within containers
echo "🧪 Testing Ollama integration..."
docker-compose -f docker-compose.cpu.yml exec web python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
import django
django.setup()

try:
    from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer
    analyzer = OllamaDocumentAnalyzer()
    print('✅ Ollama analyzer initialized successfully')
    print(f'   Model: {analyzer.model_name}')
    print(f'   LLM ready: {analyzer.llm is not None}')
except Exception as e:
    print(f'❌ Failed to initialize Ollama analyzer: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Hybrid setup completed successfully!"
    echo ""
    echo "📊 System Status:"
    echo "   🤖 Ollama: Running natively on host (port 11434)"
    echo "   🌐 Web App: Running in Docker (port 8000)"
    echo "   🔴 Redis: Running in Docker (port 6379)"
    echo "   👷 Celery: 3 workers running in Docker"
    echo ""
    echo "🔗 Access Points:"
    echo "   • Web Application: http://localhost:8000"
    echo "   • Celery Flower: http://localhost:5555"
    echo "   • Ollama API: http://localhost:11434"
    echo ""
    echo "🔍 Monitoring:"
    echo "   • Check containers: docker-compose -f docker-compose.cpu.yml ps"
    echo "   • View logs: docker-compose -f docker-compose.cpu.yml logs -f"
    echo "   • Ollama status: ollama list"
    echo "   • System resources: docker stats"
    echo ""
    echo "🛑 To stop:"
    echo "   • Stop Docker services: docker-compose -f docker-compose.cpu.yml down"
    echo "   • Stop Ollama: killall ollama (or Ctrl+C if running in foreground)"
else
    echo "❌ Setup completed with errors. Check the logs above."
    exit 1
fi