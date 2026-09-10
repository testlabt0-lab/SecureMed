"""
Tests for the public web account-deletion path (4-3 §2 — the Play-mandated
route for users who cannot open the app):

- GET privacy/account-deletion/          → the explanation + email form
- POST privacy/account-deletion/submit/  → email a one-time confirm link
- GET privacy/account-deletion/confirm/… → executes the deactivation

Security properties pinned: no user enumeration, one-time links, the
deactivation is soft (PHI chains survive), all sessions die, and both the
request and the completion are audited.
"""
import re

import pytest
from django.core import mail
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from tests.factories import UserFactory

PAGE_URL = '/privacy/account-deletion/'
SUBMIT_URL = '/privacy/account-deletion/submit/'


def _extract_uid_token(email_body: str):
    match = re.search(r'uid=([\w-]+)&token=([\w-]+)', email_body)
    assert match, 'confirm link with uid & token not found in email body'
    return match.group(1), match.group(2)


@pytest.fixture
def client_obj():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory(email='delete-me@securemed.test')


@pytest.mark.django_db
class TestDeletionPage:
    def test_page_renders_anonymously(self, client_obj):
        response = client_obj.get(PAGE_URL)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'حذف الحساب' in content
        assert 'name="email"' in content
        assert 'csrfmiddlewaretoken' in content

    def test_request_with_known_email_sends_confirm_link(self, client_obj, user):
        response = client_obj.post(SUBMIT_URL, {'email': user.email})

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        uid, token = _extract_uid_token(mail.outbox[0].alternatives[0][0])
        assert uid and token
        assert AuditLog.objects.filter(
            user=user, event_type='ACCOUNT_DELETION_REQUESTED'
        ).exists()

    def test_unknown_email_is_not_enumerated(self, client_obj, db):
        response = client_obj.post(SUBMIT_URL, {'email': 'ghost@securemed.test'})

        assert response.status_code == 200
        assert len(mail.outbox) == 0
        assert 'وصلك رابط تأكيد' in response.content.decode('utf-8')

    def test_inactive_email_is_not_enumerated(self, client_obj, db):
        UserFactory(email='gone@securemed.test', is_active=False)

        response = client_obj.post(SUBMIT_URL, {'email': 'gone@securemed.test'})

        assert response.status_code == 200
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestDeletionConfirm:
    def _request_link(self, user):
        client = APIClient()
        client.post(SUBMIT_URL, {'email': user.email})
        return _extract_uid_token(mail.outbox[0].alternatives[0][0])

    def test_confirm_deactivates_ends_sessions_and_audits(self, client_obj, user):
        uid, token = self._request_link(user)

        response = client_obj.get(
            reverse('account-deletion-confirm') + f'?uid={uid}&token={token}'
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_active is False
        assert not User.objects.filter(pk=user.pk).exists() is False  # row survives
        from django.core.cache import cache
        assert cache.get(f'token_denylist:{user.id}') is not None
        assert AuditLog.objects.filter(
            user=user, event_type='USER_DEACTIVATED'
        ).exists()

    def test_confirm_page_renders_after_deletion(self, client_obj, user):
        uid, token = self._request_link(user)

        response = client_obj.get(
            reverse('account-deletion-confirm') + f'?uid={uid}&token={token}'
        )
        content = response.content.decode('utf-8')

        assert 'تم حذف الحساب' in content

    def test_link_is_single_use(self, client_obj, user):
        uid, token = self._request_link(user)
        url = reverse('account-deletion-confirm') + f'?uid={uid}&token={token}'

        first = client_obj.get(url)
        second = client_obj.get(url)

        assert 'تم حذف الحساب' in first.content.decode('utf-8')
        assert 'رابط غير صالح' in second.content.decode('utf-8')

    def test_forged_token_does_not_delete(self, client_obj, user):
        uid, _token = self._request_link(user)

        response = client_obj.get(
            reverse('account-deletion-confirm') + f'?uid={uid}&token=forged'
        )

        user.refresh_from_db()
        assert user.is_active is True
        assert 'رابط غير صالح' in response.content.decode('utf-8')

    def test_malformed_uid_does_not_crash(self, client_obj, db):
        response = client_obj.get(
            reverse('account-deletion-confirm') + '?uid=!!!bad!!!&token=x'
        )

        assert response.status_code == 200
        assert 'رابط غير صالح' in response.content.decode('utf-8')
