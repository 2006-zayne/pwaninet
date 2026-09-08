/**
 * Native App Enhancements - Capacitor-specific functionality
 * Only active when running in Capacitor native environment
 */

(function() {
    window._pwaninet_native_load_time = performance.now();
    console.log('[PWANINET-NATIVE] Script load time:', window._pwaninet_native_load_time.toFixed(2) + 'ms');

    function initEarly() {
        var isNative = typeof window.Capacitor !== 'undefined' ||
                       window.hasOwnProperty('Capacitor') ||
                       document.documentElement.classList.contains('is-capacitor') ||
                       document.documentElement.classList.contains('is-native-app');
        if (!isNative || window._pwaninet_native_ui_initialized) return;

        document.documentElement.classList.add('is-capacitor', 'is-native-app');
        if (document.body) document.body.classList.add('is-capacitor', 'is-native-app');

        var earlyInitStart = performance.now();
        console.log('[PWANINET-NATIVE] Early UI initialization started at:', earlyInitStart.toFixed(2) + 'ms');

        // 1. Configure Status Bar immediately for edge-to-edge
        initStatusBarEarly();

        // 2. Initialize Safe Area listeners and CSS variables (insets only, no system bar config)
        initSafeAreaEarly();

        // 3. Configure Navigation Bar immediately for current theme
        var initialTheme = document.documentElement.getAttribute('data-theme') || 'light';
        updateNavigationBarForTheme(initialTheme);

        window._pwaninet_native_ui_initialized = true;
        var earlyInitEnd = performance.now();
        console.log('[PWANINET-NATIVE] Early UI initialization complete in:', (earlyInitEnd - earlyInitStart).toFixed(2) + 'ms');
    }

    // If Capacitor or AndroidBridge is already here, init immediately
    if ((window.Capacitor && window.Capacitor.Plugins) || window.AndroidBridge || window.PwaninetBridge) {
        initEarly();
    } else {
        // Fallback: wait a few frames if we're in a native environment but bridge is lagging
        var attempts = 0;
        var checkBridge = setInterval(function() {
            attempts++;
            if ((window.Capacitor && window.Capacitor.Plugins) || window.AndroidBridge || window.PwaninetBridge || attempts > 20) {
                clearInterval(checkBridge);
                if ((window.Capacitor && window.Capacitor.Plugins) || window.AndroidBridge || window.PwaninetBridge) initEarly();
            }
        }, 16);
    }
})();

/**
 * Initialize Status Bar as early as possible
 */
async function initStatusBarEarly() {
    var startTime = performance.now();
    try {
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        const isLight = theme === 'light';

        // Notify AndroidBridge directly for instantaneous update
        var bridge = window.AndroidBridge || window.PwaninetBridge;
        if (bridge && typeof bridge.setSystemBarTheme === 'function') {
            bridge.setSystemBarTheme(isLight ? 'light' : 'dark');
        }

        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.StatusBar) return;

        const { StatusBar } = window.Capacitor.Plugins;

        // Initial setup for edge-to-edge transparency
        await StatusBar.setOverlaysWebView({ overlay: true });
        await StatusBar.setBackgroundColor({ color: '#00000000' });

        // Initial theme style
        await StatusBar.setStyle({ style: isLight ? 'LIGHT' : 'DARK' });

        var endTime = performance.now();
        console.log('[PWANINET-NATIVE] StatusBar early init complete in:', (endTime - startTime).toFixed(2) + 'ms');
    } catch (e) {
        console.error('[PWANINET-NATIVE] Early StatusBar init failed', e);
    }
}

/**
 * Initialize Safe Area and inject CSS variables
 * Handles both native bridge events and plugin-based inset information
 */
