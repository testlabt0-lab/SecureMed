"""
App config for the AI assistant proxy.

The AI microservice (ai-service/, Node + GLM) is intentionally NOT exposed
to the internet. In production the frontend talks to Django (same origin)
and Django forwards assistant requests server-to-server — so every AI call
passes through JWT auth, the WAF, throttling and the audit trail.
"""
from django.apps import AppConfig


class AIConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai'
    verbose_name = 'AI Assistant (secure proxy)'
