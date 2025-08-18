"""
Privacy Engine Security Monitor
Provides runtime security verification and monitoring
"""

import os
import time
import logging
from django.conf import settings
from .strategies import derive_key_from_session_id, get_fernet_instance
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """Monitors privacy engine security at runtime"""
    
    @staticmethod
    def verify_file_encryption(file_path, session_id=None):
        """
        Verify that a file on disk is actually encrypted
        Returns (is_encrypted: bool, confidence: float, details: dict)
        """
        try:
            if not settings.PRIVACY_ENGINE_ENABLED:
                return False, 1.0, {"reason": "privacy_disabled"}
            
            if not os.path.exists(file_path):
                return False, 0.0, {"reason": "file_not_found"}
            
            # Read file content
            with open(file_path, 'rb') as f:
                content = f.read()
            
            if len(content) == 0:
                return False, 0.0, {"reason": "empty_file"}
            
            # Check for common readable patterns that shouldn't appear in encrypted files
            readable_patterns = [
                b'PDF',  # PDF header
                b'Form16',  # Common document content
                b'salary',
                b'income',
                b'PAN:',
                b'Rs.',
                b'rupees',
                b'bank',
                b'account',
                b'CONFIDENTIAL',
                b'TAX',
            ]
            
            found_readable = []
            for pattern in readable_patterns:
                if pattern.lower() in content.lower():
                    found_readable.append(pattern.decode('utf-8', errors='ignore'))
            
            # Check entropy (encrypted data should have high entropy)
            entropy = SecurityMonitor._calculate_entropy(content)
            
            # Calculate confidence
            if len(found_readable) == 0 and entropy > 7.0:
                confidence = min(1.0, entropy / 8.0)
                return True, confidence, {
                    "entropy": entropy,
                    "readable_patterns": found_readable,
                    "file_size": len(content)
                }
            else:
                confidence = max(0.0, 1.0 - (len(found_readable) * 0.2 + (8.0 - entropy) * 0.1))
                return False, confidence, {
                    "entropy": entropy,
                    "readable_patterns": found_readable,
                    "file_size": len(content),
                    "reason": "readable_content_found" if found_readable else "low_entropy"
                }
                
        except Exception as e:
            logger.error(f"Error verifying file encryption for {file_path}: {e}")
            return False, 0.0, {"reason": "verification_error", "error": str(e)}
    
    @staticmethod
    def verify_decryption_capability(encrypted_content, session_id):
        """
        Verify that we can successfully decrypt content with the session key
        Returns (can_decrypt: bool, decrypted_size: int, error: str)
        """
        try:
            if not settings.PRIVACY_ENGINE_ENABLED:
                return True, len(encrypted_content), "privacy_disabled"
            
            # Get session key
            session_key = derive_key_from_session_id(session_id)
            fernet = get_fernet_instance(session_key)
            
            # Try to decrypt
            decrypted = fernet.decrypt(encrypted_content)
            
            return True, len(decrypted), None
            
        except Exception as e:
            return False, 0, str(e)
    
    @staticmethod
    def log_security_event(event_type, session_id, details=None):
        """Log security-related events for audit"""
        timestamp = time.time()
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "session_id": session_id,
            "privacy_enabled": settings.PRIVACY_ENGINE_ENABLED,
            "details": details or {}
        }
        
        logger.info(f"SECURITY_EVENT: {event_type} for session {session_id}: {details}")
        
        # In production, you might want to send this to a security monitoring system
        # or write to a dedicated security log file
    
    @staticmethod
    def validate_session_key(session_id):
        """Validate that session key can be derived correctly"""
        try:
            if not settings.PRIVACY_ENGINE_ENABLED:
                return True, "privacy_disabled"
            
            key = derive_key_from_session_id(session_id)
            
            # Verify key properties
            if len(key) != 44:  # Base64 encoded 32-byte key
                return False, f"invalid_key_length_{len(key)}"
            
            # Try to create Fernet instance
            fernet = get_fernet_instance(key)
            
            # Test encrypt/decrypt
            test_data = b"security_test"
            encrypted = fernet.encrypt(test_data)
            decrypted = fernet.decrypt(encrypted)
            
            if decrypted != test_data:
                return False, "encrypt_decrypt_mismatch"
            
            return True, None
            
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def _calculate_entropy(data):
        """Calculate Shannon entropy of data (measure of randomness)"""
        if len(data) == 0:
            return 0
        
        # Count byte frequencies
        frequency = [0] * 256
        for byte in data:
            frequency[byte] += 1
        
        # Calculate entropy
        import math
        entropy = 0
        length = len(data)
        for count in frequency:
            if count > 0:
                p = count / length
                entropy -= p * math.log2(p)
        
        return entropy
    
    @staticmethod
    def security_health_check():
        """Perform comprehensive security health check"""
        health_report = {
            "timestamp": time.time(),
            "privacy_enabled": settings.PRIVACY_ENGINE_ENABLED,
            "checks": {}
        }
        
        # Check 1: Settings validation
        try:
            has_salt = hasattr(settings, 'ENCRYPTION_SALT') and settings.ENCRYPTION_SALT
            health_report["checks"]["encryption_salt"] = {
                "status": "pass" if has_salt else "fail",
                "details": "Encryption salt configured" if has_salt else "Missing ENCRYPTION_SALT"
            }
        except Exception as e:
            health_report["checks"]["encryption_salt"] = {
                "status": "error",
                "details": str(e)
            }
        
        # Check 2: Key derivation
        try:
            test_session_id = "test-session-123"
            key_valid, key_error = SecurityMonitor.validate_session_key(test_session_id)
            health_report["checks"]["key_derivation"] = {
                "status": "pass" if key_valid else "fail",
                "details": key_error or "Key derivation working"
            }
        except Exception as e:
            health_report["checks"]["key_derivation"] = {
                "status": "error", 
                "details": str(e)
            }
        
        # Check 3: Memory security
        try:
            import gc
            fernet_instances = [obj for obj in gc.get_objects() if isinstance(obj, Fernet)]
            health_report["checks"]["memory_security"] = {
                "status": "pass" if len(fernet_instances) < 10 else "warn",
                "details": f"Found {len(fernet_instances)} Fernet instances in memory"
            }
        except Exception as e:
            health_report["checks"]["memory_security"] = {
                "status": "error",
                "details": str(e)
            }
        
        # Overall status
        check_results = [check["status"] for check in health_report["checks"].values()]
        if "error" in check_results or "fail" in check_results:
            health_report["overall_status"] = "unhealthy"
        elif "warn" in check_results:
            health_report["overall_status"] = "degraded"
        else:
            health_report["overall_status"] = "healthy"
        
        logger.info(f"SECURITY_HEALTH_CHECK: {health_report['overall_status']} - {len(health_report['checks'])} checks performed")
        
        return health_report

