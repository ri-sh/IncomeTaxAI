#!/bin/bash

echo "🔄 Restarting Celery worker..."

# Stop and remove the existing Celery container
docker-compose -f docker-compose.cpu.yml stop celery
docker-compose -f docker-compose.cpu.yml rm -f celery

# Start the Celery service
docker-compose -f docker-compose.cpu.yml up -d celery

echo "✅ Celery worker restarted."
