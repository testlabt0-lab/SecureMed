"""
Notifications views - real-time notification system.
"""
from rest_framework import viewsets, permissions, status, filters, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.utils import timezone

from apps.notifications.models import Notification, NotificationPreference, PushToken
from apps.notifications.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer
)
from apps.audit.utils import log_security_event


class NotificationFilter(django_filters.FilterSet):
    """Filter for notifications."""
    is_read = django_filters.BooleanFilter()
    notification_type = django_filters.CharFilter(field_name='notification_type')
    priority = django_filters.CharFilter(field_name='priority')

    class Meta:
        model = Notification
        fields = ['is_read', 'notification_type', 'priority']


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Manage user notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_class = NotificationFilter
    search_fields = ['title', 'message']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']

    def get_queryset(self):
        """Only return notifications for the current user."""
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications."""
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read."""
        Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({'detail': 'تم تعليم جميع الإشعارات كمقروءة'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a single notification as read."""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'detail': 'تم تعليم الإشعار كمقروء'})

    @action(detail=True, methods=['delete'])
    def dismiss(self, request, pk=None):
        """Delete a notification."""
        notification = self.get_object()
        notification.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def test_email(self, request):
        """
        POST /api/v1/notifications/test_email/
        Send a branded test email to the current user — verifies the email
        configuration end-to-end from the UI.
        """
        from utils.email_service import send_securemed_email

        user = request.user
        if not user.email:
            return Response({'detail': 'لا يوجد بريد إلكتروني محفوظ لحسابك'}, status=400)

        ok = send_securemed_email(
            to_email=user.email,
            subject='SecureMed — رسالة اختبار البريد الإلكتروني',
            title='اختبار إعدادات البريد الإلكتروني',
            body_html=(
                f'<p>مرحباً <b>{user.full_name}</b>،</p>'
                '<p>هذه رسالة اختبار تؤكد أن إعدادات البريد الإلكتروني في منصة '
                'SecureMed تعمل بشكل صحيح. عند وصول إشعارات مهمة (تنبيهات أمنية، '
                'تحديثات القنوات، سجلات طبية جديدة) ستصل بهذا الشكل مباشرة إلى بريدك.</p>'
            ),
            footer_note='أُرسلت هذه الرسالة بناءً على طلبك من صفحة مركز الإشعارات.',
        )
        log_security_event(
            user=user,
            event_type='TEST_EMAIL_SENT',
            request=request,
            details={'to': user.email, 'delivered': ok},
        )
        if ok:
            return Response({'detail': f'تم إرسال رسالة الاختبار إلى {user.email}'})
        return Response(
            {'detail': 'فشل إرسال البريد — راجع إعدادات SMTP في السجل'},
            status=502,
        )


class PushTokenRegisterView(generics.GenericAPIView):
    """POST /api/v1/notifications/push/register/ — register an FCM device token.

    The client (Android app, web push) calls this right after login and again
    whenever FCM rotates its token. Re-registering an existing token re-binds
    it to the current account and re-activates it, which covers a device that
    logged out and back in, or moved between accounts.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = str(request.data.get('token') or '').strip()
        platform = str(request.data.get('platform') or 'ANDROID').upper()
        if not token or len(token) > 4096:
            return Response(
                {'detail': 'رمز الإشعارات مطلوب'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if platform not in ('ANDROID', 'WEB', 'IOS'):
            platform = 'ANDROID'

        from django.conf import settings as dj_settings
        device_fingerprint = (
            request.META.get('HTTP_X_DEVICE_FINGERPRINT', '')
            or request.data.get('device_fingerprint') or ''
        )[:255]

        obj, _created = PushToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'platform': platform,
                'device_fingerprint': device_fingerprint,
                'is_active': True,
            },
        )
        log_security_event(
            user=request.user,
            event_type='SYSTEM_EVENT',
            request=request,
            details={'action': 'push_token_registered', 'platform': platform},
        )
        return Response({'detail': 'تم تسجيل الجهاز للإشعارات'}, status=200)

    def delete(self, request):
        """Unregister (e.g. on logout): deactivate, keep the row for history."""
        token = str(request.data.get('token') or '').strip()
        if token:
            PushToken.objects.filter(
                token=token, user=request.user
            ).update(is_active=False)
        return Response({'detail': 'تم إلغاء تسجيل الإشعارات لهذا الجهاز'})


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """GET/PUT/PATCH /api/v1/notifications/preferences/ — the caller's own row.

    Preferences are a singleton per user, so the URL carries no id: get_object()
    resolves the row from request.user and creates it on first read.

    This was a ModelViewSet on the router, which broke the endpoint twice over.
    NotificationViewSet is registered at prefix '' and its detail route
    ^(?P<pk>[^/.]+)/$ is generated before the 'preferences' prefix, so
    /notifications/preferences/ was swallowed by it with pk='preferences' — a
    non-UUID pk lookup raises django.core.exceptions.ValidationError, which DRF
    does not translate, so the caller got HTTP 500 rather than data. And even
    unshadowed, a router's list route maps only GET and POST, so the frontend's
    PATCH could not have returned anything but 405. urls.py now declares this
    path ahead of the router include.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        obj, _created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
