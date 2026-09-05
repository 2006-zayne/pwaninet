/**
 * Native App Enhancements - Capacitor-specific functionality
 * Only active when running in Capacitor native environment
 */

(function() {
    window._pwaninet_native_load_time = performance.now();
    console.log('[PWANINET-NATIVE] Script load time:', window._pwaninet_native_load_time.toFixed(2) + 'ms');

    function initEarly() {
        var isNative = window.hasOwnProperty('Capacitor');
        if (!isNative || window._pwaninet_native_ui_initialized) return;

        var earlyInitStart = performance.now();
        console.log('[PWANINET-NATIVE] Early UI initialization started at:', earlyInitStart.toFixed(2) + 'ms');

        // 1. Configure Status Bar immediately for edge-to-edge
        initStatusBarEarly();

        // 2. Initialize Safe Area listeners and CSS variables (insets only, no system bar config)
        initSafeAreaEarly();

        window._pwaninet_native_ui_initialized = true;
        var earlyInitEnd = performance.now();
        console.log('[PWANINET-NATIVE] Early UI initialization complete in:', (earlyInitEnd - earlyInitStart).toFixed(2) + 'ms');
    }

    // If Capacitor is already here, init now. Otherwise, the bridge might be coming.
    if (window.Capacitor && window.Capacitor.Plugins) {
        initEarly();
    } else {
        // Fallback: wait a few frames if we're in a native environment but bridge is lagging
        var attempts = 0;
        var checkBridge = setInterval(function() {
            attempts++;
            if ((window.Capacitor && window.Capacitor.Plugins) || attempts > 20) {
                clearInterval(checkBridge);
                if (window.Capacitor && window.Capacitor.Plugins) initEarly();
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
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.StatusBar) return;

        const { StatusBar } = window.Capacitor.Plugins;

        // Initial setup for edge-to-edge transparency
        await StatusBar.setOverlaysWebView({ overlay: true });
        await StatusBar.setBackgroundColor({ color: '#00000000' });

        // Initial theme style (guess from HTML, will be corrected by observer later if wrong)
        const theme = document.documentElement.getAttribute('data-theme') || 'light';
        await StatusBar.setStyle({ style: theme === 'light' ? 'LIGHT' : 'DARK' });

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
            root.style.setProperty('--pwaninet-safe-area-top', insets.top + 'px');
            root.style.setProperty('--pwaninet-safe-area-bottom', insets.bottom + 'px');
            root.style.setProperty('--pwaninet-safe-area-left', insets.left + 'px');
            root.style.setProperty('--pwaninet-safe-area-right', insets.right + 'px');

            if (document.body) {
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
    const isNative = window.hasOwnProperty('Capacitor');

    if (!isNative) return;

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
 * Sync status bar with current theme
 * Navigation bar uses EdgeToEdge defaults from MainActivity.java
 */
function initThemeSync() {
    // Setup observer for future theme changes
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                const newTheme = document.documentElement.getAttribute('data-theme') || 'light';
                updateStatusBarForTheme(newTheme);
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
}

/**
 * Update status bar theme
 */
async function updateStatusBarForTheme(theme) {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.StatusBar) return;
        const { StatusBar } = window.Capacitor.Plugins;
        const style = theme === 'light' ? 'LIGHT' : 'DARK';
        await StatusBar.setStyle({ style });
        console.log('[NativeApp] StatusBar style updated to: ' + style);
    } catch (error) {
        console.error('[NativeApp] Failed to update status bar:', error);
    }
}

/**
 * Update navigation bar theme
 * NOTE: Navigation bar theme changes are limited on Android.
 * MainActivity.java EdgeToEdge sets initial transparent navigation bar with dark icons.
 * StatusBar plugin controls status bar theme. SafeArea provides insets only.
 */
async function updateNavigationBarForTheme(theme) {
    // Navigation bar theme changes not currently supported due to Android limitations
    // and to avoid competing system bar ownership with MainActivity.java EdgeToEdge
    // The navigation bar remains transparent with dark icons as set in MainActivity
    console.log('[NativeApp] Navigation bar theme change not implemented (using EdgeToEdge defaults)');
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
