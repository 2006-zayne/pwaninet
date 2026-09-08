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

    // Initialize virtual keyboard (IME) viewport management
    initKeyboardManager();

    // Initialize native-like pull to refresh
    initPullToRefresh();

    // Initialize native push notifications (Capacitor FCM / APNS)
    initNativePush();

    window._pwaninet_native_initialized = true;

    const endTime = performance.now();
    console.log('[PWANINET-NATIVE] Native initialization fully complete in:', (endTime - startTime).toFixed(2) + 'ms');
    console.log('[PWANINET-NATIVE] Total time from script load:', (endTime - window._pwaninet_native_load_time).toFixed(2) + 'ms');
}

/**
 * Instant button touch states - eliminates 300ms gesture delay and provides tactile feedback
 */
function initInstantTouchStates() {
    const clickableSelectors = [
        '.btn',
        '.btn-native',
        'button',
        '.nav-chip',
        '.action-icon',
        '.card-clickable',
        '.dropdown-item',
        '.reaction-chip',
        '.cursor-pointer',
        '[data-clickable="true"]'
    ];
    
    document.addEventListener('touchstart', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) {
            target.classList.add('activated');
            // Trigger instant light haptic if element doesn't have an explicit haptic attribute
            if (!target.hasAttribute('data-haptic') && window.Haptics && typeof window.Haptics.impactLight === 'function') {
                window.Haptics.impactLight();
            }
        }
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
 * Android Back Button Handling with Double-Tap to Exit
 */
let _lastBackPressTime = 0;

async function initBackNavigation() {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.App) return;
        const { App } = window.Capacitor.Plugins;

        App.addListener('backButton', async () => {
            // 1. Dismiss active overlays/drawers first
            const dismissed = dismissActiveOverlays();
            if (dismissed) {
                if (window.Haptics) window.Haptics.impactLight();
                return;
            }

            const currentPath = window.location.pathname;
            const isRoot = currentPath === '/' || currentPath === '/home/' || currentPath === '';

            // 2. Non-root: pop browser history
            if (!isRoot && window.history.length > 1) {
                if (window.Haptics) window.Haptics.selection();
                window.history.back();
                return;
            }

            // 3. Root: double-tap to exit
            const now = Date.now();
            if (now - _lastBackPressTime < 2000) {
                if (window.Haptics) window.Haptics.impactMedium();
                await App.exitApp();
            } else {
                _lastBackPressTime = now;
                if (window.Haptics) window.Haptics.impactLight();

                var bridge = window.AndroidBridge || window.PwaninetBridge;
                if (bridge && typeof bridge.showToast === 'function') {
                    bridge.showToast('Press back again to exit');
                } else {
                    showInAppBackToast('Press back again to exit');
                }
            }
        });
    } catch (error) {
        console.error('[NativeApp] Failed to initialize back navigation:', error);
    }
}

