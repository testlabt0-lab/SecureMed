package com.securemed.app.data

import com.securemed.app.data.api.NetworkModule
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.*

/**
 * Repository for authentication and data operations.
 */
class SecureMedRepository {

    private val api: SecureMedApi = NetworkModule.api

    // ===== AUTH =====
    suspend fun login(email: String, password: String): Result<LoginResponse> = try {
        val response = api.login(LoginRequest(email, password))
        SecurePreferences.accessToken = response.tokens.access
        SecurePreferences.refreshToken = response.tokens.refresh
        SecurePreferences.userId = response.user.id
        SecurePreferences.userEmail = response.user.email
        SecurePreferences.userName = response.user.fullName
        SecurePreferences.userRole = response.user.role
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun biometricLogin(
        email: String,
        biometricTemplate: String
    ): Result<LoginResponse> = try {
        val challenge = api.getBiometricChallenge(
            BiometricChallengeRequest(email, SecurePreferences.deviceId)
        )
        val response = api.biometricLogin(
            BiometricLoginRequest(
                challengeId = challenge.challengeId,
                biometricResponse = "android-response-${challenge.challengeId}",
                biometricTemplate = biometricTemplate
            )
        )
        SecurePreferences.accessToken = response.tokens.access
        SecurePreferences.refreshToken = response.tokens.refresh
        SecurePreferences.userId = response.user.id
        SecurePreferences.userEmail = response.user.email
        SecurePreferences.userName = response.user.fullName
        SecurePreferences.userRole = response.user.role
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun enrollBiometric(deviceName: String, biometricTemplate: String): Result<Unit> = try {
        api.enrollBiometric(
            BiometricEnrollRequest(
                deviceId = SecurePreferences.deviceId,
                deviceName = deviceName,
                platform = "ANDROID",
                biometricTemplate = biometricTemplate
            )
        )
        SecurePreferences.biometricEnabled = true
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    fun logout() {
        SecurePreferences.clear()
    }

    // ===== CHANNELS =====
    suspend fun getChannels(): Result<List<Channel>> = try {
        Result.success(api.getChannels())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getChannel(id: String): Result<Channel> = try {
        Result.success(api.getChannel(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getChannelMembers(id: String): Result<List<ChannelMembership>> = try {
        Result.success(api.getChannelMembers(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== PATIENTS =====
    suspend fun getPatients(): Result<List<Patient>> = try {
        Result.success(api.getPatients())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getMedicalRecords(channelId: String? = null): Result<List<MedicalRecord>> = try {
        Result.success(api.getMedicalRecords(channelId))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== SECURITY =====
    suspend fun getSecurityDashboard(): Result<Map<String, Any>> = try {
        Result.success(api.getSecurityDashboard())
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== NOTIFICATIONS =====
    suspend fun getNotifications(): Result<List<Notification>> = try {
        Result.success(api.getNotifications())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getUnreadCount(): Result<Map<String, Int>> = try {
        Result.success(api.getUnreadCount())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun markNotificationRead(id: String): Result<Unit> = try {
        Result.success(api.markNotificationRead(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun markAllNotificationsRead(): Result<Unit> = try {
        Result.success(api.markAllNotificationsRead())
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== ANALYTICS =====
    suspend fun getDashboardOverview(): Result<DashboardStats> = try {
        Result.success(api.getDashboardOverview())
    } catch (e: Exception) {
        Result.failure(e)
    }
}
