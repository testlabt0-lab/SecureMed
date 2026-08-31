package com.securemed.app.data

import com.securemed.app.data.api.NetworkModule
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.*
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/**
 * Repository for authentication and data operations.
 *
 * Offline mode: every cached GET stores its JSON response on disk on success
 * and falls back to the last cached copy when the network fails, so the app
 * stays browsable without connectivity.
 */
class SecureMedRepository {

    private val api: SecureMedApi = NetworkModule.api

    private val json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
    }

    private inline fun <reified T> cacheSave(key: String, value: T) {
        try {
            LocalCache.save(key, json.encodeToString(value))
        } catch (_: Exception) {
            // Never let cache failures break a successful network call.
        }
    }

    private inline fun <reified T> cacheLoad(key: String): T? = try {
        LocalCache.load(key)?.let { json.decodeFromString<T>(it) }
    } catch (_: Exception) {
        null
    }

    // ===== AUTH =====
    suspend fun login(email: String, password: String): Result<LoginResponse> = try {
        val response = api.login(LoginRequest(email, password))
        SecurePreferences.accessToken = response.tokens.access
        SecurePreferences.refreshToken = response.tokens.refresh
        SecurePreferences.userId = response.user.id
        SecurePreferences.userEmail = response.user.email
        SecurePreferences.userName = response.user.fullName
        SecurePreferences.userRole = response.user.role
        SecurePreferences.lastEmail = email
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Biometric login step 2: submit the Keystore signature over the
     * challenge obtained from [requestBiometricChallenge].
     */
    suspend fun biometricLogin(
        challengeId: String,
        signatureBase64: String
    ): Result<LoginResponse> = try {
        val response = api.biometricLogin(
            BiometricLoginRequest(challengeId, signatureBase64)
        )
        SecurePreferences.accessToken = response.tokens.access
        SecurePreferences.refreshToken = response.tokens.refresh
        SecurePreferences.userId = response.user.id
        SecurePreferences.userEmail = response.user.email
        SecurePreferences.userName = response.user.fullName
        SecurePreferences.userRole = response.user.role
        SecurePreferences.lastEmail = response.user.email
        Result.success(response)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * Biometric login step 1: ask the server for a challenge bound to
     * this email + device.
     */
    suspend fun requestBiometricChallenge(
        email: String
    ): Result<BiometricChallengeResponse> = try {
        Result.success(
            api.getBiometricChallenge(
                BiometricChallengeRequest(email, SecurePreferences.deviceId)
            )
        )
    } catch (e: Exception) {
        Result.failure(e)
    }

    /** Enroll this device's Keystore public key for biometric login. */
    suspend fun enrollBiometric(
        deviceName: String,
        publicKeyBase64: String
    ): Result<Unit> = try {
        api.enrollBiometric(
            BiometricEnrollRequest(
                deviceId = SecurePreferences.deviceId,
                deviceName = deviceName,
                platform = "ANDROID",
                publicKey = publicKeyBase64
            )
        )
        SecurePreferences.biometricEnabled = true
        SecurePreferences.lastEmail = SecurePreferences.userEmail
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    fun logout() {
        SecurePreferences.clearSession()
    }

    // ===== CHANNELS =====
    suspend fun getChannels(): Result<List<Channel>> = try {
        val data = api.getChannels().results
        cacheSave("channels", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<Channel>>("channels")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun getChannel(id: String): Result<Channel> = try {
        Result.success(api.getChannel(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getChannelMembers(id: String): Result<List<ChannelMembership>> = try {
        Result.success(api.getChannelMembers(id).results)
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== CHAT =====
    suspend fun getMessages(channelId: String): Result<List<ChatMessage>> = try {
        val data = api.getMessages(channelId)
        // Cache per channel for offline reading
        cacheSave("chat_$channelId", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<ChatMessage>>("chat_$channelId")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun sendMessage(channelId: String, body: String): Result<ChatMessage> = try {
        Result.success(api.sendMessage(channelId, ChatMessageRequest(body)))
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== PATIENTS =====
    suspend fun getPatients(): Result<List<Patient>> = try {
        val data = api.getPatients().results
        cacheSave("patients", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<Patient>>("patients")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun getMedicalRecords(channelId: String? = null): Result<List<MedicalRecord>> = try {
        val data = api.getMedicalRecords(channelId).results
        if (channelId != null) cacheSave("records_$channelId", data)
        Result.success(data)
    } catch (e: Exception) {
        if (channelId != null) {
            cacheLoad<List<MedicalRecord>>("records_$channelId")
                ?.let { return Result.success(it) }
        }
        Result.failure(e)
    }

    // ===== MEDICATIONS =====
    suspend fun getMedications(patientId: String? = null): Result<List<Medication>> = try {
        val data = api.getMedications(patientId).results
        cacheSave("medications", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<Medication>>("medications")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun createMedication(request: MedicationCreateRequest): Result<Medication> = try {
        Result.success(api.createMedication(request))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getTodayDoses(patientId: String? = null): Result<TodayDosesResponse> = try {
        val data = api.getTodayDoses(patientId)
        cacheSave("today_doses", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<TodayDosesResponse>("today_doses")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun logDose(
        medicationId: String,
        scheduledFor: String,
        status: String
    ): Result<MedicationLogResponse> = try {
        Result.success(api.logDose(LogDoseRequest(medicationId, scheduledFor, status)))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun getAdherence(patientId: String? = null): Result<AdherenceStats> = try {
        Result.success(api.getAdherence(patientId))
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
        val data = api.getNotifications().results
        cacheSave("notifications", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<Notification>>("notifications")?.let { Result.success(it) }
            ?: Result.failure(e)
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
        val data = api.getDashboardOverview()
        cacheSave("dashboard_overview", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<DashboardStats>("dashboard_overview")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    // ===== USERS (admin) =====
    suspend fun getUsers(): Result<List<User>> = try {
        val data = api.getUsers().results
        cacheSave("users", data)
        Result.success(data)
    } catch (e: Exception) {
        cacheLoad<List<User>>("users")?.let { Result.success(it) }
            ?: Result.failure(e)
    }

    suspend fun deactivateUser(id: String): Result<String> = try {
        Result.success(api.deactivateUser(id)["detail"] ?: "تم إلغاء تفعيل المستخدم")
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun activateUser(id: String): Result<String> = try {
        Result.success(api.activateUser(id)["detail"] ?: "تم تفعيل المستخدم")
    } catch (e: Exception) {
        Result.failure(e)
    }

    // ===== CHANGE PASSWORD =====
    suspend fun changePassword(
        oldPassword: String,
        newPassword: String,
        confirmPassword: String
    ): Result<String> = try {
        val response = api.changePassword(
            ChangePasswordRequest(oldPassword, newPassword, confirmPassword)
        )
        Result.success(response["detail"] ?: "تم تغيير كلمة المرور بنجاح")
    } catch (e: Exception) {
        Result.failure(e)
    }
}
