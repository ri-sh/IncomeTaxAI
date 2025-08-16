"""
Session Management Views for TaxSahaj Django Application
Handles document sessions, uploads, and analysis triggers
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.signing import Signer, BadSignature
from documents.models import ProcessingSession, Document, AnalysisTask, AnalysisResult
from api.serializers import ProcessingSessionSerializer, DocumentSerializer
from api.portal_filing_assistant import PortalFilingAssistant
import logging
import json

logger = logging.getLogger(__name__)


class SessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing document processing sessions
    
    Provides CRUD operations for sessions plus:
    - upload_document: Upload files to a session
    - analyze: Trigger analysis of uploaded documents
    """
    queryset = ProcessingSession.objects.all()
    serializer_class = ProcessingSessionSerializer

    def create(self, request, *args, **kwargs):
        """Create a new processing session with signed ID"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        # Encrypt the session ID for security
        signer = Signer()
        signed_session_id = signer.sign(str(serializer.instance.id))
        
        return Response({
            'session_id': signed_session_id,
            'created_at': serializer.instance.created_at,
            'status': serializer.instance.status
        }, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """Upload documents to a processing session"""
        signer = Signer()
        try:
            session_id = signer.unsign(pk)
            session = ProcessingSession.objects.get(pk=session_id)
        except (BadSignature, ProcessingSession.DoesNotExist):
            return Response({'error': 'Invalid session ID'}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('files')
        if not files:
            return Response({'error': 'No files provided'}, status=status.HTTP_400_BAD_REQUEST)

        documents = []
        for file in files:
            document = Document.objects.create(
                session=session,
                file=file,
                filename=file.name
            )
            documents.append(document)

        # Update session status
        if session.status == ProcessingSession.Status.CREATED:
            session.status = ProcessingSession.Status.PENDING
            session.save()

        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        """Trigger analysis of documents in a session"""
        signer = Signer()
        try:
            session_id = signer.unsign(pk)
            session = ProcessingSession.objects.get(pk=session_id)
        except (BadSignature, ProcessingSession.DoesNotExist):
            return Response({'error': 'Invalid session ID'}, status=status.HTTP_404_NOT_FOUND)

        # Check if documents exist
        if not session.documents.exists():
            return Response({'error': 'No documents uploaded for analysis'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if analysis already exists
        existing_task = AnalysisTask.objects.filter(session=session).first()
        if existing_task:
            if existing_task.status in [AnalysisTask.Status.PENDING, AnalysisTask.Status.STARTED]:
                return Response({
                    'message': 'Analysis already in progress', 
                    'task_id': existing_task.celery_task_id
                }, status=status.HTTP_200_OK)
            elif existing_task.status == AnalysisTask.Status.SUCCESS:
                return Response({
                    'message': 'Analysis already completed', 
                    'task_id': existing_task.celery_task_id
                }, status=status.HTTP_200_OK)
            else:
                # Previous task failed, delete it and create new one
                existing_task.delete()

        # Update session status
        session.status = ProcessingSession.Status.PROCESSING
        session.save()

        # Trigger parallel Celery task processing
        from api.tasks import process_session_analysis_parallel
        task = process_session_analysis_parallel.delay(session_id)

        # Create AnalysisTask record
        AnalysisTask.objects.create(
            session=session,
            celery_task_id=task.id
        )

        return Response({
            'message': 'Analysis started', 
            'task_id': task.id,
            'session_status': session.status
        }, status=status.HTTP_202_ACCEPTED)
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get status of a processing session"""
        signer = Signer()
        try:
            session_id = signer.unsign(pk)
            session = ProcessingSession.objects.get(pk=session_id)
        except (BadSignature, ProcessingSession.DoesNotExist):
            return Response({'error': 'Invalid session ID'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get associated task if exists
        task = AnalysisTask.objects.filter(session=session).first()
        task_status = task.status if task else None
        
        # Get detailed document statuses with processing info
        documents = session.documents.all()
        document_statuses = []
        
        for doc in documents:
            doc_info = {
                'id': str(doc.pk),
                'filename': doc.filename,
                'status': doc.status,
                'uploaded_at': doc.uploaded_at,
                'processed_at': getattr(doc, 'processed_at', None),
                'file_size': doc.file.size if doc.file else 0,
                'progress_percentage': 0
            }
            
            # Calculate progress percentage based on status
            if doc.status == Document.Status.UPLOADED:
                doc_info['progress_percentage'] = 0
                doc_info['status_text'] = 'Queued for processing'
            elif doc.status == Document.Status.PROCESSING:
                doc_info['progress_percentage'] = 50
                doc_info['status_text'] = 'Processing document...'
            elif doc.status == Document.Status.PROCESSED:
                doc_info['progress_percentage'] = 100
                doc_info['status_text'] = 'Completed successfully'
            elif doc.status == Document.Status.FAILED:
                doc_info['progress_percentage'] = 0
                doc_info['status_text'] = 'Processing failed'
            else:
                doc_info['status_text'] = 'Unknown status'
            
            document_statuses.append(doc_info)
        
        # Calculate overall progress
        total_docs = documents.count()
        processed_docs = documents.filter(status=Document.Status.PROCESSED).count()
        processing_docs = documents.filter(status=Document.Status.PROCESSING).count()
        failed_docs = documents.filter(status=Document.Status.FAILED).count()
        
        overall_progress = 0
        if total_docs > 0:
            overall_progress = int((processed_docs / total_docs) * 100)
        
        # Get distributed task info if available (simplified for now)
        distributed_tasks = []
        # Note: In a full implementation, we'd store this in a separate metadata table
        # For now, we'll detect distributed mode by checking if we have the new task
        
        return Response({
            'session_id': pk,
            'session_status': session.status,
            'task_status': task_status,
            'created_at': session.created_at,
            'documents': document_statuses,
            'total_documents': total_docs,
            'processed_documents': processed_docs,
            'processing_documents': processing_docs,
            'failed_documents': failed_docs,
            'overall_progress': overall_progress,
            'distributed_tasks': distributed_tasks,
            'processing_method': 'distributed' if distributed_tasks else 'single'
        })

    @action(detail=True, methods=['get'])
    def analysis_results(self, request, pk=None):
        """Get detailed analysis results for a processing session"""
        signer = Signer()
        try:
            session_id = signer.unsign(pk)
            session = ProcessingSession.objects.get(pk=session_id)
        except (BadSignature, ProcessingSession.DoesNotExist):
            return Response({'error': 'Invalid session ID'}, status=status.HTTP_404_NOT_FOUND)
        
        # Get analysis results 
        analysis_results = AnalysisResult.objects.filter(session=session)
        
        if not analysis_results.exists():
            return Response({'error': 'No analysis results found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Find the detailed tax summary result (no associated document)
        detailed_summary = None
        document_results = []
        
        for result in analysis_results:
            if result.document is None:  # Final tax summary
                result_data = result.result_data
                # Prioritize detailed structure (has income_breakdown) over simple structure
                if 'income_breakdown' in result_data:
                    detailed_summary = result_data
                    break
                elif not detailed_summary:  # Use as fallback if no detailed found
                    detailed_summary = result_data
            else:
                # Document-specific results
                document_results.append({
                    'document_id': str(result.document.pk),
                    'filename': result.document.filename,
                    'document_type': result.result_data.get('document_type', 'unknown'),
                    'data': result.result_data
                })
        
        if not detailed_summary:
            return Response({'error': 'No tax summary found'}, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'session_id': pk,
            'tax_summary': detailed_summary,
            'document_results': document_results,
            'total_documents': len(document_results),
            'session_status': session.status
        })