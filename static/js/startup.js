/**
 * PwaniNet PWA Startup Manager
 * Facebook-style splash screen with premium animations
 * Handles app initialization, offline detection, and smooth transitions
 */

class PwaniNetStartup {
    constructor() {
        this.splashElement = null;
        this.appElement = null;
        this.startTime = performance.now();
        this.isOnline = navigator.onLine;
        this.initPromise = null;
        
        // Critical: Initialize immediately
        this.init();
    }

    async init() {
        console.log('🚀 PwaniNet Startup Manager initializing...');
        
        // Check if this is a fresh launch vs refresh
        const isFreshLaunch = this.isFreshLaunch();
        
        if (!isFreshLaunch) {
            console.log('🔄 Page refresh detected - skipping splash screen');
            // Show app immediately for refreshes
            this.showMainApp();
            return;
        }
        
        console.log('🚀 Fresh PWA launch detected - showing splash screen');
        
        // Create splash screen immediately (inline for performance)
        this.createSplashScreen();
        
        // Start boot process
        await this.bootApp();
    }

    isFreshLaunch() {
        // Check if this is a fresh PWA launch vs page refresh
        const navigationEntries = performance.getEntriesByType('navigation');
        
        if (navigationEntries.length > 0) {
            const navigationType = navigationEntries[0].type;
            
            // Check navigation types that indicate fresh launch
            const isFreshNavigation = navigationType === 'navigate' || 
                                   navigationType === 'reload';
            
            // Check if we have a session storage flag for this session
            const sessionStarted = sessionStorage.getItem('pwaninet_session_started');
            
            // Additional checks for PWA launch
            const isPWAStandalone = window.matchMedia('(display-mode: standalone)').matches;
            const referrer = document.referrer;
            const hasValidReferrer = referrer && !referrer.includes(window.location.hostname);
            
            // Consider it fresh if:
            // 1. It's a fresh navigation (navigate or reload)
            // 2. It's a PWA standalone launch
            // 3. It has an external referrer (coming from outside)
            // NOTE: Always show splash on PWA launch regardless of session flag
            const isFresh = isFreshNavigation || 
                           isPWAStandalone || 
                           hasValidReferrer;
            
            if (isFresh) {
                // Set session flag
                sessionStorage.setItem('pwaninet_session_started', 'true');
                console.log('🚀 Fresh launch detected:', {
                    navigationType,
                    isPWAStandalone,
                    hasValidReferrer,
                    sessionStarted
                });
            } else {
                console.log('🔄 Refresh detected:', {
                    navigationType,
                    isPWAStandalone,
                    hasValidReferrer,
                    sessionStarted
                });
            }
            
            return isFresh;
        }
        
        // Fallback: assume fresh if we can't determine
        return !sessionStorage.getItem('pwaninet_session_started');
    }