function showInAppBackToast(message) {
    let toast = document.getElementById('pwaninet-back-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'pwaninet-back-toast';
        toast.style.cssText = 'position:fixed;bottom:calc(85px + var(--pwaninet-safe-area-bottom, 0px));left:50%;transform:translateX(-50%);background:rgba(15,23,42,0.92);color:#fff;font-size:13px;font-weight:600;padding:8px 18px;border-radius:24px;box-shadow:0 4px 16px rgba(0,0,0,0.3);z-index:100000;pointer-events:none;transition:opacity 0.25s ease;backdrop-filter:blur(8px);';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    clearTimeout(toast._fadeTimeout);
    toast._fadeTimeout = setTimeout(() => {
        toast.style.opacity = '0';
    }, 1800);
}

/**
 * Dismisses any active UI overlays
 */
function dismissActiveOverlays() {
    let dismissed = false;

    // Bootstrap Offcanvas (sidebars / navigation drawers)
    const activeOffcanvas = document.querySelectorAll('.offcanvas.show');
    activeOffcanvas.forEach(el => {
        if (window.bootstrap && window.bootstrap.Offcanvas) {
            const instance = window.bootstrap.Offcanvas.getInstance(el);
            if (instance) {
                instance.hide();
                dismissed = true;
            }
        }
        if (!dismissed) {
            el.classList.remove('show');
            dismissed = true;
        }
    });
    if (dismissed) return true;

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

    // Custom Overlays & Menus
    const customOverlays = document.querySelectorAll('.overlay.show, .emoji-picker-modal.show, .attachment-modal.show, .voice-recording-preview.show, .context-menu.show, #themeModal.show, #voiceModal.show, #attachmentModal.show, .dropdown-menu.show');
    customOverlays.forEach(overlay => {
        overlay.classList.remove('show');
        if (overlay.classList.contains('context-menu') || overlay.classList.contains('dropdown-menu')) {
            overlay.style.display = 'none';
        }
        dismissed = true;
    });

    return dismissed;
}

/**
 * Virtual Keyboard (IME) Viewport Management
 * Hides floating bottom navigation when typing to prevent viewport overlap
 */
function initKeyboardManager() {
    if (!window.visualViewport) return;

    function handleViewportChange() {
        const currentHeight = window.visualViewport.height;
        const isKeyboardVisible = (window.innerHeight - currentHeight) > 150;
        if (isKeyboardVisible) {
            document.body.classList.add('keyboard-open');
        } else {
            document.body.classList.remove('keyboard-open');
        }
    }

    window.visualViewport.addEventListener('resize', handleViewportChange);
    window.visualViewport.addEventListener('scroll', handleViewportChange);

    document.addEventListener('focusin', function(e) {
        if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) {
            setTimeout(() => {
                document.body.classList.add('keyboard-open');
            }, 60);
        }
    });

    document.addEventListener('focusout', function(e) {
        if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) {
            setTimeout(() => {
                if (window.visualViewport && (window.innerHeight - window.visualViewport.height) <= 150) {
                    document.body.classList.remove('keyboard-open');
                }
            }, 100);
        }
    });
}

/**
 * Native-style Pull-to-Refresh with tactile haptic feedback
 */
function initPullToRefresh() {
    let startY = 0;
    let currentY = 0;
    let isPulling = false;
    let hapticTriggered = false;
    const threshold = 65;

    let ptrIndicator = document.getElementById('pwaninet-ptr-indicator');
    if (!ptrIndicator) {
        ptrIndicator = document.createElement('div');
        ptrIndicator.id = 'pwaninet-ptr-indicator';
        ptrIndicator.style.cssText = 'position:fixed;top:calc(var(--navbar-height, 56px) + var(--pwaninet-safe-area-top, 0px) + 8px);left:50%;transform:translate(-50%, -150%);width:36px;height:36px;border-radius:50%;background:var(--card-bg, #ffffff);box-shadow:0 3px 12px rgba(0,0,0,0.18);display:flex;align-items:center;justify-content:center;z-index:9998;pointer-events:none;transition:transform 0.15s cubic-bezier(0.2,0,0.2,1), opacity 0.2s ease;opacity:0;';
        ptrIndicator.innerHTML = '<i class="bi bi-arrow-clockwise" style="font-size:18px;color:var(--primary, #2563eb);display:inline-block;transition:transform 0.2s;"></i>';
        document.body.appendChild(ptrIndicator);
    }

    const icon = ptrIndicator.querySelector('i');

    document.addEventListener('touchstart', function(e) {
        if (window.scrollY <= 2 && e.touches.length === 1) {
            startY = e.touches[0].clientY;
            isPulling = true;
            hapticTriggered = false;
        } else {
            isPulling = false;
        }
    }, { passive: true });

    document.addEventListener('touchmove', function(e) {
        if (!isPulling || window.scrollY > 2) return;
        currentY = e.touches[0].clientY;
        const diff = currentY - startY;

        if (diff > 10) {
            const pullDistance = Math.min(diff * 0.45, threshold + 25);
            ptrIndicator.style.opacity = String(Math.min(pullDistance / threshold, 1));
            ptrIndicator.style.transform = 'translate(-50%, ' + pullDistance + 'px)';
            if (icon) icon.style.transform = 'rotate(' + (pullDistance * 3) + 'deg)';

            if (pullDistance >= threshold && !hapticTriggered) {
                hapticTriggered = true;
                if (window.Haptics) window.Haptics.impactLight();
            } else if (pullDistance < threshold) {
                hapticTriggered = false;
            }
        }
    }, { passive: true });

    document.addEventListener('touchend', function() {
        if (!isPulling) return;
        const diff = currentY - startY;
        isPulling = false;

        if (diff * 0.45 >= threshold) {
            if (window.Haptics) window.Haptics.selection();
            ptrIndicator.style.transform = 'translate(-50%, ' + threshold + 'px)';
            if (icon) {
                icon.style.animation = 'spin 0.8s linear infinite';
            }
            setTimeout(() => {
                window.location.reload();
            }, 300);
        } else {
            ptrIndicator.style.opacity = '0';
            ptrIndicator.style.transform = 'translate(-50%, -150%)';
        }
    }, { passive: true });
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

function getNativeCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag && metaTag.getAttribute('content')) {
        return metaTag.getAttribute('content');
    }
    const inputTag = document.querySelector('[name="csrfmiddlewaretoken"]');
    if (inputTag && inputTag.value) {
        return inputTag.value;
    }
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith('csrftoken=')) {
            return decodeURIComponent(cookie.substring('csrftoken='.length));
        }
    }
    return '';
}

