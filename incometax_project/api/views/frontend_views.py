"""
Frontend Views for TaxSahaj Django Application
Handles serving the frontend HTML interface
"""

from django.shortcuts import render
from django.http import HttpResponse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def index(request):
    """Serve the multi-page TaxSahaj HTML interface"""
    try:
        # Use Django's template rendering to handle CSRF token
        return render(request, 'enhanced_taxsahaj.html')
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        return HttpResponse(f"Error loading page: {e}", status=500)

def tax_analysis_report(request):
    """Serve the improved tax analysis report page"""
    try:
        session_id = request.GET.get('session_id')
        # Serve the improved template with regime comparison focus
        return render(request, 'improved_tax_analysis_report.html', {'session_id': session_id})
    except Exception as e:
        logger.error(f"Error serving tax analysis report: {e}")
        return HttpResponse(f"Error loading report: {e}", status=500)


def adapt_html_for_django(html_content):
    """Adapt the Flask HTML template to work with Django API endpoints"""
    
    # Replace Flask API endpoints with Django REST API endpoints
    replacements = {
        # API endpoint updates for session-based workflow
        "'/api/analyze_documents'": "'/api/sessions/' + getCurrentSessionId() + '/analyze/'",
        "'/api/progress'": "'/api/progress/'",
        "'/api/download_report'": "'/api/download_report/'", 
        "'/api/health'": "'/api/health/'",
    }
    
    for old_endpoint, new_endpoint in replacements.items():
        html_content = html_content.replace(old_endpoint, new_endpoint)
    
    # Add session management JavaScript
    session_js = """
    <script>
    // Session Management for Django Backend
    let currentSessionId = null;
    
    function getCurrentSessionId() {
        if (!currentSessionId) {
            // Create new session if none exists
            createNewSession();
        }
        return currentSessionId;
    }
    
    function createNewSession() {
        fetch('/api/sessions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({'name': 'TaxSahaj Session'})
        })
        .then(response => response.json())
        .then(data => {
            currentSessionId = data.session_id;
            console.log('Created session:', currentSessionId);
        })
        .catch(error => {
            console.error('Error creating session:', error);
        });
    }
    
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initialize session on page load
    document.addEventListener('DOMContentLoaded', function() {
        createNewSession();
    });
    </script>
    """
    
    # Insert session JS before closing head tag
    html_content = html_content.replace('</head>', session_js + '\n</head>')
    
    return html_content