async function initSafeAreaEarly() {
    var startTime = performance.now();
    try {
        // Function to update CSS variables from insets
        const updateInsets = (insets) => {
            if (!insets) return;
            console.log('[PWANINET-NATIVE] Safe Area Insets Update:', JSON.stringify(insets));
            const root = document.documentElement;
            root.classList.add('is-capacitor', 'is-native-app');
            root.style.setProperty('--pwaninet-safe-area-top', insets.top + 'px');
            root.style.setProperty('--pwaninet-safe-area-bottom', insets.bottom + 'px');
            root.style.setProperty('--pwaninet-safe-area-left', insets.left + 'px');
            root.style.setProperty('--pwaninet-safe-area-right', insets.right + 'px');

            if (document.body) {
                document.body.classList.add('is-capacitor', 'is-native-app');
                document.body.style.setProperty('--pwaninet-safe-area-top', insets.top + 'px');
                document.body.style.setProperty('--pwaninet-safe-area-bottom', insets.bottom + 'px');
            }

            console.log('[PWANINET-NATIVE] Applied CSS Variables:', {
                '--pwaninet-safe-area-top': root.style.getPropertyValue('--pwaninet-safe-area-top'),
                '--pwaninet-safe-area-bottom': root.style.getPropertyValue('--pwaninet-safe-area-bottom')
            });
        };

        // Listen for native Android bridge safe area events from MainActivity
        window.addEventListener('pwaninet:safe-area-changed', function(event) {
            if (event.detail) {
                updateInsets(event.detail);
            }
        });

        // Safe plugin feature-detection (for plugins that provide getSafeAreaInsets)
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.SafeArea) {
            const { SafeArea } = window.Capacitor.Plugins;

            if (typeof SafeArea.getSafeAreaInsets === 'function') {
                try {
                    const result = await SafeArea.getSafeAreaInsets();
                    if (result && result.insets) {
                        updateInsets(result.insets);
                    }
                } catch (err) {
                    console.warn('[PWANINET-NATIVE] SafeArea.getSafeAreaInsets call failed:', err);
                }
            }

            if (typeof SafeArea.addListener === 'function') {
                try {
                    SafeArea.addListener('safeAreaChanged', (data) => {
                        if (data && data.insets) {
                            updateInsets(data.insets);
                        }
                    });
                } catch (err) {
                    console.warn('[PWANINET-NATIVE] SafeArea.addListener failed:', err);
                }
            }
        }

        var endTime = performance.now();
        console.log('[PWANINET-NATIVE] SafeArea early init complete in:', (endTime - startTime).toFixed(2) + 'ms');
    } catch (e) {
        console.error('[PWANINET-NATIVE] Early SafeArea init failed', e);
    }
}

// Initialize native app enhancements
function initNativeAppEnhancements() {
    const startTime = performance.now();
    const isNative = typeof window.Capacitor !== 'undefined' ||
                     window.hasOwnProperty('Capacitor') ||
                     document.documentElement.classList.contains('is-capacitor') ||
                     document.documentElement.classList.contains('is-native-app');

    if (!isNative) return;

    document.documentElement.classList.add('is-capacitor', 'is-native-app');
    if (document.body) document.body.classList.add('is-capacitor', 'is-native-app');

    // Prevent duplicate initialization during HTMX swaps
    if (window._pwaninet_native_initialized) return;

    console.log('[PWANINET-NATIVE] DOM-dependent initialization started at:', startTime.toFixed(2) + 'ms');

    // Initialize instant button touch states
    initInstantTouchStates();

    // Initialize caching
    initCaching();

    // Initialize back button handling
    initBackNavigation();

    // Initialize native media handling
    initNativeMedia();

    // Initialize theme synchronization
    initThemeSync();

    // Initialize native app update checks
    initNativeAppUpdates();

    window._pwaninet_native_initialized = true;

    const endTime = performance.now();
    console.log('[PWANINET-NATIVE] Native initialization fully complete in:', (endTime - startTime).toFixed(2) + 'ms');
    console.log('[PWANINET-NATIVE] Total time from script load:', (endTime - window._pwaninet_native_load_time).toFixed(2) + 'ms');
}

/**
 * Instant button touch states - eliminates 300ms gesture delay
 */
function initInstantTouchStates() {
    const clickableSelectors = ['.btn', '.btn-native', 'button'];
    
    document.addEventListener('touchstart', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) target.classList.add('activated');
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) target.classList.remove('activated');
    }, { passive: true });

    document.addEventListener('touchcancel', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) target.classList.remove('activated');
    }, { passive: true });
}

/**
 * Sync status bar and navigation bar with current theme
 */
