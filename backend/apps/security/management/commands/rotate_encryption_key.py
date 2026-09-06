"""Re-encrypt stored data with the current ENCRYPTION_KEY.

Rotating an encryption key is only a real option if there is a way to move the data
onto the new key. ``ENCRYPTION_KEY_FALLBACKS`` makes old data *readable* after a
rotation; this command is what finally makes the old key unnecessary, so it can be
removed from the fallback list.

Usage, in order:

    # 1. put the current key at the front of ENCRYPTION_KEY_FALLBACKS, set the new
    #    key as ENCRYPTION_KEY, deploy — reads keep working, writes use the new key
    # 2. see what would change
    python manage.py rotate_encryption_key --dry-run
    # 3. do it (safe to re-run; already-current rows are rewritten harmlessly)
    python manage.py rotate_encryption_key
    # 4. remove the old key from ENCRYPTION_KEY_FALLBACKS and deploy again

It also serves as the backfill for files uploaded before encryption at rest existed:
those have no header, and a run with ENCRYPT_MEDIA_AT_REST on encrypts them in place.
"""
import os
import tempfile

from django.apps import apps as django_apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.security.crypto import (
    decrypt_field,
    decrypt_media,
    encrypt_field,
    encrypt_media,
    is_encrypted_media,
)

# Columns holding Fernet ciphertext, as (app_label, model, [field names]). These are
# the raw underscore-prefixed columns, not the decrypting properties in front of
# them: assigning through the property would re-run model logic we do not want here.
FIELD_TARGETS = [
    ('patients', 'Patient', [
        '_full_name', '_national_id', '_phone', '_address', '_emergency_contact',
    ]),
    ('patients', 'MedicalRecord', ['_content']),
    ('accounts', 'User', ['mfa_secret']),
    ('accounts', 'BiometricProfile', ['biometric_hash']),
    ('accounts', 'BiometricChallenge', ['expected_response']),
]

# FileFields whose bytes are encrypted by apps.core.storage.
FILE_TARGETS = [
    ('patients', 'MedicalFile', 'file'),
    ('telemedicine', 'ChatMessage', 'attachment'),
]

BATCH_SIZE = 200


class Command(BaseCommand):
    help = 'Re-encrypt encrypted columns and media files with the current ENCRYPTION_KEY.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be rewritten without writing anything.',
        )
        parser.add_argument(
            '--fields-only', action='store_true',
            help='Skip media files.',
        )
        parser.add_argument(
            '--files-only', action='store_true',
            help='Skip database columns.',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        if options['fields_only'] and options['files_only']:
            raise CommandError('--fields-only and --files-only are mutually exclusive.')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — nothing will be written.\n'))

        if not options['files_only']:
            self._rotate_fields()
        if not options['fields_only']:
            self._rotate_files()

        self.stdout.write(self.style.SUCCESS('\nDone.'))
        if not self.dry_run:
            self.stdout.write(
                'Old keys can now be removed from ENCRYPTION_KEY_FALLBACKS — but only '
                'after confirming this run covered every environment sharing the data.'
            )

    # ------------------------------------------------------------------ columns --
    def _rotate_fields(self):
        self.stdout.write(self.style.MIGRATE_HEADING('Encrypted columns'))
        for app_label, model_name, field_names in FIELD_TARGETS:
            try:
                model = django_apps.get_model(app_label, model_name)
            except LookupError:
                self.stdout.write(f'  {app_label}.{model_name}: model not present, skipped')
                continue

            rewritten = failed = 0
            queryset = model.objects.all().only('pk', *field_names)
            batch = []
            for obj in queryset.iterator(chunk_size=BATCH_SIZE):
                changed = False
                for name in field_names:
                    current = getattr(obj, name, None)
                    if not current:
                        continue
                    try:
                        plaintext = decrypt_field(current)
                    except Exception as exc:
                        # A value no configured key can read. Reported and left
                        # untouched — overwriting it would destroy the only copy,
                        # and the likely cause is a key missing from the fallbacks.
                        failed += 1
                        self.stderr.write(
                            f'  ! {model_name} pk={obj.pk} field={name}: {exc}'
                        )
                        continue
                    setattr(obj, name, encrypt_field(plaintext))
                    changed = True
                if changed:
                    rewritten += 1
                    batch.append(obj)
                if len(batch) >= BATCH_SIZE:
                    self._flush(model, batch, field_names)
                    batch = []
            self._flush(model, batch, field_names)

            summary = f'  {app_label}.{model_name}: {rewritten} row(s) re-encrypted'
            if failed:
                self.stdout.write(self.style.ERROR(f'{summary}, {failed} unreadable'))
            else:
                self.stdout.write(self.style.SUCCESS(summary))

    def _flush(self, model, batch, field_names):
        if not batch or self.dry_run:
            return
        with transaction.atomic():
            model.objects.bulk_update(batch, field_names)

    # -------------------------------------------------------------------- files --
    def _rotate_files(self):
        self.stdout.write(self.style.MIGRATE_HEADING('Media files'))

        if getattr(settings, 'USE_S3_STORAGE', False):
            self.stdout.write(
                '  Skipped: files are in S3, where server-side encryption applies and '
                'this command has no local path to rewrite in place.'
            )
            return

        encrypt_new = getattr(settings, 'ENCRYPT_MEDIA_AT_REST', False)
        for app_label, model_name, field_name in FILE_TARGETS:
            try:
                model = django_apps.get_model(app_label, model_name)
            except LookupError:
                self.stdout.write(f'  {app_label}.{model_name}: model not present, skipped')
                continue

            rewritten = backfilled = failed = missing = 0
            queryset = (
                model.objects.exclude(**{field_name: ''})
                .exclude(**{f'{field_name}__isnull': True})
                .only('pk', field_name)
            )
            for obj in queryset.iterator(chunk_size=BATCH_SIZE):
                name = getattr(obj, field_name).name
                try:
                    path = default_storage.path(name)
                except NotImplementedError:
                    self.stdout.write('  Skipped: storage backend has no local path.')
                    return
                if not os.path.exists(path):
                    missing += 1
                    continue
                try:
                    with open(path, 'rb') as fh:
                        blob = fh.read()
                    if is_encrypted_media(blob):
                        plaintext = decrypt_media(blob)
                        rewritten += 1
                    elif encrypt_new:
                        plaintext = blob
                        backfilled += 1
                    else:
                        continue
                    if not self.dry_run:
                        _replace_atomically(path, encrypt_media(plaintext))
                except Exception as exc:
                    failed += 1
                    self.stderr.write(f'  ! {model_name} pk={obj.pk} {name}: {exc}')

            summary = (
                f'  {app_label}.{model_name}.{field_name}: {rewritten} re-encrypted, '
                f'{backfilled} newly encrypted'
            )
            if missing:
                summary += f', {missing} row(s) with no file on disk'
            if failed:
                self.stdout.write(self.style.ERROR(f'{summary}, {failed} failed'))
            else:
                self.stdout.write(self.style.SUCCESS(summary))


def _replace_atomically(path, data):
    """Write next to the target, then rename over it.

    A half-written medical file is unrecoverable, and rewriting in place leaves a
    window where a crash or a full disk truncates it. os.replace is atomic within a
    filesystem, so a reader sees either the old bytes or the new ones.
    """
    directory = os.path.dirname(path)
    handle, tmp_path = tempfile.mkstemp(dir=directory, suffix='.rotating')
    try:
        with os.fdopen(handle, 'wb') as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
