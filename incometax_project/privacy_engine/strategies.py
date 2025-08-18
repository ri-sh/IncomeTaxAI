import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from django.conf import settings

def derive_key_from_session_id(session_id: str) -> bytes:
    """
    Derives a unique and deterministic 256-bit key for the given session ID.
    """
    if not hasattr(settings, 'ENCRYPTION_SALT'):
        raise ValueError("ENCRYPTION_SALT must be defined in Django settings.")
    
    salt = settings.ENCRYPTION_SALT.encode()
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = kdf.derive(session_id.encode())
    return base64.urlsafe_b64encode(key)

def get_fernet_instance(encryption_key: bytes) -> Fernet:
    """
    Returns a Fernet instance for the given encryption key.
    """
    return Fernet(encryption_key)

# No global key_manager instance needed anymore
# The key will be passed explicitly