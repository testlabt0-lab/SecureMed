package com.securemed.app.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.TwoFactorExpiredException
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.model.BiometricChallengeResponse
import com.securemed.app.data.model.LoginResponse
import com.securemed.app.data.model.MyDevice
import com.securemed.app.security.AppLock
import com.securemed.app.security.SecurityUtils
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import retrofit2.HttpException
import javax.inject.Inject

/**
 * AuthViewModel - manages authentication state.
 *
 * Dependencies are injected by Hilt instead of being created internally,
 * making this ViewModel fully testable with fake implementations.
 */
@HiltViewModel
class AuthViewModel @Inject constructor(
    private val repository: SecureMedRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow<AuthUiState>(AuthUiState.Idle)
    val uiState: StateFlow<AuthUiState> = _uiState

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage

    fun login(email: String, password: String) {
        _errorMessage.value = null
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.login(email, password)
                .onSuccess { response ->
                    when {
                        response.isAuthenticated ->
                            _uiState.value = AuthUiState.Success(response)

                        // The server wants a second factor instead of handing
                        // over a session. Hold the short-lived mfa_token in
                        // state and let the UI collect the code; the previous
                        // build stopped here and told the user to finish on the
                        // web, which made every MFA account unusable on mobile.
                        response.requiresTwoFactor && response.mfaToken != null -> {
                            _errorMessage.value = null
                            _uiState.value = AuthUiState.AwaitingTwoFactor(
                                mfaToken = response.mfaToken,
                                method = response.method
                            )
                        }

                        // requires_2fa with no token to answer it. Nothing the
                        // client can do, so say so rather than opening a code
                        // screen that can only fail.
                        response.requiresTwoFactor -> {
                            _errorMessage.value = response.detail
                                ?: "طلب الخادم رمز تحقق دون إصدار جلسة تحقق. حاول مرة أخرى."
                            _uiState.value = AuthUiState.Error
                        }

                        else -> {
                            _errorMessage.value = response.detail ?: "استجابة غير متوقعة من الخادم"
                            _uiState.value = AuthUiState.Error
                        }
                    }
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل الدخول"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Posts the typed code to `auth/2fa/login/`.
     *
     * Stays in [AuthUiState.AwaitingTwoFactor] on a wrong code — the server
     * keeps the pending token alive for the rest of the 5 minutes, so the user
     * can simply retype. Only an expired token ends the attempt, because a new
     * one can come from nowhere but a fresh password login.
     *
     * [trustDevice] is forwarded as `trust_device`. It marks this install's
     * fingerprint trusted so adaptive MFA stops mailing a code on every sign-in;
     * it is the user's choice to make, so it is never set on their behalf.
     */
    fun submitTwoFactorCode(code: String, trustDevice: Boolean = false) {
        val awaiting = _uiState.value as? AuthUiState.AwaitingTwoFactor ?: return
        if (awaiting.submitting) return

        val trimmed = code.trim()
        if (trimmed.isEmpty()) {
            _errorMessage.value = "أدخل رمز التحقق"
            return
        }

        _errorMessage.value = null
        _uiState.value = awaiting.copy(submitting = true)
        viewModelScope.launch {
            repository.mfaLogin(awaiting.mfaToken, trimmed, trustDevice)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    if (error is TwoFactorExpiredException) {
                        expireTwoFactor(error.message)
                    } else {
                        _errorMessage.value = error.message ?: "تعذر التحقق من الرمز"
                        _uiState.value = awaiting.copy(submitting = false)
                    }
                }
        }
    }

    /**
     * The 5-minute window ran out — locally, or as reported by the server.
     *
     * Drops back to the login form rather than leaving a code screen whose
     * token no longer exists, since retrying the code there could only fail.
     */
    fun expireTwoFactor(message: String? = null) {
        _errorMessage.value = message ?: "انتهت مهلة رمز التحقق، سجّل الدخول من جديد"
        _uiState.value = AuthUiState.Error
    }

    /** The user chose to go back instead of entering a code. */
    fun cancelTwoFactor() {
        resetState()
    }

    /**
     * Step one of a biometric login: fetch the challenge and hand it to the UI,
     * which is the only layer that can raise the biometric prompt.
     *
     * A challenge arrives even for an account that never enrolled — the server
     * answers with an indistinguishable decoy on purpose — so reaching
     * [AuthUiState.AwaitingBiometric] proves nothing about the account.
     */
    fun startBiometricLogin(email: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.getBiometricChallenge(email)
                .onSuccess { challenge ->
                    _uiState.value = AuthUiState.AwaitingBiometric(challenge)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "تعذر بدء المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /** Step two: send the signature the Keystore produced behind the prompt. */
    fun completeBiometricLogin(challengeId: String, signature: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.biometricLogin(challengeId, signature)
                .onSuccess { response ->
                    _uiState.value = AuthUiState.Success(response)
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل المصادقة البيومترية"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Abandon the ceremony without contacting the server — the prompt failed, or
     * this device holds no key. The challenge is simply left to expire.
     */
    fun failBiometric(message: String) {
        _errorMessage.value = message
        _uiState.value = AuthUiState.Error
    }

    fun enrollBiometric(deviceName: String) {
        _uiState.value = AuthUiState.Loading
        viewModelScope.launch {
            repository.enrollBiometric(deviceName)
                .onSuccess {
                    _uiState.value = AuthUiState.BiometricEnrolled
                }
                .onFailure { error ->
                    _errorMessage.value = error.message ?: "فشل تسجيل البصمة"
                    _uiState.value = AuthUiState.Error
                }
        }
    }

    /**
     * Signs out. [allDevices] asks the server to end every session the account
     * holds — the answer to "I lost my phone", and the reason it is offered from
     * settings rather than being what the ordinary logout button does.
     *
     * The local wipe runs either way, so the UI can navigate to the login screen
     * as soon as this returns.
     */
    fun logout(allDevices: Boolean = false) {
        // Synchronous, so the idle lock is lifted in the same frame the caller
        // navigates to the login screen: the overlay must not outlive the session
        // it was covering, and the network call below may take seconds or fail.
        AppLock.reset()
        viewModelScope.launch {
            repository.logout(allDevices)
            _uiState.value = AuthUiState.Idle
        }
    }

    /**
     * The account was deleted server-side (DeleteAccountViewModel already ran
     * the full local wipe); the only remaining local duty is lifting the idle
     * lock so the login screen is reachable, and clearing any stale auth UI.
     */
    fun liftAppLockForSignedOut() {
        AppLock.reset()
        _uiState.value = AuthUiState.Idle
    }

    fun resetState() {
        _uiState.value = AuthUiState.Idle
        _errorMessage.value = null
    }

    private var ztnaPollingJob: Job? = null

    fun checkDeviceAuthorization(
        fingerprint: String,
        macAddress: String? = null,
        email: String? = null
    ) {
        _uiState.value = AuthUiState.CheckingDevice
        stopZtnaPolling()

        // Always verify with the server to ensure current network IP and authorization are valid

        viewModelScope.launch {
            // First check if there is an existing ZTNA approval status
            val statusResult = repository.getZtnaStatus(fingerprint)
            val ztnaStatus = statusResult.getOrNull()?.status

            if (ztnaStatus == "approved") {
                SecurePreferences.isDeviceAuthorized = true
                _uiState.value = AuthUiState.DeviceAuthorized
                return@launch
            } else if (ztnaStatus == "pending") {
                _uiState.value = AuthUiState.ZtnaPending(
                    fingerprint = fingerprint,
                    message = "تم إرسال طلبك للإدارة مسبقاً. يرجى انتظار موافقة الإدارة عبر تيليجرام."
                )
                startZtnaPolling(fingerprint)
                return@launch
            } else if (ztnaStatus == "rejected") {
                _uiState.value = AuthUiState.ZtnaRejected("تم حظر أو رفض هذا الجهاز من قبل الإدارة.")
                return@launch
            }

            // Perform regular device check
            repository.checkDevice(fingerprint, macAddress, email)
                .onSuccess { response ->
                    when (response.state) {
                        "authorized" -> {
                            SecurePreferences.isDeviceAuthorized = true
                            _uiState.value = AuthUiState.DeviceAuthorized
                        }
                        "blocked" -> _uiState.value = AuthUiState.DeviceUnauthorized(
                            response.detail ?: "هذا الجهاز محظور"
                        )
                        "pending" -> _uiState.value = AuthUiState.DevicePending(
                            response.detail ?: "طلب تفعيل الجهاز بانتظار موافقة الإدارة"
                        )
                        "unknown", null -> _uiState.value = AuthUiState.DeviceUnknown(
                            response.detail ?: "الجهاز غير معروف. أدخل بريدك الإلكتروني لطلب التفعيل."
                        )
                        else -> _uiState.value = AuthUiState.DeviceUnauthorized(
                            response.detail ?: "الجهاز غير مصرح به."
                        )
                    }
                }
                .onFailure { error ->
                    val resolvedMac = macAddress ?: SecurityUtils.getMacAddress()
                    val osInfo = SecurityUtils.getOsVersion()
                    val model = SecurityUtils.getDeviceModel()
                    val localIp = SecurityUtils.getLocalIpAddress()

                    val errorBody = (error as? HttpException)?.response()?.errorBody()?.string().orEmpty()
                    val isZtna = errorBody.contains("ZTNA_BLOCKED", ignoreCase = true) ||
                        errorBody.contains("zero trust", ignoreCase = true) ||
                        error.message?.contains("ZTNA", ignoreCase = true) == true

                    if (isZtna) {
                        _uiState.value = AuthUiState.ZtnaRequired(
                            fingerprint = fingerprint,
                            macAddress = resolvedMac,
                            osInfo = osInfo,
                            deviceModel = model,
                            localIp = localIp,
                            message = "تم رصد شبكة جديدة أو جهاز غير مصرح به. يجب طلب تصريح من المدير للمتابعة."
                        )
                    } else if (error is HttpException && error.code() == 403) {
                        _uiState.value = AuthUiState.ZtnaRequired(
                            fingerprint = fingerprint,
                            macAddress = resolvedMac,
                            osInfo = osInfo,
                            deviceModel = model,
                            localIp = localIp,
                            message = "يلزم طلب تصريح أمني من المدير للسماح لهذا الجهاز بالوصول إلى النظام."
                        )
                    } else {
                        _errorMessage.value = error.message ?: "فشل الاتصال بالخادم للتحقق من الجهاز"
                        _uiState.value = AuthUiState.DeviceUnauthorized(
                            "تعذر التحقق من الجهاز. يرجى التأكد من اتصالك بالإنترنت."
                        )
                    }
                }
        }
    }

    /**
     * إرسال طلب تصريح ZTNA إلى الخادم وبوت تيليجرام
     */
    fun sendZtnaAccessRequest(fingerprint: String, macAddress: String) {
        _uiState.value = AuthUiState.ZtnaSending
        stopZtnaPolling()

        viewModelScope.launch {
            repository.requestZtnaAccess(fingerprint, macAddress)
                .onSuccess { response ->
                    val msg = response.message ?: "تم إرسال طلبك للإدارة عبر تيليجرام. يرجى الانتظار لحين الموافقة."
                    _uiState.value = AuthUiState.ZtnaPending(
                        fingerprint = fingerprint,
                        message = msg,
                        telegramSent = response.telegramSent
                    )
                    startZtnaPolling(fingerprint)
                }
                .onFailure { error ->
                    val resolvedMac = macAddress.ifBlank { SecurityUtils.getMacAddress() }
                    _uiState.value = AuthUiState.ZtnaRequired(
                        fingerprint = fingerprint,
                        macAddress = resolvedMac,
                        osInfo = SecurityUtils.getOsVersion(),
                        deviceModel = SecurityUtils.getDeviceModel(),
                        localIp = SecurityUtils.getLocalIpAddress(),
                        message = error.message ?: "تعذر إرسال الطلب للإدارة. يرجى المحاولة مجدداً."
                    )
                }
        }
    }

    /**
     * استماع حي ومستمر لقرار المدير عبر تيليجرام
     */
    fun startZtnaPolling(fingerprint: String) {
        stopZtnaPolling()
        ztnaPollingJob = viewModelScope.launch {
            while (isActive) {
                delay(3000L) // Poll every 3 seconds
                repository.getZtnaStatus(fingerprint)
                    .onSuccess { response ->
                        when (response.status) {
                            "approved" -> {
                                stopZtnaPolling()
                                SecurePreferences.isDeviceAuthorized = true
                                _uiState.value = AuthUiState.DeviceAuthorized
                                return@launch
                            }
                            "rejected" -> {
                                stopZtnaPolling()
                                _uiState.value = AuthUiState.ZtnaRejected(
                                    "تم رفض طلب الوصول لهذا الجهاز من قبل المدير."
                                )
                                return@launch
                            }
                        }
                    }
            }
        }
    }

    fun stopZtnaPolling() {
        ztnaPollingJob?.cancel()
        ztnaPollingJob = null
    }

    override fun onCleared() {
        super.onCleared()
        stopZtnaPolling()
    }

    /** Self-service "إزالة جهازي": revoke this device's trust + kill its
     * session, without blacklisting it (the web dashboard offers the same).
     * Requires a logged-in session, so it is reachable from the devices
     * screen inside the app, not from the lock screen. */
    fun removeMyDevice(
        deviceId: String,
        onResult: (Boolean, String) -> Unit
    ) {
        viewModelScope.launch {
            repository.deactivateDevice(deviceId)
                .onSuccess {
                    onResult(true, "تم إزالة الجهاز من حسابك")
                }
                .onFailure { error ->
                    onResult(false, error.message ?: "فشل إزالة الجهاز")
                }
        }
    }

    /** أجهزة المستخدم المسجلة — لقائمة "الأجهزة" في الإعدادات. */
    fun loadMyDevices(onResult: (List<MyDevice>) -> Unit) {
        viewModelScope.launch {
            repository.getMyDevices()
                .onSuccess { onResult(it.devices) }
                .onFailure { onResult(emptyList()) }
        }
    }

    /** إزالة جهاز ببصمته (المسار المفضل من التطبيق). */
    fun removeMyDeviceByFingerprint(
        fingerprint: String,
        onResult: (Boolean, String) -> Unit
    ) {
        viewModelScope.launch {
            repository.removeMyDevice(fingerprint)
                .onSuccess { onResult(true, it.getOrDefault("detail", "تم إزالة الجهاز")) }
                .onFailure { error ->
                    onResult(false, error.message ?: "فشل إزالة الجهاز")
                }
        }
    }
}

sealed class AuthUiState {
    data object Idle : AuthUiState()
    data object Loading : AuthUiState()
    data object CheckingDevice : AuthUiState()

    /**
     * The pre-flight device check came back trusted. Distinct from
     * [Idle] because DeviceCheckScreen needs to navigate on this transition
     * but *not* on the initial Idle (which is the state the ViewModel
     * starts in, before any check has happened).
     */
    data object DeviceAuthorized : AuthUiState()

    /** طلب التفعيل وصل للإدارة ولم يُقرر بعد — أظهر شاشة انتظار لا خطأ. */
    data class DevicePending(val message: String) : AuthUiState()

    data class DeviceUnauthorized(val message: String) : AuthUiState()

    /**
     * The device is not on file and we need the user's email to register
     * it. Mirrors the web client's "unknown device" form.
     */
    data class DeviceUnknown(val message: String) : AuthUiState()

    // ===== ZTNA STATES =====
    /**
     * الجهاز أو الشبكة الحالية غير مصرح لها (ZTNA) - يتطلب إرسال طلب للمدير عبر تيليجرام
     */
    data class ZtnaRequired(
        val fingerprint: String,
        val macAddress: String,
        val osInfo: String,
        val deviceModel: String,
        val localIp: String?,
        val message: String? = null
    ) : AuthUiState()

    /** جاري إرسال الطلب إلى تيليجرام */
    data object ZtnaSending : AuthUiState()

    /** تم إرسال الطلب لتيليجرام، وبانتظار موافقة المدير (مع استماع حي) */
    data class ZtnaPending(
        val fingerprint: String,
        val message: String,
        val telegramSent: Boolean = true
    ) : AuthUiState()

    /** تم رفض الطلب من قبل المدير عبر تيليجرام */
    data class ZtnaRejected(val message: String) : AuthUiState()

    /** A challenge is in hand and the biometric prompt should now be shown. */
    data class AwaitingBiometric(val challenge: BiometricChallengeResponse) : AuthUiState()

    /**
     * The password was accepted but a second factor is outstanding.
     */
    data class AwaitingTwoFactor(
        val mfaToken: String,
        val method: String?,
        val submitting: Boolean = false
    ) : AuthUiState()

    data class Success(val response: LoginResponse) : AuthUiState()
    data object BiometricEnrolled : AuthUiState()
    data object Error : AuthUiState()
}
