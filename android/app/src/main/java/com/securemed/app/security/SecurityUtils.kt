package com.securemed.app.security

import android.content.Context
import android.content.ClipData
import android.content.ClipboardManager
import android.hardware.display.DisplayManager
import android.view.Display
import android.os.Build
import android.os.Handler
import android.os.Looper
import com.securemed.app.data.local.SecurePreferences
import java.io.File
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.Locale

object SecurityUtils {
    /**
     * هل الجهاز مكسور الحماية (Root)؟
     *
     * الفحوصات تغطي Magisk وKernelSU وأدوات الروت الحديثة. المحاكي **ليس**
     * جزءاً من هذه الدالة: خلطهما معاً كان يعني أن أي محاكي يُعَدّ جهازاً
     * مكسور الحماية، فيُغلق التطبيق على كل بيئات التطوير والاختبار الآلي.
     * من يحتاج التمييز يستدعي [isProbablyEmulator] صراحةً.
     *
     * هذه الفحوصات إرشادية لا حاسمة: Magisk في وضع الإخفاء يتجاوزها،
     * والاعتماد الأمني الحقيقي هو التشفير والمصادقة على الخادم.
     */
    fun isDeviceRooted(): Boolean {
        return checkRootFiles() || checkSuCommand()
    }

    /**
     * هل توقيع البناء يحمل `test-keys`؟
     *
     * الوسيط صريح لأن `Build.TAGS` حقل ثابت (static final) لا دالة، وMockK
     * تعترض الدوال الساكنة فقط؛ فالاختبار الذي كان يحاول
     * `every { Build.TAGS } returns …` يفشل دائماً بـ MockKException قبل أن
     * يصل إلى الفحص نفسه. بتمرير الوسيط يصبح هذا الفحص دالة نقية قابلة
     * للاختبار بلا جهاز ولا محاكي، وسلوك الإنتاج لم يتغير.
     */
    internal fun hasTestKeys(buildTags: String? = Build.TAGS): Boolean =
        buildTags?.contains("test-keys") == true

    /**
     * هل نعمل على محاكي أو بيئة افتراضية؟
     *
     * للتسجيل والقياس فقط — صور المحاكي الرسمية موقّعة بـ test-keys وتحمل
     * أسماء عامة، فبعض هذه المؤشرات تتطابق مع أجهزة تطوير مشروعة.
     */
    fun isProbablyEmulator(): Boolean = checkEmulator()

    private fun checkRootFiles(): Boolean {
        val paths = arrayOf(
            "/system/app/Superuser.apk", "/sbin/su", "/system/bin/su", "/system/xbin/su",
            "/data/local/xbin/su", "/data/local/bin/su", "/system/sd/xbin/su",
            "/system/bin/failsafe/su", "/data/local/su", "/su/bin/su",
            "/magisk/.core/bin/su", "/system/usr/we-need-root/su-backup",
            "/system/xbin/mu", "/data/adb/magisk", "/sbin/magisk", "/data/adb/ksu"
        )
        for (path in paths) {
            if (File(path).exists()) return true
        }
        return false
    }

    private fun checkSuCommand(): Boolean {
        var process: Process? = null
        return try {
            process = Runtime.getRuntime().exec(arrayOf("/system/xbin/which", "su"))
            val inReader = BufferedReader(InputStreamReader(process.inputStream))
            inReader.readLine() != null
        } catch (t: Throwable) {
            false
        } finally {
            process?.destroy()
        }
    }

    private fun checkEmulator(): Boolean {
        return (Build.BRAND.startsWith("generic") && Build.DEVICE.startsWith("generic"))
                || Build.FINGERPRINT.startsWith("generic")
                || Build.FINGERPRINT.startsWith("unknown")
                || Build.HARDWARE.contains("goldfish")
                || Build.HARDWARE.contains("ranchu")
                || Build.MODEL.contains("google_sdk")
                || Build.MODEL.contains("Emulator")
                || Build.MODEL.contains("Android SDK built for x86")
                || Build.MANUFACTURER.contains("Genymotion")
                || Build.PRODUCT.contains("sdk_google")
                || Build.PRODUCT.contains("google_sdk")
                || Build.PRODUCT.contains("sdk")
                || Build.PRODUCT.contains("sdk_x86")
                || Build.PRODUCT.contains("vbox86p")
                || Build.PRODUCT.contains("emulator")
                || Build.PRODUCT.contains("simulator")
    }

