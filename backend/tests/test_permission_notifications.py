"""
Tests for permission-change notifications.

PERMISSION_GRANTED / PERMISSION_REVOKED existed as notification types in the
notifications model, but nothing ever sent them: a grant or revoke reached the
audit log only, and the affected user learned their access changed by bumping
into a 403.
"""
import pytest
from unittest import mock

from apps.notifications.models import Notification
from apps.accounts.models import User
from tests.factories import AdminUserFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestPermissionNotifications:
    def test_grant_notifies_target_user(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        admin = AdminUserFactory()
        target = UserFactory()

        from django.contrib.auth.models import Permission
        perm = Permission.objects.filter(
            content_type__app_label='accounts'
        ).first() or Permission.objects.first()
        assert perm is not None

        client = pytest.importorskip('rest_framework.test').APIClient()
        client.force_authenticate(user=admin)
        res = client.post(
            f'/api/v1/auth/users/{target.id}/grant-permission/',
            {'permission': perm.codename}, format='json',
        )
        assert res.status_code == 200

        notif = Notification.objects.filter(
            recipient=target, notification_type='PERMISSION_GRANTED',
        ).first()
        assert notif is not None
        assert perm.codename in notif.message

    def test_revoke_notifies_target_user(self, settings):
        settings.AUDIT_LOG_ASYNC = False
        admin = AdminUserFactory()
        target = UserFactory()

        from django.contrib.auth.models import Permission
        perm = Permission.objects.filter(
            content_type__app_label='accounts'
        ).first() or Permission.objects.first()
        assert perm is not None
        target.user_permissions.add(perm)

        client = pytest.importorskip('rest_framework.test').APIClient()
        client.force_authenticate(user=admin)
        res = client.post(
            f'/api/v1/auth/users/{target.id}/revoke-permission/',
            {'permission': perm.codename}, format='json',
        )
        assert res.status_code == 200

        notif = Notification.objects.filter(
            recipient=target, notification_type='PERMISSION_REVOKED',
        ).first()
        assert notif is not None
        assert perm.codename in notif.message

    def test_non_admin_cannot_grant(self, settings):
        user = UserFactory()
        target = UserFactory()
        client = pytest.importorskip('rest_framework.test').APIClient()
        client.force_authenticate(user=user)
        res = client.post(
            f'/api/v1/auth/users/{target.id}/grant-permission/',
            {'permission': 'any'}, format='json',
        )
        assert res.status_code == 403
