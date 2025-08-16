#!/bin/bash
cd "$(dirname "$0")"

# Hybrid deployment script - assumes Ollama is already running natively
echo "🚀 Starting hybrid deployment (Native Ollama + Docker Services)..."

if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi
# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "❌ Ollama is not running. Please start it first:"
    echo "   ollama serve"
    echo "   Or run: ./setup_hybrid.sh"
    exit 1
fi

echo "✅ Ollama is running natively"

# Check if the model is available
echo "🤖 Checking if the model $OLLAMA_MODEL is available..."
if ! curl -s http://localhost:11434/api/tags | grep -q "$OLLAMA_MODEL"; then
    echo "❌ Model $OLLAMA_MODEL is not available. Please pull it first:"
    echo "   ollama pull $OLLAMA_MODEL"
    exit 1
fi
echo "✅ Model $OLLAMA_MODEL is available"

# Determine compose file
COMPOSE_FILE="docker-compose.cpu.yml"
echo "📦 Using CPU-only Docker compose configuration"

# Stop and remove existing containers
echo "📦 Stopping existing containers..."
docker-compose -f $COMPOSE_FILE down

# Build fresh images
echo "🔨 Building fresh Docker images..."
docker-compose -f $COMPOSE_FILE build --no-cache

# Start services (without Ollama)
echo "▶️ Starting Docker services..."
docker-compose -f $COMPOSE_FILE up -d

# Wait for database to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Clear stale Redis data
echo "🧹 Clearing stale Redis data..."
docker-compose -f $COMPOSE_FILE exec redis redis-cli FLUSHDB

# Reset stuck documents in database
echo "🔄 Resetting stuck documents..."
docker-compose -f $COMPOSE_FILE exec web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()
from documents.models import Document
stuck_docs = Document.objects.filter(status=Document.Status.PROCESSING)
count = stuck_docs.count()
stuck_docs.update(status=Document.Status.UPLOADED)
print(f'Reset {count} stuck documents')
"

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

# Test Ollama connectivity from containers
echo "🤖 Testing Ollama connectivity from containers..."
docker-compose -f $COMPOSE_FILE exec web curl -f http://host.docker.internal:11434/api/tags >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Docker containers can reach native Ollama"
else
    echo "⚠️ Connectivity test failed. Containers may not reach native Ollama."
fi

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

echo ""
echo "✅ Hybrid deployment completed!"
echo ""
echo "🎯 Performance Benefits:"
echo "   • Native Ollama performance (no Docker overhead)"
echo "   • Full CPU/GPU access for AI processing"
echo "   • Containerized web services for consistency"
echo "   • Parallel document processing with timeouts"
echo ""
echo "🌐 Access your application at: http://localhost:8000"
echo "📊 Monitor Celery tasks at: http://localhost:5555"
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