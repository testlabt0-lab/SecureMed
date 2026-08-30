"""
Test factories for generating test data.
"""
import factory
from datetime import date
from factory.django import DjangoModelFactory
from apps.accounts.models import User, BiometricProfile
from apps.patients.models import Patient
from apps.channels.models import Channel, ChannelMembership
from apps.basins.models import Basin


class BasinFactory(DjangoModelFactory):
    class Meta:
        model = Basin

    name = factory.Sequence(lambda n: f'الحوض الصحي {n}')
    code = factory.Sequence(lambda n: f'BSN-{n:03d}')
    basin_type = Basin.BasinType.HEALTH_CENTER
    governorate = 'صنعاء'
    is_active = True


class HospitalBasinFactory(BasinFactory):
    basin_type = Basin.BasinType.GENERAL_HOSPITAL


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)

    email = factory.Sequence(lambda n: f'user{n}@securemed.test')
    full_name = factory.Sequence(lambda n: f'Test User {n}')
    role = User.Role.DOCTOR
    phone = '+966500000000'


class AdminUserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = 'admin@securemed.test'
    full_name = 'Admin User'
    role = User.Role.SUPER_ADMIN


class PatientFactory(DjangoModelFactory):
    class Meta:
        model = Patient

    full_name = 'Test Patient'
    national_id = '1234567890'
    phone = '+966500000001'
    date_of_birth = date(1990, 1, 1)
    gender = 'M'
    blood_type = 'O+'
    address = 'Test Address'
    emergency_contact = 'Test Emergency Contact'


class ChannelFactory(DjangoModelFactory):
    class Meta:
        model = Channel

    name = factory.Sequence(lambda n: f'Test Channel {n}')
    description = 'Test channel description'
    channel_type = Channel.ChannelType.OUTPATIENT
    owner = factory.SubFactory(UserFactory)
    patient = factory.SubFactory(PatientFactory)
    status = Channel.Status.ACTIVE
    priority = 'MEDIUM'


class ChannelMembershipFactory(DjangoModelFactory):
    class Meta:
        model = ChannelMembership

    channel = factory.SubFactory(ChannelFactory)
    user = factory.SubFactory(UserFactory)
    role = ChannelMembership.Role.VIEWER
    is_active = True


class BiometricProfileFactory(DjangoModelFactory):
    class Meta:
        model = BiometricProfile

    user = factory.SubFactory(UserFactory)
    device_id = factory.Sequence(lambda n: f'device-{n}')
    device_name = 'Test Device'
    platform = 'ANDROID'
    biometric_hash = 'encrypted_hash_placeholder'
    salt = 'abcdef1234567890'
    is_active = True
