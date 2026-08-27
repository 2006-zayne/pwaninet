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

    console.log('[NativeApp] Initializing native app enhancements');

    // Initialize instant button touch states
    initInstantTouchStates();
    
    // Initialize status bar
    initStatusBar();
    
    // Initialize caching
    initCaching();
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

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initNativeAppEnhancements);
} else {
    initNativeAppEnhancements();
}