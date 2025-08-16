"""
Report and Progress Views for TaxSahaj Django Application
Handles report generation and progress tracking
"""

from rest_framework.decorators import api_view
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from documents.models import ProcessingSession, Document, AnalysisTask, AnalysisResult
from datetime import datetime
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
def get_progress(request):
    """Get current processing progress for active sessions"""
    try:
        # Get the most recent active session for this user
        # In a production app, you'd use user authentication
        recent_session = ProcessingSession.objects.filter(
            status__in=[ProcessingSession.Status.PROCESSING, ProcessingSession.Status.PENDING]
        ).order_by('-created_at').first()
        
        if not recent_session:
            return JsonResponse({
                'stage': 'idle',
                'progress': 0,
                'current_file': '',
                'files_processed': 0,
                'total_files': 0,
                'step': 'waiting',
                'timestamp': datetime.now().isoformat()
            })
        
        # Get associated task
        task = recent_session.task
        documents = recent_session.documents.all()
        processed_count = documents.filter(status=Document.Status.PROCESSED).count()
        total_count = documents.count()
        
        if task.status == AnalysisTask.Status.PENDING:
            stage = "Initializing Analysis"
            progress = 5
            step = "init"
        elif task.status == AnalysisTask.Status.STARTED:
            stage = "Processing Documents"
            progress = 20 + (processed_count * 60 // max(total_count, 1))
            step = "processing"
        elif task.status == AnalysisTask.Status.SUCCESS:
            stage = "Analysis Complete"
            progress = 100
            step = "complete"
        else:
            stage = "Analysis Failed"
            progress = 0
            step = "error"
        
        current_processing = documents.filter(status=Document.Status.PROCESSING).first()
        current_file = current_processing.filename if current_processing else ''
        
        return JsonResponse({
            'stage': stage,
            'progress': progress,
            'current_file': current_file,
            'files_processed': processed_count,
            'total_files': total_count,
            'step': step,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return JsonResponse({'error': 'Unable to get progress'}, status=500)


@api_view(['POST'])
def download_report(request):
    """Generate and download detailed tax report"""
    try:
        # Get session ID from request data or use most recent completed session
        session_id = request.data.get('session_id')
        
        if session_id:
            # Find specific session
            try:
                from django.core.signing import Signer
                signer = Signer()
                actual_session_id = signer.unsign(session_id)
                session = ProcessingSession.objects.get(pk=actual_session_id)
            except:
                return JsonResponse({'error': 'Invalid session ID'}, status=400)
        else:
            # Get most recent completed session
            session = ProcessingSession.objects.filter(
                status=ProcessingSession.Status.COMPLETED
            ).order_by('-created_at').first()
            
            if not session:
                return JsonResponse({'error': 'No completed analysis found'}, status=404)
        
        # Get analysis results
        analysis_results = AnalysisResult.objects.filter(session=session)
        
        # Compile tax summary data - prioritize detailed structure over simple structure
        tax_data = {}
        simple_data = {}
        
        for result in analysis_results:
            if result.document is None:  # Final tax summary
                result_data = result.result_data
                # Check if this is the detailed structure (has income_breakdown) or simple structure
                if 'income_breakdown' in result_data:
                    tax_data = result_data  # Prioritize detailed structure
                    break
                else:
                    simple_data = result_data  # Keep as fallback
        
        # Use detailed data if available, otherwise fall back to simple data
        if not tax_data and simple_data:
            tax_data = simple_data
        
        # Create comprehensive report
        report = {
            'report_generated': datetime.now().isoformat(),
            'session_id': str(session.id),
            'analysis_date': session.created_at.isoformat(),
            'tax_analysis': tax_data,
            'report_type': 'Comprehensive Income Tax Analysis',
            'recommendations': generate_recommendations(tax_data),
            'next_steps': [
                "Review the recommended tax regime",
                "Gather any missing investment proofs",
                "Login to the Income Tax e-filing portal", 
                "Fill ITR form with the calculated values",
                "Submit and e-verify your return"
            ],
            'documents_processed': [
                {
                    'filename': doc.filename,
                    'status': doc.status,
                    'uploaded_at': doc.uploaded_at.isoformat()
                }
                for doc in session.documents.all()
            ]
        }
        
        response = HttpResponse(
            json.dumps(report, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename=Tax_Report_{datetime.now().strftime("%Y-%m-%d")}.json'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def generate_recommendations(data: Dict[str, Any]) -> List[str]:
    """Generate personalized tax recommendations based on analysis"""
    recommendations = []
    
    if not data:
        recommendations.append("📋 Complete document analysis to get personalized recommendations")
        return recommendations
    
    # Extract data from new detailed structure
    gross_total_income = data.get('income_breakdown', {}).get('gross_total_income', 0)
    old_regime_data = data.get('tax_calculation_old_regime', {})
    new_regime_data = data.get('tax_calculation_new_regime', {})
    deductions_data = data.get('deductions_old_regime', {})
    regime_comparison = data.get('regime_comparison', {})
    
    old_tax = old_regime_data.get('total_tax_liability', 0)
    new_tax = new_regime_data.get('total_tax_liability', 0)
    total_deductions = deductions_data.get('total_deductions', 0)
    savings = regime_comparison.get('savings_by_old_regime', 0)
    
    # Regime recommendation with exact savings
    recommended_regime = regime_comparison.get('recommended_regime', 'Old Regime')
    if recommended_regime == 'Old Regime' and savings > 0:
        refund_amount = old_regime_data.get('refund_due', 0)
        if refund_amount > 0:
            recommendations.append(f"✅ RECOMMENDED: File under OLD TAX REGIME")
            recommendations.append(f"💰 You will get a REFUND of ₹{refund_amount:,.2f}")
            recommendations.append(f"💡 You save ₹{savings:,.2f} compared to New Regime")
        else:
            recommendations.append(f"✅ RECOMMENDED: File under OLD TAX REGIME to save ₹{savings:,.2f}")
        recommendations.append("📋 Ensure all Section 80C, HRA, and other deduction proofs are ready")
    else:
        recommendations.append(f"✅ RECOMMENDED: File under NEW TAX REGIME")
        recommendations.append("⚡ New regime offers simplicity with standard deduction only")
    
    # Detailed deduction optimization
    section_80c = deductions_data.get('section_80c', 0)
    if section_80c < 150000 and recommended_regime == 'Old Regime':
        shortfall = 150000 - section_80c
        recommendations.append(f"📈 OPPORTUNITY: Invest ₹{shortfall:,.0f} more in ELSS/PPF to maximize Section 80C")
    
    # HRA specific recommendations
    hra_exemption = deductions_data.get('hra_exemption', 0)
    if hra_exemption > 0:
        recommendations.append(f"🏠 HRA benefit: ₹{hra_exemption:,.0f} exemption claimed")
        recommendations.append("📋 Keep rent receipts and rental agreement as proof")
    
    # NPS specific recommendations
    nps_80ccd_1b = deductions_data.get('section_80ccd_1b', 0)
    if nps_80ccd_1b > 0:
        recommendations.append(f"🏦 NPS benefit: ₹{nps_80ccd_1b:,.0f} additional deduction under 80CCD(1B)")
    elif gross_total_income > 500000 and recommended_regime == 'Old Regime':
        recommendations.append("🏦 SUGGESTION: Consider NPS investment for additional ₹50,000 deduction under 80CCD(1B)")
    
    # Income-based specific recommendations
    if gross_total_income > 5000000:
        recommendations.append("⚠️ HIGH INCOME: Consider tax planning with professional consultation")
        recommendations.append("🏠 Explore real estate investment for additional tax benefits")
    elif gross_total_income > 1000000:
        recommendations.append("💰 Consider diversifying investments across ELSS, NPS, and insurance")
    
    # Next steps based on analysis
    recommendations.extend([
        "📅 NEXT STEPS:",
        "1️⃣ Gather investment proofs and Form 16 from employer",
        "2️⃣ Login to Income Tax e-filing portal (incometax.gov.in)",
        "3️⃣ Fill ITR-1/ITR-2 with calculated values from this report",
        "4️⃣ Submit return and e-verify using Aadhaar OTP or bank account",
        "5️⃣ Keep digital copies of all submitted documents"
    ])
    
    return recommendations


@api_view(['GET'])
def health_check(request):
    """Health check endpoint for monitoring"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'Django TaxSahaj API',
        'version': '1.0.0'
    })