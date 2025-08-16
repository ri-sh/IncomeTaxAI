import os
import sys

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src'))

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')

app = Celery('incometax_project')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Periodic tasks configuration
app.conf.beat_schedule = {
    'cleanup-dead-sessions': {
        'task': 'api.cleanup_tasks.cleanup_dead_sessions',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    'reset-stuck-documents': {
        'task': 'api.cleanup_tasks.reset_stuck_documents', 
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'cleanup-old-task-results': {
        'task': 'api.cleanup_tasks.cleanup_old_task_results',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'full-cleanup-startup': {
        'task': 'api.cleanup_tasks.cleanup_dead_sessions',
        'schedule': crontab(minute='*/60'),  # Run every hour as backup
    },
}

app.conf.timezone = 'UTC'


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
