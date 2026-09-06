package com.securemed.app.data.api

import com.securemed.app.BuildConfig
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.RefreshResponse
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
                addDeviceHeaders()
            }
            .build()
        chain.proceed(request)
    }

    /**
     * Device identity, on **every** request including `auth/login/`.
     *
     * The backend reads these off `request.META` and there is no endpoint that
     * asks for them, so a client that omits them is invisible to a whole layer of
     * the server's security: the per-device lockout after five failed logins, the
     * WAF's device blocklist, adaptive MFA's "new device" test, the trusted-device
     * row, the fingerprint stored with the session, and the device column of every
     * audit record. Until now the app sent none of them — which is the only reason
     * a mobile login never had to answer an emailed code.
     *
     * Login included, deliberately: that is the request whose device the lockout
     * and the new-device check are about.
     *
     * One value, unchanged for the life of the install ([SecurePreferences.installId]).
     * A fingerprint that varies between requests of one session is precisely the
     * pattern `SessionManager.reject_if_hijacked` revokes a session for.
     *
     * `X-MAC-Address` is read by the backend too and is deliberately never sent:
     * Android has returned a per-app randomized MAC since 6.0, so the value would
     * be a fiction, and a real one is a permanent hardware identifier we have no
     * reason to hand over.
     */
    private fun Request.Builder.addDeviceHeaders(): Request.Builder = apply {
        addHeader("X-Device-Fingerprint", SecurePreferences.installId)
        addHeader("X-OS-Info", osInfo)
        addHeader("X-Browser-Info", appInfo)
    }

    /** e.g. `Android 14 (API 34); samsung SM-A546B`. */
    private val osInfo: String by lazy {
        headerSafe(
            "Android ${android.os.Build.VERSION.RELEASE} " +
                "(API ${android.os.Build.VERSION.SDK_INT}); " +
                "${android.os.Build.MANUFACTURER} ${android.os.Build.MODEL}"
        )
    }

    /** Which build is talking, so a bug can be tied to a version from the server. */
    private val appInfo: String by lazy {
        headerSafe("SecureMed-Android/${BuildConfig.VERSION_NAME} (${BuildConfig.BUILD_TYPE})")
    }

    /**
     * Printable ASCII, truncated.
     *
     * [android.os.Build.MODEL] and `MANUFACTURER` are vendor strings and are not
     * guaranteed to be ASCII; OkHttp rejects a header value containing anything
     * outside `0x20..0x7E` by throwing, which would take down every request on
     * that device rather than just spoil a log line. 200 characters also keeps the
     * value inside the backend's `max_length=255` columns.
     */
    private fun headerSafe(value: String): String =
        value.map { if (it.code in 0x20..0x7E) it else '?' }
            .joinToString("")
            .take(200)

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
        else HttpLoggingInterceptor.Level.NONE
    }

    /**
     * SPKI pins for the backend — defence in depth against a MITM holding a
     * certificate from a compromised or coerced CA.
     *
     * Pinned at the CA level rather than the leaf: the leaf is issued by the
     * hosting platform and rotates about every 90 days, so a leaf pin would
     * break the app at the next renewal.
     *
     *  - Google Trust Services "WE1" intermediate, expires 2029-02-20
     *  - "GTS Root R4" root,                       expires 2028-01-28
     *
     * Must stay in sync with the `<pin-set>` in res/xml/network_security_config.xml,
     * which documents how to re-derive these values.
     */
    private val PRODUCTION_PINS = listOf(
        "sha256/kIdp6NNEd8wsugYyyIYFsi1ylMCED3hZbSR8ZFsa/A4=",
        "sha256/mEflZT5enoR1FuXLgYYGqnVEoZvmf9c2bVBpiOjYQ0c="
    )

    /**
     * Pinner for the host the app actually talks to.
     *
     * [CertificatePinner] matches by hostname and silently ignores pins for
     * hosts that are never contacted, so a hardcoded placeholder host pins
     * nothing at all. The host is therefore read from the configured base URL
     * — the one server every request goes to.
     *
     * Null when the base URL is http (the debug default is a cleartext
     * loopback to the dev machine, where there is no certificate to pin) or
     * unparseable.
     */
    private val certificatePinner: CertificatePinner? = runCatching {
        java.net.URI(BuildConfig.API_BASE_URL)
            .takeIf { it.scheme == "https" }
            ?.host
            ?.let { host ->
                CertificatePinner.Builder()
                    .apply { PRODUCTION_PINS.forEach { pin -> add(host, pin) } }
                    .build()
            }
    }.getOrNull()

    /**
     * Applies pinning outside debug builds. Debug stays unpinned so a
     * developer can put an intercepting proxy in front of the API; release
     * traffic is additionally pinned by the platform network-security config,
     * which does not have that exemption.
     */
    private fun OkHttpClient.Builder.applyCertificatePinner(): OkHttpClient.Builder {
        val pinner = certificatePinner
        if (!BuildConfig.DEBUG && pinner != null) {
            this.certificatePinner(pinner)
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
                // This call bypasses authInterceptor (it must not recurse into
                // the authenticator), so the device headers are added by hand —
                // otherwise the one request that renews a session would be the
                // only one the server cannot attribute to a device.
                .addDeviceHeaders()
                .build()
            refreshClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) return null
                val responseBody = response.body?.string() ?: return null
                val tokens = json.decodeFromString(RefreshResponse.serializer(), responseBody)
                SecurePreferences.accessToken = tokens.access
                // Only when the server rotated. Overwriting unconditionally would
                // store a null over a refresh token that is still valid, and
                // isLoggedIn() reads a missing refresh token as "not signed in".
                tokens.refresh?.takeIf { it.isNotBlank() }?.let {
                    SecurePreferences.refreshToken = it
                }
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
