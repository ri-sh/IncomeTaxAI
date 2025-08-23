# 🔐 Privacy Engine Architecture Design

## 🎯 Overview

The Privacy Engine is a comprehensive security system designed to protect sensitive financial data throughout the entire document processing pipeline. It implements both visual privacy (UI masking) and backend privacy (encryption/decryption) to ensure maximum data protection.

## 🔒 Core Privacy Principles

1. **Zero-Trust Architecture**: Never store sensitive data in plaintext
2. **Session-Based Encryption**: Each session has unique encryption keys
3. **End-to-End Protection**: Data encrypted from upload to analysis to storage
4. **Minimal Exposure**: Decrypt only when absolutely necessary for processing
5. **Audit Trail**: Log all encryption/decryption operations

## 🏗️ Architecture Components

### 1. **Visual Privacy Layer (Implemented)**

#### Frontend Masking System
```javascript
// Privacy modes
const PRIVACY_MODES = {
    FULL_MASK: "X,XX,XXX",     // Complete masking
    PARTIAL_MASK: "X,XX,123",   // Show last 3 digits
    NO_MASK: "1,23,456"         // Full visibility
};

// Dynamic masking based on amount size
function maskAmount(amount) {
    if (!privacyMode) return amount.toLocaleString();
    
    const amountStr = amount.toString();
    const length = amountStr.length;
    
    return generateMask(length);
}
```

#### Features Implemented:
- ✅ **Number Masking**: Financial amounts shown as "XX,XX,XXX"
- ✅ **Eye Toggle Button**: 👁️‍🗨️ Show/Hide toggle in UI
- ✅ **Privacy Status Bar**: Real-time privacy mode indicator
- ✅ **Data Attributes**: All sensitive values tagged with `data-amount`

### 2. **Backend Privacy Engine (Design)**

#### Session-Based Encryption System

```python
# Privacy Engine Core
class PrivacyEngine:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.master_key = self._derive_session_key(session_id)
        self.document_cipher = Fernet(self.master_key)
        self.db_cipher = AESCipher(self.master_key)
    
    def _derive_session_key(self, session_id: str) -> bytes:
        """Generate unique encryption key per session"""
        salt = settings.ENCRYPTION_SALT.encode()
        key = PBKDF2(session_id, salt, 32, count=100000, hmac_hash_module=SHA256)
        return base64.urlsafe_b64encode(key)
```

#### Document Processing Pipeline

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   File Upload   │───▶│   Encrypt File   │───▶│  Store Encrypted│
│   (Plaintext)   │    │  (Session Key)   │    │   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Generate Hash   │    │  Celery Worker   │◄───│ Decrypt for     │
│ for Integrity   │    │  (Processing)    │    │ Processing Only │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Re-encrypt &    │
                       │ Store Results   │
                       └─────────────────┘
```

## 🔧 Implementation Strategy

### Phase 1: Document Encryption (Priority: High)

#### A. File Upload Encryption
```python
# models.py
class EncryptedDocument(models.Model):
    session = models.ForeignKey(ProcessingSession, on_delete=models.CASCADE)
    filename_encrypted = models.CharField(max_length=255)  # Encrypted filename
    content_encrypted = models.BinaryField()  # Encrypted file content
    file_hash = models.CharField(max_length=64)  # Integrity check
    encryption_metadata = models.JSONField()  # Cipher info, IV, etc.
    
    created_at = models.DateTimeField(auto_now_add=True)
    decrypted_at = models.DateTimeField(null=True)  # Audit trail
