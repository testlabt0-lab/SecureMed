#!/bin/bash
# =====================================================
# SecureMed APK Build Script
# =====================================================
# Builds the Android APK for SecureMed.
#
# Requirements:
#   - Java 17+ (JDK)
#   - Android SDK (platform-tools, platforms;android-34, build-tools;34.0.0)
#   - Gradle 8.8+ (or use the included gradlew wrapper)
#
# Usage:
#   ./build_apk.sh                          # Build debug APK (emulator URL)
#   ./build_apk.sh release                  # Build release APK (emulator URL)
#   ./build_apk.sh release https://my-server.onrender.com/api/v1/
#                                           # Build release APK pointing at
#                                           # the production backend
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   SecureMed APK Builder                           ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"

BUILD_TYPE="${1:-debug}"
# Optional 2nd argument: the deployed backend base URL (must end with /api/v1/).
# Passed to Gradle as -PAPI_BASE_URL=... (see android/app/build.gradle.kts).
API_URL="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ANDROID_DIR="$PROJECT_DIR/android"

# Check prerequisites
echo -e "\n${YELLOW}[1/5] Checking prerequisites...${NC}"

check() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1 found"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 NOT found"
        return 1
    fi
}

if ! check java; then
    echo -e "\n${RED}❌ Java is required. Install with:${NC}"
    echo -e "   sudo apt install default-jdk"
    exit 1
fi

# Set up Android SDK
export ANDROID_HOME=${ANDROID_HOME:-$HOME/Android/Sdk}
export ANDROID_SDK_ROOT=$ANDROID_HOME
export PATH=$PATH:$ANDROID_HOME/platform-tools:$ANDROID_HOME/cmdline-tools/latest/bin

if [ ! -d "$ANDROID_HOME" ]; then
    echo -e "\n${YELLOW}⚠ Android SDK not found at $ANDROID_HOME${NC}"
    echo -e "  Install Android Studio or command-line tools:"
    echo -e "  https://developer.android.com/studio#command-line-tools-only"
    echo -e ""
    echo -e "  Then run:"
    echo -e "  sdkmanager \"platform-tools\" \"platforms;android-34\" \"build-tools;34.0.0\""
    exit 1
fi

echo -e "  ${GREEN}✓${NC} Android SDK: $ANDROID_HOME"

# Create local.properties
echo -e "\n${YELLOW}[2/5] Creating local.properties...${NC}"
echo "sdk.dir=$ANDROID_HOME" > "$ANDROID_DIR/local.properties"
echo -e "  ${GREEN}✓${NC} local.properties created"

# Ensure Gradle wrapper exists
echo -e "\n${YELLOW}[3/5] Setting up Gradle wrapper...${NC}"

if [ ! -f "$ANDROID_DIR/gradlew" ]; then
    echo -e "  ${YELLOW}⚠${NC} gradlew not found, generating..."
    if command -v gradle &> /dev/null; then
        cd "$ANDROID_DIR"
        gradle wrapper --gradle-version 8.8
    else
        echo -e "  ${RED}✗${NC} Gradle not installed"
        echo -e "  Install with: sudo apt install gradle"
        echo -e "  Or download from: https://gradle.org/install/"
        exit 1
    fi
fi
echo -e "  ${GREEN}✓${NC} Gradle wrapper ready"

# Build APK
echo -e "\n${YELLOW}[4/5] Building $BUILD_TYPE APK...${NC}"
cd "$ANDROID_DIR"
chmod +x gradlew

if [ "$BUILD_TYPE" = "release" ]; then
    if [ -n "$API_URL" ]; then
        ./gradlew assembleRelease --no-daemon -PAPI_BASE_URL="$API_URL"
    else
        ./gradlew assembleRelease --no-daemon
    fi
    APK_PATH="app/build/outputs/apk/release/app-release.apk"
else
    if [ -n "$API_URL" ]; then
        ./gradlew assembleDebug --no-daemon -PAPI_BASE_URL="$API_URL"
    else
        ./gradlew assembleDebug --no-daemon
    fi
    APK_PATH="app/build/outputs/apk/debug/app-debug.apk"
fi

# Verify APK
echo -e "\n${YELLOW}[5/5] Verifying APK...${NC}"
if [ -f "$APK_PATH" ]; then
    APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
    echo -e "  ${GREEN}✓${NC} APK built successfully!"
    if [ -n "$API_URL" ]; then
        echo -e "  ${GREEN}✓${NC} Backend: $API_URL"
    else
        echo -e "  ${YELLOW}ℹ${NC} Backend: http://10.0.2.2:8000/api/v1/ (emulator default)"
    fi
    echo -e "  ${GREEN}✓${NC} Path: $ANDROID_DIR/$APK_PATH"
    echo -e "  ${GREEN}✓${NC} Size: $APK_SIZE"
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   APK Build Complete! ✅                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Install on device/emulator:"
    echo -e "  adb install $APK_PATH"
else
    echo -e "  ${RED}✗${NC} APK build failed"
    exit 1
fi
