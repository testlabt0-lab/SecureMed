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


class TestDynamicEnforcement:
    """الإنفاذ الفعلي للمصفوفة على نقاط النهاية — ليس مجرد بنية بيانات."""

    def test_users_manage_revocation_blocks_editing_others(self, settings):
        """سحب users.manage من دور ما يمنع تعديل حسابات الآخرين فوراً."""
        settings.AUDIT_LOG_ASYNC = False
        admin = UserFactory(role='HOSPITAL_ADMIN')
        target = UserFactory(role='DOCTOR')
        RolePermission.objects.create(
            role='HOSPITAL_ADMIN', permission='users.manage', allowed=False,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.patch(
            f'/api/v1/auth/users/{target.id}/',
            {'full_name': 'Modified Name'}, format='json',
        )
        assert res.status_code == 403
        target.refresh_from_db()
        assert target.full_name != 'Modified Name'

    def test_users_manage_revocation_blocks_activation_actions(self):
        admin = UserFactory(role='HOSPITAL_ADMIN')
        target = UserFactory(role='DOCTOR', is_active=False)
        RolePermission.objects.create(
            role='HOSPITAL_ADMIN', permission='users.manage', allowed=False,
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        assert client.post(
            f'/api/v1/auth/users/{target.id}/activate/',
        ).status_code == 403
        assert client.post(
            f'/api/v1/auth/users/{target.id}/deactivate/',
        ).status_code == 403

    def test_self_profile_edit_survives_revocation(self):
        """تعديل المستخدم لملفه الشخصي لا يتأثر بسحب users.manage."""
        doctor = UserFactory(role='DOCTOR')
        client = APIClient()
        client.force_authenticate(user=doctor)
        res = client.patch(
            f'/api/v1/auth/users/{doctor.id}/',
            {'full_name': 'My Own New Name'}, format='json',
        )
        assert res.status_code == 200
        doctor.refresh_from_db()
        assert doctor.full_name == 'My Own New Name'

    def test_audit_view_revocation_blocks_auditor(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        auditor = UserFactory(role='AUDITOR')
        RolePermission.objects.create(
            role='AUDITOR', permission='audit.view', allowed=False,
        )
        client = APIClient()
        client.force_authenticate(user=auditor)
        res = client.get('/api/v1/audit/logs/')
        assert res.status_code == 403

    def test_audit_view_grant_opens_logs_to_new_role(self):
        """منح audit.view لدور جديد (محاسب) يفتح له السجل دون كود."""
        accountant = UserFactory(role='ACCOUNTANT')
        RolePermission.objects.create(
            role='ACCOUNTANT', permission='audit.view', allowed=True,
        )
        client = APIClient()
        client.force_authenticate(user=accountant)
        assert client.get('/api/v1/audit/logs/').status_code == 200

    def test_center_admin_keeps_audit_by_default(self):
        """اتساق رجعي: مدير المركز كان يقرأ التدقيق — الافتراضي يحافظ على ذلك."""
        center_admin = UserFactory(role='CENTER_ADMIN')
        client = APIClient()
        client.force_authenticate(user=center_admin)
        assert client.get('/api/v1/audit/logs/').status_code == 200
