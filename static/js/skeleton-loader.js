/**
 * PwaniNet Skeleton Loader
 * Shows skeleton screens while HTMX content is loading
 * Integrates with HTMX lifecycle events
 */

(function() {
    'use strict';

    const skeletonRegistry = {};
    const activeSkeletons = new Map();
    
    // Register a skeleton template
    function registerSkeleton(key, html) {
        console.log('[SkeletonLoader] Registering skeleton:', key);
        skeletonRegistry[key] = html;
        console.log('[SkeletonLoader] Registered skeletons:', Object.keys(skeletonRegistry));
    }

    // Get skeleton HTML for a specific target
    function getSkeletonHTML(key) {
        console.log('[SkeletonLoader] Getting skeleton for key:', key);
        console.log('[SkeletonLoader] Available skeleton keys:', Object.keys(skeletonRegistry));
        const html = skeletonRegistry[key] || null;
        console.log('[SkeletonLoader] Found skeleton:', !!html);
        return html;
    }

    // Show skeleton for a target element
    function showSkeleton(targetSelector, skeletonKey) {
        const target = document.querySelector(targetSelector);
        if (!target) return;

        const skeletonHTML = getSkeletonHTML(skeletonKey);
        if (!skeletonHTML) {
            console.warn(`Skeleton "${skeletonKey}" not found`);
            return;
        }

        // Store original content in data attribute for recovery if needed
        if (!target.dataset.originalContent) {
            target.dataset.originalContent = target.innerHTML;
        }

        // Replace with skeleton
        target.innerHTML = skeletonHTML;
        target.classList.add('skeleton-loading');
        target.dataset.skeletonActive = 'true';

        // Track active skeleton
        activeSkeletons.set(targetSelector, {
            key: skeletonKey,
            timestamp: Date.now()
        });
    }

    // Hide skeleton for a target element
    function hideSkeleton(targetSelector) {
        const target = document.querySelector(targetSelector);
        if (!target) return;

        target.classList.remove('skeleton-loading');
        target.removeAttribute('data-skeleton-active');
        activeSkeletons.delete(targetSelector);
    }

    // Inject skeleton CSS if not already present
    function injectSkeletonCSS() {
        if (document.getElementById('skeleton-loader-styles')) return;

        const css = `
        <style id="skeleton-loader-styles">
        /* Skeleton Loading State */
        .skeleton-loading {
            animation: skeletonIn 0.2s ease;
        }

        @keyframes skeletonIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        /* Skeleton Shimmer Animation */
        .skeleton-line,
        .skeleton-avatar,
        .skeleton-avatar-sm,
        .skeleton-post-card,
        .skeleton-search-bar,
        .skeleton-group-item,
        .skeleton-notification-item,
        .skeleton-msg-bubble,
        .skeleton-input-field,
        .skeleton-button,
        .skeleton-cover,
        .skeleton-name,
        .skeleton-username,
        .skeleton-bio,
        .skeleton-stat,
        .skeleton-label,
        .skeleton-section-title,
        .skeleton-detail-row,
        .skeleton-tab,
        .skeleton-post-avatar,
        .skeleton-post-username,
        .skeleton-post-time,
        .skeleton-post-text,
        .skeleton-post-media,
        .skeleton-action,
        .skeleton-comment-avatar,
        .skeleton-comment-input,
        .skeleton-avatar-link,
        .skeleton-search-input,
        .skeleton-explore-title,
        .skeleton-explore-link,
        .skeleton-group-explore-item,
        .skeleton-post-menu,
        .skeleton-page-title,
        .skeleton-new-group-btn,
        .skeleton-sidebar-label,
        .skeleton-my-group-row,
        .skeleton-tip-title,
        .skeleton-tip-text,
        .skeleton-section-title,
        .skeleton-group-count,
        .skeleton-group-card-avatar,
        .skeleton-group-name,
        .skeleton-group-badge,
        .skeleton-group-desc,
        .skeleton-group-members,
        .skeleton-group-status,
        .skeleton-group-view-btn,
        .skeleton-unread-badge,
        .skeleton-filter-dropdown,
        .skeleton-time-label,
        .skeleton-notif-avatar,
        .skeleton-notif-username,
        .skeleton-notif-time,
        .skeleton-notif-message,
        .skeleton-notif-actions,
        .skeleton-action-btn {
            position: relative;
            overflow: hidden;
            background: var(--border, #e2e8f0);
            border-radius: 4px;
        }

        .skeleton-avatar,
        .skeleton-avatar-sm,
        .skeleton-group-item::after {
            border-radius: 50%;
        }

        .skeleton-post-card {
            border-radius: 12px;
            border: 1px solid var(--border, #e2e8f0);
        }

        /* Shimmer effect */
        .skeleton-line::after,
        .skeleton-avatar::after,
        .skeleton-avatar-sm::after,
        .skeleton-post-card::after,
        .skeleton-search-bar::after,
        .skeleton-group-item::after,
        .skeleton-notification-item::after,
        .skeleton-msg-bubble::after,
        .skeleton-input-field::after,
        .skeleton-button::after,
        .skeleton-cover::after,
        .skeleton-name::after,
        .skeleton-username::after,
        .skeleton-bio::after,
        .skeleton-stat::after,
        .skeleton-label::after,
        .skeleton-section-title::after,
        .skeleton-detail-row::after,
        .skeleton-tab::after,
        .skeleton-post-avatar::after,
        .skeleton-post-username::after,
        .skeleton-post-time::after,
        .skeleton-post-text::after,
        .skeleton-post-media::after,
        .skeleton-action::after,
        .skeleton-comment-avatar::after,
        .skeleton-comment-input::after,
        .skeleton-avatar-link::after,
        .skeleton-search-input::after,
        .skeleton-explore-title::after,
        .skeleton-explore-link::after,
        .skeleton-group-explore-item::after,
        .skeleton-post-menu::after,
        .skeleton-page-title::after,
        .skeleton-new-group-btn::after,
        .skeleton-sidebar-label::after,
        .skeleton-my-group-row::after,
        .skeleton-tip-title::after,
        .skeleton-tip-text::after,
        .skeleton-group-count::after,
        .skeleton-group-card-avatar::after,
        .skeleton-group-name::after,
        .skeleton-group-badge::after,
        .skeleton-group-desc::after,
        .skeleton-group-members::after,
        .skeleton-group-status::after,
        .skeleton-group-view-btn::after,
        .skeleton-unread-badge::after,
        .skeleton-filter-dropdown::after,
        .skeleton-time-label::after,
        .skeleton-notif-avatar::after,
        .skeleton-notif-username::after,
        .skeleton-notif-time::after,
        .skeleton-notif-message::after,
        .skeleton-notif-actions::after,
        .skeleton-action-btn::after {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255, 255, 255, 0.4) 50%,
                transparent 100%
            );
            animation: shimmer 1.5s infinite;
        }

        [data-theme="dark"] .skeleton-line::after,
        [data-theme="dark"] .skeleton-avatar::after,
        [data-theme="dark"] .skeleton-avatar-sm::after,
        [data-theme="dark"] .skeleton-post-card::after,
        [data-theme="dark"] .skeleton-search-bar::after,
        [data-theme="dark"] .skeleton-group-item::after,
        [data-theme="dark"] .skeleton-notification-item::after,
        [data-theme="dark"] .skeleton-msg-bubble::after,
        [data-theme="dark"] .skeleton-input-field::after,
        [data-theme="dark"] .skeleton-button::after,
        [data-theme="dark"] .skeleton-cover::after,
        [data-theme="dark"] .skeleton-name::after,
        [data-theme="dark"] .skeleton-username::after,
        [data-theme="dark"] .skeleton-bio::after,
        [data-theme="dark"] .skeleton-stat::after,
        [data-theme="dark"] .skeleton-label::after,
        [data-theme="dark"] .skeleton-section-title::after,
        [data-theme="dark"] .skeleton-detail-row::after,
        [data-theme="dark"] .skeleton-tab::after,
        [data-theme="dark"] .skeleton-post-avatar::after,
        [data-theme="dark"] .skeleton-post-username::after,
        [data-theme="dark"] .skeleton-post-time::after,
        [data-theme="dark"] .skeleton-post-text::after,
        [data-theme="dark"] .skeleton-post-media::after,
        [data-theme="dark"] .skeleton-action::after,
        [data-theme="dark"] .skeleton-comment-avatar::after,
        [data-theme="dark"] .skeleton-comment-input::after,
        [data-theme="dark"] .skeleton-avatar-link::after,
        [data-theme="dark"] .skeleton-search-input::after,
        [data-theme="dark"] .skeleton-explore-title::after,
        [data-theme="dark"] .skeleton-explore-link::after,
        [data-theme="dark"] .skeleton-group-explore-item::after,
        [data-theme="dark"] .skeleton-post-menu::after,
        [data-theme="dark"] .skeleton-page-title::after,
        [data-theme="dark"] .skeleton-new-group-btn::after,
        [data-theme="dark"] .skeleton-sidebar-label::after,
        [data-theme="dark"] .skeleton-my-group-row::after,
        [data-theme="dark"] .skeleton-tip-title::after,
        [data-theme="dark"] .skeleton-tip-text::after,
        [data-theme="dark"] .skeleton-group-count::after,
        [data-theme="dark"] .skeleton-group-card-avatar::after,
        [data-theme="dark"] .skeleton-group-name::after,
        [data-theme="dark"] .skeleton-group-badge::after,
        [data-theme="dark"] .skeleton-group-desc::after,
        [data-theme="dark"] .skeleton-group-members::after,
        [data-theme="dark"] .skeleton-group-status::after,
        [data-theme="dark"] .skeleton-group-view-btn::after,
        [data-theme="dark"] .skeleton-unread-badge::after,
        [data-theme="dark"] .skeleton-filter-dropdown::after,
        [data-theme="dark"] .skeleton-time-label::after,
        [data-theme="dark"] .skeleton-notif-avatar::after,
        [data-theme="dark"] .skeleton-notif-username::after,
        [data-theme="dark"] .skeleton-notif-time::after,
        [data-theme="dark"] .skeleton-notif-message::after,
        [data-theme="dark"] .skeleton-notif-actions::after,
        [data-theme="dark"] .skeleton-action-btn::after {
            background: linear-gradient(
                90deg,
                transparent 0%,
                rgba(255, 255, 255, 0.08) 50%,
                transparent 100%
            );
        }

        @keyframes shimmer {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(100%); }
        }

        /* Page specific skeletons */

        /* Post Feed Skeleton */
        .skeleton-post-card {
            background: var(--card-bg, #ffffff);
            margin: 8px;
            padding: 12px;
        }

        .skeleton-post-header {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
        }

        .skeleton-avatar {
            width: 48px;
            height: 48px;
            flex-shrink: 0;
        }

        .skeleton-post-meta {
            flex: 1;
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

        .skeleton-post-body {
            margin-bottom: 12px;
        }

        .skeleton-text-line {
            width: 100%;
            height: 14px;
            margin-bottom: 8px;
        }

        .skeleton-text-line:last-child {
            width: 60%;
        }

        .skeleton-post-media {
            width: 100%;
            height: 200px;
            margin-bottom: 12px;
            border-radius: 8px;
        }

        .skeleton-post-actions {
            display: flex;
            justify-content: space-around;
            padding-top: 8px;
            border-top: 1px solid var(--border, #e2e8f0);
        }

        .skeleton-action {
            width: 50px;
            height: 16px;
        }

        /* Message Skeleton */
        .skeleton-msg-list {
            padding: 12px;
        }

        .skeleton-msg-item {
            display: flex;
            gap: 12px;
            margin-bottom: 12px;
            padding: 8px;
            background: var(--card-bg, #ffffff);
            border-radius: 8px;
        }

        .skeleton-msg-bubble {
            flex: 1;
            height: 60px;
            border-radius: 8px;
        }

        /* Notification Skeleton */
        .skeleton-notification-item {
            display: flex;
            gap: 12px;
            padding: 12px;
            margin-bottom: 8px;
            background: var(--card-bg, #ffffff);
            border-radius: 8px;
            border-left: 3px solid var(--primary, #2563eb);
        }

        .skeleton-notification-content {
            flex: 1;
        }

        .skeleton-notification-line {
            width: 100%;
            height: 12px;
            margin-bottom: 6px;
        }

        .skeleton-notification-line:last-child {
            width: 50%;
        }

        /* Group/Card Skeleton */
        .skeleton-group-item {
            width: 60px;
            flex-shrink: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
        }

        .skeleton-group-item::after {
            display: block;
            width: 48px;
            height: 48px;
        }

        .skeleton-group-label {
            width: 50px;
            height: 12px;
        }

        /* Search/Input Skeleton */
        .skeleton-search-bar {
            height: 40px;
            border-radius: 20px;
        }

        .skeleton-input-field {
            width: 100%;
            height: 40px;
            border-radius: 8px;
            margin-bottom: 8px;
        }

        /* Button Skeleton */
        .skeleton-button {
            height: 36px;
            min-width: 100px;
            border-radius: 6px;
        }

        /* New Skeleton Classes for Rebuilt Skeletons */
        
        /* Profile Skeleton */
        .skeleton-cover {
            width: 100%;
            height: 160px;
            border-radius: 12px 12px 0 0;
        }

        .skeleton-avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 4px solid var(--card-bg, #fff);
            margin: 0 auto;
        }

        .skeleton-name {
            width: 180px;
            height: 24px;
            border-radius: 4px;
        }

        .skeleton-username {
            width: 120px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-bio {
            width: 100%;
            height: 40px;
            border-radius: 8px;
        }

        .skeleton-stat {
            width: 40px;
            height: 20px;
            border-radius: 4px;
        }

        .skeleton-label {
            width: 50px;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-section-title {
            width: 140px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-detail-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .skeleton-detail-row::before,
        .skeleton-detail-row::after {
            content: '';
            display: block;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-detail-row::before {
            width: 80px;
        }

        .skeleton-detail-row::after {
            width: 120px;
        }

        .skeleton-tab {
            width: 60px;
            height: 36px;
            border-radius: 4px;
        }

        /* Post Skeleton */
        .skeleton-post-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .skeleton-post-username {
            width: 120px;
            height: 16px;
            border-radius: 4px;
            margin-bottom: 6px;
        }

        .skeleton-post-time {
            width: 80px;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-post-menu {
            width: 32px;
            height: 32px;
            border-radius: 4px;
            flex-shrink: 0;
        }

        .skeleton-post-text {
            width: 100%;
            height: 16px;
            border-radius: 4px;
            margin-bottom: 8px;
        }

        .skeleton-post-text.short {
            width: 60%;
        }

        .skeleton-post-media {
            width: 100%;
            height: 300px;
            border-radius: 8px;
            border-top: 1px solid var(--border, #e2e8f0);
            border-bottom: 1px solid var(--border, #e2e8f0);
        }

        .skeleton-action {
            width: 60px;
            height: 20px;
            border-radius: 4px;
        }

        .skeleton-comment-avatar {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .skeleton-comment-input {
            width: 100%;
            height: 42px;
            border-radius: 21px;
        }

        /* Home Feed Skeleton */
        .skeleton-avatar-link {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            flex-shrink: 0;
            border: 2px solid #fff;
            box-shadow: 0 1px 4px rgba(0,0,0,0.12);
        }

        .skeleton-search-input {
            width: 100%;
            height: 42px;
            border-radius: 999px;
        }

        .skeleton-explore-title {
            width: 140px;
            height: 14px;
            border-radius: 4px;
        }

        .skeleton-explore-link {
            width: 60px;
            height: 13px;
            border-radius: 4px;
        }

        .skeleton-group-explore-item {
            width: 70px;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }

        .skeleton-group-explore-item::before {
            content: '';
            width: 56px;
            height: 56px;
            border-radius: 50%;
            border: 2px solid #fff;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .skeleton-group-explore-item::after {
            content: '';
            width: 50px;
            height: 12px;
            border-radius: 4px;
        }

        /* Groups Skeleton */
        .skeleton-page-title {
            width: 180px;
            height: 32px;
            border-radius: 8px;
        }

        .skeleton-new-group-btn {
            width: 120px;
            height: 40px;
            border-radius: 20px;
        }

        .skeleton-sidebar-label {
            width: 100px;
            height: 14px;
            border-radius: 4px;
        }

        .skeleton-my-group-row {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px;
            border-radius: 8px;
        }

        .skeleton-my-group-row::before {
            content: '';
            width: 40px;
            height: 40px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .skeleton-my-group-row::after {
            content: '';
            flex: 1;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-tip-title {
            width: 140px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-tip-text {
            width: 100%;
            height: 12px;
            border-radius: 4px;
            margin-bottom: 6px;
        }

        .skeleton-group-count {
            width: 60px;
            height: 20px;
            border-radius: 4px;
        }

        .skeleton-group-card-avatar {
            width: 56px;
            height: 56px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .skeleton-group-name {
            width: 120px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-group-badge {
            width: 40px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-group-desc {
            width: 100%;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-group-members {
            width: 60px;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-group-status {
            width: 50px;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-group-view-btn {
            width: 60px;
            height: 28px;
            border-radius: 14px;
        }

        /* Notifications Skeleton */
        .skeleton-unread-badge {
            width: 40px;
            height: 24px;
            border-radius: 12px;
        }

        .skeleton-filter-dropdown {
            width: 100%;
            height: 42px;
            border-radius: 8px;
        }

        .skeleton-time-label {
            width: 80px;
            height: 14px;
            border-radius: 4px;
        }

        .skeleton-notif-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            border: 1px solid var(--border, #e2e8f0);
            flex-shrink: 0;
        }

        .skeleton-notif-username {
            width: 100px;
            height: 16px;
            border-radius: 4px;
        }

        .skeleton-notif-time {
            width: 60px;
            height: 12px;
            border-radius: 4px;
        }

        .skeleton-notif-message {
            width: 100%;
            height: 14px;
            border-radius: 4px;
            margin-bottom: 6px;
        }

        .skeleton-notif-message.short {
            width: 70%;
        }

        .skeleton-notif-actions {
            display: flex;
            gap: 8px;
            margin-top: 8px;
        }

        .skeleton-notif-actions::before,
        .skeleton-notif-actions::after {
            content: '';
            width: 60px;
            height: 32px;
            border-radius: 16px;
        }

        .skeleton-action-btn {
            width: 120px;
            height: 40px;
            border-radius: 20px;
        }

        /* Loading container */
        .skeleton-container {
            animation: skeletonIn 0.2s ease;
        }

        /* Fade transition for content swap */
        @keyframes contentFadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .htmx-swapping.htmx-settling > * {
            animation: contentFadeIn 0.2s ease;
        }
        </style>
        `;

        document.head.insertAdjacentHTML('beforeend', css);
    }

    // Set up HTMX integration
    function initHTMXIntegration() {
        // Listen for HTMX requests
        document.addEventListener('htmx:beforeRequest', function(event) {
            const timestamp = new Date().toISOString();
            const target = event.detail.target;
            const skeletonKey = target.dataset.skeleton;
            const requestInfo = {
                timestamp: timestamp,
                event: 'htmx:beforeRequest',
                caller: 'skeleton-loader.js initHTMXIntegration()',
                reason: 'HTMX request starting',
                requestURL: event.detail.xhr?.responseURL || event.detail.pathInfo?.requestPath || 'unknown',
                targetId: target?.id || 'unknown',
                skeletonKey: skeletonKey || 'none',
                willShowSkeleton: !!skeletonKey
            };
            console.log('[SkeletonLoader] HTMX beforeRequest', requestInfo);

            if (skeletonKey) {
                console.log('[SkeletonLoader] Showing skeleton for', target.id, 'with key', skeletonKey);
                showSkeleton(`#${target.id}`, skeletonKey);
            } else {
                console.log('[SkeletonLoader] No skeleton key for target', target.id, '- skipping skeleton');
            }
        });

        // Hide skeleton after content swapped
        document.addEventListener('htmx:afterSwap', function(event) {
            const timestamp = new Date().toISOString();
            const target = event.detail.target;
            const requestInfo = {
                timestamp: timestamp,
                event: 'htmx:afterSwap',
                caller: 'skeleton-loader.js initHTMXIntegration()',
                reason: 'HTMX content swapped into DOM',
                requestURL: event.detail.xhr?.responseURL || 'unknown',
                requestStatus: event.detail.xhr?.status || 'unknown',
                targetId: target?.id || 'unknown',
                willHideSkeleton: true
            };
            console.log('[SkeletonLoader] HTMX afterSwap', requestInfo);
            console.log('[SkeletonLoader] Hiding skeleton for', target.id);
            hideSkeleton(`#${target.id}`);
        });

        // Handle errors - keep skeleton visible if request fails
        document.addEventListener('htmx:responseError', function(event) {
            const timestamp = new Date().toISOString();
            const requestInfo = {
                timestamp: timestamp,
                event: 'htmx:responseError',
                caller: 'skeleton-loader.js initHTMXIntegration()',
                reason: 'HTMX request failed',
                requestURL: event.detail.xhr?.responseURL || 'unknown',
                requestStatus: event.detail.xhr?.status || 'unknown',
                targetId: event.detail.target?.id || 'unknown',
                errorDetail: event.detail,
                willKeepSkeletonVisible: true
            };
            console.error('[SkeletonLoader] HTMX responseError', requestInfo);
            console.warn('[SkeletonLoader] Skeleton will remain visible due to error - user can retry');
            // Skeleton will remain visible, user can retry
        });
    }

    // Initialize on page load
    function init() {
        injectSkeletonCSS();
        // HTMX integration re-enabled for feed skeleton loading when fetching more posts
        initHTMXIntegration();
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose public API
    window.PwaniNetSkeletonLoader = {
        registerSkeleton,
        getSkeletonHTML,
        showSkeleton,
        hideSkeleton,
        getActiveSkeletons: () => Object.fromEntries(activeSkeletons),
        clear: () => {
            activeSkeletons.clear();
            document.querySelectorAll('[data-skeleton-active]').forEach(el => {
                el.classList.remove('skeleton-loading');
                el.removeAttribute('data-skeleton-active');
            });
        }
    };

})();
