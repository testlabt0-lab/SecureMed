// Module-level build file
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.devtools.ksp")
    id("com.google.dagger.hilt.android")
    id("io.gitlab.arturbosch.detekt")
    id("com.github.ben-manes.versions")
}

detekt {
    config.setFrom(files("$rootDir/detekt.yml"))
    // Generated code is out of scope; the rest is the whole Kotlin tree.
    buildUponDefaultConfig = true
    parallel = true
    // Pre-existing findings are frozen in the baseline: they neither fail
    // the pipeline nor grow — any NEW finding of the same rule fails the tag.
    baseline = file("$rootDir/detekt-baseline.xml")
}

// detekt's embedded compiler inherits the running JVM's target unless pinned.
// A dev machine on JDK 24 would hand it --jvm-target 24 (unsupported in
// detekt 1.23.x); pinning to 17 matches the Kotlin build target everywhere.
tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
    jvmTarget = "17"
}
tasks.withType<io.gitlab.arturbosch.detekt.DetektCreateBaselineTask>().configureEach {
    jvmTarget = "17"
}

// FCM push is opt-in so the build never depends on a secret: drop a real
// google-services.json into android/app/ (and optionally build with
// -PSECUREMED_FCM=true) to activate. The firebase-messaging *dependency* is
// always present — it is inert without the config — so the code compiles and
// degrades to in-app notifications when push is not provisioned.
if (project.findProperty("SECUREMED_FCM") == "true") {
    apply(plugin = "com.google.gms.google-services")
}

    android {
    namespace = "com.securemed.app"
    compileSdk = 35

    // Backend URL — override at build time:
    //   ./gradlew assembleRelease -PAPI_BASE_URL=https://host/api/v1/
    // Without an override, debug goes to the emulator loopback (10.0.2.2 = the
    // dev machine) and release goes to production over TLS. A release build
    // must not inherit the loopback default: it is cleartext, 10.0.2.2 is the
    // one host network_security_config still permits in the clear, and the
    // OkHttp pinner reads its host from this URL — an http base URL therefore
    // disables pinning as well.
    val apiBaseUrlOverride = project.findProperty("API_BASE_URL") as String?
    val debugApiBaseUrl = apiBaseUrlOverride ?: "http://10.0.2.2:8000/api/v1/"
    val releaseApiBaseUrl = apiBaseUrlOverride ?: "https://securemed-production.onrender.com/api/v1/"

    // Release signing material stays out of the repository — read from
    // ~/.gradle/gradle.properties or from the CI environment:
    //   SECUREMED_KEYSTORE_FILE (absolute, or relative to the android/ root)
    //   SECUREMED_KEYSTORE_PASSWORD, SECUREMED_KEY_ALIAS, SECUREMED_KEY_PASSWORD
    fun signingValue(name: String): String? =
        (project.findProperty(name) as String?) ?: System.getenv(name)

    val releaseKeystore = signingValue("SECUREMED_KEYSTORE_FILE")
        ?.let { rootProject.file(it) }
        ?.takeIf { it.isFile }

    // An unsigned release APK fails at install time, far from the cause. Say so
    // while the build is still running, and only for release tasks so debug
    // builds stay quiet. A wrong or missing path lands here identically —
    // takeIf { it.isFile } above rejects both.
    if (releaseKeystore == null &&
        gradle.startParameter.taskNames.any { it.contains("release", ignoreCase = true) }
    ) {
        logger.warn(
            "SECUREMED_KEYSTORE_FILE is not set to an existing file — the release " +
                "build will be UNSIGNED and cannot be installed or uploaded. Set " +
                "SECUREMED_KEYSTORE_FILE / _PASSWORD, SECUREMED_KEY_ALIAS / _PASSWORD " +
                "in ~/.gradle/gradle.properties or the CI environment."
        )
    }

    defaultConfig {
        applicationId = "com.securemed.app"
        minSdk = 26
        targetSdk = 35
        // Release numbering is tag-derived (4-2): CI passes -PSECUREMED_VERSION_NAME
        // and -PSECUREMED_VERSION_CODE cut from the pushed tag (v1.4.2 → 10402),
        // so a tag alone produces an uploadable build. Local builds keep the
        // floor values below.
        val versionNameOverride = project.findProperty("SECUREMED_VERSION_NAME") as String?
        val versionCodeOverride = (project.findProperty("SECUREMED_VERSION_CODE") as String?)?.toIntOrNull()
        versionCode = versionCodeOverride ?: 1
        versionName = versionNameOverride ?: "1.0.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        vectorDrawables { useSupportLibrary = true }
    }

    signingConfigs {
        if (releaseKeystore != null) {
            create("release") {
                storeFile = releaseKeystore
                storePassword = signingValue("SECUREMED_KEYSTORE_PASSWORD")
                keyAlias = signingValue("SECUREMED_KEY_ALIAS")
                keyPassword = signingValue("SECUREMED_KEY_PASSWORD")
                // minSdk is 26, so the v1 JAR signature is dead weight and
                // only widens what an attacker can tamper with; v2+v3 cover
                // every supported device.
                enableV1Signing = false
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "API_BASE_URL", "\"$releaseApiBaseUrl\"")
            // Signed only when real key material was supplied; otherwise the
            // build produces an unsigned APK/AAB, which is a loud failure at
            // install time instead of a quiet one.
            //
            // This used to be signingConfigs["debug"], whose key ships inside
            // the Android SDK and is identical on every machine: anyone can
            // strip and re-sign such a build, Play rejects it, and the
            // fallback hid the fact that no release key was ever configured.
            signingConfig = signingConfigs.findByName("release")
        }
        debug {
            isDebuggable = true
            buildConfigField("String", "API_BASE_URL", "\"$debugApiBaseUrl\"")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.14"
    }
    packaging {
        resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" }
    }
}

dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.material3:material3-window-size-class")
    implementation("androidx.navigation:navigation-compose:2.8.0")
    implementation("androidx.compose.animation:animation")

    // Core
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.2")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.2")
    // Compose UI 1.7 deprecated its own LocalLifecycleOwner in favour of the
    // one here. Declared explicitly rather than relied on transitively through
    // compose-ui, so the import cannot break on a BOM bump.
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.2")
    implementation("androidx.activity:activity-compose:1.9.0")

    // Hilt — Dependency Injection
    implementation("com.google.dagger:hilt-android:2.51.1")
    ksp("com.google.dagger:hilt-android-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    
    // WorkManager — Offline Sync
    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("androidx.hilt:hilt-work:1.2.0")
    ksp("androidx.hilt:hilt-compiler:1.2.0")

    // Room — Local Database
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    implementation("net.zetetic:android-database-sqlcipher:4.5.4")
    implementation("androidx.sqlite:sqlite-ktx:2.4.0")

    // Biometric
    implementation("androidx.biometric:biometric:1.1.0")

    // FCM push — inert without google-services.json + SECUREMED_FCM=true;
    // SecureMedPushService registers only when Firebase initializes.
    implementation("com.google.firebase:firebase-messaging:24.0.0")

    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-kotlinx-serialization:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")

    // DataStore (for secure token storage)
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    // await() over Play-services Tasks (FirebaseMessaging.token)
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.8.1")

    // Image Loading
    implementation("io.coil-kt:coil-compose:2.6.0")

    // Paging 3
    implementation("androidx.paging:paging-runtime:3.3.0")
    implementation("androidx.paging:paging-compose:3.3.0")

    // Splash Screen
    implementation("androidx.core:core-splashscreen:1.0.1")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("io.mockk:mockk:1.13.11")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("app.cash.turbine:turbine:1.1.0")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.09.00"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    androidTestImplementation("com.google.dagger:hilt-android-testing:2.51.1")
    kspAndroidTest("com.google.dagger:hilt-android-compiler:2.51.1")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
