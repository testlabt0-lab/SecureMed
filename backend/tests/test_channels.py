"""
Tests for channels app: visibility, permissions, membership.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.channels.models import Channel, ChannelMembership
from apps.patients.models import Patient
from tests.factories import (
    UserFactory, PatientFactory, ChannelFactory, ChannelMembershipFactory,
)


@pytest.mark.django_db
class TestChannelModel:
    """Tests for Channel model - security requirement #1 (visibility)."""

    def test_can_view_as_owner(self):
        owner = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        assert channel.can_view(owner) is True

    def test_can_view_as_member(self):
        owner = UserFactory()
        member = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        ChannelMembershipFactory(channel=channel, user=member, is_active=True)
        assert channel.can_view(member) is True

    def test_cannot_view_as_non_member(self):
        owner = UserFactory()
        stranger = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)
        assert channel.can_view(stranger) is False

    def test_can_view_as_admin(self):
        admin = UserFactory(role=User.Role.SUPER_ADMIN)
        channel = ChannelFactory()
        assert channel.can_view(admin) is True

    def test_can_manage_as_owner(self):
        owner = UserFactory()
        channel = ChannelFactory(owner=owner)
        assert channel.can_manage(owner) is True

    def test_cannot_manage_as_member(self):
        owner = UserFactory()
        member = UserFactory()
        channel = ChannelFactory(owner=owner)
        ChannelMembershipFactory(channel=channel, user=member, role=ChannelMembership.Role.EDITOR)
        assert channel.can_manage(member) is False

    def test_get_user_role_owner(self):
        owner = UserFactory()
        channel = ChannelFactory(owner=owner)
        assert channel.get_user_role(owner) == ChannelMembership.Role.OWNER

    def test_get_user_role_member(self):
        owner = UserFactory()
        member = UserFactory()
        channel = ChannelFactory(owner=owner)
        ChannelMembershipFactory(channel=channel, user=member, role=ChannelMembership.Role.VIEWER)
        assert channel.get_user_role(member) == ChannelMembership.Role.VIEWER

    def test_get_user_role_none(self):
        owner = UserFactory()
        stranger = UserFactory()
        channel = ChannelFactory(owner=owner)
        assert channel.get_user_role(stranger) is None


@pytest.mark.django_db
class TestChannelMembershipModel:
    """Tests for membership - DV requirement (single role per user per channel)."""

    def test_create_membership(self):
        membership = ChannelMembershipFactory()
        assert membership.pk is not None
        assert membership.is_active is True

    def test_unique_role_per_user_per_channel(self):
        """DV requirement: Each user has exactly ONE role per channel."""
        owner = UserFactory()
        member = UserFactory()
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)

        ChannelMembership.objects.create(
            channel=channel, user=member, role=ChannelMembership.Role.VIEWER
        )

        # Trying to create a second membership for same user/channel should fail
        # Either at validation (ValidationError) or DB (IntegrityError)
        from django.db import IntegrityError, transaction
        from django.core.exceptions import ValidationError
        with pytest.raises((IntegrityError, ValidationError)):
            with transaction.atomic():
                ChannelMembership.objects.create(
                    channel=channel, user=member, role=ChannelMembership.Role.EDITOR
                )

    def test_revoke_membership(self):
        membership = ChannelMembershipFactory()
        membership.revoke()
        assert membership.is_active is False

    def test_change_role(self):
        membership = ChannelMembershipFactory(role=ChannelMembership.Role.VIEWER)
        membership.change_role(ChannelMembership.Role.EDITOR)
        assert membership.role == ChannelMembership.Role.EDITOR

    def test_cannot_change_to_owner(self):
        membership = ChannelMembershipFactory(role=ChannelMembership.Role.VIEWER)
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            membership.change_role(ChannelMembership.Role.OWNER)

    def test_role_permissions_owner(self):
        membership = ChannelMembershipFactory(role=ChannelMembership.Role.OWNER)
        assert membership.has_permission('view') is True
        assert membership.has_permission('manage_members') is True
        assert membership.has_permission('close') is True

    def test_role_permissions_viewer(self):
        membership = ChannelMembershipFactory(role=ChannelMembership.Role.VIEWER)
        assert membership.has_permission('view') is True
        assert membership.has_permission('edit') is False
        assert membership.has_permission('manage_members') is False

    def test_patient_cannot_be_member(self):
        """Patients cannot be channel members (only medical staff)."""
        owner = UserFactory()
        patient_user = UserFactory(role=User.Role.PATIENT)
        patient = PatientFactory()
        channel = ChannelFactory(owner=owner, patient=patient)

        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            ChannelMembership.objects.create(
                channel=channel, user=patient_user, role=ChannelMembership.Role.VIEWER
            )


