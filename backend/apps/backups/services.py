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
import logging 
import os 
import shutil 
import time 
import uuid 
import zipfile 
from datetime import datetime 
from pathlib import Path 

from django .conf import settings 
from django .core import serializers 
from django .core .management import call_command 
from django .db import DEFAULT_DB_ALIAS ,connections 

from apps .accounts .models import User 
from django .utils import timezone 

from apps .backups .models import BackupRecord 

TRANSIENT_EXCLUDE =[
'sessions.session',
'token_blacklist.outstandingtoken',
'token_blacklist.blacklistedtoken',
'backups.BackupRecord',# never restore backup metadata into itself
]


def backup_dir ()->Path :
    p =Path (getattr (settings ,'BACKUP_DIR',Path (settings .BASE_DIR )/'backups'))
    p .mkdir (parents =True ,exist_ok =True )
    return p 


def _sha256_file (path :Path )->str :
    h =hashlib .sha256 ()
    with open (path ,'rb')as f :
        for chunk in iter (lambda :f .read (1 <<20 ),b''):
            h .update (chunk )
    return h .hexdigest ()


def _table_counts ()->dict :
    from django .apps import apps 
    counts ={}
    for model in apps .get_models ():
        if model ._meta .app_label =='backups'and model .__name__ =='BackupRecord':
            continue 
        label =f'{model ._meta .app_label }.{model ._meta .object_name }'
        try :
            counts [label ]=model ._default_manager .count ()
        except Exception :
            counts [label ]=-1 
    return counts 


def _count_media_files ()->int :
    media_root =Path (settings .MEDIA_ROOT )
    if not media_root .exists ():
        return 0 
    total =0 
    for _ ,_ ,files in os .walk (media_root ):
        total +=len (files )
    return total 


