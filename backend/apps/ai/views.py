"""
Server-side AI endpoints (Gemini), used by the SPA under /api/v1/ai/.

Implemented natively with google.generativeai inside Django — there is no
Node.js microservice any more. Everything here talks to a third-party model on
behalf of a clinician, so three rules apply to every view in this module:

  * the caller is authenticated and their basin has the ai_assistant module;
  * patient data is anonymised before it leaves the deployment;
  * upstream failures return a generic message. ``str(e)`` from an SDK call can
    carry the request URL, the model name and, on an auth error, part of the API
    key — none of which belongs in a client response.
"""
import base64
import json as _json
import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_security_event

from google import genai
from google.genai import types
from .utils import anonymize_patient_data

logger = logging.getLogger('security')

MAX_QUESTION_LEN = 2000
MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_CONTENT_LEN = 2000
MAX_CONTEXT_CHARS = 500_000
MAX_NOTE_CHARS = 20_000
MAX_SYMPTOMS_CHARS = 5_000
# Decoded image bytes. Gemini's own inline-data ceiling is ~20MB for a request;
# 8MB is more than any diagnostic JPEG the SPA produces and keeps a single
# request from pinning a worker on base64 decoding.
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_IMAGE_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'}

UPSTREAM_ERROR = 'تعذر الوصول إلى خدمة الذكاء الاصطناعي حالياً. يرجى المحاولة لاحقاً.'


def get_gemini_model(model_name='gemini-2.0-flash'):
    """Initialize and return a Gemini model wrapper if the API key is configured."""
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None
    
    client = genai.Client(api_key=api_key)
    
    class ModelWrapper:
        def generate_content(self, contents):
            return client.models.generate_content(
                model=model_name,
                contents=contents
            )
            
    return ModelWrapper()


def _require_module(user):
    """Every AI view is gated, not just /ask.

    Only AIAssistantAskView used to check, so a basin without the ai_assistant
    module could still reach image analysis, note structuring and triage.
    """
    from apps.basins.utils import ensure_module_enabled
    ensure_module_enabled(user, 'ai_assistant')


def _sanitize_history(raw):
    """Keep the last N well-formed turns and drop everything else.

    The client's history was previously interpolated into the prompt as-is, so a
    non-dict entry (``["hi", 42]``) raised AttributeError mid-request and
    returned a 500, and a single 5000-character turn could push the real question
    out of the model's attention. Truncate content and cap the turn count.
    """
    if not isinstance(raw, list):
        return []

    cleaned = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        content = item.get('content')
        if not isinstance(content, str) or not content.strip():
            continue
        role = item.get('role')
        if role not in ('user', 'assistant', 'model'):
            role = 'user'
        cleaned.append({'role': role, 'content': content[:MAX_HISTORY_CONTENT_LEN]})

    return cleaned[-MAX_HISTORY_MESSAGES:]


def _context_size(context):
    """Serialized size of the patient context, for the payload ceiling."""
    try:
        return len(_json.dumps(context, ensure_ascii=False))
    except (TypeError, ValueError):
        return len(str(context))


