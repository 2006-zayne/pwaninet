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
 */
async function initStatusBar() {
    try {
        const { StatusBar } = await import('@capacitor/status-bar');

        // Get current theme
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';

        // Set status bar style based on theme
        await updateStatusBarForTheme(currentTheme);

        // Make status bar transparent to blend with app background
        const isAndroid = /android/i.test(navigator.userAgent);
        if (isAndroid) {
            await StatusBar.setBackgroundColor({ color: '#00000000' }); // Transparent
            console.log('[NativeApp] Status bar set to transparent');
        }

        // Debug logging for safe area insets
        setTimeout(() => {
            const safeAreaTop = getComputedStyle(document.documentElement).getPropertyValue('safe-area-inset-top');
            const navbar = document.querySelector('.navbar-top');
            if (navbar) {
                const navbarHeight = getComputedStyle(navbar).height;
                const navbarPaddingTop = getComputedStyle(navbar).paddingTop;
                console.log('[NativeApp] Debug - Safe area inset top:', safeAreaTop);
                console.log('[NativeApp] Debug - Navbar height:', navbarHeight);
                console.log('[NativeApp] Debug - Navbar padding top:', navbarPaddingTop);
                console.log('[NativeApp] Debug - Expected height calculation:', `calc(${safeAreaTop} + 80px)`);
            }
        }, 1000);

        // Listen for theme changes
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

    } catch (error) {
        console.error('[NativeApp] Failed to initialize status bar:', error);
    }
}

/**
 * Update status bar style when theme changes
 */
async function updateStatusBarForTheme(theme) {
    try {
        const { StatusBar } = await import('@capacitor/status-bar');
        
        if (theme === 'dark') {
            await StatusBar.setStyle({ style: 'Light' });
            console.log('[NativeApp] Status bar updated to Light style for dark theme');
        } else {
            await StatusBar.setStyle({ style: 'Dark' });
            console.log('[NativeApp] Status bar updated to Dark style for light theme');
        }
    } catch (error) {
        console.error('[NativeApp] Failed to update status bar style:', error);
    }
}

/**
 * Helper function to convert RGB color to hex
 */
function rgbToHex(rgb) {
    // Handle hex colors
    if (rgb.startsWith('#')) {
        return rgb;
    }
    
    // Handle rgb/rgba format
    const rgbMatch = rgb.match(/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*[\d.]+)?\)$/);
    if (rgbMatch) {
        const r = parseInt(rgbMatch[1], 16).toString(16).padStart(2, '0');
        const g = parseInt(rgbMatch[2], 16).toString(16).padStart(2, '0');
        const b = parseInt(rgbMatch[3], 16).toString(16).padStart(2, '0');
        return `#${r}${g}${b}`;
    }
    
    // Default fallback
    return '#2563eb';
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