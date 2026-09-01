package com.securemed.app

import android.app.Application
import com.securemed.app.data.local.SecurePreferences

/**
 * Application class - initializes secure storage.
 */
class SecureMedApp : Application() {
    override fun onCreate() {
        super.onCreate()
        SecurePreferences.init(this)
    }
}
