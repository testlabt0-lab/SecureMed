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
    // Static analysis for the release pipeline (4-2). The config file leans
    // on the project's own conventions — only the rules that actually bit
    // this codebase are deviated from.
    id("io.gitlab.arturbosch.detekt") version "1.23.6" apply false
    // `./gradlew dependencyUpdates` — the lightweight outdated report the
    // release pipeline runs. The heavyweight NVD-backed scanners need
    // hundreds of MB of advisory data per run; this one names what is stale
    // so a human decides before a tag.
    id("com.github.ben-manes.versions") version "0.51.0" apply false
}
