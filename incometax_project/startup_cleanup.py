#!/usr/bin/env python3
"""
Startup cleanup script that runs when containers start
"""

import os
import sys
import time
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')

def wait_for_database():
    """Wait for database to be ready"""
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            django.setup()
            from django.db import connection
            connection.ensure_connection()
            print("✅ Database connection established")
            return True
        except Exception as e:
            attempt += 1
            print(f"⏳ Waiting for database... attempt {attempt}/{max_attempts}")
            time.sleep(2)
    
    print("❌ Database connection failed after 30 attempts")
    return False

def startup_cleanup():
    """Run cleanup tasks on container startup"""
    print("🚀 Running startup cleanup...")
    
    try:
        from api.cleanup_tasks import cleanup_dead_sessions, reset_stuck_documents
        
        # Reset stuck documents first (gentle)
        print("🔄 Resetting stuck documents...")
        result = reset_stuck_documents()
        print(f"   ✅ {result.get('message', 'Reset completed')}")
        
        # Clean dead sessions (more aggressive)
        print("🧹 Cleaning dead sessions...")
        result = cleanup_dead_sessions()
        print(f"   ✅ {result.get('message', 'Cleanup completed')}")
        
        print("✅ Startup cleanup completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Startup cleanup failed: {e}")
        return False

def main():
    print("🌟 Container Startup Cleanup")
    print("===========================")
    
    # Wait for database
    if not wait_for_database():
        sys.exit(1)
    
    # Run cleanup
    if startup_cleanup():
        print("🎉 Container is ready for processing!")
        sys.exit(0)
    else:
        print("⚠️  Startup cleanup had issues, but continuing...")
        sys.exit(0)  # Don't fail container startup

if __name__ == "__main__":
    main()