@pytest.mark.django_db
class TestChannelAPI:
    """Tests for channel API endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.doctor = UserFactory(role=User.Role.DOCTOR)
        self.patient = PatientFactory()
        self.client.force_authenticate(user=self.doctor)

    def test_create_channel(self):
        response = self.client.post('/api/v1/channels/', {
            'name': 'Test Channel API',
            'description': 'Test description',
            'channel_type': 'OUTPATIENT',
            'priority': 'MEDIUM',
            'patient': str(self.patient.id),
        }, format='json')
        assert response.status_code == 201
        assert Channel.objects.filter(name='Test Channel API').exists()

    def test_list_channels_only_visible(self):
        """Security requirement #1: User can only see channels they own or are member of."""
        own_channel = ChannelFactory(owner=self.doctor, patient=self.patient)
        other_doctor = UserFactory(role=User.Role.DOCTOR)
        other_channel = ChannelFactory(owner=other_doctor, patient=self.patient)

        response = self.client.get('/api/v1/channels/')
        assert response.status_code == 200
        # With pagination, response.data is a dict with 'results'
        results = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        channel_ids = [c['id'] for c in results]
        assert str(own_channel.id) in channel_ids
        assert str(other_channel.id) not in channel_ids

    def test_retrieve_channel_as_owner(self):
        channel = ChannelFactory(owner=self.doctor, patient=self.patient)
        response = self.client.get(f'/api/v1/channels/{channel.id}/')
        assert response.status_code == 200
        assert response.data['name'] == channel.name

    def test_retrieve_channel_as_non_member_forbidden(self):
        other_doctor = UserFactory(role=User.Role.DOCTOR)
        channel = ChannelFactory(owner=other_doctor, patient=self.patient)
        response = self.client.get(f'/api/v1/channels/{channel.id}/')
        assert response.status_code == 404  # Not visible = not found

    def test_list_members(self):
        channel = ChannelFactory(owner=self.doctor, patient=self.patient)
        member = UserFactory(role=User.Role.NURSE)
        ChannelMembershipFactory(channel=channel, user=member)

        response = self.client.get(f'/api/v1/channels/{channel.id}/members/')
        assert response.status_code == 200
        assert len(response.data) >= 1


@pytest.mark.django_db
class TestPermissionsAPI:
    """Tests for security requirement #2 (permissions system)."""

    def setup_method(self):
        self.client = APIClient()
        self.owner = UserFactory(role=User.Role.DOCTOR)
        self.member = UserFactory(role=User.Role.NURSE, email='nurse@securemed.test')
        self.patient = PatientFactory()
        self.channel = ChannelFactory(owner=self.owner, patient=self.patient)
        self.client.force_authenticate(user=self.owner)

    def test_grant_permission(self):
        response = self.client.post(f'/api/v1/channels/{self.channel.id}/grant_permission/', {
            'user_email': self.member.email,
            'role': 'VIEWER',
        }, format='json')
        assert response.status_code == 201
        assert ChannelMembership.objects.filter(
            channel=self.channel, user=self.member, role='VIEWER'
        ).exists()

    def test_grant_permission_twice_fails(self):
        """DV: user can only have one role per channel."""
        self.client.post(f'/api/v1/channels/{self.channel.id}/grant_permission/', {
            'user_email': self.member.email,
            'role': 'VIEWER',
        }, format='json')

        response = self.client.post(f'/api/v1/channels/{self.channel.id}/grant_permission/', {
            'user_email': self.member.email,
            'role': 'EDITOR',
        }, format='json')
        assert response.status_code == 400

    def test_modify_permission(self):
        membership = ChannelMembershipFactory(
            channel=self.channel, user=self.member, role=ChannelMembership.Role.VIEWER
        )
        response = self.client.post(f'/api/v1/channels/{self.channel.id}/modify_permission/', {
            'membership_id': str(membership.id),
            'role': 'EDITOR',
        }, format='json')
        assert response.status_code == 200
        membership.refresh_from_db()
        assert membership.role == ChannelMembership.Role.EDITOR

    def test_revoke_permission(self):
        membership = ChannelMembershipFactory(
            channel=self.channel, user=self.member, role=ChannelMembership.Role.VIEWER
        )
        response = self.client.post(f'/api/v1/channels/{self.channel.id}/revoke_permission/', {
            'membership_id': str(membership.id),
        }, format='json')
        assert response.status_code == 200
        membership.refresh_from_db()
        assert membership.is_active is False

    def test_remove_member(self):
        membership = ChannelMembershipFactory(
            channel=self.channel, user=self.member, role=ChannelMembership.Role.VIEWER
        )
        response = self.client.post(f'/api/v1/channels/{self.channel.id}/remove_member/', {
            'membership_id': str(membership.id),
        }, format='json')
        assert response.status_code == 200
        assert not ChannelMembership.objects.filter(id=membership.id).exists()

    def test_cannot_revoke_owner(self):
        # Create OWNER membership explicitly
        membership = ChannelMembershipFactory(
            channel=self.channel, user=self.owner, role=ChannelMembership.Role.OWNER
        )

        response = self.client.post(f'/api/v1/channels/{self.channel.id}/revoke_permission/', {
            'membership_id': str(membership.id),
        }, format='json')
        assert response.status_code == 400

    def test_non_owner_cannot_grant(self):
        """Only owner or admin can manage permissions."""
        self.client.force_authenticate(user=self.member)
        response = self.client.post(f'/api/v1/channels/{self.channel.id}/grant_permission/', {
            'user_email': 'another@securemed.test',
            'role': 'VIEWER',
        }, format='json')
        # Member isn't even a member yet, so they get 404 (not visible)
        assert response.status_code in [403, 404]
