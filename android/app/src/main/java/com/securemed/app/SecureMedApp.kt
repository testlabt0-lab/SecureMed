package com.securemed.app

import android.app.Application
import android.content.Context
import com.securemed.app.data.ConnectivityObserver
import com.securemed.app.data.local.LocalCache
import com.securemed.app.data.local.MedicationStore
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.local.room.SecureMedDatabase
import com.securemed.app.reminders.NotificationHelper
import com.securemed.app.security.AppLock
import com.securemed.app.ui.theme.ThemeController
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration

import com.securemed.app.util.CrashHandler

/**
 * Application class - initializes secure storage, the offline cache,
 * notification channels, connectivity observation, theme and crash reporting.
 *
 * @HiltAndroidApp triggers Hilt's code generation for the dependency
 * injection container that serves as the application's parent component.
 */
@HiltAndroidApp
class SecureMedApp : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    @Inject lateinit var database: SecureMedDatabase

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()

    companion object {
        lateinit var instance: SecureMedApp
            private set
    }

    /** App-wide connectivity state, shared by every screen. */
    val connectivity: ConnectivityObserver by lazy { ConnectivityObserver(this) }

    override fun onCreate() {
        super.onCreate()
        instance = this
        // 1. Install crash handler first so any subsequent uncaught error is intercepted
        CrashHandler.init(this)
        
        // 2. Initialize encrypted preferences with fully attached application context
        SecurePreferences.init(this)

        // 3. Security and cache setup
        AppLock.init()
        LocalCache.init(this)

        // 4. Safely initialize MedicationStore and run one-time cache migration
        runCatching {
            MedicationStore.init(database.medicationDao())
            MedicationStore.migrateFromLocalCache()
        }.onFailure { error ->
            android.util.Log.e("SecureMedApp", "MedicationStore initialization warning", error)
        }

        // 5. System notification channels & theme
        NotificationHelper.ensureChannels(this)
        ThemeController.init(SecurePreferences.darkMode)
    }
}
