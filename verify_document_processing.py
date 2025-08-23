#!/usr/bin/env python3
"""
Verify that document processing works end-to-end on Railway
"""
import requests
import time
import json

def test_document_processing():
    """Test complete document processing flow"""
    print("🚀 Testing Document Processing on Railway")
    print("=" * 50)
    
    base_url = "https://incometax-simple-production.up.railway.app"
    
    # Step 1: Create session
    print("\n1️⃣ Creating new session...")
    try:
        response = requests.post(f"{base_url}/api/sessions/")
        if response.status_code != 201:
            print(f"   ❌ Session creation failed: {response.status_code}")
            return False
            
        session_data = response.json()
        session_id = session_data['session_id']
        print(f"   ✅ Session created: {session_id[:20]}...")
        
    except Exception as e:
        print(f"   💥 Session creation error: {e}")
        return False
    
    # Step 2: Upload test document
    print("\n2️⃣ Uploading test document...")
    test_content = """SALARY SLIP - FEB 2025

Employee: John Doe
PAN: ABCDE1234F
Employee ID: 12345

EARNINGS:
Basic Salary: ₹50,000
HRA: ₹20,000
Special Allowance: ₹10,000
Gross Salary: ₹80,000

DEDUCTIONS:
PF: ₹6,000
Professional Tax: ₹200
Total Deductions: ₹6,200

NET SALARY: ₹73,800

TDS DEDUCTED: ₹2,000
"""
    
    try:
        files = {'files': ('test_salary_slip.txt', test_content, 'text/plain')}
        response = requests.post(f"{base_url}/api/sessions/{session_id}/upload_document/", files=files)
        
        if response.status_code == 201:
            print("   ✅ Document uploaded successfully")
        else:
            print(f"   ❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   💥 Upload error: {e}")
        return False
    
    # Step 3: Trigger analysis  
    print("\n3️⃣ Starting document analysis...")
    try:
        response = requests.post(f"{base_url}/api/sessions/{session_id}/analyze/")
        
        if response.status_code == 202:
            analysis_data = response.json()
            print("   ✅ Analysis started")
            print(f"   Task ID: {analysis_data.get('task_id', 'N/A')}")
        else:
            print(f"   ❌ Analysis failed to start: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   💥 Analysis start error: {e}")
        return False
    
    # Step 4: Monitor processing
    print("\n4️⃣ Monitoring document processing...")
    max_attempts = 30  # 1 minute
    
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{base_url}/api/sessions/{session_id}/status/")
            
            if response.status_code == 200:
                status_data = response.json()
                session_status = status_data.get('session_status')
                total_docs = status_data.get('total_documents', 0)
                processed_docs = status_data.get('processed_documents', 0)
                failed_docs = status_data.get('failed_documents', 0)
                
                print(f"   📊 Attempt {attempt + 1}: {session_status} - Processed: {processed_docs}/{total_docs}")
                
                # Check individual document status
                for doc in status_data.get('documents', []):
                    doc_status = doc.get('status')
                    doc_filename = doc.get('filename')
                    print(f"      📄 {doc_filename}: {doc_status}")
                    
                    if doc_status == 'PROCESSED':
                        print("   🎉 Document processed successfully!")
                        return True
                    elif doc_status == 'FAILED':
                        print(f"   ❌ Document processing failed")
                        return False
                        
                # Check if session completed
                if session_status == 'COMPLETED':
                    if processed_docs > 0:
                        print("   🎉 Session completed with processed documents!")
                        return True
                    else:
                        print("   ⚠️ Session completed but no documents processed")
                        return False
                
            else:
                print(f"   ⚠️ Status check failed: {response.status_code}")
            
            time.sleep(2)  # Wait 2 seconds between checks
            
        except Exception as e:
            print(f"   ⚠️ Status check error: {e}")
            time.sleep(2)
    
    print("   ⏰ Timeout waiting for processing")
    return False

if __name__ == '__main__':
    success = test_document_processing()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Document processing is working on Railway!")
        print("✅ The model mismatch issue has been resolved")
        print("✅ Documents will no longer get stuck in processing")
    else:
        print("❌ FAILED: Document processing still has issues")
        print("💡 May need further investigation")