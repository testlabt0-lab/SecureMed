package com.securemed.app

import android.app.Application
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

/**
 * Application class - initializes secure storage, the offline cache,
 * notification channels, connectivity observation and the theme.
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
        SecurePreferences.init(this)
        // After SecurePreferences: the idle timeout is stored there. Before any
        // screen exists, because MainActivity checks the lock in onResume and a
        // process that was killed while locked must come back locked.
        AppLock.init()
        LocalCache.init(this)
        // 3-4: medication plans/logs moved from encrypted JSON files into
        // Room. The one-time import must run BEFORE the database is first
        // opened elsewhere, because DatabaseModule's destructive fallback is
        // the only thing that could drop these tables — and the files being
        // deleted after a successful import make this migration idempotent.
        MedicationStore.init(database.medicationDao())
        MedicationStore.migrateFromLocalCache()
        NotificationHelper.ensureChannels(this)
        ThemeController.init(SecurePreferences.darkMode)
    }
}
