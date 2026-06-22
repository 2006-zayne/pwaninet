/**
 * PwaniNet Video Manager
 * Handles feed video autoplay behavior:
 * - Only one video plays at a time
 * - Videos remain muted
 * - Videos stop when leaving viewport
 * - Uses preview clips in feed, original videos in post detail
 */

(function() {
    'use strict';

    let currentPlayingVideo = null;
    let observer = null;

    // ============================================================================
    // VIDEO AUTOPLAY CONTROLLER
    // ============================================================================

    function initVideoAutoplay() {
        const feedVideos = document.querySelectorAll('.feed-video[data-autoplay="true"]');
        
        if (feedVideos.length === 0) return;

        console.log('[VideoManager] Initializing video autoplay for', feedVideos.length, 'videos');

        // Set up Intersection Observer to detect when videos enter/leave viewport
        observer = new IntersectionObserver(handleIntersection, {
            root: null,
            rootMargin: '0px',
            threshold: 0.5 // Video must be 50% visible to play
        });

        // Observe all feed videos
        feedVideos.forEach(video => {
            observer.observe(video);
            
            // Add click handler to toggle play/pause
            video.addEventListener('click', function(e) {
                e.preventDefault();
                toggleVideoPlay(this);
            });
        });

        // Handle visibility change (tab switch)
        document.addEventListener('visibilitychange', handleVisibilityChange);
    }

    function handleIntersection(entries) {
        entries.forEach(entry => {
            const video = entry.target;
            
            if (entry.isIntersecting) {
                // Video entered viewport - play it
                playVideo(video);
            } else {
                // Video left viewport - pause it
                pauseVideo(video);
            }
        });
    }

    function handleVisibilityChange() {
        if (document.hidden) {
            // Page hidden - pause all videos
            pauseAllVideos();
        } else {
            // Page visible - play video in viewport
            const visibleVideo = getVisibleVideo();
            if (visibleVideo) {
                playVideo(visibleVideo);
            }
        }
    }

    // ============================================================================
    // VIDEO PLAYBACK CONTROL
    // ============================================================================

    function playVideo(video) {
        if (!video || currentPlayingVideo === video) return;

        // Pause currently playing video
        if (currentPlayingVideo) {
            pauseVideo(currentPlayingVideo);
        }

        // Play new video
        video.play().then(() => {
            currentPlayingVideo = video;
            console.log('[VideoManager] Playing video:', video.id);
        }).catch(err => {
            console.warn('[VideoManager] Failed to play video:', err);
        });
    }

    function pauseVideo(video) {
        if (!video) return;

        video.pause();
        video.currentTime = 0; // Reset to beginning for loop
        
        if (currentPlayingVideo === video) {
            currentPlayingVideo = null;
            console.log('[VideoManager] Paused video:', video.id);
        }
    }

    function pauseAllVideos() {
        const feedVideos = document.querySelectorAll('.feed-video');
        feedVideos.forEach(video => {
            pauseVideo(video);
        });
    }

    function toggleVideoPlay(video) {
        if (video.paused) {
            playVideo(video);
        } else {
            pauseVideo(video);
        }
    }

    function getVisibleVideo() {
        const feedVideos = document.querySelectorAll('.feed-video');
        
        for (let video of feedVideos) {
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
    // MUTE TOGGLE
    // ============================================================================

    function initMuteToggles() {
        const muteButtons = document.querySelectorAll('.mute-toggle');
        
        muteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const postId = this.dataset.postId;
                const video = document.getElementById(`video-${postId}`);
                
                if (video) {
                    video.muted = !video.muted;
                    
                    // Update icon
                    const icon = this.querySelector('i');
                    if (video.muted) {
                        icon.className = 'bi bi-volume-mute-fill';
                        this.title = 'Unmute';
                    } else {
                        icon.className = 'bi bi-volume-up-fill';
                        this.title = 'Mute';
                    }
                }
            });
        });
    }

    // ============================================================================
    // POST DETAIL VIDEO HANDLING
    // ============================================================================

    function initPostDetailVideos() {
        // Post detail videos should not autoplay
        // They should only load when user interacts
        const postDetailVideos = document.querySelectorAll('.post-detail-video');
        
        postDetailVideos.forEach(video => {
            video.preload = 'none';
            video.autoplay = false;
            
            // Load video on first interaction
            video.addEventListener('click', function() {
                if (video.readyState === 0) { // HAVE_NOTHING
                    video.load();
                }
                if (video.paused) {
                    video.play();
                } else {
                    video.pause();
                }
            });
        });
    }

    // ============================================================================
    // HTMX INTEGRATION
    // ============================================================================

    function initHTMXIntegration() {
        // Re-initialize video manager after HTMX content swap
        document.addEventListener('htmx:afterSwap', function(event) {
            // Small delay to ensure DOM is ready
            setTimeout(() => {
                initVideoAutoplay();
                initMuteToggles();
                initPostDetailVideos();
            }, 100);
        });
    }

    // ============================================================================
    // INITIALIZATION
    // ============================================================================

    function init() {
        console.log('[VideoManager] Initializing video management system');
        
        // Initialize on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                initVideoAutoplay();
                initMuteToggles();
                initPostDetailVideos();
            });
        } else {
            initVideoAutoplay();
            initMuteToggles();
            initPostDetailVideos();
        }
        
        // Initialize HTMX integration
        initHTMXIntegration();
    }

    // ============================================================================
    // PUBLIC API
    // ============================================================================

    window.PwaniNetVideoManager = {
        playVideo,
        pauseVideo,
        pauseAllVideos,
        getVisibleVideo,
        init
    };

    // Initialize
    init();

})();
