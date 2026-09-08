"""Patient self-service portal.

Read-only endpoints scoped to the caller's own linked Patient record. The
PATIENT role previously had no way to reach its own data: the appointment
viewset filtered on ``patient__user``, a column that did not exist, and every
other app scoped by channel membership — which a PATIENT account can never
hold (ChannelMembership.clean rejects them).

Everything here is strict: the caller's role must be PATIENT and the linked
record must exist. Self-reads are deliberately not audit-logged per request —
a patient reading their own chart is not a PHI access worth 30 rows a day —
but lab-result reads are, because the audit trail of *who* saw a validated
result has compliance value even when the reader is the subject.
"""
import logging

from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from apps.audit.utils import log_security_event

logger = logging.getLogger('security')

PORTAL_FORBIDDEN = 'بوابة المريض متاحة لحسابات المرضى المرتبطة بسجل طبي فقط'


class PatientPortalPermission(permissions.BasePermission):
    message = PORTAL_FORBIDDEN

    def has_permission(self, request, view):
        return (
            getattr(request.user, 'is_authenticated', False)
            and getattr(request.user, 'role', '') == 'PATIENT'
        )


def _linked_patient(request):
    return getattr(request.user, 'patient_record', None)


def _deny_if_unlinked(patient):
    if patient is None:
        from rest_framework.exceptions import NotFound
        raise NotFound(PORTAL_FORBIDDEN)
    return patient


class PatientPortalViewSet(viewsets.ViewSet):
    """GET endpoints under /api/v1/patients/portal/ — own data only."""
    permission_classes = [PatientPortalPermission]

    @staticmethod
    def _patient(request):
        return _deny_if_unlinked(_linked_patient(request))

    # ---- /portal/ ---------------------------------------------------------
    def list(self, request):
        """Summary of the caller's own record (used as the portal landing)."""
        patient = self._patient(request)
        from apps.patients.serializers import PatientSerializer
        data = PatientSerializer(patient).data
        data['sections'] = [
            'appointments', 'invoices', 'lab-results',
            'prescriptions', 'records',
        ]
        return Response(data)

    # ---- /portal/<section>/ -----------------------------------------------
    def retrieve(self, request, pk=None):
        """/portal/<section>/ — appointments, invoices, lab-results,
        prescriptions, records."""
        return self._section(request, str(pk or '').strip().lower())

    def _section(self, request, section):
        patient = self._patient(request)

        if section == 'appointments':
            from apps.appointments.serializers import AppointmentSerializer
            qs = patient.appointments.select_related(
                'doctor', 'channel', 'basin'
            ).order_by('-scheduled_at')[:100]
            return Response(AppointmentSerializer(
                qs, many=True, context={'request': request}
            ).data)

        if section == 'invoices':
            from apps.billing.serializers import InvoiceSerializer
            qs = patient.invoices.select_related(
                'created_by'
            ).prefetch_related('items').order_by('-created_at')[:100]
            return Response(InvoiceSerializer(
                qs, many=True, context={'request': request}
            ).data)

        if section == 'lab-results':
            from apps.lab.models import LabResult
            from apps.lab.serializers import LabResultSerializer
            qs = LabResult.objects.filter(
                order__patient=patient
            ).select_related(
                'order__test', 'order__doctor', 'performed_by', 'validated_by'
            ).order_by('-created_at')[:100]
            log_security_event(
                user=request.user,
                event_type='DATA_ACCESSED',
                request=request,
                details={'section': 'lab_results', 'count': qs.count()},
            )
            return Response(LabResultSerializer(
                qs, many=True, context={'request': request}
            ).data)

        if section == 'prescriptions':
            from apps.pharmacy.models import Prescription
            from apps.pharmacy.serializers import PrescriptionSerializer
            qs = patient.prescriptions.select_related(
                'doctor'
            ).prefetch_related('items__medication').order_by('-created_at')[:100]
            return Response(PrescriptionSerializer(
                qs, many=True, context={'request': request}
            ).data)

        if section == 'records':
            from apps.patients.models import MedicalRecord
            from apps.patients.serializers import MedicalRecordSerializer
            qs = MedicalRecord.objects.filter(
                channel__patient=patient
            ).select_related('channel', 'created_by').order_by('-created_at')[:100]
            return Response(MedicalRecordSerializer(
                qs, many=True, context={'request': request}
            ).data)

        return Response(
            {'detail': 'قسم غير معروف'},
            status=status.HTTP_404_NOT_FOUND,
        )

