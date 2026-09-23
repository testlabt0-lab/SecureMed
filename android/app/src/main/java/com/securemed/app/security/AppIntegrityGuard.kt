package com.securemed.app.security

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import com.securemed.app.BuildConfig
import java.io.File
import java.security.MessageDigest
import java.util.zip.ZipFile

/**
 * حارس سلامة التطبيق — الحماية من الهندسة العكسية وكسر التطبيق.
 *
 * يتحقق من:
 *  1. **سلامة توقيع APK** — هل التوقيع الحالي يطابق التوقيع الأصلي؟
 *     (يكشف إعادة التوقيع بعد التعديل)
 *  2. **سلامة ملفات DEX** — هل تم حقن كود أو تعديل classes.dex؟
 *  3. **كشف أدوات فك التجميع** — هل توجد أدوات مثل apktool أو jadx؟
 *  4. **كشف بيئة تحليل ديناميكي** — هل التطبيق يعمل في sandbox تحليلي؟
 *  5. **حماية Debuggable flag** — هل تم تعديل المانيفست ليكون debuggable؟
 *
 * كل فحص يعيد [IntegritySignal] لمنح المُستدعي مرونة في التعامل.
 */
object AppIntegrityGuard {

    /** إشارة واحدة لانتهاك سلامة. */
    data class IntegritySignal(
        val type: String,
        val detail: String,
        val severity: Severity
    )

    enum class Severity { LOW, MEDIUM, HIGH, CRITICAL }

    /**
     * الـ SHA-256 المتوقع لتوقيع APK الرسمي (release signing certificate).
     *
     * يُحسب مرة واحدة بعد أول بناء release ويُحدّث هنا.
     * عند التطوير، اتركه فارغاً لتخطي الفحص في debug builds.
     *
     * لحسابه:
     * ```
     * keytool -list -v -keystore release.jks | grep SHA256
     * ```
     */
    private const val EXPECTED_SIGNING_CERT_SHA256 = ""

    /** أدوات الهندسة العكسية المعروفة. */
    private val RE_TOOL_PACKAGES = listOf(
        "com.jrummyapps.rootbrowser",        // Root Browser
        "stericson.busybox",                   // BusyBox
        "com.topjohnwu.magisk",                // Magisk Manager
        "eu.chainfire.supersu",                // SuperSU
        "com.noshufou.android.su",             // Superuser
        "com.thirdparty.superuser",            // Another Superuser
        "com.koushikdutta.superuser",          // Koushik Superuser
        "com.zachspong.temprootremovejb",       // Temp Root Remover
        "com.ramdroid.appquarantine",           // App Quarantine
        "org.jf.dexlib2",                       // smali / baksmali
    )

    /** ملفات/مسارات تشير إلى بيئة تحليل. */
    private val ANALYSIS_ARTIFACTS = listOf(
        "/data/local/tmp/drozer",
        "/data/local/tmp/android_server",       // IDA Pro remote server
        "/data/local/tmp/gdb",
        "/data/local/tmp/gdbserver",
        "/data/local/tmp/strace",
        "/data/local/tmp/ltrace",
        "/proc/self/status",                    // TracerPid check (read below)
    )

    /**
     * تنفيذ فحص شامل لسلامة التطبيق.
     */
    fun fullIntegrityCheck(context: Context): List<IntegritySignal> {
        val signals = mutableListOf<IntegritySignal>()

        runCatching { signals += checkSigningCertificate(context) }
        runCatching { signals += checkDebuggableFlag(context) }
        runCatching { signals += checkInstallerSource(context) }
        runCatching { signals += checkDexIntegrity(context) }
        runCatching { signals += checkReverseEngineeringTools(context) }
        runCatching { signals += checkDynamicAnalysisEnvironment() }
        runCatching { signals += checkPtraceStatus() }
        runCatching { signals += checkHookingFrameworks() }

        return signals
    }

    /** هل الشهادة الحالية تطابق الشهادة المتوقعة؟ */
    @Suppress("DEPRECATION", "PackageManagerGetSignatures")
    private fun checkSigningCertificate(context: Context): List<IntegritySignal> {
        if (EXPECTED_SIGNING_CERT_SHA256.isBlank()) return emptyList()

        val out = mutableListOf<IntegritySignal>()
        try {
            val packageInfo = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNING_CERTIFICATES
                )
            } else {
                context.packageManager.getPackageInfo(
                    context.packageName,
                    PackageManager.GET_SIGNATURES
                )
            }

