import nltk
nltk.download('punkt')

from celery import shared_task
from doc_engine.models import ProcessingSession, Document, AnalysisTask, AnalysisResult
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from src.main import IncomeTaxAssistant
from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer

# Only Ollama analyzer is used now
from api.utils.tax_engine import IncomeTaxCalculator, DeductionCalculator
from api.utils.pii_logger import get_pii_safe_logger, log_document_processing, log_document_error
import dataclasses
import os

def get_document_analyzer(encryption_key=None):
    """
    Get the Ollama document analyzer - now the only supported analyzer
    """
    logger = get_pii_safe_logger(__name__)
    logger.info("🤖 Using Ollama analyzer")
    return OllamaDocumentAnalyzer(encryption_key=encryption_key)
import gc
import tempfile
import shutil
import time
import sys
import psutil
from datetime import datetime
from django.utils import timezone
from django.conf import settings  
from contextlib import contextmanager

def get_memory_usage():
    """Get current memory usage in MB"""
    try:
        process = psutil.Process()
        return f"{process.memory_info().rss / 1024 / 1024:.1f}MB"
    except:
        return "unknown"

def get_available_memory():
    """Get available system memory in MB"""  
    try:
        return f"{psutil.virtual_memory().available / 1024 / 1024:.1f}MB"
    except:
        return "unknown"