/**
 * Initialize native push notifications (Capacitor FCM / APNS)
 */
async function initNativePush() {
    if (!window.Capacitor || (typeof window.Capacitor.isNativePlatform === 'function' && !window.Capacitor.isNativePlatform())) {
        return;
    }

    const PushNotifications = window.Capacitor.Plugins && window.Capacitor.Plugins.PushNotifications;
    if (!PushNotifications) {
        console.warn('[PWANINET-NATIVE] PushNotifications plugin not available on window.Capacitor.Plugins');
        return;
    }

    try {
        let permStatus = await PushNotifications.checkPermissions();
        console.log('[PWANINET-NATIVE] Push permission status:', permStatus);

        if (permStatus.receive === 'prompt') {
            permStatus = await PushNotifications.requestPermissions();
        }

        if (permStatus.receive !== 'granted') {
            console.warn('[PWANINET-NATIVE] Push notification permission not granted:', permStatus.receive);
            return;
        }

        // Register Android Notification Channel (Android 8.0+)
        // Consolidate into ONE single unified notification channel matching in-app card system
        if (typeof PushNotifications.createChannel === 'function') {
            try {
                // Delete legacy multi-channel configurations if they exist
                if (typeof PushNotifications.deleteChannel === 'function') {
                    await PushNotifications.deleteChannel({ id: 'pwaninet_social' }).catch(() => {});
                    await PushNotifications.deleteChannel({ id: 'pwaninet_messages' }).catch(() => {});
                }

                await PushNotifications.createChannel({
                    id: 'pwaninet_notifications',
                    name: 'PwaniNet Notifications',
                    description: 'All social updates, mentions, posts, documents, and messages',
                    importance: 5,
                    visibility: 1,
                    vibration: true,
                    lights: true,
                    lightColor: '#2563eb',
                    sound: 'default'
                });
                console.log('[PWANINET-NATIVE] Push notification channel created successfully');
            } catch (chanErr) {
                console.warn('[PWANINET-NATIVE] Failed to configure notification channels:', chanErr);
            }
        }

        // Guard: On Android, Firebase FCM crashes fatally if google-services.json is missing.
        // We strictly require explicit positive confirmation from native bridge before registering.
        const platformName = (window.Capacitor.getPlatform && window.Capacitor.getPlatform()) || '';
        const isAndroid = platformName === 'android' || navigator.userAgent.includes('Android');

        if (isAndroid) {
            const bridge = window.AndroidBridge || window.PwaninetBridge;
            const isPushReady = bridge && typeof bridge.isPushNotificationsAvailable === 'function' && bridge.isPushNotificationsAvailable();
            if (!isPushReady) {
                console.warn('[PWANINET-NATIVE] Native push / Firebase is not initialized on this Android build (google-services.json missing). Push registration skipped to protect app stability.');
                return;
            }
        }

        // Listen for successful registration
        PushNotifications.addListener('registration', async function(token) {
            console.log('[PWANINET-NATIVE] Push registration success, token:', token.value);
            if (!token || !token.value) return;

            // Submit token to backend Django endpoint
            try {
                const response = await fetch('/api/push/subscribe/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getNativeCsrfToken()
                    },
                    body: JSON.stringify({
                        token_type: 'FCM',
                        platform: isAndroid ? 'ANDROID_NATIVE' : 'IOS_NATIVE',
                        fcm_token: token.value,
                        user_agent: navigator.userAgent
                    })
                });

                if (response.ok) {
                    console.log('[PWANINET-NATIVE] Successfully registered native push token with backend');
                    localStorage.setItem('pwaninet_push_subscribed', 'true');
                } else {
                    console.error('[PWANINET-NATIVE] Failed to register native push token with backend:', response.status);
                }
            } catch (err) {
                console.error('[PWANINET-NATIVE] Error registering native push token:', err);
            }
        });

        // Listen for registration errors
        PushNotifications.addListener('registrationError', function(error) {
            console.error('[PWANINET-NATIVE] Push registration error:', error);
        });

        // Listen for foreground push notifications
        PushNotifications.addListener('pushNotificationReceived', function(notification) {
            console.log('[PWANINET-NATIVE] Foreground push received:', notification);
            showNativePushBanner(notification);
        });

        // Listen for user interaction on notification
        PushNotifications.addListener('pushNotificationActionPerformed', function(notification) {
            console.log('[PWANINET-NATIVE] Push action performed:', notification);
            const data = notification.notification && notification.notification.data;
            const targetUrl = data && (data.url || data.link || data.destination_url || data.click_action);
            if (targetUrl) {
                window.location.href = targetUrl;
            }
        });

        // Register with native push service (APNS on iOS / FCM on Android)
        try {
            await PushNotifications.register();
        } catch (regErr) {
            console.warn('[PWANINET-NATIVE] Push registration call failed gracefully:', regErr);
            return;
        }

    } catch (e) {
        console.error('[PWANINET-NATIVE] Failed to initialize native push notifications:', e);
    }
}

