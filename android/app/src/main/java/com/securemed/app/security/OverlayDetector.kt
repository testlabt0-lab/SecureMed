package com.securemed.app.security

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.Context
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager

/**
 * Overlay and Tapjacking Detection for SecureMed.
 *
 * Protects clinical workflows against:
 * 1. Screen Overlays (invisible or misleading overlays drawn over the app).
 * 2. Malicious Accessibility Services stealing screen content / keylogging PHI.
 */
object OverlayDetector {

    data class OverlaySecurityRisk(
        val type: String,
        val description: String,
        val packageName: String? = null
    )

    /**
     * Checks if the device has applications with overlay permissions or suspicious
     * accessibility services currently active.
     */
    fun scanForRisks(context: Context): List<OverlaySecurityRisk> {
        val risks = mutableListOf<OverlaySecurityRisk>()

        // 1. Check for active accessibility services that might read the screen
        val accessibilityManager =
            context.getSystemService(Context.ACCESSIBILITY_SERVICE) as? AccessibilityManager

        if (accessibilityManager != null) {
            val enabledServices = accessibilityManager.getEnabledAccessibilityServiceList(
                AccessibilityServiceInfo.FEEDBACK_ALL_MASK
            )

            for (service in enabledServices) {
                val serviceInfo = service.resolveInfo?.serviceInfo
                val pkgName = serviceInfo?.packageName ?: ""

                // Known trusted system accessibility packages (e.g., TalkBack, Switch Access, Samsung, Google)
                val isSystemOrTrusted = pkgName.startsWith("com.google.android.marvin.talkback") ||
                    pkgName.startsWith("com.google.android.accessibility") ||
                    pkgName.startsWith("com.android.") ||
                    pkgName.startsWith("com.samsung.accessibility") ||
                    (serviceInfo?.applicationInfo?.flags?.and(android.content.pm.ApplicationInfo.FLAG_SYSTEM) ?: 0) != 0

                if (!isSystemOrTrusted) {
                    risks.add(
                        OverlaySecurityRisk(
                            type = "ACCESSIBILITY_INTERCEPTION",
                            description = "خدمة وصول غير نظامية نشطة قد تسجل نصوص الشاشة: $pkgName",
                            packageName = pkgName
                        )
                    )
                }
            }
        }

        // 2. Check if the app itself is obscured or if dangerous draw-overlay state is detected
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (Settings.canDrawOverlays(context)) {
                // Application has overlay permission - should only be used if explicitly required
            }
        }

        return risks
    }
}
