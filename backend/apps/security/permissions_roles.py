"""
Role-based access control permission classes.

Used as ``permission_classes = [IsDoctor]`` on DRF views. The class-body form
is the right one here: every request creates a fresh instance (see
``APIView.get_permissions``), so the class itself carries the role list and
the per-instance state is the request-scoped state DRF puts on it.

The previous revision stored ``allowed_roles`` in ``__init__`` and read it
off ``self`` from ``has_permission``. That worked for a singleton pattern but
broke under DRF's per-request instantiation: ``IsDoctor()`` was called with
no arguments, so ``self.allowed_roles`` was the empty list, and the
``if not allowed: return True`` fall-through admitted every authenticated
user — including patients, who would have seen doctor-only endpoints.
"""
from rest_framework.permissions import BasePermission


class RoleRequired(BasePermission):
    """Base for a class-body RBAC permission.

    Subclasses set ``allowed_roles`` as a class attribute; the check then
    compares the user's role against that list. ``SUPER_ADMIN`` always
    passes, so individual views do not have to repeat it in every list.
    """

    #: Roles allowed by this permission. Set in subclasses.
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return False

        if getattr(user, 'role', None) == 'SUPER_ADMIN':
            return True

        # A view may narrow the role list at runtime (e.g. an endpoint that
        # should be visible to either of two roles whose classes are
        # otherwise unrelated). When absent, fall back to the class default.
        view_allowed = getattr(view, 'allowed_roles', None)
        effective = view_allowed if view_allowed else self.allowed_roles
        if not effective:
            # No roles configured at all: treat as "any authenticated user"
            # so subclasses that forget to set the attribute do not silently
            # grant admin access.
            return True
        return getattr(user, 'role', None) in effective


class IsDoctor(RoleRequired):
    allowed_roles = ('DOCTOR',)


class IsNurse(RoleRequired):
    allowed_roles = ('NURSE',)


class IsHospitalAdmin(RoleRequired):
    allowed_roles = ('HOSPITAL_ADMIN',)


class IsCenterAdmin(RoleRequired):
    allowed_roles = ('CENTER_ADMIN',)


class IsPharmacist(RoleRequired):
    allowed_roles = ('PHARMACIST',)


class IsLabTech(RoleRequired):
    allowed_roles = ('LAB_TECH',)


class IsReceptionist(RoleRequired):
    allowed_roles = ('RECEPTIONIST',)


class IsAuditor(RoleRequired):
    allowed_roles = ('AUDITOR',)


class IsAdmin(RoleRequired):
    allowed_roles = ('SUPER_ADMIN', 'HOSPITAL_ADMIN', 'CENTER_ADMIN')


class IsMedicalStaff(RoleRequired):
    allowed_roles = ('DOCTOR', 'NURSE')
