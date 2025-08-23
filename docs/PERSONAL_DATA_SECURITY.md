# 🔒 Personal Data Security & Privacy

This document outlines how personal information is handled and protected in the IncomeTax AI system.

## 🚨 Critical Security Notice

**⚠️ NEVER COMMIT PERSONAL DATA TO GIT ⚠️**

This repository contains code for processing sensitive financial documents. Personal information must never be committed to version control.

## 📁 Protected Directories & Files

The following directories and files are automatically excluded from git:

### Personal Financial Documents
```
# Document patterns
*Form16*
*Payslip*
*payslip*
*Bank_Interest*
*Mutual_Fund*
*Capital_Gains*
*Stock*
*NPS*
*nps*
*ELSS*
*PAN*
*Aadhaar*
*aadhar*

# Personal identifiers found in this project
870937*          # Employee ID pattern
1094698116*      # Account number pattern
```

### Media Directories
```
incometax_project/media/documents/
incometax_project/media/protected_files/
documents/2025/
documents/2024/
```

### Log Files (may contain filenames with personal data)
```
logs/
incometax_project/logs/
*.log
celerybeat-schedule
```

## 🔐 Privacy Engine Protection

The system includes a privacy engine that:

### File Encryption
- ✅ Encrypts uploaded documents at rest
- ✅ Uses AES-128 encryption with session-based keys
- ✅ Stores files in encrypted format in `media/protected_files/`

### Filename Protection
- ✅ Encrypts original filenames in database
- ✅ Uses session-specific encryption keys
- ✅ Prevents filename leakage in logs and URLs

### Session Security
- ✅ Session IDs include encryption key suffix
- ✅ Deterministic key derivation using PBKDF2-HMAC-SHA256
- ✅ Session-specific encryption isolation

## 📊 Data Flow Security

### Upload Process
1. **Client Upload** → Document received via secure HTTPS
2. **Filename Encryption** → Original filename encrypted and stored
3. **File Encryption** → Document content encrypted with session key
4. **Secure Storage** → Encrypted file stored in protected directory
5. **Database Entry** → Only encrypted metadata stored

### Processing Security
1. **Temporary Decryption** → Files decrypted only during AI processing
2. **Memory Protection** → Sensitive data cleared after processing
3. **Log Sanitization** → Personal data not logged in plain text
4. **Result Encryption** → Analysis results stored encrypted

### Access Control
1. **Session Isolation** → Each user's data isolated by session
2. **Key-Based Access** → Full session ID required for data access
3. **Time-Limited** → Sessions expire after inactivity
4. **Audit Trail** → All access attempts logged

## 🛡️ Development Guidelines

### For Developers

**DO:**
- ✅ Use test documents with fake data for development
- ✅ Clear personal data from logs before committing
- ✅ Test with synthetic financial documents
- ✅ Use environment variables for sensitive configuration
- ✅ Validate the privacy engine is working in tests

**DON'T:**
- ❌ Commit any real financial documents
- ❌ Include personal identifiers in code comments
- ❌ Log sensitive document content in plain text
- ❌ Disable privacy engine in production
- ❌ Use real personal data in test cases

### Code Examples

**✅ Good: Synthetic Test Data**
```python
test_document = {
    "employee_id": "TEST123",
    "name": "Test Employee",
    "pan": "ABCDE1234F",
    "salary": 500000
}
```

**❌ Bad: Real Personal Data**
```python
# Never do this
real_document = {
    "employee_id": "870937",
    "name": "Real Name",
    "pan": "REALP1234N"  # Real PAN number
}
```

## 🔍 Data Audit Checklist

Before any git commit or deployment:

- [ ] Check `git status` for any personal files
- [ ] Verify `.gitignore` patterns are working
- [ ] Confirm no personal identifiers in code
- [ ] Validate privacy engine is enabled
- [ ] Check logs don't contain sensitive data
- [ ] Verify test documents are synthetic

## 🚀 Production Deployment

### Environment Security
```bash
# Required environment variables
PRIVACY_ENGINE_ENABLED=true
ENCRYPTION_SALT=secure-random-salt
DATABASE_URL=secure-database-connection
DEBUG=False
```

### File System Security
```bash
# Proper permissions for media directories
chmod 700 media/documents/
chmod 700 media/protected_files/
chmod 644 logs/
```

### Network Security
- HTTPS enforced for all document uploads
- Database connections encrypted
- Redis connections secured
- API endpoints rate limited

## 🆘 Incident Response

### If Personal Data is Committed

1. **Immediate Action**
   ```bash
   # DO NOT just delete files - use git history cleanup
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch personal_file.pdf' \
     --prune-empty --tag-name-filter cat -- --all
   ```

2. **Force Push** (if repository is private)
   ```bash
   git push --force --all
   git push --force --tags
   ```

3. **Notify Team** - Inform all developers of the incident
4. **Review Access** - Check who had access to the compromised data
5. **Update Security** - Improve gitignore patterns

### If Personal Data is in Production

1. **Immediate Isolation** - Stop processing if needed
2. **Data Audit** - Identify scope of exposed data
3. **Encryption Check** - Verify privacy engine was active
4. **Compliance** - Follow GDPR/data protection requirements
5. **User Notification** - Inform affected users if required

## 📞 Security Contacts

For security incidents or questions:
- Review privacy engine logs
- Check encryption status in database
- Validate session isolation is working
- Confirm all uploaded files are encrypted

## 🔄 Regular Security Tasks

### Weekly
- [ ] Review gitignore effectiveness
- [ ] Check for accidentally committed personal data
- [ ] Validate privacy engine is operational
- [ ] Monitor log files for data leakage

### Monthly
- [ ] Update security documentation
- [ ] Review access patterns
- [ ] Test incident response procedures
- [ ] Audit encryption key management

### Before Each Release
- [ ] Security code review
- [ ] Privacy engine integration tests
- [ ] Penetration testing of file handling
- [ ] Compliance documentation update

## 📚 Related Documentation

- `docs/PRIVACY_ENGINE_DESIGN.md` - Technical privacy implementation
- `docs/PRIVACY_SECURITY_REPORT.md` - Security analysis report
- `docs/E2E_TESTING_GUIDE.md` - End-to-end security testing
- `.gitignore` - File exclusion patterns