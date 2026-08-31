"""
Backup service — the real backup/restore engine.

create_backup():
  1. dumpdata → db.json  (excludes sessions & JWT blacklist = transient data)
  2. manifest.json with SHA-256 checksum + row counts
  3. copies media/ uploads into the archive
  4. writes a single ZIP under BACKUP_DIR and records it in BackupRecord
  5. retention: keeps only the newest BACKUP_KEEP_COUNT archives

restore_backup():
  1. verifies the archive + checksum
  2. flushes current data (keeping migrations)
  3. loaddata db.json
  4. restores media files
"""
import hashlib
import json
import os
import shutil
import time
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from apps.backups.models import BackupRecord

TRANSIENT_EXCLUDE = [
    'sessions.session',
    'token_blacklist.outstandingtoken',
    'token_blacklist.blacklistedtoken',
    'backups.BackupRecord',  # never restore backup metadata into itself
]


def backup_dir() -> Path:
    p = Path(getattr(settings, 'BACKUP_DIR', Path(settings.BASE_DIR) / 'backups'))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _table_counts() -> dict:
    from django.apps import apps
    counts = {}
    for model in apps.get_models():
        if model._meta.app_label == 'backups' and model.__name__ == 'BackupRecord':
            continue
        label = f'{model._meta.app_label}.{model._meta.object_name}'
        try:
            counts[label] = model._default_manager.count()
        except Exception:
            counts[label] = -1
    return counts


def _count_media_files() -> int:
    media_root = Path(settings.MEDIA_ROOT)
    if not media_root.exists():
        return 0
    total = 0
    for _, _, files in os.walk(media_root):
        total += len(files)
    return total


def create_backup(created_by=None, kind=BackupRecord.Kind.MANUAL, note='') -> BackupRecord:
    """Create a full backup archive. Raises on failure."""
    from apps.backups.models import BackupRecord as BR

    started = time.time()
    ts = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    # unique suffix avoids same-second filename collisions
    unique = uuid.uuid4().hex[:6]
    filename = f'securemed_backup_{ts}_{unique}.zip'
    out_path = backup_dir() / filename

    # 1) data dump
    dump_file = backup_dir() / f'_tmp_dump_{ts}.json'
    with open(dump_file, 'w', encoding='utf-8') as f:
        call_command(
            'dumpdata',
            exclude=TRANSIENT_EXCLUDE,
            stdout=f,
            format='json',
            indent=1,
        )
    checksum = _sha256_file(dump_file)

    manifest = {
        'created_at': timezone.now().isoformat(),
        'database': connections.databases[DEFAULT_DB_ALIAS].get('ENGINE', ''),
        'checksum_sha256': checksum,
        'row_counts': _table_counts(),
        'note': note,
        'kind': kind,
    }

    # 2) build the zip
    try:
        with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(dump_file, arcname='db.json')
            zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
            # 3) media files
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                for root, _, files in os.walk(media_root):
                    for name in files:
                        full = Path(root) / name
                        arc = Path('media') / full.relative_to(media_root)
                        zf.write(full, arcname=str(arc))
    finally:
        dump_file.unlink(missing_ok=True)

    duration_ms = int((time.time() - started) * 1000)
    record = BR.objects.create(
        filename=filename,
        filepath=str(out_path),
        size_bytes=out_path.stat().st_size,
        checksum=checksum,
        status=BR.Status.COMPLETED,
        kind=kind,
        row_counts=manifest['row_counts'],
        media_files=_count_media_files(),
        duration_ms=duration_ms,
        created_by=created_by,
        note=note[:255],
    )
    _apply_retention()
    return record


def _apply_retention():
    """Keep only the newest BACKUP_KEEP_COUNT completed archives."""
    keep = int(getattr(settings, 'BACKUP_KEEP_COUNT', 14))
    old = BackupRecord.objects.filter(status=BackupRecord.Status.COMPLETED)\
        .order_by('-created_at')[keep:]
    for rec in old:
        try:
            os.remove(rec.filepath)
        except OSError:
            pass
        rec.delete()


def verify_backup(filepath: str) -> dict:
    """Open an archive and validate structure + checksum. Returns manifest."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'الملف غير موجود: {filepath}')
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if 'db.json' not in names or 'manifest.json' not in names:
            raise ValueError('أرشيف غير صالح — db.json أو manifest.json مفقود')
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        expected = manifest.get('checksum_sha256', '')
        # extract db.json to temp and hash
        tmp = path.parent / f'_verify_{path.name}.json'
        try:
            with zf.open('db.json') as src, open(tmp, 'wb') as dst:
                shutil.copyfileobj(src, dst)
            actual = _sha256_file(tmp)
        finally:
            tmp.unlink(missing_ok=True)
        if expected and actual != expected:
            raise ValueError('فشل التحقق من البصمة — الأرشيف تالف أو معدّل')
    return manifest


def restore_backup(filepath: str, force: bool = False) -> dict:
    """
    Restore database + media from an archive.
    Refuses without force=True (destructive: flushes current data).
    """
    manifest = verify_backup(filepath)  # raises on corruption
    if not force:
        return {
            'verified': True,
            'manifest': manifest,
            'detail': 'الأرشيف سليم — أعد التنفيذ مع force=True للاستعادة الفعلية',
        }

    path = Path(filepath)
    with zipfile.ZipFile(path) as zf:
        db_json = zf.read('db.json').decode('utf-8')

        # write the dump to a temp fixture file (loaddata accepts paths)
        tmp_fixture = path.parent / f'_restore_{path.name}.json'
        tmp_fixture.write_text(db_json, encoding='utf-8')
        try:
            # 1) flush current data (django_migrations is preserved;
            #    post_migrate inhibited so loaddata refills contenttypes)
            call_command(
                'flush', interactive=False, verbosity=0,
                inhibit_post_migrate=True,
            )

            # 2) load the dump
            from django.core.serializers.base import DeserializationError
            try:
                call_command('loaddata', str(tmp_fixture), verbosity=0)
            except DeserializationError as e:
                raise ValueError(f'بيانات غير قابلة للاستعادة: {e}')
        finally:
            tmp_fixture.unlink(missing_ok=True)

        # 3) restore media files
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        restored_files = 0
        for name in zf.namelist():
            if name.startswith('media/') and not name.endswith('/'):
                rel = Path(name).relative_to('media')
                target = media_root / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(target, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
                restored_files += 1

    return {
        'verified': True,
        'restored': True,
        'restored_media_files': restored_files,
        'manifest': manifest,
        'detail': 'تمت الاستعادة بنجاح',
    }
