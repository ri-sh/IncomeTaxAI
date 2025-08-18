from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from documents.models import Document, ProcessingSession # Import Document and ProcessingSession
from privacy_engine.strategies import get_fernet_instance, derive_key_from_session_id
from django.conf import settings
import mimetypes
import os
from contextlib import contextmanager

@require_GET
@login_required
def serve_protected_file(request, file_id):
    """
    Securely serves a file after decryption (if privacy is enabled).
    Requires user to be logged in and have access to the associated session.
    """
    try:
        document = get_object_or_404(Document, id=file_id)
    except Http404:
        return HttpResponse("File not found.", status=404)

    # Authorization check: Ensure the logged-in user has access to this session's files.
    # This is a basic check. More complex logic might be needed based on your app's permissions.
    # Assuming Document.session is a ForeignKey to ProcessingSession, and ProcessingSession is linked to a user.
    # For now, let's assume request.user is directly linked to the session or has permissions.
    if not request.user.is_authenticated or document.session.pk != request.user.pk:
        return HttpResponse("You do not have permission to access this file.", status=403)

    file_content = None
    if settings.PRIVACY_ENGINE_ENABLED:
        try:
            # Derive the key for decryption
            encryption_key = derive_key_from_session_id(str(document.session.id))
            fernet_instance = get_fernet_instance(encryption_key)
            
            # Read encrypted content
            encrypted_content = document.file.read()
            
            # Decrypt content
            file_content = fernet_instance.decrypt(encrypted_content)
        except Exception as e:
            # Log the error for debugging
            print(f"Error decrypting file {file_id}: {e}")
            return HttpResponse("An error occurred while decrypting the file.", status=500)
    else:
        # If privacy is disabled, read the file directly (it's stored in plaintext)
        file_content = document.file.read()

    if file_content is None:
        return HttpResponse("File content could not be retrieved.", status=500)

    # Determine content type
    # Use the model property for decrypted filename
    display_filename = document.display_filename

    content_type, encoding = mimetypes.guess_type(display_filename)
    if content_type is None:
        content_type = 'application/octet-stream' # Default if type cannot be guessed

    response = HttpResponse(file_content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{display_filename}"'
    return response
