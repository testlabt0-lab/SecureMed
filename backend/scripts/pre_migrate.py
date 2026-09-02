"""
Pre-migration compatibility script.
Fixes legacy schema/migration state in django_migrations on PostgreSQL (Neon) and SQLite
to guarantee clean, idempotent migrations on existing cloud databases.
"""
import os
import sys
from datetime import datetime

def fix_migration_history():
    db_url = os.environ.get('DATABASE_URL', '')

    if db_url.startswith(('postgres://', 'postgresql://')):
        try:
            import psycopg2
            conn = psycopg2.connect(db_url, sslmode=os.environ.get('DB_SSLMODE', 'prefer'))
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'django_migrations'
                    );
                """)
                if not cursor.fetchone()[0]:
                    print("pre_migrate: Fresh Postgres database (no django_migrations table).")
                    conn.close()
                    return

                # 1. Update any legacy app name 'channels' to 'app_channels'
                cursor.execute("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")

                # 2. Check if accounts_user table already has basin_id column
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'accounts_user' AND column_name = 'basin_id'
                    );
                """)
                if cursor.fetchone()[0]:
                    for mig_name in ['0001_initial', '0002_initial']:
                        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'accounts' AND name = %s;", [mig_name])
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('accounts', %s, NOW());", [mig_name])
                            print(f"pre_migrate: Registered accounts.{mig_name} (schema already present).")

                # 3. Check if app_channels tables exist
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name IN ('app_channels_channel', 'channels_channel')
                    );
                """)
                if cursor.fetchone()[0]:
                    for mig_name in ['0001_initial', '0002_initial']:
                        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'app_channels' AND name = %s;", [mig_name])
                        if cursor.fetchone()[0] == 0:
                            cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('app_channels', %s, NOW());", [mig_name])
                            print(f"pre_migrate: Registered app_channels.{mig_name}.")

                # 4. Check if patients tables exist
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'patients_patient'
                    );
                """)
                if cursor.fetchone()[0]:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'patients' AND name = '0001_initial';")
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("INSERT INTO django_migrations (app, name, applied) VALUES ('patients', '0001_initial', NOW());")
                        print("pre_migrate: Registered patients.0001_initial.")

                # 5. Clean up any obsolete migration rows that no longer exist in the repo
                cursor.execute("""
                    DELETE FROM django_migrations 
                    WHERE (app = 'accounts' AND name NOT IN ('0001_initial', '0002_initial'))
                       OR (app = 'app_channels' AND name NOT IN ('0001_initial', '0002_initial'))
                       OR (app = 'patients' AND name NOT IN ('0001_initial'));
                """)

            conn.close()
            print("pre_migrate: Postgres migration history successfully aligned with current codebase.")
        except Exception as e:
            print(f"pre_migrate Postgres note: {e}")

    else:
        # SQLite database check
        try:
            import sqlite3
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db.sqlite3')
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                with conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations';")
                    if cursor.fetchone():
                        cursor.execute("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")
                conn.close()
                print("pre_migrate: SQLite checked.")
        except Exception as e:
            print(f"pre_migrate SQLite note: {e}")

if __name__ == '__main__':
    fix_migration_history()