    showMainApp() {
        console.log('⚡ Showing main app immediately (refresh mode)');
        
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
            detail: { startupTime: 0, isRefresh: true }
        }));
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
                        <div class="splash-logo">📱</div>
                        <div class="splash-brand">PwaniNet</div>
                        <div class="splash-loading">
                            <div class="splash-dot"></div>
                            <div class="splash-dot"></div>
                            <div class="splash-dot"></div>
                        </div>
                        <div class="splash-text">Loading your campus network...</div>
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

    async bootApp() {
        console.log('🔄 Booting PwaniNet app...');
        
        // Start with basic loading
        await this.updateSplashText('Initializing app...');
        
        // Load critical assets first
        await this.loadCriticalAssets();
        await this.updateSplashText('Loading resources...');
        
        // Check network status with progressive attempts FIRST
        console.log('🌐 Checking internet connectivity before showing app...');
        const networkAvailable = await this.checkNetworkStatus();
        
        if (!networkAvailable) {
            console.log('📵 No internet connection - showing offline page');
            await this.updateSplashText('No internet connection');
            await new Promise(resolve => setTimeout(resolve, 2000)); // Brief pause
            await this.showOfflinePage();
            return;
        }
        
        // Internet confirmed - continue with app setup
        await this.updateSplashText('Internet confirmed - Setting up your experience...');
        
        // Parallel initialization for performance
        const initTasks = [
            this.initializeAuth(),
            this.registerServiceWorker(),
            this.preloadCriticalData()
        ];

        await this.updateSplashText('Finalizing setup...');
        await Promise.allSettled(initTasks);
        
        // Final checks
        await this.finalizeInitialization();
        
        // Hide splash and show app
        await this.hideSplashAndShowApp();
        
    } catch (error) {
        console.error('❌ App initialization failed:', error);
        await this.handleError(error);
    }
}

    async loadCriticalAssets() {
        console.log('📦 Loading critical assets...');
        
        // Preload critical CSS
        const criticalCSS = [
            '/static/css/splash.css',
            '/static/css/bootstrap.min.css',
            '/static/css/custom.css'
        ];
        
        const cssPromises = criticalCSS.map(url => 
            this.preloadResource(url, 'style')
        );
        
        // Preload critical JS
        const criticalJS = [
            '/static/js/bootstrap.bundle.min.js',
            '/static/js/htmx.min.js'
        ];
        
        const jsPromises = criticalJS.map(url => 
            this.preloadResource(url, 'script')
        );
        
        await Promise.allSettled([...cssPromises, ...jsPromises]);
        console.log('✅ Critical assets loaded');
    }

    async initializeAuth() {
        console.log('🔐 Initializing authentication...');
        
        // Check if user is authenticated
        try {
            const response = await fetch('/api/auth/status/', {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
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
                const registration = await navigator.serviceWorker.register('/service-worker.js');
                console.log('✅ Service worker registered:', registration.scope);
                
                // Wait for service worker to be active
                if (registration.installing) {
                    await new Promise(resolve => {
                        registration.installing.addEventListener('statechange', (e) => {
                            if (e.target.state === 'activated') {
                                resolve();
                            }
                        });
                    });
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
        
        // Preload user data if authenticated
        try {
            const criticalData = [
                '/api/user/profile/',
                '/api/posts/feed/',
                '/static/images/favicon-96x96.png'
            ];
            
            const dataPromises = criticalData.map(url => 
                fetch(url, { 
                    method: 'HEAD',
                    credentials: 'include',
                    cache: 'force-cache'
                }).catch(() => null)
            );
            
            await Promise.allSettled(dataPromises);
            console.log('✅ Critical data preloaded');
            
        } catch (error) {
            console.log('⚠️ Data preloading failed:', error.message);
        }
    }

    async checkNetworkStatus() {
        console.log('🌐 Checking network status with progressive attempts...');
        
        const maxAttempts = 3;
        const timeouts = [3000, 5000, 7000]; // Progressive timeouts
        let attempt = 0;
        
        return new Promise(async (resolve) => {
            // First check if navigator thinks we're online
            if (!navigator.onLine) {
                console.log('📵 Navigator reports offline');
                this.isOnline = false;
                resolve(false);
                return;
            }
            
            // Progressive connection attempts
            while (attempt < maxAttempts) {
                attempt++;
                const timeout = timeouts[attempt - 1];
                
                console.log(`🔗 Connection attempt ${attempt}/${maxAttempts} (${timeout}ms timeout)`);
                await this.updateSplashText(`Connecting to network... (${attempt}/${maxAttempts})`);
                
                try {
                    // Test connectivity with increasing timeouts
                    const response = await fetch('/api/health/', { 
                        method: 'HEAD',
                        cache: 'no-cache',
                        signal: AbortSignal.timeout(timeout)
                    });
                    
                    if (response.ok) {
                        console.log('✅ Network connection confirmed');
                        this.isOnline = true;
                        await this.updateSplashText('Connection established!');
                        resolve(true);
                        return;
                    }
                } catch (error) {
                    console.log(`⚠️ Connection attempt ${attempt} failed:`, error.message);
                    
                    if (attempt < maxAttempts) {
                        // Wait before next attempt
                        await this.updateSplashText(`Retrying... (${attempt}/${maxAttempts})`);
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            }
            
            // All attempts failed
            console.log('❌ All connection attempts failed');
            this.isOnline = false;
            await this.updateSplashText('Unable to connect');
            resolve(false);
        });
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

    async showOfflinePage() {
        console.log('📵 Showing offline page...');
        
        // Update splash for offline
        await this.updateSplashText('You\'re offline');
        
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
        const splashText = this.splashElement.querySelector('.splash-text');
        const splashDots = this.splashElement.querySelector('.splash-loading');
        
        if (splashText) splashText.textContent = 'Something went wrong';
        if (splashDots) splashDots.innerHTML = '<div style="color: #ef4444;">⚠️</div>';
        
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
                link.onload = resolve;
                link.onerror = reject;
            }
            
            document.head.appendChild(link);
        });
    }

    // Public methods
    async restart() {
        console.log('🔄 Restarting PwaniNet...');
        await this.bootApp();
    }

    getStartupTime() {
        return performance.now() - this.startTime;
    }
}

// Auto-initialize on DOM content ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.pwaninetStartup = new PwaniNetStartup();
    });
} else {
    // Already loaded
    window.pwaninetStartup = new PwaniNetStartup();
}

// Handle online/offline events
window.addEventListener('online', () => {
    console.log('🌐 Back online!');
    if (window.pwaninetStartup) {
        window.pwaninetStartup.isOnline = true;
    }
});

window.addEventListener('offline', () => {
    console.log('📵 Gone offline!');
    if (window.pwaninetStartup) {
        window.pwaninetStartup.isOnline = false;
    }
});

// Export for global access
window.PwaniNetStartup = PwaniNetStartup;