```

#### B. Celery Worker Decryption
```python
# tasks.py
@app.task
def process_encrypted_document(session_id: str, encrypted_doc_id: int):
    privacy_engine = PrivacyEngine(session_id)
    
    # 1. Decrypt document for processing
    encrypted_doc = EncryptedDocument.objects.get(id=encrypted_doc_id)
    decrypted_content = privacy_engine.decrypt_document(encrypted_doc)
    
    # 2. Process document (AI extraction)
    extracted_data = analyze_document(decrypted_content)
    
    # 3. Encrypt extracted data
    encrypted_results = privacy_engine.encrypt_analysis_results(extracted_data)
    
    # 4. Store encrypted results
    AnalysisResult.objects.create(
        document=encrypted_doc,
        encrypted_data=encrypted_results
    )
    
    # 5. Clear decrypted content from memory
    del decrypted_content
```

### Phase 2: Database Field Encryption (Priority: Medium)

#### A. Encrypted Model Fields
```python
# Custom encrypted fields
class EncryptedFloatField(models.FloatField):
    """Encrypt sensitive financial amounts"""
    
    def to_python(self, value):
        if isinstance(value, str) and value.startswith('enc:'):
            return privacy_engine.decrypt_float(value)
        return super().to_python(value)
    
    def get_prep_value(self, value):
        if value is not None:
            return privacy_engine.encrypt_float(value)
        return value

# Updated models
class AnalysisResult(models.Model):
    gross_salary = EncryptedFloatField()  # Encrypted in DB
    tax_deducted = EncryptedFloatField()  # Encrypted in DB
    personal_info = EncryptedJSONField()  # PAN, name, etc.
```

#### B. Query-Time Decryption
```python
class DecryptionQuerySet(models.QuerySet):
    def decrypt_for_session(self, session_id: str):
        """Decrypt results for specific session only"""
        privacy_engine = PrivacyEngine(session_id)
        
        results = []
        for result in self:
            decrypted = privacy_engine.decrypt_analysis_result(result)
            results.append(decrypted)
        
        return results
```

### Phase 3: Advanced Security Features (Priority: Low)

#### A. Password-Protected PDFs
```python
class PDFPasswordProtection:
    def protect_pdf(self, pdf_path: str, session_id: str) -> str:
        """Add password protection using session-derived password"""
        password = self._generate_pdf_password(session_id)
        
        # Use PyPDF2 or similar to add password protection
        protected_pdf = self._add_password_protection(pdf_path, password)
        return protected_pdf
    
    def _generate_pdf_password(self, session_id: str) -> str:
        """Generate unique PDF password per session"""
        return hashlib.sha256(f"{session_id}:{settings.PDF_SALT}".encode()).hexdigest()[:16]
```

#### B. Key Rotation System
```python
class KeyRotationManager:
    def rotate_session_keys(self, age_threshold_hours: int = 24):
        """Rotate encryption keys for old sessions"""
        old_sessions = ProcessingSession.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=age_threshold_hours)
        )
        
        for session in old_sessions:
            self._rotate_session_encryption(session)
```

## 🛡️ Security Measures

### 1. **Encryption Standards**
- **Algorithm**: AES-256-GCM for symmetric encryption
- **Key Derivation**: PBKDF2 with 100,000 iterations
- **Session Keys**: Unique per session, derived from session ID + salt
- **File Encryption**: Fernet (AES 128 CBC + HMAC SHA256)

### 2. **Key Management**
```python
# settings.py
ENCRYPTION_CONFIG = {
    'MASTER_SALT': env('ENCRYPTION_MASTER_SALT'),  # From environment
    'KEY_ROTATION_HOURS': 24,
    'SESSION_KEY_BITS': 256,
    'PBKDF2_ITERATIONS': 100000,
}