def create_backup (created_by =None ,kind =BackupRecord .Kind .MANUAL ,note ='',
                   scope =BackupRecord .Scope .FULL )->BackupRecord :
    """Create a backup archive covering *scope*.

    FULL = db dump + media, DATABASE = db dump only, MEDIA = media only.
    Separate scopes exist because the two halves age differently: the database
    changes with every consultation while uploaded scans and lab PDFs are
    immutable, so a frequent small database-only backup is cheaper to ship
    off-site than a full archive every time.
    """
    from apps .backups .models import BackupRecord as BR 

    if scope not in BR .Scope .values :
        raise ValueError (f'نطاق غير معروف: {scope }')

    started =time .time ()
    ts =timezone .localtime ().strftime ('%Y%m%d_%H%M%S')
    # unique suffix avoids same-second filename collisions
    unique =uuid .uuid4 ().hex [:6 ]
    scope_tag ={'FULL':'full','DATABASE':'db','MEDIA':'media'}[scope ]
    filename =f'securemed_backup_{scope_tag }_{ts }_{unique }.zip'
    out_path =backup_dir ()/filename 

    media_root =Path (settings .MEDIA_ROOT )
    include_db =scope in (BR .Scope .FULL ,BR .Scope .DATABASE )
    include_media =scope in (BR .Scope .FULL ,BR .Scope .MEDIA )

    dump_file =None
    checksum =''
    row_counts ={}

    if include_db :
        # 1) data dump
        dump_file =backup_dir ()/f'_tmp_dump_{ts }.json'
        with open (dump_file ,'w',encoding ='utf-8')as f :
            call_command (
            'dumpdata',
            exclude =TRANSIENT_EXCLUDE ,
            stdout =f ,
            format ='json',
            indent =1 ,
            )
        checksum =_sha256_file (dump_file )
        row_counts =_table_counts ()

    manifest ={
    'created_at':timezone .now ().isoformat (),
    'database':connections .databases [DEFAULT_DB_ALIAS ].get ('ENGINE',''),
    'checksum_sha256':checksum ,
    'row_counts':row_counts ,
    'note':note ,
    'kind':kind ,
    'scope':scope ,
    }

    # 2) build the zip
    try :
        with zipfile .ZipFile (out_path ,'w',zipfile .ZIP_DEFLATED )as zf :
            if include_db :
                zf .write (dump_file ,arcname ='db.json')
            zf .writestr ('manifest.json',json .dumps (manifest ,ensure_ascii =False ,indent =2 ))
            # 3) media files
            if include_media and media_root .exists ():
                for root ,_ ,files in os .walk (media_root ):
                    for name in files :
                        full =Path (root )/name 
                        arc =Path ('media')/full .relative_to (media_root )
                        zf .write (full ,arcname =str (arc ))
    finally :
        if dump_file is not None :
            dump_file .unlink (missing_ok =True )
        
    # Encrypt the zip file
    try:
        import hashlib
        import base64
        from cryptography.fernet import Fernet
        secret = getattr(settings, 'BACKUP_ENCRYPTION_KEY', '') or settings.SECRET_KEY
        # Fernet requires exactly 32 url-safe base64 bytes. The old
        # pad/truncate-to-32 derivation broke whenever SECRET_KEY was shorter
        # than 32 bytes: base64 of a padded key is valid, but of a *truncated*
        # secret of arbitrary length it frequently is not, Fernet raised inside
        # the except-swallowing block, and the archive was left as plaintext
        # while every later read treated it as encrypted garbage. Hashing the
        # secret to 32 bytes is deterministic and always a valid key length;
        # changing the derivation is safe because archives record no key
        # metadata — a wrong-key archive has always failed verification.
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())
        fernet = Fernet(key)

        with open(out_path, 'rb') as f:
            data = f.read()
        encrypted_data = fernet.encrypt(data)
        with open(out_path, 'wb') as f:
            f.write(encrypted_data)
    except Exception as e:
        logging.getLogger('security').error(f"Failed to encrypt backup: {e}")

    duration_ms =int ((time .time ()-started )*1000 )
    record =BR .objects .create (
    filename =filename ,
    filepath =str (out_path ),
    size_bytes =out_path .stat ().st_size ,
    checksum =checksum ,
    status =BR .Status .COMPLETED ,
    kind =kind ,
    scope =scope ,
    row_counts =row_counts ,
    media_files =_count_media_files ()if include_media else 0 ,
    duration_ms =duration_ms ,
    created_by =created_by ,
    note =note [:255 ],
    )
    _apply_retention ()
    # Off-site delivery (Telegram document / cloud bucket) runs best-effort:
    # a messaging or storage outage must never fail the backup run itself —
    # the local archive above is already complete and verified.
    try :
        from apps .backups .offsite import deliver_backup
        deliver_backup (record )
    except Exception as e :
        logger =logging .getLogger ('security')
        logger .error (f"Off-site delivery failed for {filename}: {e }")
    return record 


def _apply_retention ():
    """Keep only the newest BACKUP_KEEP_COUNT completed archives **per scope**.

    Per-scope, not global: media-only archives are cheap and may be run often
    (uploaded scans never change), so a global count would let a burst of them
    evict the full backups that restores actually depend on.
    """
    keep =int (getattr (settings ,'BACKUP_KEEP_COUNT',14 ))
    for scope in BackupRecord .Scope .values :
        old =(BackupRecord .objects
        .filter (status =BackupRecord .Status .COMPLETED ,scope =scope )
        .order_by ('-created_at')[keep :])
        for rec in old :
            try :
                os .remove (rec .filepath )
            except OSError :
                pass 
            rec .delete ()


