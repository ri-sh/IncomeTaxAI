#!/bin/bash

# Source environment variables
if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

echo "🔍 Ollama Docker Optimization Debug Script"
echo "==========================================""

# Check if Ollama is running natively
echo "1. Checking native Ollama..."
if pgrep -f "ollama" > /dev/null; then
    echo "   ⚠️  Native Ollama is running - stop it first:"
    echo "   pkill -f ollama"
    echo ""
fi

# Check host .ollama directory
echo "2. Checking host .ollama directory..."
if [ -d ~/.ollama ]; then
    echo "   ✅ Found ~/.ollama directory"
    echo "   📁 Models: $(ls ~/.ollama/models/manifests/registry.ollama.ai/library/ 2>/dev/null | wc -l || echo 0)"
else
    echo "   ❌ ~/.ollama directory not found"
    echo "   💡 Run: mkdir -p ~/.ollama && ollama pull $OLLAMA_MODEL"
fi
echo ""

# Start optimized containers
echo "3. Starting optimized Docker containers..."
docker-compose up -d

# Wait for startup
echo "4. Waiting for services to start..."
sleep 10

# Check container processes
echo "5. Checking Ollama process inside container..."
CONTAINER_ID=$(docker-compose ps -q ollama)
if [ ! -z "$CONTAINER_ID" ]; then
    echo "   Container ID: $CONTAINER_ID"
    echo "   Process info:"
    docker exec $CONTAINER_ID ps aux | grep ollama | head -5
    echo ""
    
    # Check for --no-mmap flag
    if docker exec $CONTAINER_ID ps aux | grep -q "\-\-no-mmap"; then
        echo "   ❌ Still using --no-mmap flag!"
    else
        echo "   ✅ No --no-mmap flag detected"
    fi
else
    echo "   ❌ Ollama container not running"
fi
echo ""

# Monitor CPU usage
echo "6. Monitoring CPU usage (10 seconds)..."
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ollama
sleep 10
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ollama
echo ""

# Test Ollama API
echo "7. Testing Ollama API..."
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "   ✅ Ollama API responding"
    echo "   📊 Available models:"
    curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null || echo "   (jq not available for parsing)"
else
    echo "   ❌ Ollama API not responding"
fi
echo ""

# Quick inference test
echo "8. Quick inference test..."
echo "   Sending simple request..."
START_TIME=$(date +%s)
curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "$OLLAMA_MODEL",
    "prompt": "Hello, respond with just OK",
    "stream": false
  }' > /tmp/ollama_test.json

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $? -eq 0 ] && [ -f /tmp/ollama_test.json ]; then
    echo "   ✅ Inference completed in ${DURATION} seconds"
    RESPONSE=$(cat /tmp/ollama_test.json | jq -r '.response' 2>/dev/null || cat /tmp/ollama_test.json)
    echo "   📝 Response: ${RESPONSE:0:50}..."
    rm -f /tmp/ollama_test.json
else
    echo "   ❌ Inference test failed or timed out"
fi
echo ""

echo "9. Final CPU check..."
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep ollama
echo ""

echo "✅ Debug complete!"
echo ""
echo "💡 Next steps:"
echo "   - If CPU usage is still high (>300%), try running Ollama natively"
echo "   - Monitor: docker stats"
echo "   - Health check: docker-compose exec celery python health_check.py"