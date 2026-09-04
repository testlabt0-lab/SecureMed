package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class User(
    val id: String,
    val email: String,
    @SerialName("full_name") val fullName: String,
    val role: String,
    val phone: String? = null,
    @SerialName("license_number") val licenseNumber: String? = null,
    val department: String? = null,
    val specialization: String? = null,
    @SerialName("is_biometric_enabled") val isBiometricEnabled: Boolean = false,
    @SerialName("is_active") val isActive: Boolean = true
)

@Serializable
data class TokenPair(
    val access: String,
    val refresh: String
)

@Serializable
data class LoginResponse(
    val tokens: TokenPair,
    val user: User,
    @SerialName("requires_biometric") val requiresBiometric: Boolean = false
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

@Serializable
data class BiometricChallengeRequest(
    val email: String,
    @SerialName("device_id") val deviceId: String
)

@Serializable
data class BiometricChallengeResponse(
    @SerialName("challenge_id") val challengeId: String,
    val challenge: String
)

@Serializable
data class BiometricLoginRequest(
    @SerialName("challenge_id") val challengeId: String,
    @SerialName("biometric_response") val biometricResponse: String,
    @SerialName("biometric_template") val biometricTemplate: String
)

@Serializable
data class BiometricEnrollRequest(
    @SerialName("device_id") val deviceId: String,
    @SerialName("device_name") val deviceName: String,
    val platform: String,
    @SerialName("biometric_template") val biometricTemplate: String
)

@Serializable
data class Channel(
    val id: String,
    val name: String,
    val description: String? = null,
    @SerialName("channel_type") val channelType: String,
    @SerialName("channel_type_display") val channelTypeDisplay: String,
    @SerialName("current_user_role") val currentUserRole: String? = null,
    val status: String,
    @SerialName("status_display") val statusDisplay: String,
    val priority: String,
    @SerialName("members_count") val membersCount: Int = 0,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class Patient(
    val id: String,
    @SerialName("full_name") val fullName: String,
    @SerialName("date_of_birth") val dateOfBirth: String,
    val gender: String,
    @SerialName("blood_type") val bloodType: String? = null,
    val age: Int? = null,
    val phone: String? = null,
    @SerialName("chronic_conditions") val chronicConditions: String? = null
)

@Serializable
data class ChannelMembership(
    val id: String,
    val user: User,
    val role: String,
    @SerialName("role_display") val roleDisplay: String,
    @SerialName("is_active") val isActive: Boolean
)

@Serializable
data class MedicalRecord(
    val id: String,
    val title: String,
    val content: String,
    @SerialName("record_type") val recordType: String,
    @SerialName("record_type_display") val recordTypeDisplay: String,
    @SerialName("created_by_name") val createdByName: String,
    @SerialName("is_critical") val isCritical: Boolean = false,
    @SerialName("created_at") val createdAt: String
)


@Serializable
data class Notification(
    val id: String,
    @SerialName("notification_type") val notificationType: String,
    val priority: String = "MEDIUM",
    val title: String,
    val message: String,
    @SerialName("is_read") val isRead: Boolean = false,
    @SerialName("created_at") val createdAt: String,
    val data: Map<String, String>? = null
)

@Serializable
data class DashboardStats(
    @SerialName("total_users") val totalUsers: Int,
    @SerialName("active_users") val activeUsers: Int,
    @SerialName("total_channels") val totalChannels: Int,
    @SerialName("active_channels") val activeChannels: Int,
    @SerialName("total_patients") val totalPatients: Int,
    @SerialName("new_patients_today") val newPatientsToday: Int,
    @SerialName("total_medical_records") val totalMedicalRecords: Int,
    @SerialName("security_alerts_today") val securityAlertsToday: Int,
    @SerialName("waf_blocks_today") val wafBlocksToday: Int,
    @SerialName("biometric_logins_today") val biometricLoginsToday: Int
)

/**
 * Envelope for the backend's paginated list responses
 * (SecureMedPagination: count/page/results…).
 */
@Serializable
data class PagedResponse<T>(
    val count: Int = 0,
    val page: Int = 1,
    @SerialName("page_size") val pageSize: Int = 20,
    @SerialName("total_pages") val totalPages: Int = 1,
    @SerialName("has_next") val hasNext: Boolean = false,
    @SerialName("has_previous") val hasPrevious: Boolean = false,
    val results: List<T> = emptyList()
)

// ===== Medication plans (device-local; reminders work offline) =====

/**
 * A medication plan created on this device by an authorized clinician.
 * Persisted locally so dose alarms fire even without connectivity and
 * are re-armed after reboot by [com.securemed.app.reminders.BootReceiver].
 */
@Serializable
data class Medication(
    val id: String,
    @SerialName("patient_id") val patientId: String,
    @SerialName("patient_name") val patientName: String,
    val name: String,
    val dosage: String,
    val times: List<String> = emptyList(),
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    val instructions: String = "",
    @SerialName("prescribed_by") val prescribedByName: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("created_at") val createdAt: String
)

/** Outcome of one scheduled dose on a given day. */
@Serializable
data class MedicationDoseLog(
    val key: String,
    @SerialName("plan_id") val planId: String,
    val date: String,
    val time: String,
    val status: String,
    @SerialName("logged_at") val loggedAt: String
)

/** A single dose card shown in "today's doses". */
@Serializable
data class TodayDose(
    @SerialName("medication_id") val medicationId: String,
    @SerialName("medication_name") val medicationName: String,
    val dosage: String,
    @SerialName("patient_name") val patientName: String,
    val time: String,
    /** ISO local date-time of the scheduled dose, e.g. 2026-09-02T08:00:00. */
    @SerialName("scheduled_for") val scheduledFor: String,
    val status: String,
    val instructions: String = ""
)

@Serializable
data class TodayDosesResponse(
    val doses: List<TodayDose> = emptyList()
)

/** 7-day adherence summary computed from local dose logs. */
@Serializable
data class AdherenceStats(
    @SerialName("total_doses") val totalDoses: Int,
    @SerialName("taken_doses") val takenDoses: Int,
    @SerialName("adherence_percent") val adherencePercent: Int
)
