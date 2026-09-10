package com.securemed.app.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

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

/**
 * The pair a completed sign-in hands over. Both halves are required, and
 * deliberately so: a session with no refresh token dies at the first 401, fifteen
 * minutes in, and it is better to fail the login loudly than to open one.
 *
 * `auth/refresh/` answers with a different shape — see [RefreshResponse].
 */
@Serializable
data class TokenPair(
    val access: String,
    val refresh: String
)

/**
 * `auth/refresh/`: a new access token, and a new refresh token *only when the
 * server rotates*.
 *
 * `RefreshTokenView` builds `{'access': …}` and adds `refresh` inside
 * `if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS')`
 * (`backend/apps/accounts/views.py:386-405`). Rotation is on in both settings
 * files today, which is the only reason decoding this as a [TokenPair] worked:
 * with rotation off, the required `refresh` field made kotlinx-serialization
 * throw MissingFieldException, the authenticator read that as an unrecoverable
 * session and cleared the tokens — sending every mobile user back to the login
 * screen every fifteen minutes, on a server setting that says nothing about
 * mobile.
 */
@Serializable
data class RefreshResponse(
    val access: String,
    val refresh: String? = null
)

/**
 * Two different bodies share one 200 response on `auth/login/`.
 *
 * A completed sign-in carries `tokens` + `user`. A sign-in that still needs a
 * second factor carries `requires_2fa`, a short-lived `mfa_token` and the
 * `method` chosen by the server ("email" for a mailed OTP, "totp" for an
 * authenticator app) — and no tokens at all. The server picks the second path
 * whenever the account has MFA enabled *or* adaptive MFA fires on a new or
 * untrusted device, so it is not an edge case.
 *
 * Every field is therefore optional. While `tokens`/`user` were required,
 * kotlinx-serialization threw MissingFieldException on the 2FA body and the
 * repository turned that into a generic "login failed" — an account with MFA
 * could not sign in and the reason was invisible.
 */
@Serializable
data class LoginResponse(
    val tokens: TokenPair? = null,
    val user: User? = null,
    @SerialName("requires_biometric") val requiresBiometric: Boolean = false,
    @SerialName("requires_2fa") val requiresTwoFactor: Boolean = false,
    @SerialName("mfa_token") val mfaToken: String? = null,
    val method: String? = null,
    val detail: String? = null
) {
    /** True only when a session can actually be opened from this response. */
    val isAuthenticated: Boolean get() = tokens != null && user != null
}

@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

/**
 * Completing a sign-in the server answered with `requires_2fa`.
 *
 * [mfaToken] is the handle from [LoginResponse.mfaToken]. The server holds the
 * user id under `mfa_pending:{token}` for 300 seconds and deletes it on the
 * first success, so this body is single-use and short-lived: a 401 means the
 * handle is gone and the password step has to run again
 * (`backend/apps/accounts/views.py:814-821`).
 *
 * [code] is six digits either way — the mailed OTP when the server chose
 * `method = "email"`, or the authenticator's TOTP when it chose `"totp"`. The
 * server tries the mailed code first and only falls back to TOTP when none is
 * cached (`views.py:831-842`), so the client does not have to say which kind it
 * is holding.
 *
 * [trustDevice] marks this device trusted so adaptive MFA stops challenging it.
 * It only has an effect on a request that also carries `X-Device-Fingerprint`:
 * the server looks the device row up by that header and silently skips the
 * update when it is absent (`views.py:855-862`). The app sends the header on
 * every request now, so the flag does work — and it has to be offered, because
 * `DeviceRegistry.is_trusted` defaults to false and the adaptive branch fires on
 * `is_new_device or not device.is_trusted` (`views.py:215`): without a way to
 * trust the device, every single login would wait on a mailed code.
 *
 * It changes nothing for an account with TOTP enabled — `mfa_enabled` is tested
 * first and always demands a code — so the UI offers the option only for the
 * `email` method, where it is the difference the user can actually feel.
 */
