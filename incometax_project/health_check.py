#!/usr/bin/env python3
"""
Health check script for debugging Celery worker issues
Run this inside the Celery container to diagnose problems
"""

import os
import sys
import time
import requests
import redis

# Configure Django settings before importing Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')

import django
django.setup()

from celery import Celery
from django.conf import settings

def check_ollama_connection():
    """Test Ollama service connectivity"""
    print("🤖 Testing Ollama connection...")
    ollama_url = os.environ.get('OLLAMA_BASE_URL', 'http://ollama:11434')
    
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=30)
        if response.status_code == 200:
            print(f"✅ Ollama connected successfully at {ollama_url}")
            models = response.json().get('models', [])
            print(f"   Available models: {[m['name'] for m in models]}")
            return True
        else:
            print(f"❌ Ollama responded with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        return False

def check_redis_connection():
    """Test Redis connectivity"""
    print("🔴 Testing Redis connection...")
    redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print(f"✅ Redis connected successfully at {redis_url}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        return False

def check_celery_broker():
    """Test Celery broker connectivity"""
    print("📦 Testing Celery broker...")
    broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
    
    try:
        app = Celery('test')
        app.config_from_object('django.conf:settings', namespace='CELERY')
        
        # Test broker connection
        conn = app.connection()
        conn.ensure_connection(max_retries=3)
        print("✅ Celery broker connected successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Celery broker: {e}")
        return False

def check_memory_usage():
    """Check current memory usage"""
    print("💾 Checking memory usage...")
    try:
        # Use /proc/meminfo on Linux
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        mem_total = None
        mem_available = None
        
        for line in meminfo.split('\n'):
            if 'MemTotal:' in line:
                mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
            elif 'MemAvailable:' in line:
                mem_available = int(line.split()[1]) * 1024  # Convert KB to bytes
        
        if mem_total and mem_available:
            used_percent = ((mem_total - mem_available) / mem_total) * 100
            print(f"   Total memory: {mem_total / (1024**3):.1f} GB")
            print(f"   Available memory: {mem_available / (1024**3):.1f} GB")
            print(f"   Memory usage: {used_percent:.1f}%")
            
            if used_percent > 90:
                print("⚠️  High memory usage detected")
            else:
                print("✅ Memory usage looks good")
            return True
        else:
            print("⚠️  Could not parse memory information")
            return False
    except Exception as e:
        print(f"⚠️  Cannot check memory: {e}")
        return False

def test_ollama_inference():
    """Test actual Ollama inference"""
    print("🧠 Testing Ollama inference...")
    ollama_url = os.environ.get('OLLAMA_BASE_URL', 'http://ollama:11434')
    
    try:
        # Test simple completion
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": "Hello, respond with just 'OK'",
            "stream": False
        }
        
        response = requests.post(
            f"{ollama_url}/api/generate", 
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ollama inference successful: {result.get('response', 'No response')[:50]}...")
            return True
        else:
            print(f"❌ Ollama inference failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ollama inference failed: {e}")
        return False

def check_cleanup_status():
    """Check cleanup tasks and database health"""
    print("🧹 Checking cleanup status...")
    try:
        import django
        django.setup()
        from documents.models import ProcessingSession, Document
        from datetime import timedelta
        from django.utils import timezone
        
        # Check for stuck sessions (use created_at for sessions, uploaded_at for docs)
        stuck_threshold = timezone.now() - timedelta(hours=1)
        stuck_sessions = ProcessingSession.objects.filter(
            status=ProcessingSession.Status.PROCESSING,
            created_at__lt=stuck_threshold
        ).count()
        
        stuck_docs = Document.objects.filter(
            status=Document.Status.PROCESSING,
            uploaded_at__lt=stuck_threshold
        ).count()
        
        total_sessions = ProcessingSession.objects.count()
        total_docs = Document.objects.count()
        
        print(f"   📊 Database status:")
        print(f"      Total sessions: {total_sessions}")
        print(f"      Total documents: {total_docs}")
        print(f"      Stuck sessions (>1h): {stuck_sessions}")
        print(f"      Stuck documents (>1h): {stuck_docs}")
        
        if stuck_sessions == 0 and stuck_docs == 0:
            print("   ✅ No stuck items found")
            return True
        else:
            print(f"   ⚠️  Found {stuck_sessions} stuck sessions and {stuck_docs} stuck documents")
            return False
            
    except Exception as e:
        print(f"   ❌ Cleanup check failed: {e}")
        return False

def check_celery_beat():
    """Check if Celery Beat is running periodic tasks"""
    print("⏰ Checking Celery Beat status...")
    try:
        import django
        django.setup()
        from django_celery_beat.models import PeriodicTask
        
        # Check if periodic tasks are defined
        cleanup_tasks = PeriodicTask.objects.filter(
            name__icontains='cleanup'
        ).count()
        
        if cleanup_tasks > 0:
            print(f"   ✅ Found {cleanup_tasks} cleanup periodic tasks")
            return True
        else:
            print("   ⚠️  No cleanup periodic tasks found")
            return False
            
    except ImportError:
        print("   ⚠️  django-celery-beat not installed, skipping")
        return True
    except Exception as e:
        print(f"   ❌ Beat check failed: {e}")
        return False

def main():
    print("🔍 Starting comprehensive health check...\n")
    
    checks = [
        check_redis_connection,
        check_ollama_connection,
        check_celery_broker,
        check_memory_usage,
        check_cleanup_status,
        test_ollama_inference
    ]
    
    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"❌ Check failed with exception: {e}")
            results.append(False)
        print()
    
    print("📋 Health Check Summary:")
    print(f"   Redis: {'✅' if results[0] else '❌'}")
    print(f"   Ollama connectivity: {'✅' if results[1] else '❌'}")
    print(f"   Celery broker: {'✅' if results[2] else '❌'}")
    print(f"   Memory usage: {'✅' if results[3] else '❌'}")
    print(f"   Cleanup status: {'✅' if results[4] else '❌'}")
    print(f"   Ollama inference: {'✅' if results[5] else '❌'}")
    
    if all(results):
        print("\n🎉 All checks passed! System should be ready for document processing.")
        print("\n💡 Cleanup automation:")
        print("   - Every 10 minutes: Reset stuck documents")
        print("   - Every hour: Clean dead sessions and files")
        print("   - Daily at 2 AM: Clean old task results")
        sys.exit(0)
    else:
        print("\n⚠️  Some checks failed. Please review the issues above.")
        print("\n🔧 Troubleshooting:")
        if not results[4]:  # Cleanup status failed
            print("   - Run: docker-compose exec web python cleanup_now.py")
        sys.exit(1)

if __name__ == "__main__":
    main()
