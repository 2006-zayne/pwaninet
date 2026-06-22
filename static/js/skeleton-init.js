/**
 * PwaniNet Skeleton Templates Initializer
 * Registers all skeleton templates for HTMX loading states
 * Re-enabled for feed skeleton loading when fetching more posts
 */

(function() {
    'use strict';

    // Wait for skeleton loader to be available
    function initSkeletons() {
        if (!window.PwaniNetSkeletonLoader) {
            console.warn('[SkeletonInit] PwaniNetSkeletonLoader not available, retrying...');
            setTimeout(initSkeletons, 100);
            return;
        }

        console.log('[SkeletonInit] PwaniNetSkeletonLoader found, registering skeletons...');
        const loader = window.PwaniNetSkeletonLoader;

        // Post Feed Skeleton - Updated to match real home.html structure
        console.log('[SkeletonInit] Registering post-feed skeleton...');
        loader.registerSkeleton('post-feed', `
            <div class="container-fluid p-0">
                <header class="search-header">
                    <div class="search-inner">
                        <div class="skeleton-avatar-link"></div>
                        <div class="search-form">
                            <div class="skeleton-search-input"></div>
                        </div>
                    </div>
                </header>
                <main>
                    <div class="content-wrapper">
                        <div id="main-content-area">
                            <div class="groups-explore-section">
                                <div class="groups-explore-header">
                                    <div class="skeleton-explore-title"></div>
                                    <div class="skeleton-explore-link"></div>
                                </div>
                                <div class="groups-explore-list">
                                    <div class="skeleton-group-explore-item"></div>
                                    <div class="skeleton-group-explore-item"></div>
                                    <div class="skeleton-group-explore-item"></div>
                                    <div class="skeleton-group-explore-item"></div>
                                </div>
                            </div>
                            <div class="feed-sector">
                                <div class="post-card shadow-sm mb-2 bg-white rounded-3 overflow-hidden border-0 skeleton-post">
                                    <div class="d-flex align-items-center p-3 border-bottom">
                                        <div class="skeleton-post-avatar"></div>
                                        <div class="flex-grow-1 ms-3">
                                            <div class="skeleton-post-username"></div>
                                            <div class="skeleton-post-time"></div>
                                        </div>
                                        <div class="skeleton-post-menu"></div>
                                    </div>
                                    <div class="px-3 pb-3">
                                        <div class="skeleton-post-text"></div>
                                        <div class="skeleton-post-text"></div>
                                        <div class="skeleton-post-text short"></div>
                                    </div>
                                    <div class="skeleton-post-media"></div>
                                    <div class="d-flex align-items-center justify-content-between px-3 py-2 border-top">
                                        <div class="d-flex align-items-center gap-4">
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                        </div>
                                    </div>
                                    <div class="px-3 pb-3 pt-1 border-top bg-white">
                                        <div class="d-flex align-items-center gap-2">
                                            <div class="skeleton-comment-avatar"></div>
                                            <div class="flex-grow-1">
                                                <div class="skeleton-comment-input"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="post-card shadow-sm mb-2 bg-white rounded-3 overflow-hidden border-0 skeleton-post">
                                    <div class="d-flex align-items-center p-3 border-bottom">
                                        <div class="skeleton-post-avatar"></div>
                                        <div class="flex-grow-1 ms-3">
                                            <div class="skeleton-post-username"></div>
                                            <div class="skeleton-post-time"></div>
                                        </div>
                                        <div class="skeleton-post-menu"></div>
                                    </div>
                                    <div class="px-3 pb-3">
                                        <div class="skeleton-post-text"></div>
                                        <div class="skeleton-post-text"></div>
                                    </div>
                                    <div class="d-flex align-items-center justify-content-between px-3 py-2 border-top">
                                        <div class="d-flex align-items-center gap-4">
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                        </div>
                                    </div>
                                    <div class="px-3 pb-3 pt-1 border-top bg-white">
                                        <div class="d-flex align-items-center gap-2">
                                            <div class="skeleton-comment-avatar"></div>
                                            <div class="flex-grow-1">
                                                <div class="skeleton-comment-input"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                <div class="post-card shadow-sm mb-2 bg-white rounded-3 overflow-hidden border-0 skeleton-post">
                                    <div class="d-flex align-items-center p-3 border-bottom">
                                        <div class="skeleton-post-avatar"></div>
                                        <div class="flex-grow-1 ms-3">
                                            <div class="skeleton-post-username"></div>
                                            <div class="skeleton-post-time"></div>
                                        </div>
                                        <div class="skeleton-post-menu"></div>
                                    </div>
                                    <div class="px-3 pb-3">
                                        <div class="skeleton-post-text"></div>
                                        <div class="skeleton-post-text"></div>
                                        <div class="skeleton-post-text"></div>
                                    </div>
                                    <div class="skeleton-post-media"></div>
                                    <div class="d-flex align-items-center justify-content-between px-3 py-2 border-top">
                                        <div class="d-flex align-items-center gap-4">
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                            <div class="skeleton-action"></div>
                                        </div>
                                    </div>
                                    <div class="px-3 pb-3 pt-1 border-top bg-white">
                                        <div class="d-flex align-items-center gap-2">
                                            <div class="skeleton-comment-avatar"></div>
                                            <div class="flex-grow-1">
                                                <div class="skeleton-comment-input"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        `);
        console.log('[SkeletonInit] post-feed skeleton registered successfully');

        // Messaging Conversation List Skeleton
        console.log('[SkeletonInit] Registering messaging-list skeleton...');
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

        // Groups List Skeleton - Updated to match real groups_dashboard.html structure
        loader.registerSkeleton('groups-list', `
            <div class="page-wrap">
                <div class="page-header">
                    <div class="skeleton-page-title"></div>
                    <div class="skeleton-new-group-btn"></div>
                </div>
                <div class="groups-layout">
                    <aside class="sidebar-sticky">
                        <div class="card">
                            <div class="card-body">
                                <div class="skeleton-sidebar-label"></div>
                                <div class="my-groups-scroll">
                                    <div class="skeleton-my-group-row"></div>
                                    <div class="skeleton-my-group-row"></div>
                                    <div class="skeleton-my-group-row"></div>
                                </div>
                            </div>
                        </div>
                        <div class="tip-card">
                            <div class="skeleton-tip-title"></div>
                            <div class="skeleton-tip-text"></div>
                            <div class="skeleton-tip-text"></div>
                        </div>
                    </aside>
                    <main>
                        <div class="section-header">
                            <div class="skeleton-section-title"></div>
                            <div class="skeleton-group-count"></div>
                        </div>
                        <div class="groups-grid">
                            <a class="group-card skeleton-group-card">
                                <div class="group-card-bar"></div>
                                <div class="group-card-body">
                                    <div class="group-card-header">
                                        <div class="skeleton-group-card-avatar"></div>
                                        <div class="group-card-info">
                                            <div class="group-card-top">
                                                <div class="skeleton-group-name"></div>
                                                <div class="skeleton-group-badge"></div>
                                            </div>
                                            <div class="skeleton-group-desc"></div>
                                        </div>
                                    </div>
                                    <div class="group-card-footer">
                                        <div class="skeleton-group-members"></div>
                                        <div class="skeleton-group-status"></div>
                                        <div class="skeleton-group-view-btn"></div>
                                    </div>
                                </div>
                            </a>
                            <a class="group-card skeleton-group-card">
                                <div class="group-card-bar"></div>
                                <div class="group-card-body">
                                    <div class="group-card-header">
                                        <div class="skeleton-group-card-avatar"></div>
                                        <div class="group-card-info">
                                            <div class="group-card-top">
                                                <div class="skeleton-group-name"></div>
                                                <div class="skeleton-group-badge"></div>
                                            </div>
                                            <div class="skeleton-group-desc"></div>
                                        </div>
                                    </div>
                                    <div class="group-card-footer">
                                        <div class="skeleton-group-members"></div>
                                        <div class="skeleton-group-status"></div>
                                        <div class="skeleton-group-view-btn"></div>
                                    </div>
                                </div>
                            </a>
                            <a class="group-card skeleton-group-card">
                                <div class="group-card-bar"></div>
                                <div class="group-card-body">
                                    <div class="group-card-header">
                                        <div class="skeleton-group-card-avatar"></div>
                                        <div class="group-card-info">
                                            <div class="group-card-top">
                                                <div class="skeleton-group-name"></div>
                                                <div class="skeleton-group-badge"></div>
                                            </div>
                                            <div class="skeleton-group-desc"></div>
                                        </div>
                                    </div>
                                    <div class="group-card-footer">
                                        <div class="skeleton-group-members"></div>
                                        <div class="skeleton-group-status"></div>
                                        <div class="skeleton-group-view-btn"></div>
                                    </div>
                                </div>
                            </a>
                            <a class="group-card skeleton-group-card">
                                <div class="group-card-bar"></div>
                                <div class="group-card-body">
                                    <div class="group-card-header">
                                        <div class="skeleton-group-card-avatar"></div>
                                        <div class="group-card-info">
                                            <div class="group-card-top">
                                                <div class="skeleton-group-name"></div>
                                                <div class="skeleton-group-badge"></div>
                                            </div>
                                            <div class="skeleton-group-desc"></div>
                                        </div>
                                    </div>
                                    <div class="group-card-footer">
                                        <div class="skeleton-group-members"></div>
                                        <div class="skeleton-group-status"></div>
                                        <div class="skeleton-group-view-btn"></div>
                                    </div>
                                </div>
                            </a>
                        </div>
                    </main>
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

        // Notifications Skeleton - Updated to match real notifications.html structure
        loader.registerSkeleton('notifications', `
            <div class="page-wrap">
                <div class="page-header">
                    <div class="skeleton-page-title"></div>
                    <div class="skeleton-unread-badge"></div>
                </div>
                <div class="filter-dropdown-container">
                    <div class="skeleton-filter-dropdown"></div>
                </div>
                <div class="card" id="notification-list">
                    <div class="card-body" style="padding: 0;">
                        <div class="time-section">
                            <div class="time-section-header">
                                <div class="skeleton-time-label"></div>
                            </div>
                            <div class="list-group-item list-group-item-action border-bottom py-4 px-4 skeleton-notif-item">
                                <div class="d-flex gap-2">
                                    <div class="skeleton-notif-avatar"></div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <div class="skeleton-notif-username"></div>
                                            <div class="skeleton-notif-time"></div>
                                        </div>
                                        <div class="skeleton-notif-message"></div>
                                        <div class="skeleton-notif-message short"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="list-group-item list-group-item-action border-bottom py-4 px-4 skeleton-notif-item">
                                <div class="d-flex gap-2">
                                    <div class="skeleton-notif-avatar"></div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <div class="skeleton-notif-username"></div>
                                            <div class="skeleton-notif-time"></div>
                                        </div>
                                        <div class="skeleton-notif-message"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="list-group-item list-group-item-action border-bottom py-4 px-4 skeleton-notif-item">
                                <div class="d-flex gap-2">
                                    <div class="skeleton-notif-avatar"></div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <div class="skeleton-notif-username"></div>
                                            <div class="skeleton-notif-time"></div>
                                        </div>
                                        <div class="skeleton-notif-message"></div>
                                        <div class="skeleton-notif-actions"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="time-section">
                            <div class="time-section-header">
                                <div class="skeleton-time-label"></div>
                            </div>
                            <div class="list-group-item list-group-item-action border-bottom py-4 px-4 skeleton-notif-item">
                                <div class="d-flex gap-2">
                                    <div class="skeleton-notif-avatar"></div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <div class="skeleton-notif-username"></div>
                                            <div class="skeleton-notif-time"></div>
                                        </div>
                                        <div class="skeleton-notif-message"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="list-group-item list-group-item-action border-bottom py-4 px-4 skeleton-notif-item">
                                <div class="d-flex gap-2">
                                    <div class="skeleton-notif-avatar"></div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-center mb-1">
                                            <div class="skeleton-notif-username"></div>
                                            <div class="skeleton-notif-time"></div>
                                        </div>
                                        <div class="skeleton-notif-message"></div>
                                        <div class="skeleton-notif-message short"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 1.5rem; display: flex; justify-content: center; gap: 1rem; flex-wrap: wrap;">
                    <div class="skeleton-action-btn"></div>
                    <div class="skeleton-action-btn"></div>
                    <div class="skeleton-action-btn"></div>
                </div>
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

        // Profile Skeleton - Updated to match real profile.html structure
        loader.registerSkeleton('profile', `
            <div class="container-fluid p-0 profile-mobile-fullscreen profile-content">
                <div class="row g-3 g-md-4 justify-content-center">
                    <div class="col-12 col-md-6 col-lg-5 col-xl-4">
                        <div class="sticky-top" style="top: 85px; z-index: 10;">
                            <div class="post-card shadow-sm mb-4 border-0 rounded-3 overflow-visible profile-card">
                                <div class="cover-container skeleton-cover"></div>
                                <div class="avatar-wrapper">
                                    <div class="avatar-inner">
                                        <div class="avatar skeleton-avatar"></div>
                                    </div>
                                </div>
                                <div class="text-center pt-5 pb-3 px-3">
                                    <div class="skeleton-name" style="width: 180px; height: 24px; margin: 0 auto 8px;"></div>
                                    <div class="skeleton-username" style="width: 120px; height: 16px; margin: 0 auto 12px;"></div>
                                    <div class="bg-light rounded-3 p-2 mb-3 skeleton-bio"></div>
                                    <div class="skeleton-button" style="width: 100%; height: 36px; margin-bottom: 8px;"></div>
                                    <div class="skeleton-button" style="width: 100%; height: 36px;"></div>
                                </div>
                                <div class="row g-0 border-top text-center py-3">
                                    <div class="col-4 border-end">
                                        <div class="skeleton-stat" style="width: 40px; height: 20px; margin: 0 auto 4px;"></div>
                                        <div class="skeleton-label" style="width: 50px; height: 12px; margin: 0 auto;"></div>
                                    </div>
                                    <div class="col-4 border-end">
                                        <div class="skeleton-stat" style="width: 40px; height: 20px; margin: 0 auto 4px;"></div>
                                        <div class="skeleton-label" style="width: 50px; height: 12px; margin: 0 auto;"></div>
                                    </div>
                                    <div class="col-4">
                                        <div class="skeleton-stat" style="width: 40px; height: 20px; margin: 0 auto 4px;"></div>
                                        <div class="skeleton-label" style="width: 40px; height: 12px; margin: 0 auto;"></div>
                                    </div>
                                </div>
                            </div>
                            <div class="post-card p-3 shadow-sm border-0 mb-3">
                                <div class="skeleton-section-title" style="width: 140px; height: 16px; margin-bottom: 12px;"></div>
                                <div class="skeleton-detail-row" style="margin-bottom: 8px;"></div>
                                <div class="skeleton-detail-row" style="margin-bottom: 8px;"></div>
                                <div class="skeleton-detail-row"></div>
                            </div>
                            <div class="post-card p-3 shadow-sm border-0 mt-4">
                                <div class="skeleton-section-title" style="width: 120px; height: 16px; margin-bottom: 12px;"></div>
                                <div class="skeleton-line" style="width: 100%; height: 14px; margin-bottom: 8px;"></div>
                                <div class="skeleton-line" style="width: 80%; height: 14px; margin-bottom: 8px;"></div>
                                <div class="skeleton-line" style="width: 90%; height: 14px;"></div>
                                <div class="skeleton-button" style="width: 100%; height: 36px; margin-top: 12px;"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-12 col-md-6 col-lg-7 col-xl-6">
                        <ul class="nav nav-tabs mb-3 px-2">
                            <li class="nav-item">
                                <div class="skeleton-tab" style="width: 60px; height: 36px;"></div>
                            </li>
                            <li class="nav-item">
                                <div class="skeleton-tab" style="width: 100px; height: 36px;"></div>
                            </li>
                        </ul>
                        <div class="tab-content">
                            <div class="tab-pane fade show active">
                                <div class="intel-stream">
                                    <div class="post-card shadow-sm mb-2 bg-white rounded-3 overflow-hidden border-0 skeleton-post">
                                        <div class="d-flex align-items-center p-3 border-bottom">
                                            <div class="skeleton-post-avatar"></div>
                                            <div class="flex-grow-1 ms-3">
                                                <div class="skeleton-post-username"></div>
                                                <div class="skeleton-post-time"></div>
                                            </div>
                                        </div>
                                        <div class="px-3 pb-3">
                                            <div class="skeleton-post-text"></div>
                                            <div class="skeleton-post-text"></div>
                                            <div class="skeleton-post-text short"></div>
                                        </div>
                                        <div class="skeleton-post-media"></div>
                                        <div class="d-flex align-items-center justify-content-between px-3 py-2 border-top">
                                            <div class="d-flex align-items-center gap-4">
                                                <div class="skeleton-action"></div>
                                                <div class="skeleton-action"></div>
                                                <div class="skeleton-action"></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="post-card shadow-sm mb-2 bg-white rounded-3 overflow-hidden border-0 skeleton-post">
                                        <div class="d-flex align-items-center p-3 border-bottom">
                                            <div class="skeleton-post-avatar"></div>
                                            <div class="flex-grow-1 ms-3">
                                                <div class="skeleton-post-username"></div>
                                                <div class="skeleton-post-time"></div>
                                            </div>
                                        </div>
                                        <div class="px-3 pb-3">
                                            <div class="skeleton-post-text"></div>
                                            <div class="skeleton-post-text"></div>
                                        </div>
                                        <div class="skeleton-post-media"></div>
                                        <div class="d-flex align-items-center justify-content-between px-3 py-2 border-top">
                                            <div class="d-flex align-items-center gap-4">
                                                <div class="skeleton-action"></div>
                                                <div class="skeleton-action"></div>
                                                <div class="skeleton-action"></div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
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
