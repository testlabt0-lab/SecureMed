"""
Tests for dynamic role permissions management (إدارة الصلاحيات).

المصفوفة: كتالوج صلاحيات + وضع افتراضي لكل دور + تجاوزات ديناميكية
تدار من الواجهة، مع تدقيق كل تغيير.
"""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import RolePermission
from apps.accounts.permissions import (
    ALL_PERMISSION_CODES,
    default_allows,
    effective_allows,
    user_has_permission,
)
from apps.audit.models import AuditLog
from tests.factories import AdminUserFactory, UserFactory

pytestmark = pytest.mark.django_db

PERMISSIONS_URL = '/api/v1/auth/permissions/'


class TestCatalogAndDefaults:
    def test_doctor_defaults(self):
        assert default_allows('DOCTOR', 'records.create') is True
        assert default_allows('DOCTOR', 'users.manage') is False

    def test_super_admin_always_allows(self):
        assert default_allows('SUPER_ADMIN', 'anything.at.all') is True
        assert effective_allows('SUPER_ADMIN', 'anything.at.all') is True

    def test_override_changes_effective(self):
        assert effective_allows('NURSE', 'records.delete') is False
        RolePermission.objects.create(
            role='NURSE', permission='records.delete', allowed=True,
        )
        assert effective_allows('NURSE', 'records.delete') is True

    def test_user_has_permission_helper(self):
        user = UserFactory(role='DOCTOR')
        assert user_has_permission(user, 'records.create') is True
        assert user_has_permission(user, 'backups.manage') is False
        assert user_has_permission(None, 'records.view') is False


class TestRolePermissionAPI:
    def test_admin_reads_matrix(self):
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.get(PERMISSIONS_URL)
        assert res.status_code == 200
        body = res.data
        codes = {p['code'] for p in body['permissions']}
        assert codes == set(ALL_PERMISSION_CODES)
        roles = {r['value'] for r in body['roles']}
        assert 'DOCTOR' in roles and 'SUPER_ADMIN' in roles
        cell = body['matrix']['DOCTOR']['records.create']
        assert cell['default'] is True and cell['effective'] is True

    def test_admin_sets_override(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)

        res = client.post(f'{PERMISSIONS_URL}set/', {
            'role': 'DOCTOR', 'permission': 'records.delete', 'allowed': False,
        }, format='json')
        assert res.status_code == 200
        assert effective_allows('DOCTOR', 'records.delete') is False
        override = RolePermission.objects.get(role='DOCTOR', permission='records.delete')
        assert override.allowed is False
        assert override.updated_by == admin
        # the change is audited
        assert AuditLog.objects.filter(
            event_type='ROLE_PERMISSION_CHANGED',
            details__role='DOCTOR',
            details__permission='records.delete',
            details__allowed=False,
        ).exists()

    def test_reset_returns_to_default(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        admin = AdminUserFactory()
        RolePermission.objects.create(
            role='DOCTOR', permission='records.delete', allowed=False,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'{PERMISSIONS_URL}reset/', {
            'role': 'DOCTOR', 'permission': 'records.delete',
        }, format='json')
        assert res.status_code == 200
        assert not RolePermission.objects.filter(
            role='DOCTOR', permission='records.delete',
        ).exists()
        assert effective_allows('DOCTOR', 'records.delete') is True

    def test_super_admin_cannot_be_restricted(self):
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'{PERMISSIONS_URL}set/', {
            'role': 'SUPER_ADMIN', 'permission': 'backups.manage', 'allowed': False,
        }, format='json')
        assert res.status_code == 400
        assert not RolePermission.objects.filter(role='SUPER_ADMIN').exists()

    def test_unknown_permission_refused(self):
        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'{PERMISSIONS_URL}set/', {
            'role': 'DOCTOR', 'permission': 'made.up.permission', 'allowed': True,
        }, format='json')
        assert res.status_code == 400

    def test_non_admin_is_refused(self):
        doctor = UserFactory(role='DOCTOR')
        client = APIClient()
        client.force_authenticate(user=doctor)
        assert client.get(PERMISSIONS_URL).status_code == 403
        assert client.post(
            f'{PERMISSIONS_URL}set/',
            {'role': 'DOCTOR', 'permission': 'records.view', 'allowed': False},
            format='json',
        ).status_code == 403

    def test_anonymous_is_refused(self):
        client = APIClient()
        assert client.get(PERMISSIONS_URL).status_code in (401, 403)