function initThemeSync() {
    // Setup observer for future theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                const newTheme = document.documentElement.getAttribute('data-theme') || 'light';
                updateStatusBarForTheme(newTheme);
                updateNavigationBarForTheme(newTheme);
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });

    // Initial sync
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
    updateStatusBarForTheme(currentTheme);
    updateNavigationBarForTheme(currentTheme);
}

/**
 * Update status bar theme
 */
async function updateStatusBarForTheme(theme) {
    try {
        let isLight = theme === 'light';
        if (theme !== 'dark' && theme !== 'light' && window.matchMedia) {
            isLight = !window.matchMedia('(prefers-color-scheme: dark)').matches;
        }

        // Instant synchronous native update
        var bridge = window.AndroidBridge || window.PwaninetBridge;
        if (bridge && typeof bridge.setSystemBarTheme === 'function') {
            bridge.setSystemBarTheme(isLight ? 'light' : 'dark');
        }

        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.StatusBar) {
            const { StatusBar } = window.Capacitor.Plugins;
            const style = isLight ? 'LIGHT' : 'DARK';
            await StatusBar.setStyle({ style });
            console.log('[NativeApp] StatusBar style updated to: ' + style);
        }
    } catch (error) {
        console.error('[NativeApp] Failed to update status bar:', error);
    }
}

/**
 * Update navigation bar theme
 * Communicates with MainActivity via AndroidBridge to set navigation bar icon contrast
 */
async function updateNavigationBarForTheme(theme) {
    try {
        let isLight = true;
        if (theme === 'dark') {
            isLight = false;
        } else if (theme === 'light') {
            isLight = true;
        } else if (window.matchMedia) {
            isLight = !window.matchMedia('(prefers-color-scheme: dark)').matches;
        }

        const style = isLight ? 'LIGHT' : 'DARK';
        const themeStr = isLight ? 'light' : 'dark';

        // 1. Try AndroidBridge / PwaninetBridge JavascriptInterface (instantaneous call)
        var bridge = window.AndroidBridge || window.PwaninetBridge;
        if (bridge && typeof bridge.setNavigationBarTheme === 'function') {
            bridge.setNavigationBarTheme(themeStr);
            console.log('[NativeApp] Navigation bar theme updated via AndroidBridge to: ' + themeStr);
        } else if (bridge && typeof bridge.setSystemBarTheme === 'function') {
            bridge.setSystemBarTheme(themeStr);
            console.log('[NativeApp] System bar theme updated via AndroidBridge to: ' + themeStr);
        }

        // 2. Try Capacitor NavigationBar plugin (official plugin bridge)
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.NavigationBar) {
            try {
                await window.Capacitor.Plugins.NavigationBar.setStyle({ style });
                console.log('[NativeApp] Navigation bar updated via Capacitor NavigationBar plugin to: ' + style);
            } catch (pluginErr) {
                console.warn('[NativeApp] Capacitor NavigationBar plugin error:', pluginErr);
            }
        }
    } catch (error) {
        console.error('[NativeApp] Failed to update navigation bar:', error);
    }
}

/**
 * Initialize caching for better performance
 */
function initCaching() {
    try {
        const theme = localStorage.getItem('theme');
        const fontScale = localStorage.getItem('font_scale');
        console.log('[NativeApp] Cached preferences loaded');
        
        if (window.PwaniNetUsername) {
            sessionStorage.setItem('username', window.PwaniNetUsername);
        }
    } catch (error) {
        console.error('[NativeApp] Failed to initialize caching:', error);
    }
}

/**
 * Native Media Handling (Camera/Gallery)
 */
function initNativeMedia() {
    document.addEventListener('click', async (e) => {
        const target = e.target.closest('input[type="file"][capture]');
        if (target && window.Capacitor.Plugins.Camera) {
            e.preventDefault();
            try {
                const { Camera, CameraResultType, CameraSource } = window.Capacitor.Plugins;
                const image = await Camera.getPhoto({
                    quality: 90,
                    allowEditing: false,
                    resultType: CameraResultType.Uri,
                    source: CameraSource.Camera
                });

                const response = await fetch(image.webPath);
                const blob = await response.blob();
                const file = new File([blob], 'captured_image_' + Date.now() + '.jpg', { type: 'image/jpeg' });

                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                target.files = dataTransfer.files;
                target.dispatchEvent(new Event('change', { bubbles: true }));
            } catch (error) {
                if (error.message !== 'User cancelled photos app') {
                    console.error('[NativeApp] Camera capture failed:', error);
                }
            }
        }
    }, true);
}

