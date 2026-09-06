"""HL7 FHIR R4 read-only API.

Authorisation mirrors apps.core.mixins: a caller only ever reaches patients they
share an active channel with, or — for the privileged roles — every patient in
their basin. The FHIR representation itself lives on the model
(``Patient.to_fhir``) so there is exactly one place that decrypts PHI into a
FHIR resource.
"""
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
