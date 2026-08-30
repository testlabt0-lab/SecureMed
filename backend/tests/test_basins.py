"""
Tests for the Basins (الأحواز الصحية) app.

Covers the plan requirements:
  * «يجب أن ترتبط بالأحواز» — users/patients/channels link to basins
  * «تُفعّل بحسب نوع الأحواز» — modules activate by basin type
"""
import json

import pytest
from django.core.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.basins.models import Basin
from apps.basins.utils import ensure_module_enabled
from tests.factories import (
    AdminUserFactory, BasinFactory, ChannelFactory, HospitalBasinFactory,
    PatientFactory, UserFactory,
)

pytestmark = pytest.mark.django_db


class TestBasinModel:
    """Basin model: default module activation by type."""

    def test_hospital_gets_all_modules_by_default(self):
        basin = HospitalBasinFactory()
        assert set(basin.enabled_modules) == set(Basin.ALL_MODULES)

    def test_health_center_default_modules(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_CENTER)
        assert 'patients' in basin.enabled_modules
        assert 'lab' not in basin.enabled_modules
        assert 'pharmacy' not in basin.enabled_modules

    def test_health_unit_minimal_modules(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_UNIT)
        assert basin.enabled_modules == ['patients', 'channels']

    def test_apply_type_defaults_on_type_change(self):
        basin = HospitalBasinFactory()
        basin.basin_type = Basin.BasinType.HEALTH_UNIT
        basin.apply_default_modules()
        assert basin.enabled_modules == ['patients', 'channels']

    def test_has_module_toggle(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_UNIT)
        assert basin.has_module('patients')
        assert not basin.has_module('lab')
        basin.enable_module('lab')
        assert basin.has_module('lab')
        basin.disable_module('lab')
        assert not basin.has_module('lab')

    def test_enable_unknown_module_raises(self):
        basin = BasinFactory()
        with pytest.raises(Exception):
            basin.enable_module('rocket_launch')

    def test_stats_counts(self):
        basin = BasinFactory()
        admin = AdminUserFactory(basin=basin)
        patient = PatientFactory(basin=basin)
        ChannelFactory(patient=patient, owner=admin, basin=basin)
        stats = basin.stats()
        assert stats['users'] == 1
        assert stats['patients'] == 1
        assert stats['channels'] == 1
        assert stats['active_channels'] == 1


class TestModuleGating:
    """ensure_module_enabled: feature activation per basin type."""

    def test_user_without_basin_passes(self):
        user = UserFactory()  # global user, no basin
        ensure_module_enabled(user, 'lab')  # no exception

    def test_blocked_when_module_disabled(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_UNIT)
        user = UserFactory(basin=basin)
        with pytest.raises(PermissionDenied):
            ensure_module_enabled(user, 'lab')

    def test_allowed_when_module_enabled(self):
        basin = BasinFactory(basin_type=Basin.BasinType.GENERAL_HOSPITAL)
        user = UserFactory(basin=basin)
        ensure_module_enabled(user, 'lab')  # no exception

    def test_inactive_basin_blocks_everything(self):
        basin = BasinFactory(is_active=False)
        user = UserFactory(basin=basin)
        with pytest.raises(PermissionDenied):
            ensure_module_enabled(user, 'patients')


