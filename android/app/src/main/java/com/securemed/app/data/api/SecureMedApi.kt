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

    @POST("auth/logout/")
    suspend fun logout(@Body body: Map<String, String>): Unit

    @POST("auth/refresh/")
    suspend fun refreshToken(@Body body: Map<String, String>): TokenPair

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
    suspend fun getPatients(@Query("page") page: Int = 1): PagedResponse<Patient>

    @GET("patients/{id}/")
    suspend fun getPatient(@Path("id") id: String): Patient

    @GET("patients/records/")
    suspend fun getMedicalRecords(@Query("channel") channelId: String? = null): PagedResponse<MedicalRecord>

    // ===== SECURITY =====
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
    @GET("lab/requests/")
    suspend fun getLabRequests(@Query("page") page: Int = 1): PagedResponse<LabTestRequest>

    // ===== APPOINTMENTS =====
    @GET("appointments/")
    suspend fun getAppointments(@Query("page") page: Int = 1): PagedResponse<Appointment>

    // ===== TELEMEDICINE =====
    @GET("telemedicine/sessions/")
    suspend fun getTelemedicineSessions(@Query("page") page: Int = 1): PagedResponse<TelemedicineSession>
}
