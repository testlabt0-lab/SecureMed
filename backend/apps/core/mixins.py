from django.core.exceptions import PermissionDenied
from django.db.models import Q

# Roles that may see every patient record in their basin scope. Keep this in
# ONE place: check_patient_access(), accessible_patients() and the media
# download guard must never disagree about who is privileged.
PATIENT_INDEX_ADMIN_ROLES = ('SUPER_ADMIN', 'HOSPITAL_ADMIN')

# Roles that must never be handed the staff directory. PATIENT is the default
# role for new accounts (User.Role default), so any self-registered user could
# previously enumerate every employee's name, email and role.
NON_CLINICAL_ROLES = ('PATIENT',)


def accessible_patients(qs, user):
    """Restrict a Patient queryset to what `user` is allowed to see.

    Queryset-level twin of check_patient_access(): basin scoping first, then the
    channel-membership rule. Use this anywhere patients are *listed* or
    *searched* — check_patient_access() only guards a single known record.

    Non-privileged roles are reduced to patients they share a channel with, so a
    PATIENT-role account resolves to its own record at most rather than to the
    whole index.
    """
    from apps.basins.utils import basin_scoped_queryset

    qs = basin_scoped_queryset(qs, user, lookup='basin_id')
    if getattr(user, 'role', None) in PATIENT_INDEX_ADMIN_ROLES:
        return qs
    return qs.filter(
        Q(channels__owner=user)
        | Q(channels__memberships__user=user, channels__memberships__is_active=True)
    ).distinct()


class PatientAccessMixin:
    """
    Mixin to enforce access control and reduce code duplication
    across Patient-related views.
    """

    def check_patient_access(self, user, patient, action_name='access'):
        if user.role in PATIENT_INDEX_ADMIN_ROLES:
            return True
        if patient.channels.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
        ).exists():
            return True
        raise PermissionDenied(f'غير مصرح لك بالوصول إلى بيانات هذا المريض')

    def get_viewable_channels(self, user, patient):
        """Returns channels the user is allowed to view for a patient."""
        if user.role in PATIENT_INDEX_ADMIN_ROLES:
            return list(patient.channels.all())
        return [c for c in patient.channels.all() if c.can_view(user)]
