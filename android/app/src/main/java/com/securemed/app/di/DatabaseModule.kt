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
            "securemed_local_db"
        )
        .openHelperFactory(factory)
        .build()
    }

    @Provides
    fun provideSecureMedDao(database: SecureMedDatabase): SecureMedDao {
        return database.secureMedDao()
    }
}
