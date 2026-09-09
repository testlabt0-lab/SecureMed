"""
Tests for the Backups (النسخ الاحتياطي) app.

Dev requirement: «تتضمن آلية للنسخ الاحتياطي»
"""
import base64
import hashlib
import io
import json
import os
import unittest.mock as mock
import zipfile

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.backups.models import BackupRecord
from apps.backups.services import (
    _get_decrypted_backup, create_backup, restore_backup, verify_backup,
)
from apps.patients.models import Patient
from tests.factories import AdminUserFactory, PatientFactory, UserFactory

pytestmark = pytest.mark.django_db


class TestBackupService:
    def test_create_backup_creates_zip_and_record(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(3)
        PatientFactory.create_batch(2)

        record = create_backup()
        assert os.path.exists(record.filepath)
        assert record.filename.startswith('securemed_backup_')
        assert record.filename.endswith('.zip')
        assert record.size_bytes > 0
        assert len(record.checksum) == 64
        assert record.row_counts.get('accounts.User', 0) >= 3

        # The archive at rest is Fernet-encrypted (backup encryption
        # requirement); verify through the same decryption path production
        # reads use, which also asserts the file is *not* plain zip anymore.
        with open(record.filepath, 'rb') as fh:
            assert not fh.read(4).startswith(b'PK\x03\x04')
        with zipfile.ZipFile(_get_decrypted_backup(record.filepath)) as zf:
            names = zf.namelist()
            assert 'db.json' in names
            assert 'manifest.json' in names
            data = json.loads(zf.read('db.json').decode('utf-8'))
            labels = {obj['model'] for obj in data}
            assert 'accounts.user' in labels
            assert 'patients.patient' in labels
            # transient tables are excluded
            assert 'sessions.session' not in labels

    def test_verify_backup_detects_tampering(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup()
        manifest = verify_backup(record.filepath)
        assert manifest['checksum_sha256'] == record.checksum

        # Tamper with the archive → verification must fail. The stored archive
        # is encrypted, so the tampered copy is built from the decrypted
        # payload and then re-encrypted with the same key.
        with zipfile.ZipFile(_get_decrypted_backup(record.filepath)) as zf:
            db_json = zf.read('db.json')
        tampered_plain = tmp_path / 'tampered_plain.zip'
        with zipfile.ZipFile(tampered_plain, 'w') as zf:
            zf.writestr('db.json', db_json + b'[]')
            zf.writestr('manifest.json', '{"checksum_sha256": "%s"}' % ('0' * 64))
        tampered = tmp_path / 'tampered.zip'
        from cryptography.fernet import Fernet
        import hashlib
        secret = settings.BACKUP_ENCRYPTION_KEY or settings.SECRET_KEY
        fkey = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        tampered.write_bytes(Fernet(fkey).encrypt(tampered_plain.read_bytes()))
        with pytest.raises(ValueError):
            verify_backup(str(tampered))

    def test_retention_keeps_newest_n(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        settings.BACKUP_KEEP_COUNT = 3
        for _ in range(5):
            create_backup()
        assert BackupRecord.objects.count() == 3
        files = list(tmp_path.joinpath('backups').glob('*.zip'))
        assert len(files) == 3

    def test_restore_roundtrip(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        patient = PatientFactory(full_name='مريض النسخ')
        record = create_backup()

        # Delete everything, then restore
        User.objects.all().delete()
        Patient.objects.all().delete()
        assert User.objects.count() == 0

        result = restore_backup(record.filepath, force=True)
        assert result['restored'] is True
        assert result['scope'] == 'FULL'
        assert User.objects.count() >= 2
        assert Patient.objects.filter(id=patient.id).exists()


class TestBackupScopes:
    """فصل النسخ الاحتياطي: قاعدة البيانات وحدها / الملفات وحدها / كامل."""

    def test_database_scope_archive_has_no_media(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        record = create_backup(scope=BackupRecord.Scope.DATABASE)
        assert record.scope == BackupRecord.Scope.DATABASE
        assert record.filename.startswith('securemed_backup_db_')

        with zipfile.ZipFile(_get_decrypted_backup(record.filepath)) as zf:
            names = zf.namelist()
            assert 'db.json' in names
            assert not any(n.startswith('media/') for n in names)
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
            assert manifest['scope'] == 'DATABASE'

    def test_media_scope_archive_has_no_db(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup(scope=BackupRecord.Scope.MEDIA)
        assert record.scope == BackupRecord.Scope.MEDIA

        with zipfile.ZipFile(_get_decrypted_backup(record.filepath)) as zf:
            names = zf.namelist()
            assert 'db.json' not in names
            assert 'manifest.json' in names
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
            assert manifest['scope'] == 'MEDIA'

    def test_invalid_scope_rejected(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        with pytest.raises(ValueError):
            create_backup(scope='EVERYTHING')

    def test_verify_and_restore_per_scope(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        PatientFactory(full_name='مريض النطاقات')
        PatientFactory(full_name='مريض ثانٍ')

        db_record = create_backup(scope=BackupRecord.Scope.DATABASE)
        media_record = create_backup(scope=BackupRecord.Scope.MEDIA)

        # Both scopes verify cleanly
        assert verify_backup(db_record.filepath)['scope'] == 'DATABASE'
        assert verify_backup(media_record.filepath)['scope'] == 'MEDIA'

        # DATABASE restore flushes and refills the DB
        User.objects.all().delete()
        Patient.objects.all().delete()
        result = restore_backup(db_record.filepath, force=True)
        assert result['scope'] == 'DATABASE'
        assert Patient.objects.count() == 2

        # MEDIA restore touches files only — the DB rows stay intact
        users_before = User.objects.count()
        result = restore_backup(media_record.filepath, force=True)
        assert result['scope'] == 'MEDIA'
        assert User.objects.count() == users_before
        assert Patient.objects.count() == 2

    def test_retention_is_per_scope(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        settings.BACKUP_KEEP_COUNT = 2
        for _ in range(3):
            create_backup(scope=BackupRecord.Scope.DATABASE)
        create_backup(scope=BackupRecord.Scope.FULL)
        # 2 db-scope kept (retention), 1 full kept — the full one is not
        # evicted by the burst of database-scoped backups
        assert (
            BackupRecord.objects.filter(scope=BackupRecord.Scope.DATABASE).count() == 2
        )
        assert BackupRecord.objects.filter(scope=BackupRecord.Scope.FULL).count() == 1

    def test_scope_via_api(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        client = APIClient()
        admin = AdminUserFactory()
        client.force_authenticate(user=admin)

        res = client.post(
            '/api/v1/backups/create_backup_action/',
            {'note': 'قاعدة فقط', 'scope': 'DATABASE'}, format='json',
        )
        assert res.status_code == 201
        assert res.data['scope'] == 'DATABASE'
        assert res.data['scope_display'] == 'قاعدة البيانات فقط'

        # unknown scope refused
        res = client.post(
            '/api/v1/backups/create_backup_action/',
            {'scope': 'EVERYTHING'}, format='json',
        )
        assert res.status_code == 400


class TestRestoreSafetyNet:
    """نسخة الأمان قبل الاستعادة — خطأ الاستعادة لا يصبح نهائياً."""

    def test_restore_creates_safety_backup_first(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        PatientFactory(full_name='مريض قبل الأمان')

        record = create_backup()
        User.objects.all().delete()
        Patient.objects.all().delete()

        result = restore_backup(record.filepath, force=True)
        # a full safety archive was snapshotted before the flush
        assert result['safety_backup']
        safety = BackupRecord.objects.get(filename=result['safety_backup'])
        assert safety.scope == BackupRecord.Scope.FULL
        assert safety.note == 'أمان تلقائي قبل الاستعادة'

    def test_safety_backup_failure_aborts_restore(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        record = create_backup()
        users_before = User.objects.count()

        with mock.patch(
            'apps.backups.services.create_backup',
            side_effect=RuntimeError('disk full — no safety copy possible'),
        ):
            with pytest.raises(RuntimeError):
                restore_backup(record.filepath, force=True)
        # the live data was NOT flushed — a failed safety net stops the knife
        assert User.objects.count() == users_before

    def test_media_restore_takes_no_safety_backup(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup(scope=BackupRecord.Scope.MEDIA)
        count_before = BackupRecord.objects.count()
        result = restore_backup(record.filepath, force=True)
        # media restore never touches the DB → no safety copy needed
        assert result['safety_backup'] is None
        assert BackupRecord.objects.count() == count_before

    def test_restore_sends_telegram_alert(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        UserFactory.create_batch(2)
        record = create_backup()
        client = APIClient()
        admin = AdminUserFactory()
        client.force_authenticate(user=admin)
        with mock.patch(
            'apps.security.telegram_service.send_critical_alert',
            return_value=True,
        ) as alert:
            res = client.post(
                f'/api/v1/backups/{record.id}/restore/',
                {'force': True}, format='json',
            )
        assert res.status_code == 200
        alert.assert_called_once()
        assert 'استعادة' in alert.call_args.args[0]


class TestBackupCommands:
    def test_create_backup_command(self, tmp_path, settings, capsys):
        settings.BACKUP_DIR = tmp_path / 'backups'
        call_command('create_backup', '--note', 'اختبار')
        out = capsys.readouterr().out
        assert 'تم إنشاء النسخة الاحتياطية' in out
        assert BackupRecord.objects.count() == 1

    def test_restore_backup_plan_mode(self, tmp_path, settings, capsys):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup()
        # Without --force: verify only (data untouched)
        call_command('restore_backup', record.filepath)
        out = capsys.readouterr().out
        assert 'الأرشيف سليم' in out


class TestBackupAPI:
    def setup_method(self):
        self.client = APIClient()
        self.admin = AdminUserFactory()
        self.client.force_authenticate(user=self.admin)

    def test_backup_endpoints_admin_only(self):
        # Anonymous → 401
        client = APIClient()
        assert client.get('/api/v1/backups/').status_code == 401
        # Regular user → 403
        client.force_authenticate(user=UserFactory())
        assert client.get('/api/v1/backups/').status_code == 403

    def test_create_and_download_backup_via_api(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        res = self.client.post(
            '/api/v1/backups/create_backup_action/',
            {'note': 'نسخة من الواجهة'}, format='json',
        )
        assert res.status_code == 201
        backup_id = res.data['id']

        # List shows it
        res = self.client.get('/api/v1/backups/')
        assert res.status_code == 200
        assert len(res.data['results']) == 1

        # Download
        res = self.client.get(f'/api/v1/backups/{backup_id}/download/')
        assert res.status_code == 200
        content = b''.join(res.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            assert 'db.json' in zf.namelist()

        # Verify endpoint
        res = self.client.get(f'/api/v1/backups/{backup_id}/verify/')
        assert res.status_code == 200
        assert res.data['valid'] is True

    def test_delete_backup(self, tmp_path, settings):
        settings.BACKUP_DIR = tmp_path / 'backups'
        record = create_backup(created_by=self.admin)
        path = record.filepath
        res = self.client.delete(f'/api/v1/backups/{record.id}/')
        assert res.status_code == 204
        assert not os.path.exists(path)
        assert BackupRecord.objects.count() == 0
