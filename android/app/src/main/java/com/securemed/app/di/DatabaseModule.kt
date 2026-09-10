package com.securemed.app.di

import android.content.Context
import androidx.room.Room
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.local.room.SecureMedDatabase
import net.sqlcipher.database.SupportFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): SecureMedDatabase {
        val passphrase = SecurePreferences.getDatabasePassphrase()
        val factory = SupportFactory(passphrase)

        return Room.databaseBuilder(
            context,
            SecureMedDatabase::class.java,
            SecureMedDatabase.DATABASE_NAME
        )
        .openHelperFactory(factory)
        // Version 2 → 3 added the medication tables, and SecureMedApp ran
        // `MedicationStore.migrateFromLocalCache()` before this builder ever
        // opens the file — so by the time Room reads the file the device-only
        // rows are importable and no destructive fallback can lose them.
        // Version 3 → 4 added the pending-sync idempotency columns.
        .addMigrations(SecureMedDatabase.MIGRATION_3_4)
        // Still a floor, not a substitute for migrations: for versions ≥ 3 a
        // destructive fallback WOULD drop device-only rows (plans/logs are
        // not refetchable from the server). A release that bumps the schema
        // past 4 must write real Migrations and, to test them, flip
        // exportSchema = true plus a room.schemaLocation KSP argument.
        .fallbackToDestructiveMigration()
        .build()
    }

    @Provides
    fun provideSecureMedDao(database: SecureMedDatabase): SecureMedDao {
        return database.secureMedDao()
    }
}
