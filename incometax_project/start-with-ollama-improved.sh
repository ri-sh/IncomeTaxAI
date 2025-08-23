#!/bin/bash
set -e

echo "🚀 TaxSahaj + Ollama Startup (Improved)"
echo "======================================="

export DJANGO_SETTINGS_MODULE=incometax_project.settings_production

# Function to check if a process is running
check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo "✅ $1 is running"
        return 0
    else
        echo "❌ $1 is not running"
        return 1
    fi
}

# Function to wait for service
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            echo "✅ $service_name is ready"
            return 0
        fi
        echo "   Attempt $attempt/$max_attempts..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start after $max_attempts attempts"
    return 1
}

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up processes..."
    pkill -f "ollama serve" || true
    pkill -f "celery.*worker" || true
    exit 1
}

# Set up trap for cleanup
trap cleanup SIGTERM SIGINT

# Check available memory
echo "💾 System Resources:"
free -h 2>/dev/null || echo "   Memory info not available"
df -h /tmp 2>/dev/null || echo "   Disk info not available"

# Start Ollama server
echo "🤖 Starting Ollama server..."
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "   Ollama PID: $OLLAMA_PID"

# Wait for Ollama to be ready
if wait_for_service "Ollama" "curl -s http://localhost:11434/api/tags"; then
    echo "🎯 Ollama server started successfully"
else
    echo "❌ Ollama server failed to start"
    echo "📄 Ollama logs:"
    tail -20 /tmp/ollama.log 2>/dev/null || echo "No logs available"
    exit 1
fi

# Clean up old models to save space
echo "🧹 Cleaning up unused Ollama models..."
ollama list | grep -E "qwen2\.5:|qwen3:|llama|deepseek|gpt-oss" | while read -r line; do
    model_name=$(echo "$line" | awk '{print $1}')
    if [ "$model_name" != "$OLLAMA_MODEL" ] && [ "$model_name" != "NAME" ]; then
        echo "   🗑️ Removing unused model: $model_name"
        ollama rm "$model_name" || echo "   ⚠️ Failed to remove $model_name"
    fi
done

# Ensure target model is available
echo "🔍 Checking if target model $OLLAMA_MODEL is available..."
if ollama list | grep -q "$OLLAMA_MODEL"; then
    echo "✅ Target model $OLLAMA_MODEL is already available"
else
    echo "📥 Pulling required model: $OLLAMA_MODEL"
    if ollama pull "$OLLAMA_MODEL"; then
        echo "✅ Model $OLLAMA_MODEL pulled successfully"
    else
        echo "❌ Failed to pull model - will use any available model"
    fi
fi

echo "📋 Final model inventory:"
ollama list || echo "⚠️ Could not list models"

# Setup Django
echo "📁 Setting up persistent storage..."
mkdir -p /app/data/media

echo "🔧 Running migrations..."
python manage.py migrate --noinput

echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

echo "🧹 Cleaning up orphaned documents..."
python manage.py cleanup_documents || echo "⚠️ Cleanup failed"

echo "🔄 Flushing Redis cache..."
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('✅ Redis cleared')" || echo "⚠️ Redis flush failed"

# Start Celery worker
echo "🚀 Starting Celery worker..."
celery -A incometax_project worker --loglevel=info --concurrency=1 --pool=solo > /tmp/celery.log 2>&1 &
CELERY_PID=$!
echo "   Celery PID: $CELERY_PID"

# Wait a moment for Celery to start
sleep 5
if check_process "celery.*worker"; then
    echo "✅ Celery worker started"
else
    echo "❌ Celery worker failed to start"
    echo "📄 Celery logs:"
    tail -10 /tmp/celery.log 2>/dev/null || echo "No logs available"
fi

# Verify all services before starting Django
echo "🔍 Final service check..."
echo "   Ollama: $(curl -s http://localhost:11434/api/tags >/dev/null 2>&1 && echo 'OK' || echo 'FAILED')"
echo "   Celery: $(check_process "celery.*worker" && echo 'OK' || echo 'FAILED')"

# Start Django server
PORT=${PORT:-8000}
echo "🚀 Starting Django server on port $PORT"
echo "📋 Process Summary:"
echo "   - Ollama PID: $OLLAMA_PID"
echo "   - Celery PID: $CELERY_PID"
echo "   - Django starting on port: $PORT"

# Use exec to replace the shell with gunicorn
exec gunicorn incometax_project.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --preload