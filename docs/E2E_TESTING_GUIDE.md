# End-to-End (E2E) Testing Guide for IncomeTaxAI (using cURL)

This guide outlines a basic end-to-end testing flow for the IncomeTaxAI application's API using `curl` commands. These commands simulate a user's interaction with the system, from creating a session to retrieving analysis results.

**Assumptions:**
*   The Django application is running and accessible at `http://localhost:8000`.
*   You have `curl` installed on your system.
*   You have a sample PDF document (e.g., `document.pdf`) available for upload.

---

## E2E Test Flow

### 1. Create a New Session

This command initiates a new processing session. The response will provide a `session_id` that is crucial for all subsequent interactions related to this session.

```bash
curl -X POST http://localhost:8000/api/sessions/ \
-H "Content-Type: application/json" \
-d "{}"
```

**Expected Output (Example):**
```json
{
  "session_id": "random_signed_session_id_abc123",
  "created_at": "2025-08-18T10:00:00.000000Z",
  "status": "CREATED"
}
```
*   **Action:** Copy the `session_id` from the output. You will use it in the following steps.

---

### 2. Upload a Document to a Session

This command uploads a document (e.g., a PDF) to the newly created session. Replace the placeholder with your actual `session_id` and the path to your document.

```bash
curl -X POST http://localhost:8000/api/sessions/your_signed_session_id_here/upload_document/ \
-H "Content-Type: multipart/form-data" \
-F "files=@/path/to/your/document.pdf"
```

*   **Replace:**
    *   `your_signed_session_id_here`: The `session_id` obtained from Step 1.
    *   `/path/to/your/document.pdf`: The absolute or relative path to the PDF document you wish to upload.

**Expected Output (Example):**
```json
[
  {
    "id": "random_document_id_xyz789",
    "display_filename": "sample_document.pdf",
    "status": "UPLOADED",
    "uploaded_at": "2025-08-18T10:01:00.000000Z"
  }
]
```

---

### 3. Trigger Analysis for a Session

Once documents are uploaded, this command initiates the analysis process for all documents within the specified session.

```bash
curl -X POST http://localhost:8000/api/sessions/your_signed_session_id_here/analyze/
```

*   **Replace:**
    *   `your_signed_session_id_here`: The `session_id` obtained from Step 1.

**Expected Output (Example):**
```json
{
  "message": "Analysis started",
  "task_id": "random_celery_task_id_def456",
  "session_status": "PROCESSING"
}
```

---

### 4. Check the Status of a Session

This command allows you to monitor the progress of the analysis. You might need to execute this command multiple times until the `session_status` changes to `COMPLETED` and `task_status` changes to `SUCCESS`.

```bash
curl -X GET http://localhost:8000/api/sessions/your_signed_session_id_here/status/
```

*   **Replace:**
    *   `your_signed_session_id_here`: The `session_id` obtained from Step 1.

**Expected Output (Example - during processing):**
```json
{
  "session_id": "random_signed_session_id_abc123",
  "session_status": "PROCESSING",
  "task_status": "STARTED",
  "created_at": "2025-08-18T10:00:00.000000Z",
  "documents": [
    {
      "id": "random_document_id_xyz789",
      "filename": "sample_document.pdf",
      "status": "PROCESSING",
      "uploaded_at": "2025-08-18T10:01:00.000000Z",
      "processed_at": null,
      "file_size": 0,
      "progress_percentage": 0,
      "status_text": "Processing document..."
    }
  ],
  "total_documents": 0,
  "processed_documents": 0,
  "processing_documents": 0,
  "failed_documents": 0,
  "overall_progress": 0,
  "distributed_tasks": [],
  "processing_method": "single"
}
```

**Expected Output (Example - when completed):**
```json
{
  "session_id": "random_signed_session_id_abc123",
  "session_status": "COMPLETED",
  "task_status": "SUCCESS",
  "created_at": "2025-08-18T10:00:00.000000Z",
  "documents": [
    {
      "id": "random_document_id_xyz789",
      "filename": "sample_document.pdf",
      "status": "PROCESSED",
      "uploaded_at": "2025-08-18T10:01:00.000000Z",
      "processed_at": "2025-08-18T10:05:00.000000Z",
      "file_size": 0,
      "progress_percentage": 0,
      "status_text": "Completed successfully"
    }
  ],
  "total_documents": 0,
  "processed_documents": 0,
  "processing_documents": 0,
  "failed_documents": 0,
  "overall_progress": 0,
  "distributed_tasks": [],
  "processing_method": "single"
}
```

---

### 5. Retrieve Analysis Results for a Session

Once the session status is `COMPLETED`, you can fetch the detailed analysis results.

```bash
curl -X GET http://localhost:8000/api/sessions/your_signed_session_id_here/analysis_results/
```

*   **Replace:**
    *   `your_signed_session_id_here`: The `session_id` obtained from Step 1.

**Expected Output (Example - content will vary based on analysis):**
```json
{
  "session_id": "random_signed_session_id_abc123",
  "tax_summary": {
    "financial_year": "2024-25",
    "assessment_year": "2025-26",
    "client_name": "Generic Tax Analysis Report",
    "income_breakdown": {
      "salary_income": {
        "basic_and_allowances_17_1": 0,
        "perquisites_espp_17_2": 0,
        "total_salary": 0
      },
      "other_income": {
        "bank_interest": 0,
        "dividend_income": 0,
        "total_other": 0
      },
      "gross_total_income": 0
    },
    "deductions_old_regime": {
      "section_80c": 0,
      "section_80d": 0,
      "total_deductions": 0
    },
    "tax_calculation_old_regime": {
      "taxable_income": 0,
      "tax_on_income": 0,
      "surcharge": 0,
      "health_education_cess": 0,
      "total_tax_liability": 0,
      "tds_paid": 0,
      "refund_due": 0,
      "additional_tax_payable": 0
    },
    "tax_calculation_new_regime": {
      "taxable_income": 0,
      "tax_on_income": 0,
      "surcharge": 0,
      "health_education_cess": 0,
      "total_tax_liability": 0,
      "tds_paid": 0,
      "refund_due": 0,
      "additional_tax_payable": 0
    },
    "regime_comparison": {
      "old_regime_position": "Tax payable: ₹0.00",
      "new_regime_position": "Additional tax: ₹0.00",
      "savings_by_old_regime": 0,
      "recommended_regime": "old_regime",
      "recommendation_reason": "Old regime results in lower tax liability."
    },
    "documents_processed": 0,
    "processing_method": "parallel",
    "analysis_date": "2025-08-18"
  },
  "document_results": [
    {
      "document_id": "random_document_id_xyz789",
      "filename": "sample_document.pdf",
      "document_type": "form16",
      "data": {
        "document_type": "form16",
        "financial_year": "2024-25",
        "employer_details": {
          "employer_name": "Sample Corp",
          "employee_pan": "ABCDE9876G"
        },
        "salary_details": {
          "basic_salary": 0,
          "total_section_17_1": 0,
          "perquisites_espp": 0,
          "gross_salary": 0,
          "hra_received": 0
        },
        "deductions": {
          "pf_employee": 0,
          "professional_tax": 0
        },
        "exemptions": {
          "hra_exemption": 0
        },
        "tax_details": {
          "total_tds": 0
        }
      }
    }
  ],
  "total_documents": 0,
  "session_status": "COMPLETED"
}