/**
 * Display an in-app foreground notification banner matching the PwaniNet in-app notification card design.
 * Renders actor avatar, title, body, and post/document thumbnail previews.
 */
function showNativePushBanner(notification) {
    if (!notification) return;

    // Trigger native haptic feedback
    try {
        if (window.AndroidBridge && typeof window.AndroidBridge.hapticNotification === 'function') {
            window.AndroidBridge.hapticNotification('SUCCESS');
        } else if (window.Haptics && typeof window.Haptics.impactLight === 'function') {
            window.Haptics.impactLight();
        }
    } catch (_) {}

    const title = notification.title || 'PwaniNet';
    const body = notification.body || '';
    const data = notification.data || {};
    const icon = data.icon || notification.icon || '/static/images/web-app-manifest-192x192-rounded.png';
    const previewImage = data.image || notification.image || data.thumbnail_url || null;
    const resourceType = (data.resource_type || '').toUpperCase();
    const resourceTitle = data.resource_title || '';
    const targetUrl = data.url || data.link || data.destination_url || '/notifications/';

    // Remove existing banner if any
    const existing = document.getElementById('pwaninet-foreground-push-banner');
    if (existing) {
        existing.remove();
    }

    const banner = document.createElement('div');
    banner.id = 'pwaninet-foreground-push-banner';
    banner.className = 'notif-item pwaninet-native-card-banner';
    banner.style.cssText = [
        'position: fixed',
        'top: calc(var(--pwaninet-safe-area-top, 0px) + 10px)',
        'left: 12px',
        'right: 12px',
        'max-width: 500px',
        'margin: 0 auto',
        'background: var(--bg-card, #ffffff)',
        'color: var(--text-primary, #1e293b)',
        'border: 1px solid var(--border-color, rgba(0, 0, 0, 0.12))',
        'border-radius: 16px',
        'box-shadow: 0 12px 30px -6px rgba(0, 0, 0, 0.2), 0 6px 12px -4px rgba(0, 0, 0, 0.1)',
        'padding: 12px 14px',
        'display: flex',
        'align-items: center',
        'gap: 12px',
        'z-index: 100000',
        'cursor: pointer',
        'transform: translateY(-130%)',
        'opacity: 0',
        'transition: transform 0.38s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease',
        'user-select: none',
        '-webkit-user-select: none'
    ].join('; ');

    // Build right-side preview column matching in-app notification card
    let previewHtml = '';
    if (previewImage) {
        previewHtml = `
            <div class="notif-preview-col flex-shrink-0" style="width: 48px; height: 48px; border-radius: 10px; overflow: hidden; border: 1px solid var(--border, rgba(0,0,0,0.1)); background-color: var(--bg-secondary, #f8fafc); display: flex; align-items: center; justify-content: center;">
                <img src="${previewImage}" alt="Preview" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.style.display='none';">
            </div>
        `;
    } else if (resourceType === 'DOCUMENT' || (data.notification_type && data.notification_type.includes('DOC'))) {
        previewHtml = `
            <div class="notif-preview-col flex-shrink-0" style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background-color: var(--bg-secondary, #f1f5f9); border: 1px solid var(--border, rgba(0,0,0,0.1));">
                <i class="bi bi-file-earmark-text" style="font-size: 1.35rem; color: var(--text-secondary, #64748b);"></i>
            </div>
        `;
    } else if (resourceType === 'POST' || (data.notification_type && (data.notification_type.includes('POST') || data.notification_type === 'LIKE' || data.notification_type === 'COMMENT'))) {
        previewHtml = `
            <div class="notif-preview-col flex-shrink-0" style="width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; background-color: var(--bg-secondary, #f1f5f9); border: 1px solid var(--border, rgba(0,0,0,0.1));">
                <i class="bi bi-chat-text" style="font-size: 1.35rem; color: var(--text-secondary, #64748b);"></i>
            </div>
        `;
    }

    banner.innerHTML = `
        <div class="notif-avatar-col flex-shrink-0" style="position: relative;">
            <img src="${icon}" alt="Avatar" style="width: 44px; height: 44px; border-radius: 50%; object-fit: cover; border: 1.5px solid var(--border, rgba(0,0,0,0.1)); background-color: var(--bg-secondary, #f1f5f9);" onerror="this.src='/static/images/web-app-manifest-192x192-rounded.png';">
        </div>
        <div class="notif-body flex-grow-1" style="min-width: 0;">
            <div class="notif-title" style="font-size: 0.88rem; font-weight: 700; color: var(--text-primary, #0f172a); line-height: 1.25; margin-bottom: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                ${title}
            </div>
            <div class="notif-message" style="font-size: 0.82rem; color: var(--text-secondary, #475569); line-height: 1.35; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
                ${body}
            </div>
            ${resourceTitle && resourceTitle !== body ? `<div style="font-size: 0.75rem; color: var(--text-muted, #94a3b8); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">“${resourceTitle}”</div>` : ''}
        </div>
        ${previewHtml}
        <button type="button" aria-label="Dismiss" style="background: none; border: none; padding: 4px 6px; cursor: pointer; color: var(--text-secondary, #94a3b8); font-size: 1.35rem; line-height: 1; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-left: 2px;">
            &times;
        </button>
    `;

    // Click handler to open target
    banner.addEventListener('click', function(e) {
        if (e.target.closest('button')) {
            dismissBanner();
            return;
        }
        dismissBanner();
        if (targetUrl) {
            window.location.href = targetUrl;
        }
    });

    document.body.appendChild(banner);

    // Animate in
    requestAnimationFrame(() => {
        banner.style.transform = 'translateY(0)';
        banner.style.opacity = '1';
    });

    let dismissTimer = setTimeout(dismissBanner, 6000);

    function dismissBanner() {
        clearTimeout(dismissTimer);
        banner.style.transform = 'translateY(-130%)';
        banner.style.opacity = '0';
        setTimeout(() => {
            if (banner.parentNode) {
                banner.parentNode.removeChild(banner);
            }
        }, 380);
    }
}

// Expose globally
window.initNativePush = initNativePush;
window.showNativePushBanner = showNativePushBanner;


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
