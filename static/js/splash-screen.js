/**
 * PWA Splash Screen Manager
 * Handles splash screen display during app launch
 */

class SplashScreenManager {
    constructor() {
        this.splashElement = null;
        this.isLoading = true;
        this.minSplashTime = 1000; // Reduced to 1 second for snappier experience
        this.startTime = Date.now();
        
        this.init();
    }

    init() {
        // Check if we should show splash screen
        const pwaMode = this.isPWA();
        const fromLogin = this.isComingFromLogin();
        const debugMode = localStorage.getItem('debugSplashMode') === 'true';
        const forcePWA = localStorage.getItem('forcePWAMode') === 'true';
        const isDevelopment = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        
        // Enhanced detection for desktop PWA
        const shouldShow = pwaMode || forcePWA || (debugMode && isDevelopment);
        
        if (shouldShow) {
            console.log('Showing splash screen:', {
                pwaMode,
                debugMode,
                forcePWA,
                isDevelopment,
                fromLogin,
                reason: pwaMode ? 'PWA mode detected' : 
                        forcePWA ? 'PWA mode forced' : 
                        'Development debug mode'
            });
            
            if (fromLogin) {
                console.log('Coming from login, showing splash screen');
            }
            this.createSplashScreen();
            this.hideSplashWhenReady();
        } else {
            console.log('Not showing splash screen:', {
                pwaMode,
                debugMode,
                forcePWA,
                isDevelopment,
                reason: 'Not in PWA mode and debug mode disabled'
            });
        }
        
        // Enhanced PWA detection with debugging
        const displayMode = this.getDisplayMode();
        
        console.log('Splash Screen Init:', {
            pwaMode,
            displayMode,
            fromLogin,
            userAgent: navigator.userAgent,
            standalone: window.navigator.standalone,
            displayModeMatch: window.matchMedia('(display-mode: standalone)').matches,
            referrer: document.referrer,
            currentPath: window.location.pathname,
            alwaysShow: 'PWA launch always shows splash'
        });
        
        // Add debugging method to window
        window.debugSplashScreen = () => {
            console.log('Splash Screen Debug Info:', this.getSplashStatus());
        };
    }

    isComingFromLogin() {
        // Check if coming from login page or login-related URLs
        const referrer = document.referrer;
        const currentPath = window.location.pathname;
        
        // Check if referrer contains login-related paths
        const loginPaths = ['/login/', '/accounts/login/', '/auth/login/'];
        const isFromLogin = loginPaths.some(path => referrer.includes(path));
        
        // Check if current page is home page (after login redirect)
        const homePaths = ['/', '/home/', '/posts/', '/dashboard/'];
        const isHomePage = homePaths.some(path => currentPath === path || currentPath.startsWith(path));
        
        // Check URL parameters for login indicators
        const urlParams = new URLSearchParams(window.location.search);
        const hasLoginParam = urlParams.has('login') || urlParams.has('authenticated') || urlParams.has('from_login');
        
        // Check session storage for login state
        const justLoggedIn = sessionStorage.getItem('justLoggedIn') === 'true';
        
        return isFromLogin || (isHomePage && (hasLoginParam || justLoggedIn));
    }

    isPWA() {
        // Enhanced PWA detection for all platforms
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isIOSStandalone = window.navigator.standalone === true;
        const isAndroidApp = document.referrer.includes('android-app://');
        const isFromPWA = window.matchMedia('(display-mode: minimal-ui)').matches;
        const isFullscreen = window.matchMedia('(display-mode: fullscreen)').matches;
        
        // Check for desktop PWA indicators
        const isDesktopPWA = !window.matchMedia('(display-mode: browser)').matches && 
                             (isStandalone || isFromPWA || isFullscreen);
        
        // Check window properties for desktop PWA
        const hasDesktopPWAFeatures = window.outerHeight > window.innerHeight &&
                                     window.screenY === 0 &&
                                     window.screenX === 0;
        
        // Override for testing
        const forcePWA = localStorage.getItem('forcePWAMode') === 'true';
        
        // Check if native-pwa-install.js detected installation
        const pwaInstalled = localStorage.getItem('pwaInstalled') === 'true';
        
        const isPWA = isStandalone || isIOSStandalone || isAndroidApp || isDesktopPWA || 
                     hasDesktopPWAFeatures || forcePWA || pwaInstalled;
        
        console.log('PWA Detection Details:', {
            isStandalone,
            isIOSStandalone,
            isAndroidApp,
            isFromPWA,
            isFullscreen,
            isDesktopPWA,
            hasDesktopPWAFeatures,
            forcePWA,
            pwaInstalled,
            finalResult: isPWA
        });
        
        return isPWA;
    }

