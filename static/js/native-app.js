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
