"""Authenticated access to user-uploaded media.

Every file under ``MEDIA_ROOT`` in SecureMed is protected health information:
``medical_files/<channel_id>/<uuid>.<ext>`` (``patients.MedicalFile``) and
``telemedicine/attachments/...`` (``telemedicine.ChatMessage``). Django's
``static.serve()`` applies no authorisation whatsoever, so wiring MEDIA_URL to it
in production hands PHI to anyone who holds — or guesses — a URL, with nothing
written to the audit trail.

This view enforces the same rule as the API download endpoints: the caller must
be authenticated, and for a channel-scoped file they must be able to view that
channel. Reads are recorded and audited just like
``MedicalFileViewSet.download``, so a PHI access is never invisible.

Two further reasons this no longer calls ``static.serve()``:

* ``serve()`` reads the file straight off disk, bypassing the storage API. Files are
  now encrypted at rest (``apps.core.storage``), so that path would hand the client
  AES-GCM ciphertext. Opening through ``default_storage`` decrypts transparently.
* ``serve()`` guesses ``Content-Type`` from the filename and serves it inline. An
  attachment on ``telemedicine.ChatMessage`` has no content validation at all, so an
  uploaded ``.html`` or ``.svg`` came back as ``text/html`` / ``image/svg+xml`` on
  this origin — stored XSS in an authenticated clinician's session, with access to
  the SPA's storage. Anything outside a small inline-safe allow-list is now forced to
  ``application/octet-stream`` with ``Content-Disposition: attachment``.
"""
import mimetypes
import posixpath

from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework import permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from apps.audit.utils import log_security_event
from apps.core.mixins import PATIENT_INDEX_ADMIN_ROLES, accessible_patients

MEDICAL_FILES_PREFIX = 'medical_files/'
TELEMEDICINE_PREFIX = 'telemedicine/attachments/'

# Types a browser may render in place. Deliberately narrow, and deliberately without
# SVG: an SVG is a script container, and rendering one from this origin is equivalent
# to serving HTML. Everything else downloads.
INLINE_SAFE_TYPES = frozenset({
    'image/png',
    'image/jpeg',
    'image/gif',
    'application/pdf',
})


def _normalise(path):
    """Collapse the request path the way static.serve() will, and reject escapes."""
    cleaned = posixpath.normpath(path.replace('\\', '/')).lstrip('/')
    if cleaned.startswith('..') or '/../' in cleaned:
        raise Http404('Invalid media path')
    return cleaned


def _serve(rel_path, content_type, download_name):
    """Stream a stored file with the headers PHI should carry.

    ``default_storage`` rather than the filesystem, so encryption at rest is
    transparent; ``FileResponse`` sets Content-Length itself from the decrypted
    stream, and emits RFC 5987 ``filename*`` so Arabic filenames survive.
    """
    try:
        handle = default_storage.open(rel_path, 'rb')
    except (FileNotFoundError, SuspiciousFileOperation):
        raise Http404('Media file not found')

    inline = content_type in INLINE_SAFE_TYPES
    response = FileResponse(
        handle,
        content_type=content_type if inline else 'application/octet-stream',
        as_attachment=not inline,
        filename=download_name or posixpath.basename(rel_path),
    )
    # nosniff matters most on the forced-download branch: without it a browser may
    # sniff HTML out of a payload we deliberately labelled octet-stream.
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    response['Referrer-Policy'] = 'no-referrer'
    # PHI must not sit in a shared or on-disk HTTP cache.
    response['Cache-Control'] = 'private, no-store, max-age=0'
    return response


class ProtectedMediaView(APIView):
    """Serve a file from MEDIA_ROOT only to a caller allowed to read it."""

    # JWT (the SPA's normal credential) comes from DEFAULT_AUTHENTICATION_CLASSES;
    # SessionAuthentication is added so staff browsing via Django admin work too.
    authentication_classes = [
        *api_settings.DEFAULT_AUTHENTICATION_CLASSES,
        SessionAuthentication,
    ]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, path):
        rel_path = _normalise(path)

        if rel_path.startswith(MEDICAL_FILES_PREFIX):
            instance = self._authorise_medical_file(request, rel_path)
            return _serve(
                rel_path,
                instance.mime_type or 'application/octet-stream',
                instance.original_filename,
            )

        if rel_path.startswith(TELEMEDICINE_PREFIX):
            self._authorise_chat_attachment(request, rel_path)
            # ChatMessage.attachment has no validators, so nothing here is trusted:
            # the guess only decides between "render" and "download", and anything
            # not on the allow-list downloads.
            guessed = mimetypes.guess_type(rel_path)[0] or 'application/octet-stream'
            return _serve(rel_path, guessed, posixpath.basename(rel_path))

        # No other model writes under MEDIA_ROOT today, so this branch is
        # only reachable by a probe or by a namespace added later. Default to
        # deny: a file we cannot attribute to a channel is a file we cannot
        # authorise, and 404 (not 403) keeps it from confirming what exists.
        if getattr(request.user, 'role', None) not in PATIENT_INDEX_ADMIN_ROLES:
            raise Http404('Media file not found')
        log_security_event(
            user=request.user,
            event_type='FILE_DOWNLOADED',
            request=request,
            severity='WARNING',
            details={'action': 'unclassified_media_download', 'path': rel_path},
        )
        # Unclassified: never rendered, always downloaded.
        return _serve(rel_path, 'application/octet-stream', posixpath.basename(rel_path))

    def _authorise_medical_file(self, request, rel_path):
        from apps.patients.models import MedicalFile

        instance = MedicalFile.objects.filter(file=rel_path).first()
        if instance is None:
            # No row means nothing may authorise this read, so refuse rather
            # than falling through to an unguarded file system read.
            raise Http404('Media file not found')

        if not instance.channel.can_view(request.user):
            raise PermissionDenied('غير مصرح لك بتنزيل هذا الملف')

        instance.record_access(request.user)
        log_security_event(
            user=request.user,
            event_type='PATIENT_DATA_ACCESSED',
            request=request,
            details={
                'action': 'file_download',
                'file_id': str(instance.id),
                'channel_id': str(instance.channel.id),
                'via': 'media',
            },
        )
        return instance

    def _authorise_chat_attachment(self, request, rel_path):
        from apps.patients.models import Patient
        from apps.telemedicine.models import ChatMessage

        message = (
            ChatMessage.objects
            .select_related('consultation')
            .filter(attachment=rel_path)
            .first()
        )
        if message is None:
            raise Http404('Media file not found')

        consultation = message.consultation
        allowed = (
            getattr(request.user, 'role', None) in PATIENT_INDEX_ADMIN_ROLES
            or message.sender_id == request.user.id
            or consultation.doctor_id == request.user.id
            or accessible_patients(
                Patient.objects.filter(pk=consultation.patient_id), request.user
            ).exists()
        )
        if not allowed:
            raise PermissionDenied('غير مصرح لك بالوصول إلى هذا المرفق')

        log_security_event(
            user=request.user,
            event_type='PATIENT_DATA_ACCESSED',
            request=request,
            details={
                'action': 'consultation_attachment_download',
                'message_id': str(message.id),
                'consultation_id': str(consultation.id),
            },
        )
        return message
