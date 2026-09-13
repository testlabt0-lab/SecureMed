package com.securemed.app.di

import android.content.Context
import androidx.room.Room
import com.securemed.app.data.local.SecurePreferences
import com.securemed.app.data.local.room.MedicationDao
import com.securemed.app.data.local.room.SecureMedDao
import com.securemed.app.data.local.room.SecureMedDatabase
import net.sqlcipher.database.SQLiteDatabase
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
        // 1. Ensure SQLCipher native binaries are loaded
        SQLiteDatabase.loadLibs(context)

        // 2. Initialize preferences and retrieve the database passphrase
        SecurePreferences.init(context)
        val passphrase = SecurePreferences.getDatabasePassphrase(context)

        // 3. Pre-flight check: if database file exists on disk, ensure it opens with the passphrase.
        // If an older build created it with a wiped or mismatched key, delete it before Room starts
        // to avoid a fatal "file is not a database" SQLiteException.
        val dbFile = context.getDatabasePath(SecureMedDatabase.DATABASE_NAME)
        if (dbFile.exists()) {
            try {
                val db = SQLiteDatabase.openOrCreateDatabase(
                    dbFile.absolutePath,
                    passphrase,
                    null,
                    null,
                    null
                )
                try {
                    val cursor = db.rawQuery("SELECT count(*) FROM sqlite_master;", null)
                    try {
                        cursor.moveToFirst()
                    } finally {
                        cursor.close()
                    }
                } finally {
                    db.close()
                }
            } catch (e: Exception) {
                android.util.Log.e("DatabaseModule", "Existing database unreadable, recreating cleanly", e)
                context.deleteDatabase(SecureMedDatabase.DATABASE_NAME)
            }
        }

        // 4. clearPassphrase = false ensures Room can perform multiple connections/migrations
        // without SQLCipher zeroing out the passphrase array in memory.
        val factory = SupportFactory(passphrase, null, false)

        return Room.databaseBuilder(
            context,
            SecureMedDatabase::class.java,
            SecureMedDatabase.DATABASE_NAME
        )
        .openHelperFactory(factory)
        .addMigrations(SecureMedDatabase.MIGRATION_3_4)
        .fallbackToDestructiveMigration()
        .build()
    }

    @Provides
    fun provideSecureMedDao(database: SecureMedDatabase): SecureMedDao {
        return database.secureMedDao()
    }

    @Provides
    fun provideMedicationDao(database: SecureMedDatabase): MedicationDao {
        return database.medicationDao()
    }
}
