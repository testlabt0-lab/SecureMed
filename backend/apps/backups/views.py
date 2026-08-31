"""
Backup API — SUPER_ADMIN only.
list / create / download / delete backups. Every action is audited.
"""
import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.backups.models import BackupRecord
from apps.backups.serializers import BackupRecordSerializer
from apps.backups.services import create_backup, verify_backup, backup_dir
from apps.audit.utils import log_security_event


class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and request.user.is_authenticated
            and request.user.role == 'SUPER_ADMIN'
        )


class BackupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET    /api/v1/backups/          → list archives
    POST   /api/v1/backups/create/   → run a backup now
    GET    /api/v1/backups/{id}/download/ → download the ZIP
    DELETE /api/v1/backups/{id}/     → delete archive + record
    GET    /api/v1/backups/{id}/verify/   → integrity check
    """
    queryset = BackupRecord.objects.all()
    serializer_class = BackupRecordSerializer
    permission_classes = [IsSuperAdmin]

    @action(detail=False, methods=['post'])
    def create_backup_action(self, request):
        """Run a synchronous backup (demo scale)."""
        note = str(request.data.get('note') or '')[:255]
        try:
            record = create_backup(
                created_by=request.user,
                kind=BackupRecord.Kind.MANUAL,
                note=note,
            )
        except Exception as e:
            log_security_event(
                user=request.user,
                event_type='BACKUP_FAILED',
                request=request,
                details={'error': str(e)[:200]},
                severity='ERROR',
            )
            return Response(
                {'detail': f'فشل إنشاء النسخة الاحتياطية: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        log_security_event(
            user=request.user,
            event_type='BACKUP_CREATED',
            request=request,
            details={'filename': record.filename, 'size': record.size_bytes},
        )
        return Response(
            BackupRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        record = self.get_object()
        if not record.exists_on_disk:
            return Response(
                {'detail': 'ملف النسخة غير موجود على القرص'},
                status=status.HTTP_404_NOT_FOUND,
            )
        log_security_event(
            user=request.user,
            event_type='BACKUP_DOWNLOADED',
            request=request,
            details={'filename': record.filename},
        )
        response = FileResponse(
            open(record.filepath, 'rb'),
            content_type='application/zip',
            as_attachment=True,
            filename=record.filename,
        )
        return response

    @action(detail=True, methods=['get'])
    def verify(self, request, pk=None):
        record = self.get_object()
        if not record.exists_on_disk:
            return Response(
                {'detail': 'ملف النسخة غير موجود على القرص'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            manifest = verify_backup(record.filepath)
        except Exception as e:
            return Response(
                {'valid': False, 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'valid': True, 'manifest': manifest})

    def destroy(self, request, *args, **kwargs):
        record = self.get_object()
        try:
            os.remove(record.filepath)
        except OSError:
            pass
        log_security_event(
            user=request.user,
            event_type='BACKUP_DELETED',
            request=request,
            details={'filename': record.filename},
        )
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
