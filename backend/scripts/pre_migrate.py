"""
One-shot repair for databases created by an *older* SecureMed schema.

It exists for one historical event: the ``channels`` app was relabelled
``app_channels``, which orphaned its tables and its ``django_migrations`` rows.
Everything here realigns a pre-rename database with the current code.

Two things changed, both of which made this script dangerous to run on a boot:

  * It is now **opt-in**. Set ``PRE_MIGRATE=1`` to run it. It used to be invoked
    unconditionally from ``deploy/start.sh`` with ``|| true``, so every container
    start issued ``ALTER TABLE`` and ``DELETE FROM django_migrations`` against a
    live PHI database and threw away the error. Migration history is not
    self-healing: once a row is wrong, ``migrate`` either re-applies a migration
    over existing objects or skips one that never ran.
  * The prune is derived from **what is on disk**, not from a hardcoded list.
    The old statement deleted every history row for six apps whose name was not
    in a pinned set of initials — but ``accounts`` has since gained 0003, 0004
    and 0005, and ``billing`` a 0002. All four rows were deleted on every run,
    after which ``migrate`` tried to re-apply them: ``--fake-initial`` only fakes
    *initial* migrations, so ``0005_biometric_public_key_credentials`` re-ran
    ``AddField`` against columns that already existed and the deploy failed with
    ``DuplicateColumn``. Now a row is dropped only when its migration file is
    genuinely gone.

Nothing here is destructive to *data*: no DROP, no DELETE against an application
table. It rewrites bookkeeping and adds missing columns.
"""
import os
import sys

# The only apps whose history is ever pruned — the ones touched by the rename and
# the schema drift that followed it. Everything else is left exactly as recorded.
LEGACY_APPS = (
    'accounts',
    'app_channels',
    'patients',
    'appointments',
    'pharmacy',
    'billing',
)

# apps/<package>/migrations/. The label was renamed; the package was not.
PACKAGE_FOR_LABEL = {'app_channels': 'channels'}

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tables renamed by the relabel, old -> new.
CHANNEL_TABLES = (
    ('channels_channel', 'app_channels_channel'),
    ('channels_channelmembership', 'app_channels_channelmembership'),
    ('channels_channelmessage', 'app_channels_channelmessage'),
    ('channels_channelinvitation', 'app_channels_channelinvitation'),
)

# Forensic columns added to audit_auditlog after its initial migration. ADD COLUMN
# IF NOT EXISTS, so this is a no-op on an up-to-date database.
AUDIT_COLUMNS = (
    ('mac_address', "VARCHAR(100) DEFAULT ''"),
    ('device_fingerprint', "VARCHAR(255) DEFAULT ''"),
    ('hostname', "VARCHAR(255) DEFAULT ''"),
    ('os_info', "VARCHAR(255) DEFAULT ''"),
    ('browser_info', "VARCHAR(255) DEFAULT ''"),
    ('screen_resolution', "VARCHAR(50) DEFAULT ''"),
    ('timezone_offset', "VARCHAR(50) DEFAULT ''"),
    ('language', "VARCHAR(50) DEFAULT ''"),
    ('session_id', "VARCHAR(255) DEFAULT ''"),
    ('geo_location', "VARCHAR(255) DEFAULT ''"),
    ('risk_score', 'DOUBLE PRECISION DEFAULT 0.0'),
)

def _enabled():
    """Whether the operator asked for this repair."""
    return os.environ.get('PRE_MIGRATE', '').strip().lower() in ('1', 'true', 'yes', 'on')


def _connect_postgres(db_url):
    """Connect without weakening the TLS mode the DSN asked for.

    ``psycopg2.connect(dsn, sslmode=...)`` lets the keyword beat the DSN, so the
    old ``sslmode=os.environ.get('DB_SSLMODE', 'prefer')`` silently downgraded a
    ``?sslmode=require`` URL to opportunistic TLS — on the one connection that
    carries schema changes and the database password. The keyword is supplied
    only when the DSN is silent, and then it defaults to require.
    """
    import psycopg2

    if 'sslmode=' in db_url:
        return psycopg2.connect(db_url)
    return psycopg2.connect(db_url, sslmode=os.environ.get('DB_SSLMODE', 'require'))


def _table_exists(cursor, name):
    cursor.execute(
        'SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);',
        [name],
    )
    return bool(cursor.fetchone()[0])


def _column_exists(cursor, table, column):
    cursor.execute(
        'SELECT EXISTS (SELECT 1 FROM information_schema.columns '
        'WHERE table_name = %s AND column_name = %s);',
        [table, column],
    )
    return bool(cursor.fetchone()[0])


def _migrations_on_disk(app_label):
    """Names of the migrations that still exist as files, or None if unknowable.

    Returning None (no migrations package at all) means "do not prune this app":
    an empty set would read as "every recorded migration is an orphan".
    """
    package = PACKAGE_FOR_LABEL.get(app_label, app_label)
    path = os.path.join(BACKEND_DIR, 'apps', package, 'migrations')
    if not os.path.isdir(path):
        return None
    names = {
        entry[:-3]
        for entry in os.listdir(path)
        if entry.endswith('.py') and entry != '__init__.py'
    }
    return names or None