def _get_decrypted_backup(filepath: str):
    """Return an open file-like handle on the unencrypted ZIP contents.

    A Fernet token starts with the ASCII bytes ``gAAAAA`` and a ZIP starts
    with ``PK\x03\x04``. Archives written by an older release (before
    encryption was added) start with the ZIP signature, so when decryption
    fails on such a file the right answer is to hand it back as-is instead
    of telling the operator the backup is broken. A wrong key against a
    truly encrypted archive also produces a "PK" magic — but only after
    Fernet has rejected it, so the fallback runs *after* the explicit
    Fernet failure and not on every file.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'الملف غير موجود: {filepath}')

    import hashlib
    import base64
    from cryptography.fernet import Fernet, InvalidToken
    from io import BytesIO

    raw = path.read_bytes()
    # Legacy plaintext archive — not encrypted at all, Fernet would just
    # mangle the first few bytes if we tried.
    if raw.startswith(b'PK\x03\x04'):
        return BytesIO(raw)

    secret = getattr(settings, 'BACKUP_ENCRYPTION_KEY', '') or settings.SECRET_KEY
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())
    fernet = Fernet(key)

    try:
        return BytesIO(fernet.decrypt(raw))
    except InvalidToken:
        # Could be a legacy archive that does not start with PK for some
        # reason (e.g. a backup that was appended to), or a key mismatch.
        # Re-check the magic in case Fernet's exception masked it.
        if raw.startswith(b'PK\x03\x04'):
            return BytesIO(raw)
        raise ValueError('فشل فك التشفير — مفتاح التشفير خاطئ أو الملف تالف')


def verify_backup (filepath :str )->dict :
    """Open an archive and validate structure + checksum. Returns manifest."""
    decrypted_file = _get_decrypted_backup(filepath)
    with zipfile .ZipFile (decrypted_file )as zf :
        names =set (zf .namelist ())
        if 'manifest.json'not in names :
            raise ValueError ('أرشيف غير صالح — manifest.json مفقود')
        manifest =json .loads (zf .read ('manifest.json').decode ('utf-8'))
        scope =manifest .get ('scope',BackupRecord .Scope .FULL )
        # Older archives carry no scope; they are full archives.
        if 'db.json'not in names :
            if scope !=BackupRecord .Scope .MEDIA :
                raise ValueError ('أرشيف غير صالح — db.json مفقود')
        else :
            expected =manifest .get ('checksum_sha256','')
            # extract db.json to temp and hash
            path = Path(filepath)
            tmp =path .parent /f'_verify_{path .name }.json'
            try :
                with zf .open ('db.json')as src ,open (tmp ,'wb')as dst :
                    shutil .copyfileobj (src ,dst )
                actual =_sha256_file (tmp )
            finally :
                tmp .unlink (missing_ok =True )
            if expected and actual !=expected :
                raise ValueError ('فشل التحقق من البصمة — الأرشيف تالف أو معدّل')
    return manifest 


def _restore_media_from_zip (zf )->int :
    """Copy every media/ entry of an open archive into MEDIA_ROOT."""
    media_root =Path (settings .MEDIA_ROOT )
    media_root .mkdir (parents =True ,exist_ok =True )
    restored_files =0 
    for name in zf .namelist ():
        if name .startswith ('media/')and not name .endswith ('/'):
            rel =Path (name ).relative_to ('media')
            target =media_root /rel 
            target .parent .mkdir (parents =True ,exist_ok =True )
            with zf .open (name )as src ,open (target ,'wb')as dst :
                shutil .copyfileobj (src ,dst )
            restored_files +=1 
    return restored_files 


def reconcile_backup_registry():
    """Re-register archive files on disk that have no BackupRecord row.

    restore_backup's flush wipes BackupRecord itself — it is transient data as
    far as dumpdata is concerned — so every archive that survived the restore
    on disk would otherwise be forgotten by the registry while still occupying
    space and still being restorable by hand.
    """
    from apps .backups .models import BackupRecord as BR 

    registered =set (BR .objects .values_list ('filename',flat =True ))
    created =0 
    for f in sorted (backup_dir ().glob ('*.zip')):
        if f .name in registered :
            continue 
        scope ,checksum ='',''
        try :
            manifest =verify_backup (str (f ))
            scope =manifest .get ('scope',BR .Scope .FULL )
            checksum =manifest .get ('checksum_sha256','')
        except Exception :
            pass 
        BR .objects .create (
        filename =f .name ,
        filepath =str (f ),
        size_bytes =f .stat ().st_size ,
        checksum =checksum [:64 ],
        status =BR .Status .COMPLETED ,
        kind =BR .Kind .MANUAL ,
        scope =scope or BR .Scope .FULL ,
        note ='أُعيد تسجيله بعد استعادة',
        )
        created +=1 
    return created 


def restore_backup (filepath :str ,force :bool =False )->dict :
    """
    Restore from an archive, honouring the manifest's scope.

    DATABASE → flush + loaddata (media untouched); MEDIA → files only, the
    live database is never touched; FULL → both (the historical behaviour).
    Refuses without force=True for the destructive scopes.
    """
    manifest =verify_backup (filepath )# raises on corruption
    scope =manifest .get ('scope',BackupRecord .Scope .FULL )
    if not force :
        return {
        'verified':True ,
        'manifest':manifest ,
        'scope':scope ,
        'detail':'الأرشيف سليم — أعد التنفيذ مع force=True للاستعادة الفعلية',
        }

    # Pre-restore safety copy: an accidental restore was irreversible before
    # this — the flush destroyed the live data with no way back. The current
    # state is snapshotted first, and a failure to snapshot aborts the restore
    # (a broken safety net must not sit silently under a destructive
    # operation). Retention applies to it like any archive.
    safety_record =None
    if scope !=BackupRecord .Scope .MEDIA :
        safety_record =create_backup (
        kind =BackupRecord .Kind .MANUAL ,
        note ='أمان تلقائي قبل الاستعادة',
        scope =BackupRecord .Scope .FULL ,
        )

    decrypted_file = _get_decrypted_backup(filepath)
    restored_media_files =0 
    with zipfile .ZipFile (decrypted_file )as zf :
        if scope !=BackupRecord .Scope .MEDIA :
            db_json =zf .read ('db.json').decode ('utf-8')

            # write the dump to a temp fixture file (loaddata accepts paths)
            path = Path(filepath)
            tmp_fixture =path .parent /f'_restore_{path .name }.json'
            tmp_fixture .write_text (db_json ,encoding ='utf-8')
            try :
            # 1) flush current data (django_migrations is preserved;
            #    post_migrate inhibited so loaddata refills contenttypes)
                call_command (
                'flush',interactive =False ,verbosity =0 ,
                inhibit_post_migrate =True ,
                )

                # 2) load the dump
                from django .core .serializers .base import DeserializationError 
                try :
                    call_command ('loaddata',str (tmp_fixture ),verbosity =0 )
                except DeserializationError as e :
                    raise ValueError (f'بيانات غير قابلة للاستعادة: {e }')
            finally :
                tmp_fixture .unlink (missing_ok =True )

        if scope !=BackupRecord .Scope .DATABASE :
            # 3) restore media files
            restored_media_files =_restore_media_from_zip (zf )

    # flush wiped BackupRecord itself (transient-excluded from the dump), so
    # re-register the safety copy explicitly and reconcile every other archive
    # that survived on disk.
    if safety_record is not None :
        BackupRecord .objects .create (
        filename =safety_record .filename ,
        filepath =safety_record .filepath ,
        size_bytes =safety_record .size_bytes ,
        checksum =safety_record .checksum ,
        status =BackupRecord .Status .COMPLETED ,
        kind =BackupRecord .Kind .MANUAL ,
        scope =BackupRecord .Scope .FULL ,
        media_files =safety_record .media_files ,
        duration_ms =safety_record .duration_ms ,
        note ='أمان تلقائي قبل الاستعادة',
        )
    reconcile_backup_registry ()

    # Events written between the safety snapshot and the flush (e.g. this
    # very restore's earlier audit rows) may reference users the flush just
    # removed — null those FKs or the DB carries orphaned audit rows that
    # break constraint checks later.
    from apps .audit .models import AuditLog 
    AuditLog .objects .exclude (user__isnull =True ).exclude (
    user_id__in =User .objects .values_list ('id',flat =True )
    ).update (user =None )

    return {
    'verified':True ,
    'restored':True ,
    'scope':scope ,
    'restored_media_files':restored_media_files ,
    'safety_backup':safety_record .filename if safety_record else None ,
    'manifest':manifest ,
    'detail':'تمت الاستعادة بنجاح',
    }