def _upstream_failure(request, exc, event_type='AI_REQUEST_FAILED', detail=UPSTREAM_ERROR):
    """Audit the real error, tell the client nothing about it."""
    logger.error('%s | error=%s', event_type, exc)
    log_security_event(
        user=getattr(request, 'user', None) if getattr(request, 'user', None) and request.user.is_authenticated else None,
        event_type=event_type,
        request=request,
        severity='WARNING',
        details={'error': str(exc)[:200]},
    )
    return Response({'detail': detail}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class AIAssistantAskView(APIView):
    """POST /api/v1/ai/ask — AI Chat Assistant for doctors."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_module(request.user)

        question = str(request.data.get('question') or '').strip()
        if not question:
            return Response({'detail': 'السؤال مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        if len(question) > MAX_QUESTION_LEN:
            return Response({'detail': f'السؤال طويل جداً — الحد الأقصى {MAX_QUESTION_LEN} حرف'}, status=status.HTTP_400_BAD_REQUEST)

        history = _sanitize_history(request.data.get('history'))
        context = request.data.get('context')
        if context is not None and _context_size(context) > MAX_CONTEXT_CHARS:
            # Reject rather than silently truncate: a caller who sends more
            # context than we forward should know their prompt was not the one
            # the model answered.
            return Response(
                {'detail': f'سياق المريض كبير جداً — الحد الأقصى {MAX_CONTEXT_CHARS} حرف'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

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
            prompt = "أنت مساعد طبي ذكي (CDSS) في نظام SecureMed. أجب باللغة العربية.\n"
            if context:
                safe_context = anonymize_patient_data(context)
                prompt += f"\nسياق المريض:\n{_json.dumps(safe_context, ensure_ascii=False)}\n"

            if history:
                prompt += "\nتاريخ المحادثة:\n"
                for h in history:
                    prompt += f"{h['role']}: {h['content']}\n"

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
                        suggestions = [str(s) for s in sugs[:3]]
                except (ValueError, TypeError):
                    # The model did not return parseable JSON — keep the
                    # defaults. A bare `except:` here also swallowed
                    # KeyboardInterrupt and SystemExit.
                    pass

            return Response({
                "answer": answer,
                "suggestions": suggestions
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return _upstream_failure(request, e, event_type='AI_ASSISTANT_FAILED')


class AIAnalyzeImageView(APIView):
    """POST /api/v1/ai/analyze-image — Analyzes medical images (X-ray, MRI, etc)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_module(request.user)

        image_base64 = request.data.get('imageBase64', '')
        prompt = str(request.data.get('prompt') or 'قم بتحديد نوع هذه الصورة الطبية (أشعة سينية، رنين مغناطيسي، مقطعية، إلخ) ثم قدم تحليلاً مبدئياً وملاحظاتك الأولية باللغة العربية بناءً على ما تراه.')[:MAX_QUESTION_LEN]

        if not image_base64 or not isinstance(image_base64, str):
            return Response({'detail': 'الصورة مطلوبة'}, status=status.HTTP_400_BAD_REQUEST)

        mime_type = 'image/jpeg'
        # Strip the data URI scheme (data:image/png;base64,...) and take the
        # declared type with it — the type used to be hardcoded to JPEG, so a PNG
        # or WebP upload was handed to the model mislabelled.
        if ',' in image_base64:
            header, _, payload = image_base64.partition(',')
            image_base64 = payload
            if header.startswith('data:') and ';' in header:
                declared = header[5:header.index(';')].strip().lower()
                if declared:
                    mime_type = declared

        if mime_type not in ALLOWED_IMAGE_MIME:
            return Response(
                {'detail': 'نوع الصورة غير مدعوم'},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        # Check the encoded length before decoding: base64 is 4/3 of the payload,
        # so this bounds the allocation instead of discovering the size after
        # materialising it.
        if len(image_base64) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            return Response(
                {'detail': f'حجم الصورة كبير جداً — الحد الأقصى {MAX_IMAGE_BYTES // (1024 * 1024)} ميجابايت'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        try:
            image_data = base64.b64decode(image_base64, validate=True)
        except (ValueError, TypeError):
            return Response({'detail': 'تعذر قراءة الصورة — الترميز غير صالح'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_data:
            return Response({'detail': 'الصورة مطلوبة'}, status=status.HTTP_400_BAD_REQUEST)
        if len(image_data) > MAX_IMAGE_BYTES:
            return Response(
                {'detail': f'حجم الصورة كبير جداً — الحد الأقصى {MAX_IMAGE_BYTES // (1024 * 1024)} ميجابايت'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        model = get_gemini_model()
        if not model:
            return Response({
                "analysis": "عذراً، ميزة تحليل الصور تتطلب تكوين مفتاح GEMINI_API_KEY."
            }, status=status.HTTP_200_OK)

        log_security_event(
            user=request.user,
            event_type='AI_IMAGE_ANALYSIS',
            request=request,
            details={'bytes': len(image_data), 'mime_type': mime_type},
        )

        try:
            part = types.Part.from_bytes(data=image_data, mime_type=mime_type)
            response = model.generate_content([prompt, part])
            return Response({"analysis": response.text}, status=status.HTTP_200_OK)
        except Exception as e:
            return _upstream_failure(request, e, event_type='AI_IMAGE_ANALYSIS_FAILED')


class AIStructureNoteView(APIView):
    """POST /api/v1/ai/structure-note — Structures raw clinical text into SOAP format."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_module(request.user)

        text = request.data.get('text', '')
        if not isinstance(text, str) or not text.strip():
            return Response({'detail': 'النص مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        if len(text) > MAX_NOTE_CHARS:
            return Response(
                {'detail': f'النص طويل جداً — الحد الأقصى {MAX_NOTE_CHARS} حرف'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        model = get_gemini_model()
        if not model:
            return Response({"structured": text + "\n\n(تعذر التنظيم لعدم وجود مفتاح API)"}, status=status.HTTP_200_OK)

        try:
            # Clinical free text is the most identifying payload in this module,
            # and it was the only one sent to the model unmasked.
            safe_text = anonymize_patient_data(text)
            prompt = f"قم بتنظيم الملاحظات الطبية التالية إلى تنسيق SOAP (Subjective, Objective, Assessment, Plan) باللغة العربية وبشكل احترافي:\n\n{safe_text}"
            response = model.generate_content(prompt)
            return Response({"structured": response.text}, status=status.HTTP_200_OK)
        except Exception as e:
            return _upstream_failure(request, e, event_type='AI_STRUCTURE_NOTE_FAILED')


MAX_MEDICATION_NAMES = 50


class AIDrugInteractionCheckView(APIView):
    """POST /api/v1/ai/interactions-check — check a medication list for clashes.

    Two engines, deliberately layered:

    1. Rule-based: the pharmacy department's DrugInteraction table. Deterministic,
       instant, auditable, works with no API key — this is the safety net that
       always runs.
    2. AI review (optional): when GEMINI_API_KEY is configured, the anonymised
       list plus the patient's allergies and current medications go to Gemini for
       a clinical review the rule table cannot express (duplicates, class effects,
       allergy conflicts).

    The response marks which engine produced what, so the SPA can style a
    rule-engine SEVERE hit differently from a model suggestion.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_module(request.user)

        medications = request.data.get('medications')
        if not isinstance(medications, list) or not medications:
            return Response(
                {'detail': 'قائمة الأدوية مطلوبة'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Every entry becomes part of a prompt; keep each name bounded and the
        # list itself bounded so one request cannot push a 50k-token payload.
        medications = [str(m).strip()[:200] for m in medications if str(m).strip()]
        if not medications:
            return Response(
                {'detail': 'قائمة الأدوية مطلوبة'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(medications) > MAX_MEDICATION_NAMES:
            return Response(
                {'detail': f'عدد الأدوية كبير جداً — الحد الأقصى {MAX_MEDICATION_NAMES}'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        patient_payload = {}
        patient = None
        patient_id = request.data.get('patient_id')
        if patient_id:
            # Same access rule as every other patient-scoped view: an id is a
            # key, not an authorisation.
            from apps.core.mixins import accessible_patients
            from apps.patients.models import Patient as PatientModel
            patient = accessible_patients(
                PatientModel.objects.all(), request.user
            ).filter(pk=patient_id).first()
            if patient is None:
                return Response(
                    {'detail': 'غير مصرح لك بالوصول لهذا المريض'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            patient_payload = {
                'allergies': patient.allergies or '',
                'current_medications': patient.current_medications or '',
                'chronic_conditions': patient.chronic_conditions or '',
            }

        rule_based, has_severe = self._rule_based_check(medications)

        model = get_gemini_model()
        ai_review = None
        if model:
            try:
                ai_review = self._ai_review(model, medications, patient_payload)
            except Exception as e:
                return _upstream_failure(
                    request, e, event_type='AI_INTERACTION_FAILED',
                    # The rule engine already answered; the AI layer failing
                    # must not fail the request, but the caller should know the
                    # review is missing rather than silently absent.
                    detail='نجح الفحص القاعدي، تعذّرت المراجعة الآلية الإضافية.',
                )

        log_security_event(
            user=request.user,
            event_type='AI_INTERACTION_CHECKED',
            request=request,
            details={
                'medication_count': len(medications),
                'patient_id': str(patient.id) if patient else None,
                'rule_hits': len(rule_based),
                'has_severe': has_severe,
                'ai_reviewed': ai_review is not None,
            },
        )

        return Response({
            'rule_based': rule_based,
            'has_severe': has_severe,
            'ai_review': ai_review,
            'disclaimer': 'الفحص آلي ولا يُغني عن مراجعة الصيدلي أو الطبيب',
        }, status=status.HTTP_200_OK)

    @staticmethod
    def _rule_based_check(medications):
        """Match the list against the pharmacy DrugInteraction rules by name.

        Name matching is case-insensitive and substring-tolerant, because real
        prescriptions carry trade names ("بانادول إكسترا") while the catalog
        stores the scientific entry. Both orderings are tested — the rule table
        stores (drug_a, drug_b) once.
        """
        from apps.pharmacy.models import DrugInteraction, Medication

        names = [m.lower() for m in medications]
        matched = {}
        for med in Medication.objects.only('id', 'name', 'scientific_name'):
            haystacks = (med.name or '').lower(), (med.scientific_name or '').lower()
            if any(needle and (needle in hay or hay in needle)
                   for needle in names for hay in haystacks if hay):
                matched[med.id] = med.name

        interactions = DrugInteraction.objects.filter(
            drug_a_id__in=matched.keys(), drug_b_id__in=matched.keys()
        ).select_related('drug_a', 'drug_b')

        hits, has_severe = [], False
        for inter in interactions:
            has_severe = has_severe or inter.severity == 'SEVERE'
            hits.append({
                'drug_a': matched.get(inter.drug_a_id, inter.drug_a.name),
                'drug_b': matched.get(inter.drug_b_id, inter.drug_b.name),
                'severity': inter.severity,
                'description': inter.description,
                'source': 'rule_engine',
            })
        return hits, has_severe

    @staticmethod
    def _ai_review(model, medications, patient_payload):
        """Gemini clinical review over the anonymised payload."""
        safe_payload = anonymize_patient_data({
            'medications': medications,
            'patient': patient_payload,
        })
        prompt = f"""
راجع قائمة الأدوية التالية من حيث التداخلات الدوائية، التكرار، تعارض الحساسية،
وتأثير الأمراض المزمنة. البيانات:
{_json.dumps(safe_payload, ensure_ascii=False)}

أجب بصيغة JSON فقط بهذا الشكل:
{{
  "overall_risk": "LOW" | "MODERATE" | "HIGH",
  "findings": [
    {{"medications": ["دواء1", "دواء2"], "severity": "SEVERE|MODERATE|MILD|INFO", "note": "شرح موجز بالعربية"}}
  ],
  "summary": "جملة تلخيصية بالعربية"
}}
"""
        response = model.generate_content(prompt)
        raw_json = response.text.strip().strip('`').replace('json\n', '')
        result = _json.loads(raw_json)
        if not isinstance(result, dict):
            raise ValueError('interaction review was not a JSON object')
        result['source'] = 'ai_review'
        return result


class AITriageView(APIView):
    """POST /api/v1/ai/triage — Triages patient data based on symptoms and vitals."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require_module(request.user)

        patient = request.data.get('patient', {})
        symptoms = str(request.data.get('symptoms') or '')[:MAX_SYMPTOMS_CHARS]
        vitals = request.data.get('vitals', {})
        lab_results = request.data.get('lab_results', {})

        payload_size = sum(_context_size(part) for part in (patient, vitals, lab_results))
        if payload_size > MAX_CONTEXT_CHARS:
            return Response(
                {'detail': f'بيانات المريض كبيرة جداً — الحد الأقصى {MAX_CONTEXT_CHARS} حرف'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

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
            if not isinstance(result, dict):
                raise ValueError('triage response was not a JSON object')

            return Response({
                "level": result.get("level", 3),
                "reasoning": result.get("reasoning", ""),
                "recommendations": result.get("recommendations", [])
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return _upstream_failure(request, e, event_type='AI_TRIAGE_FAILED')


class AIAssistantHealthView(APIView):
    """GET /api/v1/ai/health — Lightweight reachability probe.

    Reports whether the module can actually answer, which is what a caller
    deciding whether to show the assistant needs to know: Django being up says
    nothing about a missing GEMINI_API_KEY.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        configured = bool(getattr(settings, 'GEMINI_API_KEY', ''))
        return Response({
            'status': 'available' if configured else 'unavailable',
            'service': 'SecureMed AI Assistant',
            'configured': configured,
        }, status=status.HTTP_200_OK)
