"""
SecureMed Database Seed Script
Populates the database with realistic test data for development and demos.
"""
import os
import sys
import django
from datetime import date, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ.get('DJANGO_SETTINGS_MODULE', 'config.dev_settings'))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/ (project root)
django.setup()

from apps.accounts.models import User
from apps.patients.models import Patient
from apps.channels.models import Channel, ChannelMembership
from apps.patients.models import MedicalRecord
from apps.audit.models import AuditLog
from apps.audit.utils import log_security_event
from apps.basins.models import Basin


def seed_basins():
    """Create demo health basins with type-based module activation."""
    print("🏛️  Creating health basins (الأحواز)...")

    basins_data = [
        ('مستشفى الثورة العام', 'THH-SAN-01', Basin.BasinType.GENERAL_HOSPITAL, 'صنعاء', 'الثورة'),
        ('مستشفى الرازي التخصصي', 'SRH-TAI-01', Basin.BasinType.SPECIALIZED_HOSPITAL, 'تعز', 'المدينة'),
        ('مركز الحصبة الصحي', 'HCH-SAN-05', Basin.BasinType.HEALTH_CENTER, 'صنعاء', 'الحصبة'),
        ('وحدة بني حشيش الصحية', 'HUH-SAN-11', Basin.BasinType.HEALTH_UNIT, 'صنعاء', 'بني حشيش'),
    ]

    created = []
    for name, code, btype, gov, dir_ in basins_data:
        basin, was_created = Basin.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'basin_type': btype,
                'governorate': gov,
                'directorate': dir_,
                'phone': f'+96701{abs(hash(code)) % 1000000:06d}',
            }
        )
        if was_created:
            # module activation by basin type (plan requirement)
            basin.apply_default_modules(save=False)
            basin.save()
            print(f"  ✓ {name} — {basin.get_basin_type_display()} ({len(basin.enabled_modules)} وحدات مفعّلة)")
            created.append(basin)
        else:
            print(f"  - Already exists: {name}")
            created.append(basin)
    return created


def link_demo_data_to_basins(basins):
    """Link existing demo users/patients/channels to basins."""
    if not basins:
        return
    print("\n🔗 Linking users/patients/channels to basins...")
    main = basins[0]
    secondary = basins[min(1, len(basins) - 1)]

    users = User.objects.filter(basin__isnull=True)
    for i, u in enumerate(users):
        u.basin = main if i % 2 == 0 else secondary
        u.save(update_fields=['basin'])
    print(f"  ✓ {users.count()} users linked")

    patients = Patient.objects.filter(basin__isnull=True)
    for i, p in enumerate(patients):
        p.basin = main if i % 2 == 0 else secondary
        p.save(update_fields=['basin'])
    print(f"  ✓ {patients.count()} patients linked")

    channels = Channel.objects.filter(basin__isnull=True)
    for c in channels:
        c.basin = c.patient.basin or main
        c.save(update_fields=['basin'])
    print(f"  ✓ {channels.count()} channels linked")


def seed_users():
    """Create test users with different roles."""
    print("👥 Creating users...")

    users_data = [
        ('admin@securemed.app', 'System Admin', User.Role.SUPER_ADMIN, 'Admin@2026!'),
        ('doctor.ahmed@securemed.app', 'Dr. Ahmed Al-Saud', User.Role.DOCTOR, 'Doctor@2026!', 'Cardiology'),
        ('doctor.fatima@securemed.app', 'Dr. Fatima Al-Qahtani', User.Role.DOCTOR, 'Doctor@2026!', 'Neurology'),
        ('doctor.mohammed@securemed.app', 'Dr. Mohammed Al-Rashid', User.Role.DOCTOR, 'Doctor@2026!', 'Pediatrics'),
        ('nurse.sara@securemed.app', 'Nurse Sara Al-Otaibi', User.Role.NURSE, 'Nurse@2026!', 'ICU'),
        ('nurse.layla@securemed.app', 'Nurse Layla Al-Harbi', User.Role.NURSE, 'Nurse@2026!', 'Emergency'),
        ('lab.khalid@securemed.app', 'Lab Tech Khalid Al-Zahra', User.Role.LAB_TECH, 'Lab@2026!', 'Laboratory'),
        ('pharm.nora@securemed.app', 'Pharmacist Nora Al-Mutairi', User.Role.PHARMACIST, 'Pharm@2026!', 'Pharmacy'),
        ('auditor.ali@securemed.app', 'Auditor Ali Al-Dossari', User.Role.AUDITOR, 'Audit@2026!'),
        ('hospital.admin@securemed.app', 'Hospital Admin', User.Role.HOSPITAL_ADMIN, 'HAdmin@2026!'),
    ]

    created = []
    for email, full_name, role, password, dept in [(*u, '') if len(u) == 4 else u for u in users_data]:
        user, was_created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': full_name,
                'role': role,
                'department': dept,
                'phone': f'+9665{hash(email) % 100000000:08d}',
                'license_number': f'LIC-{hash(email) % 100000:05d}' if role in ['DOCTOR', 'NURSE', 'LAB_TECH', 'PHARMACIST'] else '',
            }
        )
        if was_created:
            user.set_password(password)
            user.save()
            created.append(user)
            print(f"  ✓ {role}: {full_name} ({email})")
        else:
            print(f"  - Already exists: {email}")
    return created


