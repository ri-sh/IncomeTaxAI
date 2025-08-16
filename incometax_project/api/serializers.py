from rest_framework import serializers
from documents.models import ProcessingSession, Document, AnalysisTask, AnalysisResult

class ProcessingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingSession
        fields = ['id', 'status', 'created_at']

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'filename', 'status', 'uploaded_at']

class AnalysisTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisTask
        fields = ['id', 'status', 'started_at', 'completed_at']

class AnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalysisResult
        fields = ['id', 'result_data', 'created_at']
