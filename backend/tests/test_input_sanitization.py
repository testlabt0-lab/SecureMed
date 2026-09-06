"""Regression tests for apps.security.parsers.SanitizedJSONParser.

The parser used to run bleach over every string in every JSON body, which
HTML-escaped bare ``& < > " '`` in prose and in credentials. It corrupted
clinical text on every write and stored password hashes for a string the user
never typed. These tests pin the two properties that matter: plain text is
passed through byte-for-byte, and markup is still neutralised.
"""
import io
import json

import pytest
from rest_framework.test import APIClient

from apps.security.parsers import SanitizedJSONParser
from tests.factories import UserFactory

LOGIN_URL = '/api/v1/auth/login/'

# Every character bleach escapes, in a password a real person could choose.
AMPERSAND_PASSWORD = 'Qn7&Tz2<Vb9>Kw4"Rj6\'Lp3!'


def _parse(payload):
    stream = io.BytesIO(json.dumps(payload).encode('utf-8'))
    return SanitizedJSONParser().parse(stream)


class TestPlainTextSurvives:
    """Clinical prose is data, not markup. It must come out as it went in."""

    @pytest.mark.parametrize('text', [
        'SpO2 < 90% on room air',
        'Tmax > 38.5 C',
        'Metformin 500mg & Insulin glargine 10u',
        'أعراض: ألم في الصدر < 10 دقائق',
        "Patient's own words: \"I can't breathe\"",
        'BP 190/120 — 5 < x > 3',
    ])
    def test_unchanged(self, text):
        assert _parse({'content': text})['content'] == text

    def test_round_trip_does_not_compound(self):
        # Read-edit-save used to turn & into &amp; then &amp;amp; …
        text = 'Aspirin & Clopidogrel'
        once = _parse({'content': text})['content']
        twice = _parse({'content': once})['content']
        assert once == twice == text

    def test_non_string_values_are_untouched(self):
        payload = {'age': 42, 'weight': 71.5, 'critical': True, 'notes': None}
        assert _parse(payload) == payload

    def test_nested_structures_are_walked(self):
        payload = {'records': [{'content': 'K+ 5.9 & rising'}, {'content': 'a < b'}]}
        assert _parse(payload) == payload


class TestMarkupIsStillRemoved:

    @pytest.mark.parametrize('payload_text', [
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
        '<iframe src="javascript:alert(1)"></iframe>',
        '&#60;script&#62;alert(1)&#60;/script&#62;',
    ])
    def test_dangerous_markup_does_not_survive(self, payload_text):
        cleaned = _parse({'content': payload_text})['content']
        assert '<script' not in cleaned.lower()
        assert '<img' not in cleaned.lower()
        assert '<iframe' not in cleaned.lower()
        assert 'onerror=alert' not in cleaned.replace(' ', '')

    def test_surrounding_text_is_kept(self):
        cleaned = _parse({'content': 'Fever<script>x</script>39C'})['content']
        assert 'Fever' in cleaned and '39C' in cleaned


class TestCredentialsAreNeverRewritten:

    @pytest.mark.parametrize('key', [
        'password', 'new_password', 'confirm_password', 'old_password',
        'token', 'refresh_token', 'mfa_token', 'secret', 'otp', 'totp_code',
        'api_key', 'private_key', 'signature', 'device_fingerprint',
    ])
    def test_opaque_keys_pass_through_verbatim(self, key):
        hostile = '<script>&amp;</script>' + AMPERSAND_PASSWORD
        assert _parse({key: hostile})[key] == hostile

    def test_list_of_credentials_keeps_parent_key_context(self):
        payload = {'recovery_codes': ['a&b', '<c>d']}
        assert _parse(payload) == payload


@pytest.mark.django_db
class TestLoginAcceptsTheCharactersBleachEscapes:
    """End-to-end: the stored hash must match what the user actually typed.

    Before the fix the parser escaped ``&`` on the way in, so the hash on file
    belonged to ``…&amp;…``. API login escaped identically and appeared to work,
    while every non-JSON entry point (createsuperuser, INITIAL_ADMIN_PASSWORD,
    the admin login form) was permanently locked out.
    """

    def test_password_with_escapable_characters_works(self):
        user = UserFactory(email='amp@securemed.test')
        user.set_password(AMPERSAND_PASSWORD)
        user.save(update_fields=['password'])

        res = APIClient().post(
            LOGIN_URL,
            {'email': 'amp@securemed.test', 'password': AMPERSAND_PASSWORD},
            format='json',
        )
        assert res.status_code == 200, res.data
        assert 'tokens' in res.data

    def test_the_escaped_variant_is_rejected(self):
        user = UserFactory(email='amp2@securemed.test')
        user.set_password(AMPERSAND_PASSWORD)
        user.save(update_fields=['password'])

        res = APIClient().post(
            LOGIN_URL,
            {'email': 'amp2@securemed.test',
             'password': AMPERSAND_PASSWORD.replace('&', '&amp;')},
            format='json',
        )
        assert res.status_code in (400, 401)
