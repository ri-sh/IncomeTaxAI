#!/bin/bash

echo "🔍 Cleanup Monitoring Dashboard"
echo "==============================="
echo ""

# Get compose file
if command -v nvidia-smi &> /dev/null; then
    COMPOSE_FILE="docker-compose.yml"
else
    COMPOSE_FILE="docker-compose.cpu.yml"
fi

# Check if services are running
echo "📊 Service Status:"
docker-compose -f $COMPOSE_FILE ps | grep -E "(celery|beat|flower)" | while read line; do
    echo "   $line"
done
echo ""

# Check Celery Beat logs for cleanup tasks
echo "⏰ Recent Cleanup Activity (last 20 lines):"
docker-compose -f $COMPOSE_FILE logs --tail=20 celery-beat | grep -E "(cleanup|reset)" || echo "   No recent cleanup activity"
echo ""

# Check current database status
echo "🗄️ Database Status:"
docker-compose -f $COMPOSE_FILE exec web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()
from documents.models import ProcessingSession, Document
from datetime import timedelta
from django.utils import timezone

# Current status counts
processing_sessions = ProcessingSession.objects.filter(status=ProcessingSession.Status.PROCESSING).count()
processing_docs = Document.objects.filter(status=Document.Status.PROCESSING).count()
failed_sessions = ProcessingSession.objects.filter(status=ProcessingSession.Status.FAILED).count()
failed_docs = Document.objects.filter(status=Document.Status.FAILED).count()
total_sessions = ProcessingSession.objects.count()
total_docs = Document.objects.count()

print(f'   Total sessions: {total_sessions}')
print(f'   Total documents: {total_docs}')
print(f'   Currently processing: {processing_sessions} sessions, {processing_docs} documents')
print(f'   Failed items: {failed_sessions} sessions, {failed_docs} documents')

# Check for items stuck longer than 1 hour
stuck_threshold = timezone.now() - timedelta(hours=1)
stuck_sessions = ProcessingSession.objects.filter(
    status=ProcessingSession.Status.PROCESSING,
    created_at__lt=stuck_threshold
).count()
stuck_docs = Document.objects.filter(
    status=Document.Status.PROCESSING,
    uploaded_at__lt=stuck_threshold
).count()

if stuck_sessions > 0 or stuck_docs > 0:
    print(f'   ⚠️  STUCK ITEMS: {stuck_sessions} sessions, {stuck_docs} documents (>1h)')
else:
    print('   ✅ No stuck items detected')
"
echo ""

# Check Redis cleanup status
echo "🔴 Redis Status:"
REDIS_KEYS=$(docker-compose -f $COMPOSE_FILE exec redis redis-cli info keyspace | grep "keys=" | wc -l || echo "0")
CELERY_KEYS=$(docker-compose -f $COMPOSE_FILE exec redis redis-cli keys "celery-task-meta-*" | wc -l || echo "0")
echo "   Total databases with keys: $REDIS_KEYS"
echo "   Celery task metadata keys: $CELERY_KEYS"
echo ""

# Show active Celery workers
echo "👷 Active Celery Workers:"
docker-compose -f $COMPOSE_FILE exec celery celery -A incometax_project inspect ping 2>/dev/null | grep -E "(pong|nodes online)" || echo "   No workers responding"
echo ""

# Show next scheduled cleanup
echo "⏰ Next Scheduled Tasks:"
docker-compose -f $COMPOSE_FILE exec web python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()
from incometax_project.celery import app
from datetime import datetime, timedelta

print('   Cleanup automation schedule:')
for task_name, task_config in app.conf.beat_schedule.items():
    schedule = task_config['schedule']
    print(f'   - {task_name}: {schedule}')
"
echo ""

# Manual cleanup options
echo "🔧 Manual Commands:"
echo "   Full cleanup:     docker-compose -f $COMPOSE_FILE exec web python cleanup_now.py"
echo "   Health check:     docker-compose -f $COMPOSE_FILE exec celery python health_check.py"
echo "   Monitor logs:     docker-compose -f $COMPOSE_FILE logs -f celery-beat"
echo "   Flower dashboard: http://localhost:5555"