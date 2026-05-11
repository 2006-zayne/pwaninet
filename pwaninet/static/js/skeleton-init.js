/**
 * PwaniNet Skeleton Templates Initializer
 * Registers all skeleton templates for HTMX loading states
 */

(function() {
    'use strict';

    // Wait for skeleton loader to be available
    function initSkeletons() {
        if (!window.PwaniNetSkeletonLoader) {
            console.warn('PwaniNetSkeletonLoader not available, retrying...');
            setTimeout(initSkeletons, 100);
            return;
        }

        const loader = window.PwaniNetSkeletonLoader;

        // Post Feed Skeleton
        loader.registerSkeleton('post-feed', `
            <div class="skeleton-container">
                <div class="skeleton-post-card">
                    <div class="skeleton-post-header">
                        <div class="skeleton-avatar"></div>
                        <div class="skeleton-post-meta">
                            <div class="skeleton-line skeleton-name"></div>
                            <div class="skeleton-line skeleton-time"></div>
                        </div>
                    </div>
                    <div class="skeleton-post-body">
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                    </div>
                    <div class="skeleton-post-media"></div>
                    <div class="skeleton-post-actions">
                        <div class="skeleton-action"></div>
                        <div class="skeleton-action"></div>
                        <div class="skeleton-action"></div>
                    </div>
                </div>
                <div class="skeleton-post-card">
                    <div class="skeleton-post-header">
                        <div class="skeleton-avatar"></div>
                        <div class="skeleton-post-meta">
                            <div class="skeleton-line skeleton-name"></div>
                            <div class="skeleton-line skeleton-time"></div>
                        </div>
                    </div>
                    <div class="skeleton-post-body">
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                    </div>
                    <div class="skeleton-post-actions">
                        <div class="skeleton-action"></div>
                        <div class="skeleton-action"></div>
                        <div class="skeleton-action"></div>
                    </div>
                </div>
                <div class="skeleton-post-card">
                    <div class="skeleton-post-header">
                        <div class="skeleton-avatar"></div>
                        <div class="skeleton-post-meta">
                            <div class="skeleton-line skeleton-name"></div>
                            <div class="skeleton-line skeleton-time"></div>
                        </div>
                    </div>
                    <div class="skeleton-post-body">
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                    </div>
                </div>
            </div>
        `);

        // Messaging Conversation List Skeleton
        loader.registerSkeleton('messaging-list', `
            <div class="skeleton-container">
                <div class="skeleton-msg-item">
                    <div class="skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-line skeleton-name" style="width: 140px; margin-bottom: 6px;"></div>
                        <div class="skeleton-line skeleton-time" style="width: 100%; height: 12px;"></div>
                    </div>
                </div>
                <div class="skeleton-msg-item">
                    <div class="skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-line skeleton-name" style="width: 160px; margin-bottom: 6px;"></div>
                        <div class="skeleton-line skeleton-time" style="width: 100%; height: 12px;"></div>
                    </div>
                </div>
                <div class="skeleton-msg-item">
                    <div class="skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-line skeleton-name" style="width: 130px; margin-bottom: 6px;"></div>
                        <div class="skeleton-line skeleton-time" style="width: 100%; height: 12px;"></div>
                    </div>
                </div>
                <div class="skeleton-msg-item">
                    <div class="skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-line skeleton-name" style="width: 150px; margin-bottom: 6px;"></div>
                        <div class="skeleton-line skeleton-time" style="width: 100%; height: 12px;"></div>
                    </div>
                </div>
                <div class="skeleton-msg-item">
                    <div class="skeleton-avatar"></div>
                    <div style="flex: 1;">
                        <div class="skeleton-line skeleton-name" style="width: 140px; margin-bottom: 6px;"></div>
                        <div class="skeleton-line skeleton-time" style="width: 100%; height: 12px;"></div>
                    </div>
                </div>
            </div>
        `);

        // Messaging Conversation Detail Skeleton
        loader.registerSkeleton('messaging-detail', `
            <div class="skeleton-container" style="display: flex; flex-direction: column; height: 100%;">
                <div class="skeleton-msg-list" style="flex: 1; overflow-y: auto;">
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div class="skeleton-avatar-sm"></div>
                        <div class="skeleton-msg-bubble" style="width: 70%; height: 40px;"></div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 16px;">
                        <div class="skeleton-msg-bubble" style="width: 60%; height: 40px;"></div>
                    </div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px;">
                        <div class="skeleton-avatar-sm"></div>
                        <div class="skeleton-msg-bubble" style="width: 75%; height: 60px;"></div>
                    </div>
                    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 16px;">
                        <div class="skeleton-msg-bubble" style="width: 50%; height: 40px;"></div>
                    </div>
                </div>
                <div style="padding: 12px; border-top: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-input-field"></div>
                </div>
            </div>
        `);

        // Groups List Skeleton
        loader.registerSkeleton('groups-list', `
            <div class="skeleton-container">
                <div style="padding: 12px 16px; background: var(--card-bg, #ffffff); border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-line" style="width: 100px; height: 16px; margin-bottom: 12px;"></div>
                    <div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 8px;">
                        <div class="skeleton-group-item"><div class="skeleton-avatar" style="width: 60px; height: 60px;"></div><div class="skeleton-group-label"></div></div>
                        <div class="skeleton-group-item"><div class="skeleton-avatar" style="width: 60px; height: 60px;"></div><div class="skeleton-group-label"></div></div>
                        <div class="skeleton-group-item"><div class="skeleton-avatar" style="width: 60px; height: 60px;"></div><div class="skeleton-group-label"></div></div>
                        <div class="skeleton-group-item"><div class="skeleton-avatar" style="width: 60px; height: 60px;"></div><div class="skeleton-group-label"></div></div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding: 12px;">
                    <div class="skeleton-post-card" style="padding: 0; height: 180px;"><div style="width: 100%; height: 120px;"></div><div style="padding: 8px;"><div class="skeleton-line" style="width: 80%; height: 12px; margin-bottom: 4px;"></div></div></div>
                    <div class="skeleton-post-card" style="padding: 0; height: 180px;"><div style="width: 100%; height: 120px;"></div><div style="padding: 8px;"><div class="skeleton-line" style="width: 85%; height: 12px; margin-bottom: 4px;"></div></div></div>
                    <div class="skeleton-post-card" style="padding: 0; height: 180px;"><div style="width: 100%; height: 120px;"></div><div style="padding: 8px;"><div class="skeleton-line" style="width: 75%; height: 12px; margin-bottom: 4px;"></div></div></div>
                    <div class="skeleton-post-card" style="padding: 0; height: 180px;"><div style="width: 100%; height: 120px;"></div><div style="padding: 8px;"><div class="skeleton-line" style="width: 80%; height: 12px; margin-bottom: 4px;"></div></div></div>
                </div>
            </div>
        `);

        // Group Detail Skeleton
        loader.registerSkeleton('group-detail', `
            <div class="skeleton-container">
                <div style="background: var(--card-bg, #ffffff); border-bottom: 1px solid var(--border, #e2e8f0); padding: 16px;">
                    <div style="width: 100%; height: 250px; background: var(--border, #e2e8f0); border-radius: 12px; margin-bottom: 16px;"></div>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <div class="skeleton-avatar" style="width: 64px; height: 64px;"></div>
                        <div style="flex: 1;">
                            <div class="skeleton-line skeleton-name" style="width: 180px; margin-bottom: 8px;"></div>
                            <div class="skeleton-line" style="width: 120px; height: 12px;"></div>
                        </div>
                    </div>
                </div>
                <div style="display: flex; gap: 8px; padding: 12px; background: var(--card-bg, #ffffff); border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-button" style="flex: 1;"></div>
                    <div class="skeleton-button" style="flex: 1;"></div>
                </div>
                <div style="background: var(--card-bg, #ffffff); padding: 16px; margin-bottom: 8px; border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-line" style="width: 100px; height: 14px; margin-bottom: 12px;"></div>
                    <div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="width: 80%; height: 12px;"></div>
                </div>
            </div>
        `);

        // Notifications Skeleton
        loader.registerSkeleton('notifications', `
            <div class="skeleton-container">
                <div class="skeleton-notification-item"><div class="skeleton-avatar-sm"></div><div class="skeleton-notification-content"><div class="skeleton-line skeleton-notification-line"></div><div class="skeleton-line skeleton-notification-line"></div></div></div>
                <div class="skeleton-notification-item"><div class="skeleton-avatar-sm"></div><div class="skeleton-notification-content"><div class="skeleton-line skeleton-notification-line"></div><div class="skeleton-line skeleton-notification-line"></div></div></div>
                <div class="skeleton-notification-item"><div class="skeleton-avatar-sm"></div><div class="skeleton-notification-content"><div class="skeleton-line skeleton-notification-line"></div><div class="skeleton-line skeleton-notification-line"></div></div></div>
                <div class="skeleton-notification-item"><div class="skeleton-avatar-sm"></div><div class="skeleton-notification-content"><div class="skeleton-line skeleton-notification-line"></div><div class="skeleton-line skeleton-notification-line"></div></div></div>
                <div class="skeleton-notification-item"><div class="skeleton-avatar-sm"></div><div class="skeleton-notification-content"><div class="skeleton-line skeleton-notification-line"></div><div class="skeleton-line skeleton-notification-line"></div></div></div>
            </div>
        `);

        // Search Results Skeleton
        loader.registerSkeleton('search-results', `
            <div class="skeleton-container">
                <div class="skeleton-post-card"><div class="skeleton-post-header"><div class="skeleton-avatar"></div><div class="skeleton-post-meta"><div class="skeleton-line skeleton-name"></div><div class="skeleton-line skeleton-time"></div></div></div><div class="skeleton-post-body"><div class="skeleton-line skeleton-text-line"></div><div class="skeleton-line skeleton-text-line"></div></div><div class="skeleton-post-media"></div></div>
                <div class="skeleton-post-card"><div class="skeleton-post-header"><div class="skeleton-avatar"></div><div class="skeleton-post-meta"><div class="skeleton-line skeleton-name"></div><div class="skeleton-line skeleton-time"></div></div></div><div class="skeleton-post-body"><div class="skeleton-line skeleton-text-line"></div><div class="skeleton-line skeleton-text-line"></div><div class="skeleton-line skeleton-text-line"></div></div></div>
                <div class="skeleton-post-card"><div class="skeleton-post-header"><div class="skeleton-avatar"></div><div class="skeleton-post-meta"><div class="skeleton-line skeleton-name"></div><div class="skeleton-line skeleton-time"></div></div></div><div class="skeleton-post-body"><div class="skeleton-line skeleton-text-line"></div><div class="skeleton-line skeleton-text-line"></div></div><div class="skeleton-post-media"></div></div>
            </div>
        `);

        // Profile Skeleton
        loader.registerSkeleton('profile', `
            <div class="skeleton-container">
                <div style="width: 100%; height: 180px; background: var(--border, #e2e8f0); margin-bottom: 0;"></div>
                <div style="background: var(--card-bg, #ffffff); padding: 16px; border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div style="display: flex; gap: 16px; align-items: flex-start;">
                        <div class="skeleton-avatar" style="width: 80px; height: 80px; margin-top: -40px;"></div>
                        <div style="flex: 1;">
                            <div class="skeleton-line skeleton-name" style="width: 180px; margin-bottom: 8px;"></div>
                            <div class="skeleton-line" style="width: 140px; height: 12px; margin-bottom: 8px;"></div>
                            <div class="skeleton-line" style="width: 100%; height: 12px;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `);

        // Course Detail Skeleton
        loader.registerSkeleton('course-detail', `
            <div class="skeleton-container">
                <div style="background: var(--card-bg, #ffffff); padding: 16px; border-bottom: 1px solid var(--border, #e2e8f0); margin-bottom: 8px;">
                    <div class="skeleton-line" style="width: 200px; height: 16px; margin-bottom: 12px;"></div>
                    <div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div>
                    <div class="skeleton-line" style="width: 80%; height: 12px;"></div>
                </div>
                <div style="background: var(--card-bg, #ffffff); padding: 16px; margin-bottom: 8px; border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-line" style="width: 120px; height: 14px; margin-bottom: 12px;"></div>
                    <div style="margin-bottom: 16px;"><div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div><div class="skeleton-line" style="width: 100%; height: 12px; margin-bottom: 8px;"></div></div>
                </div>
            </div>
        `);

        // Post Detail Skeleton
        loader.registerSkeleton('post-detail', `
            <div class="skeleton-container">
                <div style="background: var(--card-bg, #ffffff); padding: 16px; border-bottom: 1px solid var(--border, #e2e8f0); margin-bottom: 8px;">
                    <div style="display: flex; gap: 12px; margin-bottom: 12px;">
                        <div class="skeleton-avatar"></div>
                        <div style="flex: 1;">
                            <div class="skeleton-line skeleton-name" style="width: 140px; margin-bottom: 6px;"></div>
                            <div class="skeleton-line skeleton-time" style="width: 100px;"></div>
                        </div>
                    </div>
                </div>
                <div style="background: var(--card-bg, #ffffff); padding: 16px; margin-bottom: 8px; border-bottom: 1px solid var(--border, #e2e8f0);">
                    <div class="skeleton-post-body">
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                        <div class="skeleton-line skeleton-text-line"></div>
                    </div>
                    <div class="skeleton-post-media" style="margin: 12px 0 0;"></div>
                </div>
            </div>
        `);

        console.log('✅ All skeleton templates registered');
    }

    // Initialize when DOM is ready or skeleton loader is available
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSkeletons);
    } else {
        initSkeletons();
    }

})();
