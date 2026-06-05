/**
 * PwaniNet PWA Startup Manager - Clean Version
 * No loops. No hanging. Simple and robust.
 */

(function() {
    'use strict';
    
    const SESSION_KEY = 'pwaninet_launched';

    function isAuthPage() {
        const path = window.location.pathname;
        return path.startsWith('/accounts/') || path.endsWith('/register/');
    }

    // Check if this is a fresh PWA launch
    function isFreshLaunch() {
        const alreadyLaunched = sessionStorage.getItem(SESSION_KEY);
        const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
        const isIOS = window.navigator.standalone === true;
        const isPWA = isStandalone || isIOS;
        
        // Show splash if: PWA mode OR first page load (not already launched this session)
        const fresh = !alreadyLaunched;
        
        if (fresh) {
            sessionStorage.setItem(SESSION_KEY, 'true');
            console.log('🚀 Fresh launch - showing splash', { isPWA });
        } else {
            console.log('📱 Not a fresh launch - skipping splash', {
                isPWA, alreadyLaunched
            });
        }
        
        return fresh;
    }
    
    // Show app immediately (no splash) - for non-fresh launches
    function showAppImmediately() {
        var splash = document.getElementById('startup-splash');
        var app = document.getElementById('app');
        
        // Just make sure splash is hidden and app is visible
        if (splash) {
            splash.classList.remove('show-splash');
            splash.style.display = 'none';
        }
        if (app) {
            app.classList.remove('hide-for-splash');
            app.style.opacity = '1';
            app.style.pointerEvents = 'auto';
        }
    }
    
    // Update splash text
    function setSplashText(text) {
        const el = document.querySelector('#startup-splash .splash-text');
        if (el) el.textContent = text;
    }
    
    // Check internet with synchronized progress bar updates
    function checkInternetWithProgress() {
        return new Promise(function(resolve) {
            var attempts = 0;
            var maxAttempts = 3;
            var timeouts = [4000, 6000, 8000];
            var progressTargets = [60, 70, 80]; // Progress targets for each attempt
            
            function tryConnect() {
                attempts++;
                var timeout = timeouts[attempts - 1];
                var targetProgress = progressTargets[attempts - 1];
                
                // Update text and progress for this attempt
                if (attempts === 1) {
                    setSplashText('Connecting to server...');
                    animateProgress(20, targetProgress, timeout - 500); // Reach target just before timeout
                } else if (attempts === 2) {
                    setSplashText('Connection slow, retrying...');
                    animateProgress(60, targetProgress, timeout - 500);
                    var dots = document.querySelectorAll('#startup-splash .splash-dot');
                    dots.forEach(function(d) { d.style.animationDuration = '2s'; });
                } else if (attempts === 3) {
                    setSplashText('Still trying to connect...');
                    animateProgress(70, targetProgress, timeout - 500);
                    var dots2 = document.querySelectorAll('#startup-splash .splash-dot');
                    dots2.forEach(function(d) { d.style.animationDuration = '3s'; });
                }
                
                var attemptTimeout = setTimeout(function() {
                    if (attempts < maxAttempts) {
                        tryConnect();
                    } else {
                        resolve(false);
                    }
                }, timeout);
                
                fetch('/static/images/favicon.ico', {
                    method: 'HEAD',
                    cache: 'no-cache'
                }).then(function(response) {
                    clearTimeout(attemptTimeout);
                    
                    if (response.ok) {
                        // Success - jump to 80% then we'll go to 100% in main flow
                        setProgress(80);
                        if (attempts === 1) {
                            setSplashText('Connected!');
                        } else {
                            setSplashText('Connection restored!');
                        }
                        resolve(true);
                    } else {
                        clearTimeout(attemptTimeout);
                        if (attempts < maxAttempts) {
                            tryConnect();
                        } else {
                            resolve(false);
                        }
                    }
                }).catch(function() {
                    clearTimeout(attemptTimeout);
                    if (attempts < maxAttempts) {
                        tryConnect();
                    } else {
                        resolve(false);
                    }
                });
            }
            
            tryConnect();
        });
    }
    
    // Animate progress bar from start to end over duration
    function animateProgress(start, end, duration) {
        var startTime = Date.now();
        var diff = end - start;
        
        function update() {
            var elapsed = Date.now() - startTime;
            var progress = Math.min(elapsed / duration, 1);
            var current = start + (diff * progress);
            
            setProgress(Math.round(current));
            
            if (progress < 1) {
                requestAnimationFrame(update);
            }
        }
        
        requestAnimationFrame(update);
    }
    
    // Fill progress bar to a percentage
    function setProgress(pct) {
        var bar = document.querySelector('#startup-splash .splash-progress-bar');
        if (bar) bar.style.width = pct + '%';
    }
    
    // Fade out splash and show app - ONLY when bar is 100%
    function transitionToApp() {
        // First: fill bar to 100%
        setProgress(100);
        setSplashText('Ready!');
        
        // Wait for bar to visually reach 100%, then transition
        setTimeout(function() {
            var splash = document.getElementById('startup-splash');
            var app = document.getElementById('app');
            
            if (splash) {
                splash.classList.remove('show-splash');
                splash.classList.add('fade-out');
                setTimeout(function() {
                    if (splash.parentNode) splash.parentNode.removeChild(splash);
                }, 400);
            }
            
            if (app) {
                app.classList.remove('hide-for-splash');
                app.style.opacity = '1';
                app.style.pointerEvents = 'auto';
            }
            
            console.log('✅ App ready');
        }, 400);
    }
    
    // Go to skeleton screen instead of offline page
    function goToOffline() {
        setSplashText('No internet connection');
        
        // Wait a moment then transition to skeleton
        setTimeout(function() {
            var splash = document.getElementById('startup-splash');
            if (splash && splash.parentNode) splash.parentNode.removeChild(splash);
            
            // Show the Facebook-style skeleton overlay
            if (window.PwaniNetOfflineSkeleton) {
                window.PwaniNetOfflineSkeleton.show();
            }
            
            // Show the app behind the skeleton so it can load cached content
            var app = document.getElementById('app');
            if (app) {
                app.classList.remove('hide-for-splash');
                app.style.opacity = '1';
                app.style.pointerEvents = 'auto';
            }
        }, 1500);
    }
    
    // Main startup flow
    async function startUp() {
        if (sessionStorage.getItem('showLoginWelcome') === 'true') {
            showAppImmediately();
            return;
        }

        if (isAuthPage()) {
            showAppImmediately();
            return;
        }

        // Step 1: Is this a fresh PWA launch?
        if (!isFreshLaunch()) {
            showAppImmediately();
            return;
        }
        
        // Step 2: Check if splash already visible from inline script, otherwise show it
        var splash = document.getElementById('startup-splash');
        var app = document.getElementById('app');
        var splashAlreadyVisible = splash && getComputedStyle(splash).opacity === '1';
        
        if (!splashAlreadyVisible && splash) splash.classList.add('show-splash');
        if (!splashAlreadyVisible && app) app.classList.add('hide-for-splash');
        setProgress(0);
        
        // Step 3: Check internet with synchronized progress updates
        setProgress(20);
        var hasInternet = await checkInternetWithProgress();
        
        if (!hasInternet) {
            setProgress(30); // Bar stays partial on failure
            goToOffline();
            return;
        }
        
        // Step 4: Internet confirmed - fill to 80%
        setProgress(80);
        setSplashText('Connected!');
        
        // Brief pause so user sees "Connected!"
        await new Promise(function(r) { setTimeout(r, 500); });
        
        // Step 5: Transition to app (fills bar to 100% first)
        transitionToApp();
    }
    
    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startUp);
    } else {
        startUp();
    }
    
})();