def seed_patients():
    """Create test patients with encrypted PII."""
    print("\n🏥 Creating patients...")

    patients_data = [
        ('Ahmed Mohammed Al-Ghamdi', date(1985, 3, 15), 'M', 'O+', 'Asthma', '+966501234567'),
        ('Fatima Saleh Al-Malki', date(1990, 7, 22), 'F', 'A+', 'Diabetes Type 2', '+966502345678'),
        ('Mohammed Ali Al-Subaie', date(1978, 11, 5), 'M', 'B-', 'Hypertension', '+966503456789'),
        ('Nora Abdullah Al-Dosari', date(1995, 2, 18), 'F', 'AB+', 'Migraine', '+966504567890'),
        ('Khalid Saeed Al-Otaibi', date(1970, 9, 30), 'M', 'O-', 'Heart Disease', '+966505678901'),
        ('Sara Mansour Al-Qahtani', date(2000, 5, 12), 'F', 'A-', 'Allergies (Penicillin)', '+966506789012'),
        ('Abdulrahman Nasser Al-Harbi', date(1982, 12, 8), 'M', 'B+', 'Arthritis', '+966507890123'),
        ('Layla Hassan Al-Zahrani', date(1988, 4, 25), 'F', 'AB-', 'Thyroid Disorder', '+966508901234'),
    ]

    created = []
    for name, dob, gender, blood, conditions, phone in patients_data:
        from apps.security.crypto import encrypt_field
        patient, was_created = Patient.objects.get_or_create(
            _national_id=encrypt_field(f'{hash(name) % 10**10:010d}'),
            defaults={
                'full_name': name,
                'date_of_birth': dob,
                'gender': gender,
                'blood_type': blood,
                'chronic_conditions': conditions,
                'national_id': f'{hash(name) % 10**10:010d}',
                'address': 'Riyadh, Saudi Arabia',
                'emergency_contact': f'Family Member - +9665{hash(name) % 100000000:08d}',
            }
        )
        if was_created:
            created.append(patient)
            print(f"  ✓ {name} ({blood}, {conditions})")
        else:
            print(f"  - Already exists: {name}")
    return created


