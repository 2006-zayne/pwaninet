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

    // Intercept navigation to start progress bar
    function interceptNavigation() {
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Skip if: external, anchor, HTMX, JS, target blank
            if (!href || 
                href.startsWith('http') && !href.startsWith(window.location.origin) ||
                href.startsWith('#') ||
                link.hasAttribute('hx-get') || 
                link.hasAttribute('hx-post') ||
                href.startsWith('javascript:') ||
                link.getAttribute('target') === '_blank') {
                return;
            }
            
            // Check if this is a back navigation (browser history)
            if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
                return;
            }
            
            const isSameOrigin = href.startsWith(window.location.origin) || href.startsWith('/');
            
            if (isSameOrigin) {
                console.log('[NavigationProgress] Navigation detected to:', href);
                startNavigationProgress();
            }
        });
    }

    // Handle browser navigation
    function handleBrowserNavigation() {
        // Handle popstate (back/forward buttons)
        window.addEventListener('popstate', function() {
            console.log('[NavigationProgress] Popstate detected, cancelling progress bar');
            cancelNavigationProgress();
        });
    }

    // Monitor page load to complete progress bar
    function monitorPageLoad() {
        window.addEventListener('load', function() {
            console.log('[NavigationProgress] Window load event fired');
            
            // Check if this is a navigation (not initial load)
            const navigationEntries = performance.getEntriesByType('navigation');
            const isNavigation = navigationEntries.length > 0 && 
                               (navigationEntries[0].type === 'navigate' || 
                                navigationEntries[0].type === 'reload');
            
            if (isNavigation) {
                console.log('[NavigationProgress] Page load detected, completing progress bar');
                completeNavigationProgress();
            }
        });
        
        // Failsafe: ensure progress bar doesn't get stuck
        setTimeout(function() {
            const progressContainer = document.getElementById('navigation-progress');
            if (progressContainer && progressContainer.classList.contains('active')) {
                console.warn('[NavigationProgress] Force completing progress bar after timeout');
                completeNavigationProgress();
            }
        }, 5000); // 5 second failsafe
    }

    // Initialize
    function init() {
        console.log('[NavigationProgress] Initializing navigation progress bar');
        
        interceptNavigation();
        handleBrowserNavigation();
        monitorPageLoad();
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
