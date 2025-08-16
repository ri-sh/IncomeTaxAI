from django.contrib import admin
from .models import ProcessingSession, Document, AnalysisTask, AnalysisResult

@admin.register(ProcessingSession)
class ProcessingSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('id', 'created_at')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'session', 'status', 'uploaded_at')
    list_filter = ('status',)
    readonly_fields = ('id', 'uploaded_at')

@admin.register(AnalysisTask)
class AnalysisTaskAdmin(admin.ModelAdmin):
    list_display = ('session', 'celery_task_id', 'status', 'started_at', 'completed_at')
    list_filter = ('status',)
    readonly_fields = ('id', 'started_at', 'completed_at')

@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ('session', 'document', 'created_at')
    readonly_fields = ('id', 'created_at')