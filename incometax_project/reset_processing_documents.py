#!/usr/bin/env python3
"""
Reset documents stuck in processing state
"""

import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'incometax_project.settings')
django.setup()

from documents.models import Document, ProcessingSession, AnalysisTask

def reset_stuck_documents():
    """Reset documents and sessions stuck in processing state"""
    try:
        # Find documents stuck in processing
        stuck_docs = Document.objects.filter(status=Document.Status.PROCESSING)
        stuck_sessions = ProcessingSession.objects.filter(status=ProcessingSession.Status.PROCESSING)
        stuck_tasks = AnalysisTask.objects.filter(status=AnalysisTask.Status.STARTED)
        
        print(f"🔍 Found:")
        print(f"   {stuck_docs.count()} documents stuck in processing")
        print(f"   {stuck_sessions.count()} sessions stuck in processing") 
        print(f"   {stuck_tasks.count()} tasks stuck in started state")
        
        if stuck_docs.exists() or stuck_sessions.exists() or stuck_tasks.exists():
            print("🔄 Resetting stuck items...")
            
            # Reset documents to uploaded state
            stuck_docs.update(status=Document.Status.UPLOADED)
            print(f"   Reset {stuck_docs.count()} documents to UPLOADED")
            
            # Reset sessions to pending state
            stuck_sessions.update(status=ProcessingSession.Status.PENDING)
            print(f"   Reset {stuck_sessions.count()} sessions to PENDING")
            
            # Reset tasks to pending state
            stuck_tasks.update(status=AnalysisTask.Status.PENDING)
            print(f"   Reset {stuck_tasks.count()} tasks to PENDING")
            
            print("✅ Reset completed - documents ready for reprocessing")
        else:
            print("✅ No stuck documents found")
            
        return True
        
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

if __name__ == "__main__":
    if reset_stuck_documents():
        exit(0)
    else:
        exit(1)