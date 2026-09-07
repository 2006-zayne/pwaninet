/**
 * PwaniNet Navigation Progress Bar
 * Shows a subtle progress indicator during page navigation
 */

(function() {
    'use strict';

    let progressStartTime = null;
    let progressTimeout = null;
    let progressAnimationId = null;
    let currentProgress = 0;
    const PROGRESS_THRESHOLD = 150; // ms - don't show for very fast navigations

    function startNavigationProgress() {
        const progressContainer = document.getElementById('navigation-progress');
        const progressBar = document.getElementById('navigation-progress-bar');
        
        if (!progressContainer || !progressBar) {
            console.warn('[NavigationProgress] Progress bar elements not found');
            return;
        }

        // Reset state
        currentProgress = 0;
        progressBar.style.width = '0%';
        progressBar.style.opacity = '0';
        progressContainer.classList.remove('active', 'completing');
        
        // Start timer for threshold check
        progressStartTime = Date.now();
        
        // Clear any existing timeout
        if (progressTimeout) {
            clearTimeout(progressTimeout);
        }
        
        // Cancel any existing animation
        if (progressAnimationId) {
            cancelAnimationFrame(progressAnimationId);
        }

        // Wait for threshold before showing
        progressTimeout = setTimeout(() => {
            progressContainer.classList.add('active');
            progressBar.style.opacity = '1';
            animateProgress();
        }, PROGRESS_THRESHOLD);
        
        console.log('[NavigationProgress] Started (will show after', PROGRESS_THRESHOLD, 'ms)');
    }

    function animateProgress() {
        const progressBar = document.getElementById('navigation-progress-bar');
        if (!progressBar) return;

        // Simulated progress: quick to 60-70%, then slow
        if (currentProgress < 60) {
            // Quick initial progress
            currentProgress += Math.random() * 15 + 5; // 5-20% increments
        } else if (currentProgress < 70) {
            // Slow down as we approach 70%
            currentProgress += Math.random() * 3 + 1; // 1-4% increments
        } else {
            // Hold at 70% until completion
            currentProgress = 70;
        }

        // Cap at 70% during waiting phase
        if (currentProgress > 70) {
            currentProgress = 70;
        }

        progressBar.style.width = currentProgress + '%';

        // Continue animation if not completing
        if (currentProgress < 70) {
            progressAnimationId = requestAnimationFrame(animateProgress);
        }
    }

    function completeNavigationProgress() {
        const progressContainer = document.getElementById('navigation-progress');
        const progressBar = document.getElementById('navigation-progress-bar');
        
        if (!progressContainer || !progressBar) return;

        // Clear timeout and animation
        if (progressTimeout) {
            clearTimeout(progressTimeout);
            progressTimeout = null;
        }
        
        if (progressAnimationId) {
            cancelAnimationFrame(progressAnimationId);
            progressAnimationId = null;
        }

        // If we haven't shown the bar yet (below threshold), just hide
        if (!progressContainer.classList.contains('active')) {
            console.log('[NavigationProgress] Completed before threshold, no visible flash');
            progressBar.style.width = '0%';
            return;
        }

        // Animate to completion
        progressContainer.classList.add('completing');
        currentProgress = 85;
        progressBar.style.width = '85%';

        // Quick transition to 100%
        setTimeout(() => {
            currentProgress = 100;
            progressBar.style.width = '100%';
        }, 100);

        // Fade out and hide
        setTimeout(() => {
            progressBar.style.opacity = '0';
            setTimeout(() => {
                progressBar.style.width = '0%';
                progressContainer.classList.remove('active', 'completing');
            }, 300);
        }, 200);

        console.log('[NavigationProgress] Completed');
    }

    function cancelNavigationProgress() {
        const progressContainer = document.getElementById('navigation-progress');
        const progressBar = document.getElementById('navigation-progress-bar');
        
        if (!progressContainer || !progressBar) return;

        // Clear timeout and animation
        if (progressTimeout) {
            clearTimeout(progressTimeout);
            progressTimeout = null;
        }
        
        if (progressAnimationId) {
            cancelAnimationFrame(progressAnimationId);
            progressAnimationId = null;
        }

        // Hide immediately
        progressBar.style.opacity = '0';
        progressBar.style.width = '0%';
        progressContainer.classList.remove('active', 'completing');
        
        console.log('[NavigationProgress] Cancelled');
    }

    // Intercept navigation to start progress bar.
    // Only fires for genuine full-page navigations (href links NOT managed by HTMX).
    // HTMX-managed navigation is handled separately via htmx events.
    function interceptNavigation() {
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            if (!link) return;

            const href = link.getAttribute('href');

            // Skip non-navigating links
            if (!href ||
                href.startsWith('#') ||
                href.startsWith('javascript:') ||
                link.getAttribute('target') === '_blank' ||
                link.getAttribute('target') === 'pwaninet-download-target' ||
                link.hasAttribute('download') ||
                link.dataset.apkDownload) {
                return;
            }

            // Skip HTMX-enhanced links — htmx:beforeRequest handles those
            if (link.hasAttribute('hx-get') ||
                link.hasAttribute('hx-post') ||
                link.hasAttribute('hx-put') ||
                link.hasAttribute('hx-delete') ||
                link.hasAttribute('hx-patch') ||
                link.closest('[hx-boost="true"]') ||
                link.closest('[data-hx-boost="true"]')) {
                return;
            }

            // Skip modifier keys (open in new tab, etc.)
            if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
                return;
            }

            // Skip external links
            const isSameOrigin = href.startsWith('/') || href.startsWith(window.location.origin);
            if (!isSameOrigin) return;

            console.log('[NavigationProgress] Full-page navigation detected to:', href);
            startNavigationProgress();
        });
    }

    // Hook HTMX lifecycle — this is the primary path for HTMX SPA navigation
    function hookHtmxEvents() {
        // Start bar when any HTMX request kicks off
        document.addEventListener('htmx:beforeRequest', function(evt) {
            // Only show for main page-content swaps, not small partial fetches
            const target = evt.detail && evt.detail.target;
            const isPageNav = target && (
                target.id === 'page-content-target' ||
                target.id === 'main-content' ||
                target.id === 'content'
            );
            if (isPageNav) {
                console.log('[NavigationProgress] HTMX request starting');
                startNavigationProgress();
            }
        });

        // Complete bar on successful HTMX swap
        document.addEventListener('htmx:afterSwap', function(evt) {
            const target = evt.detail && evt.detail.target;
            const isPageNav = target && (
                target.id === 'page-content-target' ||
                target.id === 'main-content' ||
                target.id === 'content'
            );
            if (isPageNav) {
                console.log('[NavigationProgress] HTMX swap completed');
                completeNavigationProgress();
            }
        });

        // Cancel bar on HTMX errors
        document.addEventListener('htmx:responseError', function() {
            console.warn('[NavigationProgress] HTMX response error, cancelling progress');
            cancelNavigationProgress();
        });

        document.addEventListener('htmx:sendError', function() {
            console.warn('[NavigationProgress] HTMX send error, cancelling progress');
            cancelNavigationProgress();
        });

        // Complete bar on HTMX history restore
        document.addEventListener('htmx:historyRestore', function() {
            console.log('[NavigationProgress] HTMX history restore');
            completeNavigationProgress();
        });
    }

    // Handle browser back/forward buttons
    function handleBrowserNavigation() {
        window.addEventListener('popstate', function() {
            // popstate fires immediately on back/forward; complete bar quickly
            completeNavigationProgress();
        });
    }

    // Failsafe: complete the bar if it's been stuck for more than 8s
    function installFailsafe() {
        setInterval(function() {
            const progressContainer = document.getElementById('navigation-progress');
            if (progressContainer && progressContainer.classList.contains('active')) {
                const elapsed = progressStartTime ? Date.now() - progressStartTime : 0;
                if (elapsed > 8000) {
                    console.warn('[NavigationProgress] Failsafe: force-completing stuck progress bar after', elapsed, 'ms');
                    completeNavigationProgress();
                }
            }
        }, 2000);
    }

    // Initialize
    function init() {
        console.log('[NavigationProgress] Initializing navigation progress bar');

        interceptNavigation();
        hookHtmxEvents();
        handleBrowserNavigation();
        installFailsafe();
    }

    // Public API
    window.PwaniNetNavigationProgress = {
        start: startNavigationProgress,
        complete: completeNavigationProgress,
        cancel: cancelNavigationProgress
    };

    // Auto-initialize
    init();

})();

