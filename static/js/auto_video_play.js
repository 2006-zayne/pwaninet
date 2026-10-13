/**
 * Auto Video Play (Deprecated)
 * 
 * Video playback and IntersectionObserver management have been centralized into
 * static/js/video-manager.js (vastoVideoManager) to eliminate memory leaks,
 * duplicate observers, and conflicting playback policies.
 */
(function() {
    'use strict';
    // No-op stub preserving compatibility if referenced by legacy caches
    if (window.AutoVideoPlayer) return;
    window.AutoVideoPlayer = class DeprecatedAutoVideoPlayer {
        constructor() {
            console.log('[AutoVideoPlayer] Deprecated: Superceded by vastoVideoManager');
        }
        init() {}
        setup() {}
    };
})();