@Serializable
data class MfaLoginRequest(
    @SerialName("mfa_token") val mfaToken: String,
    val code: String,
    @SerialName("trust_device") val trustDevice: Boolean = false
)

@Serializable
data class BiometricChallengeRequest(
    val email: String,
    @SerialName("device_id") val deviceId: String
)

/**
 * The challenge to sign.
 *
 * The server also returns `rp_id`, `allow_credentials` and `user_verification`,
 * which only the browser ceremony consumes; unknown keys are ignored by the
 * Retrofit Json, so they are deliberately absent here. [timeout] is milliseconds
 * and mirrors the row's real TTL — a challenge is single-use and burned by the
 * server on first presentation, so a stale one cannot be retried.
 *
 * An unknown email or an unenrolled device gets a well-formed decoy backed by no
 * database row, indistinguishable from the real thing on purpose. The client must
 * not try to interpret that: it signs and lets the server refuse.
 */
@Serializable
data class BiometricChallengeResponse(
    @SerialName("challenge_id") val challengeId: String,
    val challenge: String,
    val timeout: Long = 0
)

/**
 * A native assertion: the id of the challenge, and an ECDSA P-256 signature over
 * its raw bytes, base64url.
 *
 * The retired shape carried `biometric_response` — a string the client built out
 * of the challenge id — and `biometric_template`, a fresh random value per call.
 * Neither was a signature, so the server could only ever have compared strings.
 */
@Serializable
data class BiometricLoginRequest(
    @SerialName("challenge_id") val challengeId: String,
    val signature: String
)

/**
 * Enrollment: the public half of the Keystore key pair, base64url SPKI DER.
 *
 * `biometric_template` is gone. Sending a fingerprint template — or any stand-in
 * for one — to a server is precisely what a biometric authenticator exists to
 * avoid: the raw trait cannot be revoked once it leaks.
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

/** One message in a channel's secure discussion thread. */
@Serializable
data class ChannelMessage(
    val id: String,
    val channel: String,
    val sender: String,
    @SerialName("sender_name") val senderName: String = "",
    @SerialName("sender_role_display") val senderRoleDisplay: String = "",
    val body: String,
    @SerialName("is_edited") val isEdited: Boolean = false,
    @SerialName("is_system") val isSystem: Boolean = false,
    @SerialName("created_at") val createdAt: String
)

/** Server twin of a device-local medication plan (pharmacy sync endpoint). */
@Serializable
data class MedicationPlanDto(
    val id: String,
    @SerialName("source_id") val sourceId: String? = null,
    @SerialName("patient_id") val patientId: String,
    @SerialName("patient_name") val patientName: String,
    val name: String,
    val dosage: String,
    val times: List<String> = emptyList(),
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    val instructions: String = "",
    @SerialName("is_active") val isActive: Boolean = true,
    @SerialName("prescribed_by") val prescribedBy: String = "",
    @SerialName("created_at") val createdAt: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null
)

