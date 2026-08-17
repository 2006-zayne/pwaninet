/**
 * PwaniNet Unified Video Manager
 * Modern video experience with:
 * - Single observer with proper lifecycle
 * - HTMX-safe initialization
 * - No duplicate listeners
 * - No memory leaks
 * - Native HTML5 video controls
 * - IntersectionObserver autoplay
 * - Auto pause when videos leave viewport
 */

(function() {
    'use strict';

    // ============================================================================
    // STATE MANAGEMENT
    // ============================================================================

    const state = {
        videos: new Map(), // video element -> video data
        currentPlayingVideo: null,
        observer: null,
        mutationObserver: null,
        isInitialized: false,
        visibilityChangeHandler: null
    };

    // ============================================================================
    // VIDEO DATA STRUCTURE
    // ============================================================================

    function createVideoData(video) {
        return {
            element: video,
            postId: extractPostId(video),
            type: getVideoType(video),
            isVisible: false,
            isPlaying: false,
            hasStarted: false,
            listeners: new Set()
        };
    }

    function extractPostId(video) {
        if (video.id && video.id.startsWith('video-')) {
            return video.id.replace('video-', '');
        }
        const parent = video.closest('[data-post-id]');
        return parent ? parent.dataset.postId : null;
    }

    function getVideoType(video) {
        if (video.classList.contains('feed-video')) return 'feed';
        if (video.classList.contains('post-detail-video')) return 'detail';
        return 'unknown';
    }

    // ============================================================================
    // OBSERVER LIFECYCLE
    // ============================================================================

    function destroyObserver() {
        if (state.observer) {
            state.observer.disconnect();
            state.observer = null;
            console.log('[VideoManager] Observer destroyed');
        }
    }

    function createObserver() {
        destroyObserver(); // Ensure no duplicate observers

        state.observer = new IntersectionObserver(handleIntersection, {
            root: null,
            rootMargin: '0px',
            threshold: 0.5 // Video must be 50% visible to play
        });

        console.log('[VideoManager] Observer created');
    }

    function observeVideo(video) {
        if (state.observer && video) {
            state.observer.observe(video);
        }
    }

    function unobserveVideo(video) {
        if (state.observer && video) {
            state.observer.unobserve(video);
        }
    }

    // ============================================================================
    // MUTATION OBSERVER FOR DYNAMIC CONTENT
    // ============================================================================

    function setupMutationObserver() {
        if (state.mutationObserver) {
            state.mutationObserver.disconnect();
        }

        state.mutationObserver = new MutationObserver((mutations) => {
            let hasNewVideos = false;
            let removedVideos = [];

            mutations.forEach((mutation) => {
                // Check for added nodes
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.tagName === 'VIDEO' || node.querySelector('video')) {
                            hasNewVideos = true;
                        }
                    }
                });

                // Check for removed nodes
                mutation.removedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.tagName === 'VIDEO') {
                            removedVideos.push(node);
                        } else {
                            const videos = node.querySelectorAll('video');
                            videos.forEach(v => removedVideos.push(v));
                        }
                    }
                });
            });

            if (hasNewVideos) {
                // Initialize only new videos in the swapped content
                setTimeout(() => {
                    initializeVideos(document.body);
                }, 100);
            }

            // Cleanup removed videos
            removedVideos.forEach(video => {
                cleanupVideo(video);
            });
        });

        state.mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });

        console.log('[VideoManager] Mutation observer setup');
    }

    // ============================================================================
    // VIDEO INITIALIZATION
    // ============================================================================

    function initializeVideos(container = document.body) {
        const videos = container.querySelectorAll('video');
        
        videos.forEach(video => {
            if (!state.videos.has(video)) {
                const videoData = createVideoData(video);
                state.videos.set(video, videoData);
                
                // Enable native controls
                video.controls = true;
                
                setupVideoListeners(video, videoData);
                observeVideo(video);
                
                // Set preload to metadata for performance
                if (videoData.type === 'feed') {
                    video.preload = 'metadata';
                }
            }
        });

        console.log('[VideoManager] Initialized', state.videos.size, 'videos');
    }






    // ============================================================================
    // VIDEO LISTENERS
    // ============================================================================

    function setupVideoListeners(video, videoData) {
        // Play event
        video.addEventListener('play', () => {
            videoData.isPlaying = true;
            videoData.hasStarted = true;
        });

        // Pause event
        video.addEventListener('pause', () => {
            videoData.isPlaying = false;
        });

        // Ended event
        video.addEventListener('ended', () => {
            videoData.isPlaying = false;
            videoData.hasStarted = false;
            if (video.loop) {
                // Loop the video
                setTimeout(() => {
                    if (videoData.isVisible) {
                        video.play().catch(e => console.log('Auto-play prevented:', e));
                    }
                }, 1000);
            }
        });

        // Error event
        video.addEventListener('error', (e) => {
            console.error('[VideoManager] Video error:', e);
        });
    }

    // ============================================================================
    // VIDEO PLAYBACK CONTROL
    // ============================================================================

    function playVideo(video, videoData) {
        if (!video || state.currentPlayingVideo === video) return;

        // Pause currently playing video
        if (state.currentPlayingVideo) {
            const currentData = state.videos.get(state.currentPlayingVideo);
            if (currentData) {
                pauseVideo(state.currentPlayingVideo, currentData);
            }
        }

        // Check global audio preference (user-specific)
        const username = window.PwaniNetUsername || '';
        const storageKey = username ? `pwaninet_audio_preference_${username}` : 'pwaninet_audio_preference';
        const globalAudioPref = localStorage.getItem(storageKey) || window.PwaniNetUserAudioPreference || 'muted';
        video.muted = globalAudioPref === 'muted';

        // Play new video
        video.play().then(() => {
            state.currentPlayingVideo = video;
            videoData.isPlaying = true;
            console.log('[VideoManager] Playing video:', video.id, 'muted:', video.muted);
        }).catch(err => {
            console.warn('[VideoManager] Failed to play video:', err);
            // Try muted autoplay if not already muted
            if (!video.muted) {
                video.muted = true;
                video.play().catch(e => console.log('Muted auto-play also prevented:', e));
            }
        });
    }

    function pauseVideo(video, videoData) {
        if (!video) return;

        video.pause();
        videoData.isPlaying = false;
        
        if (state.currentPlayingVideo === video) {
            state.currentPlayingVideo = null;
            console.log('[VideoManager] Paused video:', video.id);
        }
    }





    // ============================================================================
    // INTERSECTION OBSERVER HANDLER
    // ============================================================================

    function handleIntersection(entries) {
        entries.forEach(entry => {
            const video = entry.target;
            const videoData = state.videos.get(video);
            
            if (!videoData) return;

            if (entry.isIntersecting) {
                // Video entered viewport - play it
                videoData.isVisible = true;
                if (videoData.type === 'feed' && !videoData.hasStarted) {
                    playVideo(video, videoData);
                }
            } else {
                // Video left viewport - pause it
                videoData.isVisible = false;
                if (videoData.type === 'feed') {
                    pauseVideo(video, videoData);
                }
            }
        });
    }

    // ============================================================================
    // VISIBILITY CHANGE HANDLER
    // ============================================================================

    function handleVisibilityChange() {
        if (document.hidden) {
            // Page hidden - pause all videos
            state.videos.forEach((videoData, video) => {
                if (videoData.isPlaying) {
                    pauseVideo(video, videoData);
                }
            });
        } else {
            // Page visible - play video in viewport
            const visibleVideo = getVisibleVideo();
            if (visibleVideo) {
                const videoData = state.videos.get(visibleVideo);
                if (videoData && !videoData.isPlaying) {
                    playVideo(visibleVideo, videoData);
                }
            }
        }
    }

    function getVisibleVideo() {
        for (let [video, videoData] of state.videos) {
            if (videoData.type !== 'feed') continue;
            
            const rect = video.getBoundingClientRect();
            const isVisible = (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
            
            if (isVisible) {
                return video;
            }
        }
        
        return null;
    }

    // ============================================================================
    // CLEANUP
    // ============================================================================

    function cleanupVideo(video) {
        const videoData = state.videos.get(video);
        if (!videoData) return;

        // Unobserve
        unobserveVideo(video);

        // Remove from state
        state.videos.delete(video);

        console.log('[VideoManager] Cleaned up video:', video.id);
    }

    function destroy() {
        // Disconnect observers
        destroyObserver();
        
        if (state.mutationObserver) {
            state.mutationObserver.disconnect();
            state.mutationObserver = null;
        }

        // Remove visibility change handler
        if (state.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', state.visibilityChangeHandler);
        }

        // Cleanup all videos
        state.videos.forEach((videoData, video) => {
            cleanupVideo(video);
        });

        state.videos.clear();
        state.currentPlayingVideo = null;
        state.isInitialized = false;

        console.log('[VideoManager] Destroyed');
    }

    // ============================================================================
    // HTMX INTEGRATION
    // ============================================================================

    function initHTMXIntegration() {
        // Only initialize videos in swapped content
        document.addEventListener('htmx:afterSwap', function(event) {
            const target = event.detail.target;
            
            // Check if swap contains videos
            if (target.querySelector('video')) {
                setTimeout(() => {
                    initializeVideos(target);
                }, 100);
            }
        });
    }


    // ============================================================================
    // INITIALIZATION
    // ============================================================================

    function init() {
        if (state.isInitialized) {
            console.log('[VideoManager] Already initialized');
            return;
        }

        console.log('[VideoManager] Initializing video management system');

        // Create observer
        createObserver();

        // Setup mutation observer
        setupMutationObserver();

        // Initialize videos
        initializeVideos();

        // Setup visibility change handler
        state.visibilityChangeHandler = handleVisibilityChange;
        document.addEventListener('visibilitychange', state.visibilityChangeHandler);

        // Initialize HTMX integration
        initHTMXIntegration();

        state.isInitialized = true;
    }

    // ============================================================================
    // PUBLIC API
    // ============================================================================

    window.PwaniNetVideoManager = {
        init,
        destroy,
        playVideo,
        pauseVideo,
        getVisibleVideo,
        get state() { return state; }
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