class TestBasinAPI:
    """Basin REST API: RBAC + module toggling."""

    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.client.force_authenticate(user=self.admin)

    def test_list_basins_authenticated(self):
        BasinFactory.create_batch(3)
        res = self.client.get('/api/v1/basins/')
        assert res.status_code == 200
        assert len(res.data['results']) >= 3

    def test_create_basin_admin_only(self):
        payload = {
            'name': 'حوض المستشفى الرئيسي',
            'code': 'THH-001',
            'basin_type': 'GENERAL_HOSPITAL',
            'governorate': 'صنعاء',
        }
        res = self.client.post('/api/v1/basins/', payload, format='json')
        assert res.status_code == 201
        assert res.data['enabled_modules']  # defaults auto-applied

        # Non-admin cannot create
        self.client.force_authenticate(user=UserFactory())
        res = self.client.post('/api/v1/basins/', payload, format='json')
        assert res.status_code == 403

    def test_toggle_module(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_UNIT)
        res = self.client.post(
            f'/api/v1/basins/{basin.id}/toggle_module/',
            {'module': 'lab', 'enabled': True},
            format='json',
        )
        assert res.status_code == 200
        basin.refresh_from_db()
        assert 'lab' in basin.enabled_modules

        res = self.client.post(
            f'/api/v1/basins/{basin.id}/toggle_module/',
            {'module': 'lab', 'enabled': False},
            format='json',
        )
        basin.refresh_from_db()
        assert 'lab' not in basin.enabled_modules

    def test_toggle_unknown_module_400(self):
        basin = BasinFactory()
        res = self.client.post(
            f'/api/v1/basins/{basin.id}/toggle_module/',
            {'module': 'nope', 'enabled': True}, format='json',
        )
        assert res.status_code == 400

    def test_apply_type_defaults_endpoint(self):
        basin = BasinFactory(basin_type=Basin.BasinType.HEALTH_UNIT)
        basin.enable_module('lab')
        res = self.client.post(
            f'/api/v1/basins/{basin.id}/apply_type_defaults/',
            {'basin_type': 'GENERAL_HOSPITAL'}, format='json',
        )
        assert res.status_code == 200
        basin.refresh_from_db()
        assert basin.basin_type == 'GENERAL_HOSPITAL'
        assert set(basin.enabled_modules) == set(Basin.ALL_MODULES)

    def test_my_basin(self):
        basin = BasinFactory()
        user = UserFactory(basin=basin)
        self.client.force_authenticate(user=user)
        res = self.client.get('/api/v1/basins/my_basin/')
        assert res.status_code == 200
        assert res.data['basin']['name'] == basin.name

    def test_overview(self):
        BasinFactory.create_batch(2)
        res = self.client.get('/api/v1/basins/overview/')
        assert res.status_code == 200
        assert res.data['total'] >= 2

    def test_delete_basin_with_users_blocked(self):
        basin = BasinFactory()
        UserFactory(basin=basin)
        res = self.client.delete(f'/api/v1/basins/{basin.id}/')
        assert res.status_code == 403
        assert Basin.objects.filter(id=basin.id).exists()

    def test_modules_catalogue(self):
        res = self.client.get('/api/v1/basins/modules/')
        assert res.status_code == 200
        keys = {m['key'] for m in res.data}
        assert {'patients', 'channels', 'lab', 'ai_assistant'} <= keys


class TestBasinScoping:
    """Data is scoped to the admin's basin."""

    def setup_method(self):
        self.client = APIClient()

    def test_hospital_admin_sees_only_own_basin_users(self):
        basin_a = BasinFactory()
        basin_b = BasinFactory()
        admin = UserFactory(role='HOSPITAL_ADMIN', basin=basin_a)
        in_basin = UserFactory(basin=basin_a)
        other = UserFactory(basin=basin_b)

        self.client.force_authenticate(user=admin)
        res = self.client.get('/api/v1/auth/users/')
        assert res.status_code == 200
        emails = [u['email'] for u in res.data['results']]
        assert in_basin.email in emails
        assert other.email not in emails

    def test_super_admin_sees_all_users(self):
        basin = BasinFactory()
        admin = AdminUserFactory()
        UserFactory(basin=basin)
        self.client.force_authenticate(user=admin)
        res = self.client.get('/api/v1/auth/users/')
        assert res.status_code == 200

    def test_hospital_admin_scoped_patients(self):
        basin_a, basin_b = BasinFactory(), BasinFactory()
        admin = UserFactory(role='HOSPITAL_ADMIN', basin=basin_a)
        p_a = PatientFactory(basin=basin_a)
        p_b = PatientFactory(basin=basin_b)

        self.client.force_authenticate(user=admin)
        res = self.client.get('/api/v1/patients/')
        assert res.status_code == 200
        ids = [p['id'] for p in res.data['results']]
        assert str(p_a.id) in ids
        assert str(p_b.id) not in ids

    def test_basin_query_param_filter(self):
        basin_a, basin_b = BasinFactory(), BasinFactory()
        admin = AdminUserFactory()
        p_a = PatientFactory(basin=basin_a)
        PatientFactory(basin=basin_b)
        self.client.force_authenticate(user=admin)
        res = self.client.get(f'/api/v1/patients/?basin={basin_a.id}')
        assert res.status_code == 200
        ids = [p['id'] for p in res.data['results']]
        assert str(p_a.id) in ids
        assert len(ids) == 1


class TestPatientBasinGating:
    """Creating patients is blocked when the basin disables the module."""

    def test_patient_create_blocked_when_module_disabled(self):
        basin = HospitalBasinFactory()
        basin.disable_module('patients')  # admin fine-tuning
        user = UserFactory(basin=basin)
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post('/api/v1/patients/', {
            'full_name': 'مريض الاختبار',
            'date_of_birth': '1990-01-01',
            'gender': 'M',
        }, format='json')
        assert res.status_code == 403
        assert 'غير مفعّلة' in res.data['detail']

    def test_patient_create_ok_for_hospital_basin(self):
        basin = HospitalBasinFactory()
        user = UserFactory(basin=basin)
        client = APIClient()
        client.force_authenticate(user=user)
        res = client.post('/api/v1/patients/', {
            'full_name': 'مريض المستشفى',
            'date_of_birth': '1990-01-01',
            'gender': 'F',
            'basin': str(basin.id),
        }, format='json')
        assert res.status_code == 201