def seed_channels(users, patients):
    """Create test channels (patient cases) with memberships."""
    print("\n📋 Creating channels...")

    doctor1 = User.objects.get(email='doctor.ahmed@securemed.app')
    doctor2 = User.objects.get(email='doctor.fatima@securemed.app')
    doctor3 = User.objects.get(email='doctor.mohammed@securemed.app')
    nurse1 = User.objects.get(email='nurse.sara@securemed.app')
    nurse2 = User.objects.get(email='nurse.layla@securemed.app')
    lab_tech = User.objects.get(email='lab.khalid@securemed.app')
    pharmacist = User.objects.get(email='pharm.nora@securemed.app')

    channels_data = [
        {
            'name': 'Case: Ahmed Al-Ghamdi - Cardiac Follow-up',
            'desc': 'Routine cardiac checkup for hypertension patient',
            'type': Channel.ChannelType.FOLLOW_UP,
            'priority': 'MEDIUM',
            'patient': patients[0],
            'owner': doctor1,
            'members': [
                (nurse1, ChannelMembership.Role.CONTRIBUTOR),
                (lab_tech, ChannelMembership.Role.VIEWER),
            ],
        },
        {
            'name': 'Case: Fatima Al-Malki - Diabetes Management',
            'desc': 'Diabetes Type 2 management and monitoring',
            'type': Channel.ChannelType.OUTPATIENT,
            'priority': 'HIGH',
            'patient': patients[1],
            'owner': doctor1,
            'members': [
                (nurse1, ChannelMembership.Role.EDITOR),
                (pharmacist, ChannelMembership.Role.CONTRIBUTOR),
            ],
        },
        {
            'name': 'Case: Mohammed Al-Subaie - Emergency Admission',
            'desc': 'Emergency admission for hypertensive crisis',
            'type': Channel.ChannelType.EMERGENCY,
            'priority': 'URGENT',
            'patient': patients[2],
            'owner': doctor2,
            'members': [
                (nurse2, ChannelMembership.Role.EDITOR),
                (lab_tech, ChannelMembership.Role.CONTRIBUTOR),
            ],
        },
        {
            'name': 'Case: Nora Al-Dosari - Neurological Consultation',
            'desc': 'Chronic migraine consultation',
            'type': Channel.ChannelType.CONSULTATION,
            'priority': 'MEDIUM',
            'patient': patients[3],
            'owner': doctor2,
            'members': [
                (nurse1, ChannelMembership.Role.VIEWER),
            ],
        },
        {
            'name': 'Case: Khalid Al-Otaibi - Pediatric Care',
            'desc': 'Pediatric checkup for heart condition',
            'type': Channel.ChannelType.INPATIENT,
            'priority': 'HIGH',
            'patient': patients[4],
            'owner': doctor3,
            'members': [
                (nurse2, ChannelMembership.Role.EDITOR),
                (pharmacist, ChannelMembership.Role.VIEWER),
            ],
        },
    ]

    created = []
    for ch_data in channels_data:
        channel, was_created = Channel.objects.get_or_create(
            name=ch_data['name'],
            defaults={
                'description': ch_data['desc'],
                'channel_type': ch_data['type'],
                'priority': ch_data['priority'],
                'patient': ch_data['patient'],
                'owner': ch_data['owner'],
            }
        )
        if was_created:
            # Create owner membership
            ChannelMembership.objects.get_or_create(
                channel=channel,
                user=ch_data['owner'],
                defaults={
                    'role': ChannelMembership.Role.OWNER,
                    'granted_by': ch_data['owner'],
                }
            )
            # Create member memberships
            for member_user, member_role in ch_data['members']:
                ChannelMembership.objects.get_or_create(
                    channel=channel,
                    user=member_user,
                    defaults={
                        'role': member_role,
                        'granted_by': ch_data['owner'],
                    }
                )
            created.append(channel)
            print(f"  ✓ {ch_data['name']}")
        else:
            print(f"  - Already exists: {ch_data['name']}")
    return created


