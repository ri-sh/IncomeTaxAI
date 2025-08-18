import uuid
from django.db import models
from privacy_engine.storage import EncryptedStorage

class ProcessingSession(models.Model):
    """
    Represents a user's session for uploading and analyzing documents.
    """
    class Status(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        PENDING = 'PENDING', 'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATED)

    def __str__(self):
        return f"Session {self.id} ({self.status})"

class Document(models.Model):
    """
    Represents a single document uploaded by the user.
    """
    class Status(models.TextChoices):
        UPLOADED = 'UPLOADED', 'Uploaded'
        PROCESSING = 'PROCESSING', 'Processing'
        PROCESSED = 'PROCESSED', 'Processed'
        FAILED = 'FAILED', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProcessingSession, related_name='documents', on_delete=models.CASCADE)
    file = models.FileField(upload_to='documents/%Y/%m/%d/', storage=EncryptedStorage())
    filename = models.CharField(max_length=255)
    encrypted_filename = models.BinaryField(null=True, blank=True)
    is_filename_encrypted = models.BooleanField(default=False)

    @property
    def display_filename(self):
        from django.conf import settings
        from privacy_engine.strategies import derive_key_from_session_id, get_fernet_instance

        if self.is_filename_encrypted and settings.PRIVACY_ENGINE_ENABLED:
            try:
                # Derive key from session ID
                encryption_key = derive_key_from_session_id(str(self.session.id))
                fernet_instance = get_fernet_instance(encryption_key)
                # Convert memoryview/bytes to proper format for Fernet
                encrypted_data = bytes(self.encrypted_filename)
                return fernet_instance.decrypt(encrypted_data).decode('utf-8')
            except Exception as e:
                print(f"Error decrypting filename for doc {self.id}: {e}")
                return f"Encrypted Filename Error ({self.id})"
        else:
            return self.filename  # Return plaintext filename
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.filename

class AnalysisTask(models.Model):
    """
    Tracks the state of a Celery task for a given session.
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        STARTED = 'STARTED', 'Started'
        SUCCESS = 'SUCCESS', 'Success'
        FAILED = 'FAILED', 'Failed'
        TIMEOUT = 'TIMEOUT', 'Timeout'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.OneToOneField(ProcessingSession, related_name='task', on_delete=models.CASCADE)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Analysis for session {self.session.id}"

class AnalysisResult(models.Model):
    """
    Stores the results from the document analysis.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ProcessingSession, related_name='results', on_delete=models.CASCADE)
    document = models.ForeignKey(Document, related_name='results', on_delete=models.CASCADE, null=True, blank=True)
    result_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)