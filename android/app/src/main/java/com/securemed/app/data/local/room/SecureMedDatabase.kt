package com.securemed.app.data.local.room

import androidx.room.Database
import androidx.room.RoomDatabase

/**
 * On-device mirror of data the server owns — patients, records and appointments —
 * kept so the app stays readable with no connectivity. Nothing here is the only
 * copy of anything: medication plans and dose logs, which *are* device-only, live
 * in [com.securemed.app.data.local.MedicationStore] instead.
 *
 * That distinction is what licenses the destructive upgrade policy in
 * `DatabaseModule`, and what makes the file safe to delete outright when its
 * SQLCipher passphrase is lost (`SecurePreferences.init`).
 */
@Database(
    entities = [
        PatientEntity::class,
        MedicalRecordEntity::class,
        AppointmentEntity::class
    ],
    version = 1,
    exportSchema = false
)
abstract class SecureMedDatabase : RoomDatabase() {
    abstract fun secureMedDao(): SecureMedDao

    companion object {
        /**
         * One spelling of the file name, because two places need it: the builder
         * that opens it and the recovery path that deletes it by name after the
         * passphrase is gone.
         */
        const val DATABASE_NAME = "securemed_local_db"
    }
}