/**
 * Android Back Button Handling
 */
async function initBackNavigation() {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.App) return;
        const { App } = window.Capacitor.Plugins;

        App.addListener('backButton', async () => {
            const dismissed = dismissActiveOverlays();
            if (dismissed) return;

            const currentPath = window.location.pathname;
            const isRoot = currentPath === '/' || currentPath === '/home/';

            if (!isRoot && window.history.length > 1) {
                window.history.back();
            } else {
                await App.exitApp();
            }
        });
    } catch (error) {
        console.error('[NativeApp] Failed to initialize back navigation:', error);
    }
}

/**
 * Dismisses any active UI overlays
 */
function dismissActiveOverlays() {
    let dismissed = false;

    // Modals
    const activeModals = document.querySelectorAll('.modal.show, #pwaninetStatusModal.show');
    activeModals.forEach(modalEl => {
        if (window.bootstrap && window.bootstrap.Modal) {
            const modal = window.bootstrap.Modal.getInstance(modalEl);
            if (modal) {
                modal.hide();
                dismissed = true;
            }
        }
        if (!dismissed) {
            modalEl.classList.remove('show');
            modalEl.style.display = 'none';
            document.body.classList.remove('modal-open');
            const backdrop = document.querySelector('.modal-backdrop');
            if (backdrop) backdrop.remove();
            dismissed = true;
        }
    });
    if (dismissed) return true;

    // Custom Overlays
    const customOverlays = document.querySelectorAll('.overlay.show, .emoji-picker-modal.show, .attachment-modal.show, .voice-recording-preview.show, .context-menu.show, #themeModal.show, #voiceModal.show, #attachmentModal.show');
    customOverlays.forEach(overlay => {
        overlay.classList.remove('show');
        if (overlay.classList.contains('context-menu')) overlay.style.display = 'none';
        dismissed = true;
    });

    return dismissed;
}

/**
 * Native App Update Notification & Version Management
 */
function injectNativeUpdateStyles() {
    if (document.getElementById('pwaninet-native-update-styles')) return;
    const style = document.createElement('style');
    style.id = 'pwaninet-native-update-styles';
    style.textContent = `
        #pwaninet-native-update-banner {
            position: fixed;
            right: 16px;
            left: 16px;
            max-width: 420px;
            margin: 0 auto;
            bottom: calc(84px + var(--pwaninet-safe-area-bottom, 0px));
            z-index: 10002;
            background: var(--card-bg, #ffffff);
            color: var(--text-dark, #0f172a);
            border: 1px solid var(--border, #e2e8f0);
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
            overflow: hidden;
            animation: pwaninet-banner-fade-up 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        [data-theme="dark"] #pwaninet-native-update-banner {
            background: var(--card-bg, #1e293b);
            color: var(--text-primary, #f8fafc);
            border-color: var(--border, #334155);
        }
        .pwaninet-native-update-inner {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
        }
        .pwaninet-native-update-icon {
            flex-shrink: 0;
            display: flex;
            align-items: center;
        }
        .pwaninet-native-update-content {
            flex: 1;
            min-width: 0;
        }
        .pwaninet-native-update-title {
            font-weight: 700;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 6px;
            line-height: 1.2;
            color: var(--text-dark, #0f172a);
        }
        [data-theme="dark"] .pwaninet-native-update-title {
            color: var(--text-primary, #f8fafc);
        }
        .pwaninet-native-update-badge {
            background: var(--primary-light, #dbeafe);
            color: var(--primary, #2563eb);
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 6px;
            letter-spacing: 0.5px;
        }
        [data-theme="dark"] .pwaninet-native-update-badge {
            background: #312e81;
            color: #a5b4fc;
        }
        .pwaninet-native-update-sub {
            font-size: 12px;
            color: var(--text-secondary, #64748b);
            margin-top: 3px;
            line-height: 1.3;
        }
        .pwaninet-native-update-actions {
            display: flex;
            flex-direction: column;
            gap: 6px;
            flex-shrink: 0;
        }
        .pwaninet-native-later-btn {
            background: transparent;
            border: none;
            padding: 0;
            font-size: 11px;
            color: var(--text-secondary, #64748b);
            cursor: pointer;
            text-align: center;
            text-decoration: underline;
            text-underline-offset: 2px;
        }
        .pwaninet-native-later-btn:hover {
            color: var(--text-primary, #0f172a);
        }
        [data-theme="dark"] .pwaninet-native-later-btn:hover {
            color: #ffffff;
        }
        #pwaninet-mandatory-modal-backdrop {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 100000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .pwaninet-mandatory-modal {
            background: var(--card-bg, #ffffff);
            border-radius: 20px;
            padding: 28px 24px;
            max-width: 400px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border, #e2e8f0);
        }
        [data-theme="dark"] .pwaninet-mandatory-modal {
            background: var(--card-bg, #1e293b);
            color: var(--text-primary, #f8fafc);
            border-color: var(--border, #334155);
        }
    `;
    document.head.appendChild(style);
}

