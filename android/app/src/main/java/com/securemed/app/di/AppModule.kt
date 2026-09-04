package com.securemed.app.di

import com.securemed.app.data.SecureMedRepository
import com.securemed.app.data.api.NetworkModule
import com.securemed.app.data.api.SecureMedApi
import com.securemed.app.data.local.MedicationStore
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Main Hilt module — provides app-wide singletons for networking and data.
 *
 * All ViewModels receive their dependencies through constructor injection
 * instead of creating instances internally, making them testable with fakes.
 */
@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideSecureMedApi(): SecureMedApi = NetworkModule.api

}
