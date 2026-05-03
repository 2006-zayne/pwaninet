/**
 * PwaniNet PWA Startup Manager - Final Version
 * Strict launch detection with internet connectivity check
 */

class PwaniNetStartupFinal {
    constructor() {
        this.splashElement = null;
        this.appElement = null;
        this.startTime = performance.now();
        this.isOnline = navigator.onLine;
        this.initPromise = null;
        this.maxStartupTime = 30000; // 30 seconds max
        
        // Critical: Initialize immediately
        this.init();
    }

    async init() {
        console.log('🚀 PwaniNet Startup Manager initializing...');
        
        // Check if this is an absolute initial PWA launch
        const isInitialLaunch = this.isInitialLaunch();
        
        if (!isInitialLaunch) {
            console.log('📱 Subsequent navigation detected - skipping splash screen');
            // Show app immediately for any navigation after initial launch
            this.showMainApp();
            return;
        }
        
        console.log('🚀 Initial PWA launch detected - showing splash screen');
        
        // Create splash screen immediately (inline for performance)
        this.createSplashScreen();
        
        // Start boot process with internet connectivity check
        await this.bootAppWithConnectivityCheck();
    }

    createSplashScreen() {
        // Create splash element if not exists
        this.splashElement = document.getElementById('startup-splash');
        this.appElement = document.getElementById('app');
        
        if (!this.splashElement) {
            // Inject splash screen inline for instant render
            const splashHTML = `
                <div id="startup-splash">
                    <div class="splash-logo-container">
                        <div class="splash-logo">
                            <img src="/static/images/web-app-manifest-192x192.png" alt="PwaniNet" style="width: 100%; height: 100%; object-fit: cover; border-radius: 18px;">
                        </div>
                        <div class="splash-brand">PwaniNet</div>
                        <div class="splash-loading">
                            <div class="splash-dot"></div>
                            <div class="splash-dot"></div>
                            <div class="splash-dot"></div>
                        </div>
                        <div class="splash-text">Checking internet connectivity...</div>
                        <div class="splash-progress">
                            <div class="splash-progress-bar"></div>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('afterbegin', splashHTML);
            this.splashElement = document.getElementById('startup-splash');
        }
        
        // Hide main app initially
        if (this.appElement) {
            this.appElement.style.opacity = '0';
            this.appElement.style.pointerEvents = 'none';
        }
        
        console.log('✅ Splash screen created in', performance.now() - this.startTime, 'ms');
    }

    async bootAppWithConnectivityCheck() {
        console.log('🔄 Booting PwaniNet app with connectivity check...');
        
        try {
            // Step 1: Check internet connectivity FIRST
            await this.updateSplashText('Checking internet connectivity...');
            const hasInternet = await this.checkInternetConnectivity();
            
            if (!hasInternet) {
                console.log('📵 No internet connection - showing offline page');
                await this.updateSplashText('No internet connection');
                
                // Show offline screen instead of app
                setTimeout(() => {
                    window.location.href = '/offline/';
                }, 2000);
                return;
            }
            
            // Step 2: Internet confirmed - continue with app setup
            await this.updateSplashText('Internet confirmed - Loading app...');
            
            // Step 3: Load critical assets
            await this.loadCriticalAssets();
            
            // Step 4: Initialize authentication
            await this.initializeAuth();
            
            // Step 5: Register service worker
            await this.registerServiceWorker();
            
            // Step 6: Preload critical data
            await this.preloadCriticalData();
            
            // Step 7: Final setup
            await this.finalizeInitialization();
            
            // Step 8: Show app
            await this.hideSplashAndShowApp();
            
        } catch (error) {
            console.error('❌ App initialization failed:', error);
            await this.handleError(error);
        }
    }

    isInitialLaunch() {
        // STRICT: Only show splash on absolute initial PWA launch
        console.log('🔍 Checking for initial PWA launch...');
        
        // Check if we have a session storage flag for this session
        const sessionStarted = sessionStorage.getItem('pwaninet_session_started');
        
        // Check if this is PWA standalone mode
        const isPWAStandalone = window.matchMedia('(display-mode: standalone)').matches;
        
        // Check referrer - only external referrers count as fresh launch
        const referrer = document.referrer;
        const hasExternalReferrer = referrer && !referrer.includes(window.location.hostname);
        
        // Check navigation type
        const navigationEntries = performance.getEntriesByType('navigation');
        let isFirstNavigation = false;
        
        if (navigationEntries.length > 0) {
            const navigationType = navigationEntries[0].type;
            isFirstNavigation = navigationType === 'navigate';
        }
        
        // STRICT CRITERIA: Must be ALL of these for initial launch
        // 1. PWA standalone mode (launched from app drawer/home screen)
        // 2. No session flag (first time in this session)
        // 3. External referrer OR first navigation
        const isInitialLaunch = isPWAStandalone && 
                            !sessionStarted && 
                            (hasExternalReferrer || isFirstNavigation);
        
        if (isInitialLaunch) {
            // Set session flag to prevent future splashes
            sessionStorage.setItem('pwaninet_session_started', 'true');
            console.log('🚀 Initial PWA launch CONFIRMED:', {
                isPWAStandalone,
                hasExternalReferrer,
                isFirstNavigation,
                sessionStarted
            });
        } else {
            console.log('📱 Subsequent navigation CONFIRMED - skipping splash:', {
                isPWAStandalone,
                hasExternalReferrer,
                isFirstNavigation,
                sessionStarted,
                reason: !isPWAStandalone ? 'Not PWA standalone' : 
                       sessionStarted ? 'Session already started' : 
                       'Internal navigation'
            });
        }
        
        return isInitialLaunch;
    }

    async checkInternetConnectivity() {
        console.log('🌐 Checking internet connectivity...');
        
        try {
            // Test with a reliable endpoint and timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
            
            const response = await fetch('/api/health/', {
                method: 'HEAD',
                cache: 'no-cache',
                signal: controller.signal,
                headers: {
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                console.log('✅ Internet connectivity confirmed');
                return true;
            } else {
                console.log('❌ Internet connectivity failed');
                return false;
            }
            
        } catch (error) {
            console.log('❌ Connectivity check error:', error.message);
            return false;
        }
    }

    async updateSplashText(text) {
        const splashText = this.splashElement?.querySelector('.splash-text');
        if (splashText) {
            splashText.textContent = text;
            // Add subtle animation for text changes
            splashText.style.animation = 'none';
            setTimeout(() => {
                splashText.style.animation = 'pulse 0.5s ease-in-out';
            }, 10);
        }
    }

    showMainApp() {
        console.log('⚡ Showing main app immediately (subsequent navigation)');
        
        // Hide splash if it exists
        if (this.splashElement) {
            this.splashElement.style.display = 'none';
        }
        
        // Show main app immediately
        const appElement = document.getElementById('app');
        if (appElement) {
            appElement.style.opacity = '1';
            appElement.style.pointerEvents = 'auto';
            appElement.classList.add('show');
        }
        
        // Set session flag
        sessionStorage.setItem('pwaninet_session_started', 'true');
        
        // Dispatch ready event
        window.dispatchEvent(new CustomEvent('pwaninet:ready', {
            detail: { startupTime: 0, isSubsequentNavigation: true }
        }));
    }

    async loadCriticalAssets() {
        console.log('📦 Loading critical assets...');
        
        // Preload critical CSS with timeout
        const criticalCSS = [
            '/static/css/splash.css',
            '/static/css/bootstrap.min.css',
            '/static/css/custom.css'
        ];
        
        const cssPromises = criticalCSS.map(url => 
            Promise.race([
                this.preloadResource(url, 'style'),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000)
            ])
        );
        
        // Preload critical JS with timeout
        const criticalJS = [
            '/static/js/bootstrap.bundle.min.js',
            '/static/js/htmx.min.js'
        ];
        
        const jsPromises = criticalJS.map(url => 
            Promise.race([
                this.preloadResource(url, 'script'),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 5000)
            ])
        );
        
        try {
            await Promise.allSettled([...cssPromises, ...jsPromises]);
            console.log('✅ Critical assets loaded');
        } catch (error) {
            console.log('⚠️ Some assets failed to load:', error.message);
        }
    }

    async initializeAuth() {
        console.log('🔐 Initializing authentication...');
        
        // Check if user is authenticated with timeout
        try {
            const response = await Promise.race([
                fetch('/api/auth/status/', {
                    method: 'GET',
                    credentials: 'include',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                }),
                new Promise((_, reject) => setTimeout(() => reject(new Error('Auth timeout')), 5000)
            ]);
            
            if (response.ok) {
                const authData = await response.json();
                console.log('✅ Authentication status:', authData.authenticated ? 'authenticated' : 'anonymous');
            }
        } catch (error) {
            console.log('⚠️ Auth check failed, continuing anyway:', error.message);
        }
    }

    async registerServiceWorker() {
        console.log('🔧 Registering service worker...');
        
        if ('serviceWorker' in navigator) {
            try {
                const registration = await Promise.race([
                    navigator.serviceWorker.register('/static/service-worker.js'),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('SW timeout')), 5000)
                ]);
                console.log('✅ Service worker registered:', registration.scope);
                
                // Wait for service worker to be active with timeout
                if (registration.installing) {
                    await Promise.race([
                        new Promise(resolve => {
                            registration.installing.addEventListener('statechange', (e) => {
                                if (e.target.state === 'activated') {
                                    resolve();
                                }
                            });
                        }),
                        new Promise((_, reject) => setTimeout(() => reject(new Error('SW activation timeout')), 10000)
                    ]);
                }
                
            } catch (error) {
                console.log('⚠️ Service worker registration failed:', error.message);
            }
        } else {
            console.log('⚠️ Service worker not supported');
        }
    }

    async preloadCriticalData() {
        console.log('📊 Preloading critical data...');
        
        // Preload user data if authenticated with timeout
        try {
            const criticalData = [
                '/api/user/profile/',
                '/api/posts/feed/',
                '/static/images/favicon-96x96.png'
            ];
            
            const dataPromises = criticalData.map(url => 
                Promise.race([
                    fetch(url, { 
                        method: 'HEAD',
                        credentials: 'include',
                        cache: 'force-cache'
                    }).catch(() => null),
                    new Promise((_, reject) => setTimeout(() => reject(new Error('Data timeout')), 3000)
                ])
            );
            
            await Promise.allSettled(dataPromises);
            console.log('✅ Critical data preloaded');
            
        } catch (error) {
            console.log('⚠️ Data preloading failed:', error.message);
        }
    }

    async finalizeInitialization() {
        console.log('🎯 Finalizing initialization...');
        
        // Wait minimum splash time for UX
        const minSplashTime = 1500; // 1.5 seconds
        const elapsed = performance.now() - this.startTime;
        const remainingTime = Math.max(0, minSplashTime - elapsed);
        
        if (remainingTime > 0) {
            await new Promise(resolve => setTimeout(resolve, remainingTime));
        }
        
        // Final online check
        this.isOnline = navigator.onLine;
        
        console.log('✅ Initialization complete in', performance.now() - this.startTime, 'ms');
    }

    async hideSplashAndShowApp() {
        console.log('🎬 Transitioning to main app...');
        
        // Fade out splash
        if (this.splashElement) {
            this.splashElement.classList.add('fade-out');
            
            // Wait for fade animation
            await new Promise(resolve => setTimeout(resolve, 300));
            
            // Remove splash element
            this.splashElement.remove();
        }
        
        // Show main app
        if (this.appElement) {
            this.appElement.style.opacity = '1';
            this.appElement.style.pointerEvents = 'auto';
            this.appElement.classList.add('show');
        }
        
        console.log('✅ App ready! Total startup time:', performance.now() - this.startTime, 'ms');
        
        // Dispatch ready event
        window.dispatchEvent(new CustomEvent('pwaninet:ready', {
            detail: { startupTime: performance.now() - this.startTime }
        }));
    }

    async showOfflinePage() {
        console.log('📵 Showing offline page...');
        
        // Update splash for offline
        await this.updateSplashText('You are offline');
        
        const splashDots = this.splashElement.querySelector('.splash-loading');
        const progressBar = this.splashElement.querySelector('.splash-progress');
        
        if (splashDots) {
            splashDots.innerHTML = '<div class="splash-offline-icon">📵</div>';
            splashDots.style.display = 'flex';
        }
        if (progressBar) progressBar.style.display = 'none';
        
        // Navigate to offline page after brief delay
        setTimeout(() => {
            window.location.href = '/offline/';
        }, 2000);
    }

    async handleError(error) {
        console.error('❌ Startup error:', error);
        
        // Show error state in splash
        const splashText = this.splashElement?.querySelector('.splash-text');
        const splashDots = this.splashElement.querySelector('.splash-loading');
        
        if (splashText) {
            splashText.textContent = 'Something went wrong';
            splashText.classList.add('error');
        }
        if (splashDots) {
            splashDots.innerHTML = '<div class="splash-offline-icon">⚠️</div>';
        }
        
        // Try to continue to app after delay
        setTimeout(() => {
            this.hideSplashAndShowApp();
        }, 3000);
    }

    // Utility methods
    preloadResource(url, type) {
        return new Promise((resolve, reject) => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.href = url;
            link.as = type;
            
            if (type === 'style') {
                link.onload = resolve;
                link.onerror = reject;
            } else if (type === 'script') {
                const script = document.createElement('script');
                script.src = url;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
                return;
            }
            
            document.head.appendChild(link);
        });
    }
}

// Auto-initialize on DOM content ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaninetStartupFinal = new PwaniNetStartupFinal();
    });
} else {
    // Already loaded
    window.pwaninetStartupFinal = new PwaniNetStartupFinal();
}

// Handle online/offline events
window.addEventListener('online', () => {
    console.log('🌐 Back online!');
    if (window.pwaninetStartupFinal) {
        window.pwaninetStartupFinal.isOnline = true;
    }
});

window.addEventListener('offline', () => {
    console.log('📵 Gone offline!');
    if (window.pwaninetStartupFinal) {
        window.pwaninetStartupFinal.isOnline = false;
    }
});

// Export for global access
window.PwaniNetStartupFinal = PwaniNetStartupFinal;
