"""
Views for the Appointments app.
Full CRUD + calendar + availability + statistics.
"""
from datetime import timedelta, date
from django.utils import timezone
from django.db.models import Q, Count
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.appointments.models import Appointment, AppointmentSlot
from apps.appointments.serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentCompleteSerializer,
    AppointmentCancelSerializer,
    CalendarEventSerializer,
    AppointmentSlotSerializer,
)
from apps.audit.utils import log_security_event


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for appointments.
    Doctors can manage their own appointments.
    Admins can manage all appointments.
    Patients can view their own appointments.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'appointment_type', 'priority', 'doctor', 'patient', 'is_virtual']
    search_fields = ['title', 'notes', 'patient__full_name', 'doctor__full_name']
    ordering_fields = ['scheduled_at', 'created_at', 'status', 'priority']
    ordering = ['scheduled_at']

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related(
            'patient', 'doctor', 'channel', 'basin', 'created_by', 'cancelled_by'
        )

        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return qs.all()
        elif user.role == 'DOCTOR':
            return qs.filter(Q(doctor=user) | Q(created_by=user))
        elif user.role == 'PATIENT':
            return qs.filter(patient__user=user)
        elif user.role in ['NURSE', 'LAB_TECH', 'PHARMACIST']:
            return qs.filter(
                Q(doctor=user) | Q(channel__memberships__user=user)
            ).distinct()
        return qs.filter(doctor=user)

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AppointmentCreateSerializer
        return AppointmentSerializer

    def perform_create(self, serializer):
        appt = serializer.save(created_by=self.request.user)
        log_security_event(
            user=self.request.user,
            event_type='APPOINTMENT_CREATED',
            request=self.request,
            details={'appointment_id': str(appt.id), 'patient': str(appt.patient_id)},
        )

    def perform_destroy(self, instance):
        log_security_event(
            user=self.request.user,
            event_type='APPOINTMENT_DELETED',
            request=self.request,
            details={'appointment_id': str(instance.id)},
        )
        instance.delete()

    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        """Return appointments in calendar-event format for a date range."""
        start_str = request.query_params.get('start')
        end_str = request.query_params.get('end')

        try:
            from django.utils.dateparse import parse_datetime, parse_date
            from datetime import datetime as dt, time as dt_time

            if start_str:
                dt_val = parse_datetime(start_str)
                if dt_val is None:
                    d_val = parse_date(start_str)
                    if d_val:
                        dt_val = timezone.make_aware(dt.combine(d_val, dt_time.min))
                if dt_val and timezone.is_naive(dt_val):
                    dt_val = timezone.make_aware(dt_val)
                start = dt_val or timezone.now().replace(day=1, hour=0, minute=0, second=0)
            else:
                start = timezone.now().replace(day=1, hour=0, minute=0, second=0)

            if end_str:
                dt_val = parse_datetime(end_str)
                if dt_val is None:
                    d_val = parse_date(end_str)
                    if d_val:
                        dt_val = timezone.make_aware(dt.combine(d_val, dt_time.max))
                if dt_val and timezone.is_naive(dt_val):
                    dt_val = timezone.make_aware(dt_val)
                end = dt_val or (start + timedelta(days=30))
            else:
                end = start + timedelta(days=30)
        except Exception:
            return Response({'error': 'تنسيق التاريخ غير صحيح'}, status=400)

        qs = self.get_queryset().filter(
            scheduled_at__gte=start,
            scheduled_at__lte=end,
        ).exclude(status=Appointment.Status.CANCELLED)

        serializer = CalendarEventSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        """Appointments scheduled for today."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        qs = self.get_queryset().filter(
            scheduled_at__gte=today_start,
            scheduled_at__lt=today_end,
        ).exclude(status=Appointment.Status.CANCELLED)
        serializer = AppointmentSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': qs.count()})

    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """Next 7 days of upcoming appointments."""
        now = timezone.now()
        qs = self.get_queryset().filter(
            scheduled_at__gte=now,
            scheduled_at__lte=now + timedelta(days=7),
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
        )
        serializer = AppointmentSerializer(qs[:20], many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': qs.count()})

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Confirm a scheduled appointment."""
        appt = self.get_object()
        if appt.status != Appointment.Status.SCHEDULED:
            return Response({'detail': 'يمكن تأكيد المواعيد المجدولة فقط.'}, status=400)
        appt.status = Appointment.Status.CONFIRMED
        appt.save(update_fields=['status'])
        log_security_event(
            user=request.user, event_type='APPOINTMENT_CONFIRMED',
            request=request, details={'appointment_id': str(appt.id)},
        )
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """Mark appointment as in progress."""
        appt = self.get_object()
        if appt.status not in [Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED]:
            return Response({'detail': 'الموعد في حالة غير صالحة.'}, status=400)
        appt.status = Appointment.Status.IN_PROGRESS
        appt.save(update_fields=['status'])
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Complete an appointment with optional summary."""
        appt = self.get_object()
        serializer = AppointmentCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        appt.status = Appointment.Status.COMPLETED
        appt.summary = serializer.validated_data.get('summary', '')
        appt.follow_up_needed = serializer.validated_data.get('follow_up_needed', False)
        appt.follow_up_date = serializer.validated_data.get('follow_up_date')
        appt.save(update_fields=['status', 'summary', 'follow_up_needed', 'follow_up_date'])

        log_security_event(
            user=request.user, event_type='APPOINTMENT_COMPLETED',
            request=request, details={'appointment_id': str(appt.id)},
        )
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appt = self.get_object()
        if appt.status in [Appointment.Status.COMPLETED, Appointment.Status.CANCELLED]:
            return Response({'detail': 'لا يمكن إلغاء موعد مكتمل أو ملغى.'}, status=400)

        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appt.cancel(cancelled_by=request.user, reason=serializer.validated_data.get('reason', ''))

        log_security_event(
            user=request.user, event_type='APPOINTMENT_CANCELLED',
            request=request, details={'appointment_id': str(appt.id)},
        )
        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, pk=None):
        """Mark patient as no-show."""
        appt = self.get_object()
        appt.status = Appointment.Status.NO_SHOW
        appt.save(update_fields=['status'])
        return Response(AppointmentSerializer(appt).data)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Appointment statistics."""
        qs = self.get_queryset()
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0)

        by_status = dict(qs.values('status').annotate(c=Count('id')).values_list('status', 'c'))
        by_type = dict(qs.values('appointment_type').annotate(c=Count('id')).values_list('appointment_type', 'c'))

        return Response({
            'total': qs.count(),
            'today': qs.filter(scheduled_at__date=now.date()).count(),
            'this_month': qs.filter(scheduled_at__gte=this_month_start).count(),
            'upcoming_7days': qs.filter(
                scheduled_at__gte=now,
                scheduled_at__lte=now + timedelta(days=7),
                status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
            ).count(),
            'by_status': by_status,
            'by_type': by_type,
            'completion_rate': round(
                by_status.get('COMPLETED', 0) / max(qs.count(), 1) * 100, 1
            ),
            'no_show_rate': round(
                by_status.get('NO_SHOW', 0) / max(qs.count(), 1) * 100, 1
            ),
        })

    @action(detail=False, methods=['get'], url_path='doctor-availability')
    def doctor_availability(self, request):
        """Check doctor availability for a specific date."""
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')

        if not doctor_id or not date_str:
            return Response({'error': 'doctor_id و date مطلوبان'}, status=400)

        try:
            from django.utils.dateparse import parse_date
            target_date = parse_date(date_str)
            day_of_week = target_date.weekday()  # 0=Monday
            # Convert to Sunday=0 system
            day_of_week = (day_of_week + 1) % 7
        except (ValueError, TypeError):
            return Response({'error': 'تنسيق التاريخ غير صحيح'}, status=400)

        # Get working slots
        slots = AppointmentSlot.objects.filter(
            doctor_id=doctor_id,
            day_of_week=day_of_week,
            is_active=True,
        )

        # Get booked appointments
        booked = Appointment.objects.filter(
            doctor_id=doctor_id,
            scheduled_at__date=target_date,
            status__in=[Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED],
        ).values_list('scheduled_at', 'duration_minutes')

        slot_data = AppointmentSlotSerializer(slots, many=True).data
        booked_data = [
            {
                'start': str(b[0]),
                'end': str(b[0] + timedelta(minutes=b[1])),
            }
            for b in booked
        ]

        return Response({
            'date': date_str,
            'day_of_week': day_of_week,
            'available_slots': slot_data,
            'booked_times': booked_data,
        })


