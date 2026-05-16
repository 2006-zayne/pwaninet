/**
 * PwaniNet Offline Skeleton Manager
 * Shows Facebook-style skeleton when connection is lost
 * Automatically hides when connection is restored
 */

(function() {
    'use strict';
    
    var overlayId = 'offline-skeleton-overlay';
    var isShowing = false;
    
    // Build the full-page skeleton overlay HTML
    function buildSkeletonHTML() {
        return `
        <div id="${overlayId}">
            <!-- Offline Banner -->
            <div class="offline-banner">
                <i class="bi bi-wifi-off"></i>
                <span>No internet connection</span>
                <span class="offline-retry">Retrying...</span>
            </div>
            
            <!-- Search Header Skeleton -->
            <div class="skeleton-search-header">
                <div class="skeleton-search-avatar"></div>
                <div class="skeleton-search-bar"></div>
            </div>
            
            <!-- Groups Explore Skeleton -->
            <div class="skeleton-groups-section">
                <div class="skeleton-groups-header"></div>
                <div class="skeleton-groups-row">
                    <div class="skeleton-group-item"></div>
                    <div class="skeleton-group-item"></div>
                    <div class="skeleton-group-item"></div>
                    <div class="skeleton-group-item"></div>
                    <div class="skeleton-group-item"></div>
                </div>
            </div>
            
            <!-- Post Skeletons (3 cards) -->
            <div class="skeleton-post-card">
                <div class="skeleton-post-header">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-post-meta">
                        <div class="skeleton-line skeleton-name"></div>
                        <div class="skeleton-line skeleton-time"></div>
                    </div>
                    <div class="skeleton-menu-dot"></div>
                </div>
                <div class="skeleton-post-body">
                    <div class="skeleton-line skeleton-text-full"></div>
                    <div class="skeleton-line skeleton-text-full"></div>
                    <div class="skeleton-line skeleton-text-short"></div>
                </div>
                <div class="skeleton-post-media"></div>
                <div class="skeleton-post-actions">
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                </div>
                <div class="skeleton-post-comment">
                    <div class="skeleton-avatar-sm"></div>
                    <div class="skeleton-line skeleton-comment-input"></div>
                </div>
            </div>
            
            <div class="skeleton-post-card">
                <div class="skeleton-post-header">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-post-meta">
                        <div class="skeleton-line skeleton-name"></div>
                        <div class="skeleton-line skeleton-time"></div>
                    </div>
                    <div class="skeleton-menu-dot"></div>
                </div>
                <div class="skeleton-post-body">
                    <div class="skeleton-line skeleton-text-full"></div>
                    <div class="skeleton-line skeleton-text-short"></div>
                </div>
                <div class="skeleton-post-actions">
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                </div>
                <div class="skeleton-post-comment">
                    <div class="skeleton-avatar-sm"></div>
                    <div class="skeleton-line skeleton-comment-input"></div>
                </div>
            </div>
            
            <div class="skeleton-post-card">
                <div class="skeleton-post-header">
                    <div class="skeleton-avatar"></div>
                    <div class="skeleton-post-meta">
                        <div class="skeleton-line skeleton-name"></div>
                        <div class="skeleton-line skeleton-time"></div>
                    </div>
                    <div class="skeleton-menu-dot"></div>
                </div>
                <div class="skeleton-post-body">
                    <div class="skeleton-line skeleton-text-full"></div>
                    <div class="skeleton-line skeleton-text-full"></div>
                    <div class="skeleton-line skeleton-text-short"></div>
                </div>
                <div class="skeleton-post-media"></div>
                <div class="skeleton-post-actions">
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                    <div class="skeleton-line skeleton-action"></div>
                </div>
                <div class="skeleton-post-comment">
                    <div class="skeleton-avatar-sm"></div>
                    <div class="skeleton-line skeleton-comment-input"></div>
                </div>
            </div>
        </div>`;
    }
    
    // Build the CSS for the skeleton overlay
    function buildSkeletonCSS() {
        return `
        <style id="offline-skeleton-styles">
        #${overlayId} {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: var(--background, #f8fafc);
            z-index: 99999;
            overflow-y: auto;
            padding-bottom: 80px;
            animation: skeletonFadeIn 0.3s ease;
            pointer-events: none;
        }
        #${overlayId}.show { pointer-events: auto; }
        
        @keyframes skeletonFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        /* Offline Banner */
        .offline-banner {
            position: sticky;
            top: 0;
            z-index: 100000;
            background: #ef4444;
            color: white;
            text-align: center;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .offline-banner .bi-wifi-off {
            font-size: 14px;
        }
        
        .offline-retry {
            opacity: 0.8;
            font-weight: 400;
        }
        
        .offline-retry.pulse {
            animation: retryPulse 1.5s ease-in-out infinite;
        }
        
        @keyframes retryPulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 1; }
        }
        
        /* Search Header Skeleton */
        .skeleton-search-header {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--card-bg, #ffffff);
            border-bottom: 1px solid var(--border, #e2e8f0);
        }
        
        .skeleton-search-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: var(--border, #e2e8f0);
            flex-shrink: 0;
            overflow: hidden;
            position: relative;
        }
        
        .skeleton-search-avatar::after,
        .skeleton-search-bar::after,
        .skeleton-groups-header::after,
        .skeleton-group-item::after,
        .skeleton-avatar::after,
        .skeleton-avatar-sm::after,
        .skeleton-line::after,
        .skeleton-menu-dot::after,
        .skeleton-post-media::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255,255,255,0.4) 50%,
                transparent 100%
            );
            animation: shimmer 1.5s infinite;
        }
        
        [data-theme="dark"] .skeleton-search-avatar::after,
        [data-theme="dark"] .skeleton-search-bar::after,
        [data-theme="dark"] .skeleton-groups-header::after,
        [data-theme="dark"] .skeleton-group-item::after,
        [data-theme="dark"] .skeleton-avatar::after,
        [data-theme="dark"] .skeleton-avatar-sm::after,
        [data-theme="dark"] .skeleton-line::after,
        [data-theme="dark"] .skeleton-menu-dot::after,
        [data-theme="dark"] .skeleton-post-media::after {
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255,255,255,0.08) 50%,
                transparent 100%
            );
        }
        
        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }
        
        .skeleton-search-bar {
            flex-grow: 1;
            height: 40px;
            border-radius: 20px;
            background: var(--border, #e2e8f0);
            position: relative;
            overflow: hidden;
        }
        
        /* Groups Section Skeleton */
        .skeleton-groups-section {
            padding: 12px 16px;
            background: var(--card-bg, #ffffff);
            border-bottom: 1px solid var(--border, #e2e8f0);
        }
        
        .skeleton-groups-header {
            width: 140px;
            height: 14px;
            background: var(--border, #e2e8f0);
            border-radius: 4px;
            margin-bottom: 12px;
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-groups-row {
            display: flex;
            gap: 16px;
            overflow: hidden;
        }
        
        .skeleton-group-item {
            width: 60px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }
        
        .skeleton-group-item::after {
            content: '';
            display: block;
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--border, #e2e8f0);
            position: relative;
            overflow: hidden;
        }
        
        /* Post Card Skeleton */
        .skeleton-post-card {
            background: var(--card-bg, #ffffff);
            border-radius: 12px;
            margin: 8px;
            overflow: hidden;
            border: 1px solid var(--border, #e2e8f0);
            animation: skeletonCardIn 0.3s ease forwards;
        }
        
        .skeleton-post-card:nth-child(3) { animation-delay: 0.1s; }
        .skeleton-post-card:nth-child(4) { animation-delay: 0.2s; }
        .skeleton-post-card:nth-child(5) { animation-delay: 0.3s; }
        
        @keyframes skeletonCardIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .skeleton-post-header {
            display: flex;
            align-items: center;
            padding: 12px;
            gap: 10px;
        }
        
        .skeleton-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: var(--border, #e2e8f0);
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-avatar-sm {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--border, #e2e8f0);
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-post-meta {
            flex-grow: 1;
        }
        
        .skeleton-line {
            border-radius: 4px;
            background: var(--border, #e2e8f0);
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-name {
            width: 120px;
            height: 14px;
            margin-bottom: 6px;
        }
        
        .skeleton-time {
            width: 80px;
            height: 10px;
        }
        
        .skeleton-menu-dot {
            width: 28px;
            height: 28px;
            border-radius: 4px;
            background: var(--border, #e2e8f0);
            flex-shrink: 0;
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-post-body {
            padding: 0 12px 12px;
        }
        
        .skeleton-text-full {
            width: 100%;
            height: 14px;
            margin-bottom: 8px;
        }
        
        .skeleton-text-short {
            width: 60%;
            height: 14px;
            margin-bottom: 8px;
        }
        
        .skeleton-post-media {
            width: 100%;
            height: 250px;
            background: var(--border, #e2e8f0);
            position: relative;
            overflow: hidden;
        }
        
        .skeleton-post-actions {
            display: flex;
            gap: 24px;
            padding: 8px 12px;
            border-top: 1px solid var(--border, #e2e8f0);
        }
        
        .skeleton-action {
            width: 56px;
            height: 16px;
        }
        
        .skeleton-post-comment {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px 12px;
            border-top: 1px solid var(--border, #e2e8f0);
        }
        
        .skeleton-comment-input {
            flex-grow: 1;
            height: 36px;
            border-radius: 18px;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 767px) {
            .skeleton-post-media { height: 200px; }
            .skeleton-name { width: 100px; }
            .skeleton-time { width: 60px; }
            .skeleton-action { width: 44px; }
        }
        </style>`;
    }
    
    // Show the skeleton overlay
    function show() {
        if (isShowing) return;
        isShowing = true;
        
        console.log('📵 Showing offline skeleton overlay');
        
        // Inject CSS if not present
        if (!document.getElementById('offline-skeleton-styles')) {
            document.head.insertAdjacentHTML('beforeend', buildSkeletonCSS());
        }
        
        // Inject skeleton HTML
        document.body.insertAdjacentHTML('beforeend', buildSkeletonHTML());
        
        // Start retry indicator
        var retryEl = document.querySelector('.offline-retry');
        if (retryEl) retryEl.classList.add('pulse');
    }
    
    // Hide the skeleton overlay
    function hide() {
        if (!isShowing) return;
        isShowing = false;
        
        console.log('🌐 Hiding offline skeleton overlay - connection restored');
        
        var overlay = document.getElementById(overlayId);
        if (overlay) {
            overlay.style.animation = 'skeletonFadeIn 0.3s ease reverse';
            setTimeout(function() {
                if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
            }, 300);
        }
    }
    
    // Check if currently showing
    function isActive() {
        return isShowing;
    }
    
    // Listen for online/offline events
    window.addEventListener('offline', function() {
        console.log('📵 Browser reports offline');
        show();
    });
    
    window.addEventListener('online', function() {
        console.log('🌐 Browser reports online');
        if (isShowing) {
            // Verify connection actually works before hiding
            fetch('/static/images/favicon.ico', {
                method: 'HEAD',
                cache: 'no-cache'
            }).then(function(response) {
                if (response.ok) {
                    hide();
                }
            }).catch(function() {
                // Still no real connection, keep skeleton
                console.log('⚠️ Online event fired but connection still failing');
            });
        }
    });
    
    // Expose globally
    window.PwaniNetOfflineSkeleton = {
        show: show,
        hide: hide,
        isActive: isActive
    };
    
})();
