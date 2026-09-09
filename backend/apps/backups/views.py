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
        """Run a synchronous backup (demo scale).

        `scope` selects what the archive covers: FULL (default), DATABASE
        (db dump only) or MEDIA (uploaded files only) — القاعدة والملفات
        قابلة للفصل عند النسخ والاستعادة.
        """
        note = str(request.data.get('note') or '')[:255]
        scope = str(request.data.get('scope') or BackupRecord.Scope.FULL).upper()
        if scope not in BackupRecord.Scope.values:
            return Response(
                {'detail': f'نطاق غير معروف: {scope} — المسموح: {", ".join(BackupRecord.Scope.values)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            record = create_backup(
                created_by=request.user,
                kind=BackupRecord.Kind.MANUAL,
                note=note,
                scope=scope,
            )
        except Exception as e:
            log_security_event(
                user=request.user,
                event_type='BACKUP_FAILED',
                request=request,
                details={'error': str(e)[:200], 'scope': scope},
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
            details={'filename': record.filename, 'size': record.size_bytes, 'scope': record.scope},
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
        # The file on disk is encrypted-at-rest. Streaming it as
        # application/zip would hand the operator a blob they cannot open
        # (and one that, since it lives in BACKUP_DIR, may also be the
        # file that the next encrypted backup will overwrite). Decrypt it
        # here so what reaches the browser is a real ZIP.
        from apps.backups.services import _get_decrypted_backup
        decrypted = _get_decrypted_backup(record.filepath)
        response = FileResponse(
            decrypted,
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

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        record = self.get_object()
        if not record.exists_on_disk:
            return Response(
                {'detail': 'ملف النسخة غير موجود على القرص'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        force_raw = request.data.get('force', False)
        if isinstance(force_raw, str):
            force = force_raw.strip().lower() in ('1', 'true', 'yes', 'on')
        else:
            force = bool(force_raw)
        
        try:
            from apps.backups.services import restore_backup
            result = restore_backup(record.filepath, force=force)
            
            if force:
                log_security_event(
                    user=request.user,
                    event_type='BACKUP_RESTORED',
                    request=request,
                    details={'filename': record.filename, 'restored_media_files': result.get('restored_media_files', 0)},
                    severity='CRITICAL',
                )
                # Restore is the most destructive operation in the system —
                # the admin chat hears about it immediately, with the safety
                # copy that was taken right before it.
                try:
                    from apps.security.telegram_service import send_critical_alert
                    send_critical_alert(
                        'تمت استعادة نسخة احتياطية!',
                        [
                            f"<b>الأرشيف المستعاد:</b> <code>{record.filename}</code>",
                            f"<b>النطاق:</b> {result.get('scope', 'FULL')}",
                            f"<b>بواسطة:</b> {request.user.email}",
                            result.get('safety_backup') and (
                                f"<b>نسخة الأمان قبل الاستعادة:</b> "
                                f"<code>{result['safety_backup']}</code>"
                            ) or None,
                        ],
                    )
                except Exception as e:
                    import logging
                    logging.getLogger('security').error(f"Restore telegram alert failed: {e}")
                return Response(result)
        except Exception as e:
            log_security_event(
                user=request.user,
                event_type='SYSTEM_EVENT',
                request=request,
                details={'action': 'RESTORE_FAILED', 'error': str(e)[:200]},
                severity='ERROR',
            )
            return Response(
                {'detail': f'فشلت الاستعادة: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def delivery_status(self, request):
        """Which off-site channels are configured, for the dashboard UI."""
        from django.conf import settings as s
        telegram_ready = bool(
            getattr(s, 'TELEGRAM_BOT_TOKEN', '') and getattr(s, 'TELEGRAM_ADMIN_CHAT_ID', '')
        )
        cloud_ready = bool(getattr(s, 'BACKUP_OFFSITE_BUCKET', ''))
        return Response({
            'telegram': {
                'enabled': bool(getattr(s, 'BACKUP_SEND_TO_TELEGRAM', False)),
                'ready': telegram_ready,
            },
            'cloud': {
                'enabled': bool(getattr(s, 'BACKUP_OFFSITE_ENABLED', False)),
                'ready': cloud_ready,
                'bucket': getattr(s, 'BACKUP_OFFSITE_BUCKET', '') or None,
            },
            'any_enabled': (
                bool(getattr(s, 'BACKUP_SEND_TO_TELEGRAM', False))
                or bool(getattr(s, 'BACKUP_OFFSITE_ENABLED', False))
            ),
        })

    @action(detail=True, methods=['post'])
    def deliver_offsite(self, request, pk=None):
        """Re-run off-site delivery (Telegram / cloud) for one archive."""
        record = self.get_object()
        if not record.exists_on_disk:
            return Response(
                {'detail': 'ملف النسخة غير موجود على القرص'},
                status=status.HTTP_404_NOT_FOUND,
            )
        from apps.backups.offsite import deliver_backup
        result = deliver_backup(record)
        log_security_event(
            user=request.user,
            event_type='BACKUP_DELIVERED' if record.delivered_offsite else 'BACKUP_DELIVERY_FAILED',
            request=request,
            details={
                'filename': record.filename,
                'delivery_status': record.delivery_status,
            },
            severity='INFO' if record.delivered_offsite else 'WARNING',
        )
        return Response({
            'delivery_status': record.delivery_status,
            'delivery_status_display': record.get_delivery_status_display(),
            'results': result['results'],
        })

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
