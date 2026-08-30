"""
Secure server-side proxy to the AI microservice.

Why a proxy?
  * The AI service never touches the internet — only Django calls it
    (server-to-server over the internal network / Docker network).
  * Every assistant request is authenticated (JWT), filtered by the WAF,
    rate-limited and audited before it reaches the model.
  * In production the React SPA is served from Django itself, so the
    frontend's same-origin `/ai/...` calls land here instead of the
    Vite dev proxy used in development.
"""
import json as _json
import urllib.request

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_security_event

MAX_QUESTION_LEN = 2000
MAX_HISTORY_MESSAGES = 10
MAX_CONTEXT_CHARS = 500_000  # ~0.5 MB of JSON context from the SPA


def _ai_url(path: str) -> str:
    base = getattr(settings, 'AI_SERVICE_URL', 'http://127.0.0.1:8100')
    return f"{base.rstrip('/')}{path}"


class AIAssistantAskView(APIView):
    """POST /ai/ask — proxy a question (with optional context/history) to the AI service."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Module activation by basin type (plan requirement)
        from apps.basins.utils import ensure_module_enabled
        ensure_module_enabled(request.user, 'ai_assistant')

        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response(
                {'detail': 'السؤال مطلوب'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(question) > MAX_QUESTION_LEN:
            return Response(
                {'detail': f'السؤال طويل جداً — الحد الأقصى {MAX_QUESTION_LEN} حرف'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        history = request.data.get('history') or []
        if not isinstance(history, list):
            return Response(
                {'detail': 'history يجب أن يكون قائمة'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        history = [
            {
                'role': 'assistant' if str(h.get('role')) == 'assistant' else 'user',
                'content': str(h.get('content'))[:MAX_QUESTION_LEN],
            }
            for h in history[-MAX_HISTORY_MESSAGES:]
            if isinstance(h, dict) and h.get('content')
        ]

        payload = {'question': question, 'history': history}

        context = request.data.get('context')
        if context is not None:
            try:
                context_json = _json.dumps(context, ensure_ascii=False)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'سياق غير صالح'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(context_json) > MAX_CONTEXT_CHARS:
                return Response(
                    {'detail': 'حجم السياق كبير جداً'},
                    status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                )
            payload['context'] = context

        try:
            req = urllib.request.Request(
                _ai_url('/ask'),
                data=_json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=85) as resp:
                ai_data = _json.loads(resp.read().decode('utf-8'))
        except Exception as e:  # service down / timeout / invalid payload
            log_security_event(
                user=request.user,
                event_type='AI_ASSISTANT_FAILED',
                request=request,
                details={'error': str(e)[:200]},
            )
            return Response(
                {'detail': 'خدمة المساعد الذكي غير متاحة حالياً — حاول لاحقاً'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        log_security_event(
            user=request.user,
            event_type='AI_ASSISTANT_QUERY',
            request=request,
            details={'question_length': len(question), 'history_len': len(history)},
        )
        return Response(ai_data, status=status.HTTP_200_OK)


class AIAssistantHealthView(APIView):
    """GET /ai/health — lightweight reachability probe (no data exposed)."""

    permission_classes = [AllowAny]

    def get(self, request):
        try:
            with urllib.request.urlopen(_ai_url('/health'), timeout=5) as resp:
                data = _json.loads(resp.read().decode('utf-8'))
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {'status': 'unavailable', 'service': 'SecureMed AI Assistant'},
                status=status.HTTP_200_OK,
            )
