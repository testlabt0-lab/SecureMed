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
        // The schema is at version 1 with no migrations written, and Room's
        // default for a version bump it cannot migrate is to throw
        // IllegalStateException on the first query — on every already-installed
        // device, at the first screen that reads the cache. Dropping the tables
        // instead is safe *here* specifically because every entity in this
        // database is a copy of something the server still holds (see
        // SecureMedDatabase): the next successful request refills it. Device-only
        // data — medication plans and dose logs — is deliberately not in Room.
        //
        // This is a floor, not a substitute for migrations: a release that must
        // keep the cached rows still has to add a Migration and, to test it,
        // exportSchema = true plus a room.schemaLocation KSP argument.
        .fallbackToDestructiveMigration()
        .build()
    }

    @Provides
    fun provideSecureMedDao(database: SecureMedDatabase): SecureMedDao {
        return database.secureMedDao()
    }
}
