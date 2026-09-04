"""
Pre-migration compatibility script.
Fixes legacy schema/migration state in django_migrations on PostgreSQL (Neon) and SQLite
to guarantee clean, idempotent migrations on existing cloud databases.
"""
import os 
import sys 

def fix_migration_history ():
    db_url =os .environ .get ('DATABASE_URL','')

    if db_url .startswith (('postgres://','postgresql://')):
        try :
            import psycopg2 
            conn =psycopg2 .connect (db_url ,sslmode =os .environ .get ('DB_SSLMODE','prefer'))
            conn .autocommit =True 
            with conn .cursor ()as cursor :
                cursor .execute ("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'django_migrations'
                    );
                """)
                if not cursor .fetchone ()[0 ]:
                    print ("pre_migrate: Fresh Postgres database (no django_migrations table).")
                    conn .close ()
                    return 

                    # Comment_585
                channel_tables =[
                ('channels_channel','app_channels_channel'),
                ('channels_channelmembership','app_channels_channelmembership'),
                ('channels_channelmessage','app_channels_channelmessage'),
                ('channels_channelinvitation','app_channels_channelinvitation'),
                ]
                for old_name ,new_name in channel_tables :
                    cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);",[old_name ])
                    old_exists =cursor .fetchone ()[0 ]
                    cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = %s);",[new_name ])
                    new_exists =cursor .fetchone ()[0 ]
                    if old_exists and not new_exists :
                        cursor .execute (f"ALTER TABLE {old_name } RENAME TO {new_name };")
                        print (f"pre_migrate: Renamed table {old_name } -> {new_name }")

                        # Comment_586
                cursor .execute ("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")

                # Comment_587
                cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_auditlog');")
                if cursor .fetchone ()[0 ]:
                    audit_columns =[
                    ("mac_address","VARCHAR(100) DEFAULT ''"),
                    ("device_fingerprint","VARCHAR(255) DEFAULT ''"),
                    ("hostname","VARCHAR(255) DEFAULT ''"),
                    ("os_info","VARCHAR(255) DEFAULT ''"),
                    ("browser_info","VARCHAR(255) DEFAULT ''"),
                    ("screen_resolution","VARCHAR(50) DEFAULT ''"),
                    ("timezone_offset","VARCHAR(50) DEFAULT ''"),
                    ("language","VARCHAR(50) DEFAULT ''"),
                    ("session_id","VARCHAR(255) DEFAULT ''"),
                    ("geo_location","VARCHAR(255) DEFAULT ''"),
                    ("risk_score","DOUBLE PRECISION DEFAULT 0.0"),
                    ]
                    for col_name ,col_type in audit_columns :
                        cursor .execute (f"ALTER TABLE audit_auditlog ADD COLUMN IF NOT EXISTS {col_name } {col_type };")
                    print ("pre_migrate: Ensured all forensic columns exist in audit_auditlog.")

                    # Comment_588
                cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'app_channels_channel');")
                if not cursor .fetchone ()[0 ]:
                    cursor .execute ("DELETE FROM django_migrations WHERE app = 'app_channels';")
                    print ("pre_migrate: Table app_channels_channel not found. Reset app_channels migrations to create table.")
                else :
                    for mig in ['0001_initial','0002_initial']:
                        cursor .execute ("SELECT COUNT(*) FROM django_migrations WHERE app = 'app_channels' AND name = %s;",[mig ])
                        if cursor .fetchone ()[0 ]==0 :
                            cursor .execute ("INSERT INTO django_migrations (app, name, applied) VALUES ('app_channels', %s, NOW());",[mig ])

                            # Comment_589
                cursor .execute ("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'accounts_user' AND column_name = 'basin_id'
                    );
                """)
                if cursor .fetchone ()[0 ]:
                    for mig in ['0001_initial','0002_initial']:
                        cursor .execute ("SELECT COUNT(*) FROM django_migrations WHERE app = 'accounts' AND name = %s;",[mig ])
                        if cursor .fetchone ()[0 ]==0 :
                            cursor .execute ("INSERT INTO django_migrations (app, name, applied) VALUES ('accounts', %s, NOW());",[mig ])
                            print (f"pre_migrate: Registered accounts.{mig } (column basin_id exists).")

                            # Comment_590
                cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'patients_patient');")
                if cursor .fetchone ()[0 ]:
                    cursor .execute ("SELECT COUNT(*) FROM django_migrations WHERE app = 'patients' AND name = '0001_initial';")
                    if cursor .fetchone ()[0 ]==0 :
                        cursor .execute ("INSERT INTO django_migrations (app, name, applied) VALUES ('patients', '0001_initial', NOW());")
                else :
                    cursor .execute ("DELETE FROM django_migrations WHERE app = 'patients';")

                    # Comment_591
                cursor .execute ("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'appointments_appointment');")
                if not cursor .fetchone ()[0 ]:
                    cursor .execute ("DELETE FROM django_migrations WHERE app = 'appointments';")

                    # Comment_592
                cursor .execute ("""
                    DELETE FROM django_migrations 
                    WHERE (app = 'accounts' AND name NOT IN ('0001_initial', '0002_initial'))
                       OR (app = 'app_channels' AND name NOT IN ('0001_initial', '0002_initial'))
                       OR (app = 'patients' AND name NOT IN ('0001_initial'))
                       OR (app = 'appointments' AND name NOT IN ('0001_initial'))
                       OR (app = 'pharmacy' AND name NOT IN ('0001_initial'))
                       OR (app = 'billing' AND name NOT IN ('0001_initial'));
                """)

            conn .close ()
            print ("pre_migrate: Postgres migration history successfully aligned with current codebase.")
        except Exception as e :
            print (f"pre_migrate Postgres note: {e }")

    else :
    # Comment_593
        try :
            import sqlite3 
            db_path =os .path .join (os .path .dirname (os .path .dirname (os .path .abspath (__file__ ))),'db.sqlite3')
            if os .path .exists (db_path ):
                conn =sqlite3 .connect (db_path )
                with conn :
                    cursor =conn .cursor ()
                    cursor .execute ("SELECT name FROM sqlite_master WHERE type='table' AND name='django_migrations';")
                    if cursor .fetchone ():
                        cursor .execute ("UPDATE django_migrations SET app = 'app_channels' WHERE app = 'channels';")
                conn .close ()
                print ("pre_migrate: SQLite checked.")
        except Exception as e :
            print (f"pre_migrate SQLite note: {e }")

if __name__ =='__main__':
    fix_migration_history ()
