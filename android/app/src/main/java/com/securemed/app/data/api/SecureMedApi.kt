package com.securemed.app.data.api

import com.securemed.app.data.model.*
import retrofit2.http.*

/**
 * Retrofit API interface for SecureMed backend.
 *
 * NOTE: list endpoints return the DRF paginated envelope {count,...,results}
 * (SecureMedPagination) — raw List<T> decodes would fail at runtime.
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

    @POST("auth/biometric/enroll/")
    suspend fun enrollBiometric(@Body request: BiometricEnrollRequest): Map<String, String>

    @POST("auth/biometric/challenge/")
    suspend fun getBiometricChallenge(@Body request: BiometricChallengeRequest): BiometricChallengeResponse

    @POST("auth/biometric/login/")
    suspend fun biometricLogin(@Body request: BiometricLoginRequest): LoginResponse

    // ===== CHANNELS =====
    @GET("channels/")
    suspend fun getChannels(): Paginated<Channel>

    @GET("channels/{id}/")
    suspend fun getChannel(@Path("id") id: String): Channel

    @GET("channels/{id}/members/")
    suspend fun getChannelMembers(@Path("id") id: String): Paginated<ChannelMembership>

    // ===== CHAT =====
    @GET("channels/{id}/messages/")
    suspend fun getMessages(
        @Path("id") id: String,
        @Query("after") after: String? = null,
        @Query("limit") limit: Int = 200
    ): List<ChatMessage>

    @POST("channels/{id}/messages/")
    suspend fun sendMessage(
        @Path("id") id: String,
        @Body request: ChatMessageRequest
    ): ChatMessage

    // ===== PATIENTS =====
    @GET("patients/")
    suspend fun getPatients(): Paginated<Patient>

    @GET("patients/records/")
    suspend fun getMedicalRecords(@Query("channel") channelId: String? = null): Paginated<MedicalRecord>

    // ===== MEDICATIONS =====
    @GET("patients/medications/")
    suspend fun getMedications(@Query("patient") patientId: String? = null): Paginated<Medication>

    @POST("patients/medications/")
    suspend fun createMedication(@Body request: MedicationCreateRequest): Medication

    @GET("patients/medications/today/")
    suspend fun getTodayDoses(@Query("patient") patientId: String? = null): TodayDosesResponse

    @POST("patients/medications/log_dose/")
    suspend fun logDose(@Body request: LogDoseRequest): MedicationLogResponse

    @GET("patients/medications/adherence/")
    suspend fun getAdherence(@Query("patient") patientId: String? = null): AdherenceStats

    // ===== USERS (admin) =====
    @GET("auth/users/")
    suspend fun getUsers(@Query("search") search: String? = null): PaginatedUsers

    @POST("auth/users/{id}/deactivate/")
    suspend fun deactivateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/users/{id}/activate/")
    suspend fun activateUser(@Path("id") id: String): Map<String, String>

    @POST("auth/users/change_password/")
    suspend fun changePassword(@Body request: ChangePasswordRequest): Map<String, String>

    // ===== SECURITY =====
    @GET("security/dashboard/")
    suspend fun getSecurityDashboard(): Map<String, Any>

    // ===== NOTIFICATIONS =====
    @GET("notifications/")
    suspend fun getNotifications(): Paginated<Notification>

    @GET("notifications/unread_count/")
    suspend fun getUnreadCount(): Map<String, Int>

    @POST("notifications/{id}/mark_read/")
    suspend fun markNotificationRead(@Path("id") id: String): Unit

    @POST("notifications/mark_all_read/")
    suspend fun markAllNotificationsRead(): Unit

    // ===== ANALYTICS =====
    @GET("analytics/dashboard/overview/")
    suspend fun getDashboardOverview(): DashboardStats
}
