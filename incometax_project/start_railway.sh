#!/bin/bash

# Railway Startup Script for IncomeTax AI
echo "🚂 Starting IncomeTax AI on Railway..."

# Set Django settings module for Railway
export DJANGO_SETTINGS_MODULE=incometax_project.settings_railway

# Wait for database to be available
echo "⏳ Waiting for database connection..."
python -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL
db_url = os.environ.get('DATABASE_URL')
if db_url:
    parsed = urlparse(db_url)
    for i in range(30):
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path[1:]
            )
            conn.close()
            print('✅ Database connection successful')
            break
        except:
            print(f'⏳ Waiting for database... ({i+1}/30)')
            time.sleep(2)
    else:
        print('❌ Database connection failed')
        exit(1)
"

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "👤 Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✅ Superuser created: admin/admin123')
else:
    print('ℹ️ Superuser already exists')
"

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Download NLTK data if needed
echo "📚 Downloading NLTK data..."
python -c "
import nltk
import os
nltk_data_dir = os.environ.get('NLTK_DATA', '/app/nltk_data')
try:
    nltk.download('punkt', download_dir=nltk_data_dir, quiet=True)
    nltk.download('stopwords', download_dir=nltk_data_dir, quiet=True)
    print('✅ NLTK data downloaded')
except Exception as e:
    print(f'⚠️ NLTK download warning: {e}')
"

# Start the application
echo "🚀 Starting gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 300 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --access-logfile - \
    --error-logfile - \
    incometax_project.wsgi:application