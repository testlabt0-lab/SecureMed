# ═══════════════════════════════════════════════════════════════════════════════
# SecureMed ProGuard / R8 Rules — Hardened for Healthcare App Security
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 1. Crash Trace Readability ──────────────────────────────────────────────
# Retain file and line info so Firebase Crashlytics / Logcat stack traces
# remain usable. The attribute names are obfuscated but the mapping file
# (build/outputs/mapping/) lets us retrace production crashes.
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile

# ─── 2. Aggressive Obfuscation Settings ─────────────────────────────────────
# Force R8 to obfuscate as aggressively as possible:
# • repackageclasses — flattens all class packages into a single empty package
#   so the decompiled output loses all structural information.
# • allowaccessmodification — lets R8 widen access modifiers to unlock
#   inlining / merging optimizations that aren't possible when privates stay.
# • optimizationpasses — multiple passes squeeze out more dead code.
-repackageclasses ''
-allowaccessmodification
-optimizationpasses 5

# Remove all Android logging calls in release builds to prevent information
# leakage through logcat. Log.v/d/i are stripped entirely; Log.w/e remain
# for production monitoring.
-assumenosideeffects class android.util.Log {
    public static int v(...);
    public static int d(...);
    public static int i(...);
}

# ─── 3. Retrofit ─────────────────────────────────────────────────────────────
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}

# ─── 4. OkHttp ───────────────────────────────────────────────────────────────
-dontwarn okhttp3.**
-dontwarn okio.**

# ─── 5. Kotlinx Serialization ────────────────────────────────────────────────
# The serialization plugin generates synthetic companion members that R8
# removes unless explicitly kept. @Serializable models must survive intact.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKd
-keep class kotlinx.serialization.** { *; }
-keepclassmembers class kotlinx.serialization.** {
    <init>(...);
    static <methods>;
}
# Keep @Serializable-annotated classes and their generated serializers
-keepclassmembers @kotlinx.serialization.Serializable class ** {
    *** Companion;
    *** INSTANCE;
    kotlinx.serialization.KSerializer serializer(...);
}

# ─── 6. Room ─────────────────────────────────────────────────────────────────
-keep class * extends androidx.room.RoomDatabase
-dontwarn androidx.room.paging.**

# ─── 7. SQLCipher ────────────────────────────────────────────────────────────
-keep class net.sqlcipher.** { *; }
-keep class net.sqlcipher.database.** { *; }

# ─── 8. ErrorProne annotations (Tink / crypto) ──────────────────────────────
-dontwarn com.google.errorprone.annotations.CanIgnoreReturnValue
-dontwarn com.google.errorprone.annotations.CheckReturnValue
-dontwarn com.google.errorprone.annotations.Immutable
-dontwarn com.google.errorprone.annotations.RestrictedApi

# ─── 9. Hilt / Dagger ───────────────────────────────────────────────────────
-keep class dagger.hilt.** { *; }
-keep class * extends dagger.hilt.internal.GeneratedComponent

# ─── 10. Data Models ────────────────────────────────────────────────────────
# API response and Room entity models must keep their field names for JSON
# deserialization and database column mapping.
-keep class com.securemed.app.data.model.** { *; }
-keep class com.securemed.app.data.local.room.** { *; }

# ─── 11. Security Module — Anti-Tamper Logic ────────────────────────────────
# The security classes use reflection, class-name checks, and JNI that
# break under obfuscation. We keep the class names but still let R8
# obfuscate the internal implementation.
-keep class com.securemed.app.security.TamperDetection { public *; }
-keep class com.securemed.app.security.TamperDetection$Signal { *; }
-keep class com.securemed.app.security.SecurityUtils { public *; }
-keep class com.securemed.app.security.SecurityUtils$DeviceIntegrityVerdict { *; }
-keep class com.securemed.app.security.AppIntegrityGuard { public *; }

# ─── 12. Biometric ──────────────────────────────────────────────────────────
-keep class androidx.biometric.** { *; }

# ─── 13. ML Kit Barcode Scanner ─────────────────────────────────────────────
-keep class com.google.mlkit.** { *; }
-dontwarn com.google.mlkit.**

# ─── 14. Firebase ────────────────────────────────────────────────────────────
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# ─── 15. Glance AppWidget ───────────────────────────────────────────────────
-keep class com.securemed.app.ui.widget.** { *; }

# ─── 16. Kotlin Coroutines ──────────────────────────────────────────────────
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembers class kotlinx.coroutines.** {
    volatile <fields>;
}

# ─── 17. Enum Safety ────────────────────────────────────────────────────────
-keepclassmembers enum * {
    public static **[] values();
    public static ** valueOf(java.lang.String);
}

# ─── 18. Native Methods ─────────────────────────────────────────────────────
-keepclasseswithmembernames class * {
    native <methods>;
}

# ─── 19. Parcelable ─────────────────────────────────────────────────────────
-keepclassmembers class * implements android.os.Parcelable {
    public static final ** CREATOR;
}

# ─── 20. Anti-Reverse Engineering Hardening ─────────────────────────────────
# Strip line numbers and source file names in release builds to thwart stack-tracing decompilers
-renamesourcefileattribute ""
-keepattributes !SourceFile,!LineNumberTable

# Obfuscate class and method signatures aggressively; prevent reflection abuse
-dontusemixedcaseclassnames false
-flattenpackagehierarchy ""

# Strip any residual debug / test helper calls
-assumenosideeffects class com.securemed.app.security.SecurityUtils {
    public static void logDebug(...);
}