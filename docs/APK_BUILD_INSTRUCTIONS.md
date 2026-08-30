# 📱 SecureMed Android APK - Build Instructions

This document explains how to build the SecureMed Android APK.

## ⚠️ Note on Pre-built APK

The APK cannot be pre-built in this environment due to:
- Android SDK needs to download ~2GB of dependencies (Gradle, Kotlin compiler, AndroidX libraries)
- Build takes 5-10 minutes on first run
- Requires internet connection to Maven Central and Google Maven

However, the **complete source code is ready** and the APK can be built easily on your machine.

## 🚀 Quick Build (Recommended)

### Option 1: Using Android Studio (Easiest)

1. Install [Android Studio](https://developer.android.com/studio)
2. Open the `android/` folder in Android Studio
3. Wait for Gradle sync to complete
4. Click **Build → Build Bundle(s) / APK(s) → Build APK(s)**
5. APK will be at: `android/app/build/outputs/apk/debug/app-debug.apk`

### Option 2: Using Command Line

#### Prerequisites
- Java JDK 17+
- Android SDK (API 34 + Build Tools 34.0.0)

#### Steps

```bash
cd securemed/android

# Set Android SDK location
export ANDROID_HOME=$HOME/Android/Sdk  # Adjust as needed

# Create local.properties
echo "sdk.dir=$ANDROID_HOME" > local.properties

# Make gradlew executable
chmod +x gradlew

# Build debug APK
./gradlew assembleDebug

# Or build release APK
./gradlew assembleRelease
```

#### Output
- Debug APK: `app/build/outputs/apk/debug/app-debug.apk`
- Release APK: `app/build/outputs/apk/release/app-release.apk`

### Option 3: Using the Build Script

```bash
cd securemed
./build_apk.sh           # Debug APK
./build_apk.sh release    # Release APK
```

## 📲 Installing the APK

### On a Physical Device

1. Enable **Developer Options** (tap Build Number 7 times in Settings)
2. Enable **USB Debugging** in Developer Options
3. Connect device via USB
4. Run:
   ```bash
   adb install android/app/build/outputs/apk/debug/app-debug.apk
   ```

### On an Emulator

1. Open Android Studio → AVD Manager
2. Create a Pixel 7 (or similar) emulator with API 34+
3. Start the emulator
4. Run:
   ```bash
   adb install android/app/build/outputs/apk/debug/app-debug.apk
   ```

## 🔧 Troubleshooting

### "SDK location not found"
- Ensure `local.properties` contains: `sdk.dir=/path/to/Android/Sdk`

### "Failed to resolve: androidx..."
- Ensure you have internet connection
- Run: `./gradlew --refresh-dependencies assembleDebug`

### "Minimum SDK version requires..."
- Use a device/emulator with Android 8.0 (API 26) or higher

### Build is very slow
- First build downloads ~500MB of dependencies
- Subsequent builds use cached dependencies (much faster)

## 📋 APK Information

| Property | Value |
|----------|-------|
| Application ID | `com.securemed.app` |
| Min SDK | 26 (Android 8.0) |
| Target SDK | 34 (Android 14) |
| Version Code | 1 |
| Version Name | 1.0.0 |
| Permissions | INTERNET, USE_BIOMETRIC, USE_FINGERPRINT |

## 🔐 Security Features in APK

- ✅ Biometric authentication (fingerprint)
- ✅ EncryptedSharedPreferences (AES-256)
- ✅ Network security config (HTTPS only in production)
- ✅ ProGuard/R8 code obfuscation (release builds)
- ✅ No backup of sensitive data (allowBackup=false)

## 🎯 Testing the App

1. Start the Django backend server (see main README.md)
2. Update `API_BASE_URL` in `app/build.gradle.kts` to point to your server
3. For emulator testing: use `http://10.0.2.2:8000/api/v1/` (maps to host localhost)
4. For physical device: use your computer's IP address

## 📞 Support

If you encounter build issues:
1. Check the [Android Studio docs](https://developer.android.com/studio/build)
2. Ensure all prerequisites are installed
3. Try `./gradlew clean build` to start fresh
