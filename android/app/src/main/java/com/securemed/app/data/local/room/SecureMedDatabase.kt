package com.securemed.app.data.local.room

import androidx.room.Database
import androidx.room.RoomDatabase

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
}
