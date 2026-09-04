from django.urls import path
from apps.ai.views import (
    AIAssistantAskView,
    AIAssistantHealthView,
    AIAnalyzeImageView,
    AIStructureNoteView,
    AITriageView,
)

urlpatterns = [
    path('ask/', AIAssistantAskView.as_view(), name='ai-ask'),
    path('analyze-image/', AIAnalyzeImageView.as_view(), name='ai-analyze-image'),
    path('structure-note/', AIStructureNoteView.as_view(), name='ai-structure-note'),
    path('triage/', AITriageView.as_view(), name='ai-triage'),
    path('health/', AIAssistantHealthView.as_view(), name='ai-health'),
]
