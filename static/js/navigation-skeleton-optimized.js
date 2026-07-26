/**
 * PwaniNet Optimized Navigation Skeleton Manager
 * Shows skeleton screens only when necessary:
 * - First visit to a page
 * - Navigation takes longer than threshold
 * - Heavy operations (search, large lists)
 * Uses client-side caching to avoid unnecessary skeletons
 */

(function() {
    'use strict';

    const overlayId = 'navigation-skeleton-overlay';
    let isShowing = false;
    let navigationStartTime = null;
    
    // Configuration
    const CONFIG = {
        // Show skeleton only if navigation takes longer than this (ms)
        NAVIGATION_THRESHOLD: 300,
        // Cache duration for visited pages (ms) - 5 minutes
        CACHE_DURATION: 5 * 60 * 1000,
        // Always show skeleton for these page types
        ALWAYS_SKELETON_PAGES: ['search', 'notifications'],
        // Storage key for cache
        STORAGE_KEY: 'pwaninet_page_cache'
    };

    /**
     * Get cached page data
     */
    function getCachedPage(url) {
        try {
            const cache = JSON.parse(sessionStorage.getItem(CONFIG.STORAGE_KEY) || '{}');
            const pageData = cache[url];
            
            if (!pageData) return null;
            
            // Check if cache is expired
            if (Date.now() - pageData.timestamp > CONFIG.CACHE_DURATION) {
                delete cache[url];
                sessionStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(cache));
                return null;
            }
            
            return pageData;
        } catch (e) {
            console.warn('[OptimizedNavSkeleton] Cache read error:', e);
            return null;
        }
    }

    /**
     * Cache page data
     */
    function cachePage(url, pageType) {
        try {
            const cache = JSON.parse(sessionStorage.getItem(CONFIG.STORAGE_KEY) || '{}');
            cache[url] = {
                pageType: pageType,
                timestamp: Date.now()
            };
            sessionStorage.setItem(CONFIG.STORAGE_KEY, JSON.stringify(cache));
        } catch (e) {
            console.warn('[OptimizedNavSkeleton] Cache write error:', e);
        }
    }

    /**
     * Detect current page type from URL
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
     * Check if skeleton should be shown for this navigation
     */
    function shouldShowSkeleton(url) {
        const pageType = detectPageType(url);
        
        // Always show skeleton for certain page types
        if (CONFIG.ALWAYS_SKELETON_PAGES.includes(pageType)) {
            console.log('[OptimizedNavSkeleton] Always skeleton for page type:', pageType);
            return true;
        }
        
        // Check cache
        const cached = getCachedPage(url);
        if (cached) {
            console.log('[OptimizedNavSkeleton] Page cached, skipping skeleton:', url);
            return false;
        }
        
        return true;
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
                console.warn('[OptimizedNavSkeleton] Template fetch failed, using fallback:', templateUrl);
                return getFallbackSkeleton(pageType);
            }
            return await response.text();
        } catch (error) {
            console.error('[OptimizedNavSkeleton] Error loading skeleton template:', error);
            return getFallbackSkeleton(pageType);
        }
    }

    /**
     * Fallback skeleton if template loading fails
     */
    function getFallbackSkeleton(pageType) {
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

            [data-theme="dark"] #${overlayId} {
                background: var(--bg, #15161a);
            }
        `;
        document.head.appendChild(css);
    }

    /**
     * Show navigation skeleton with delay
     */
    let skeletonTimeout = null;
    
    async function showNavigationSkeleton(targetUrl) {
        if (isShowing) return;
        
        // Check if we should show skeleton at all
        if (!shouldShowSkeleton(targetUrl)) {
            console.log('[OptimizedNavSkeleton] Skipping skeleton for cached page');
            return;
        }
        
        const pageType = detectPageType(targetUrl);
        console.log('[OptimizedNavSkeleton] Delayed skeleton for page type:', pageType, 'target:', targetUrl);
        
        // Delay showing skeleton to see if navigation is fast
        skeletonTimeout = setTimeout(async () => {
            if (isShowing) return;
            
            isShowing = true;
            navigationStartTime = Date.now();
            
            injectCSS();
            
            const existingOverlay = document.getElementById(overlayId);
            if (existingOverlay) {
                existingOverlay.remove();
            }
            
            const skeletonHTML = await loadSkeletonTemplate(pageType);
            document.body.insertAdjacentHTML('beforeend', `<div id="${overlayId}">${skeletonHTML}</div>`);
            
            const overlay = document.getElementById(overlayId);
            if (overlay) {
                overlay.classList.add('show');
            }
        }, CONFIG.NAVIGATION_THRESHOLD);
    }

    /**
     * Hide navigation skeleton
     */
    function hideNavigationSkeleton() {
        // Clear pending skeleton
        if (skeletonTimeout) {
            clearTimeout(skeletonTimeout);
            skeletonTimeout = null;
        }
        
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
        console.log('[OptimizedNavSkeleton] Skeleton hidden after', duration, 'ms');
        
        isShowing = false;
        navigationStartTime = null;
        
        // Cache the current page
        cachePage(window.location.href, detectPageType());
    }

    /**
     * Intercept navigation clicks
     */
    function interceptNavigation() {
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
            
            // Check if this is a back navigation (browser history)
            // Don't show skeleton for back/forward
            if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
                return;
            }
            
            console.log('[OptimizedNavSkeleton] Intercepting navigation to:', href);
            showNavigationSkeleton(href);
        });
    }

    /**
     * Handle browser back/forward navigation
     */
    function handleBrowserNavigation() {
        // Use Page Visibility API to detect when page becomes visible again
        document.addEventListener('visibilitychange', function() {
            if (!document.hidden) {
                // Page became visible (back from another tab or history navigation)
                console.log('[OptimizedNavSkeleton] Page visible, hiding any skeleton');
                hideNavigationSkeleton();
            }
        });
        
        // Handle popstate (back/forward buttons)
        window.addEventListener('popstate', function() {
            console.log('[OptimizedNavSkeleton] Popstate detected, hiding skeleton');
            hideNavigationSkeleton();
        });
    }

    /**
     * Hide skeleton when page is fully loaded
     */
    function setupPageLoadHandlers() {
        // Hide skeleton when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                console.log('[OptimizedNavSkeleton] DOMContentLoaded, hiding skeleton');
                hideNavigationSkeleton();
            });
        } else {
            console.log('[OptimizedNavSkeleton] DOM already loaded, hiding skeleton');
            hideNavigationSkeleton();
        }
        
        // Cache the current page on load
        cachePage(window.location.href, detectPageType());
        
        // Failsafe: hide skeleton after maximum timeout
        setTimeout(function() {
            if (isShowing) {
                console.warn('[OptimizedNavSkeleton] Force hiding skeleton after timeout');
                hideNavigationSkeleton();
            }
        }, 5000);
    }

    /**
     * Initialize the optimized navigation skeleton manager
     */
    function init() {
        console.log('[OptimizedNavSkeleton] Initializing optimized navigation skeleton system');
        
        setupPageLoadHandlers();
        interceptNavigation();
        handleBrowserNavigation();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose public API
    window.PwaniNetOptimizedNavigationSkeleton = {
        showNavigationSkeleton,
        hideNavigationSkeleton,
        detectPageType,
        getSkeletonTemplateUrl,
        clearCache: function() {
            sessionStorage.removeItem(CONFIG.STORAGE_KEY);
            console.log('[OptimizedNavSkeleton] Cache cleared');
        }
    };

})();
