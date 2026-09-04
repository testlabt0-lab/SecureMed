package com.securemed.app

import android.app.Application
import com.securemed.app.data.ConnectivityObserver
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.ui.theme.ThemeController
import dagger.hilt.android.HiltAndroidApp

/**
 * Application class - initializes secure storage, the offline cache,
 * notification channels, connectivity observation and the theme.
 *
 * @HiltAndroidApp triggers Hilt's code generation for the dependency
 * injection container that serves as the application's parent component.
 */
@HiltAndroidApp
class SecureMedApp : Application() {

    companion object {
        lateinit var instance: SecureMedApp
            private set
    }

    /** App-wide connectivity state, shared by every screen. */
    val connectivity: ConnectivityObserver by lazy { ConnectivityObserver(this) }

    override fun onCreate() {
        super.onCreate()
        instance = this
        SecurePreferences.init(this)
        LocalCache.init(this)
        NotificationHelper.ensureChannels(this)
        ThemeController.init(SecurePreferences.darkMode)
    }
}
