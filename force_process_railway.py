#!/usr/bin/env python3
"""
Force process stuck documents on Railway using management command API
"""
import requests
import json

def force_process_documents():
    """Trigger processing of stuck documents via Railway API"""
    print("🔧 Force Processing Stuck Documents on Railway")
    print("=" * 50)
    
    # We need to create a session and trigger analysis
    # Since the upload logs show documents exist but aren't being processed
    
    # Try to access a recent session that has documents
    session_ids_to_try = [
        # These are from the recent logs showing document uploads
        "ODU5NjVmMjMtNTI3Zi00MmZmLWEzMWItYzFmMzcwNzlmYmQzOm5BTnVwRlpacnU2V1c0bTY1OEJyeGxtLU1Pb2xBd09GNU5pdUFhXzRFNEk=",
        "NDI4NmVlMjMtZDZhNy00MmZmLWEzMWItYzFmMzcwNzlmYmQzOm5BTnVwRlpacnU2V1c0bTY1OEJyeGxtLU1Pb2xBd09GNU5pdUFhXzRFNEk="
    ]
    
    base_url = "https://incometax-simple-production.up.railway.app"
    
    for session_id in session_ids_to_try:
        print(f"\n🔍 Checking session: {session_id[:20]}...")
        
        try:
            # Check session status first
            status_response = requests.get(f"{base_url}/api/sessions/{session_id}/status/")
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"   📊 Session status: {status_data.get('session_status')}")
                print(f"   📄 Documents: {status_data.get('total_documents', 0)}")
                
                docs = status_data.get('documents', [])
                uploaded_docs = [d for d in docs if d.get('status') == 'UPLOADED']
                
                if uploaded_docs:
                    print(f"   📋 Found {len(uploaded_docs)} documents needing processing:")
                    for doc in uploaded_docs:
                        print(f"      - {doc.get('filename')}: {doc.get('status')}")
                    
                    # Try to trigger analysis
                    print(f"\n🚀 Triggering analysis for session...")
                    analyze_response = requests.post(f"{base_url}/api/sessions/{session_id}/analyze/")
                    
                    if analyze_response.status_code == 202:
                        analyze_data = analyze_response.json()
                        print(f"   ✅ Analysis started!")
                        print(f"   📋 Task ID: {analyze_data.get('task_id')}")
                        return True
                    else:
                        print(f"   ❌ Analysis failed: {analyze_response.status_code}")
                        try:
                            error_data = analyze_response.json()
                            print(f"   Error: {error_data}")
                        except:
                            print(f"   Error text: {analyze_response.text}")
                else:
                    print("   ✅ No documents need processing")
                    
            elif status_response.status_code == 403:
                print("   ⚠️ Session permission denied (expired or invalid)")
            else:
                print(f"   ❌ Status check failed: {status_response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error checking session: {e}")
    
    return False

def test_direct_celery():
    """Test Celery worker directly"""
    print("\n🔧 Testing Celery Worker Direct")
    print("=" * 30)
    
    base_url = "https://incometax-simple-production.up.railway.app"
    
    try:
        response = requests.post(f"{base_url}/api/sessions/test_celery/")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Celery test: {data.get('message')}")
            print(f"   📋 Task state: {data.get('task_state')}")
            print(f"   🔄 Task ready: {data.get('task_ready')}")
            return True
        else:
            print(f"   ❌ Celery test failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   💥 Celery test error: {e}")
        return False

if __name__ == '__main__':
    print("🔍 Diagnosing stuck document processing on Railway...")
    
    # Test Celery first
    celery_ok = test_direct_celery()
    
    # Try to force process documents
    if celery_ok:
        success = force_process_documents()
        
        if success:
            print("\n🎉 Analysis triggered! Documents should start processing.")
            print("💡 Check the Railway logs to see processing progress.")
        else:
            print("\n❌ Could not trigger processing.")
            print("💡 May need to check Railway deployment logs for errors.")
    else:
        print("\n❌ Celery worker issues detected.")
        print("💡 Check Railway logs for Celery startup errors.")