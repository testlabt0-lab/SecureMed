package com.securemed.app.data.local.room

import androidx.room.Database
import androidx.room.RoomDatabase

/**
 * On-device mirror of data the server owns — patients, records and appointments —
 * kept so the app stays readable with no connectivity. Since 3-4 it also owns
 * the device-only medication tables: plans and dose logs moved out of the
 * encrypted JSON files (`LocalCache`) into [MedicationPlanEntity] and
 * [DoseLogEntity], with a one-time migration that carries the old rows over.
 *
 * The distinction still matters for the upgrade policy: the mirrored entities
 * are refetchable copies, while the medication tables are the ONLY copy of a
 * device-first feature — which is why the JSON→Room migration runs before any
 * destructive fallback could touch them (see `DatabaseModule`).
 */
@Database(
    entities = [
        PatientEntity::class,
        MedicalRecordEntity::class,
        AppointmentEntity::class,
        PendingSyncActionEntity::class,
        MedicationPlanEntity::class,
        DoseLogEntity::class
    ],
    version = 3,
    exportSchema = false
)
abstract class SecureMedDatabase : RoomDatabase() {
    abstract fun secureMedDao(): SecureMedDao
    abstract fun medicationDao(): MedicationDao

    companion object {
        /**
         * One spelling of the file name, because two places need it: the builder
         * that opens it and the recovery path that deletes it by name after the
         * passphrase is gone.
         */
        const val DATABASE_NAME = "securemed_local_db"

        /**
         * Version of the database layout the JSON→Room migration writes. The
         * migrator checks this so a future schema bump does not silently
         * import rows into a table shape it no longer matches.
         */
        const val MIGRATION_TARGET_VERSION = 3
    }
}
