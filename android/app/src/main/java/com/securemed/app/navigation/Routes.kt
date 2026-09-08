package com.securemed.app.navigation

/**
 * Type-safe navigation routes for the app.
 *
 * Using a sealed class instead of raw strings prevents typo-related crashes
 * and gives compile-time safety for every navigation destination.
 */
sealed class Route(val route: String) {

    // ===== Auth =====
    data object DeviceCheck : Route("device_check")
    data object Login : Route("login")

    // ===== Main tabs =====
    data object Dashboard : Route("dashboard")
    data object Patients : Route("patients")
    data object Channels : Route("channels")
    data object Medications : Route("medications")
    data object Profile : Route("profile")

    // ===== Detail screens =====
    data object ChannelDetail : Route("channel/{id}") {
        fun createRoute(id: String) = "channel/$id"
    }

    data object PatientDetail : Route("patient/{id}") {
        fun createRoute(id: String) = "patient/$id"
    }

    // ===== Secondary screens =====
    data object Users : Route("users")
    data object Notifications : Route("notifications")
    data object Appointments : Route("appointments")
    data object Pharmacy : Route("pharmacy")
    data object Lab : Route("lab")
    data object Telemedicine : Route("telemedicine")
    data object Analytics : Route("analytics")
    data object Settings : Route("settings")

    // ===== Channel sub-screens =====
    /**
     * Reserved for the channel chat screen (roadmap Phase 4). Declared but
     * not yet registered in the NavHost — navigating to it would throw, so
     * it must stay unused until ChannelChatScreen exists.
     */
    data object ChannelChat : Route("channel/{id}/chat") {
        fun createRoute(id: String) = "channel/$id/chat"
    }
}
