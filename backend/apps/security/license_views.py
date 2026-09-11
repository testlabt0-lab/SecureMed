"""API لإدارة تراخيص الأجهزة — امتداد للوحة تحكم الأمان.

نفس قواعد licensing.py تُطبَّق هنا ومن البوت حتى لا يتباعد المساران.
"""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.security.licensing import deactivate_license, issue_license
from apps.security.models import DeviceLicense, DeviceRegistry
from apps.security.permissions import IsAdmin, IsAuditor


class DeviceLicenseSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source='device.user.email', read_only=True)
    device_fingerprint = serializers.CharField(
        source='device.device_fingerprint', read_only=True,
    )
    mac_address = serializers.CharField(source='device.mac_address', read_only=True)
    os_info = serializers.CharField(source='device.os_info', read_only=True)

    class Meta:
        model = DeviceLicense
        fields = [
            'id', 'license_key', 'device', 'owner_email', 'device_fingerprint',
            'mac_address', 'os_info', 'status', 'issued_by', 'issued_at',
            'activated_at', 'deactivated_at', 'expires_at', 'last_verified_at',
            'notes',
        ]
        read_only_fields = [
            'license_key', 'device', 'issued_by', 'issued_at', 'activated_at',
            'deactivated_at', 'expires_at', 'last_verified_at',
        ]


class DeviceLicenseViewSet(viewsets.ModelViewSet):
    """تراخيص الأجهزة: عرض، ترخيص/تجديد، وإلغاء التفعيل — للإدارة فقط."""
    queryset = DeviceLicense.objects.select_related('device__user').all()
    serializer_class = DeviceLicenseSerializer
    permission_classes = [IsAdmin | IsAuditor]

    @action(detail=False, methods=['post'], url_path='issue')
    def issue(self, request):
        """ترخيص جهاز: {device_id, days?, notes?} — days بدون قيمة = دائم."""
        device_id = request.data.get('device_id') or ''
        device = DeviceRegistry.objects.filter(id=device_id).first()
        if device is None:
            return Response(
                {'detail': 'الجهاز غير موجود'},
                status=status.HTTP_404_NOT_FOUND,
            )
        license_obj, created = issue_license(
            device,
            issued_by='dashboard',
            days=request.data.get('days'),
            notes=request.data.get('notes', ''),
        )
        return Response(
            {
                **self.get_serializer(license_obj).data,
                'created': created,
                'detail': 'تم إصدار الترخيص' if created else 'تم تجديد تفعيل الترخيص',
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """إلغاء ترخيص: شاشة القفل تعود للظهور دون قائمة سوداء."""
        license_obj = self.get_object()
        if license_obj.status == DeviceLicense.Status.REVOKED:
            return Response({'detail': 'الترخيص ملغى بالفعل'})
        deactivate_license(license_obj.device, via='dashboard', request=request)
        return Response({
            **self.get_serializer(license_obj).data,
            'detail': 'تم إلغاء ترخيص الجهاز',
        })
