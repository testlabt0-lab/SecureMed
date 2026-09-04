package com.securemed.app.data.local.room

import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Local representation of a Patient.
 */
@Entity(tableName = "patients")
data class PatientEntity(
    @PrimaryKey val id: String,
    val fullName: String,
    val email: String,
    val dateOfBirth: String,
    val nationalId: String?,
    val insuranceNumber: String?,
    val phoneNumber: String?,
    val isHighRisk: Boolean
)

/**
 * Local representation of a Medical Record.
 */
@Entity(tableName = "medical_records")
data class MedicalRecordEntity(
    @PrimaryKey val id: String,
    val patientId: String,
    val channelId: String?,
    val recordType: String,
    val contentSummary: String,
    val diagnosis: String?,
    val createdBy: String,
    val createdAt: String,
    val encryptedDataBlob: String? // For E2E encrypted records
)

/**
 * Local representation of an Appointment.
 */
@Entity(tableName = "appointments")
data class AppointmentEntity(
    @PrimaryKey val id: String,
    val patientId: String,
    val providerId: String,
    val scheduledTime: String,
    val type: String,
    val status: String
)
