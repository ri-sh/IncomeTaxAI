from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet, get_progress, download_report, health_check
from .views.frontend_views import tax_analysis_report

router = DefaultRouter()
router.register(r'sessions', SessionViewSet)

urlpatterns = [
    # REST API endpoints
    path('', include(router.urls)),
    
    # Additional API endpoints
    path('progress/', get_progress, name='api_progress'),
    path('download_report/', download_report, name='api_download_report'),
    path('health/', health_check, name='api_health'),
    
    # Frontend pages
    path('tax_analysis_report/', tax_analysis_report, name='tax_analysis_report'),
]
