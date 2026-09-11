"""API إدارة صلاحيات الأدوار — لوحة تحكم الإدارة.

تعمل فوق كتالوج apps.accounts.permissions: العرض يبني المصفوفة الكاملة
(أدوار × صلاحيات)، والتعديل يسجل تجاوزاً في RolePermission مع تدقيق
الحدث في سجل التدقيق.
"""
import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.models import RolePermission
from apps.accounts.permissions import (
    ALL_PERMISSION_CODES,
    default_allows,
    effective_allows,
    permission_category,
    permission_label,
    role_permission_matrix,
)
from apps.audit.utils import log_security_event

logger = logging.getLogger('security')


class RolePermissionViewSet(viewsets.ViewSet):
    """إدارة صلاحيات الأدوار — SUPER_ADMIN/HOSPITAL_ADMIN فقط."""

    def list(self, request):
        return Response(role_permission_matrix())

    @action(detail=False, methods=['post'], url_path='set')
    def set_permission(self, request):
        """تسجيل تجاوز: {role, permission, allowed}."""
        role = (request.data.get('role') or '').strip()
        permission = (request.data.get('permission') or '').strip()
        allowed = request.data.get('allowed')

        from apps.accounts.models import User
        if role not in {value for value, _ in User.Role.choices}:
            return Response({'detail': 'دور غير معروف'},
                            status=status.HTTP_400_BAD_REQUEST)
        if permission not in ALL_PERMISSION_CODES:
            return Response({'detail': 'صلاحية غير معروفة في الكتالوج'},
                            status=status.HTTP_400_BAD_REQUEST)
        if role == 'SUPER_ADMIN':
            return Response(
                {'detail': 'لا يمكن تقييد صلاحيات مدير النظام الأعلى'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(allowed, bool):
            return Response({'detail': 'allowed يجب أن يكون true/false'},
                            status=status.HTTP_400_BAD_REQUEST)

        previous = effective_allows(role, permission)
        obj, _created = RolePermission.objects.update_or_create(
            role=role, permission=permission,
            defaults={'allowed': allowed, 'updated_by': request.user},
        )
        log_security_event(
            user=request.user,
            event_type='ROLE_PERMISSION_CHANGED',
            request=request,
            details={
                'role': role,
                'permission': permission,
                'allowed': allowed,
                'previous_effective': previous,
                'label': permission_label(permission),
                'category': permission_category(permission),
            },
            severity='WARNING',
        )
        return Response({
            'detail': 'تم تحديث الصلاحية',
            'role': role, 'permission': permission, 'allowed': allowed,
            'previous_effective': previous,
        })

    @action(detail=False, methods=['post'], url_path='reset')
    def reset_permission(self, request):
        """حذف التجاوز والعودة إلى الافتراضي: {role, permission}."""
        role = (request.data.get('role') or '').strip()
        permission = (request.data.get('permission') or '').strip()
        if permission not in ALL_PERMISSION_CODES:
            return Response({'detail': 'صلاحية غير معروفة في الكتالوج'},
                            status=status.HTTP_400_BAD_REQUEST)
        deleted, _ = RolePermission.objects.filter(
            role=role, permission=permission,
        ).delete()
        if deleted:
            log_security_event(
                user=request.user,
                event_type='ROLE_PERMISSION_RESET',
                request=request,
                details={
                    'role': role, 'permission': permission,
                    'default': default_allows(role, permission),
                },
                severity='WARNING',
            )
        return Response({
            'detail': 'أعيدت الصلاحية للوضع الافتراضي' if deleted
            else 'لا يوجد تجاوز لهذه الصلاحية',
            'default': default_allows(role, permission),
        })
