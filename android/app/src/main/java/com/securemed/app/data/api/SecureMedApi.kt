package com.securemed.app.data.api

import com.securemed.app.data.model.*
import retrofit2.http.*

/**
 * Retrofit API interface for SecureMed backend.
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
    suspend fun enrollBiometric(@Body request: BiometricEnrollRequest): Unit

    @POST("auth/biometric/challenge/")
    suspend fun getBiometricChallenge(@Body request: BiometricChallengeRequest): BiometricChallengeResponse

    @POST("auth/biometric/login/")
    suspend fun biometricLogin(@Body request: BiometricLoginRequest): LoginResponse

    // ===== CHANNELS =====
    @GET("channels/")
    suspend fun getChannels(): List<Channel>

    @GET("channels/{id}/")
    suspend fun getChannel(@Path("id") id: String): Channel

    @GET("channels/{id}/members/")
    suspend fun getChannelMembers(@Path("id") id: String): List<ChannelMembership>

    // ===== PATIENTS =====
    @GET("patients/")
    suspend fun getPatients(): List<Patient>

    @GET("patients/records/")
    suspend fun getMedicalRecords(@Query("channel") channelId: String? = null): List<MedicalRecord>

    // ===== SECURITY =====
    @GET("security/dashboard/")
    suspend fun getSecurityDashboard(): Map<String, Any>

    // ===== NOTIFICATIONS =====
    @GET("notifications/")
    suspend fun getNotifications(): List<Notification>

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