    /**
     * Stable per-install identifier used as the device fingerprint.
     *
     * Returns exactly the value the OkHttp interceptor sends in
     * `X-Device-Fingerprint` on every request (`SecurePreferences.installId`).
     * The pre-flight `security/check-device/` call has to use the same string
     * the login headers do, otherwise the server would record the device
     * under one fingerprint and the login would check it under another —
     * admin approval would then apply to a row the login path never reads.
     *
     * The [context] parameter is accepted only for parity with the
     * pre-existing call sites; [SecurePreferences] is already initialised at
     * app start, so the value can be read without touching it.
     */
    @Suppress("UNUSED_PARAMETER")
    fun getDeviceFingerprint(context: Context? = null): String = SecurePreferences.installId

    /**
     * Get or derive device MAC address.
     * Checks network interfaces (wlan0, eth0, etc.) for a valid hardware address.
     * If restricted by Android (returns 02:00:00:00:00:00 or null), derives a deterministic
     * locally administered MAC address (02-XX-XX-XX-XX-XX) tied to the device installation
     * so that the server and Telegram alerts always receive a valid, stable, format-compliant MAC.
     */
    @Suppress("UNUSED_PARAMETER")
    fun getMacAddress(context: Context? = null): String {
        val hardwareMac = firstHardwareMac()
        if (hardwareMac != null) return hardwareMac

        // Fallback: Deterministic Locally Administered MAC address (02-xx-xx-xx-xx-xx)
        val seed = SecurePreferences.installId.ifBlank { Build.FINGERPRINT ?: "securemed_device" }
        // SHA-256, not MD5: this only derives a display identifier, but a weak
        // hash in a security-adjacent file is exactly what scanners (and
        // reviewers) flag, and SHA-256 costs nothing here.
        val digest = java.security.MessageDigest.getInstance("SHA-256").digest(seed.toByteArray())
        return String.format(
            Locale.US,
            "02-%02X-%02X-%02X-%02X-%02X",
            digest[0].toInt() and 0xFF, digest[1].toInt() and 0xFF,
            digest[2].toInt() and 0xFF, digest[3].toInt() and 0xFF,
            digest[4].toInt() and 0xFF
        )
    }

