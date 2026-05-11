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
        skeletonRegistry[key] = html;
    }

    // Get skeleton HTML for a specific target
    function getSkeletonHTML(key) {
        return skeletonRegistry[key] || null;
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
        .skeleton-button {
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
        .skeleton-button::after {
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
        [data-theme="dark"] .skeleton-button::after {
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
            const target = event.detail.target;
            const skeletonKey = target.dataset.skeleton;

            if (skeletonKey) {
                showSkeleton(`#${target.id}`, skeletonKey);
            }
        });

        // Hide skeleton after content swapped
        document.addEventListener('htmx:afterSwap', function(event) {
            const target = event.detail.target;
            hideSkeleton(`#${target.id}`);
        });

        // Handle errors - keep skeleton visible if request fails
        document.addEventListener('htmx:responseError', function(event) {
            console.warn('HTMX Request Error:', event.detail);
            // Skeleton will remain visible, user can retry
        });
    }

    // Initialize on page load
    function init() {
        injectSkeletonCSS();
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
