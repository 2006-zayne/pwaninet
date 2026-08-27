# Capacitor Mobile App Shell Integration Documentation

**Version:** 1.0.0  
**Last Updated:** 2026-08-25  
**Status:** Production Ready  
**Project:** Pwaninet Django + Capacitor Android App

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Architecture Overview](#2-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Setup Instructions](#5-setup-instructions)
6. [Integration Details](#6-integration-details)
7. [Build and Deployment](#7-build-and-deployment)
8. [Current Features](#8-current-features)
9. [Development Workflow](#9-development-workflow)
10. [Troubleshooting](#10-troubleshooting)
11. [Recommendations](#11-recommendations)
12. [Future Improvements](#12-future-improvements)

---

## 1. Executive Summary

### 1.1 Purpose

This documentation covers the integration of Capacitor framework with the Pwaninet Django project to create a native Android mobile application. The integration wraps the existing Django web application in a native Android shell while maintaining full functionality of the web platform.

### 1.2 Key Benefits

- **Native Performance**: Leverages native Android WebView for improved performance
- **Offline Support**: Built-in offline fallback and network monitoring
- **Native Features**: Access to device capabilities like status bar customization
- **Single Codebase**: Maintains existing Django backend with minimal native code
- **Progressive Enhancement**: Web-first approach with native enhancements when available

### 1.3 Integration Approach

The integration uses a **hybrid architecture** where:
- Django serves as the primary backend and frontend
- Capacitor provides the native Android container
- WebView renders the web application with native enhancements
- Network monitoring handles online/offline states automatically

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Android Native Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  MainActivity.java (Capacitor Bridge)                │  │
│  │  - Network Monitoring                                │  │
│  │  - WebView Configuration                             │  │
│  │  - Offline Fallback                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Capacitor Plugins (StatusBar, SplashScreen)          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    WebView Layer                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  www/index.html (Redirect to Django Server)          │  │
│  │  www/offline.html (Offline Fallback Page)            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Django Backend                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Django Templates (base.html with Capacitor detection)│  │
│  │  Static Files (native-app.js enhancements)           │  │
│  │  REST API + WebSocket (Daphne/Channels)               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

1. **App Launch**: MainActivity loads `www/index.html`
2. **Redirect**: index.html redirects to Django server (`http://10.0.2.2:8000` for emulator)
3. **Django Rendering**: Django renders templates with Capacitor detection
4. **Native Enhancements**: `native-app.js` activates when Capacitor is detected
5. **Native Features**: Status bar, touch states, and other native features initialize
6. **Offline Handling**: Network changes trigger reload or offline page display

---

## 3. Technology Stack

### 3.1 Mobile Layer

| Component | Version | Purpose |
|-----------|---------|---------|
| **Capacitor Core** | 8.5.0 | Native bridge framework |
| **Capacitor Android** | 8.5.0 | Android native runtime |
| **Capacitor CLI** | 8.5.0 | Build and sync tools |
| **Capacitor StatusBar** | 8.0.3 | Status bar customization |
| **Android SDK** | Latest | Native Android development |
| **Gradle** | Latest | Build automation |

### 3.2 Web Layer

| Component | Version | Purpose |
|-----------|---------|---------|
| **Django** | 5.2.13 | Backend framework |
| **Daphne** | 4.2.1 | ASGI server for WebSockets |
| **Django Channels** | 4.0.0 | Real-time communication |
| **HTMX** | Latest | Dynamic frontend interactions |
| **Redis** | 5.0.1 | Channel layer and caching |

### 3.3 Development Tools

| Tool | Purpose |
|------|---------|
| **Android Studio** | Native Android development |
| **Node.js + npm** | Capacitor package management |
| **Python virtualenv** | Django environment isolation |
| **ADB** | Android debugging and deployment |

---

## 4. Project Structure

### 4.1 Capacitor-Specific Files

```
pwaninet/
├── android/                          # Android native project
│   ├── app/
│   │   ├── src/main/
│   │   │   ├── java/com/pwaninet/app/
│   │   │   │   └── MainActivity.java  # Custom bridge activity
│   │   │   ├── assets/
│   │   │   │   └── www/               # Web assets (synced)
│   │   │   └── res/                   # Android resources
│   │   ├── build.gradle               # App-level build config
│   │   └── capacitor.build.gradle     # Capacitor-specific config
│   ├── build-app.sh                   # Build automation script
│   ├── settings.gradle                # Project settings
│   └── capacitor.settings.gradle      # Capacitor Gradle integration
├── www/                              # Capacitor web directory
│   ├── index.html                     # Entry point (redirect)
│   └── offline.html                   # Offline fallback page
├── capacitor.config.json             # Capacitor configuration
├── package.json                       # Node dependencies
└── package-lock.json                  # Dependency lock file
```

### 4.2 Django Integration Files

```
pwaninet/
├── static/js/
│   └── native-app.js                  # Capacitor-specific enhancements
├── templates/
│   └── base.html                      # Base template with Capacitor detection
└── pwaninet/settings/
    └── local.py                       # Local settings with capacitor://localhost
```

---

## 5. Setup Instructions

### 5.1 Prerequisites

- **Android Studio** installed with Android SDK
- **Node.js** (v16 or higher) and npm
- **Python** 3.8+ with virtualenv
- **Java** JDK 8 or higher (for Android builds)
- **ADB** (Android Debug Bridge) for device testing

### 5.2 Initial Setup

#### 5.2.1 Install Node Dependencies

```bash
cd /home/zayne/projects/pwaninet
npm install
```

This installs:
- `@capacitor/android@^8.5.0`
- `@capacitor/cli@^8.5.0`
- `@capacitor/core@^8.5.0`
- `@capacitor/status-bar@^8.0.3`

#### 5.2.2 Initialize Capacitor (if not already done)

```bash
npx cap init
npx cap add android
```

#### 5.2.3 Configure Django Settings

Add to `pwaninet/settings/local.py`:

```python
ALLOWED_HOSTS = [
    # ... existing hosts ...
    'capacitor://localhost',  # Required for Capacitor
]
```

#### 5.2.4 Sync Web Assets

```bash
npx cap sync android
```

This copies the `www/` directory to Android assets.

### 5.3 Development Setup

#### 5.3.1 Start Django Server

```bash
cd /home/zayne/projects/pwaninet
python manage.py runserver 0.0.0.0:8000
```

#### 5.3.2 Configure Android Emulator/Device

For **Android Emulator**, the Django server is accessible at `http://10.0.2.2:8000`.

For **Physical Device**, use your machine's local IP:
```bash
# Find your local IP
ip addr show | grep inet
```

Update `www/index.html` accordingly:
```html
<script>
    window.location.href = 'http://10.0.2.2:8000'; // Emulator
    // or
    window.location.href = 'http://192.168.1.X:8000'; // Physical device
</script>
```

#### 5.3.3 Open in Android Studio

```bash
npm run cap:open
```

Or manually:
```bash
CAPACITOR_ANDROID_STUDIO_PATH=/opt/android-studio/bin/studio.sh npx cap open android
```

#### 5.3.4 Run on Device/Emulator

From Android Studio:
1. Select your device/emulator
2. Click "Run" or press Shift+F10

Or via command line:
```bash
cd android
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.pwaninet.app/.MainActivity
```

### 5.4 Production Setup

#### 5.4.1 Update Production URL

Edit `capacitor.config.json`:

```json
{
  "server": {
    "url": "https://pwaninet.app",
    "cleartext": false
  }
}
```

#### 5.4.2 Build Release APK

```bash
cd android
./gradlew assembleRelease
```

Release APK will be at: `android/app/build/outputs/apk/release/app-release.apk`

#### 5.4.3 Automated Build Script

Use the provided `build-app.sh`:

```bash
cd /home/zayne/projects/pwaninet/android
./build-app.sh
```

This script:
- Builds the debug APK
- Installs on connected device
- Launches the app automatically

---

## 6. Integration Details

### 6.1 Capacitor Configuration

**File:** `capacitor.config.json`

```json
{
  "appId": "com.pwaninet.app",
  "appName": "Pwaninet",
  "webDir": "www",
  "server": {
    "url": "https://pwaninet.app",
    "cleartext": false,
    "errorPath": "/offline.html"
  },
  "plugins": {
    "SplashScreen": {
      "launchShowDuration": 0,
      "launchAutoHide": true,
      "backgroundColor": "#0f172a",
      "androidSplashResourceName": "splash",
      "androidScaleType": "CENTER_CROP",
      "showSpinner": false,
      "splashFullScreen": true,
      "splashImmersive": true
    },
    "StatusBar": {
      "style": "DEFAULT"
    }
  }
}
```

### 6.2 Django-Capacitor Bridge

#### 6.2.1 Capacitor Detection in Templates

**File:** `templates/base.html`

```html
<script>
    // Capacitor detection
    const isNative = window.hasOwnProperty('Capacitor');
    if (isNative) {
        document.documentElement.classList.add('is-capacitor');
    }
</script>
```

```html
<script>
    // Add native app class to body
    const isNative = window.hasOwnProperty('Capacitor');
    if (isNative) {
        document.body.classList.add('is-native-app');
    }
</script>
```

#### 6.2.2 Native App Enhancements

**File:** `static/js/native-app.js`

**Status Bar Integration:**
- Automatically matches app theme (light/dark)
- Updates when theme changes
- Sets Android status bar background color to match navbar

**Touch State Enhancements:**
- Eliminates 300ms gesture delay on buttons
- Provides instant visual feedback on touch
- Uses event delegation for performance

### 6.3 Android Native Layer

#### 6.3.1 Custom MainActivity

**File:** `android/app/src/main/java/com/pwaninet/app/MainActivity.java`

**Key Features:**
- **Network Monitoring**: Automatically detects network changes
- **Auto Reload**: Reloads WebView when network becomes available
- **Offline Fallback**: Displays offline.html when network is unavailable
- **Custom WebViewClient**: Handles navigation and errors

#### 6.3.2 Gradle Configuration

**App-level build.gradle** includes:
- Capacitor Android dependencies
- Cordova plugin integration
- Google Services (optional, for push notifications)

**Settings.gradle** includes:
- Capacitor project references
- Cordova plugins project

### 6.4 Offline Handling

#### 6.4.1 Offline Page

**File:** `www/offline.html`

Custom HTML page displayed when:
- Network is unavailable
- Django server is unreachable
- Navigation errors occur

#### 6.4.2 Network Monitoring

MainActivity includes:
```java
private void setupNetworkMonitoring() {
    // Monitors network state changes
    // Triggers reload when network becomes available
    // Sets offline state when network is lost
}
```

---

## 7. Build and Deployment

### 7.1 Development Build

**Quick Build:**
```bash
cd android
./gradlew assembleDebug
```

**Build and Install:**
```bash
cd android
./build-app.sh
```

### 7.2 Production Build

**Release Build:**
```bash
cd android
./gradlew assembleRelease
```

**Signed APK:** Configure signing in `app/build.gradle`:

```gradle
android {
    signingConfigs {
        release {
            storeFile file("keystore.jks")
            storePassword "your_password"
            keyAlias "your_key_alias"
            keyPassword "your_key_password"
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }
}
```

### 7.3 Sync Process

After updating web assets:

```bash
# Sync static files to Capacitor www directory
npx cap sync android

# Or just copy files
cp -r static/* www/
cp -r templates/* www/
```

### 7.4 Deployment Workflow

1. **Update Django Code**
2. **Test Web Version**
3. **Sync to Capacitor**: `npx cap sync android`
4. **Build APK**: `./gradlew assembleDebug`
5. **Test on Device**: `adb install -r app-debug.apk`
6. **Release**: `./gradlew assembleRelease`

---

## 8. Current Features

### 8.1 Implemented Features

#### 8.1.1 Native Status Bar
- ✅ Automatic theme matching (light/dark)
- ✅ Dynamic updates on theme change
- ✅ Android background color customization
- ✅ Immersive mode support

#### 8.1.2 Touch Optimization
- ✅ Instant button touch states
- ✅ Elimination of 300ms gesture delay
- ✅ Touch cancellation handling
- ✅ Event delegation for performance

#### 8.1.3 Network Management
- ✅ Automatic network monitoring
- ✅ Offline fallback page
- ✅ Auto-reload on network recovery
- ✅ Custom error handling

#### 8.1.4 Splash Screen
- ✅ Configurable launch duration
- ✅ Custom background color
- ✅ Immersive splash mode
- ✅ Android and iOS specific settings

#### 8.1.5 Django Integration
- ✅ Capacitor detection in templates
- ✅ Conditional native enhancements
- ✅ ALLOWED_HOSTS configuration
- ✅ WebSocket support via Daphne

### 8.2 Features Available via Django

All existing Django features work in the native app:
- ✅ User authentication and profiles
- ✅ Real-time messaging (WebSockets)
- ✅ Social feed and posts
- ✅ Groups and communities
- ✅ Notifications
- ✅ File uploads and media
- ✅ PWA offline support (service workers)

---

## 9. Development Workflow

### 9.1 Typical Development Cycle

1. **Make Django Changes**
   ```bash
   # Edit Django templates, views, static files
   ```

2. **Test Web Version**
   ```bash
   python manage.py runserver
   # Test in browser at http://localhost:8000
   ```

3. **Sync to Capacitor**
   ```bash
   npx cap sync android
   ```

4. **Test in Android**
   ```bash
   # Open Android Studio
   npm run cap:open
   # Run app on emulator/device
   ```

5. **Debug Native Issues**
   ```bash
   adb logcat | grep pwaninet
   ```

### 9.2 Hot Reload Development

For faster development during native changes:

1. **Live Reload in Android Studio**
   - Enable "Instant Run" in Android Studio
   - Changes to Java code require rebuild
   - Changes to web assets require sync

2. **Web Asset Hot Reload**
   - Django dev server auto-reloads
   - Capacitor WebView reloads on network changes
   - Manual reload via MainActivity network monitoring

### 9.3 Debugging Tools

#### 9.3.1 Chrome DevTools

```bash
# Enable WebView debugging in MainActivity
# Add before super.onCreate():
if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.KITKAT) {
    WebView.setWebContentsDebuggingEnabled(true);
}
```

Then in Chrome:
```
chrome://inspect
```

#### 9.3.2 Android Logcat

```bash
# Filter for Pwaninet logs
adb logcat | grep -E "pwaninet|Capacitor|MainActivity"

# Filter for errors
adb logcat | grep -E "AndroidRuntime|pwaninet"
```

#### 9.3.3 Django Debugging

Standard Django debugging applies:
- Django Debug Toolbar
- Print statements
- Django logging

---

## 10. Troubleshooting

### 10.1 Common Issues

#### Issue: App shows "Loading Pwaninet..." indefinitely

**Cause:** Django server not accessible from device

**Solutions:**
1. Ensure Django server is running: `python manage.py runserver 0.0.0.0:8000`
2. Check firewall settings
3. For emulator: Use `http://10.0.2.2:8000`
4. For physical device: Use machine's local IP
5. Verify `www/index.html` redirect URL

#### Issue: White screen after loading

**Cause:** JavaScript errors or Capacitor plugin issues

**Solutions:**
1. Check Chrome DevTools console
2. Verify `native-app.js` is loading correctly
3. Check Capacitor plugin installation: `npx cap sync android`
4. Review logcat for errors

#### Issue: Status bar not matching theme

**Cause:** StatusBar plugin not initialized

**Solutions:**
1. Verify `@capacitor/status-bar` is installed
2. Check `native-app.js` is loading
3. Ensure theme attribute is set on `document.documentElement`
4. Check logcat for StatusBar errors

#### Issue: Offline page not showing

**Cause:** Network monitoring not working

**Solutions:**
1. Verify MainActivity network monitoring setup
2. Check `www/offline.html` exists in assets
3. Test by turning off network on device
4. Review logcat for network callback errors

#### Issue: Build fails with Gradle errors

**Cause:** Gradle version mismatch or dependency issues

**Solutions:**
1. Clean Gradle cache: `./gradlew clean`
2. Update Gradle wrapper: `./gradlew wrapper --gradle-version=8.0`
3. Check Android SDK installation
4. Verify JAVA_HOME is set correctly

#### Issue: WebSocket connections not working

**Cause:** Daphne not configured for Capacitor origins

**Solutions:**
1. Add `capacitor://localhost` to ALLOWED_HOSTS
2. Ensure Daphne is running: `daphne -b 0.0.0.0 -p 8001 pwaninet.asgi:application`
3. Check WebSocket URL configuration
4. Verify CORS settings include Capacitor origins

### 10.2 Performance Issues

#### Issue: App feels slow/laggy

**Solutions:**
1. Enable WebView hardware acceleration
2. Optimize Django templates and queries
3. Use lazy loading for images
4. Enable static file compression
5. Check for memory leaks in native code

#### Issue: High memory usage

**Solutions:**
1. Monitor WebView memory usage
2. Implement proper cleanup in MainActivity
3. Optimize image sizes
4. Limit cached data
5. Use Android Profiler to identify leaks

---

## 11. Recommendations

### 11.1 Immediate Improvements

#### 11.1.1 Add iOS Support

**Benefits:**
- Reach iOS users
- Consistent cross-platform experience

**Implementation:**
```bash
npx cap add ios
npx cap sync ios
npm run cap:open ios
```

#### 11.1.2 Implement App Icons and Splash Screens

**Current Status:** Basic configuration

**Recommendation:**
- Create professional app icons (multiple sizes)
- Design branded splash screens
- Use Capacitor Assets CLI: `@capacitor/assets`

#### 11.1.3 Add Push Notifications

**Benefits:**
- Real-time user engagement
- Important alerts and updates

**Implementation:**
```bash
npm install @capacitor/push-notifications
npx cap sync android
```

Requires Firebase Cloud Messaging setup.

#### 11.1.4 Implement Deep Linking

**Benefits:**
- Share links that open directly in app
- Better user experience from external sources

**Implementation:**
```bash
npm install @capacitor/app-launcher
```

Configure Android intent filters in `AndroidManifest.xml`.

### 11.2 Code Quality Improvements

#### 11.2.1 Error Handling

**Current:** Basic error handling in MainActivity

**Recommendation:**
- Add comprehensive error logging
- Implement graceful degradation
- Add user-friendly error messages
- Track errors in analytics

#### 11.2.2 Testing

**Current:** No automated tests for native layer

**Recommendation:**
- Add Android unit tests
- Implement Espresso UI tests
- Add integration tests for Capacitor plugins
- Test offline scenarios

#### 11.2.3 Configuration Management

**Current:** Hardcoded URLs in `www/index.html`

**Recommendation:**
- Use environment-based configuration
- Create build variants (dev/staging/prod)
- Implement configuration via Capacitor config
- Add API endpoint for dynamic configuration

### 11.3 Security Improvements

#### 11.3.1 Certificate Pinning

**Benefits:**
- Prevent man-in-the-middle attacks
- Ensure secure communication

**Implementation:**
- Implement SSL certificate pinning in MainActivity
- Use Network Security Configuration

#### 11.3.2 App Security

**Recommendations:**
- Enable code obfuscation (ProGuard/R8)
- Implement app integrity checks
- Add tamper detection
- Secure sensitive data in storage

#### 11.3.3 Authentication

**Current:** Uses Django authentication

**Recommendation:**
- Implement biometric authentication (fingerprint/face)
- Add secure token storage
- Implement session timeout
- Add logout on app background

### 11.4 Performance Optimizations

#### 11.4.1 WebView Performance

**Recommendations:**
- Enable hardware acceleration
- Implement WebView caching strategy
- Optimize JavaScript execution
- Use lazy loading for heavy components

#### 11.4.2 Build Optimization

**Recommendations:**
- Enable App Bundle for Play Store
- Implement APK splitting
- Optimize resource compression
- Use shrink resources in release builds

#### 11.4.3 Network Optimization

**Recommendations:**
- Implement request caching
- Add offline data synchronization
- Optimize image loading and compression
- Implement CDN for static assets

---

## 12. Future Improvements

### 12.1 Advanced Native Features

#### 12.1.1 Camera and Gallery Integration

**Use Cases:**
- Profile picture uploads
- Post image attachments
- Document scanning

**Implementation:**
```bash
npm install @capacitor/camera
npm install @capacitor/filesystem
```

#### 12.1.2 Geolocation Services

**Use Cases:**
- Location-based posts
- Nearby users discovery
- Campus features

**Implementation:**
```bash
npm install @capacitor/geolocation
```

#### 12.1.3 Local Notifications

**Use Cases:**
- In-app reminders
- Background task alerts
- Local event notifications

**Implementation:**
```bash
npm install @capacitor/local-notifications
```

#### 12.1.4 Background Tasks

**Use Cases:**
- Sync data in background
- Update notifications
- Refresh content periodically

**Implementation:**
```bash
npm install @capacitor/background-task
npm install @capacitor/app
```

### 12.2 Enhanced Offline Support

#### 12.2.1 Offline Data Synchronization

**Current:** Basic offline page

**Future:**
- Implement offline queue for actions
- Sync when connection restored
- Conflict resolution for concurrent edits
- Offline-first data architecture

#### 12.2.2 Service Worker Integration

**Current:** Django PWA has service worker

**Future:**
- Enhance service worker for native app
- Implement background sync
- Cache API responses
- Offline data storage (IndexedDB)

### 12.3 Analytics and Monitoring

#### 12.3.1 Crash Reporting

**Implementation:**
- Integrate Firebase Crashlytics
- Add Sentry for JavaScript errors
- Implement custom error tracking
- User feedback on crashes

#### 12.3.2 Usage Analytics

**Implementation:**
- Track feature usage
- Monitor performance metrics
- User engagement analytics
- A/B testing framework

#### 12.3.3 Performance Monitoring

**Implementation:**
- Real-time performance tracking
- WebView performance metrics
- Network request monitoring
- Memory usage tracking

### 12.4 User Experience Enhancements

#### 12.4.1 Native UI Components

**Potential:**
- Native bottom navigation
- Native modal dialogs
- Native pull-to-refresh
- Native share sheet

#### 12.4.2 Gesture Support

**Potential:**
- Swipe gestures for navigation
- Pinch-to-zoom for images
- Long-press actions
- Custom gesture recognizers

#### 12.4.3 Accessibility

**Improvements:**
- Screen reader support
- High contrast mode
- Font scaling support
- Voice control integration

### 12.5 Distribution and Updates

#### 12.5.1 App Store Distribution

**Implementation:**
- Google Play Store listing
- App signing and publishing
- Version management
- Release notes automation

#### 12.5.2 In-App Updates

**Implementation:**
```bash
npm install @capacitor/app-update
```

- Check for updates on app launch
- Prompt users for updates
- Force critical updates
- Background update downloads

#### 12.5.3 Beta Testing

**Implementation:**
- Google Play Internal Test
- Firebase App Distribution
- Crashlytics beta testing
- TestFlight for iOS

### 12.6 Development Tooling

#### 12.6.1 CI/CD Pipeline

**Implementation:**
- Automated builds on push
- Automated testing
- Automated deployment to beta
- Release automation

#### 12.6.2 Development Environment

**Improvements:**
- Docker container for consistency
- Hot reload for native code
- Development mode configuration
- Debug builds with logging

#### 12.6.3 Documentation

**Maintenance:**
- Keep this documentation updated
- Add API documentation
- Create troubleshooting guides
- Document common patterns

---

## 13. Quick Reference

### 13.1 Essential Commands

```bash
# Capacitor operations
npx cap sync android              # Sync web assets to native
npx cap open android               # Open in Android Studio
npm run cap:open                   # Open with custom path

# Android build
cd android
./gradlew assembleDebug            # Build debug APK
./gradlew assembleRelease          # Build release APK
./gradlew clean                    # Clean build

# Device operations
adb devices                        # List connected devices
adb install -r app-debug.apk       # Install APK
adb shell am start -n com.pwaninet.app/.MainActivity  # Launch app
adb logcat                          # View logs
adb logcat -c                      # Clear logs

# Django operations
python manage.py runserver 0.0.0.0:8000    # Start dev server
python manage.py collectstatic            # Collect static files
daphne -b 0.0.0.0 -p 8001 pwaninet.asgi:application  # Start ASGI server
```

### 13.2 Configuration Files

| File | Purpose |
|------|---------|
| `capacitor.config.json` | Main Capacitor configuration |
| `package.json` | Node dependencies and scripts |
| `android/app/build.gradle` | Android app build configuration |
| `android/settings.gradle` | Android project settings |
| `www/index.html` | App entry point (redirect) |
| `www/offline.html` | Offline fallback page |
| `static/js/native-app.js` | Native enhancements |
| `pwaninet/settings/local.py` | Django local settings |

### 13.3 Key URLs

| Environment | URL |
|-------------|-----|
| Development (Emulator) | `http://10.0.2.2:8000` |
| Development (Device) | `http://YOUR_LOCAL_IP:8000` |
| Production | `https://pwaninet.app` |
| Capacitor Local | `capacitor://localhost` |

### 13.4 Version Information

- **Capacitor:** 8.5.0
- **Django:** 5.2.13
- **Android Target SDK:** Latest
- **Minimum SDK:** Configured in `android/app/build.gradle`

---

## 14. Support and Resources

### 14.1 Official Documentation

- [Capacitor Documentation](https://capacitorjs.com/docs)
- [Capacitor Android Guide](https://capacitorjs.com/docs/android)
- [Django Documentation](https://docs.djangoproject.com/)
- [Android Developer Guide](https://developer.android.com/guide)

### 14.2 Community Resources

- [Capacitor Community Forum](https://forum.capacitorjs.com/)
- [Stack Overflow - Capacitor](https://stackoverflow.com/questions/tagged/capacitor)
- [Django Users Forum](https://groups.google.com/g/django-users)

### 14.3 Project-Specific Resources

- System Architecture: `PWANINET_SYSTEM_ARCHITECTURE.md`
- Backend Architecture: `BACKEND_ARCHITECTURE.md`
- Project Documentation: `DOCUMENTATION.md`

---

## 15. Changelog

### Version 1.0.0 (2026-08-25)
- Initial Capacitor integration
- Android native shell implementation
- Network monitoring and offline support
- Status bar integration
- Touch optimization
- Django-Capacitor bridge
- Basic documentation

---

## 16. Contributing

When making changes to the Capacitor integration:

1. Update this documentation accordingly
2. Test on both emulator and physical device
3. Test offline scenarios
4. Verify Django functionality remains intact
5. Document any new features or breaking changes

---

## 17. License

This integration follows the same license as the Pwaninet project.

---

**Document End**

For questions or issues related to this Capacitor integration, refer to the troubleshooting section or consult the official Capacitor documentation.