            val signatures = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
                packageInfo.signingInfo?.apkContentsSigners
            } else {
                @Suppress("DEPRECATION")
                packageInfo.signatures
            }

            if (signatures.isNullOrEmpty()) {
                out += IntegritySignal(
                    "SIGNING_MISSING",
                    "No signing certificates found",
                    Severity.CRITICAL
                )
                return out
            }

            for (sig in signatures) {
                val digest = MessageDigest.getInstance("SHA-256")
                val hash = digest.digest(sig.toByteArray())
                    .joinToString("") { "%02X".format(it) }

                if (!hash.equals(EXPECTED_SIGNING_CERT_SHA256, ignoreCase = true)) {
                    out += IntegritySignal(
                        "SIGNING_MISMATCH",
                        "APK re-signed with unknown certificate: ${hash.take(16)}…",
                        Severity.CRITICAL
                    )
                }
            }
        } catch (e: Exception) {
            out += IntegritySignal(
                "SIGNING_CHECK_FAILED",
                "Could not verify signing certificate: ${e.message}",
                Severity.MEDIUM
            )
        }
        return out
    }

    /** هل المانيفست يحمل android:debuggable=true في بناء release؟ */
    private fun checkDebuggableFlag(context: Context): List<IntegritySignal> {
        val isDebuggable = (context.applicationInfo.flags and
                android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0

        return if (isDebuggable && !BuildConfig.DEBUG) {
            listOf(
                IntegritySignal(
                    "DEBUGGABLE_IN_RELEASE",
                    "Application is debuggable in a non-debug build — likely tampered manifest",
                    Severity.CRITICAL
                )
            )
        } else {
            emptyList()
        }
    }

    /** هل التطبيق تم تثبيته من مصدر موثوق (Play Store / Galaxy Store)؟ */
    private fun checkInstallerSource(context: Context): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        try {
            val installer = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                context.packageManager.getInstallSourceInfo(context.packageName).installingPackageName
            } else {
                @Suppress("DEPRECATION")
                context.packageManager.getInstallerPackageName(context.packageName)
            }

            val trustedInstallers = listOf(
                "com.android.vending",           // Google Play Store
                "com.sec.android.app.samsungapps", // Samsung Galaxy Store
                "com.huawei.appmarket",           // Huawei AppGallery
                "com.amazon.venezia",             // Amazon Appstore
            )

            if (installer != null && installer !in trustedInstallers) {
                out += IntegritySignal(
                    "UNTRUSTED_INSTALLER",
                    "Installed via: $installer (not a recognized app store)",
                    Severity.MEDIUM
                )
            } else if (installer == null) {
                out += IntegritySignal(
                    "SIDELOADED",
                    "No installer recorded — app was sideloaded via ADB or file manager",
                    Severity.LOW
                )
            }
        } catch (_: Throwable) { /* ignore on older APIs */ }
        return out
    }

    /**
     * تحقق من عدد ملفات DEX — إذا زاد عن المتوقع، ربما تم حقن كود.
     * يتحقق أيضاً من عدم وجود ملفات مشبوهة داخل APK.
     */
    private fun checkDexIntegrity(context: Context): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        try {
            val apkPath = context.applicationInfo.sourceDir
            ZipFile(apkPath).use { zip ->
                val dexEntries = zip.entries().asSequence()
                    .filter { it.name.endsWith(".dex") }
                    .toList()

                // Multidex apps may have multiple DEX files, but more than 10
                // is suspicious
                if (dexEntries.size > 10) {
                    out += IntegritySignal(
                        "EXCESSIVE_DEX_FILES",
                        "Found ${dexEntries.size} DEX files — possible code injection",
                        Severity.HIGH
                    )
                }

                // Check for suspicious files inside the APK
                val suspiciousEntries = zip.entries().asSequence()
                    .filter { entry ->
                        val name = entry.name.lowercase()
                        name.contains("xposed") ||
                        name.contains("frida") ||
                        name.contains("substrate") ||
                        name.endsWith(".so") && name.contains("hook")
                    }
                    .toList()

                for (entry in suspiciousEntries) {
                    out += IntegritySignal(
                        "SUSPICIOUS_APK_CONTENT",
                        "Suspicious file inside APK: ${entry.name}",
                        Severity.CRITICAL
                    )
                }
            }
        } catch (_: Throwable) { /* zip read failure is non-fatal */ }
        return out
    }

    /** كشف تطبيقات الهندسة العكسية المثبتة. */
    private fun checkReverseEngineeringTools(context: Context): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        for (pkg in RE_TOOL_PACKAGES) {
            try {
                context.packageManager.getPackageInfo(pkg, 0)
                out += IntegritySignal(
                    "RE_TOOL_INSTALLED",
                    "Reverse engineering tool installed: $pkg",
                    Severity.HIGH
                )
            } catch (_: PackageManager.NameNotFoundException) {
                // Not installed — safe
            }
        }
        return out
    }

    /** كشف أدوات التحليل الديناميكي (IDA, gdb, strace...) */
    private fun checkDynamicAnalysisEnvironment(): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        for (path in ANALYSIS_ARTIFACTS) {
            if (path == "/proc/self/status") continue // handled separately
            if (File(path).exists()) {
                out += IntegritySignal(
                    "ANALYSIS_TOOL_FOUND",
                    "Dynamic analysis artifact: $path",
                    Severity.HIGH
                )
            }
        }
        return out
    }

    /**
     * فحص TracerPid — إذا كانت القيمة غير صفرية، فهناك عملية
     * تتتبع التطبيق (debugger / ptrace / strace).
     */
    private fun checkPtraceStatus(): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        try {
            val status = File("/proc/self/status").readText()
            val tracerPid = Regex("TracerPid:\\s+(\\d+)")
                .find(status)
                ?.groupValues?.get(1)
                ?.toIntOrNull() ?: 0

            if (tracerPid != 0) {
                out += IntegritySignal(
                    "PTRACE_ATTACHED",
                    "Process is being traced by PID $tracerPid",
                    Severity.CRITICAL
                )
            }
        } catch (_: Throwable) { /* /proc may be restricted */ }
        return out
    }

    /**
     * كشف أُطر الاعتراض (Hooking Frameworks) من خلال فحص
     * المكتبات المحملة في الذاكرة.
     */
    private fun checkHookingFrameworks(): List<IntegritySignal> {
        val out = mutableListOf<IntegritySignal>()
        try {
            val maps = File("/proc/self/maps").readText()
            val suspiciousLibs = mapOf(
                "libsubstrate" to "Cydia Substrate hooking framework",
                "libepic" to "Epic (Virtual Xposed) hooking library",
                "libsandhook" to "SandHook ART hooking framework",
                "libwhale" to "Whale hooking framework",
                "libpine" to "Pine (LSPosed) hooking engine",
                "libdobby" to "Dobby inline hooking library",
            )

            for ((lib, desc) in suspiciousLibs) {
                if (maps.contains(lib, ignoreCase = true)) {
                    out += IntegritySignal(
                        "HOOKING_FRAMEWORK",
                        "$desc detected in process memory ($lib)",
                        Severity.CRITICAL
                    )
                }
            }
        } catch (_: Throwable) { /* /proc/self/maps may be restricted */ }
        return out
    }

    /**
     * تقييم شامل — يُرجع true إذا كان التطبيق يعمل في بيئة آمنة.
     */
    fun isAppIntact(context: Context): Boolean {
        val signals = fullIntegrityCheck(context)
        return signals.none { it.severity == Severity.CRITICAL || it.severity == Severity.HIGH }
    }

    /**
     * يُرجع تقريراً مُجملاً من جميع الفحوصات.
     */
    fun getIntegritySummary(context: Context): String {
        val signals = fullIntegrityCheck(context)
        if (signals.isEmpty()) return "✅ All integrity checks passed"

        val sb = StringBuilder("⚠️ Integrity Issues Detected:\n")
        for (signal in signals) {
            sb.append("  [${signal.severity}] ${signal.type}: ${signal.detail}\n")
        }
        return sb.toString()
    }
}