/** Push body for pharmacy/medication-plans/ (upsert by source_id). */
@Serializable
data class MedicationPlanUpsert(
    @SerialName("patient_id") val patientId: String,
    val name: String,
    val dosage: String,
    val times: List<String>,
    @SerialName("start_date") val startDate: String,
    @SerialName("end_date") val endDate: String? = null,
    val instructions: String = "",
    @SerialName("source_id") val sourceId: String? = null,
    @SerialName("is_active") val isActive: Boolean = true
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
    /**
     * `created_by` on the server is nullable (a deleted or system actor), so
     * `created_by_name` can arrive as null — as a required field that dropped
     * every such record, then the whole list (م10).
     */
    @SerialName("created_by_name") val createdByName: String? = null,
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
    /**
     * The server column is a free JSONField — numbers or nested objects in it
     * made the strict Map<String, String> throw and the whole list with it
     * (م10). Parsed as a generic element so any JSON value decodes.
     */
    val data: JsonElement? = null
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

@Serializable
data class DeviceCheckRequest(
    @SerialName("device_fingerprint") val deviceFingerprint: String,
    @SerialName("mac_address") val macAddress: String? = null,
    val email: String? = null
)

@Serializable
data class DeviceCheckResponse(
    val state: String? = null,
    val authorized: Boolean,
    val detail: String? = null
)

/** أحد أجهزة المستخدم المسجلة (من security/my-devices/). */
data class MyDevice(
    val id: String,
    @SerialName("device_fingerprint") val deviceFingerprint: String,
    @SerialName("os_info") val osInfo: String? = null,
    @SerialName("browser_info") val browserInfo: String? = null,
    @SerialName("last_ip_address") val lastIpAddress: String? = null,
    @SerialName("is_trusted") val isTrusted: Boolean = false,
    @SerialName("mac_address") val macAddress: String? = null,
)

data class MyDevicesResponse(
    val devices: List<MyDevice> = emptyList()
)

data class RemoveDeviceRequest(
    @SerialName("device_fingerprint") val deviceFingerprint: String
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

@Serializable
data class PatientCreateRequest(
    @SerialName("full_name") val fullName: String,
    @SerialName("date_of_birth") val dateOfBirth: String,
    val gender: String,
    @SerialName("blood_type") val bloodType: String? = null,
    val phone: String? = null,
    @SerialName("chronic_conditions") val chronicConditions: String? = null
)

@Serializable
data class MedicalRecordCreateRequest(
    val title: String,
    val content: String,
    @SerialName("record_type") val recordType: String,
    @SerialName("is_critical") val isCritical: Boolean = false,
    /**
     * The server field is `channel` (`MedicalRecordSerializer.Meta.fields`);
     * this used to be sent as `channel_id`, which the serializer rejected with
     * a 400 about the missing `channel` — every queued offline record failed
     * forever.
     */
    val channel: String
)

/** Partial update of `PATCH patients/records/{id}/` — all fields optional. */
@Serializable
data class MedicalRecordUpdateRequest(
    val title: String? = null,
    val content: String? = null,
    @SerialName("record_type") val recordType: String? = null,
    @SerialName("is_critical") val isCritical: Boolean? = null
)

/**
 * `GET patients/{id}/profile/` — the patient-scoped aggregate.
 *
 * `records` holds only records of channels this patient actually belongs to
 * and the caller may view (`PatientViewSet.profile` → `get_viewable_channels`),
 * which is what makes the patient page attribute records correctly (ع6).
 */
@Serializable
data class PatientProfileResponse(
    val patient: Patient,
    val records: List<MedicalRecord> = emptyList(),
    val channels: List<Channel> = emptyList(),
    val files: List<PatientFileInfo> = emptyList(),
    val stats: PatientProfileStats? = null
)

@Serializable
data class PatientFileInfo(
    val id: String,
    val title: String = "",
    @SerialName("file_name") val fileName: String = "",
    @SerialName("file_type") val fileType: String = "",
    @SerialName("file_type_display") val fileTypeDisplay: String = "",
    @SerialName("file_size") val fileSize: Long = 0,
    @SerialName("is_critical") val isCritical: Boolean = false,
    @SerialName("uploaded_at") val uploadedAt: String = ""
)

@Serializable
data class PatientProfileStats(
    @SerialName("total_records") val totalRecords: Int = 0,
    @SerialName("total_channels") val totalChannels: Int = 0,
    @SerialName("total_files") val totalFiles: Int = 0
)

/** Body of `POST appointments/` (`AppointmentCreateSerializer`). */
@Serializable
data class AppointmentCreateRequest(
    val patient: String,
    val doctor: String,
    @SerialName("appointment_type") val appointmentType: String,
    val priority: String = "MEDIUM",
    val status: String = "SCHEDULED",
    /** ISO-8601 local date-time, e.g. 2026-09-10T14:30:00 — must be in the future. */
    @SerialName("scheduled_at") val scheduledAt: String,
    @SerialName("duration_minutes") val durationMinutes: Int = 30,
    val title: String = "",
    val notes: String? = null,
    val location: String? = null,
    @SerialName("is_virtual") val isVirtual: Boolean = false
)
