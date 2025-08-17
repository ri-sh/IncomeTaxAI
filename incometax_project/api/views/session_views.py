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
            # URL decode the pk parameter in case it's URL encoded
            import urllib.parse
            decoded_pk = urllib.parse.unquote(pk)
            session_id = signer.unsign(decoded_pk)
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
            # URL decode the pk parameter in case it's URL encoded
            import urllib.parse
            decoded_pk = urllib.parse.unquote(pk)
            session_id = signer.unsign(decoded_pk)
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

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Recalculate tax with user-provided data"""
        signer = Signer()
        try:
            # URL decode the pk parameter in case it's URL encoded
            import urllib.parse
            decoded_pk = urllib.parse.unquote(pk)
            session_id = signer.unsign(decoded_pk)
            session = ProcessingSession.objects.get(pk=session_id)
        except (BadSignature, ProcessingSession.DoesNotExist):
            return Response({'error': 'Invalid session ID'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Get user input data
            input_data = request.data
            regime = input_data.get('regime', 'old')
            income_data = input_data.get('income', {})
            deductions_data = input_data.get('deductions', {})
            
            # Import the enhanced tax calculator
            from api.utils.tax_engine import IncomeTaxCalculator, DeductionCalculator
            
            # Calculate gross income
            gross_income = (
                income_data.get('basic_salary', 0) +
                income_data.get('perquisites', 0) +
                income_data.get('bank_interest', 0) +
                income_data.get('dividend_income', 0)
            )
            
            # Calculate deductions based on regime
            if regime == 'old':
                # Old regime deductions
                old_deductions = DeductionCalculator.calculate_old_regime_deductions(
                    hra_received=income_data.get('hra_received', 0),
                    basic_salary=income_data.get('basic_salary', 0),
                    rent_paid=deductions_data.get('rent_paid', 0),
                    elss_investments=deductions_data.get('section_80c', 0),
                    employee_pf=0,  # Not provided in UI
                    nps_additional=deductions_data.get('section_80ccd_1b', 0),
                    professional_tax=deductions_data.get('professional_tax', 0),
                    health_insurance_premium=deductions_data.get('section_80d', 0),
                    parents_health_insurance=deductions_data.get('parents_health_insurance', 0),
                    charitable_donations=deductions_data.get('section_80g', 0),
                    charity_type=deductions_data.get('charity_type', '50_percent'),
                    education_loan_interest=deductions_data.get('section_80e', 0),
                    loan_year=deductions_data.get('loan_year', 1),
                    savings_interest=income_data.get('bank_interest', 0),
                    age_above_60=deductions_data.get('age_above_60', False)
                )
                
                new_deductions = DeductionCalculator.calculate_new_regime_deductions(75000)
                
                # Calculate taxes
                old_taxable = gross_income - old_deductions['total_deductions']
                new_taxable = gross_income - new_deductions['total_deductions']
                
                old_tax = IncomeTaxCalculator.calculate_old_regime_tax(old_taxable)
                new_tax = IncomeTaxCalculator.calculate_new_regime_tax(new_taxable)
                
                # Calculate detailed breakdown for old regime
                old_income_tax = IncomeTaxCalculator.calculate_tax_by_slabs(old_taxable, IncomeTaxCalculator.OLD_REGIME_SLABS)
                old_cess = old_income_tax * 0.04
                
                # Calculate detailed breakdown for new regime
                new_income_tax_base = IncomeTaxCalculator.calculate_tax_by_slabs(new_taxable, IncomeTaxCalculator.NEW_REGIME_SLABS)
                new_rebate_87a = IncomeTaxCalculator.calculate_rebate_87a(new_taxable, new_income_tax_base)
                new_income_tax = new_income_tax_base - new_rebate_87a
                new_surcharge = IncomeTaxCalculator.calculate_surcharge(new_income_tax, new_taxable, regime='new')
                new_cess = (new_income_tax + new_surcharge) * 0.04
                
            else:
                # New regime only
                new_deductions = DeductionCalculator.calculate_new_regime_deductions(
                    standard_deduction=75000
                )
                
                old_deductions = {'total_deductions': 0}  # Placeholder
                
                # Calculate taxes
                new_taxable = gross_income - new_deductions['total_deductions']
                old_taxable = gross_income  # No deductions for comparison
                
                new_tax = IncomeTaxCalculator.calculate_new_regime_tax(new_taxable)
                old_tax = IncomeTaxCalculator.calculate_old_regime_tax(old_taxable)
                
                # Calculate detailed breakdown for new regime
                new_income_tax_base = IncomeTaxCalculator.calculate_tax_by_slabs(new_taxable, IncomeTaxCalculator.NEW_REGIME_SLABS)
                new_rebate_87a = IncomeTaxCalculator.calculate_rebate_87a(new_taxable, new_income_tax_base)
                new_income_tax = new_income_tax_base - new_rebate_87a
                new_surcharge = IncomeTaxCalculator.calculate_surcharge(new_income_tax, new_taxable, regime='new')
                new_cess = (new_income_tax + new_surcharge) * 0.04
                
                # Calculate old regime for comparison
                old_income_tax = IncomeTaxCalculator.calculate_tax_by_slabs(old_taxable, IncomeTaxCalculator.OLD_REGIME_SLABS)
                old_cess = old_income_tax * 0.04
            
            # Create response data structure
            tax_summary = {
                'gross_total_income': gross_income,
                'income_breakdown': {
                    'salary_income': {
                        'basic_and_allowances_17_1': income_data.get('basic_salary', 0),
                        'perquisites_espp_17_2': income_data.get('perquisites', 0),
                        'hra_received': income_data.get('hra_received', 0)
                    },
                    'other_income': {
                        'bank_interest': income_data.get('bank_interest', 0),
                        'dividend_income': income_data.get('dividend_income', 0)
                    }
                },
                'deductions_old_regime': old_deductions,
                'deductions_new_regime': new_deductions,
                'tax_calculation_old_regime': {
                    'taxable_income': max(0, old_taxable),
                    'income_tax': old_income_tax,
                    'surcharge': 0,  # Simplified for now
                    'cess': old_cess,
                    'total_liability': old_tax,
                    'tds_paid': income_data.get('tds_paid', 0),
                    'additional_tax_payable': max(0, old_tax - income_data.get('tds_paid', 0)),
                    'refund_due': max(0, income_data.get('tds_paid', 0) - old_tax)
                },
                'tax_calculation_new_regime': {
                    'taxable_income': max(0, new_taxable),
                    'income_tax': new_income_tax,
                    'rebate_87a': new_rebate_87a if regime == 'new' or 'new_rebate_87a' in locals() else 0,
                    'surcharge': new_surcharge if regime == 'new' or 'new_surcharge' in locals() else 0,
                    'cess': new_cess if regime == 'new' or 'new_cess' in locals() else 0,
                    'total_liability': new_tax,
                    'tds_paid': income_data.get('tds_paid', 0),
                    'additional_tax_payable': max(0, new_tax - income_data.get('tds_paid', 0)),
                    'refund_due': max(0, income_data.get('tds_paid', 0) - new_tax)
                }
            }
            
            # Update the session's analysis results
            AnalysisResult.objects.filter(session=session, document__isnull=True).delete()
            
            # Create new analysis result
            AnalysisResult.objects.create(
                session=session,
                result_data=tax_summary
            )
            
            logger.info(f"Recalculated tax for session {session_id} with regime {regime}")
            
            return Response({
                'success': True,
                'tax_summary': tax_summary,
                'message': f'Tax recalculated successfully for {regime} regime'
            })
            
        except Exception as e:
            logger.error(f"Error recalculating tax for session {session_id}: {e}", exc_info=True)
            return Response({
                'error': 'Failed to recalculate tax',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)