package com.securemed.app.util

import android.app.Application
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Process
import android.util.Log
import com.securemed.app.BuildConfig
import com.securemed.app.ui.CrashActivity
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.system.exitProcess

/**
 * Global uncaught exception handler.
 * Catches fatal crashes, writes diagnostics to a persistent file, and launches
 * [CrashActivity] in a separate process so the user and developer can inspect
 * the root cause instead of suffering a silent OS kill.
 */
object CrashHandler {
    private const val TAG = "CrashHandler"
    const val CRASH_LOG_FILE = "last_crash.txt"

    private var defaultHandler: Thread.UncaughtExceptionHandler? = null
    @Volatile
    private var isHandlingCrash = false

    fun init(app: Application) {
        if (defaultHandler != null) return
        defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            handleUncaughtException(app, thread, throwable)
        }
    }

    private fun handleUncaughtException(context: Context, thread: Thread, throwable: Throwable) {
        if (isHandlingCrash) {
            defaultHandler?.uncaughtException(thread, throwable)
            return
        }
        isHandlingCrash = true

        val sw = StringWriter()
        val pw = PrintWriter(sw)
        throwable.printStackTrace(pw)
        val stackTrace = sw.toString()

        val timeStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(Date())
        val report = buildString {
            appendLine("=== SecureMed Crash Report ===")
            appendLine("Time: $timeStr")
            appendLine("App Version: ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})")
            appendLine("Build Type: ${BuildConfig.BUILD_TYPE}")
            appendLine("Device: ${Build.MANUFACTURER} ${Build.MODEL} (${Build.DEVICE})")
            appendLine("Android OS: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
            appendLine("Thread: ${thread.name} (id: ${thread.id})")
            appendLine("Exception: ${throwable.javaClass.name}: ${throwable.message}")
            appendLine("\n--- Stack Trace ---")
            appendLine(stackTrace)
            var cause = throwable.cause
            var depth = 1
            while (cause != null && depth <= 5) {
                appendLine("\n--- Caused by ($depth): ${cause.javaClass.name}: ${cause.message} ---")
                val causeSw = StringWriter()
                cause.printStackTrace(PrintWriter(causeSw))
                appendLine(causeSw.toString())
                cause = cause.cause
                depth++
            }
        }

        Log.e(TAG, "FATAL CRASH:\n$report")

        runCatching {
            val file = File(context.filesDir, CRASH_LOG_FILE)
            file.writeText(report)
        }

        runCatching {
            val intent = Intent(context, CrashActivity::class.java).apply {
                putExtra(CrashActivity.EXTRA_CRASH_INFO, report)
                addFlags(
                    Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP
                )
            }
            context.startActivity(intent)
        }

        try {
            Thread.sleep(300)
        } catch (_: InterruptedException) {}

        Process.killProcess(Process.myPid())
        exitProcess(10)
    }
}