async function getInstalledAppVersion() {
    // 1. Try AndroidBridge / PwaninetBridge getAppVersionInfo
    var bridge = window.AndroidBridge || window.PwaninetBridge;
    if (bridge && typeof bridge.getAppVersionInfo === 'function') {
        try {
            var info = JSON.parse(bridge.getAppVersionInfo());
            if (info && (info.versionName || info.versionCode)) {
                return {
                    version: String(info.versionName || '1.0.0').replace(/^v/, '').trim(),
                    build: parseInt(info.versionCode || '1', 10)
                };
            }
        } catch (e) {
            console.warn('[NativeApp] getAppVersionInfo parse error:', e);
        }
    }

    // 2. Try Capacitor App plugin via registerPlugin, Plugins.App, or nativePromise
    if (window.Capacitor) {
        try {
            var App = (window.Capacitor.Plugins && window.Capacitor.Plugins.App) ||
                      (typeof window.Capacitor.registerPlugin === 'function' && window.Capacitor.registerPlugin('App'));
            if (App && typeof App.getInfo === 'function') {
                var appInfo = await App.getInfo();
                if (appInfo && (appInfo.version || appInfo.build)) {
                    return {
                        version: String(appInfo.version || '1.0.0').replace(/^v/, '').trim(),
                        build: parseInt(appInfo.build || '1', 10)
                    };
                }
            } else if (typeof window.Capacitor.nativePromise === 'function') {
                var rawInfo = await window.Capacitor.nativePromise('App', 'getInfo');
                if (rawInfo && (rawInfo.version || rawInfo.build)) {
                    return {
                        version: String(rawInfo.version || '1.0.0').replace(/^v/, '').trim(),
                        build: parseInt(rawInfo.build || '1', 10)
                    };
                }
            }
        } catch (e) {
            console.warn('[NativeApp] Capacitor App.getInfo error:', e);
        }
    }

    // 3. Try User-Agent parsing
    if (typeof navigator !== 'undefined' && navigator.userAgent) {
        var uaMatch = navigator.userAgent.match(/PwaniNetApp\/Android\/([0-9\.]+)/);
        if (uaMatch && uaMatch[1]) {
            var uaBuildMatch = navigator.userAgent.match(/Build\/([0-9]+)/);
            return {
                version: uaMatch[1].trim(),
                build: uaBuildMatch ? parseInt(uaBuildMatch[1], 10) : 1
            };
        }
    }

    var cachedVer = localStorage.getItem('pwaninet_installed_apk_version') || '1.0.0';
    var cachedBuild = parseInt(localStorage.getItem('pwaninet_installed_apk_build') || '1', 10);
    return { version: cachedVer.replace(/^v/, '').trim(), build: cachedBuild };
}

