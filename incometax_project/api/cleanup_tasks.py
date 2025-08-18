"""
Celery tasks for cleaning up dead sessions and orphaned files
"""

import os
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
from documents.models import ProcessingSession, Document, AnalysisTask
from django.conf import settings
from api.utils.pii_logger import get_pii_safe_logger

logger = get_pii_safe_logger(__name__)

@shared_task(bind=True)
def cleanup_dead_sessions(self):
    """
    Clean up sessions that have been stuck in processing state for too long
    Also removes associated files from disk
    """
    try:
        # Define timeout thresholds  
        PROCESSING_TIMEOUT = timedelta(minutes=20)  # 20 minutes max processing time (reduced from 2 hours)
        FAILED_CLEANUP_AGE = timedelta(days=7)   # Clean failed sessions after 7 days
        
        now = timezone.now()
        cleanup_stats = {
            'dead_sessions': 0,
            'dead_documents': 0,
            'dead_tasks': 0,
            'files_deleted': 0,
            'failed_sessions_cleaned': 0
        }
        
        logger.info("🧹 Starting dead session cleanup...")
        
        # 1. Find sessions stuck in processing for too long
        cutoff_time = now - PROCESSING_TIMEOUT
        dead_sessions = ProcessingSession.objects.filter(
            status=ProcessingSession.Status.PROCESSING,
            created_at__lt=cutoff_time
        )
        
        for session in dead_sessions:
            logger.warning(f"Found dead session: {session.id} (stuck for {now - session.created_at})")
            
            # Mark session as failed
            session.status = ProcessingSession.Status.FAILED
            session.save()
            cleanup_stats['dead_sessions'] += 1
            
            # Mark associated task as failed
            if hasattr(session, 'task') and session.task:
                session.task.status = AnalysisTask.Status.FAILED
                session.task.save()
                cleanup_stats['dead_tasks'] += 1
            
            # Mark associated documents as failed and clean up files
            documents = session.documents.all()
            for doc in documents:
                if doc.status in [Document.Status.PROCESSING, Document.Status.UPLOADED]:
                    doc.status = Document.Status.FAILED
                    doc.save()
                    cleanup_stats['dead_documents'] += 1
                
                # Delete file from disk if it exists
                if doc.file and os.path.exists(doc.file.path):
                    try:
                        os.remove(doc.file.path)
                        logger.info(f"Deleted file: {doc.file.path}")
                        cleanup_stats['files_deleted'] += 1
                    except Exception as e:
                        logger.error(f"Failed to delete file {doc.file.path}: {e}")
        
        # 2. Find documents stuck in processing without a session
        orphaned_docs = Document.objects.filter(
            status=Document.Status.PROCESSING,
            uploaded_at__lt=cutoff_time
        )
        
        for doc in orphaned_docs:
            logger.warning(f"Found orphaned processing document: {doc.id}")
            doc.status = Document.Status.FAILED
            doc.save()
            cleanup_stats['dead_documents'] += 1
            
            # Delete file from disk
            if doc.file and os.path.exists(doc.file.path):
                try:
                    os.remove(doc.file.path)
                    cleanup_stats['files_deleted'] += 1
                except Exception as e:
                    logger.error(f"Failed to delete orphaned file {doc.file.path}: {e}")
        
        # 3. Clean up old failed sessions and their files
        old_failed_cutoff = now - FAILED_CLEANUP_AGE
        old_failed_sessions = ProcessingSession.objects.filter(
            status=ProcessingSession.Status.FAILED,
            created_at__lt=old_failed_cutoff
        )
        
        for session in old_failed_sessions:
            logger.info(f"Cleaning up old failed session: {session.id}")
            
            # Delete all associated files
            for doc in session.documents.all():
                if doc.file and os.path.exists(doc.file.path):
                    try:
                        os.remove(doc.file.path)
                        cleanup_stats['files_deleted'] += 1
                    except Exception as e:
                        logger.error(f"Failed to delete old file {doc.file.path}: {e}")
            
            # Delete the session and all related objects
            session.delete()  # Cascades to documents and results
            cleanup_stats['failed_sessions_cleaned'] += 1
        
        # 4. Clean up orphaned files in media directory
        media_docs_path = os.path.join(settings.MEDIA_ROOT, 'documents')
        if os.path.exists(media_docs_path):
            orphaned_files = cleanup_orphaned_files(media_docs_path)
            cleanup_stats['files_deleted'] += orphaned_files
        
        logger.info(f"✅ Cleanup completed: {cleanup_stats}")
        
        return {
            'status': 'success',
            'stats': cleanup_stats,
            'message': f"Cleaned up {cleanup_stats['dead_sessions']} dead sessions, "
                      f"{cleanup_stats['dead_documents']} dead documents, "
                      f"deleted {cleanup_stats['files_deleted']} files"
        }
        
    except Exception as e:
        logger.error(f"❌ Cleanup task failed: {e}")
        raise e

