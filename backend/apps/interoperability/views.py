"""HL7 FHIR R4 read-only API.

Authorisation mirrors apps.core.mixins: a caller only ever reaches patients they
share an active channel with, or — for the privileged roles — every patient in
their basin. The FHIR representation itself lives on the model
(``Patient.to_fhir``) so there is exactly one place that decrypts PHI into a
FHIR resource.
"""
import uuid

from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from apps.audit.utils import log_security_event
from apps.core.mixins import accessible_patients
from apps.patients.models import Patient


class FHIRPatientViewSet(viewsets.ViewSet):
    """
    HL7 FHIR compliant API for Patients.
    Exposes patient data in the standard FHIR JSON format.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return accessible_patients(Patient.objects.all(), self.request.user)

    def retrieve(self, request, pk=None):
        # Scoping the lookup (instead of Patient.objects.all()) is what stops an
        # authenticated caller from reading any patient by guessing an id, and
        # keeps an unauthorised id indistinguishable from a missing one.
        patient = get_object_or_404(self.get_queryset(), pk=pk)

        # A FHIR export hands out decrypted name, national id, phone and
        # address, so it belongs in the audit trail like any other PHI read.
        log_security_event(
            user=request.user,
            event_type='FHIR_PATIENT_EXPORT',
            request=request,
            details={'patient_id': str(patient.id)},
        )
        return Response(patient.to_fhir())


class FHIRObservationViewSet(viewsets.ViewSet):
    """HL7 FHIR R4 read-only Observation endpoint over validated lab results.

    Maps apps.lab models to the FHIR Observation resource: the LabTest code is
    the LOINC coding, the numeric or text value becomes
    valueQuantity/valueCodeableConcept, and the reference range comes from the
    test catalog. Only results whose order reached COMPLETED/VALIDATED are
    exposed — a technical value a lab tech just keyed is not yet a clinical
    fact.
    """
    permission_classes = [permissions.IsAuthenticated]

    _STATUS_MAP = {
        'ORDERED': 'registered',
        'SAMPLE_COLLECTED': 'registered',
        'IN_PROGRESS': 'registered',
        'COMPLETED': 'final',
        'VALIDATED': 'final',
        'CANCELLED': 'cancelled',
    }

    def _results(self, request):
        from apps.lab.models import LabResult
        # Scoped ALWAYS, not only when a patient filter is present: without
        # this, an authenticated caller could fetch any Observation by
        # guessing ids, bypassing the channel/basin model entirely.
        from django.db.models import Q
        scoped = self._patient_queryset(request).values_list('id', flat=True)
        qs = LabResult.objects.select_related(
            'order__test', 'order__patient'
        ).filter(
            Q(order__patient_id__in=scoped[:500]),
            order__status__in=('COMPLETED', 'VALIDATED'),
        ).order_by('-created_at')

        patient_id = request.query_params.get('patient')
        if patient_id:
            try:
                uuid.UUID(str(patient_id))
            except (ValueError, AttributeError):
                return None, Response(
                    {'detail': 'patient id غير صالح'}, status=400
                )
            if not self._patient_queryset(request).filter(pk=patient_id).exists():
                # Same 404-not-403 rule as the Patient endpoint.
                return None, Response(status=404)
            qs = qs.filter(order__patient_id=patient_id)
        return qs, None

    def _patient_queryset(self, request):
        return accessible_patients(Patient.objects.all(), request.user)

    def list(self, request):
        qs, error = self._results(request)
        if error is not None:
            return error
        # The export hand-off is bulk here, so it is audited as one event with
        # a count rather than one row per observation.
        results = list(qs[:100])
        if results:
            log_security_event(
                user=request.user,
                event_type='FHIR_PATIENT_EXPORT',
                request=request,
                details={
                    'resource': 'Observation',
                    'count': len(results),
                    'patient_id': str(results[0].order.patient_id)
                    if request.query_params.get('patient') else None,
                },
            )
        return Response({
            'resourceType': 'Bundle',
            'type': 'searchset',
            'total': len(results),
            'entry': [
                {'resource': result.to_fhir()} for result in results
            ],
        })

    def retrieve(self, request, pk=None):
        from apps.lab.models import LabResult
        qs, error = self._results(request)
        if error is not None:
            return error
        result = get_object_or_404(qs, pk=pk)
        log_security_event(
            user=request.user,
            event_type='FHIR_PATIENT_EXPORT',
            request=request,
            details={
                'resource': 'Observation',
                'result_id': str(result.id),
            },
        )
        return Response(result.to_fhir())

