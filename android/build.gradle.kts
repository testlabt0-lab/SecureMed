// Top-level build file
plugins {
    id("com.android.application") version "8.6.1" apply false
    id("org.jetbrains.kotlin.android") version "1.9.24" apply false
    id("org.jetbrains.kotlin.plugin.serialization") version "1.9.24" apply false
    id("com.google.devtools.ksp") version "1.9.24-1.0.20" apply false
    id("com.google.dagger.hilt.android") version "2.51.1" apply false
    // Applied conditionally in the app module: FCM needs google-services.json
    // at configuration time, and this repository deliberately does not carry
    // one (secrets out of git). See android/app/README-FCM.md.
    id("com.google.gms.google-services") version "4.4.2" apply false
}
