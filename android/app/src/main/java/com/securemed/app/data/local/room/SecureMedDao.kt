package com.securemed.app.data.local.room

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface SecureMedDao {
    // Patients
    @Query("SELECT * FROM patients")
    suspend fun getAllPatients(): List<PatientEntity>

    @Query("SELECT * FROM patients WHERE id = :id LIMIT 1")
    suspend fun getPatientById(id: String): PatientEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertPatients(patients: List<PatientEntity>)

    @Query("DELETE FROM patients")
    suspend fun clearPatients()

    // Medical Records
    @Query("SELECT * FROM medical_records WHERE channelId = :channelId ORDER BY createdAt DESC")
    suspend fun getRecordsByChannel(channelId: String): List<MedicalRecordEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertRecords(records: List<MedicalRecordEntity>)

    @Query("DELETE FROM medical_records")
    suspend fun clearRecords()
}