    getDisplayMode() {
        if (window.matchMedia('(display-mode: standalone)').matches) {
            return 'standalone';
        } else if (window.matchMedia('(display-mode: minimal-ui)').matches) {
            return 'minimal-ui';
        } else if (window.matchMedia('(display-mode: fullscreen)').matches) {
            return 'fullscreen';
        } else if (window.navigator.standalone) {
            return 'ios-standalone';
        } else {
            return 'browser';
        }
    }

    createSplashScreen() {
        // Create splash screen element
        this.splashElement = document.createElement('div');
        this.splashElement.id = 'pwa-splash-screen';
        this.splashElement.className = 'pwa-splash-screen';
        this.splashElement.innerHTML = `
            <div class="splash-content">
                <div class="splash-logo">
                    <img src="/static/images/web-app-manifest-192x192.png" alt="PwaniNet" class="splash-icon">
                </div>
                <div class="splash-text">
                    <h1 class="splash-title">PwaniNet</h1>
                    <p class="splash-subtitle">Campus Social Network</p>
                </div>
                <div class="splash-loader">
                    <div class="splash-spinner"></div>
                </div>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            .pwa-splash-screen {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: var(--splash-primary, linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%));
                color: var(--splash-text, white);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                opacity: 1;
                transform: translateY(0);
                pointer-events: none; /* Don't block interactions unless explicitly shown */
            }

            .pwa-splash-screen.show { pointer-events: auto; }

            /* Theme-aware splash screen colors */
            [data-theme="light"] .pwa-splash-screen {
                --splash-primary: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
                --splash-text: #ffffff;
                --splash-text-secondary: rgba(255, 255, 255, 0.9);
                --splash-icon-bg: rgba(255, 255, 255, 0.15);
            }

            [data-theme="dark"] .pwa-splash-screen {
                --splash-primary: linear-gradient(135deg, #18191f 0%, #242526 100%);
                --splash-text: #e4e6eb;
                --splash-text-secondary: rgba(228, 230, 235, 0.8);
                --splash-icon-bg: rgba(99, 102, 241, 0.2);
            }

            .splash-content {
                text-align: center;
                max-width: 300px;
                opacity: 1;
                transform: translateY(0);
            }

            .splash-logo {
                margin-bottom: 24px;
            }

            .splash-icon {
                width: 80px;
                height: 80px;
                border-radius: 20px;
                background: var(--splash-icon-bg, rgba(255, 255, 255, 0.15));
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                animation: pulse 2s ease-in-out infinite;
            }

            .splash-text {
                margin-bottom: 32px;
            }

            .splash-title {
                font-size: 32px;
                font-weight: 700;
                margin: 0 0 8px 0;
                letter-spacing: -0.5px;
                opacity: 1;
                transform: translateY(0);
                color: var(--splash-text, white);
            }

            .splash-subtitle {
                font-size: 16px;
                margin: 0;
                opacity: 0.8;
                transform: translateY(0);
                color: var(--splash-text-secondary, rgba(255, 255, 255, 0.9));
            }

            .splash-loader {
                opacity: 1;
                transform: translateY(0);
            }

            .splash-spinner {
                width: 32px;
                height: 32px;
                border: 3px solid var(--splash-text-secondary, rgba(255, 255, 255, 0.3));
                border-top: 3px solid var(--splash-text, white);
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto;
            }

            /* Animations */
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes slideUp {
                from {
                    transform: translateY(20px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            @keyframes fadeInUp {
                from {
                    transform: translateY(15px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            @keyframes pulse {
                0%, 100% {
                    transform: scale(1);
                    opacity: 1;
                }
                50% {
                    transform: scale(1.05);
                    opacity: 0.8;
                }
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            /* Hide splash screen */
            .pwa-splash-screen.hide {
                animation: fadeOut 0.3s ease forwards;
            }

            @keyframes fadeOut {
                from {
                    opacity: 1;
                }
                to {
                    opacity: 0;
                    pointer-events: none;
                }
            }

            /* Mobile optimizations */
            @media (max-width: 768px) {
                .splash-content {
                    max-width: 280px;
                }

                .splash-icon {
                    width: 64px;
                    height: 64px;
                    border-radius: 16px;
                }

                .splash-title {
                    font-size: 28px;
                }

                .splash-subtitle {
                    font-size: 14px;
                }

                .splash-spinner {
                    width: 28px;
                    height: 28px;
                    border-width: 2.5px;
                }
            }

            @media (max-width: 480px) {
                .splash-content {
                    max-width: 240px;
                }

                .splash-icon {
                    width: 56px;
                    height: 56px;
                    border-radius: 14px;
                }

                .splash-title {
                    font-size: 24px;
                }

                .splash-subtitle {
                    font-size: 13px;
                }

                .splash-spinner {
                    width: 24px;
                    height: 24px;
                    border-width: 2px;
                }
            }

            /* Landscape mode adjustments */
            @media (orientation: landscape) and (max-height: 600px) {
                .splash-content {
                    display: flex;
                    flex-direction: row;
                    align-items: center;
                    max-width: 400px;
                    gap: 24px;
                }

                .splash-logo {
                    margin-bottom: 0;
                    flex-shrink: 0;
                }

                .splash-icon {
                    width: 48px;
                    height: 48px;
                }

                .splash-text {
                    margin-bottom: 0;
                    text-align: left;
                    flex-shrink: 0;
                }

                .splash-title {
                    font-size: 24px;
                    margin-bottom: 4px;
                }

                .splash-subtitle {
                    font-size: 14px;
                }

                .splash-loader {
                    margin-left: auto;
                }

                .splash-spinner {
                    width: 24px;
                    height: 24px;
                    border-width: 2px;
                }
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(this.splashElement);
        this.splashElement.classList.add('show');
        // Prevent scrolling while splash is visible
        document.body.style.overflow = 'hidden';
    }

    hideSplashWhenReady() {
        // Check network connectivity during splash
        this.checkNetworkConnectivity();
        
        // Wait for minimum splash time and page to be ready
        const checkReady = () => {
            const elapsed = Date.now() - this.startTime;
            const pageReady = document.readyState === 'complete' && 
                             window.performance && 
                             window.performance.timing.loadEventEnd > 0;

            console.log('Splash readiness check:', {
                elapsed: Math.floor(elapsed / 1000) + 's',
                minTime: this.minSplashTime / 1000 + 's',
                pageReady,
                readyState: document.readyState,
                networkStatus: this.networkStatus
            });

            if (elapsed >= this.minSplashTime && pageReady) {
                if (this.networkStatus === 'offline') {
                    this.redirectToOffline();
                } else {
                    this.hideSplashScreen();
                }
            } else {
                // Check again in 100ms
                setTimeout(checkReady, 100);
            }
        };

        // Start checking immediately, but also ensure page load
        checkReady();
        
        if (document.readyState !== 'complete') {
            window.addEventListener('load', () => {
                console.log('Page loaded, checking splash readiness');
                checkReady();
            });
        }
        
        // Fallback: hide after 5 seconds max or redirect to offline
        setTimeout(() => {
            if (this.splashElement) {
                if (this.networkStatus === 'offline') {
                    console.log('Fallback: redirecting to offline page');
                    this.redirectToOffline();
                } else {
                    console.log('Fallback: hiding splash after 5 seconds');
                    this.hideSplashScreen();
                }
            }
        }, 5000);
    }

    checkNetworkConnectivity() {
        this.networkStatus = 'checking';
        
        // Quick initial check
        if (!navigator.onLine) {
            this.networkStatus = 'offline';
            console.log('Quick check: offline');
            return;
        }
        
        // More thorough check by fetching a small resource
        this.testNetworkConnection();
    }

    async testNetworkConnection() {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 3000);
            
            const response = await fetch('/static/images/favicon.ico', {
                method: 'HEAD',
                cache: 'no-cache',
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                this.networkStatus = 'online';
                console.log('Network check: online');
            } else {
                this.networkStatus = 'offline';
                console.log('Network check: offline (bad response)');
            }
        } catch (error) {
            this.networkStatus = 'offline';
            console.log('Network check: offline (error)', error.message);
        }
    }

    redirectToOffline() {
        console.log('Redirecting to offline page...');
        
        // Update splash to show offline state
        this.updateSplashForOffline();
        
        // Redirect after a short delay to show offline splash
        setTimeout(() => {
            window.location.href = '/offline/';
        }, 1500);
    }

    updateSplashForOffline() {
        if (!this.splashElement) return;
        
        // Update splash content to show offline state
        const splashContent = this.splashElement.querySelector('.splash-content');
        if (splashContent) {
            splashContent.innerHTML = `
                <div class="splash-logo">
                    <div class="offline-icon">
                        <i class="bi bi-wifi-off" style="font-size: 48px;"></i>
                    </div>
                </div>
                <div class="splash-text">
                    <h1 class="splash-title">No Internet Connection</h1>
                    <p class="splash-subtitle">Connecting to offline mode...</p>
                </div>
                <div class="splash-loader">
                    <div class="splash-spinner"></div>
                </div>
            `;
        }
        
        // Add offline styles with theme awareness
        const style = document.createElement('style');
        style.textContent = `
            .offline-icon {
                width: 80px;
                height: 80px;
                background: var(--splash-icon-bg, rgba(255, 255, 255, 0.15));
                border-radius: 20px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                animation: pulse 2s ease-in-out infinite;
            }
            
            .offline-icon i {
                color: var(--splash-text, white);
                opacity: 0.8;
            }
            
            .offline-title {
                color: var(--splash-text, white);
            }
            
            .offline-subtitle {
                color: var(--splash-text-secondary, rgba(255, 255, 255, 0.9));
            }
        `;
        document.head.appendChild(style);
    }

    hideSplashScreen() {
        if (!this.splashElement) return;

        console.log('Hiding splash screen');
        
        // Add hide animation
        this.splashElement.classList.remove('show');
        this.splashElement.classList.add('hide');
        
        // Remove element after animation
        setTimeout(() => {
            if (this.splashElement && this.splashElement.parentNode) {
                this.splashElement.parentNode.removeChild(this.splashElement);
                this.splashElement = null;
            }
            
            // Restore scrolling
            document.body.style.overflow = '';
            
            // Dispatch splash hidden event
            window.dispatchEvent(new CustomEvent('splashHidden'));
            
            console.log('Splash screen hidden');
        }, 300);
    }

    // Public API
    forceHideSplash() {
        this.hideSplashScreen();
    }

    forceShowSplash() {
        console.log('Force showing splash screen');
        this.createSplashScreen();
        
        // Auto-hide after 3 seconds for testing
        setTimeout(() => {
            this.hideSplashScreen();
        }, 3000);
    }

    getSplashStatus() {
        return {
            isVisible: !!this.splashElement,
            isPWA: this.isPWA(),
            displayMode: this.getDisplayMode(),
            elapsed: Date.now() - this.startTime,
            minTimeMet: (Date.now() - this.startTime) >= this.minSplashTime,
            networkStatus: this.networkStatus || 'unknown',
            fromLogin: this.isComingFromLogin(),
            userAgent: navigator.userAgent,
            standalone: window.navigator.standalone,
            displayModeMatch: window.matchMedia('(display-mode: standalone)').matches,
            navigatorOnline: navigator.onLine,
            currentPath: window.location.pathname,
            referrer: document.referrer
        };
    }
}

// Global instance
window.splashScreenManager = new SplashScreenManager();