class AppointmentSlotViewSet(viewsets.ModelViewSet):
    """Manage doctor availability slots."""
    serializer_class = AppointmentSlotSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['doctor', 'day_of_week', 'is_active']

    def get_queryset(self):
        user = self.request.user
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return AppointmentSlot.objects.select_related('doctor').all()
        return AppointmentSlot.objects.select_related('doctor').filter(doctor=user)

from rest_framework.views import APIView
import google.generativeai as genai
from django.conf import settings
import json

class AIAssistantView(APIView):
    """
    Clinical Decision Support System (CDSS).
    Simulates AI analysis of symptoms and returns suggested diagnoses.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get('question', '')
        
        # In a real app, this would connect to an LLM (like OpenAI/Gemini)
        if not question:
            return Response({"error": "No question provided"}, status=400)
            
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key:
            return Response({
                "answer": "مفتاح API الخاص بـ Gemini غير متوفر. الرجاء إضافته في إعدادات النظام.",
                "suggestions": ["تواصل مع الإدارة لتكوين الذكاء الاصطناعي"]
            })
            
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""أنت مساعد طبي ذكي (CDSS) تابع لنظام SecureMed.
مهمتك هي مساعدة الأطباء في تحليل الأعراض واقتراح تشخيصات مبدئية، وتنبيههم لأي تداخلات دوائية محتملة.
الرجاء الرد باللغة العربية بأسلوب احترافي طبي. لا تقم بوصف أدوية نهائية، بل أعطِ توصيات فقط.

سؤال الطبيب أو المريض: {question}

في النهاية، قدم بالضبط 3 اقتراحات لأسئلة متابعة أو فحوصات (مثل "طلب فحص دم") في صيغة JSON array فقط.
افصل هذا الـ JSON عن نص الإجابة بخط فاصل `---SUGGESTIONS---`.
"""
            response = model.generate_content(prompt)
            text = response.text
            
            parts = text.split('---SUGGESTIONS---')
            answer = parts[0].strip()
            
            suggestions = ["استشارة طبيب مختص", "طلب تحاليل عامة", "متابعة العلامات الحيوية"]
            if len(parts) > 1:
                try:
                    raw_json = parts[1].strip().strip('`').replace('json\n', '')
                    sugs = json.loads(raw_json)
                    if isinstance(sugs, list) and len(sugs) > 0:
                        suggestions = sugs[:3]
                except:
                    pass
                    
            return Response({
                "answer": answer,
                "suggestions": suggestions
            })
            
        except Exception as e:
            return Response({"error": f"AI Service Error: {str(e)}"}, status=500)
