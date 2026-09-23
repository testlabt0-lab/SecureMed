from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

# Roles that may see every patient record in their basin scope. Keep this in
# ONE place: check_patient_access(), accessible_patients() and the media
# download guard must never disagree about who is privileged.
PATIENT_INDEX_ADMIN_ROLES = ('SUPER_ADMIN', 'HOSPITAL_ADMIN')

# Roles permitted to trigger emergency break-glass protocol
CLINICAL_BREAK_GLASS_ROLES = (
    'DOCTOR', 'NURSE', 'LAB_TECH', 'PHARMACIST',
    'SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN'
)

# Roles that must never be handed the staff directory. PATIENT is the default
# role for new accounts (User.Role default), so any self-registered user could
# previously enumerate every employee's name, email and role.
NON_CLINICAL_ROLES = ('PATIENT', 'ACCOUNTANT', 'RECEPTIONIST', 'AUDITOR')


def accessible_patients(qs, user):
    """Restrict a Patient queryset to what `user` is allowed to see.

    Queryset-level twin of check_patient_access(): basin scoping first, then the
    channel-membership rule. Use this anywhere patients are *listed* or
    *searched* — check_patient_access() only guards a single known record.

    Non-privileged roles are reduced to patients they share a channel with, or
    patients for which they have an active Break-Glass access.
    """
    from apps.basins.utils import basin_scoped_queryset
    from apps.security.models import BreakGlassAccess

    qs = basin_scoped_queryset(qs, user, lookup='basin_id')
    if getattr(user, 'role', None) in PATIENT_INDEX_ADMIN_ROLES:
        return qs

    now = timezone.now()
    active_bg_patient_ids = BreakGlassAccess.objects.filter(
        user=user,
        status=BreakGlassAccess.Status.ACTIVE,
        expires_at__gt=now
    ).values_list('patient_id', flat=True)

    return qs.filter(
        Q(channels__owner=user)
        | Q(channels__memberships__user=user, channels__memberships__is_active=True)
        | Q(id__in=active_bg_patient_ids)
    ).distinct()


class BreakGlassAvailableDenied(PermissionDenied):
    """Specific PermissionDenied error signaling that Break-Glass can be activated."""
    def __init__(self, message='غير مصرح لك بالوصول إلى بيانات هذا المريض', break_glass_available=False, patient_id=None):
        super().__init__(message)
        self.break_glass_available = break_glass_available
        self.patient_id = patient_id


class PatientAccessMixin:
    """
    Mixin to enforce access control and reduce code duplication
    across Patient-related views.
    """

    def check_patient_access(self, user, patient, action_name='access'):
        # 1. Canary / Honeypot patient trap: any access immediately triggers tripwire
        from apps.security.honeypot import is_canary_patient, handle_canary_access
        if is_canary_patient(patient):
            req = getattr(self, 'request', None)
            handle_canary_access(user, patient, request=req, action=action_name)
            from django.http import Http404
            raise Http404('المريض غير موجود')

        # 2. Track EHR hopping velocity across distinct patient charts
        try:
            from apps.core.anomaly import record_patient_hopping
            patient_pk = getattr(patient, 'id', getattr(patient, 'pk', None))
            if patient_pk:
                record_patient_hopping(user, patient_pk)
        except Exception:
            pass

        from apps.security.models import BreakGlassAccess

        if getattr(user, 'role', None) in PATIENT_INDEX_ADMIN_ROLES:
            return True

        if patient.channels.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
        ).exists():
            return True

        now = timezone.now()
        active_bg = BreakGlassAccess.objects.filter(
            user=user,
            patient=patient,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).first()

        if active_bg:
            return True

        can_break_glass = getattr(user, 'role', None) in CLINICAL_BREAK_GLASS_ROLES

        raise BreakGlassAvailableDenied(
            message='غير مصرح لك بالوصول إلى بيانات هذا المريض',
            break_glass_available=can_break_glass,
            patient_id=str(patient.id)
        )

    def get_viewable_channels(self, user, patient):
        """Returns channels the user is allowed to view for a patient."""
        from apps.security.models import BreakGlassAccess

        channels_qs = patient.channels.select_related('owner', 'patient', 'basin').prefetch_related('memberships__user')

        if getattr(user, 'role', None) in PATIENT_INDEX_ADMIN_ROLES:
            return list(channels_qs)

        now = timezone.now()
        has_active_bg = BreakGlassAccess.objects.filter(
            user=user,
            patient=patient,
            status=BreakGlassAccess.Status.ACTIVE,
            expires_at__gt=now
        ).exists()

        if has_active_bg:
            return list(channels_qs)

        return list(
            channels_qs.filter(
                Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
            ).distinct()
        )

