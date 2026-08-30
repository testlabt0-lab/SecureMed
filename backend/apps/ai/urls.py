"""
URLs for the AI assistant proxy (mounted at /ai/ — same paths the
frontend already calls; in dev Vite proxies them, in prod Django answers).
"""
from django.urls import path

from apps.ai.views import AIAssistantAskView, AIAssistantHealthView

urlpatterns = [
    path('ask/', AIAssistantAskView.as_view(), name='ai-ask'),
    path('health/', AIAssistantHealthView.as_view(), name='ai-health'),
]
