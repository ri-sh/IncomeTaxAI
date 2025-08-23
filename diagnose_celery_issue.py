#!/usr/bin/env python3
"""
Diagnose why Celery tasks are not processing
"""
import requests
import time

def check_celery_issue():
    """Check what's wrong with Celery task processing"""
    print("🔍 Diagnosing Celery Task Processing Issue")
    print("=" * 50)
    
    base_url = "https://incometax-simple-production.up.railway.app"
    
    # Test 1: Simple Celery test
    print("\n1️⃣ Testing basic Celery connectivity...")
    try:
        response = requests.post(f"{base_url}/api/sessions/test_celery/")
        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')
            print(f"   ✅ Task created: {task_id}")
            print(f"   📊 Initial state: {data.get('task_state')}")
            
            # Wait and check if task progresses
            print("\n   ⏳ Waiting 10 seconds to see if task progresses...")
            time.sleep(10)
            
            # Check task again (we can't directly query task status via API, but we can try the test again)
            response2 = requests.post(f"{base_url}/api/sessions/test_celery/")
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get('task_state') == 'SUCCESS':
                    print(f"   ✅ Celery worker is processing tasks correctly")
                    return True
                else:
                    print(f"   ⚠️ Task still in state: {data2.get('task_state')}")
                    print("   💡 Celery worker may not be picking up tasks")
            
        else:
            print(f"   ❌ Celery test failed: {response.status_code}")
            
    except Exception as e:
        print(f"   💥 Celery test error: {e}")
    
    # Test 2: Check what's in Redis/task queue
    print("\n2️⃣ Checking for task queue issues...")
    print("   💡 On Railway, common issues:")
    print("      - Celery worker not connected to Redis")
    print("      - Worker pool configuration issues")  
    print("      - Django settings mismatch")
    print("      - Model import errors preventing task execution")
    
    return False

if __name__ == '__main__':
    issue_found = check_celery_issue()
    
    print("\n" + "=" * 50)
    if not issue_found:
        print("❌ CELERY WORKER ISSUE DETECTED")
        print("\n🔧 Likely causes:")
        print("   1. Celery worker not processing tasks from Redis")
        print("   2. Model import errors in Celery tasks") 
        print("   3. Django settings mismatch between web and worker")
        print("   4. Pool configuration issues (prefork vs solo)")
        
        print("\n💡 Solutions:")
        print("   1. Check Railway logs for Celery worker errors")
        print("   2. Switch to eager mode for debugging: CELERY_TASK_ALWAYS_EAGER=True")
        print("   3. Check if Redis is properly connected")
        print("   4. Verify Celery task imports work correctly")