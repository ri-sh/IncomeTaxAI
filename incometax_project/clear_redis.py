#!/usr/bin/env python3
"""
Clear stale Celery tasks from Redis on startup
"""

import redis
import os
import sys

def clear_stale_celery_data():
    """Clear old Celery task data from Redis"""
    try:
        redis_url = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
        r = redis.from_url(redis_url)
        
        print("🔍 Checking for stale Celery data...")
        
        # Get all Celery-related keys
        celery_keys = r.keys("celery-task-meta-*")
        kombu_keys = r.keys("_kombu.binding.*")
        
        total_keys = len(celery_keys) + len(kombu_keys)
        
        if total_keys > 0:
            print(f"🧹 Found {total_keys} stale keys, clearing...")
            
            # Delete task metadata
            if celery_keys:
                r.delete(*celery_keys)
                print(f"   Cleared {len(celery_keys)} task metadata entries")
            
            # Delete kombu bindings
            if kombu_keys:
                r.delete(*kombu_keys)
                print(f"   Cleared {len(kombu_keys)} kombu bindings")
            
            # Clear any hanging queues
            for queue in ['celery', 'celery.pidbox']:
                try:
                    queue_len = r.llen(queue)
                    if queue_len > 0:
                        r.delete(queue)
                        print(f"   Cleared {queue_len} items from {queue} queue")
                except:
                    pass
            
            print("✅ Redis cleanup completed")
        else:
            print("✅ No stale data found")
            
        return True
        
    except Exception as e:
        print(f"❌ Redis cleanup failed: {e}")
        return False

if __name__ == "__main__":
    if clear_stale_celery_data():
        sys.exit(0)
    else:
        sys.exit(1)