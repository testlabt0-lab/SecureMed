"""
Secure server-side proxy for the AI microservice.

Now natively implemented using google.generativeai (Gemini) directly in Django.
No Node.js microservice required.
"""
import json as _json
import base64
from io import BytesIO

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_security_event

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from .utils import anonymize_patient_data

MAX_QUESTION_LEN = 2000
MAX_HISTORY_MESSAGES = 10
MAX_CONTEXT_CHARS = 500_000

def get_gemini_model(model_name='gemini-3.6-flash'):
    """Initialize and return a Gemini model if the API key is configured."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


class AIAssistantAskView(APIView):
    """POST /ai/ask — AI Chat Assistant for doctors."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.basins.utils import ensure_module_enabled
        ensure_module_enabled(request.user, 'ai_assistant')

        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response({'detail': 'السؤال مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        if len(question) > MAX_QUESTION_LEN:
            return Response({'detail': f'السؤال طويل جداً — الحد الأقصى {MAX_QUESTION_LEN} حرف'}, status=status.HTTP_400_BAD_REQUEST)

        history = request.data.get('history') or []
        context = request.data.get('context')

        log_security_event(
            user=request.user,
            event_type='AI_ASSISTANT_QUERY',
            request=request,
            details={'question_length': len(question), 'history_len': len(history)}
        )

        model = get_gemini_model()
        if not model:
            return Response({
                "answer": "مفتاح API الخاص بـ Gemini غير متوفر. الرجاء إضافة GEMINI_API_KEY في إعدادات النظام.",
                "suggestions": ["تواصل مع الدعم الفني لإعداد الذكاء الاصطناعي"]
            }, status=status.HTTP_200_OK)

        try:
            prompt = f"أنت مساعد طبي ذكي (CDSS) في نظام SecureMed. أجب باللغة العربية.\n"
            if context:
                safe_context = anonymize_patient_data(context)
                prompt += f"\nسياق المريض:\n{_json.dumps(safe_context, ensure_ascii=False)[:MAX_CONTEXT_CHARS]}\n"
            
            prompt += f"\nتاريخ المحادثة:\n"
            for h in history[-MAX_HISTORY_MESSAGES:]:
                prompt += f"{h.get('role', 'user')}: {h.get('content', '')}\n"
            
            prompt += f"\nالسؤال الحالي:\n{question}\n"
            prompt += "\nفي النهاية، قدم بالضبط 3 اقتراحات لأسئلة متابعة في صيغة JSON array فقط وافصل هذا الـ JSON بخط فاصل `---SUGGESTIONS---`."

            response = model.generate_content(prompt)
            text = response.text

            parts = text.split('---SUGGESTIONS---')
            answer = parts[0].strip()
            
            suggestions = ["استشارة طبيب مختص", "طلب تحاليل عامة", "مراجعة العلامات الحيوية"]
            if len(parts) > 1:
                try:
                    raw_json = parts[1].strip().strip('`').replace('json\n', '')
                    sugs = _json.loads(raw_json)
                    if isinstance(sugs, list) and len(sugs) > 0:
                        suggestions = sugs[:3]
                except:
                    pass

            return Response({
                "answer": answer,
                "suggestions": suggestions
            }, status=status.HTTP_200_OK)
        except Exception as e:
            log_security_event(user=request.user, event_type='AI_ASSISTANT_FAILED', request=request, details={'error': str(e)[:200]})
            return Response({'detail': f'خطأ في الذكاء الاصطناعي: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIAnalyzeImageView(APIView):
    """POST /ai/analyze-image — Analyzes medical images (X-ray, MRI, etc)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image_base64 = request.data.get('imageBase64', '')
        prompt = request.data.get('prompt', 'قم بتحليل هذه الصورة الطبية وقدم ملاحظاتك الأولية باللغة العربية.')

        if not image_base64:
            return Response({'detail': 'الصورة مطلوبة'}, status=status.HTTP_400_BAD_REQUEST)

        # Remove data URI scheme if present (e.g. data:image/jpeg;base64,...)
        if ',' in image_base64:
            image_base64 = image_base64.split(',')[1]

        model = get_gemini_model()
        if not model:
            return Response({
                "analysis": "عذراً، ميزة تحليل الصور تتطلب تكوين مفتاح GEMINI_API_KEY."
            }, status=status.HTTP_200_OK)

        try:
            image_data = base64.b64decode(image_base64)
            image_parts = [{"mime_type": "image/jpeg", "data": image_data}]

            response = model.generate_content([prompt, image_parts[0]])
            return Response({"analysis": response.text}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': f'فشل تحليل الصورة: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIStructureNoteView(APIView):
    """POST /ai/structure-note — Structures raw clinical text into SOAP format."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = request.data.get('text', '')
        if not text:
            return Response({'detail': 'النص مطلوب'}, status=status.HTTP_400_BAD_REQUEST)

        model = get_gemini_model()
        if not model:
            return Response({"structured": text + "\n\n(تعذر التنظيم لعدم وجود مفتاح API)"}, status=status.HTTP_200_OK)

        try:
            prompt = f"قم بتنظيم الملاحظات الطبية التالية إلى تنسيق SOAP (Subjective, Objective, Assessment, Plan) باللغة العربية وبشكل احترافي:\n\n{text}"
            response = model.generate_content(prompt)
            return Response({"structured": response.text}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AITriageView(APIView):
    """POST /ai/triage — Triages patient data based on symptoms and vitals."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patient = request.data.get('patient', {})
        symptoms = request.data.get('symptoms', '')
        vitals = request.data.get('vitals', {})
        lab_results = request.data.get('lab_results', {})

        model = get_gemini_model()
        if not model:
            return Response({
                "level": 3,
                "reasoning": "التقييم الآلي معطل (مفتاح API مفقود).",
                "recommendations": ["قم بالتقييم يدوياً"]
            }, status=status.HTTP_200_OK)

        try:
            safe_patient = anonymize_patient_data(patient)
            safe_symptoms = anonymize_patient_data(symptoms)
            safe_vitals = anonymize_patient_data(vitals)
            safe_lab = anonymize_patient_data(lab_results)
            
            prompt = f"""
قم بتقييم حالة هذا المريض وتحديد مستوى الخطورة (Triage Level) من 1 إلى 5 حيث 1 هو الأشد خطورة (إنعاش) و 5 غير طارئ.
المريض: {_json.dumps(safe_patient, ensure_ascii=False)}
الأعراض: {safe_symptoms}
العلامات الحيوية: {_json.dumps(safe_vitals, ensure_ascii=False)}
التحاليل: {_json.dumps(safe_lab, ensure_ascii=False)}

يجب أن ترد بصيغة JSON فقط بهذا الشكل:
{{
  "level": 2,
  "reasoning": "شرح سبب التقييم باللغة العربية",
  "recommendations": ["توصية 1", "توصية 2"]
}}
"""
            response = model.generate_content(prompt)
            raw_json = response.text.strip().strip('`').replace('json\n', '')
            result = _json.loads(raw_json)
            
            return Response({
                "level": result.get("level", 3),
                "reasoning": result.get("reasoning", ""),
                "recommendations": result.get("recommendations", [])
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': f'فشل التقييم: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIAssistantHealthView(APIView):
    """GET /ai/health — Lightweight reachability probe."""
    permission_classes = [AllowAny]

    def get(self, request):
        # We no longer proxy, so the service is always available if Django is up.
        return Response({'status': 'available', 'service': 'SecureMed AI Assistant'}, status=status.HTTP_200_OK)
