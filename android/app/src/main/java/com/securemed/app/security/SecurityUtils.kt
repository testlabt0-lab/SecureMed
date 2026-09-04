package com.securemed.app.security

import android.os.Build
import java.io.File
import java.io.BufferedReader
import java.io.InputStreamReader

object SecurityUtils {
    /**
     * التحقق مما إذا كان الجهاز مكسور الحماية (Rooted) أو يعمل على محاكي (Emulator).
     * هذه الفحوصات موسعة لتشمل Magisk وأدوات الروت الحديثة، بالإضافة لبيئات المحاكاة.
     */
    fun isDeviceRooted(): Boolean {
        return checkTestKeys() || checkRootFiles() || checkSuCommand() || checkEmulator()
    }

    private fun checkTestKeys(): Boolean {
        val buildTags = Build.TAGS
        return buildTags != null && buildTags.contains("test-keys")
    }

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
}
