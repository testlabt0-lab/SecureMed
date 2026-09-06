"""
Cross-cutting endpoints that belong to no single domain app.

Mounted under /api/v1/core/.
"""
import logging

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.utils import log_security_event

logger = logging.getLogger(__name__)

# Operation types a future implementation is expected to accept. Kept here so the
# rejection response can tell a client which of its queued operations would be
# understood at all.
KNOWN_OPERATION_TYPES = ('vital_sign', 'medical_note')


class OfflineSyncAPIView(APIView):
    """POST /api/v1/core/sync/ — offline batch upload. NOT IMPLEMENTED.

    This endpoint used to accept a batch of offline operations, log each payload
    and answer ``{"status": "success", "synced": N}`` — while writing nothing to
    the database. Two consequences, both bad:

      * a PWA that trims its local queue on a successful sync (the whole point of
        the contract) discarded clinical observations permanently. Silent data
        loss is worse than a visible failure;
      * every payload was written verbatim to the application log at INFO, so
        vitals and clinical notes — PHI — ended up in a log file that is not
        access-controlled, not encrypted and shipped off-box.

    There is no model to persist into yet: the project has ``patients.Patient``,
    ``MedicalRecord`` and ``MedicalFile``, but no vitals table and no
    client-operation identifier to deduplicate replayed batches against. Until
    both exist, the honest answer is 501 — a client that keeps its queue can
    replay it once the feature lands.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        operations = request.data.get('operations')
        if not isinstance(operations, list):
            operations = []

        # Counts and types only. The payloads themselves are PHI and are never
        # logged; nothing here is persisted, so there is nothing else to record.
        counts = {}
        for op in operations:
            op_type = op.get('type') if isinstance(op, dict) else None
            key = op_type if op_type in KNOWN_OPERATION_TYPES else 'unknown'
            counts[key] = counts.get(key, 0) + 1

        logger.warning(
            'OFFLINE_SYNC_REJECTED | user=%s | operations=%d | types=%s',
            request.user.pk, len(operations), sorted(counts),
        )
        log_security_event(
            user=request.user,
            event_type='OFFLINE_SYNC_REJECTED',
            request=request,
            severity='WARNING',
            details={'operation_count': len(operations), 'by_type': counts},
        )

        return Response(
            {
                'detail': 'مزامنة العمل دون اتصال غير مفعّلة بعد — لم يتم حفظ أي بيانات. '
                          'احتفظ بالعمليات محلياً وأعد إرسالها لاحقاً.',
                'code': 'OFFLINE_SYNC_NOT_IMPLEMENTED',
                'synced': 0,
                'received': len(operations),
                'supported_types': list(KNOWN_OPERATION_TYPES),
            },
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )
