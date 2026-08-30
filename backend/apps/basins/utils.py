"""
Reusable basin helpers: module gating + queryset scoping.

The plan requirement:
  «يجب أن ترتبط بالأحواز وتُفعّل بحسب نوع الأحواز»
is enforced here in ONE place so every app (patients, channels, ai,
reports...) gates its features through the same function.
"""
from django.core.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response

from apps.basins.models import Basin


def basin_of(user):
    """Return the user's basin (or None for global/unassigned users)."""
    return getattr(user, 'basin', None)


def ensure_module_enabled(user, module: str):
    """
    Raise PermissionDenied when the user's basin does NOT have `module`
    activated. Users without a basin (global deployment accounts) pass.
    """
    basin = basin_of(user)
    if basin is None:
        return
    if not basin.is_active:
        raise PermissionDenied(
            f'الحوض «{basin.name}» غير مفعّل حالياً — راجع مدير النظام'
        )
    if not basin.has_module(module):
        label = Basin.MODULE_LABELS.get(module, module)
        raise PermissionDenied(
            f'وحدة «{label}» غير مفعّلة في حوض «{basin.name}» '
            f'(نوع الحوض: {basin.get_basin_type_display()})'
        )


def basin_scoped_queryset(qs, user, lookup: str = 'basin_id'):
    """
    Restrict a queryset to the user's basin when the user is a
    HOSPITAL_ADMIN bound to a basin. SUPER_ADMIN / basin-less users see all.
    """
    if user.role == 'SUPER_ADMIN':
        return qs
    basin = basin_of(user)
    if basin is None:
        return qs
    if user.role in ['HOSPITAL_ADMIN', 'AUDITOR']:
        kwargs = {lookup: basin.id}
        # Admins also keep visibility of legacy basin-less rows.
        null_kwarg = {f'{lookup}__isnull': True}
        return (qs.filter(**kwargs) | qs.filter(**null_kwarg)).distinct()
    return qs
