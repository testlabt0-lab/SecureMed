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

    // ===== Operations screens (3-6) =====
    data object LabResults : Route("lab_results")
    data object Wards : Route("wards")
    data object Invoices : Route("invoices")
    data object Audit : Route("audit")

    // ===== Channel sub-screens =====
    /**
     * In-channel secure chat (Phase 4). `name` is an optional query argument
     * carrying the channel title so the chat bar renders it before the
     * channel request resolves; the ViewModel re-fetches regardless.
     */
    data object ChannelChat : Route("channel/{id}/chat?name={name}") {
        fun createRoute(id: String, name: String = "") =
            "channel/$id/chat?name=${android.net.Uri.encode(name)}"
    }
}
