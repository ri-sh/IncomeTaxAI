"""
PII-aware logging utilities for the Income Tax AI system.
This module provides utilities to control logging of personally identifiable information (PII)
based on the LOG_PII environment variable.
"""

import logging
from django.conf import settings


def get_pii_safe_logger(name):
    """
    Get a logger with PII-aware logging capabilities.
    
    Args:
        name: The name of the logger (typically __name__)
        
    Returns:
        PIILogger: A logger wrapper that respects LOG_PII setting
    """
    return PIILogger(logging.getLogger(name))


class PIILogger:
    """
    A logger wrapper that provides PII-aware logging.
    When LOG_PII is False, it sanitizes or skips logging that might contain PII.
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.log_pii = getattr(settings, 'LOG_PII', False)
    
    def _sanitize_filename(self, filename):
        """
        Sanitize filename for logging when LOG_PII is disabled.
        Keep filename extension but anonymize the name.
        """
        if not filename:
            return "[no_filename]"
        
        if '.' in filename:
            parts = filename.rsplit('.', 1)
            return f"[document].{parts[1]}"
        return "[document]"
    
    def _should_log_pii(self):
        """Check if PII logging is enabled."""
        return self.log_pii
    
    def info_with_filename(self, message, filename=None, **kwargs):
        """
        Log info message with filename, sanitizing if needed.
        
        Args:
            message: Base message template (should use {filename} placeholder)
            filename: The filename to include
            **kwargs: Additional format parameters
        """
        if self._should_log_pii():
            # Log with actual filename
            format_dict = {'filename': filename or '[no_filename]', **kwargs}
            self.logger.info(message.format(**format_dict))
        else:
            # Log with sanitized filename
            sanitized_filename = self._sanitize_filename(filename)
            format_dict = {'filename': sanitized_filename, **kwargs}
            self.logger.info(message.format(**format_dict))
    
    def error_with_filename(self, message, filename=None, **kwargs):
        """
        Log error message with filename, sanitizing if needed.
        Errors are always logged but with sanitized filenames when LOG_PII is False.
        """
        if self._should_log_pii():
            # Log with actual filename
            format_dict = {'filename': filename or '[no_filename]', **kwargs}
            self.logger.error(message.format(**format_dict))
        else:
            # Log with sanitized filename
            sanitized_filename = self._sanitize_filename(filename)
            format_dict = {'filename': sanitized_filename, **kwargs}
            self.logger.error(message.format(**format_dict))
    
    def warning_with_filename(self, message, filename=None, **kwargs):
        """
        Log warning message with filename, sanitizing if needed.
        """
        if self._should_log_pii():
            # Log with actual filename
            format_dict = {'filename': filename or '[no_filename]', **kwargs}
            self.logger.warning(message.format(**format_dict))
        else:
            # Log with sanitized filename
            sanitized_filename = self._sanitize_filename(filename)
            format_dict = {'filename': sanitized_filename, **kwargs}
            self.logger.warning(message.format(**format_dict))
    
    def debug_with_pii(self, message, **kwargs):
        """
        Log debug message that may contain PII.
        Only logs if LOG_PII is True.
        """
        if self._should_log_pii():
            self.logger.debug(message.format(**kwargs))
        # Silently skip if PII logging is disabled
    
    # Delegate standard logging methods
    def info(self, message, *args, **kwargs):
        """Standard info logging (no PII sanitization)."""
        self.logger.info(message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        """Standard error logging (no PII sanitization)."""
        self.logger.error(message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        """Standard warning logging (no PII sanitization)."""
        self.logger.warning(message, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        """Standard debug logging (no PII sanitization)."""
        self.logger.debug(message, *args, **kwargs)


# Convenience function for quick document processing logging
def log_document_processing(logger, operation, filename, **details):
    """
    Log document processing operations with PII awareness.
    
    Args:
        logger: PIILogger instance
        operation: Operation being performed (e.g., "AI processing", "Completed")
        filename: Document filename
        **details: Additional details to log (e.g., document_type, task_id)
    """
    detail_str = ', '.join([f"{k}: {v}" for k, v in details.items()])
    if detail_str:
        message = f"{operation}: {{filename}} ({detail_str})"
    else:
        message = f"{operation}: {{filename}}"
    
    logger.info_with_filename(message, filename)


# Convenience function for errors
def log_document_error(logger, error_type, filename, error_details=None):
    """
    Log document processing errors with PII awareness.
    
    Args:
        logger: PIILogger instance
        error_type: Type of error (e.g., "AI processing error", "Timeout")
        filename: Document filename
        error_details: Additional error information
    """
    if error_details:
        message = f"{error_type} for {{filename}}: {error_details}"
    else:
        message = f"{error_type} for {{filename}}"
    
    logger.error_with_filename(message, filename)