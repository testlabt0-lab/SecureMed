from django.core.exceptions import PermissionDenied
from django.db.models import Q

class PatientAccessMixin:
    """
    Mixin to enforce access control and reduce code duplication 
    across Patient-related views.
    """

    def check_patient_access(self, user, patient, action_name='access'):
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return True
        if patient.channels.filter(
            Q(owner=user) | Q(memberships__user=user, memberships__is_active=True)
        ).exists():
            return True
        raise PermissionDenied(f'غير مصرح لك بالوصول إلى بيانات هذا المريض')

    def get_viewable_channels(self, user, patient):
        """Returns channels the user is allowed to view for a patient."""
        if user.role in ['SUPER_ADMIN', 'HOSPITAL_ADMIN']:
            return list(patient.channels.all())
        return [c for c in patient.channels.all() if c.can_view(user)]
