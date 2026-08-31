package com.securemed.app

import android.app.Application
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper

/**
 * Application class - initializes secure storage and offline cache.
 */
class SecureMedApp : Application() {

    companion object {
        /** Global application reference (for components without context). */
        @Volatile
        var instance: SecureMedApp? = null
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        SecurePreferences.init(this)
        LocalCache.init(this)
        NotificationHelper.ensureChannels(this)
    }
}