def _prune_orphaned_history(cursor):
    """Delete history rows whose migration file no longer exists — nothing else.

    This is the whole of the old blanket DELETE, narrowed to the case it was
    actually trying to cover: a migration that was removed from the repository
    but is still recorded as applied, which makes ``migrate`` fail to build the
    graph. A migration that is still on disk keeps its row, so it is never
    re-applied over objects it already created.
    """
    for app_label in LEGACY_APPS:
        on_disk = _migrations_on_disk(app_label)
        if on_disk is None:
            continue
        cursor.execute('SELECT name FROM django_migrations WHERE app = %s;', [app_label])
        orphans = [row[0] for row in cursor.fetchall() if row[0] not in on_disk]
        for name in orphans:
            cursor.execute(
                'DELETE FROM django_migrations WHERE app = %s AND name = %s;',
                [app_label, name],
            )
            print(f'pre_migrate: dropped orphaned history row {app_label}.{name} (no file on disk)')


def _fix_postgres(db_url):
    conn = _connect_postgres(db_url)
    conn.autocommit = True
    try:
        with conn.cursor() as cursor:
            if not _table_exists(cursor, 'django_migrations'):
                print('pre_migrate: fresh Postgres database (no django_migrations table) — nothing to repair.')
                return

            for old_name, new_name in CHANNEL_TABLES:
                if _table_exists(cursor, old_name) and not _table_exists(cursor, new_name):
                    # Identifiers are module constants, never request input.
                    cursor.execute(f'ALTER TABLE {old_name} RENAME TO {new_name};')
                    print(f'pre_migrate: renamed table {old_name} -> {new_name}')

            cursor.execute("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")

            if _table_exists(cursor, 'audit_auditlog'):
                for col_name, col_type in AUDIT_COLUMNS:
                    cursor.execute(
                        f'ALTER TABLE audit_auditlog ADD COLUMN IF NOT EXISTS {col_name} {col_type};'
                    )
                print('pre_migrate: ensured forensic columns exist on audit_auditlog.')

            _align_app_channels(cursor)
            _align_accounts(cursor)
            _align_patients(cursor)
            _align_appointments(cursor)
            _prune_orphaned_history(cursor)
    finally:
        conn.close()
    print('pre_migrate: Postgres migration history aligned with the current codebase.')


def _record_if_missing(cursor, app_label, names):
    """Mark migrations as applied when their schema is demonstrably already there."""
    for name in names:
        cursor.execute(
            'SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s;',
            [app_label, name],
        )
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                'INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW());',
                [app_label, name],
            )
            print(f'pre_migrate: registered {app_label}.{name} (its schema already exists).')


def _align_app_channels(cursor):
    if not _table_exists(cursor, 'app_channels_channel'):
        # Table genuinely absent: let migrate create it from scratch.
        cursor.execute("DELETE FROM django_migrations WHERE app = 'app_channels';")
        print('pre_migrate: app_channels_channel missing — reset app_channels history so migrate creates it.')
        return
    _record_if_missing(cursor, 'app_channels', ('0001_initial', '0002_initial'))


def _align_accounts(cursor):
    # basin_id only exists once accounts' initials have run.
    if _column_exists(cursor, 'accounts_user', 'basin_id'):
        _record_if_missing(cursor, 'accounts', ('0001_initial', '0002_initial'))


def _align_patients(cursor):
    if _table_exists(cursor, 'patients_patient'):
        _record_if_missing(cursor, 'patients', ('0001_initial',))
    else:
        cursor.execute("DELETE FROM django_migrations WHERE app = 'patients';")
        print('pre_migrate: patients_patient missing — reset patients history so migrate creates it.')


def _align_appointments(cursor):
    if not _table_exists(cursor, 'appointments_appointment'):
        cursor.execute("DELETE FROM django_migrations WHERE app = 'appointments';")
        print('pre_migrate: appointments_appointment missing — reset appointments history so migrate creates it.')


def _fix_sqlite():
    import sqlite3

    db_path = os.path.join(BACKEND_DIR, 'db.sqlite3')
    if not os.path.exists(db_path):
        print('pre_migrate: no local db.sqlite3 — nothing to repair.')
        return
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations';"
            )
            if cursor.fetchone():
                cursor.execute("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")
    finally:
        conn.close()
    print('pre_migrate: SQLite checked.')


def fix_migration_history():
    db_url = os.environ.get('DATABASE_URL', '')
    if db_url.startswith(('postgres://', 'postgresql://')):
        _fix_postgres(db_url)
    else:
        _fix_sqlite()


def main():
    if not _enabled():
        print(
            'pre_migrate: skipped (PRE_MIGRATE is not set).\n'
            '  This script rewrites django_migrations and issues ALTER TABLE. It is only\n'
            '  needed once, when upgrading a database created before the channels ->\n'
            '  app_channels rename. Run it deliberately with PRE_MIGRATE=1, against a\n'
            '  database you have a backup of, then unset it again.'
        )
        return 0

    # Errors are no longer swallowed: a repair that half-succeeded leaves history
    # in a state `migrate` cannot reason about, and the caller must see that.
    try:
        fix_migration_history()
    except Exception as exc:
        print(f'pre_migrate: FAILED — {type(exc).__name__}: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
