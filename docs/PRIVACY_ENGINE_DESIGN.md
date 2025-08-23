# Privacy Engine: Architecture & Implementation Plan

This document outlines the architecture, design, and implementation plan for the modular, production-ready Privacy Engine.

## 1. Core Architecture: A Modular, Storage-Based Approach

The core of the engine will be a **Custom Encrypted Storage Backend** implemented in a new, reusable Django app named `privacy_engine`.

### How it Works:
1.  The `privacy_engine` app will provide a custom storage class, `EncryptedStorage`.
2.  This class will wrap another Django storage backend (e.g., `FileSystemStorage` for local development, `S3Boto3Storage` for production).
3.  When a file is saved via a `FileField`, `EncryptedStorage` will automatically encrypt the file's content *before* passing it to the underlying storage system.
4.  When a file is accessed, `EncryptedStorage` will fetch the encrypted data and decrypt it on the fly.

### Key Benefits:
- **Modularity & DRY:** Encryption logic is completely isolated. The rest of the application remains unaware of the encryption details.
- **Scalability & Flexibility:** The engine is storage-agnostic. Switching from local storage to a cloud provider like S3 will require minimal configuration changes.
- **Best Practice:** This approach properly leverages Django's built-in storage system, making it clean and maintainable.

## 2. Identified Gaps & Solutions

- **Gap:** The storage backend needs access to the session-specific encryption key but doesn't have direct access to the request context.
- **Solution:** We will implement a **Thread-Local Key Manager**. A view or Celery task will set the key for the current thread at the beginning of an operation. The storage backend will then securely access this key to perform encryption/decryption.

- **Gap:** The existing `documents.Document` model is not suitable for an encrypted-by-default system.
- **Solution:** The `privacy_engine` app will provide its own universal model, `ProtectedFile`, which will use the `EncryptedStorage` by default. Other apps will link to this model.

## 3. Implementation Task Breakdown

### Phase 1: Secure File Storage (Core Engine)

- **Task 1: Scaffolding:** Create the `privacy_engine` Django app using `manage.py startapp`.
- **Task 2: Key Management:** Implement the `ThreadLocalKeyManager` in `privacy_engine/strategies.py` for securely managing session-specific keys.
- **Task 3: Custom Storage:** Build the core `EncryptedStorage` class in `privacy_engine/storage.py`.
- **Task 4: Models & Migrations:** Create the `ProtectedFile` model in `privacy_engine/models.py` and generate the initial database migrations.
- **Task 5: Integration:** Update the file upload logic to use the new `ProtectedFile` model and the key manager.
- **Task 6: Secure Serving:** Create a secure view in `privacy_engine/views.py` to check permissions and serve decrypted files.

### Phase 2: Database Field Encryption (Future)

- **Task 7:** Implement custom encrypted model fields (e.g., `EncryptedCharField`, `EncryptedIntegerField`) in `privacy_engine/fields.py`.
- **Task 8:** Update models in other apps to use these encrypted fields for sensitive database columns.

## 4. Conditional Privacy Feature (On/Off Switch)

To provide flexibility and maintain backward compatibility, the Privacy Engine can be conditionally enabled or disabled via an environment variable. This allows the application to run in a non-privacy-enforced mode without significant code changes.

### Design & Implementation:

1.  **Central Configuration (`incometax_project/settings.py`)**
    *   A new Django setting, `PRIVACY_ENGINE_ENABLED`, controls the feature.
    *   It reads its value from an environment variable (e.g., `PRIVACY_ENGINE_ENABLED=false`) and defaults to `True` if the variable is not set.
    *   **Impact:** This single setting acts as the master switch for the entire privacy mechanism.

2.  **Conditional Storage Behavior (`privacy_engine/storage.py`)**
    *   The `EncryptedStorage` class is modified to check `settings.PRIVACY_ENGINE_ENABLED` in its core methods (`_save`, `_open`, `url`).
    *   **If Enabled (`PRIVACY_ENGINE_ENABLED = True`):** It performs encryption on save and decryption on read, as originally designed. Direct URL access remains disabled.
    *   **If Disabled (`PRIVACY_ENGINE_ENABLED = False`):** It acts as a transparent pass-through. Files are saved and read in plaintext, and the `url` method returns the direct URL to the file, behaving like a standard Django `FileField`.
    *   **Impact:** This centralizes the conditional encryption/decryption logic at the storage layer, making it transparent to the rest of the application.

3.  **Conditional Key Management (`privacy_engine/strategies.py`)**
    *   The `ThreadLocalKeyManager` is modified to check `settings.PRIVACY_ENGINE_ENABLED`.
    *   **If Enabled:** It derives and manages session-specific encryption keys as designed.
    *   **If Disabled:** Its `key_context` becomes a no-op (it yields without setting a key), and `get_key` returns a dummy key or `None` to prevent errors in code that might still call it.
    *   **Impact:** Prevents errors and unnecessary key management operations when privacy is not enforced.

4.  **Model Definition (`documents/models.py`)**
    *   The `Document` model's `file` field is configured to explicitly use `EncryptedStorage` (`file = models.FileField(..., storage=EncryptedStorage())`).
    *   The `ProtectedFile` model (in `privacy_engine/models.py`) is no longer directly used by the `Document` model for file storage in this new design. Its purpose as a generic secure file storage remains, but it's not part of the core document upload flow.
    *   **Impact:** The `Document` model's API remains consistent, but its underlying file storage behavior (encrypted or not) is now dynamically controlled by `EncryptedStorage`.

5.  **Views and Tasks (`api/views/session_views.py`, `api/tasks.py`)**
    *   The `upload_document` view in `api/views/session_views.py` is reverted to directly create `Document` objects and save files to `document.file`.
    *   It conditionally wraps the file saving operation in `key_manager.key_context` only if `settings.PRIVACY_ENGINE_ENABLED` is `True`.
    *   Celery tasks will continue to fetch `Document` objects and access `document.file.read()`. The `EncryptedStorage` will automatically handle decryption if privacy is enabled.
    *   **Impact:** These components remain largely unaware of the privacy setting, interacting with `Document.file` as usual. The conditional logic is handled by the lower-level `EncryptedStorage` and `key_manager` components.

### Backward Compatibility & Maintainability:

This design ensures strong backward compatibility because the public API for interacting with `Document` objects and their files remains consistent. The privacy enforcement becomes a transparent layer at the storage level, controlled by a single configuration switch. This adheres to DRY principles by centralizing conditional logic and promotes maintainability by separating concerns.