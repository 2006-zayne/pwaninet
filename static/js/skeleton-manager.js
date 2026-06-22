/**
 * PwaniNet Unified Skeleton Manager
 * Single source of truth for all skeleton states: loading, offline, error
 * Consolidates navigation-skeleton.js, offline-skeleton-v2.js, skeleton-loader.js, and page-skeleton-manager.js
 */

(function() {
    'use strict';

    // ============================================================================
    // STATE MANAGEMENT
    // ============================================================================
    
    const STATE = {
        LOADING: 'loading',
        OFFLINE: 'offline',
        ERROR: 'error',
        NONE: 'none'
    };

    let currentState = STATE.NONE;
    let overlayElement = null;
    let currentSkeletonKey = null;
    let skeletonStartTime = null;
    let pendingContentCheck = null;
    
    // Feed state preservation
    const feedState = {
        scrollY: 0,
        loadedPages: [],
        activeTab: null,
        filters: {},
        cachedContent: null
    };

    // Cache for skeleton templates
    const skeletonTemplateCache = new Map();

    // ============================================================================
    // PAGE TYPE DETECTION
    // ============================================================================

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

    // ============================================================================
    // SKELETON TEMPLATE LOADING
    // ============================================================================

    async function loadSkeletonTemplate(pageType) {
        // Check cache first
        if (skeletonTemplateCache.has(pageType)) {
            return skeletonTemplateCache.get(pageType);
        }

        const templateUrl = getSkeletonTemplateUrl(pageType);
        
        try {
            const response = await fetch(templateUrl);
            if (!response.ok) {
                console.warn('[SkeletonManager] Template fetch failed, using fallback:', templateUrl);
                return getFallbackSkeleton(pageType);
            }
            const html = await response.text();
            skeletonTemplateCache.set(pageType, html);
            return html;
        } catch (error) {
            console.error('[SkeletonManager] Error loading skeleton template:', error);
            return getFallbackSkeleton(pageType);
        }
    }

    function getFallbackSkeleton(pageType) {
        return `
            <div style="padding: 24px; max-width: 600px; margin: 0 auto;">
                <div style="width: 100%; height: 200px; background: var(--border, #e2e8f0); border-radius: 12px; margin-bottom: 16px;"></div>
                <div style="width: 100%; height: 200px; background: var(--border, #e2e8f0); border-radius: 12px; margin-bottom: 16px;"></div>
                <div style="width: 100%; height: 200px; background: var(--border, #e2e8f0); border-radius: 12px;"></div>
            </div>
        `;
    }

    // ============================================================================
    // STATE BANNER GENERATION
    // ============================================================================

    function getStateBanner(state) {
        switch (state) {
            case STATE.OFFLINE:
                return '<div class="skel-state-banner skel-offline"><i class="bi bi-wifi-off"></i><span>No internet</span><span class="skel-pulse">Retrying...</span></div>';
            case STATE.ERROR:
                return '<div class="skel-state-banner skel-error"><i class="bi bi-exclamation-triangle"></i><span>Error loading</span><span class="skel-pulse">Retrying...</span></div>';
            case STATE.LOADING:
            default:
                return '';
        }
    }

    // ============================================================================
    // CRITICAL CONTENT CHECKING (Fixes Skeleton Flicker)
    // ============================================================================

    function waitForCriticalContent(targetElement, callback) {
        // Cancel any pending check
        if (pendingContentCheck) {
            clearTimeout(pendingContentCheck);
        }

        // Check if critical content is ready
        const checkContent = () => {
            if (!targetElement || !document.body.contains(targetElement)) {
                console.warn('[SkeletonManager] Target element not found, hiding skeleton');
                callback();
                return;
            }

            // Check for critical content
            const hasText = targetElement.textContent.trim().length > 0;
            const hasImages = targetElement.querySelectorAll('img').length > 0;
            const hasStructure = targetElement.children.length > 0;

            // For feed: check if we have actual post content
            const hasPosts = targetElement.querySelectorAll('.post-card, .intel-stream-item').length > 0;

            // Content is ready if we have text and structure, or posts
            const isReady = (hasText && hasStructure) || hasPosts;

            if (isReady) {
                console.log('[SkeletonManager] Critical content detected, hiding skeleton');
                callback();
            } else {
                // Retry after short delay
                pendingContentCheck = setTimeout(checkContent, 50);
            }
        };

        // Start checking
        checkContent();
    }

    // ============================================================================
    // SKELETON DISPLAY
    // ============================================================================

    function injectCSS() {
        if (document.getElementById('skeleton-manager-css')) return;

        const css = document.createElement('style');
        css.id = 'skeleton-manager-css';
        css.textContent = `
            #skeleton-manager-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: var(--bg, #f7f8fa);
                z-index: 99998;
                overflow-y: auto;
                padding-bottom: 80px;
                animation: skelFadeIn 0.2s ease;
                pointer-events: none;
            }

            #skeleton-manager-overlay.show {
                pointer-events: auto;
            }

            @keyframes skelFadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            /* State banners */
            .skel-state-banner {
                position: sticky;
                top: 0;
                z-index: 100000;
                text-align: center;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
            }

            .skel-offline {
                background: #ef4444;
                color: #fff;
            }

            .skel-error {
                background: #f59e0b;
                color: #fff;
            }

            .skel-pulse {
                animation: skelPulse 1.5s infinite;
            }

            @keyframes skelPulse {
                0%, 100% { opacity: 0.5; }
                50% { opacity: 1; }
            }

            /* Dark mode support */
            [data-theme="dark"] #skeleton-manager-overlay {
                background: var(--bg, #15161a);
            }

            /* Skeleton shimmer effect */
            .sk {
                background: linear-gradient(100deg, var(--sk-base, #e9eaee) 30%, var(--sk-shine, #f6f7f9) 45%, var(--sk-base, #e9eaee) 60%);
                background-size: 250% 100%;
                animation: shimmer 1.5s ease-in-out infinite;
                border-radius: 6px;
            }

            @keyframes shimmer {
                0% { background-position: 120% 0; }
                100% { background-position: -20% 0; }
            }

            [data-theme="dark"] .sk {
                --sk-base: #2a2d34;
                --sk-shine: #363a42;
            }

            @media (prefers-reduced-motion: reduce) {
                .sk { animation: none; background: var(--sk-base, #e9eaee); }
            }
        `;
        document.head.appendChild(css);
    }

    async function showSkeleton(state, targetUrl = null, targetElement = null) {
        // Don't show skeleton if we're returning from cache
        if (shouldSkipSkeleton()) {
            console.log('[SkeletonManager] Skipping skeleton (cached/back navigation)');
            return;
        }

        const pageType = detectPageType(targetUrl);
        console.log('[SkeletonManager] Showing skeleton:', state, 'for page type:', pageType);
        
        currentState = state;
        currentSkeletonKey = pageType;
        skeletonStartTime = Date.now();
        
        injectCSS();
        
        // Remove existing overlay
        if (overlayElement) {
            overlayElement.remove();
        }
        
        // Load skeleton template
        const skeletonHTML = await loadSkeletonTemplate(pageType);
        const stateBanner = getStateBanner(state);
        
        // Create overlay
        overlayElement = document.createElement('div');
        overlayElement.id = 'skeleton-manager-overlay';
        overlayElement.innerHTML = stateBanner + skeletonHTML;
        document.body.appendChild(overlayElement);
        
        // Show overlay
        requestAnimationFrame(() => {
            overlayElement.classList.add('show');
        });

        // Save feed state before navigation
        if (pageType === 'home') {
            saveFeedState();
        }
    }

    function hideSkeleton(targetElement = null) {
        if (!overlayElement) return;
        
        console.log('[SkeletonManager] Hiding skeleton');
        
        // Wait for critical content if target element provided
        if (targetElement && currentState === STATE.LOADING) {
            waitForCriticalContent(targetElement, () => {
                performHide();
            });
        } else {
            performHide();
        }
    }

    function performHide() {
        if (!overlayElement) return;
        
        overlayElement.style.opacity = '0';
        overlayElement.style.transition = 'opacity 0.2s ease';
        
        setTimeout(() => {
            if (overlayElement && overlayElement.parentNode) {
                overlayElement.parentNode.removeChild(overlayElement);
            }
            overlayElement = null;
        }, 200);
        
        const duration = Date.now() - skeletonStartTime;
        console.log('[SkeletonManager] Skeleton hidden after', duration, 'ms');
        
        currentState = STATE.NONE;
        currentSkeletonKey = null;
        skeletonStartTime = null;
    }

    // ============================================================================
    // FEED STATE PRESERVATION
    // ============================================================================

    function saveFeedState() {
        feedState.scrollY = window.scrollY;
        feedState.loadedPages = Array.from(document.querySelectorAll('.post-card, .intel-stream-item')).map(el => el.id);
        feedState.activeTab = document.querySelector('.nav-tabs .active')?.dataset.tab || null;
        
        // Cache current feed content
        const feedContainer = document.querySelector('#main-content-area, .feed-sector');
        if (feedContainer) {
            feedState.cachedContent = feedContainer.innerHTML;
        }
        
        // Save to sessionStorage
        try {
            sessionStorage.setItem('pwaninet_feed_state', JSON.stringify(feedState));
            console.log('[SkeletonManager] Feed state saved:', feedState);
        } catch (e) {
            console.warn('[SkeletonManager] Failed to save feed state:', e);
        }
    }

    function restoreFeedState() {
        try {
            const saved = sessionStorage.getItem('pwaninet_feed_state');
            if (!saved) return false;
            
            const state = JSON.parse(saved);
            console.log('[SkeletonManager] Restoring feed state:', state);
            
            // Restore scroll position
            if (state.scrollY > 0) {
                window.scrollTo(0, state.scrollY);
            }
            
            // Restore cached content if available
            if (state.cachedContent) {
                const feedContainer = document.querySelector('#main-content-area, .feed-sector');
                if (feedContainer && !feedContainer.innerHTML.trim()) {
                    feedContainer.innerHTML = state.cachedContent;
                }
            }
            
            // Clear after restore
            sessionStorage.removeItem('pwaninet_feed_state');
            return true;
        } catch (e) {
            console.warn('[SkeletonManager] Failed to restore feed state:', e);
            return false;
        }
    }

    function shouldSkipSkeleton() {
        // Skip skeleton if:
        // 1. Browser back navigation
        // 2. Restoring from cache
        // 3. Feed state exists in sessionStorage
        
        const navigationEntries = performance.getEntriesByType('navigation');
        const isBackNavigation = navigationEntries.length > 0 && navigationEntries[0].type === 'back_forward';
        
        if (isBackNavigation) {
            console.log('[SkeletonManager] Back navigation detected');
            return true;
        }
        
        const hasFeedState = sessionStorage.getItem('pwaninet_feed_state');
        if (hasFeedState) {
            console.log('[SkeletonManager] Feed state exists, restoring');
            restoreFeedState();
            return true;
        }
        
        return false;
    }

    // ============================================================================
    // HTMX INTEGRATION
    // ============================================================================

    function initHTMXIntegration() {
        document.addEventListener('htmx:beforeRequest', function(event) {
            const target = event.detail.target;
            const skeletonKey = target.dataset.skeleton;
            
            console.log('[SkeletonManager] HTMX beforeRequest:', skeletonKey);
            
            if (skeletonKey) {
                // For HTMX requests, show inline skeleton instead of full page overlay
                showInlineSkeleton(target, skeletonKey);
            }
        });

        document.addEventListener('htmx:afterSwap', function(event) {
            const target = event.detail.target;
            
            console.log('[SkeletonManager] HTMX afterSwap');
            
            hideInlineSkeleton(target);
        });

        document.addEventListener('htmx:responseError', function(event) {
            const target = event.detail.target;
            
            console.error('[SkeletonManager] HTMX responseError');
            
            // Keep skeleton visible on error
            // User can retry
        });
    }

    function showInlineSkeleton(target, skeletonKey) {
        if (!target) return;
        
        // Store original content
        if (!target.dataset.originalContent) {
            target.dataset.originalContent = target.innerHTML;
        }
        
        // Get skeleton HTML from registry (if available) or use simple loader
        let skeletonHTML = '';
        if (window.PwaniNetSkeletonLoader) {
            skeletonHTML = window.PwaniNetSkeletonLoader.getSkeletonHTML(skeletonKey) || '';
        }
        
        if (!skeletonHTML) {
            skeletonHTML = '<div class="sk" style="width: 100%; height: 200px; border-radius: 12px;"></div>';
        }
        
        target.innerHTML = skeletonHTML;
        target.classList.add('skeleton-loading');
        target.dataset.skeletonActive = 'true';
    }

    function hideInlineSkeleton(target) {
        if (!target) return;
        
        target.classList.remove('skeleton-loading');
        target.removeAttribute('data-skeleton-active');
        
        // Wait for critical content before fully removing skeleton state
        waitForCriticalContent(target, () => {
            // Content is ready
        });
    }

    // ============================================================================
    // NAVIGATION INTERCEPTION
    // ============================================================================

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
            
            // Show skeleton for internal navigation
            console.log('[SkeletonManager] Intercepting navigation to:', href);
            showSkeleton(STATE.LOADING, href);
        });
    }

    // ============================================================================
    // OFFLINE/ONLINE HANDLING
    // ============================================================================

    function initConnectivityHandlers() {
        window.addEventListener('offline', function() {
            console.log('[SkeletonManager] Offline detected');
            showSkeleton(STATE.OFFLINE);
        });
        
        window.addEventListener('online', function() {
            console.log('[SkeletonManager] Online detected');
            hideSkeleton();
        });
    }

    // ============================================================================
    // INFINITE SCROLL SUPPORT
    // ============================================================================

    function showInfiniteScrollSkeleton(container) {
        const skeletonHTML = `
            <div class="infinite-scroll-skeleton">
                <div class="sk" style="width: 100%; height: 200px; border-radius: 12px; margin-bottom: 16px;"></div>
                <div class="sk" style="width: 100%; height: 200px; border-radius: 12px; margin-bottom: 16px;"></div>
                <div class="sk" style="width: 100%; height: 200px; border-radius: 12px;"></div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', skeletonHTML);
    }

    function hideInfiniteScrollSkeleton(container) {
        const skeleton = container.querySelector('.infinite-scroll-skeleton');
        if (skeleton) {
            skeleton.remove();
        }
    }

    // ============================================================================
    // INITIALIZATION
    // ============================================================================

    function init() {
        console.log('[SkeletonManager] Initializing unified skeleton system');
        
        // Inject CSS
        injectCSS();
        
        // Initialize HTMX integration
        initHTMXIntegration();
        
        // Intercept navigation
        interceptNavigation();
        
        // Handle connectivity changes
        initConnectivityHandlers();
        
        // Handle initial page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                // Check if we should show initial skeleton
                if (!shouldSkipSkeleton()) {
                    showSkeleton(STATE.LOADING);
                }
                
                // Hide skeleton when page is ready
                window.addEventListener('load', function() {
                    hideSkeleton(document.body);
                });
            });
        } else {
            // DOM already loaded
            if (!shouldSkipSkeleton()) {
                showSkeleton(STATE.LOADING);
            }
            
            window.addEventListener('load', function() {
                hideSkeleton(document.body);
            });
        }
        
        // Failsafe: hide skeleton after maximum timeout
        setTimeout(function() {
            if (overlayElement) {
                console.warn('[SkeletonManager] Force hiding skeleton after timeout');
                performHide();
            }
        }, 5000);
    }

    // ============================================================================
    // PUBLIC API
    // ============================================================================

    window.PwaniNetSkeletonManager = {
        // State constants
        STATE,
        
        // Current state
        getState: () => currentState,
        
        // Show/hide skeletons
        show: (state, targetUrl, targetElement) => showSkeleton(state, targetUrl, targetElement),
        hide: (targetElement) => hideSkeleton(targetElement),
        
        // Feed state
        saveFeedState,
        restoreFeedState,
        
        // Infinite scroll
        showInfiniteScrollSkeleton,
        hideInfiniteScrollSkeleton,
        
        // Page detection
        detectPageType,
        getSkeletonTemplateUrl,
        
        // Manual control
        forceHide: performHide
    };

    // Initialize
    init();

})();
