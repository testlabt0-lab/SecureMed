"""
Break-Glass Emergency Protocol API Views.
Enables clinicians to access patient medical records during life-critical emergencies with full auditing.
"""
import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from apps.security.models import BreakGlassAccess
from apps.patients.models import Patient
from apps.audit.utils import log_security_event
from apps.audit.models import AuditLog
from apps.core.net import get_client_ip
from apps.core.mixins import CLINICAL_BREAK_GLASS_ROLES, PATIENT_INDEX_ADMIN_ROLES
from apps.security.telegram_service import send_break_glass_alert

User = get_user_model()


class BreakGlassActivateView(APIView):
    """
    POST /api/v1/security/break-glass/activate/
    Activate Emergency Break-Glass access to a patient's record.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        role = getattr(user, 'role', None)

        if role not in CLINICAL_BREAK_GLASS_ROLES:
            return Response(
                {
                    "detail": "فقط الكوادر الطبية والسريرية مخولة بتفعيل بروتوكول كسر الزجاج للطوارئ.",
                    "code": "PERMISSION_DENIED"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response(
                {"detail": "معرّف المريض (patient_id) مطلوب.", "code": "MISSING_PATIENT_ID"},
                status=status.HTTP_400_BAD_REQUEST
            )

        patient = get_object_or_404(Patient, id=patient_id)

        reason = str(request.data.get('reason', '')).strip()
        if len(reason) < 20:
            return Response(
                {
                    "detail": "التبرير الطبي الإسعافي إجباري ويجب أن يحتوي على 20 حرفاً على الأقل لتوضيح الحالة الطارئة.",
                    "code": "INVALID_REASON"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        department = str(request.data.get('department', '')).strip()
        if not department:
            department = getattr(user, 'department', '') or 'قسم الطوارئ'

        now = timezone.now()

        # Check if user already has an active, valid break-glass access
        existing_access = BreakGlassAccess.objects.filter(
            user=user,
            patient=patient,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).first()

        if existing_access:
            return Response(
                {
                    "status": "already_active",
                    "message": "بروتوكول كسر الزجاج مفعل بالفعل لهذا المريض وهو قيد السريان.",
                    "break_glass": {
                        "id": str(existing_access.id),
                        "patient_id": str(patient.id),
                        "patient_name": patient.full_name,
                        "department": existing_access.department,
                        "reason": existing_access.reason,
                        "activated_at": existing_access.activated_at.isoformat(),
                        "expires_at": existing_access.expires_at.isoformat(),
                        "remaining_seconds": max(0, int((existing_access.expires_at - now).total_seconds())),
                    }
                },
                status=status.HTTP_200_OK
            )

        # Standard emergency access window: 4 hours
        expires_at = now + datetime.timedelta(hours=4)
        client_ip = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        device_fingerprint = request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')[:255]

        access = BreakGlassAccess.objects.create(
            user=user,
            patient=patient,
            reason=reason,
            department=department,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=user_agent,
            device_fingerprint=device_fingerprint
        )

        # 1. Log Critical Security Audit Event with HMAC chain integrity
        log_security_event(
            user=user,
            event_type=AuditLog.EventType.BREAK_GLASS_ACTIVATED,
            request=request,
            severity='CRITICAL',
            details={
                'break_glass_id': str(access.id),
                'patient_id': str(patient.id),
                'patient_name': patient.full_name,
                'doctor_name': getattr(user, 'full_name', '') or user.email,
                'doctor_role': role,
                'department': department,
                'reason': reason,
                'expires_at': expires_at.isoformat(),
            }
        )

        # 2. Dispatch Urgent Alert via Telegram Bot
        try:
            send_break_glass_alert(
                user=user,
                patient=patient,
                reason=reason,
                department=department,
                ip_address=client_ip,
                expires_at=expires_at
            )
        except Exception:
            pass

        # 3. Dispatch In-App Notifications to Hospital & System Administrators
        try:
            from apps.notifications.utils import send_notification
            from apps.notifications.models import Notification

            admins = User.objects.filter(
                role__in=['SUPER_ADMIN', 'HOSPITAL_ADMIN'],
                is_active=True
            ).exclude(id=user.id)[:15]

            alert_title = f"🚨 تفعيل وصول طوارئ كسر الزجاج: {patient.full_name}"
            alert_msg = (
                f"قام الطبيب {getattr(user, 'full_name', '') or user.email} بتفعيل وصول الطوارئ (Break-Glass) "
                f"للمريض {patient.full_name} في قسم {department}. التبرير: {reason}"
            )

            for admin in admins:
                send_notification(
                    recipient=admin,
                    notification_type=Notification.Type.SECURITY_ALERT,
                    priority='CRITICAL',
                    title=alert_title,
                    message=alert_msg,
                    sender=user,
                    related_object_type='break_glass',
                    related_object_id=str(access.id)
                )
        except Exception:
            pass

        return Response(
            {
                "status": "success",
                "message": "تم تفعيل بروتوكول كسر الزجاج للطوارئ بنجاح. تم تسجيل الحدث وإشعار الإدارة الأمنية.",
                "break_glass": {
                    "id": str(access.id),
                    "patient_id": str(patient.id),
                    "patient_name": patient.full_name,
                    "department": access.department,
                    "reason": access.reason,
                    "activated_at": access.activated_at.isoformat(),
                    "expires_at": access.expires_at.isoformat(),
                    "remaining_seconds": int((expires_at - now).total_seconds()),
                }
            },
            status=status.HTTP_201_CREATED
        )


class BreakGlassRevokeView(APIView):
    """
    POST /api/v1/security/break-glass/revoke/
    Conclude an emergency break-glass session once the emergency has passed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        break_glass_id = request.data.get('break_glass_id')
        patient_id = request.data.get('patient_id')

        query = {'status': BreakGlassAccess.Status.ACTIVE}
        if break_glass_id:
            query['id'] = break_glass_id
        elif patient_id:
            query['patient_id'] = patient_id
        else:
            return Response(
                {"detail": "يجب تمرير break_glass_id أو patient_id لإلغاء الوصول.", "code": "MISSING_PARAM"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if getattr(user, 'role', None) not in PATIENT_INDEX_ADMIN_ROLES:
            query['user'] = user

        access = BreakGlassAccess.objects.filter(**query).first()
        if not access:
            return Response(
                {"detail": "لم يتم العثور على جلسة وصول طوارئ نشطة مطابقة.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND
            )

        access.revoke(user=user)

        # Log revocation
        log_security_event(
            user=user,
            event_type=AuditLog.EventType.BREAK_GLASS_REVOKED,
            request=request,
            severity='INFO',
            details={
                'break_glass_id': str(access.id),
                'patient_id': str(access.patient_id),
                'practitioner_id': str(access.user_id),
                'revoked_by': str(user.id),
            }
        )

        return Response(
            {
                "status": "success",
                "message": "تم إنهاء جلسة الوصول الطارئ بنجاح وإعادة تطبيق الحماية العادية.",
            },
            status=status.HTTP_200_OK
        )


class BreakGlassStatusView(APIView):
    """
    GET /api/v1/security/break-glass/status/?patient_id=...
    Check if the current user has active break-glass access to a specific patient.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response(
                {"detail": "patient_id query param is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()
        access = BreakGlassAccess.objects.filter(
            user=request.user,
            patient_id=patient_id,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).first()

        if not access:
            can_break_glass = getattr(request.user, 'role', None) in CLINICAL_BREAK_GLASS_ROLES
            return Response({
                "has_active_break_glass": False,
                "can_break_glass": can_break_glass,
            })

        return Response({
            "has_active_break_glass": True,
            "can_break_glass": True,
            "break_glass": {
                "id": str(access.id),
                "patient_id": str(access.patient_id),
                "reason": access.reason,
                "department": access.department,
                "activated_at": access.activated_at.isoformat(),
                "expires_at": access.expires_at.isoformat(),
                "remaining_seconds": max(0, int((access.expires_at - now).total_seconds())),
            }
        })


class BreakGlassActiveListView(APIView):
    """
    GET /api/v1/security/break-glass/active/
    List all active break-glass events (user's own, or hospital-wide for admins).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        qs = BreakGlassAccess.objects.filter(
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).select_related('user', 'patient')

        if getattr(request.user, 'role', None) not in PATIENT_INDEX_ADMIN_ROLES:
            qs = qs.filter(user=request.user)

        results = []
        for bg in qs[:50]:
            results.append({
                "id": str(bg.id),
                "practitioner_id": str(bg.user_id),
                "practitioner_name": getattr(bg.user, 'full_name', '') or bg.user.email,
                "practitioner_role": getattr(bg.user, 'role', ''),
                "patient_id": str(bg.patient_id),
                "patient_name": bg.patient.full_name,
                "reason": bg.reason,
                "department": bg.department,
                "activated_at": bg.activated_at.isoformat(),
                "expires_at": bg.expires_at.isoformat(),
                "remaining_seconds": max(0, int((bg.expires_at - now).total_seconds())),
            })

        return Response({"count": len(results), "results": results})