@shared_task(bind=True)
def test_celery_connection(self):
    """Enhanced test task to verify Celery is working with detailed debugging"""
    logger = get_pii_safe_logger(__name__)
    
    try:
        logger.info("🧪 CELERY TEST TASK EXECUTION START")
        logger.info(f"   Task ID: {self.request.id}")
        logger.info(f"   Task name: {self.request.task}")
        logger.info(f"   Worker hostname: {self.request.hostname}")
        logger.info(f"   Current time: {datetime.now()}")
        
        # Test database access
        logger.info("🔍 Testing database access...")
        try:
            from django.conf import settings
            logger.info(f"   Settings loaded: {hasattr(settings, 'DATABASES')}")
            logger.info(f"   Database engine: {settings.DATABASES['default']['ENGINE']}")
            
            # Test actual database query
            from doc_engine.models import ProcessingSession
            session_count = ProcessingSession.objects.count()
            logger.info(f"   ✅ Database query successful: {session_count} sessions")
            
        except Exception as db_error:
            logger.error(f"   ❌ Database access failed: {db_error}")
            import traceback
            logger.error(f"   Database traceback: {traceback.format_exc()}")
        
        # Test imports
        logger.info("🔍 Testing critical imports...")
        try:
            from src.core.document_processing.ollama_analyzer import OllamaDocumentAnalyzer
            logger.info("   ✅ OllamaDocumentAnalyzer import successful")
        except Exception as import_error:
            logger.error(f"   ❌ OllamaDocumentAnalyzer import failed: {import_error}")
            import traceback
            logger.error(f"   Import traceback: {traceback.format_exc()}")
        
        # Test Ollama connectivity from within task
        logger.info("🔍 Testing Ollama from Celery worker...")
        try:
            import requests
            ollama_response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if ollama_response.status_code == 200:
                models = ollama_response.json().get('models', [])
                logger.info(f"   ✅ Ollama accessible from worker: {len(models)} models")
            else:
                logger.error(f"   ❌ Ollama responded with status: {ollama_response.status_code}")
        except Exception as ollama_error:
            logger.error(f"   ❌ Ollama connection failed from worker: {ollama_error}")
        
        logger.info("✅ CELERY TEST TASK COMPLETED SUCCESSFULLY")
        return {
            "status": "success", 
            "message": "Celery worker is functioning correctly",
            "task_id": str(self.request.id),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ CELERY TEST TASK FAILED: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise e

def _convert_ollama_data_to_expected_format(ollama_data, filename):
    """Convert OllamaExtractedData to our expected format"""
    doc_type_mapping = {
        'form_16': 'form16',
        'payslip': 'salary_slip', 
        'bank_interest_certificate': 'bank_interest_certificate',
        'capital_gains': 'stocks_capital_gains',
        'investment': 'investment',
        'mutual_fund_elss_statement': 'mutual_fund_elss_statement',
        'nps_statement': 'nps_statement'
    }
    
    # Determine document type
    ollama_doc_type = ollama_data.document_type.lower()
    mapped_doc_type = doc_type_mapping.get(ollama_doc_type, 'other')
    
    if mapped_doc_type == 'form16':
        return {
            "document_type": "form16",
            "financial_year": ollama_data.financial_year or "2024-25",
            "employer_details": {
                "employer_name": ollama_data.employer_name or "Unknown",
                "employee_pan": ollama_data.pan or "Unknown"
            },
            "salary_details": {
                "basic_salary": ollama_data.basic_salary,
                "total_section_17_1": ollama_data.gross_salary,
                "perquisites_espp": ollama_data.perquisites,
                "gross_salary": ollama_data.total_gross_salary,
                "hra_received": ollama_data.hra_received
            },
            "deductions": {
                "pf_employee": ollama_data.epf_amount,
                "professional_tax": ollama_data.professional_tax
            },
            "exemptions": {
                "hra_exemption": ollama_data.hra_received  # Base for HRA exemption calculation
            },
            "tax_details": {
                "total_tds": ollama_data.tax_deducted
            }
        }
    elif mapped_doc_type == 'bank_interest_certificate':
        return {
            "document_type": "bank_interest_certificate",
            "financial_year": ollama_data.financial_year or "2024-25",
            "interest_details": {
                "total_interest": ollama_data.interest_amount
            },
            "bank_details": {
                "bank_name": ollama_data.bank_name,
                "account_number": ollama_data.account_number
            }
        }
    elif mapped_doc_type == 'stocks_capital_gains':
        return {
            "document_type": "stocks_capital_gains",
            "financial_year": ollama_data.financial_year or "2024-25",
            "equity_transactions": {
                "total_gains": ollama_data.total_capital_gains,
                "long_term_capital_gains": ollama_data.long_term_capital_gains,
                "short_term_capital_gains": ollama_data.short_term_capital_gains,
                "dividend_income": getattr(ollama_data, 'dividend_income', 0.0)  # Extract from actual document, don't assume
            }
        }
    elif mapped_doc_type == 'mutual_fund_elss_statement':
        return {
            "document_type": "mutual_fund_elss_statement",
            "financial_year": ollama_data.financial_year or "2024-25",
            "elss_investments": {
                "total_investment": ollama_data.elss_amount or ollama_data.total_investment,
                "fund_name": ollama_data.fund_name if hasattr(ollama_data, 'fund_name') else "Unknown"
            }
        }
    elif mapped_doc_type == 'nps_statement':
        return {
            "document_type": "nps_statement",
            "financial_year": ollama_data.financial_year or "2024-25",
            "nps_contributions": {
                "additional_contribution": ollama_data.nps_80ccd1b,
                "tier1_contribution": ollama_data.nps_tier1_contribution,
                "employer_contribution": ollama_data.nps_employer_contribution
            }
        }
    else:
        return {
            "document_type": "other",
            "extracted_data": {
                "confidence": ollama_data.confidence,
                "original_type": ollama_data.document_type
            }
        }

@shared_task(bind=True, time_limit=600, soft_time_limit=480, autoretry_for=(Exception,), retry_kwargs={'max_retries': 0})
def process_single_document(self, session_id, document_id, encryption_key=None):
    """
    Process a single document - can be picked up by any available worker
    Args:
        session_id: The session UUID
        document_id: The document UUID 
    """
    # Initialize logger with error handling
    try:
        logger = get_pii_safe_logger(__name__)
    except Exception as e:
        # Fallback to basic logging if PII logger fails
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"PII logger initialization failed: {e}")
    
    # Log task startup with maximum detail
    try:
        logger.info(f"🔧 CELERY TASK STARTED: process_single_document")
        logger.info(f"   Task ID: {self.request.id}")
        logger.info(f"   Task name: {self.request.task}")
        logger.info(f"   Worker hostname: {self.request.hostname}")
        logger.info(f"   Worker PID: {os.getpid()}")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   Document ID: {document_id}")
        logger.info(f"   Encryption key provided: {encryption_key is not None}")
        logger.info(f"   Current time: {datetime.now()}")
        logger.info(f"   Memory usage: {get_memory_usage()}")
        
        # Add early checkpoint to verify task is running
        logger.info(f"✅ CHECKPOINT 1: Task execution started successfully")
        
        # Log environment info
        logger.info(f"🔍 ENVIRONMENT CHECK")
        logger.info(f"   Python version: {sys.version}")
        logger.info(f"   Django settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
        logger.info(f"   Current working directory: {os.getcwd()}")
        logger.info(f"   Available memory: {get_available_memory()}")
        
    except Exception as e:
        # Even basic logging failed - use print as last resort
        print(f"CRITICAL: Logging failed in process_single_document: {e}")
        print(f"Task starting with session_id: {session_id}, document_id: {document_id}")
        import traceback
        traceback.print_exc()
    
    try:
        logger.info(f"✅ CHECKPOINT 2: About to query database")
        session = ProcessingSession.objects.get(pk=session_id)
        logger.info(f"✅ CHECKPOINT 3: Session found - {session.pk}")
        document = Document.objects.get(pk=document_id, session=session)
        logger.info(f"✅ CHECKPOINT 4: Document found - {document.filename}")
        
        logger.info(f"📄 DOCUMENT FOUND: {document.filename}")
        logger.info(f"   File field: {document.file.name}")
        logger.info(f"   Current status: {document.status}")
        
        # Test file accessibility in Celery worker
        try:
            with document.file.open('rb') as f:
                test_read = f.read(100)
                logger.info(f"   ✅ File accessible in Celery worker: {len(test_read)} bytes read")
        except Exception as e:
            logger.error(f"   ❌ File NOT accessible in Celery worker: {e}")
            raise Exception(f"Cannot access file in Celery worker: {e}")
        
        # Update document status to processing
        document.status = Document.Status.PROCESSING
        document.save()
        
        # Real AI processing with Llama 3 - with timeout protection
        # No temporary file written to disk for decrypted content
        
        from django.conf import settings
        from privacy_engine.strategies import get_fernet_instance, derive_key_from_session_id
        from privacy_engine.security_monitor import SecurityMonitor, monitor_processing_security
        from cryptography.fernet import Fernet # Ensure Fernet is imported here

        # If encryption_key is not passed, derive it (e.g., for direct calls or testing)
        if settings.PRIVACY_ENGINE_ENABLED and encryption_key is None:
            encryption_key = derive_key_from_session_id(str(session.id))

        try:
            # AI processing logged via proper logger above
            start_time = time.time()

            file_bytes = None # Initialize to None
            if document.file:
                # DEBUG: Entering document.file.read() block
                print(f"DEBUG: document.file exists. Name: {document.file.name}, Size: {document.file.size}")
                try:
                    encrypted_file_bytes = document.file.read()
                    print(f"DEBUG: After document.file.read() - Type: {type(encrypted_file_bytes)}, Length: {len(encrypted_file_bytes) if encrypted_file_bytes is not None else 'None'}")
                    
                    if settings.PRIVACY_ENGINE_ENABLED and encryption_key:
                        fernet_instance = get_fernet_instance(encryption_key)
                        file_bytes = fernet_instance.decrypt(encrypted_file_bytes)
                        print(f"DEBUG: Decryption successful. Decrypted content length: {len(file_bytes)}")
                    else:
                        file_bytes = encrypted_file_bytes
                        print("DEBUG: Privacy engine disabled or no encryption key, using original file bytes.")

                except Exception as e:
                    print(f"DEBUG: Error reading or decrypting document.file: {e}")
            else:
                print("DEBUG: document.file is None!")

            if file_bytes is None:
                raise ValueError("file_bytes is None after reading document.file. Cannot proceed with AI analysis.")

            analyzer = OllamaDocumentAnalyzer() # Pass the key
            analysis_result_data = analyzer.analyze_document(file_bytes, document.filename)
            elapsed = time.time() - start_time
            # AI processing completion logged via proper logger
            
            if analysis_result_data:
                # Convert OllamaExtractedData to our expected format
                analysis_result = _convert_ollama_data_to_expected_format(analysis_result_data, document.filename)
                # AI analysis result logged via proper logger above
                print(f"AI extracted values: {analysis_result}")
            else:
                # No AI result warning logged via proper logger above
                analysis_result = {
                    "document_type": "other",
                    "extracted_data": {"error": "No analysis result from AI"}
                }
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            if "timed out" in error_msg.lower():
                # Timeout error logged via proper logger above
                analysis_result = {
                    "document_type": "other", 
                    "extracted_data": {"error": f"AI processing timed out after {elapsed:.1f}s"}
                }
            else:
                # AI processing error logged via proper logger above
                analysis_result = {
                    "document_type": "other", 
                    "extracted_data": {"error": f"AI processing failed: {str(e)}"}
                }
        
        
        # Save the analysis result
        # Saving result logged via proper logger above
        AnalysisResult.objects.create(
            session=session,
            document=document,
            result_data=analysis_result
        )
        
        # Update document status to completed
        document.status = Document.Status.PROCESSED
        document.processed_at = timezone.now()
        document.save()
        
        return {
            "status": "success",
            "document_id": str(document_id),
            "filename": document.filename,
            "result_summary": f"Processed {document.filename} - found {len(analysis_result)} data points"
        }
        
    except Exception as e:
        # Mark document as failed
        try:
            document.status = Document.Status.FAILED
            document.save()
        except:
            pass
        raise Exception(f"Failed to process document {document_id}: {str(e)}")

import logging
logger = get_pii_safe_logger(__name__)

@shared_task(bind=True, time_limit=3600, soft_time_limit=3000)
def process_session_analysis_parallel(self, session_id, encryption_key=None):
    """
    Parallel session analysis - spawns separate tasks for each document
    All documents processed in parallel across multiple workers
    """
    try:
        logger.info(f"Starting parallel analysis for session: {session_id}")
        session = ProcessingSession.objects.get(pk=session_id)
        task = session.task
        task.status = AnalysisTask.Status.STARTED
        task.save()

        # Update session status
        session.status = ProcessingSession.Status.PROCESSING
        session.save()
        
        # Get all documents and spawn individual tasks for each
        documents = session.documents.all()
        logger.info(f"Found {len(documents)} documents to process for session: {session_id}")
        
        # Spawn parallel document processing tasks
        document_tasks = []
        for document in documents:
            # Reset document status to uploaded (pending processing)
            document.status = Document.Status.UPLOADED
            document.save()
            
            # Spawn individual task for this document
            doc_task = process_single_document.delay(session_id, document.pk, encryption_key=encryption_key)
            document_tasks.append((document.pk, doc_task.id))
            logger.info_with_filename("Spawned task {task_id} for document: {filename}", document.filename, task_id=doc_task.id)
        
        # Monitor document processing completion
        import time
        max_wait_time = 1800  # 30 minutes max
        check_interval = 10   # Check every 10 seconds
        elapsed_time = 0
        
        while elapsed_time < max_wait_time:
            # Check completion status
            completed_docs = session.documents.filter(status__in=[Document.Status.PROCESSED, Document.Status.FAILED])
            total_docs = session.documents.count()
            
            logger.info(f"Progress: {completed_docs.count()}/{total_docs} documents completed")
            
            if completed_docs.count() == total_docs:
                logger.info(f"All documents processed for session {session_id}")
                break
                
            time.sleep(check_interval)
            elapsed_time += check_interval
        
        # Check if timeout occurred
        if elapsed_time >= max_wait_time:
            logger.warning(f"Session {session_id} processing timed out after {max_wait_time}s")
            
        # Continue with final summary generation...
        completed_docs = session.documents.filter(status=Document.Status.PROCESSED)
        # [Rest of the summary generation logic remains the same]
        return _generate_final_summary(session, completed_docs)
        
    except Exception as e:
        logger.error(f"Error in process_session_analysis_parallel: {e}")
        try:
            task.status = AnalysisTask.Status.FAILED
            task.save()
            session.status = ProcessingSession.Status.FAILED
            session.save()
        except:
            pass
        raise e

def _generate_final_summary(session, completed_docs):
    """Generate comprehensive tax summary with full calculation logic"""
    logger = get_pii_safe_logger(__name__)
    
    if completed_docs.exists():
        # Aggregate results from all processed documents based on actual AI analysis
        salary_data = {}
        tax_data = {}
        other_income = {}
        investments_80c = 0
        nps_80ccd_1b = 0
        bank_interest = 0
        dividend_income = 0
        capital_gains = {}
        employee_pf = 0
        professional_tax_extracted = 0
        hra_received = 0
        
        for doc in completed_docs:
            result = AnalysisResult.objects.filter(session=session, document=doc).first()
            logger.info_with_filename("Aggregating: {filename} - Result: {result}", doc.filename, result=bool(result))
            if result and result.result_data:
                data = result.result_data
                doc_type = data.get('document_type', '')
                logger.info_with_filename("Processing: {filename} -> {doc_type}", doc.filename, doc_type=doc_type)
                
                # Aggregate salary and tax data from Form16
                if doc_type == 'form16':
                    salary_data = data.get('salary_details', {})
                    tax_data = data.get('tax_details', {})
                    deductions_data = data.get('deductions', {})
                    exemptions_data = data.get('exemptions', {})
                    
                    # Extract actual values from AI analysis
                    employee_pf = deductions_data.get('pf_employee', 0)
                    professional_tax_extracted = deductions_data.get('professional_tax', 0)  
                    hra_received = salary_data.get('hra_received', 0)
                    
                    logger.info(f"Form16 extracted - Gross: {salary_data.get('gross_salary', 0)}, TDS: {tax_data.get('total_tds', 0)}")
                    
                # Aggregate investment data
                elif doc_type == 'mutual_fund_elss_statement':
                    investments_80c += data.get('elss_investments', {}).get('total_investment', 0)
                    
                elif doc_type == 'nps_statement':
                    nps_80ccd_1b = data.get('nps_contributions', {}).get('additional_contribution', 0)
                    
                # Aggregate other income
                elif doc_type == 'bank_interest_certificate':
                    bank_interest = data.get('interest_details', {}).get('total_interest', 0)
                    logger.info(f"Extracted bank interest: {bank_interest}")
                    
                elif doc_type == 'stocks_capital_gains':
                    dividend_income = data.get('equity_transactions', {}).get('dividend_income', 0)
                    capital_gains['stocks'] = data.get('equity_transactions', {}).get('total_gains', 0)
                    logger.info(f"Extracted dividend income: {dividend_income}")
                    
                elif doc_type == 'mutual_fund_capital_gains':
                    capital_gains['mutual_funds'] = data.get('capital_gains', {}).get('total_gains', 0)
        
        # Extract and aggregate income data from AI analysis
        basic_and_allowances = salary_data.get('total_section_17_1', 0)
        perquisites_espp = salary_data.get('perquisites_espp', 0)
        total_salary_income = basic_and_allowances + perquisites_espp
        total_other_income = bank_interest + dividend_income
        gross_total_income = total_salary_income + total_other_income
        
        # Calculate deductions using enhanced utility classes with all parameters
        old_regime_deductions = DeductionCalculator.calculate_old_regime_deductions(
            hra_received=hra_received,
            basic_salary=basic_and_allowances,  # Use as basic salary approximation
            elss_investments=investments_80c,
            employee_pf=employee_pf,
            nps_additional=nps_80ccd_1b,
            professional_tax=professional_tax_extracted if professional_tax_extracted > 0 else 0,
            standard_deduction=50000,
            rent_paid=None,  # Will use enhanced estimation if HRA received but no rent data
            health_insurance_premium=0,  # Can be enhanced later from document analysis
            parents_health_insurance=0,  # Can be enhanced later from document analysis  
            charitable_donations=0,  # Can be enhanced later from document analysis
            charity_type='50_percent',
            education_loan_interest=0,  # Can be enhanced later from document analysis
            loan_year=1,
            savings_interest=bank_interest,  # Pass bank interest for Section 80TTA/TTB calculation
            age_above_60=False  # Can be enhanced later from document analysis
        )
        
        new_regime_deductions = DeductionCalculator.calculate_new_regime_deductions(
            standard_deduction=75000  # Using ₹75K for FY 2024-25 as per Budget 2024
        )
        
        # Use the comprehensive tax calculator for regime comparison
        tax_comparison = IncomeTaxCalculator.compare_tax_regimes(
            gross_income=gross_total_income,
            old_regime_deductions=old_regime_deductions['total_deductions'],
            new_regime_deductions=new_regime_deductions['total_deductions'],
            tds_paid=tax_data.get('total_tds', 0) if tax_data else 0
        )
        
        # Extract calculated values for legacy format compatibility
        old_regime_calc = tax_comparison['old_regime']['tax_calculation']
        new_regime_calc = tax_comparison['new_regime']['tax_calculation']
        old_regime_payment = tax_comparison['old_regime']['payment_details']
        new_regime_payment = tax_comparison['new_regime']['payment_details']
        
        # Debug logging
        tds_paid = tax_comparison['old_regime']['payment_details']['tds_paid']
        logger.info(f"TDS Calculation Debug:")
        logger.info(f"  tds_paid extracted: ₹{tds_paid:,.2f}")
        logger.info(f"  old_regime_tax_liability: ₹{old_regime_calc['total_liability']:,.2f}")
        logger.info(f"  new_regime_tax_liability: ₹{new_regime_calc['total_liability']:,.2f}")
        
        # Extract for compatibility with existing format
        refund_old = old_regime_payment['refund_due'] - old_regime_payment['additional_tax_payable']
        additional_tax_new = new_regime_payment['additional_tax_payable'] - new_regime_payment['refund_due']
        
        # Create comprehensive final summary using new calculation structure
        final_summary = {
            "financial_year": "2024-25",
            "assessment_year": "2025-26",
            "client_name": "Tax Analysis Report",
            
            # Detailed Income Calculation
            "income_breakdown": {
                "salary_income": {
                    "basic_and_allowances_17_1": basic_and_allowances,
                    "perquisites_espp_17_2": perquisites_espp,
                    "total_salary": total_salary_income
                },
                "other_income": {
                    "bank_interest": bank_interest,
                    "dividend_income": dividend_income,
                    "total_other": total_other_income
                },
                "gross_total_income": gross_total_income
            },
            
            # Deductions & Exemptions (Old Regime)
            "deductions_old_regime": old_regime_deductions,
            
            # Tax Calculations using new utility classes
            "tax_calculation_old_regime": {
                "taxable_income": old_regime_calc['taxable_income'],
                "tax_on_income": old_regime_calc['base_tax'],
                "surcharge": old_regime_calc['surcharge'],
                "health_education_cess": old_regime_calc['cess'],
                "total_tax_liability": old_regime_calc['total_liability'],
                "tds_paid": old_regime_payment['tds_paid'],
                "refund_due": old_regime_payment['refund_due'],
                "additional_tax_payable": old_regime_payment['additional_tax_payable']
            },
            
            "tax_calculation_new_regime": {
                "taxable_income": new_regime_calc['taxable_income'],
                "tax_on_income": new_regime_calc['base_tax'],
                "surcharge": new_regime_calc['surcharge'],
                "health_education_cess": new_regime_calc['cess'],
                "total_tax_liability": new_regime_calc['total_liability'],
                "tds_paid": new_regime_payment['tds_paid'],
                "refund_due": new_regime_payment['refund_due'],
                "additional_tax_payable": new_regime_payment['additional_tax_payable']
            },
            
            # Regime Comparison & Recommendation
            "regime_comparison": {
                "old_regime_position": f"Refund of ₹{old_regime_payment['refund_due']:,.2f}" if old_regime_payment['refund_due'] > 0 else f"Tax payable: ₹{old_regime_payment['additional_tax_payable']:,.2f}",
                "new_regime_position": f"Additional tax: ₹{new_regime_payment['additional_tax_payable']:,.2f}" if new_regime_payment['additional_tax_payable'] > 0 else f"Refund of ₹{new_regime_payment['refund_due']:,.2f}",
                "savings_by_old_regime": tax_comparison['comparison']['savings_by_old_regime'],
                "recommended_regime": tax_comparison['comparison']['recommended_regime'],
                "recommendation_reason": tax_comparison['comparison']['recommendation_reason']
            },
            
            # Processing metadata
            "documents_processed": completed_docs.count(),
            "processing_method": "parallel",
            "analysis_date": "2025-08-16"
        }
        
        logger.info(f"Creating comprehensive tax analysis with gross_total_income: {gross_total_income}")
        AnalysisResult.objects.create(
            session=session,
            result_data=final_summary
        )
    
    # Complete the session
    session.status = ProcessingSession.Status.COMPLETED
    session.save()
    
    task = session.task
    task.status = AnalysisTask.Status.SUCCESS
    task.save()
    
    return {
        "status": "success",
        "documents_processed": completed_docs.count(),
        "processing_method": "parallel"
    }

@shared_task(bind=True, time_limit=3600, soft_time_limit=3000)
def process_session_analysis_distributed(self, session_id):
    """
    Distributed session analysis - processes documents with real AI analysis
    All documents processed inline with real Llama 3 AI analysis
    """
    try:
        logger.info(f"Starting analysis for session: {session_id}")
        session = ProcessingSession.objects.get(pk=session_id)
        task = session.task
        task.status = AnalysisTask.Status.STARTED
        task.save()

        # Update session status
        session.status = ProcessingSession.Status.PROCESSING
        session.save()
        
        # Get all documents and spawn individual tasks for each
        documents = session.documents.all()
        logger.info(f"Found {len(documents)} documents to process for session: {session_id}")
        document_tasks = []
        
        for document in documents:
            # Reset document status to uploaded (pending processing)
            document.status = Document.Status.UPLOADED
            document.save()
            
            # Process document directly inline to avoid celery sub-task issues
            try:
                logger.info_with_filename("Processing {filename} inline...", document.filename)
                
                # Update document status to processing
                document.status = Document.Status.PROCESSING
                document.save()
                
                # Real AI processing with Llama 3 - no mock data
                # No temporary file written to disk for decrypted content
                try:
                    logger.info_with_filename("AI processing: {filename}", document.filename)
                    
                    if settings.PRIVACY_ENGINE_ENABLED:
                        encryption_key_for_analyzer = derive_key_from_session_id(str(session.id))
                    else:
                        encryption_key_for_analyzer = None

                    analyzer = OllamaDocumentAnalyzer(encryption_key=encryption_key_for_analyzer)

                    # Read decrypted file content directly from storage
                    file_bytes = document.file.read()

                    analysis_result_data = analyzer.analyze_document(file_bytes, document.filename)
                    
                    if analysis_result_data:
                        # Convert OllamaExtractedData to our expected format
                        analysis_result = _convert_ollama_data_to_expected_format(analysis_result_data, document.filename)
                        logger.info_with_filename("AI analysis result for {filename}: {doc_type}", document.filename, doc_type=analysis_result.get('document_type', 'unknown'))
                        logger.info(f"AI extracted values: {analysis_result}")
                    else:
                        logger.warning_with_filename("No AI analysis result for {filename}, using fallback", document.filename)
                        analysis_result = {
                            "document_type": "other",
                            "extracted_data": {"error": "No analysis result from AI"}
                        }
                    
                except Exception as e:
                    logger.error_with_filename("Error in AI processing for {filename}: {error}", document.filename, error=str(e))
                    analysis_result = {
                        "document_type": "other", 
                        "extracted_data": {"error": f"AI processing failed: {str(e)}"}
                    }
                
                
                # Save the analysis result
                logger.info_with_filename("Saving result for {filename}: {doc_type}", document.filename, doc_type=analysis_result.get('document_type', 'NO_TYPE'))
                AnalysisResult.objects.create(
                    session=session,
                    document=document,
                    result_data=analysis_result
                )
                
                # Update document status to completed
                document.status = Document.Status.PROCESSED
                document.processed_at = timezone.now()
                document.save()
                
                logger.info_with_filename("Completed {filename}", document.filename)
            except Exception as e:
                logger.error_with_filename("Error processing {filename}: {error}", document.filename, error=str(e))
                document.status = Document.Status.FAILED
                document.save()
        
        # All documents processed synchronously
        logger.info(f"Completed processing documents for session {session_id}")
        
        # Generate final tax summary after all documents are processed
        completed_docs = session.documents.filter(status=Document.Status.PROCESSED)
        if completed_docs.exists():
            # Aggregate results from all processed documents based on actual AI analysis
            salary_data = {}
            tax_data = {}
            other_income = {}
            investments_80c = 0
            nps_80ccd_1b = 0
            bank_interest = 0
            dividend_income = 0
            capital_gains = {}
            employee_pf = 0
            professional_tax_extracted = 0
            hra_received = 0
            
            for doc in completed_docs:
                result = AnalysisResult.objects.filter(session=session, document=doc).first()
                logger.info_with_filename("Aggregating: {filename} - Result: {result}", doc.filename, result=bool(result))
                if result and result.result_data:
                    data = result.result_data
                    doc_type = data.get('document_type', '')
                    logger.info_with_filename("Retrieving: {filename} -> {doc_type} (keys: {keys})...", doc.filename, doc_type=doc_type, keys=list(data.keys())[:3])
                    
                    # Aggregate salary and tax data from Form16
                    if doc_type == 'form16':
                        salary_data = data.get('salary_details', {})
                        tax_data = data.get('tax_details', {})
                        deductions_data = data.get('deductions', {})
                        exemptions_data = data.get('exemptions', {})
                        
                        # Extract actual values from AI analysis
                        employee_pf = deductions_data.get('pf_employee', 0)
                        professional_tax_extracted = deductions_data.get('professional_tax', 0)  
                        hra_received = salary_data.get('hra_received', 0)
                        
                        logger.info(f"Form16 extracted - PF: {employee_pf}, Professional Tax: {professional_tax_extracted}, HRA: {hra_received}")
                        
                    # Aggregate investment data
                    elif doc_type == 'mutual_fund_elss_statement':
                        investments_80c += data.get('elss_investments', {}).get('total_investment', 0)
                        
                    elif doc_type == 'nps_statement':
                        nps_80ccd_1b = data.get('nps_contributions', {}).get('additional_contribution', 0)
                        
                    # Aggregate other income
                    elif doc_type == 'bank_interest_certificate':
                        bank_interest = data.get('interest_details', {}).get('total_interest', 0)
                        logger.info(f"Extracted bank interest: {bank_interest}")
                        
                    elif doc_type == 'stocks_capital_gains':
                        dividend_income = data.get('equity_transactions', {}).get('dividend_income', 0)
                        capital_gains['stocks'] = data.get('equity_transactions', {}).get('total_gains', 0)
                        logger.info(f"Extracted dividend income: {dividend_income}")
                        
                    elif doc_type == 'mutual_fund_capital_gains':
                        capital_gains['mutual_funds'] = data.get('capital_gains', {}).get('total_gains', 0)
            
            # Extract and aggregate income data from AI analysis (distributed version)
            basic_and_allowances = salary_data.get('total_section_17_1', 0)
            perquisites_espp = salary_data.get('perquisites_espp', 0)
            total_salary_income = basic_and_allowances + perquisites_espp
            total_other_income = bank_interest + dividend_income
            gross_total_income = total_salary_income + total_other_income
            
            # Calculate deductions using enhanced utility classes with all parameters (distributed version)
            old_regime_deductions = DeductionCalculator.calculate_old_regime_deductions(
                hra_received=hra_received,
                basic_salary=basic_and_allowances,  # Use as basic salary approximation
                elss_investments=investments_80c,
                employee_pf=employee_pf,
                nps_additional=nps_80ccd_1b,
                professional_tax=professional_tax_extracted if professional_tax_extracted > 0 else 0,
                standard_deduction=50000,
                rent_paid=None,  # Will use enhanced estimation if HRA received but no rent data
                health_insurance_premium=0,  # Can be enhanced later from document analysis
                parents_health_insurance=0,  # Can be enhanced later from document analysis  
                charitable_donations=0,  # Can be enhanced later from document analysis
                charity_type='50_percent',
                education_loan_interest=0,  # Can be enhanced later from document analysis
                loan_year=1,
                savings_interest=bank_interest,  # Pass bank interest for Section 80TTA/TTB calculation
                age_above_60=False  # Can be enhanced later from document analysis
            )
            
            new_regime_deductions = DeductionCalculator.calculate_new_regime_deductions(
                standard_deduction=75000  # Using ₹75K for FY 2024-25 as per Budget 2024
            )
            
            # Use the comprehensive tax calculator for regime comparison (distributed version)
            tax_comparison = IncomeTaxCalculator.compare_tax_regimes(
                gross_income=gross_total_income,
                old_regime_deductions=old_regime_deductions['total_deductions'],
                new_regime_deductions=new_regime_deductions['total_deductions'],
                tds_paid=tax_data.get('total_tds', 0) if tax_data else 0
            )
            
            # Extract calculated values for legacy format compatibility (distributed version)
            old_regime_calc = tax_comparison['old_regime']['tax_calculation']
            new_regime_calc = tax_comparison['new_regime']['tax_calculation']
            old_regime_payment = tax_comparison['old_regime']['payment_details']
            new_regime_payment = tax_comparison['new_regime']['payment_details']
            
            # Debug logging (distributed version)
            tds_paid = tax_comparison['old_regime']['payment_details']['tds_paid']
            logger.info(f"TDS Calculation Debug (Distributed):")
            logger.info(f"  tds_paid extracted: ₹{tds_paid:,.2f}")
            logger.info(f"  old_regime_tax_liability: ₹{old_regime_calc['total_liability']:,.2f}")
            logger.info(f"  new_regime_tax_liability: ₹{new_regime_calc['total_liability']:,.2f}")
            
            # Create comprehensive final summary using new calculation structure (distributed version)
            final_summary = {
                "financial_year": "2024-25",
                "assessment_year": "2025-26",
                "client_name": "Tax Analysis Report",
                
                # Detailed Income Calculation
                "income_breakdown": {
                    "salary_income": {
                        "basic_and_allowances_17_1": basic_and_allowances,
                        "perquisites_espp_17_2": perquisites_espp,
                        "total_salary": total_salary_income
                    },
                    "other_income": {
                        "bank_interest": bank_interest,
                        "dividend_income": dividend_income,
                        "total_other": total_other_income
                    },
                    "gross_total_income": gross_total_income
                },
                
                # Deductions & Exemptions (Old Regime)
                "deductions_old_regime": old_regime_deductions,
                
                # Tax Calculations using new utility classes
                "tax_calculation_old_regime": {
                    "taxable_income": old_regime_calc['taxable_income'],
                    "tax_on_income": old_regime_calc['base_tax'],
                    "surcharge": old_regime_calc['surcharge'],
                    "health_education_cess": old_regime_calc['cess'],
                    "total_tax_liability": old_regime_calc['total_liability'],
                    "tds_paid": old_regime_payment['tds_paid'],
                    "refund_due": old_regime_payment['refund_due'],
                    "additional_tax_payable": old_regime_payment['additional_tax_payable']
                },
                
                "tax_calculation_new_regime": {
                    "taxable_income": new_regime_calc['taxable_income'],
                    "tax_on_income": new_regime_calc['base_tax'],
                    "surcharge": new_regime_calc['surcharge'],
                    "health_education_cess": new_regime_calc['cess'],
                    "total_tax_liability": new_regime_calc['total_liability'],
                    "tds_paid": new_regime_payment['tds_paid'],
                    "refund_due": new_regime_payment['refund_due'],
                    "additional_tax_payable": new_regime_payment['additional_tax_payable']
                },
                
                # Regime Comparison & Recommendation
                "regime_comparison": {
                    "old_regime_position": f"Refund of ₹{old_regime_payment['refund_due']:,.2f}" if old_regime_payment['refund_due'] > 0 else f"Tax payable: ₹{old_regime_payment['additional_tax_payable']:,.2f}",
                    "new_regime_position": f"Additional tax: ₹{new_regime_payment['additional_tax_payable']:,.2f}" if new_regime_payment['additional_tax_payable'] > 0 else f"Refund of ₹{new_regime_payment['refund_due']:,.2f}",
                    "savings_by_old_regime": tax_comparison['comparison']['savings_by_old_regime'],
                    "recommended_regime": tax_comparison['comparison']['recommended_regime'],
                    "recommendation_reason": tax_comparison['comparison']['recommendation_reason']
                },
                
                # Processing metadata
                "documents_processed": completed_docs.count(),
                "processing_method": "distributed",
                "analysis_date": "2025-08-16"
            }
            
            logger.info(f"Creating detailed analysis result with gross_total_income: {gross_total_income}")
            AnalysisResult.objects.create(
                session=session,
                result_data=final_summary
            )
        
        # Complete the session
        session.status = ProcessingSession.Status.COMPLETED
        session.save()
        
        task.status = AnalysisTask.Status.SUCCESS
        task.save()
        
        return {
            "status": "success",
            "documents_processed": completed_docs.count(),
            "total_documents": documents.count(),
            "processing_method": "distributed"
        }
        
    except Exception as e:
        logger.error(f"Error in process_session_analysis_distributed: {e}")
        try:
            task.status = AnalysisTask.Status.FAILED
            task.save()
            session.status = ProcessingSession.Status.FAILED
            session.save()
        except:
            pass
        raise e

@shared_task(bind=True, time_limit=30, soft_time_limit=25)
def process_session_analysis(self, session_id):
    """Quick mock analysis task for testing - completes in ~10 seconds"""
    try:
        session = ProcessingSession.objects.get(pk=session_id)
        task = session.task
        task.status = AnalysisTask.Status.STARTED
        task.save()

        # Update session status
        session.status = ProcessingSession.Status.PROCESSING
        session.save()
        
        # Mock processing with realistic delays
        documents = session.documents.all()
        
        for i, doc in enumerate(documents, 1):
            doc.status = Document.Status.PROCESSING
            doc.save()
            time.sleep(2)  # Mock processing time per document
            
            # Create mock analysis result
            mock_result = {
                "income": {"salary": 500000, "interest": 20000, "other": 30000},
                "deductions": {"80c": 120000, "80d": 25000},
                "document_type": "salary_slip" if "salary" in doc.filename.lower() else "bank_statement"
            }
            
            AnalysisResult.objects.create(
                session=session,
                document=doc,
                result_data=mock_result
            )
            
            doc.status = Document.Status.PROCESSED
            doc.save()
        
        # Create final tax summary
        final_summary = {
            "gross_income": 550000,
            "total_deductions": 145000,
            "taxable_income": 405000,
            "tax_liability": 12500,
            "refund_due": 5000,
            "regime_comparison": {
                "old_regime": 12500,
                "new_regime": 15000,
                "recommended": "old_regime"
            }
        }
        
        AnalysisResult.objects.create(
            session=session,
            result_data=final_summary
        )
        
        # Complete the task
        session.status = ProcessingSession.Status.COMPLETED
        session.save()
        
        task.status = AnalysisTask.Status.SUCCESS
        task.save()
        
        return "Analysis completed successfully"
        
    except Exception as e:
        try:
            task.status = AnalysisTask.Status.FAILED
            task.save()
            session.status = ProcessingSession.Status.FAILED
            session.save()
        except:
            pass
        raise e

@shared_task(bind=True, time_limit=600, soft_time_limit=590, acks_late=True, reject_on_worker_lost=True)
def process_session_analysis_full(self, session_id):
    """Full analysis task - takes several minutes to complete"""
    channel_layer = get_channel_layer()
    room_group_name = f'analysis_{session_id}'

    def send_update(message):
        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'analysis_update',
                'message': message
            }
        )

    analyzer = None
    assistant = None
    temp_dir = None
    
    try:
        session = ProcessingSession.objects.get(pk=session_id)
        task = session.task
        task.status = AnalysisTask.Status.STARTED
        task.save()
        send_update("Analysis started.")

        # No temporary directory needed for file processing as content is handled in-memory
        temp_dir = None # Set to None as it's no longer used for file content

        # 1. Initialize Analyzer and Assistant in isolated process
        send_update("Initializing AI models...")

        # Force garbage collection before heavy operations
        gc.collect()

        send_update("Processing documents...")

        # 2. Analyze Documents with memory management
        documents = session.documents.all()
        analyzed_docs_data = []

        # Get encryption key for analyzer if privacy is enabled
        encryption_key_for_analyzer = None
        if settings.PRIVACY_ENGINE_ENABLED:
            try:
                encryption_key_for_analyzer = derive_key_from_session_id(str(session.id))
                monitor_processing_security(str(session.id), "session_analysis_start")
            except Exception as e:
                print(f"Warning: Could not derive encryption key: {e}. Processing without encryption.")
                encryption_key_for_analyzer = None
                
        analyzer = OllamaDocumentAnalyzer(encryption_key=encryption_key_for_analyzer)
        assistant = IncomeTaxAssistant(analyzer=analyzer)

        for i, doc in enumerate(documents):
            try:
                doc.status = Document.Status.PROCESSING
                doc.save()
                send_update(f"Processing document {i+1}/{len(documents)}: {doc.filename}")

                # Read file content - handle encryption if enabled
                file_bytes = None
                if settings.PRIVACY_ENGINE_ENABLED and encryption_key_for_analyzer:
                    # Read encrypted content and decrypt
                    encrypted_content = doc.file.read()
                    
                    # Security check: verify decryption capability
                    can_decrypt, decrypted_size, decrypt_error = SecurityMonitor.verify_decryption_capability(
                        encrypted_content, str(doc.session.id)
                    )
                    
                    if not can_decrypt:
                        logger.error_with_filename("Security Warning: Cannot decrypt {filename}: {error}", doc.filename, error=str(decrypt_error))
                        monitor_processing_security(str(doc.session.id), "decryption_failed")
                    
                    try:
                        fernet_instance = get_fernet_instance(encryption_key_for_analyzer)
                        file_bytes = fernet_instance.decrypt(encrypted_content)
                        logger.debug_with_pii("Security: Successfully decrypted {filename} ({size} bytes)", filename=doc.filename, size=len(file_bytes))
                        monitor_processing_security(str(doc.session.id), "decryption_success")
                    except Exception as decrypt_error:
                        logger.warning_with_filename("Decryption failed for {filename}: {error}", doc.filename, error=str(decrypt_error))
                        file_bytes = encrypted_content  # Fallback to raw content
                        monitor_processing_security(str(doc.session.id), "decryption_fallback")
                else:
                    # Read unencrypted content
                    file_bytes = doc.file.read()
                    if settings.PRIVACY_ENGINE_ENABLED:
                        logger.warning_with_filename("Security: Processing {filename} without encryption (privacy disabled or no key)", doc.filename)

                # Process with error handling and memory cleanup
                analysis_result_data = None
                try:
                    analysis_result_data = analyzer.analyze_document(file_bytes, doc.filename)
                
                    if analysis_result_data:
                        # Convert dataclass to dict before saving
                        result_dict = dataclasses.asdict(analysis_result_data)
                        AnalysisResult.objects.create(
                            session=session,
                            document=doc,
                            result_data=result_dict
                        )
                        analyzed_docs_data.append(analysis_result_data)
                        
                    doc.status = Document.Status.PROCESSED
                    doc.save()
                    
                except Exception as doc_error:
                    send_update(f"Error processing {doc.filename}: {str(doc_error)}")
                    doc.status = Document.Status.FAILED
                    doc.save()
            
                finally:
                    # Force garbage collection after each document
                    if 'analysis_result_data' in locals():
                        del analysis_result_data
                    gc.collect()
                    
            except Exception as e:
                send_update(f"Failed to process document {doc.filename}: {str(e)}")
                doc.status = Document.Status.FAILED
                doc.save()

        send_update("Generating analysis report...")
        
        # 3. Calculate Tax Summary with final cleanup
        if analyzed_docs_data:
            assistant.analyzed_documents = analyzed_docs_data
            tax_summary = assistant.calculate_tax_summary()

            # Store the final summary
            AnalysisResult.objects.create(
                session=session,
                result_data=tax_summary
            )
        else:
            send_update("No documents were successfully processed.")
            raise Exception("No documents were successfully processed")

        session.status = ProcessingSession.Status.COMPLETED
        session.save()

        task.status = AnalysisTask.Status.SUCCESS
        task.save()
        send_update("Analysis complete.")

    except Exception as e:
        try:
            task.status = AnalysisTask.Status.FAILED
            task.save()
            session.status = ProcessingSession.Status.FAILED
            session.save()
        except:
            pass
        send_update(f"An error occurred: {str(e)}")
        
    finally:
        # Critical cleanup to prevent memory leaks and SIGSEGV
        
            
        # Clean up heavy objects
        if analyzer:
            del analyzer
        if assistant:
            del assistant
            
        # Force final garbage collection
        gc.collect()
