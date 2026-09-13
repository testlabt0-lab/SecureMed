package com.securemed.app.security

import android.content.Context
import android.os.Build
import com.securemed.app.data.local.SecurePreferences
import java.io.File
import java.io.BufferedReader
import java.io.InputStreamReader

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
        try {
            val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
            if (interfaces != null) {
                while (interfaces.hasMoreElements()) {
                    val nif = interfaces.nextElement()
                    if (!nif.name.equals("wlan0", ignoreCase = true) &&
                        !nif.name.equals("eth0", ignoreCase = true) &&
                        !nif.name.contains("wlan", ignoreCase = true)
                    ) continue
                    val macBytes = nif.hardwareAddress ?: continue
                    val sb = StringBuilder()
                    for (b in macBytes) {
                        sb.append(String.format("%02X-", b))
                    }
                    if (sb.isNotEmpty()) {
                        sb.deleteCharAt(sb.length - 1)
                    }
                    val macStr = sb.toString()
                    if (macStr.isNotBlank() && macStr != "02-00-00-00-00-00" && macStr != "00-00-00-00-00-00") {
                        return macStr
                    }
                }
            }
        } catch (_: Throwable) {
            // Ignore security or network exceptions
        }

        // Fallback: Deterministic Locally Administered MAC address (02-xx-xx-xx-xx-xx)
        val seed = SecurePreferences.installId.ifBlank { Build.FINGERPRINT ?: "securemed_device" }
        val digest = java.security.MessageDigest.getInstance("MD5").digest(seed.toByteArray())
        return String.format(
            "02-%02X-%02X-%02X-%02X-%02X",
            digest[0], digest[1], digest[2], digest[3], digest[4]
        )
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
}

