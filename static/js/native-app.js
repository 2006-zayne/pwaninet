/**
 * Native App Enhancements - Capacitor-specific functionality
 * Only active when running in Capacitor native environment
 */

// Initialize native app enhancements
function initNativeAppEnhancements() {
    const isNative = window.hasOwnProperty('Capacitor');
    
    if (!isNative) {
        console.log('[NativeApp] Not running in native environment, skipping enhancements');
        return;
    }

    // Prevent duplicate initialization during HTMX swaps or manual re-runs
    if (window._pwaninet_native_initialized) {
        console.log('[NativeApp] Already initialized, skipping');
        return;
    }

    console.log('[NativeApp] Initializing native app enhancements');

    // Initialize instant button touch states
    initInstantTouchStates();
    
    // Initialize status bar
    initStatusBar();
    
    // Initialize caching
    initCaching();

    // Initialize back button handling
    initBackNavigation();

    // Initialize native media handling
    initNativeMedia();

    window._pwaninet_native_initialized = true;
}

/**
 * Instant button touch states - eliminates 300ms gesture delay
 */
function initInstantTouchStates() {
    // Select all clickable elements
    const clickableSelectors = ['.btn', '.btn-native', 'button'];
    
    // Use event delegation for better performance
    document.addEventListener('touchstart', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) {
            target.classList.add('activated');
        }
    }, { passive: true });

    document.addEventListener('touchend', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) {
            target.classList.remove('activated');
        }
    }, { passive: true });

    // Also handle touchcancel to remove activated state
    document.addEventListener('touchcancel', function(e) {
        const target = e.target.closest(clickableSelectors.join(','));
        if (target) {
            target.classList.remove('activated');
        }
    }, { passive: true });

    console.log('[NativeApp] Instant touch states initialized');
}

/**
 * Status bar integration with theme matching
 * Uses official Capacitor StatusBar plugin for transparency control
 * Handles both status bar (top) and navigation bar (bottom) on Android
 */
async function initStatusBar() {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.StatusBar) {
            console.error('[NativeApp] StatusBar plugin not available on window.Capacitor.Plugins');
            return;
        }
        const { StatusBar } = window.Capacitor.Plugins;

        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const initialStyle = currentTheme === 'light' ? 'LIGHT' : 'DARK';

        await StatusBar.setStyle({ style: initialStyle });
        await StatusBar.setBackgroundColor({ color: '#00000000' });
        await StatusBar.setOverlaysWebView({ overlay: true });

        console.log(`[NativeApp] StatusBar configured for edge-to-edge with initial style: ${initialStyle}`);

        await updateStatusBarForTheme(currentTheme);
        await updateNavigationBarForTheme(currentTheme);

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

    } catch (error) {
        console.error('[NativeApp] Failed to initialize status bar:', error);
    }
}

/**
 * Update status bar theme when theme changes
 * Uses official Capacitor StatusBar plugin for control
 * Handles both status bar (top) and navigation bar (bottom) on Android
 */
async function updateStatusBarForTheme(theme) {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.StatusBar) {
            console.error('[NativeApp] StatusBar plugin not available on window.Capacitor.Plugins');
            return;
        }
        const { StatusBar } = window.Capacitor.Plugins;

        const statusBarStyle = theme === 'light' ? 'LIGHT' : 'DARK';
        await StatusBar.setStyle({ style: statusBarStyle });
        await StatusBar.setBackgroundColor({ color: '#00000000' });
        await StatusBar.setOverlaysWebView({ overlay: true });

        console.log('[NativeApp] Status/navigation bars updated to:', theme, 'with style:', statusBarStyle);
    } catch (error) {
        console.error('[NativeApp] Failed to update status/navigation bars:', error);
    }
}

/**
 * Update navigation bar theme when theme changes
 * Uses community SafeArea plugin for Android navigation bar control
 * Sets navigation bar to transparent so app theme background shows through
 */
async function updateNavigationBarForTheme(theme) {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.SafeArea) {
            console.error('[NativeApp] SafeArea plugin not available on window.Capacitor.Plugins');
            return;
        }
        const { SafeArea } = window.Capacitor.Plugins;

        await SafeArea.enable({
            config: {
                customColorsForSystemBars: true,
                statusBarColor: '#00000000',
                statusBarContent: theme === 'light' ? 'dark' : 'light',
                // Transparent nav bar background — the app's own themed
                // background (bottom tab bar / page background) shows through
                // instead of a separate solid bar.
                navigationBarColor: '#00000000',
                navigationBarContent: theme === 'light' ? 'dark' : 'light',
            }
        });

        console.log('[NativeApp] Navigation bar updated to:', theme, '(transparent, icon content:', theme === 'light' ? 'dark' : 'light', ')');
    } catch (error) {
        console.error('[NativeApp] Failed to update navigation bar:', error);
    }
}

/**
 * Initialize caching for better performance
 */