def cleanup_orphaned_files(media_docs_path):
    """
    Remove files from media/documents that don't have corresponding database entries.
    Also validates session IDs to ensure files belong to valid sessions.
    """
    orphaned_count = 0
    
    try:
        for root, dirs, files in os.walk(media_docs_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                
                # Check if this file is referenced in the database
                file_document = Document.objects.filter(file=relative_path).first()
                
                should_delete = False
                delete_reason = ""
                
                if not file_document:
                    # File has no database entry - it's orphaned
                    should_delete = True
                    delete_reason = "no database entry"
                else:
                    # File has database entry, check if session still exists
                    if not ProcessingSession.objects.filter(id=file_document.session_id).exists():
                        # Session was deleted but file still exists
                        should_delete = True
                        delete_reason = f"session {file_document.session_id} no longer exists"
                
                # Time-based cleanup logic
                file_age = datetime.fromtimestamp(os.path.getctime(file_path))
                file_age_delta = timezone.now() - timezone.make_aware(file_age)
                
                if should_delete:
                    # For orphaned files, use shorter timeout (20 minutes instead of 6 hours)
                    if file_age_delta > timedelta(minutes=20):
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted orphaned file: {file_path} (reason: {delete_reason}, age: {file_age_delta})")
                            orphaned_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete orphaned file {file_path}: {e}")
                    else:
                        logger.debug(f"Skipping recent orphaned file: {file_path} (reason: {delete_reason}, age: {file_age_delta})")
                else:
                    # For files with valid database entries, delete if older than 20 minutes
                    # This catches unprocessed files that might be stuck
                    if file_age_delta > timedelta(minutes=20):
                        try:
                            os.remove(file_path)
                            logger.info(f"Deleted old unprocessed file: {file_path} (age: {file_age_delta})")
                            orphaned_count += 1
                        except Exception as e:
                            logger.error(f"Failed to delete old file {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error during orphaned file cleanup: {e}")
    
    return orphaned_count

def validate_file_sessions():
    """
    Additional validation to ensure all files belong to valid sessions.
    Returns statistics about file-session relationships.
    """
    stats = {
        'total_files': 0,
        'valid_files': 0,
        'orphaned_files': 0,
        'invalid_session_files': 0,
        'recent_files_skipped': 0
    }
    
    try:
        media_docs_path = os.path.join(settings.MEDIA_ROOT, 'documents')
        if not os.path.exists(media_docs_path):
            return stats
            
        for root, dirs, files in os.walk(media_docs_path):
            for filename in files:
                stats['total_files'] += 1
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT)
                
                # Check database relationship
                file_document = Document.objects.filter(file=relative_path).first()
                
                if not file_document:
                    stats['orphaned_files'] += 1
                    logger.debug(f"Orphaned file (no DB entry): {relative_path}")
                elif not ProcessingSession.objects.filter(id=file_document.session_id).exists():
                    stats['invalid_session_files'] += 1
                    # Only log session ID, not the file path which may contain PII
                    logger.warning(f"File with invalid session ID: {file_document.session_id}")
                else:
                    stats['valid_files'] += 1
                    
        logger.info(f"File validation complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error during file validation: {e}")
        return stats

@shared_task(bind=True)
def reset_stuck_documents(self):
    """
    Reset documents that have been in processing state for a reasonable time
    This is less aggressive than cleanup_dead_sessions
    """
    try:
        RESET_TIMEOUT = timedelta(minutes=10)  # Reset after 10 minutes (reduced from 30)
        cutoff_time = timezone.now() - RESET_TIMEOUT
        
        stuck_docs = Document.objects.filter(
            status=Document.Status.PROCESSING,
            uploaded_at__lt=cutoff_time
        )
        
        reset_count = 0
        for doc in stuck_docs:
            doc.status = Document.Status.UPLOADED  # Reset to uploaded for retry
            doc.save()
            reset_count += 1
            logger.info_with_filename("Reset stuck document: {filename}", doc.filename)
        
        stuck_sessions = ProcessingSession.objects.filter(
            status=ProcessingSession.Status.PROCESSING,
            created_at__lt=cutoff_time
        )
        
        session_reset_count = 0
        for session in stuck_sessions:
            session.status = ProcessingSession.Status.PENDING
            session.save()
            session_reset_count += 1
            logger.info(f"Reset stuck session: {session.id}")
        
        return {
            'status': 'success',
            'documents_reset': reset_count,
            'sessions_reset': session_reset_count,
            'message': f"Reset {reset_count} documents and {session_reset_count} sessions"
        }
        
    except Exception as e:
        logger.error(f"❌ Reset task failed: {e}")
        raise e

@shared_task(bind=True)
def cleanup_old_task_results(self):
    """
    Clean up old Celery task results from Redis
    """
    try:
        import redis
        redis_client = redis.from_url(settings.CELERY_RESULT_BACKEND)
        
        # Get all task result keys
        task_keys = redis_client.keys("celery-task-meta-*")
        deleted_count = 0
        
        for key in task_keys:
            try:
                # Delete keys older than 24 hours
                ttl = redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    redis_client.expire(key, 86400)  # Set to 24 hours
                elif ttl > 86400:  # More than 24 hours
                    redis_client.delete(key)
                    deleted_count += 1
            except Exception as e:
                logger.error(f"Error processing task key {key}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old task results")
        return {'status': 'success', 'deleted_keys': deleted_count}
        
    except Exception as e:
        logger.error(f"❌ Redis cleanup failed: {e}")
        return {'status': 'failed', 'error': str(e)}