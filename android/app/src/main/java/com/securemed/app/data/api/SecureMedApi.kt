package com.securemed.app.data.api

import com.securemed.app.data.model.*
import kotlinx.serialization.json.JsonObject
import retrofit2.http.*

/**
 * Retrofit API interface for SecureMed backend.
 *
 * List endpoints return [PagedResponse] because the backend wraps every
 * collection in SecureMedPagination ({count, page, results…}).
 */
interface SecureMedApi {

    // ===== AUTH =====
    @POST("auth/login/")
    suspend fun login(@Body request: LoginRequest): LoginResponse

    /**
     * Second leg of a `requires_2fa` login. Returns the same [LoginResponse]
     * shape as `auth/login/`, but always with tokens — the server answers 400
     * for a wrong code and 401 once the 5-minute `mfa_token` has expired.
     */
    @POST("auth/2fa/login/")
    suspend fun mfaLogin(@Body request: MfaLoginRequest): LoginResponse

    @POST("auth/logout/")
    suspend fun logout(@Body body: Map<String, String>): Unit

    /**
     * Unused: the refresh that keeps a session alive runs through OkHttp's
     * Authenticator in [NetworkModule], which must not recurse back into this
     * client. Kept declared so the endpoint is visible here, and typed as
     * [RefreshResponse] rather than [TokenPair] so any future caller inherits the
     * rotation-dependent shape instead of the bug it caused.
     */
    @POST("auth/refresh/")
    suspend fun refreshToken(@Body body: Map<String, String>): RefreshResponse

    @GET("auth/users/me/")
    suspend fun getCurrentUser(): User

    @GET("auth/users/")
    suspend fun getUsers(): PagedResponse<User>

    @POST("auth/users/{id}/activate/")
    suspend fun activateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/users/{id}/deactivate/")
    suspend fun deactivateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/biometric/enroll/")
    suspend fun enrollBiometric(@Body request: BiometricEnrollRequest): Unit

    @POST("auth/biometric/challenge/")
    suspend fun getBiometricChallenge(@Body request: BiometricChallengeRequest): BiometricChallengeResponse

    @POST("auth/biometric/login/")
    suspend fun biometricLogin(@Body request: BiometricLoginRequest): LoginResponse

    // ===== CHANNELS =====
    @GET("channels/")
    suspend fun getChannels(): PagedResponse<Channel>

    @GET("channels/{id}/")
    suspend fun getChannel(@Path("id") id: String): Channel

    @GET("channels/{id}/members/")
    suspend fun getChannelMembers(@Path("id") id: String): PagedResponse<ChannelMembership>

    // ===== PATIENTS =====
    @GET("patients/")
    suspend fun getPatients(
        @Query("page") page: Int = 1,
        @Query("search") search: String? = null
    ): PagedResponse<Patient>

    @POST("patients/")
    suspend fun createPatient(@Body patient: PatientCreateRequest): Patient

    @GET("patients/{id}/")
    suspend fun getPatient(@Path("id") id: String): Patient

    @GET("patients/records/")
    suspend fun getMedicalRecords(@Query("channel") channelId: String? = null): PagedResponse<MedicalRecord>

    @POST("patients/records/")
    suspend fun createMedicalRecord(@Body record: MedicalRecordCreateRequest): MedicalRecord

    // ===== SECURITY =====
    @POST("security/check-device/")
    suspend fun checkDevice(@Body request: DeviceCheckRequest): DeviceCheckResponse

    @GET("security/dashboard/")
    suspend fun getSecurityDashboard(): JsonObject

    // ===== NOTIFICATIONS =====
    @GET("notifications/")
    suspend fun getNotifications(): PagedResponse<Notification>

    @GET("notifications/unread_count/")
    suspend fun getUnreadCount(): Map<String, Int>

    @POST("notifications/{id}/mark_read/")
    suspend fun markNotificationRead(@Path("id") id: String): Map<String, String>

    @POST("notifications/mark_all_read/")
    suspend fun markAllNotificationsRead(): Map<String, String>

    // ===== ANALYTICS =====
    @GET("analytics/dashboard/overview/")
    suspend fun getDashboardOverview(): DashboardStats

    // ===== PHARMACY =====
    @GET("pharmacy/prescriptions/")
    suspend fun getPrescriptions(@Query("page") page: Int = 1): PagedResponse<Prescription>

    @POST("pharmacy/prescriptions/{id}/dispense/")
    suspend fun dispensePrescription(@Path("id") id: String, @Body body: Map<String, String> = emptyMap()): Prescription

    // ===== LAB =====
    // Router basename is `orders` (apps/lab/urls.py); `lab/requests/` was a 404.
    @GET("lab/orders/")
    suspend fun getLabRequests(@Query("page") page: Int = 1): PagedResponse<LabTestRequest>

    // ===== APPOINTMENTS =====
    @GET("appointments/")
    suspend fun getAppointments(@Query("page") page: Int = 1): PagedResponse<Appointment>

    // ===== TELEMEDICINE =====
    // Router basename is `consultations`; `telemedicine/sessions/` was a 404.
    @GET("telemedicine/consultations/")
    suspend fun getTelemedicineSessions(@Query("page") page: Int = 1): PagedResponse<TelemedicineSession>
}
