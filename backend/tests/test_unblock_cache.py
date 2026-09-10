"""
Tests for unblock cache invalidation.

Blocking caches a positive decision (WAF: waf_device_blacklist / waf_blacklist,
tracker: blocked_device:{fp}:{mac}); "unblock" flipped the DB row but left the
cached verdicts standing, so an unblocked device/IP kept being refused for the
original block's TTL.
"""
import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.security.models import BlockedDevice, BlockedIP
from tests.factories import AdminUserFactory

pytestmark = pytest.mark.django_db


class TestUnblockCacheInvalidation:
    def test_device_unblock_invalidates_waf_and_tracker_caches(self):
        device = BlockedDevice.objects.create(
            device_fingerprint='AND-unblock-1',
            mac_address='AA:00:00:00:00:01',
            reason='test',
        )
        cache.set('waf_device_blacklist:AND-unblock-1', True, 600)
        cache.set('blocked_device:AND-unblock-1:AA:00:00:00:00:01', True, 600)

        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'/api/v1/security/blocked-devices/{device.id}/unblock/')
        assert res.status_code == 200

        assert cache.get('waf_device_blacklist:AND-unblock-1') is None
        assert cache.get(
            'blocked_device:AND-unblock-1:AA:00:00:00:00:01'
        ) is None

    def test_ip_unblock_invalidates_waf_cache(self):
        blocked = BlockedIP.objects.create(ip_address='203.0.113.99')
        cache.set('waf_blacklist:203.0.113.99', True, 600)

        admin = AdminUserFactory()
        client = APIClient()
        client.force_authenticate(user=admin)
        res = client.post(f'/api/v1/security/blocked-ips/{blocked.id}/unblock/')
        assert res.status_code == 200

        assert cache.get('waf_blacklist:203.0.113.99') is None

    def test_blocklist_is_non_enforcing_after_unblock(self):
        """The DB side too: enforceable() must stop matching the unblocked row."""
        device = BlockedDevice.objects.create(
            device_fingerprint='AND-unblock-2', reason='test',
        )
        assert BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-unblock-2'
        ).exists()
        device.is_active = False
        device.save(update_fields=['is_active'])
        assert not BlockedDevice.objects.enforceable().filter(
            device_fingerprint='AND-unblock-2'
        ).exists()
