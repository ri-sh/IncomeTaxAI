# TaxSahaj Security Documentation

## Overview

TaxSahaj implements a **security-first, privacy-preserving** architecture for income tax document processing without requiring user registration or storing personal identifiable information.

## Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend UI   │───▶│  Session + Rate  │───▶│  Privacy Engine │
│                 │    │    Limiting      │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   Django API     │───▶│   Encrypted     │
                       │                  │    │   File Storage  │
                       └──────────────────┘    └─────────────────┘
```

## Authentication & Access Control

### Session-Based Authentication
**Design**: Uses Django sessions + IP validation instead of user accounts.

**Example Flow**:
```
User Visit ──▶ Auto Session Creation ──▶ IP + Session Validation ──▶ API Access
            └─ 30min timeout          └─ Max 3 sessions/IP       └─ Rate limited
```

**Benefits**:
- No personal data collection
- Automatic session management
- IP-based isolation

### Rate Limiting
**Design**: Multi-level rate limiting per IP address to prevent resource abuse.

**Example Limits**:
```
Session Creation:  5 requests/hour/IP
File Upload:      20 requests/hour/IP  
API Calls:       100 requests/hour/IP
```

**Implementation**:
- Django cache-based tracking
- Sliding window counters
- Graceful degradation

## Privacy Engine

### Document Encryption
**Design**: All uploaded documents are encrypted using session-derived keys before storage.

**Example Process**:
```
Document Upload ──▶ Generate Session Key ──▶ Encrypt Content ──▶ Store Encrypted
                 └─ Derive from Session ID  └─ AES-256        └─ Encrypted filename
```

**Key Features**:
- Session-specific encryption keys
- Filename encryption for privacy
- No plaintext storage

### Data Flow Diagram
```
┌─────────────┐    Encryption    ┌─────────────┐    Processing    ┌─────────────┐
│   Upload    │ ──────────────▶  │  Encrypted  │ ──────────────▶  │   Analysis  │
│ (Plaintext) │                  │   Storage   │                  │  (In Memory)│
└─────────────┘                  └─────────────┘                  └─────────────┘
                                          │                              │
                                          ▼                              ▼
                                 ┌─────────────┐                ┌─────────────┐
                                 │ Auto-Delete │                │   Secure    │
                                 │After Session│                │  Cleanup    │
                                 └─────────────┘                └─────────────┘
```

## API Security

### CORS & CSRF Protection
**Design**: Restricts API access to authorized domains with CSRF token validation.

**Example Configuration**:
```python
# Only allow your Railway domain
CORS_ALLOWED_ORIGINS = [
    "https://incometax-simple-production.up.railway.app"
]
CORS_ALLOW_CREDENTIALS = True  # Enable CSRF tokens
```

### Input Validation
**Example**: Document upload validation
- File type checking (PDF, images only)
- Size limits (max 10MB per file)
- Malware scanning integration
- Content sanitization

## Deployment Security

### Railway Configuration
**Design**: Environment-specific security settings for production deployment.

**Example Security Headers**:
```python
# Production settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

### Environment Variables
**Example Sensitive Data**:
```bash
# Never in code - only in Railway environment
SECRET_KEY=production-secret-key
DATABASE_URL=encrypted-db-connection
ENCRYPTION_MASTER_KEY=session-key-derivation
```

## Monitoring & Logging

### Security Event Logging
**Design**: Privacy-safe logging that tracks security events without exposing user data.

**Example Log Entry**:
```json
{
  "event": "rate_limit_exceeded",
  "ip_hash": "sha256_hash_of_ip",
  "action": "file_upload", 
  "timestamp": "2024-01-01T10:00:00Z",
  "session_hash": "anonymized_session_id"
}
```

### Privacy-Safe Monitoring
**What We Track**:
- Request patterns (anonymized)
- Error rates and types
- Resource usage metrics
- Security violations

**What We Never Track**:
- Document contents
- Personal information
- Actual IP addresses (only hashes)
- Unencrypted session data

## Threat Model

### Protected Against
✅ **Unauthorized API access** - Session + IP validation  
✅ **Resource exhaustion** - Rate limiting  
✅ **Data breaches** - End-to-end encryption  
✅ **Session hijacking** - IP binding + timeouts  
✅ **CSRF attacks** - Token validation  

### Example Attack Scenario
```
Attacker attempts bulk API calls ──▶ Rate limiter blocks after 100/hour
                                 └──▶ IP gets temporarily blacklisted
                                 └──▶ Legitimate users unaffected
```

## Quick Security Checklist

- [ ] All documents encrypted at rest
- [ ] Session-based access control active  
- [ ] Rate limiting configured per environment
- [ ] CORS restricted to authorized domains
- [ ] Environment secrets properly configured
- [ ] Privacy-safe logging enabled
- [ ] Auto-cleanup of expired sessions working

---

> **Note**: This security model prioritizes user privacy and resource protection while maintaining ease of use. No user registration is required, and no personal data is permanently stored.