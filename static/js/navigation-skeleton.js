/**
 * PwaniNet Navigation Skeleton Manager
 * Shows skeleton screens during page navigation (before content loads)
 * Uses the same skeleton templates as offline-skeleton-v2.js for consistency
 */

(function() {
    'use strict';

    const overlayId = 'navigation-skeleton-overlay';
    let isShowing = false;
    let navigationStartTime = null;

    /**
     * Detect current page type from URL
     * Matches the logic in offline-skeleton-v2.js for consistency
     */
    function detectPageType(url) {
        const p = url || window.location.pathname;
        
        if (p.includes('/profile/') || p.match(/^\/users\/[^\/]+\/?$/)) return 'profile';
        if (p.includes('/groups/') && !p.includes('/create')) {
            if (p.match(/\/groups\/[^\/]+\/?$/)) return 'group-detail';
            return 'groups';
        }
        if (p.includes('/notifications/')) return 'notifications';
        if (p.includes('/posts/') && p.match(/\/posts\/[^\/]+\/?$/)) return 'post-detail';
        if (p.includes('/courses/') && p.match(/\/courses\/[^\/]+\/?$/)) return 'course-detail';
        if (p.includes('/search') || p.includes('?q=')) return 'search';
        if (p.includes('/messages/')) {
            if (p.match(/\/messages\/[^\/]+\/?$/)) return 'messaging-detail';
            return 'messaging-list';
        }
        if (p === '/' || p === '/home/' || p.includes('/posts/')) return 'home';
        return 'home';
    }

    /**
     * Get skeleton template URL based on page type
     */
    function getSkeletonTemplateUrl(pageType) {
        const templateMap = {
            'home': '/skeleton-template/_skeleton_post_feed.html',
            'profile': '/skeleton-template/_skeleton_profile.html',
            'groups': '/skeleton-template/_skeleton_groups_list.html',
            'group-detail': '/skeleton-template/_skeleton_group_detail.html',
            'notifications': '/skeleton-template/_skeleton_notifications.html',
            'post-detail': '/skeleton-template/_skeleton_post_detail.html',
            'course-detail': '/skeleton-template/_skeleton_course_detail.html',
            'messaging-list': '/skeleton-template/_skeleton_messaging_list.html',
            'messaging-detail': '/skeleton-template/_skeleton_messaging_detail.html',
            'search': '/skeleton-template/_skeleton_search_results.html'
        };
        
        return templateMap[pageType] || templateMap['home'];
    }

    /**
     * Load skeleton template from server
     */
    async function loadSkeletonTemplate(pageType) {
        const templateUrl = getSkeletonTemplateUrl(pageType);
        
        try {
            const response = await fetch(templateUrl);
            if (!response.ok) {
                console.warn('[NavigationSkeleton] Template fetch failed, using fallback:', templateUrl);
                return getFallbackSkeleton(pageType);
            }
            return await response.text();
        } catch (error) {
            console.error('[NavigationSkeleton] Error loading skeleton template:', error);
            return getFallbackSkeleton(pageType);
        }
    }

    /**
     * Fallback skeleton if template loading fails
     */
    function getFallbackSkeleton(pageType) {
        // Simple fallback that shows at least some loading state
        return `
            <div style="padding: 24px; max-width: 600px; margin: 0 auto;">
                <div style="width: 100%; height: 200px; background: #e2e8f0; border-radius: 12px; margin-bottom: 16px;"></div>
                <div style="width: 100%; height: 200px; background: #e2e8f0; border-radius: 12px; margin-bottom: 16px;"></div>
                <div style="width: 100%; height: 200px; background: #e2e8f0; border-radius: 12px;"></div>
            </div>
        `;
    }

    /**
     * Inject skeleton CSS
     */
    function injectCSS() {
        if (document.getElementById('nav-skeleton-css')) return;

        const css = document.createElement('style');
        css.id = 'nav-skeleton-css';
        css.textContent = `
            #${overlayId} {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: var(--bg, #f7f8fa);
                z-index: 99998;
                overflow-y: auto;
                padding-bottom: 80px;
                animation: navSkelFadeIn 0.2s ease;
                pointer-events: none;
            }

            #${overlayId}.show {
                pointer-events: auto;
            }

            @keyframes navSkelFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            /* Dark mode support */
            [data-theme="dark"] #${overlayId} {
                background: var(--bg, #15161a);
            }
        `;
        document.head.appendChild(css);
    }

    /**
     * Show navigation skeleton
     */
    async function showNavigationSkeleton(targetUrl) {
        if (isShowing) return;
        
        const pageType = detectPageType(targetUrl);
        console.log('[NavigationSkeleton] Showing skeleton for page type:', pageType, 'target:', targetUrl);
        
        isShowing = true;
        navigationStartTime = Date.now();
        
        injectCSS();
        
        // Remove existing overlay if any
        const existingOverlay = document.getElementById(overlayId);
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        // Load and inject the appropriate skeleton template
        const skeletonHTML = await loadSkeletonTemplate(pageType);
        document.body.insertAdjacentHTML('beforeend', `<div id="${overlayId}">${skeletonHTML}</div>`);
        
        const overlay = document.getElementById(overlayId);
        if (overlay) {
            overlay.classList.add('show');
        }
    }

    /**
     * Hide navigation skeleton
     */
    function hideNavigationSkeleton() {
        if (!isShowing) return;
        
        const overlay = document.getElementById(overlayId);
        if (overlay) {
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 0.2s ease';
            
            setTimeout(() => {
                if (overlay && overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 200);
        }
        
        const duration = Date.now() - navigationStartTime;
        console.log('[NavigationSkeleton] Skeleton hidden after', duration, 'ms');
        
        isShowing = false;
        navigationStartTime = null;
    }

    /**
     * Intercept navigation clicks
     */
    function interceptNavigation() {
        // Intercept all link clicks
        document.addEventListener('click', function(event) {
            const link = event.target.closest('a');
            if (!link) return;
            
            const href = link.getAttribute('href');
            
            // Skip if:
            // - No href
            // - External link
            // - Anchor link
            // - HTMX request
            // - JavaScript link
            // - Already has target="_blank"
            if (!href || 
                href.startsWith('http') && !href.startsWith(window.location.origin) ||
                href.startsWith('#') ||
                link.hasAttribute('hx-get') || 
                link.hasAttribute('hx-post') ||
                href.startsWith('javascript:') ||
                link.getAttribute('target') === '_blank') {
                return;
            }
            
            // Show skeleton for internal navigation
            console.log('[NavigationSkeleton] Intercepting navigation to:', href);
            showNavigationSkeleton(href);
        });
    }

    /**
     * Hide skeleton when page is fully loaded
     */
    function setupPageLoadHandlers() {
        // Hide skeleton when DOM is ready (content has arrived)
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                console.log('[NavigationSkeleton] DOMContentLoaded, hiding skeleton');
                setTimeout(hideNavigationSkeleton, 100); // Small delay to ensure content is rendered
            });
        } else {
            // DOM already loaded
            console.log('[NavigationSkeleton] DOM already loaded, hiding skeleton');
            setTimeout(hideNavigationSkeleton, 100);
        }
        
        // Failsafe: hide skeleton after maximum timeout
        setTimeout(function() {
            if (isShowing) {
                console.warn('[NavigationSkeleton] Force hiding skeleton after timeout');
                hideNavigationSkeleton();
            }
        }, 5000);
    }

    /**
     * Sync with offline skeleton system
     */
    function syncWithOfflineSkeleton() {
        // When offline, ensure the offline skeleton takes precedence
        window.addEventListener('offline', function() {
            console.log('[NavigationSkeleton] Offline detected, deferring to offline skeleton');
            // Hide navigation skeleton if visible
            if (isShowing) {
                hideNavigationSkeleton();
            }
        });
        
        // When coming back online, ensure we don't show navigation skeleton unexpectedly
        window.addEventListener('online', function() {
            console.log('[NavigationSkeleton] Online detected');
        });
    }

    /**
     * Initialize the navigation skeleton manager
     */
    function init() {
        console.log('[NavigationSkeleton] Initializing navigation skeleton system');
        
        // Show skeleton for initial page load if we're navigating
        // (This handles the case where user clicks a link and page loads)
        setupPageLoadHandlers();
        
        // Intercept navigation clicks
        interceptNavigation();
        
        // Sync with offline skeleton
        syncWithOfflineSkeleton();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose public API
    window.PwaniNetNavigationSkeleton = {
        showNavigationSkeleton,
        hideNavigationSkeleton,
        detectPageType,
        getSkeletonTemplateUrl
    };

})();