function initCaching() {
    const isNative = window.hasOwnProperty('Capacitor');
    
    if (!isNative) {
        return;
    }

    console.log('[NativeApp] Initializing caching optimizations');

    // Enable localStorage caching for API responses
    try {
        // Cache user preferences
        const theme = localStorage.getItem('theme');
        const fontScale = localStorage.getItem('font_scale');
        const fontFamily = localStorage.getItem('font_family');
        const fontStyle = localStorage.getItem('font_style');
        
        console.log('[NativeApp] Cached preferences loaded:', { theme, fontScale, fontFamily, fontStyle });
        
        // Cache important session data
        if (window.PwaniNetUsername) {
            sessionStorage.setItem('username', window.PwaniNetUsername);
        }
        
    } catch (error) {
        console.error('[NativeApp] Failed to initialize caching:', error);
    }
}

/**
 * Native Media Handling (Camera/Gallery)
 * Provides bridges for Capacitor Camera plugin
 */
function initNativeMedia() {
    // Intercept file inputs that have capture="camera" or capture="environment"
    document.addEventListener('click', async (e) => {
        const target = e.target.closest('input[type="file"][capture]');
        if (target && window.Capacitor.Plugins.Camera) {
            e.preventDefault();
            console.log('[NativeApp] Intercepting camera capture input');

            try {
                const { Camera, CameraResultType, CameraSource } = window.Capacitor.Plugins;

                const image = await Camera.getPhoto({
                    quality: 90,
                    allowEditing: false,
                    resultType: CameraResultType.Uri,
                    source: CameraSource.Camera
                });

                // Convert URI to blob
                const response = await fetch(image.webPath);
                const blob = await response.blob();
                const file = new File([blob], `captured_image_${Date.now()}.jpg`, { type: 'image/jpeg' });

                // Trigger a change event on the target with the new file
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                target.files = dataTransfer.files;
                target.dispatchEvent(new Event('change', { bubbles: true }));

            } catch (error) {
                console.error('[NativeApp] Camera capture failed:', error);
                // If user cancelled, don't show error
                if (error.message !== 'User cancelled photos app') {
                    showNativeError('Camera Error', 'Could not access the camera. Please check your permissions.');
                }
            }
        }
    }, true);
}

/**
 * Show a native-friendly error notification
 */
function showNativeError(title, message) {
    // Try to use the application's existing status modal if available
    if (window.showStatusModal) {
        window.showStatusModal('error', title, message);
    } else {
        alert(`${title}: ${message}`);
    }
}

/**
 * Android Back Button Handling
 * Hierarchy: Overlays -> Browser History -> App Exit
 */
async function initBackNavigation() {
    try {
        if (!window.Capacitor || !window.Capacitor.Plugins || !window.Capacitor.Plugins.App) {
            console.error('[NativeApp] App plugin not available for back button handling');
            return;
        }

        const { App } = window.Capacitor.Plugins;

        App.addListener('backButton', async (data) => {
            console.log('[NativeApp] Back button pressed', data);

            // 1. Try to dismiss active overlays first
            const dismissed = dismissActiveOverlays();
            if (dismissed) {
                console.log('[NativeApp] Overlay dismissed, stopping back propagation');
                return;
            }

            // 2. Check browser history
            // We consider the root to be / or /home/
            const currentPath = window.location.pathname;
            const isRoot = currentPath === '/' || currentPath === '/home/';

            if (!isRoot && window.history.length > 1) {
                console.log('[NativeApp] Navigating back in browser history');
                window.history.back();
            } else {
                // 3. Exit the app if at root or no history
                console.log('[NativeApp] At root or no history, exiting app');
                await App.exitApp();
            }
        });

        console.log('[NativeApp] Back button listener initialized');
    } catch (error) {
        console.error('[NativeApp] Failed to initialize back navigation:', error);
    }
}

/**
 * Dismisses any active UI overlays
 * Returns true if an overlay was dismissed, false otherwise
 */
function dismissActiveOverlays() {
    let dismissed = false;

    // 1. Bootstrap Modals
    const activeModals = document.querySelectorAll('.modal.show, #pwaninetStatusModal.show');
    if (activeModals.length > 0) {
        activeModals.forEach(modalEl => {
            // Use Bootstrap API if available, otherwise manual hide
            if (window.bootstrap && window.bootstrap.Modal) {
                const modal = window.bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                    dismissed = true;
                }
            }

            // Fallback: trigger hidden events if manual hide is needed
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
    }

    // 2. Custom Overlays (Messaging, Voice, theme selector, etc.)
    const customOverlays = document.querySelectorAll('.overlay.show, .emoji-picker-modal.show, .attachment-modal.show, .voice-recording-preview.show, .context-menu.show, #themeModal.show, #voiceModal.show, #attachmentModal.show');
    if (customOverlays.length > 0) {
        customOverlays.forEach(overlay => {
            overlay.classList.remove('show');
            if (overlay.classList.contains('context-menu')) {
                overlay.style.display = 'none';
            }
            dismissed = true;
        });
        if (dismissed) return true;
    }

    // 3. Dropdowns
    const activeDropdowns = document.querySelectorAll('.dropdown-menu.show');
    if (activeDropdowns.length > 0) {
        activeDropdowns.forEach(dropdown => {
            dropdown.classList.remove('show');
            dismissed = true;
        });
        if (dismissed) return true;
    }

    return dismissed;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNativeAppEnhancements);
} else {
    initNativeAppEnhancements();
}