def seed_medical_records(channels):
    """Create medical records for channels."""
    print("\n📝 Creating medical records...")

    doctor1 = User.objects.get(email='doctor.ahmed@securemed.app')
    doctor2 = User.objects.get(email='doctor.fatima@securemed.app')
    doctor3 = User.objects.get(email='doctor.mohammed@securemed.app')
    nurse1 = User.objects.get(email='nurse.sara@securemed.app')
    nurse2 = User.objects.get(email='nurse.layla@securemed.app')
    lab_tech = User.objects.get(email='lab.khalid@securemed.app')

    records_data = [
        {
            'channel_idx': 0,
            'type': MedicalRecord.RecordType.DIAGNOSIS,
            'title': 'Primary Diagnosis: Hypertension Stage 2',
            'content': 'Patient presents with elevated blood pressure (160/100 mmHg). Recommending lifestyle changes and medication.',
            'created_by': doctor1,
            'critical': False,
            'vitals': {'bp_sys': 160, 'bp_dia': 100, 'hr': 88, 'temp': 37.0, 'rr': 18, 'spo2': 98},
        },
        {
            'channel_idx': 0,
            'type': MedicalRecord.RecordType.PRESCRIPTION,
            'title': 'Prescription: Lisinopril 10mg',
            'content': 'Lisinopril 10mg once daily. Monitor kidney function. Follow-up in 2 weeks.',
            'created_by': doctor1,
            'critical': False,
        },
        {
            'channel_idx': 0,
            'type': MedicalRecord.RecordType.VITALS,
            'title': 'Vital Signs - Day 1',
            'content': 'Routine vital signs monitoring. BP slightly elevated, will adjust medication.',
            'created_by': nurse1,
            'critical': False,
            'vitals': {'bp_sys': 150, 'bp_dia': 95, 'hr': 82, 'temp': 36.8, 'rr': 16, 'spo2': 99},
        },
        {
            'channel_idx': 1,
            'type': MedicalRecord.RecordType.DIAGNOSIS,
            'title': 'Diabetes Type 2 - Initial Assessment',
            'content': 'HbA1c: 8.5%. Fasting glucose: 180 mg/dL. Recommending Metformin and diet plan.',
            'created_by': doctor1,
            'critical': False,
        },
        {
            'channel_idx': 1,
            'type': MedicalRecord.RecordType.LAB_ORDER,
            'title': 'Lab Order: HbA1c + Lipid Panel',
            'content': 'Order complete blood count, HbA1c, lipid panel, and kidney function tests.',
            'created_by': doctor1,
            'critical': False,
        },
        {
            'channel_idx': 1,
            'type': MedicalRecord.RecordType.LAB_RESULT,
            'title': 'Lab Results - HbA1c: 7.8%',
            'content': 'HbA1c improved to 7.8% (was 8.5%). Continue current treatment plan.',
            'created_by': lab_tech,
            'critical': False,
        },
        {
            'channel_idx': 2,
            'type': MedicalRecord.RecordType.DIAGNOSIS,
            'title': 'EMERGENCY: Hypertensive Crisis',
            'content': 'Patient admitted with BP 200/120 mmHg. Administering IV medication. ICU monitoring required.',
            'created_by': doctor2,
            'critical': True,
            'vitals': {'bp_sys': 200, 'bp_dia': 120, 'hr': 110, 'temp': 37.5, 'rr': 22, 'spo2': 95},
        },
        {
            'channel_idx': 2,
            'type': MedicalRecord.RecordType.VITALS,
            'title': 'ICU Monitoring - Hour 1',
            'content': 'BP stabilizing after treatment: 175/105. Continue monitoring.',
            'created_by': nurse2,
            'critical': True,
            'vitals': {'bp_sys': 175, 'bp_dia': 105, 'hr': 95, 'temp': 37.2, 'rr': 20, 'spo2': 97},
        },
        {
            'channel_idx': 3,
            'type': MedicalRecord.RecordType.DIAGNOSIS,
            'title': 'Chronic Migraine - Neurological Assessment',
            'content': 'Patient reports 3-4 migraines per month. Recommending prophylactic treatment.',
            'created_by': doctor2,
            'critical': False,
        },
        {
            'channel_idx': 4,
            'type': MedicalRecord.RecordType.NOTES,
            'title': 'Pediatric Assessment Notes',
            'content': 'Child showing improvement. Heart function stable. Continue current medication.',
            'created_by': doctor3,
            'critical': False,
            'vitals': {'bp_sys': 110, 'bp_dia': 70, 'hr': 95, 'temp': 36.9, 'rr': 20, 'spo2': 99},
        },
    ]

    created = 0
    for rec_data in records_data:
        if rec_data['channel_idx'] >= len(channels):
            continue
        channel = channels[rec_data['channel_idx']]
        record, was_created = MedicalRecord.objects.get_or_create(
            channel=channel,
            title=rec_data['title'],
            defaults={
                'record_type': rec_data['type'],
                'content': rec_data['content'],
                'created_by': rec_data['created_by'],
                'is_critical': rec_data.get('critical', False),
                'blood_pressure_systolic': rec_data.get('vitals', {}).get('bp_sys'),
                'blood_pressure_diastolic': rec_data.get('vitals', {}).get('bp_dia'),
                'heart_rate': rec_data.get('vitals', {}).get('hr'),
                'temperature': rec_data.get('vitals', {}).get('temp'),
                'respiratory_rate': rec_data.get('vitals', {}).get('rr'),
                'oxygen_saturation': rec_data.get('vitals', {}).get('spo2'),
            }
        )
        if was_created:
            created += 1
            print(f"  ✓ {rec_data['title']}")
    print(f"\n  Total records created: {created}")
    return created


