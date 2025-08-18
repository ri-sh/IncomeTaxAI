"""
Railway Production Settings for IncomeTax AI
Optimized for Railway's cloud platform
"""

import os
import dj_database_url
from .settings import *

# Railway automatically provides PORT
PORT = int(os.environ.get('PORT', 8000))

# Debug settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
TEMPLATE_DEBUG = DEBUG

# Allowed hosts for Railway
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    # Railway domains
    '*.railway.app',
    '*.up.railway.app',
]

# Add any custom domain from environment
if 'RAILWAY_STATIC_URL' in os.environ:
    import re
    domain = re.sub(r'^https?://', '', os.environ['RAILWAY_STATIC_URL'])
    ALLOWED_HOSTS.append(domain)

# CSRF trusted origins for Railway
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
]

# Database configuration (Railway auto-provides DATABASE_URL)
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ['DATABASE_URL'],
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback for local development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'incometax_db',
            'USER': 'incometax_user',
            'PASSWORD': 'incometax_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Redis configuration (Railway auto-provides REDIS_URL)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Celery configuration for Railway
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_ALWAYS_EAGER = False  # Disable for production
CELERY_WORKER_CONCURRENCY = 2  # Limited for Railway resource constraints

# Static files configuration for Railway
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Security settings for production
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True').lower() == 'true'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'True').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session configuration
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Logging configuration for Railway
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'incometax_project': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Privacy Engine configuration
PRIVACY_ENGINE_ENABLED = os.environ.get('PRIVACY_ENGINE_ENABLED', 'true').lower() == 'true'
ENCRYPTION_SALT = os.environ.get('ENCRYPTION_SALT', 'default-salt-change-in-production')

# Ollama configuration (external service or Railway deployment)
OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'qwen2.5:3b')

# Ollama connection settings for production
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', 120))  # 2 minutes
OLLAMA_MAX_RETRIES = int(os.environ.get('OLLAMA_MAX_RETRIES', 3))
OLLAMA_RETRY_DELAY = int(os.environ.get('OLLAMA_RETRY_DELAY', 5))  # seconds

# Validate Ollama configuration
if 'RAILWAY_ENVIRONMENT' in os.environ:
    if not OLLAMA_BASE_URL or OLLAMA_BASE_URL == 'http://localhost:11434':
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "OLLAMA_BASE_URL not configured for production. "
            "Please set OLLAMA_BASE_URL to your Railway Ollama service URL."
        )

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        }
    }
}

# Email configuration for Railway
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# Default from email
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
SERVER_EMAIL = EMAIL_HOST_USER

# Railway deployment optimizations
if 'RAILWAY_ENVIRONMENT' in os.environ:
    # Railway-specific optimizations
    CONN_MAX_AGE = 600  # Database connection pooling
    
    # Middleware optimization
    MIDDLEWARE = [
        'whitenoise.middleware.WhiteNoiseMiddleware',
    ] + MIDDLEWARE
    
    # Additional security for production
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True