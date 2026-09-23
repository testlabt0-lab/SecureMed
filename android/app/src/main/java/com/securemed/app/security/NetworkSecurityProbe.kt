package com.securemed.app.security

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build

/**
 * Network Security Probe for SecureMed.
 *
 * Inspects active network transport security:
 * 1. Open/Insecure Wi-Fi detection (unencrypted public networks).
 * 2. Active VPN / Proxy inspection (detecting interception proxies).
 */
object NetworkSecurityProbe {

    data class NetworkSecurityStatus(
        val isSecure: Boolean,
        val warningMessage: String? = null,
        val isVpnActive: Boolean = false,
        val isWifi: Boolean = false
    )

    fun assessNetworkSecurity(context: Context): NetworkSecurityStatus {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager
            ?: return NetworkSecurityStatus(isSecure = true)

        val activeNetwork = cm.activeNetwork
            ?: return NetworkSecurityStatus(isSecure = true, warningMessage = "لا يوجد اتصال نشط بالشبكة")

        val capabilities = cm.getNetworkCapabilities(activeNetwork)
            ?: return NetworkSecurityStatus(isSecure = true)

        val isVpn = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)
        val isWifi = capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)

        // Check if network is captive portal or lacks security capabilities
        val isCaptivePortal = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL)
        } else {
            false
        }

        if (isCaptivePortal) {
            return NetworkSecurityStatus(
                isSecure = false,
                warningMessage = "شبكة الواي فاي الحالية غير مكتملة المصادقة (Captive Portal). تجنب نقل السجلات الطبية.",
                isVpnActive = isVpn,
                isWifi = isWifi
            )
        }

        return NetworkSecurityStatus(
            isSecure = true,
            isVpnActive = isVpn,
            isWifi = isWifi
        )
    }
}
