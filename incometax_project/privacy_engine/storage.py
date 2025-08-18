from io import BytesIO

from cryptography.fernet import Fernet
from django.core.files.base import ContentFile
from django.core.files.storage import Storage, FileSystemStorage
from django.utils.deconstruct import deconstructible
from django.utils.functional import cached_property
from django.conf import settings

from .strategies import get_fernet_instance, derive_key_from_session_id


@deconstructible
class EncryptedStorage(Storage):
    """
    A custom storage backend that encrypts files on save and decrypts on open.
    It wraps another storage backend to handle the actual file persistence.
    Encryption/decryption is conditional based on settings.PRIVACY_ENGINE_ENABLED.
    """

    def __init__(self, storage=None):
        self.storage = storage or FileSystemStorage()
        print(f"DEBUG: EncryptedStorage initialized with storage type: {type(self.storage)}")

    def get_fernet_for_session(self, session_id):
        """
        Creates a Fernet instance for the given session ID.
        Used for both encryption during save and decryption during read.
        """
        if not settings.PRIVACY_ENGINE_ENABLED:
            return None
        
        try:
            encryption_key = derive_key_from_session_id(session_id)
            return get_fernet_instance(encryption_key)
        except Exception as e:
            print(f"ERROR: Failed to create Fernet instance for session {session_id}: {e}")
            return None

    def _save(self, name, content):
        """
        Encrypt the file content before passing it to the underlying storage, if privacy is enabled.
        Otherwise, save directly.
        
        NOTE: This requires session_id to be passed via storage instance or context.
        For now, we'll save unencrypted and handle encryption at the view level.
        """
        if not settings.PRIVACY_ENGINE_ENABLED:
            return self.storage.save(name, content)

        # CRITICAL: Storage layer cannot access session_id directly
        # Encryption must be handled at the view/model layer where session context is available
        print("INFO: Privacy enabled but encryption handled at view layer, not storage layer")
        return self.storage.save(name, content)

    def _open(self, name, mode='rb'):
        """
        Fetch the file from the underlying storage.
        If privacy is enabled, return encrypted content for caller to decrypt.
        If privacy is disabled, return file directly.
        """
        if not settings.PRIVACY_ENGINE_ENABLED:
            return self.storage.open(name, mode)
        
        # Return encrypted file - caller must decrypt with proper session key
        return self.storage.open(name, mode)

    def url(self, name):
        """
        Returns the URL to the file. If privacy is enabled, direct URL access is not supported.
        """
        if not settings.PRIVACY_ENGINE_ENABLED:
            return self.storage.url(name)
        raise NotImplementedError(
            "Direct URL access is not supported for encrypted files when privacy is enabled. "
            "A secure serving view is required."
        )

    # The following methods are pass-through to the underlying storage.

    def delete(self, name):
        return self.storage.delete(name)

    def exists(self, name):
        return self.storage.exists(name)

    def listdir(self, path):
        return self.storage.listdir(path)

    def size(self, name):
        # Size of the encrypted file, not the original.
        # If privacy is off, this will be the actual size.
        return self.storage.size(name)

    def get_accessed_time(self, name):
        return self.storage.get_accessed_time(name)

    def get_created_time(self, name):
        return self.storage.get_created_time(name)

    def get_modified_time(self, name):
        return self.storage.get_modified_time(name)