    /**
     * First valid hardware MAC on a Wi-Fi/Ethernet interface, or null when the
     * platform withholds it (Android 6+) or every candidate is the masked
     * `02:00:00:00:00:00`.
     */
    private fun firstHardwareMac(): String? {
        return try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces() ?: return null
            while (interfaces.hasMoreElements()) {
                val mac = macOf(interfaces.nextElement())
                if (mac != null) return mac
            }
            null
        } catch (_: Throwable) {
            // Ignore security or network exceptions
            null
        }
    }

    /**
     * Hardware MAC of a single interface, or null when the interface is not a
     * network candidate or its address is withheld/masked.
     */
    private fun macOf(nif: java.net.NetworkInterface): String? {
        val name = nif.name
        val isCandidate = name.equals("wlan0", ignoreCase = true) ||
            name.equals("eth0", ignoreCase = true) ||
            name.contains("wlan", ignoreCase = true)
        if (!isCandidate) return null
        // `and 0xFF` keeps two's-complement sign extension out of the hex:
        // without it a byte above 0x7F formats as eight digits ("FFFFFFAB")
        // instead of two, corrupting every MAC whose vendor prefix is high-bit.
        val macBytes = nif.hardwareAddress ?: return null
        val macStr = macBytes.joinToString("-") { byte ->
            String.format(Locale.US, "%02X", byte.toInt() and 0xFF)
        }
        return macStr.takeUnless {
            it.isBlank() || it == "02-00-00-00-00-00" || it == "00-00-00-00-00-00"
        }
    }

    /** Local IP address of active network interface (IPv4) */
    fun getLocalIpAddress(): String? {
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces() ?: return null
            while (interfaces.hasMoreElements()) {
                val nif = interfaces.nextElement()
                val addresses = nif.inetAddresses
                while (addresses.hasMoreElements()) {
                    val addr = addresses.nextElement()
                    if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                        return addr.hostAddress
                    }
                }
            }
        } catch (_: Throwable) {
            // ignore
        }
        return null
    }

    /** Readable Device Model (e.g. "Samsung SM-G991B" or "Google Pixel 7") */
    fun getDeviceModel(): String {
        val manufacturer = Build.MANUFACTURER.replaceFirstChar { it.uppercase() }
        val model = Build.MODEL
        return if (model.startsWith(manufacturer, ignoreCase = true)) {
            model
        } else {
            "$manufacturer $model"
        }
    }

    /** Readable OS version (e.g. "Android 14 (API 34)") */
    fun getOsVersion(): String = "Android ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})"

    /**
     * Checks if the device is currently mirroring or casting its screen to an
     * external display, presentation screen, or virtual display.
     *
     * In healthcare contexts, screen casting in public hospital waiting rooms or unapproved
     * monitors can leak sensitive Protected Health Information (PHI).
     */
    fun isScreenMirrored(context: Context): Boolean {
        if (!SecurePreferences.isScreenMirroringProtectionEnabled) return false
        return try {
            val displayManager = context.getSystemService(Context.DISPLAY_SERVICE) as? DisplayManager ?: return false
            val displays = displayManager.displays
            for (display in displays) {
                if (display.displayId != Display.DEFAULT_DISPLAY) {
                    val flags = display.flags
                    val isPresentation = (flags and Display.FLAG_PRESENTATION) != 0
                    val isNonSecure = (flags and Display.FLAG_SECURE) == 0
                    if (isPresentation || isNonSecure) {
                        return true
                    }
                }
            }
            false
        } catch (_: Throwable) {
            false
        }
    }

    /**
     * Clear the system clipboard immediately.
     */
    fun clearClipboard(context: Context) {
        try {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                clipboard.clearPrimaryClip()
            } else {
                clipboard.setPrimaryClip(ClipData.newPlainText("", ""))
            }
        } catch (_: Throwable) {}
    }

    /**
     * Schedules a delayed clipboard wipe after copying sensitive clinical data.
     * Default timeout is 30 seconds.
     */
    fun scheduleClipboardClear(context: Context, delayMillis: Long = 30_000L) {
        if (!SecurePreferences.isClipboardAutoClearEnabled) return
        val appContext = context.applicationContext ?: context
        Handler(Looper.getMainLooper()).postDelayed({
            clearClipboard(appContext)
        }, delayMillis)
    }

    /**
     * Mobile Attestation / Play Integrity Verdict for Device Posture.
     */
    data class DeviceIntegrityVerdict(
        val isHardwareBacked: Boolean,
        val hasBasicIntegrity: Boolean,
        val hasStrongIntegrity: Boolean,
        val isTampered: Boolean,
        val signals: List<String>
    )

    /**
     * Evaluates comprehensive hardware, OS, runtime, and app-level integrity:
     * - Root detection (Magisk, su binaries, remounts)
     * - Runtime tampering (Frida, Xposed, LSPosed, ptrace debugger)
     * - Emulator & custom test-keys firmware
     * - Hardware StrongBox KeyStore presence
     * - APK signing, DEX injection, hooking frameworks, RE tools
     */
    fun evaluateDeviceIntegrity(context: Context): DeviceIntegrityVerdict {
        val signals = mutableListOf<String>()

        val isRooted = isDeviceRooted()
        if (isRooted) signals.add("ROOT_DETECTED")

        val tamperSignals = TamperDetection.scan(context)
        for (signal in tamperSignals) {
            signals.add("${signal.check}:${signal.evidence}")
        }

        // App-level integrity (signing, DEX, hooking, RE tools)
        val appIntegritySignals = AppIntegrityGuard.fullIntegrityCheck(context)
        for (signal in appIntegritySignals) {
            signals.add("${signal.type}:${signal.detail}")
        }

        val isEmulator = isProbablyEmulator()
        if (isEmulator) signals.add("EMULATOR_ENVIRONMENT")

        val hasTestKeys = hasTestKeys()
        if (hasTestKeys) signals.add("TEST_KEYS_SIGNATURE")

        val hasStrongBox = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            context.packageManager.hasSystemFeature(android.content.pm.PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        } else {
            false
        }

        val hasCriticalAppIssue = appIntegritySignals.any {
            it.severity == AppIntegrityGuard.Severity.CRITICAL
        }
        val hasBasicIntegrity = !isRooted && tamperSignals.isEmpty() && !hasCriticalAppIssue
        val hasStrongIntegrity = hasBasicIntegrity && !isEmulator && !hasTestKeys

        return DeviceIntegrityVerdict(
            isHardwareBacked = hasStrongBox,
            hasBasicIntegrity = hasBasicIntegrity,
            hasStrongIntegrity = hasStrongIntegrity,
            isTampered = !hasBasicIntegrity,
            signals = signals
        )
    }
}

