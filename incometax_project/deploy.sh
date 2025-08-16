#!/bin/bash

# Production deployment script for IncomeTax AI

echo "🚀 Starting production deployment..."

# Check for GPU support
GPU_SUPPORT=""
if command -v nvidia-smi &> /dev/null; then
    echo "🎮 NVIDIA GPU detected - using GPU-accelerated deployment"
    COMPOSE_FILE="docker-compose.yml"
else
    echo "💻 No GPU detected - using CPU-only deployment"
    COMPOSE_FILE="docker-compose.cpu.yml"
fi

# Stop and remove existing containers
echo "📦 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Build fresh images
echo "🔨 Building fresh Docker images..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Start services
echo "▶️ Starting services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 5

# Clear stale Redis data
echo "🧹 Clearing stale Redis data..."
docker-compose -f $COMPOSE_FILE exec redis redis-cli FLUSHDB

# Reset stuck documents in database
echo "🔄 Resetting stuck documents..."
docker-compose -f $COMPOSE_FILE exec web python reset_processing_documents.py

# Run comprehensive cleanup on startup
echo "🧹 Running comprehensive startup cleanup..."
docker-compose -f $COMPOSE_FILE exec web python cleanup_now.py

# Schedule immediate cleanup via Celery
echo "⚡ Triggering immediate cleanup via Celery..."
docker-compose -f $COMPOSE_FILE exec web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()
from api.cleanup_tasks import cleanup_dead_sessions, reset_stuck_documents
cleanup_dead_sessions.delay()
reset_stuck_documents.delay()
print('✅ Cleanup tasks scheduled')
"

# Wait for Ollama to be ready and download model
echo "🤖 Waiting for Ollama service to be ready..."
sleep 10

# Pull Ollama model
echo "🤖 Pulling Ollama model llama3:8b..."
docker-compose -f $COMPOSE_FILE exec ollama ollama pull llama3:8b

# Test Ollama connection
echo "🔍 Testing Ollama connection from celery container..."
docker-compose -f $COMPOSE_FILE exec celery curl http://ollama:11434/api/tags

# Run comprehensive health check
echo "🏥 Running comprehensive health check..."
docker-compose -f $COMPOSE_FILE exec celery python health_check.py

# Verify cleanup automation is working
echo "⏰ Verifying cleanup automation..."
docker-compose -f $COMPOSE_FILE exec web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()
from incometax_project.celery import app
print('📋 Periodic tasks configured:')
for task_name, task_config in app.conf.beat_schedule.items():
    print(f'   - {task_name}: {task_config[\"schedule\"]}')
print('✅ Cleanup automation verified')
"

# Generate migrations
echo "📝 Generating database migrations..."
docker-compose -f $COMPOSE_FILE exec web python manage.py makemigrations

# Run migrations
echo "🗄️ Running database migrations..."
docker-compose -f $COMPOSE_FILE exec web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose -f $COMPOSE_FILE exec web python manage.py collectstatic --noinput

# Check if all services are running
echo "🔍 Checking service status..."
docker-compose -f $COMPOSE_FILE ps

echo "✅ Deployment completed!"
echo ""
echo "🌐 Access your application at: http://localhost:8000"
echo "📊 Monitor Celery tasks at: http://localhost:5555"
echo "🗄️ PostgreSQL is available at: localhost:5432"
echo "🔴 Redis is available at: localhost:6379"
echo "🤖 Ollama AI service available at: localhost:11434"
echo ""
echo "📝 View logs with: docker-compose -f $COMPOSE_FILE logs -f [service_name]"
echo "🛑 Stop services with: docker-compose -f $COMPOSE_FILE down"
echo ""
echo "🔍 Test AI processing: curl http://localhost:11434/api/tags"
echo "🏥 Run health check: docker-compose -f $COMPOSE_FILE exec celery python health_check.py"
echo "📋 Monitor Celery logs: docker-compose -f $COMPOSE_FILE logs -f celery"
echo "🧹 Manual cleanup: docker-compose -f $COMPOSE_FILE exec web python cleanup_now.py"
echo "⏰ Monitor periodic tasks: docker-compose -f $COMPOSE_FILE logs -f celery-beat"
echo "📊 Cleanup dashboard: ./monitor_cleanup.sh"
echo "🏥 Enhanced health check: docker-compose -f $COMPOSE_FILE exec celery python health_check.py"