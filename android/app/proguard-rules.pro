# Add project specific ProGuard rules here.
# You can control the set of applied configuration files using the
# proguardFiles setting in build.gradle.

# Retrofit
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}

# Kotlinx Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKd
-keep,allowdictionarywarnings class kotlinx.serialization.** { *; }
-keepclassmembers class kotlinx.serialization.** {
    <init>(...);
    static <methods>;
}

# Room
-keep class * extends androidx.room.RoomDatabase
-dontwarn androidx.room.paging.**

# SQLCipher
-keep class net.sqlcipher.** { *; }
-keep class net.sqlcipher.database.** { *; }

# Hilt / Dagger
-keep class dagger.hilt.** { *; }
-keep class * extends dagger.hilt.internal.GeneratedComponent

# Keep data models
-keep class com.securemed.app.data.model.** { *; }
-keep class com.securemed.app.data.local.room.** { *; }