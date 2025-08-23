# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IncomeTax AI is a Django-based web application that processes Indian income tax documents using AI (Ollama/Qwen2.5:3b model) to extract financial data and calculate tax obligations. The system supports both old and new tax regimes for FY 2024-25.

## Development Commands

### Local Development Setup
```bash
# Hybrid setup (recommended - native Ollama + Docker services)
cd incometax_project
./setup_hybrid.sh

# Full Docker setup (alternative)
./deploy.sh

# Hybrid deployment (if Ollama already running)
./deploy_hybrid.sh
```

### Database Operations
```bash
# Run migrations
docker-compose -f docker-compose.cpu.yml exec web python manage.py migrate

# Create migrations
docker-compose -f docker-compose.cpu.yml exec web python manage.py makemigrations

# Collect static files
docker-compose -f docker-compose.cpu.yml exec web python manage.py collectstatic --noinput
```

### Testing
```bash
# Run specific tax calculator tests
python run_tax_calculator_tests.py
python test_ca_calculations.py
python test_esop_integration.py

# Test document extraction
python test_document_extraction.py

# Test system integration
python test_complete_implementation.py

# Run Django tests
docker-compose -f docker-compose.cpu.yml exec web python manage.py test
```

### Monitoring and Debugging
```bash
# View service logs
docker-compose -f docker-compose.cpu.yml logs -f [service_name]

# Check service status
docker-compose -f docker-compose.cpu.yml ps

# Run health check
docker-compose -f docker-compose.cpu.yml exec celery python health_check.py

# Manual cleanup of stuck documents
docker-compose -f docker-compose.cpu.yml exec web python cleanup_now.py

# Monitor cleanup dashboard
./monitor_cleanup.sh

# Test Ollama connectivity
curl http://localhost:11434/api/tags
```

### Celery Operations
```bash
# Restart Celery workers
docker-compose -f docker-compose.cpu.yml restart celery celery2 celery3

# Clear Redis data
docker-compose -f docker-compose.cpu.yml exec redis redis-cli FLUSHDB

# Monitor Celery tasks
# Access Flower dashboard at http://localhost:5555
```

## Architecture

### High-Level Structure
- **Django Backend**: REST API with channels for WebSocket support
- **Document Processing**: AI-powered extraction using Ollama/Qwen2.5:3b
- **Tax Calculations**: Multi-regime support (old vs new) with ESOP handling
- **Distributed Processing**: Multiple Celery workers for concurrent document analysis
- **Production Ready**: Docker containerization with Redis/PostgreSQL

### Core Components

#### Django Apps
- `api/`: Main REST API endpoints, Celery tasks, views
- `documents/`: Document upload and session management models
- `analysis/`: Tax analysis logic and models

#### Document Processing Pipeline
1. **Upload**: Documents uploaded via `/api/sessions/{id}/upload_document/`
2. **Classification**: AI determines document type (Form16, payslip, bank certificate, etc.)
3. **Extraction**: Regex + AI extraction of financial data
4. **Processing**: Tax calculations using extracted data
5. **Results**: Comprehensive tax analysis with regime comparison

#### Key Processing Classes
- `OllamaDocumentAnalyzer` (`src/core/document_processing/ollama_analyzer.py`): AI document analysis
- `TaxCalculator` (`src/core/tax_calculator.py`): FY-aware tax calculations  
- `ESOPCalculator` (`src/core/esop_calculator.py`): ESOP/ESPP perquisite calculations
- `IncomeTaxCalculator` (`api/utils/tax_calculator.py`): Official tax rate implementation

#### Document Types Supported
- Form 16 (salary certificate)
- Payslips
- Bank interest certificates
- Capital gains statements
- Investment proofs (80C deductions)
- ELSS mutual fund statements
- NPS statements

### Database Models
- `ProcessingSession`: User session for document upload/analysis
- `Document`: Individual uploaded documents with processing status
- `AnalysisTask`: Celery task tracking
- `AnalysisResult`: Final tax analysis results

### AI Integration
- **Model**: Qwen2.5:3b via Ollama (configurable via `OLLAMA_MODEL`)
- **Timeout Protection**: 60s classification, 120s extraction limits
- **Memory Management**: Solo pool workers, 1 task per worker lifecycle
- **Error Handling**: Graceful fallback to regex extraction

### Tax Calculation Features
- **FY Support**: 2023-24 and 2024-25 with accurate slab rates
- **Regime Comparison**: Automatic old vs new regime analysis
- **ESOP Handling**: Section 17(2)(vi) perquisite calculations
- **Deduction Support**: 80C, 80D, HRA, standard deduction
- **Live Editing**: Interactive tax parameter adjustment

## Environment Configuration

### Key Environment Variables
- `OLLAMA_BASE_URL`: Ollama service URL (default: http://localhost:11434)
- `OLLAMA_MODEL`: AI model name (default: Qwen2.5:3b)
- `CELERY_BROKER_URL`: Redis URL for Celery
- `DATABASE_URL`: PostgreSQL connection string
- `DEBUG`: Development mode flag

### Development vs Production
- **Development**: SQLite database, native Ollama recommended
- **Production**: PostgreSQL, Redis, containerized deployment
- **Hybrid Mode**: Native Ollama + Docker services (best performance)

## File Paths and Structure

### Key Directories
- `incometax_project/`: Main Django project
- `src/core/`: Core tax calculation and document processing logic
- `api/`: REST API implementation and Celery tasks
- `documents/`: Document models and upload handling
- `static/`: Frontend assets
- `media/documents/`: Uploaded document storage

### Important Files
- `manage.py`: Django management commands (note: adds src/ to Python path)
- `docker-compose.yml`: GPU-enabled deployment
- `docker-compose.cpu.yml`: CPU-only deployment (default)
- `requirements.txt`: Production Django dependencies
- `../requirements.txt`: Development AI/ML dependencies

## Development Notes

### Working with Tax Calculations
- Tax slabs are FY-specific in `TaxCalculator._configure_for_fy()`
- ESOP calculations follow Section 17(2)(vi) rules
- Always test both old and new regime calculations
- Use `test_ca_calculations.py` for comprehensive validation

### Document Processing Development
- Regex extractors in `src/core/document_processing/regex_extractor.py`
- AI prompts in `src/core/document_processing/prompts.py`
- Test extraction with individual test files before integration

### Celery Task Development
- Tasks in `api/tasks.py` handle document processing pipeline
- Use timeouts and error handling for AI operations
- Clean up memory after heavy operations (`gc.collect()`)
- Monitor task status via Flower dashboard

### Performance Considerations
- Hybrid deployment gives 50-90% CPU reduction vs full Docker
- Use solo pool for Celery workers to prevent memory conflicts
- Limit worker concurrency to 1 for AI processing stability
- Monitor memory usage with `docker stats`

## Access Points

- **Web Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/
- **Celery Monitoring**: http://localhost:5555 (Flower)
- **Tax Analysis Report**: http://localhost:8000/api/tax_analysis_report/
- **Admin Interface**: http://localhost:8000/admin/