function triggerNativeApkDownload(apkUrl) {
    var url = apkUrl || '/download/app/latest/';
    if (!url.startsWith('http')) {
        url = window.location.origin + (url.startsWith('/') ? '' : '/') + url;
    }
    var bridge = window.AndroidBridge || window.PwaninetBridge;
    if (bridge && typeof bridge.openExternalUrl === 'function') {
        bridge.openExternalUrl(url);
    } else {
        window.open(url, '_blank');
    }
}

function semverCompare(v1, v2) {
    if (!v1 || !v2) return 0;
    var p1 = v1.replace(/^v/, '').split('.').map(Number);
    var p2 = v2.replace(/^v/, '').split('.').map(Number);
    for (var i = 0; i < Math.max(p1.length, p2.length); i++) {
        var num1 = p1[i] || 0;
        var num2 = p2[i] || 0;
        if (num1 > num2) return 1;
        if (num1 < num2) return -1;
    }
    return 0;
}
window.semverCompare = semverCompare;

function isRunningInNativeApp() {
    return Boolean(
        (window.AndroidBridge && typeof window.AndroidBridge.getAppVersionInfo === 'function') ||
        (window.PwaninetBridge && typeof window.PwaninetBridge.getAppVersionInfo === 'function') ||
        (window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function' && window.Capacitor.isNativePlatform()) ||
        (typeof navigator !== 'undefined' && /PwaniNetApp\/Android/i.test(navigator.userAgent))
    );
}
window.isRunningInNativeApp = isRunningInNativeApp;

async function checkNativeAppUpdates(manual) {
    try {
        // Strict separation: Only run native update checks when inside the native app
        if (!isRunningInNativeApp()) {
            // Clean up legacy cookie on web/PWA so it never pollutes server context
            document.cookie = 'pwaninet_native_version=; path=/; max-age=0; SameSite=Lax';
            return;
        }

        var installed = await getInstalledAppVersion();
        if (installed && installed.version) {
            localStorage.setItem('pwaninet_installed_apk_version', installed.version);
            localStorage.setItem('pwaninet_installed_apk_build', String(installed.build));
            document.cookie = 'pwaninet_native_version=' + encodeURIComponent(installed.version) + '; path=/; max-age=31536000; SameSite=Lax';
        }

        var res = await fetch('/api/releases/version_check/?installed_build=' + installed.build + '&installed_version=' + encodeURIComponent(installed.version));
        var data = res.ok ? await res.json() : {
            update_available: false,
            latest_version: installed.version,
            latest_apk_version: installed.version,
            running_version: installed.version
        };

        // Real-time GitHub Releases API check fallback
        try {
            var ghRes = await fetch('https://api.github.com/repos/2006-zayne/pwaninet/releases/latest');
            if (ghRes.ok) {
                var ghData = await ghRes.json();
                var ghTag = (ghData.tag_name || '').replace(/^v/, '').trim();
                var hasApk = ghData.assets && ghData.assets.some(function(a) {
                    return (a.name || '').endsWith('.apk');
                });

                if (ghTag) {
                    if (!data.latest_version || semverCompare(ghTag, data.latest_version) > 0) {
                        data.latest_version = ghTag;
                    }
                    if (hasApk) {
                        if (!data.latest_apk_version || semverCompare(ghTag, data.latest_apk_version) > 0) {
                            data.latest_apk_version = ghTag;
                        }
                    }
                }
            }
        } catch (ghErr) {
            // Ignore offline or rate limits
        }

        // Ensure latest numbers are never lower than what client actually has installed
        if (semverCompare(installed.version, data.latest_apk_version) > 0) {
            data.latest_apk_version = installed.version;
        }
        if (semverCompare(installed.version, data.latest_version) > 0) {
            data.latest_version = installed.version;
        }

        var targetApkVer = data.latest_apk_version || data.latest_version;

        // Strict invariant: update is ONLY available if targetApkVer is strictly higher than installed.version
        if (semverCompare(targetApkVer, installed.version) > 0) {
            data.update_available = true;
            data.running_version = installed.version; // STICKS!
        } else {
            data.update_available = false;
            // Running version is the installed version or latest web version if higher
            data.running_version = semverCompare(installed.version, data.latest_version) >= 0 ? installed.version : data.latest_version;
            var existingBanner = document.getElementById('pwaninet-native-update-banner');
            if (existingBanner) existingBanner.remove();
            var existingModal = document.getElementById('pwaninet-mandatory-modal-backdrop');
            if (existingModal) existingModal.remove();
        }

        // Hydrate running version in DOM (footer, about page, updates page)
        var effectiveVer = data.running_version || installed.version;
        var curVerElements = document.querySelectorAll('.app-current-version, #current-version');
        curVerElements.forEach(function(el) {
            if (el.id === 'footer-app-version') {
                el.textContent = 'Version ' + effectiveVer;
            } else {
                el.textContent = effectiveVer;
            }
        });

        // Check if Settings page native update card is present in DOM
        var card = document.getElementById('settings-native-update-card');
        if (card) {
            var installedVerSpan = document.getElementById('native-installed-version');
            if (installedVerSpan) installedVerSpan.textContent = 'v' + installed.version;

            var latestVerSpan = document.getElementById('native-latest-version-meta');
            if (latestVerSpan) latestVerSpan.textContent = 'Latest v' + targetApkVer;

            var badge = document.getElementById('native-app-status-badge');
            var desc = document.getElementById('native-app-update-desc');
            var updateBtn = document.getElementById('native-app-download-update-btn');
            var checkBtn = document.getElementById('native-app-check-update-btn');

            if (data.update_available) {
                if (badge) {
                    badge.textContent = 'Update Available';
                    badge.style.background = '#fef3c7';
                    badge.style.color = '#d97706';
                }
                if (desc) {
                    desc.textContent = 'Version ' + targetApkVer + ' is available with native enhancements. Please install the new APK build.';
                }
                if (updateBtn) {
                    updateBtn.classList.remove('d-none');
                    updateBtn.classList.add('d-inline-flex');
                }
                if (checkBtn) {
                    checkBtn.classList.add('btn-outline-secondary');
                    checkBtn.classList.remove('btn-outline-primary');
                }
            } else {
                if (badge) {
                    badge.textContent = 'Up to date';
                    badge.style.background = '#dcfce7';
                    badge.style.color = '#15803d';
                }
                if (desc) {
                    desc.textContent = 'You have the latest version of the native Android app installed (v' + installed.version + ').';
                }
                if (updateBtn) {
                    updateBtn.classList.add('d-none');
                    updateBtn.classList.remove('d-inline-flex');
                }
                if (checkBtn) {
                    checkBtn.classList.remove('btn-outline-secondary');
                    checkBtn.classList.add('btn-outline-primary');
                }
            }
        }

        if (manual && !data.update_available) {
            alert('PwaniNet is up to date! You are running version ' + effectiveVer + '.');
            return;
        }

        if (data.update_available && semverCompare(targetApkVer, installed.version) > 0) {
            if (manual) {
                showNativeUpdateBanner(data);
                if (confirm('A new native version (v' + targetApkVer + ') is available! Would you like to download the APK update now?')) {
                    triggerNativeApkDownload(data.apk_url || '/download/app/latest/');
                }
                return;
            }

            // Check for mandatory update
            if (data.mandatory_update) {
                showMandatoryUpdateModal(data);
                return;
            }

            // Check snooze for standard optional prompt
            var snoozedUntil = parseInt(localStorage.getItem('pwaninet_native_update_snooze') || '0', 10);
            if (!manual && snoozedUntil && Date.now() < snoozedUntil) {
                return;
            }

            showNativeUpdateBanner(data);
        }
    } catch (e) {
        console.warn('[NativeApp] Update check failed:', e);
        if (manual) {
            alert('Unable to check for updates. Please verify your internet connection.');
        }
    }
}

function showNativeUpdateBanner(data) {
    if (document.getElementById('pwaninet-native-update-banner')) return;
    injectNativeUpdateStyles();

    var targetVer = data.latest_apk_version || data.latest_version;
    var banner = document.createElement('div');
    banner.id = 'pwaninet-native-update-banner';
    banner.innerHTML = `
        <div class="pwaninet-native-update-inner">
            <div class="pwaninet-native-update-icon">
                <img src="/static/images/pwaninet-app-icon.png" alt="PwaniNet" width="42" height="42" style="border-radius:10px;"/>
            </div>
            <div class="pwaninet-native-update-content">
                <div class="pwaninet-native-update-title">
                    <span>PwaniNet Update</span>
                    <span class="pwaninet-native-update-badge">v${targetVer}</span>
                </div>
                <div class="pwaninet-native-update-sub">
                    ${data.release_title || 'New update available with performance enhancements.'}
                </div>
            </div>
            <div class="pwaninet-native-update-actions">
                <button type="button" class="btn btn-primary btn-sm" id="pwaninet-native-update-download-btn">
                    <i class="bi bi-download me-1"></i>Update
                </button>
                <button type="button" class="pwaninet-native-later-btn" id="pwaninet-native-update-later-btn">
                    Later
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(banner);

    var dlBtn = document.getElementById('pwaninet-native-update-download-btn');
    if (dlBtn) {
        dlBtn.addEventListener('click', function() {
            triggerNativeApkDownload(data.apk_url || '/download/app/latest/');
            banner.remove();
        });
    }

    var laterBtn = document.getElementById('pwaninet-native-update-later-btn');
    if (laterBtn) {
        laterBtn.addEventListener('click', function() {
            banner.remove();
            // Snooze for 24 hours
            localStorage.setItem('pwaninet_native_update_snooze', String(Date.now() + 86400000));
        });
    }
}

function showMandatoryUpdateModal(data) {
    if (document.getElementById('pwaninet-mandatory-modal-backdrop')) return;
    injectNativeUpdateStyles();

    var targetVer = data.latest_apk_version || data.latest_version;
    var backdrop = document.createElement('div');
    backdrop.id = 'pwaninet-mandatory-modal-backdrop';
    backdrop.innerHTML = `
        <div class="pwaninet-mandatory-modal">
            <img src="/static/images/pwaninet-app-icon.png" alt="PwaniNet" width="56" height="56" style="border-radius:14px; margin-bottom: 16px;"/>
            <h4 style="font-weight: 700; margin-bottom: 8px;">Update Required</h4>
            <p style="font-size: 14px; color: var(--text-secondary, #64748b); margin-bottom: 20px;">
                A critical update (v${targetVer}) is required to continue using PwaniNet. Please download and install the latest APK.
            </p>
            <button type="button" class="btn btn-primary w-100 py-2" id="pwaninet-mandatory-download-btn" style="font-weight: 600;">
                <i class="bi bi-download me-2"></i>Download & Install Update
            </button>
        </div>
    `;
    document.body.appendChild(backdrop);

    var btn = document.getElementById('pwaninet-mandatory-download-btn');
    if (btn) {
        btn.addEventListener('click', function() {
            triggerNativeApkDownload(data.apk_url || '/download/app/latest/');
        });
    }
}

function initNativeAppUpdates() {
    // Expose globally
    window.checkNativeAppUpdates = checkNativeAppUpdates;
    window.triggerNativeApkDownload = triggerNativeApkDownload;
    window.getInstalledAppVersion = getInstalledAppVersion;

    // Delay initial check slightly after app boot
    setTimeout(function() {
        checkNativeAppUpdates(false);
    }, 2000);

    // Re-check when app returns from background
    if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.App) {
        window.Capacitor.Plugins.App.addListener('appStateChange', function(state) {
            if (state && state.isActive) {
                checkNativeAppUpdates(false);
            }
        });
    }

    // Re-evaluate Settings card on HTMX page swaps
    document.addEventListener('htmx:afterSwap', function() {
        if (document.getElementById('settings-native-update-card')) {
            checkNativeAppUpdates(false);
        }
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        var domReadyTime = performance.now();
        console.log('[PWANINET-NATIVE] DOMContentLoaded at:', domReadyTime.toFixed(2) + 'ms');
        console.log('[PWANINET-NATIVE] Time from script load to DOMReady:', (domReadyTime - window._pwaninet_native_load_time).toFixed(2) + 'ms');
        initNativeAppEnhancements();
    });
} else {
    var domReadyTime = performance.now();
    console.log('[PWANINET-NATIVE] DOM already ready at:', domReadyTime.toFixed(2) + 'ms');
    initNativeAppEnhancements();
}
