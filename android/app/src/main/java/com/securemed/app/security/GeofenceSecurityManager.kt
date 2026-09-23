package com.securemed.app.security

import android.content.Context
import android.location.Location
import com.securemed.app.data.local.SecurePreferences
import kotlin.math.*

/**
 * Geofence & Subnet Security Manager for Healthcare Data.
 *
 * Implements perimeter-based clinical data protection:
 * Ensures patient records are protected when devices operate outside hospital grounds,
 * requiring explicit biometric confirmation or break-glass authorization.
 */
object GeofenceSecurityManager {

    // Default Clinic / Hospital Coordinates (configurable)
    var clinicLatitude: Double = 24.7136
    var clinicLongitude: Double = 46.6753
    var perimeterRadiusMeters: Float = 2000f // 2 km radius

    /**
     * Calculates the great-circle distance between two coordinates in meters.
     */
    fun calculateDistanceMeters(
        lat1: Double,
        lon1: Double,
        lat2: Double,
        lon2: Double
    ): Float {
        val results = FloatArray(1)
        Location.distanceBetween(lat1, lon1, lat2, lon2, results)
        return results[0]
    }

    /**
     * Evaluates if the current coordinates are within the safe clinic perimeter.
     */
    fun isInsideClinicPerimeter(currentLat: Double?, currentLon: Double?): Boolean {
        if (!SecurePreferences.isGeoRestrictionEnabled) return true
        if (currentLat == null || currentLon == null) return false

        val distance = calculateDistanceMeters(currentLat, currentLon, clinicLatitude, clinicLongitude)
        return distance <= perimeterRadiusMeters
    }
}
