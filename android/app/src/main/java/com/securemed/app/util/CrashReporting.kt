package com.securemed.app.util

import android.util.Log

/**
 * CrashReporting utility.
 * In a real-world production app, this would wrap Firebase Crashlytics or Sentry.
 * For this DevSecOps university project, it serves as the logging abstraction layer.
 */
object CrashReporting {
    
    fun recordException(e: Throwable, contextInfo: String = "") {
        // Here you would normally call FirebaseCrashlytics.getInstance().recordException(e)
        // For development, we log it securely without leaking PII.
        Log.e("SecureMed_Crash", "Exception caught in $contextInfo: ${e.message}")
    }
    
    fun logMessage(message: String) {
        // FirebaseCrashlytics.getInstance().log(message)
        Log.i("SecureMed_Crash", message)
    }
}
