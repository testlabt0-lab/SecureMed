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

/** Wrapper for paginated user lists (DRF page style: count/next/previous/results). */
@Serializable
data class PaginatedUsers(
    val count: Int = 0,
    @SerialName("next") val next: String? = null,
    @SerialName("previous") val previous: String? = null,
    val results: List<User> = emptyList()
)

@Serializable
data class ChangePasswordRequest(
    @SerialName("old_password") val oldPassword: String,
    @SerialName("new_password") val newPassword: String,
    @SerialName("confirm_password") val confirmPassword: String
)

@Serializable
data class TokenPair(
    val access: String,
    val refresh: String
)

/** Generic DRF paginated response wrapper: {count, page, ..., results} */
@Serializable
data class Paginated<T>(
    val count: Int = 0,
    val results: List<T> = emptyList()
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

/**
 * Login with biometrics = sign the server challenge with the private
 * EC key stored in the Android Keystore (unlocked by the fingerprint).
 */
@Serializable
data class BiometricLoginRequest(
    @SerialName("challenge_id") val challengeId: String,
    val signature: String
)

/**
 * Enrollment submits the PUBLIC key (base64 DER SubjectPublicKeyInfo)
 * of the biometric-gated Keystore key. Raw biometric data never leaves
 * the device.
 */
@Serializable
data class BiometricEnrollRequest(
    @SerialName("device_id") val deviceId: String,
    @SerialName("device_name") val deviceName: String,
    val platform: String,
    @SerialName("public_key") val publicKey: String
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

// ============================================================
// Chat (in-channel secure messaging)
// ============================================================

@Serializable
data class ChatMessage(
    val id: String,
    val channel: String,
    val sender: String,
    @SerialName("sender_name") val senderName: String,
    @SerialName("sender_role") val senderRole: String = "",
    @SerialName("sender_role_display") val senderRoleDisplay: String = "",
    val body: String,
    @SerialName("is_system") val isSystem: Boolean = false,
    @SerialName("created_at") val createdAt: String
)

@Serializable
data class ChatMessageRequest(val body: String)

// ============================================================
// Medications + reminders
// ============================================================

@Serializable
data class Medication(
    val id: String,
    val patient: String,
    @SerialName("patient_name") val patientName: String,
    val channel: String? = null,
    @SerialName("channel_name") val channelName: String? = null,
    val name: String,
    val dosage: String,
    @SerialName("dose_times") val doseTimes: String = "08:00",
    val times: List<String> = emptyList(),
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    val instructions: String = "",
    @SerialName("prescribed_by_name") val prescribedByName: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("is_scheduled_today") val isScheduledToday: Boolean = false
)

@Serializable
data class MedicationCreateRequest(
    val patient: String,
    val channel: String? = null,
    val name: String,
    val dosage: String,
    @SerialName("dose_times") val doseTimes: String,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    val instructions: String = ""
)

/** GET medications/today/ → {date, doses: [...]} */
@Serializable
data class TodayDosesResponse(
    val date: String = "",
    val doses: List<TodayDose> = emptyList()
)

@Serializable
data class TodayDose(
    @SerialName("medication_id") val medicationId: String,
    @SerialName("patient_id") val patientId: String,
    @SerialName("patient_name") val patientName: String,
    @SerialName("medication_name") val medicationName: String,
    val dosage: String,
    val instructions: String = "",
    val time: String,
    @SerialName("scheduled_for") val scheduledFor: String,
    val status: String,
    @SerialName("log_id") val logId: String? = null
)

@Serializable
data class LogDoseRequest(
    @SerialName("medication_id") val medicationId: String,
    @SerialName("scheduled_for") val scheduledFor: String,
    val status: String,
    val notes: String = ""
)

@Serializable
data class MedicationLogResponse(
    val id: String,
    val medication: String,
    @SerialName("medication_name") val medicationName: String = "",
    @SerialName("scheduled_for") val scheduledFor: String,
    val status: String,
    @SerialName("status_display") val statusDisplay: String = "",
    @SerialName("taken_at") val takenAt: String? = null
)

@Serializable
data class AdherenceStats(
    val days: Int = 7,
    @SerialName("total_doses") val totalDoses: Int = 0,
    @SerialName("taken_doses") val takenDoses: Int = 0,
    @SerialName("adherence_percent") val adherencePercent: Double = 0.0
)
