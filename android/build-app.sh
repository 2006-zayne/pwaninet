#!/bin/bash
set -e

# Sync capacitor assets and plugins from root project directory
cd /home/zayne/projects/pwaninet
npx cap sync android

# Build and deploy Android app
cd /home/zayne/projects/pwaninet/android
unset ANDROID_PREFS_ROOT && \
VERSION_CODE=100 VERSION_NAME=1.4.1 JAVA_HOME=/opt/android-studio/jbr ./gradlew assembleDebug --no-daemon && \
~/Android/Sdk/platform-tools/adb uninstall com.pwaninet.app || true && \
~/Android/Sdk/platform-tools/adb install -r app/build/outputs/apk/debug/app-debug.apk && \
~/Android/Sdk/platform-tools/adb shell am start -n com.pwaninet.app/.MainActivity