# Never store keys in code or database
# Use environment variables + HSM for production
```

### 3. **Audit Trail**
```python
class PrivacyAuditLog(models.Model):
    session_id = models.CharField(max_length=255)
    operation = models.CharField(max_length=50)  # 'encrypt', 'decrypt', 'access'
    document_id = models.CharField(max_length=255, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    user_ip = models.GenericIPAddressField(null=True)
    success = models.BooleanField(default=True)
```

## 📊 Performance Considerations

### 1. **Encryption Overhead**
- **File Encryption**: ~5-10% overhead for PDF processing
- **Database Fields**: ~2-3% query performance impact
- **Memory Usage**: +20% during decryption operations

### 2. **Optimization Strategies**
```python
# Lazy decryption - only when needed
class LazyDecryptionResult:
    def __init__(self, encrypted_data, privacy_engine):
        self.encrypted_data = encrypted_data
        self.privacy_engine = privacy_engine
        self._decrypted_cache = None
    
    @property
    def gross_salary(self):
        if not self._decrypted_cache:
            self._decrypted_cache = self.privacy_engine.decrypt(self.encrypted_data)
        return self._decrypted_cache['gross_salary']
```

### 3. **Caching Strategy**
- **Session-based cache**: Decrypt once per session, cache in memory
- **Cache expiration**: Auto-expire after session timeout
- **Memory limits**: Clear cache when memory usage > threshold

## 🚀 Implementation Roadmap

### Week 1-2: Foundation
- ✅ **Visual Privacy**: Implemented (masking + eye toggle)
- ⏳ **Core Privacy Classes**: PrivacyEngine, encryption utilities
- ⏳ **Session Key Management**: Derivation and storage

### Week 3-4: Document Encryption
- ⏳ **File Upload Encryption**: Encrypt on upload
- ⏳ **Celery Worker Decryption**: Process encrypted files
- ⏳ **Results Re-encryption**: Encrypt analysis results

### Week 5-6: Database Encryption
- ⏳ **Custom Field Types**: EncryptedFloatField, EncryptedJSONField
- ⏳ **Model Updates**: Migrate sensitive fields to encrypted versions
- ⏳ **Query Optimization**: Efficient decryption queries

### Week 7-8: Advanced Features
- ⏳ **PDF Password Protection**: Session-based PDF passwords
- ⏳ **Audit Logging**: Track all encryption operations
- ⏳ **Key Rotation**: Automated key rotation system

## 💡 Usage Examples

### Frontend Privacy Toggle
```javascript
// User clicks eye button
togglePrivacy(); // Shows: ₹XX,XX,XXX → ₹12,68,359

// Privacy status
<div id="privacyIndicator">🔒 Privacy Mode: ON</div>
```

### Backend Encryption
```python
# Upload and encrypt document
privacy_engine = PrivacyEngine(session_id)
encrypted_doc = privacy_engine.encrypt_document(uploaded_file)

# Process with temporary decryption
with privacy_engine.temporary_decrypt(encrypted_doc) as decrypted_content:
    results = ai_analyzer.analyze(decrypted_content)
    # Content auto-cleared after context

# Store encrypted results
encrypted_results = privacy_engine.encrypt_results(results)
```

## 🔍 Security Benefits

### User Benefits
- 🔒 **Visual Privacy**: Sensitive amounts hidden from shoulder surfing
- 🛡️ **Data Protection**: Files encrypted even if database compromised
- 🔑 **Session Isolation**: Each session's data encrypted with unique keys
- 📱 **Screen Recording Protection**: Masked values in screenshots

### System Benefits
- 🏰 **Defense in Depth**: Multiple layers of protection
- 🔄 **Key Rotation**: Regular key updates minimize exposure
- 📊 **Audit Trail**: Complete encryption/decryption logging
- ⚡ **Performance**: Optimized for minimal overhead

## 🎯 Compliance & Standards

### Regulatory Compliance
- **GDPR**: Right to erasure via key destruction
- **SOX**: Audit trail for financial data access
- **PCI DSS**: Encryption standards for sensitive data
- **Indian IT Act**: Data localization and protection

### Security Standards
- **NIST Cybersecurity Framework**: Comprehensive protection
- **ISO 27001**: Information security management
- **OWASP Top 10**: Web application security best practices

This privacy engine provides enterprise-grade protection for sensitive financial data while maintaining usability and performance.