# Convenience functions for common security checks
def verify_document_security(document):
    """Verify security for a Document instance"""
    if not settings.PRIVACY_ENGINE_ENABLED:
        return {"status": "disabled", "message": "Privacy engine disabled"}
    
    try:
        # Check file encryption
        file_encrypted, confidence, details = SecurityMonitor.verify_file_encryption(
            document.file.path, 
            str(document.session.id)
        )
        
        # Check filename encryption
        filename_encrypted = document.is_filename_encrypted
        
        # Log security event
        SecurityMonitor.log_security_event(
            "document_security_check",
            str(document.session.id),
            {
                "document_id": str(document.id),
                "filename": document.filename,
                "file_encrypted": file_encrypted,
                "filename_encrypted": filename_encrypted,
                "confidence": confidence
            }
        )
        
        return {
            "status": "secure" if file_encrypted and filename_encrypted else "insecure",
            "file_encryption": {
                "encrypted": file_encrypted,
                "confidence": confidence,
                "details": details
            },
            "filename_encryption": filename_encrypted
        }
        
    except Exception as e:
        logger.error(f"Error in document security verification: {e}")
        return {"status": "error", "message": str(e)}

def monitor_processing_security(session_id, operation):
    """Monitor security during processing operations"""
    if not settings.PRIVACY_ENGINE_ENABLED:
        return
    
    SecurityMonitor.log_security_event(
        f"processing_{operation}",
        session_id,
        {
            "operation": operation,
            "timestamp": time.time()
        }
    )