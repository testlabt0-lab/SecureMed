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
    @SerialName("is_biometric_enabled") val isBiometricEnabled: Boolean = false
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
