package com.securemed.app.data.api

import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.TokenPair
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.CertificatePinner
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Network module - provides Retrofit instance with auth interceptor and
 * automatic access-token refresh on 401 responses.
 */
object NetworkModule {

    @Serializable
    private data class RefreshRequest(val refresh: String)

    private val json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        encodeDefaults = true
    }

    private val authInterceptor = Interceptor { chain ->
        val token = SecurePreferences.accessToken
        val request = chain.request().newBuilder()
            .apply {
                if (token != null) {
                    addHeader("Authorization", "Bearer $token")
                }
                addHeader("Accept", "application/json")
                addHeader("Content-Type", "application/json")
            }
            .build()
        chain.proceed(request)
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
        else HttpLoggingInterceptor.Level.NONE
    }

    /**
     * Certificate Pinning لمنع هجمات Man-in-the-Middle (MITM)
     * يتم التأكد من أن التطبيق يتصل فقط بالخادم الموثوق الذي يمتلك هذا المفتاح العام.
     */
    private val certificatePinner = CertificatePinner.Builder()
        // TODO: استبدل الهاش بالهاش الحقيقي لشهادة السيرفر الخاص بك في الإنتاج
        .add("api.securemed.local", "sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=") 
        .build()

    // تعطيل Certificate Pinning في بيئة التطوير (Debug) لتجنب أخطاء الاتصال
    private fun OkHttpClient.Builder.applyCertificatePinner(): OkHttpClient.Builder {
        if (!BuildConfig.DEBUG) {
            this.certificatePinner(certificatePinner)
        }
        return this
    }

    /** Plain client for the refresh call — must not recurse into the authenticator. */
    private val refreshClient = OkHttpClient.Builder()
        .applyCertificatePinner()
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val refreshLock = Any()

    /**
     * Exchange the refresh token for a new token pair. Returns the new
     * access token, or null when the session is unrecoverable (tokens are
     * cleared so the next navigation sends the user back to login).
     */
    private fun refreshAccessToken(): String? = synchronized(refreshLock) {
        val refreshToken = SecurePreferences.refreshToken ?: return null
        try {
            val body = json.encodeToString(
                RefreshRequest.serializer(), RefreshRequest(refreshToken)
            ).toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url(BuildConfig.API_BASE_URL + "auth/refresh/")
                .post(body)
                .build()
            refreshClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return null
                val responseBody = response.body?.string() ?: return null
                val tokens = json.decodeFromString(TokenPair.serializer(), responseBody)
                SecurePreferences.accessToken = tokens.access
                SecurePreferences.refreshToken = tokens.refresh
                tokens.access
            }
        } catch (_: Exception) {
            null
        }
    }

    /**
     * Retries a failed request once with a fresh access token. Null (give
     * up) when the refresh itself failed or the retry already got a 401.
     */
    private val tokenAuthenticator = okhttp3.Authenticator { _, response ->
        if (response.priorResponse != null) {
            null
        } else {
            val newToken = refreshAccessToken()
            if (newToken == null) {
                SecurePreferences.clearTokens()
                null
            } else {
                response.request.newBuilder()
                    .header("Authorization", "Bearer $newToken")
                    .build()
            }
        }
    }

    private val okHttpClient = OkHttpClient.Builder()
        .applyCertificatePinner()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .authenticator(tokenAuthenticator)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(okHttpClient)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()

    val api: SecureMedApi = retrofit.create(SecureMedApi::class.java)
}
