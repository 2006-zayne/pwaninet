/**
 * PwaniNet Page Skeleton Manager
 * Unified page-aware skeleton system for initial page load and offline mode
 * Ensures consistent skeleton display across loading and offline states
 */

(function() {
    'use strict';

    const overlayId = 'page-skeleton';
    let isShowing = false;

    /**
     * Detect current page type from URL
     * Matches the logic in offline-skeleton-v2.js for consistency
     */
    function detectPageType() {
        const p = window.location.pathname;
        
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
                console.warn('[PageSkeletonManager] Template fetch failed, using fallback:', templateUrl);
                return getFallbackSkeleton(pageType);
            }
            return await response.text();
        } catch (error) {
            console.error('[PageSkeletonManager] Error loading skeleton template:', error);
            return getFallbackSkeleton(pageType);
        }
    }

    /**
     * Fallback skeleton if template loading fails
     * Uses inline HTML generation as backup
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
     * Show page skeleton for initial load
     */
    async function showPageSkeleton() {
        if (isShowing) return;
        
        const pageType = detectPageType();
        console.log('[PageSkeletonManager] Showing skeleton for page type:', pageType);
        
        const skeletonEl = document.getElementById(overlayId);
        if (!skeletonEl) {
            console.warn('[PageSkeletonManager] Skeleton element not found');
            return;
        }
        
        isShowing = true;
        
        // Load and inject the appropriate skeleton template
        const skeletonHTML = await loadSkeletonTemplate(pageType);
        skeletonEl.innerHTML = skeletonHTML;
        
        // Ensure skeleton is visible
        skeletonEl.classList.remove('hidden');
        skeletonEl.style.display = 'block';
    }

    /**
     * Hide page skeleton
     */
    function hidePageSkeleton() {
        if (!isShowing) return;
        
        const skeletonEl = document.getElementById(overlayId);
        if (skeletonEl) {
            skeletonEl.classList.add('hidden');
            skeletonEl.style.display = 'none';
            console.log('[PageSkeletonManager] Skeleton hidden');
        }
        
        isShowing = false;
    }

    /**
     * Initialize the page skeleton manager
     */
    function init() {
        // Show skeleton immediately on page load
        showPageSkeleton();
        
        // Hide skeleton when page is fully loaded
        window.addEventListener('load', function() {
            console.log('[PageSkeletonManager] Page loaded, hiding skeleton');
            hidePageSkeleton();
        });
        
        // Failsafe: hide skeleton after maximum timeout
        setTimeout(function() {
            if (isShowing) {
                console.warn('[PageSkeletonManager] Force hiding skeleton after timeout');
                hidePageSkeleton();
            }
        }, 5000);
        
        // Sync with offline skeleton system
        // When offline, ensure the same skeleton is shown
        window.addEventListener('offline', function() {
            console.log('[PageSkeletonManager] Offline detected, ensuring skeleton consistency');
            // The offline-skeleton-v2.js will handle showing the skeleton
            // We just need to ensure our page type detection matches
        });
        
        // Ensure skeleton is hidden when coming back online
        window.addEventListener('online', function() {
            console.log('[PageSkeletonManager] Online detected, hiding skeleton if visible');
            if (isShowing) {
                hidePageSkeleton();
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose public API
    window.PwaniNetPageSkeletonManager = {
        detectPageType,
        showPageSkeleton,
        hidePageSkeleton,
        getSkeletonTemplateUrl
    };

})();
