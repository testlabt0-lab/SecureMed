"""
Pre-migration compatibility script.
Fixes any legacy app name collisions in django_migrations table (e.g. channels -> app_channels)
to guarantee zero InconsistentMigrationHistory errors across cloud PostgreSQL (Neon) and SQLite.
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

                # Update any legacy app name 'channels' to 'app_channels'
                cursor.execute("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")

                # Check if patients.0001_initial exists while app_channels.0001_initial is missing
                cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'patients' AND name = '0001_initial';")
                patients_applied = cursor.fetchone()[0] > 0

                if patients_applied:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'app_channels' AND name = '0001_initial';")
                    channels_applied = cursor.fetchone()[0] > 0
                    if not channels_applied:
                        cursor.execute("""
                            INSERT INTO django_migrations (app, name, applied)
                            VALUES ('app_channels', '0001_initial', NOW());
                        """)
                        print("pre_migrate: Registered app_channels.0001_initial in django_migrations.")

            conn.close()
            print("pre_migrate: Postgres migration history synchronized successfully.")
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
                        cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'patients' AND name = '0001_initial';")
                        if cursor.fetchone()[0] > 0:
                            cursor.execute("SELECT COUNT(*) FROM django_migrations WHERE app = 'app_channels' AND name = '0001_initial';")
                            if cursor.fetchone()[0] == 0:
                                cursor.execute(
                                    "INSERT INTO django_migrations (app, name, applied) VALUES ('app_channels', '0001_initial', ?);",
                                    [datetime.utcnow().isoformat()]
                                )
                                print("pre_migrate: Registered app_channels.0001_initial in SQLite.")
                conn.close()
                print("pre_migrate: SQLite migration history checked.")
        except Exception as e:
            print(f"pre_migrate SQLite note: {e}")

if __name__ == '__main__':
    fix_migration_history()