def seed_appointments(users, patients):
    """Create sample appointments for demo."""
    from apps.appointments.models import Appointment, AppointmentSlot
    print("\n📅 Creating sample appointments...")
    if not users or not patients:
        return

    doctors = [u for u in users if u.role == User.Role.DOCTOR]
    if not doctors:
        doctors = list(User.objects.filter(role=User.Role.DOCTOR))
    if not doctors:
        return

    now = timezone.now()
    demo_appts = [
        ('كشف واستشارة قلبية', doctors[0], patients[0], now + timedelta(hours=2), 30, 'INITIAL', 'HIGH', 'عيادة القلب', '201'),
        ('متابعة سكري وفحوصات', doctors[min(1, len(doctors)-1)], patients[min(1, len(patients)-1)], now + timedelta(days=1, hours=4), 45, 'FOLLOW_UP', 'MEDIUM', 'عيادة الباطنية', '105'),
        ('استشارة عصبية عاجلة', doctors[min(1, len(doctors)-1)], patients[min(2, len(patients)-1)], now + timedelta(days=2, hours=1), 30, 'CONSULTATION', 'URGENT', '', '', True, 'https://meet.securemed.app/room-neuro-101'),
        ('فحص دوري للأطفال', doctors[min(2, len(doctors)-1)], patients[min(3, len(patients)-1)], now + timedelta(days=3, hours=3), 30, 'ROUTINE', 'LOW', 'عيادة الأطفال', '302'),
    ]

    created = 0
    for title, doc, pat, sched, dur, atype, prio, loc, rm, *extra in demo_appts:
        is_virt = extra[0] if extra else False
        vlink = extra[1] if len(extra) > 1 else ''
        appt, was_created = Appointment.objects.get_or_create(
            title=title,
            doctor=doc,
            patient=pat,
            defaults={
                'scheduled_at': sched,
                'duration_minutes': dur,
                'appointment_type': atype,
                'priority': prio,
                'location': loc,
                'room_number': rm,
                'is_virtual': is_virt,
                'virtual_link': vlink,
                'status': 'CONFIRMED' if prio == 'HIGH' else 'SCHEDULED',
            }
        )
        if was_created:
            created += 1
            print(f"  ✓ {title} ({doc.full_name} ➔ {pat.full_name})")

    # Also seed doctor slots
    for doc in doctors:
        for day in [0, 1, 2, 3, 4]:  # Sun-Thu
            AppointmentSlot.objects.get_or_create(
                doctor=doc,
                day_of_week=day,
                start_time='09:00:00',
                end_time='16:00:00',
                defaults={'slot_duration_minutes': 30, 'is_active': True}
            )
    print(f"  Total appointments created: {created}")


def main():
    print("=" * 60)
    print("  SecureMed Database Seed Script")
    print("=" * 60)

    users = seed_users()
    basins = seed_basins()
    patients = seed_patients()
    channels = seed_channels(users, patients)
    seed_medical_records(channels)
    link_demo_data_to_basins(basins)
    seed_appointments(users, patients)

    # Log the seed event
    admin = User.objects.filter(role=User.Role.SUPER_ADMIN).first()
    if admin:
        log_security_event(
            user=admin,
            event_type='CHANNEL_CREATED',
            details={'message': 'Database seeded with test data'}
        )

    print("\n" + "=" * 60)
    print("✅ Database seeded successfully!")
    print("=" * 60)
    print("\n📊 Summary:")
    print(f"  Users:        {User.objects.count()}")
    print(f"  Patients:     {Patient.objects.count()}")
    print(f"  Channels:     {Channel.objects.count()}")
    print(f"  Appointments: {Appointment.objects.count() if 'Appointment' in locals() else 0}")
    print(f"  Members:      {ChannelMembership.objects.count()}")
    print(f"  Records:      {MedicalRecord.objects.count()}")
    print(f"\n🔑 Login credentials:")
    print("  Admin:    admin@securemed.app / Admin@2026!")
    print("  Doctor:   doctor.ahmed@securemed.app / Doctor@2026!")
    print("  Nurse:    nurse.sara@securemed.app / Nurse@2026!")



if __name__ == '__main__':
    main()
