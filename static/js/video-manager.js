/**
 * PwaniNet Unified Video Manager
 * Modern video experience with:
 * - Single observer with proper lifecycle
 * - HTMX-safe initialization
 * - No duplicate listeners
 * - No memory leaks
 * - Modern social-media-style controls
 * - Accessibility support
 * - Mobile-first design
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
            listeners: new Set(),
            controlsVisible: false,
            controlsTimeout: null,
            controls: {
                playButton: null,
                muteButton: null,
                loadingSpinner: null,
                controlBar: null
            }
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
                setupVideoControls(video, videoData);
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

    function setupVideoControls(video, videoData) {
        const container = video.closest('[data-media-type="video"]');
        if (!container) return;

        // Create play button
        const playButton = createPlayButton(video, videoData);
        container.appendChild(playButton);
        videoData.controls.playButton = playButton;

        // Create duration badge
        /*const durationBadge = createDurationBadge(video, videoData);
        container.appendChild(durationBadge);
        videoData.controls.durationBadge = durationBadge;*/

        // Create loading spinner
        const loadingSpinner = createLoadingSpinner(video, videoData);
        container.appendChild(loadingSpinner);
        videoData.controls.loadingSpinner = loadingSpinner;

        // Setup mute button if exists
        const existingMuteButton = container.querySelector('.mute-toggle');
        if (existingMuteButton) {
            const muteButton = setupMuteButton(existingMuteButton, video, videoData);
            videoData.controls.muteButton = muteButton;
            // Update initial state
            updateMuteButton(video, videoData);
        }

        // Create control bar for both feed and detail videos
        const controlBar = createControlBar(video, videoData);
        container.appendChild(controlBar);
        videoData.controls.controlBar = controlBar;
    }

    function createPlayButton(video, videoData) {
        const button = document.createElement('button');
        button.className = 'btn btn-light rounded-circle position-absolute video-play-toggle';
        button.setAttribute('aria-label', 'Play video');
        button.style.cssText = `
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 5;
            width: 48px;
            height: 48px;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: var(--card-bg);
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.2s ease-in-out;
            opacity: 1;
            pointer-events: auto;
        `;
        
        const icon = document.createElement('i');
        icon.className = 'bi bi-play-fill';
        icon.style.cssText = 'font-size: 20px; color: var(--text-dark);';
        button.appendChild(icon);

        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleVideoPlay(video, videoData);
        });
        button.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleVideoPlay(video, videoData);
        });

        return button;
    }
/*
    function createDurationBadge(video, videoData) {
        const badge = document.createElement('span');
        badge.className = 'video-duration position-absolute rounded-pill px-2 py-1';
        badge.style.cssText = `
            bottom: 10px;
            right: 10px;
            z-index: 5;
            background: rgba(0, 0, 0, 0.7);
            color: white;
            font-size: 12px;
            font-weight: 600;
            backdrop-filter: blur(4px);
            pointer-events: none;
        `;
        badge.textContent = '0:00';

        video.addEventListener('loadedmetadata', () => {
            badge.textContent = formatDuration(video.duration);
        });

        return badge;
    }*/

    function createLoadingSpinner(video, videoData) {
        const spinner = document.createElement('div');
        spinner.className = 'video-loading position-absolute';
        spinner.style.cssText = `
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 5;
            display: none;
            pointer-events: none;
        `;
        
        const innerSpinner = document.createElement('div');
        innerSpinner.className = 'spinner-border text-primary';
        innerSpinner.setAttribute('role', 'status');
        innerSpinner.style.cssText = 'width: 40px; height: 40px;';
        spinner.appendChild(innerSpinner);

        return spinner;
    }

    function createControlBar(video, videoData) {
        const bar = document.createElement('div');
        bar.className = 'video-control-bar';
        bar.style.cssText = `
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 5;
            background: linear-gradient(to top, rgba(0,0,0,0.75), transparent);
            padding: 12px 16px 24px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        `;

        // Progress bar
        const progress = document.createElement('input');
        progress.type = 'range';
        progress.min = 0;
        progress.max = 100;
        progress.value = 0;
        progress.style.cssText = 'flex-grow: 1; accent-color: var(--primary); pointer-events: auto;';
        progress.addEventListener('input', (e) => {
            e.stopPropagation();
            const time = (e.target.value / 100) * video.duration;
            video.currentTime = time;
        });
        progress.addEventListener('touchend', (e) => {
            e.stopPropagation();
        });
        video.addEventListener('timeupdate', () => {
            progress.value = (video.currentTime / video.duration) * 100;
        });
        bar.appendChild(progress);

        // Duration
        const duration = document.createElement('span');
        duration.style.cssText = 'color: white; font-size: 12px; min-width: 40px; pointer-events: none;';
        duration.textContent = '0:00';
        video.addEventListener('loadedmetadata', () => {
            duration.textContent = formatDuration(video.duration);
        });
        video.addEventListener('timeupdate', () => {
            duration.textContent = formatDuration(video.currentTime);
        });
        bar.appendChild(duration);

        // Fullscreen button
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.className = 'btn btn-link p-0';
        fullscreenBtn.style.cssText = 'color: white; width: 32px; height: 32px; pointer-events: auto;';
        fullscreenBtn.innerHTML = '<i class="bi bi-arrows-fullscreen" style="font-size: 18px;"></i>';
        fullscreenBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFullscreen(video);
        });
        fullscreenBtn.addEventListener('touchend', (e) => {
            e.stopPropagation();
            toggleFullscreen(video);
        });
        bar.appendChild(fullscreenBtn);

        return bar;
    }

    function setupMuteButton(button, video, videoData) {
        // Remove existing listener if any
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        newButton.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleMute(video, videoData);
        });
        newButton.addEventListener('touchend', (e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleMute(video, videoData);
        });
        
        return newButton;
    }

    // ============================================================================
    // VIDEO LISTENERS
    // ============================================================================

    function setupVideoListeners(video, videoData) {
        let touchHandled = false;

        // Video click - toggle controls visibility only
        video.addEventListener('click', (e) => {
            e.preventDefault();
            // Skip if this was triggered by touch
            if (touchHandled) {
                touchHandled = false;
                return;
            }
            if (videoData.controlsVisible) {
                hideControls(videoData);
            } else {
                showControls(videoData);
                if (!video.paused) {
                    scheduleHide(videoData);
                }
            }
        });

        // Touch support for mobile - same behavior as click
        video.addEventListener('touchend', (e) => {
            e.preventDefault();
            touchHandled = true;
            if (videoData.controlsVisible) {
                hideControls(videoData);
            } else {
                showControls(videoData);
                if (!video.paused) {
                    scheduleHide(videoData);
                }
            }
        });

        // Play event
        video.addEventListener('play', () => {
            videoData.isPlaying = true;
            videoData.hasStarted = true;
            updatePlayButton(video, videoData, true);
            hideLoadingSpinner(videoData);
            // Show controls briefly then auto-hide
            showControls(videoData);
            scheduleHide(videoData);
        });

        // Pause event
        video.addEventListener('pause', () => {
            videoData.isPlaying = false;
            updatePlayButton(video, videoData, false);
            // Show controls permanently when paused
            if (videoData.controlsTimeout) {
                clearTimeout(videoData.controlsTimeout);
                videoData.controlsTimeout = null;
            }
            showControls(videoData);
        });

        // Ended event
        video.addEventListener('ended', () => {
            videoData.isPlaying = false;
            videoData.hasStarted = false;
            updatePlayButton(video, videoData, false);
            if (video.loop) {
                // Loop the video
                setTimeout(() => {
                    if (videoData.isVisible) {
                        video.play().catch(e => console.log('Auto-play prevented:', e));
                    }
                }, 1000);
            }
        });

        // Waiting event (buffering)
        video.addEventListener('waiting', () => {
            showLoadingSpinner(videoData);
        });

        // Canplay event
        video.addEventListener('canplay', () => {
            hideLoadingSpinner(videoData);
        });

        // Error event
        video.addEventListener('error', (e) => {
            console.error('[VideoManager] Video error:', e);
            showErrorMessage(videoData);
        });

        // Volume change
        video.addEventListener('volumechange', () => {
            updateMuteButton(video, videoData);
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

        // Play new video
        video.play().then(() => {
            state.currentPlayingVideo = video;
            videoData.isPlaying = true;
            console.log('[VideoManager] Playing video:', video.id);
        }).catch(err => {
            console.warn('[VideoManager] Failed to play video:', err);
            // Try muted autoplay
            if (!video.muted) {
                video.muted = true;
                video.play().catch(e => console.log('Muted auto-play also prevented:', e));
                updateMuteButton(video, videoData);
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

    function toggleVideoPlay(video, videoData) {
        if (video.paused) {
            playVideo(video, videoData);
        } else {
            pauseVideo(video, videoData);
        }
    }

    function toggleMute(video, videoData) {
        video.muted = !video.muted;
        updateMuteButton(video, videoData);
    }

    function toggleFullscreen(video) {
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            video.requestFullscreen().catch(err => {
                console.error('[VideoManager] Fullscreen error:', err);
            });
        }
    }

    // ============================================================================
    // UI UPDATES
    // ============================================================================

    function updatePlayButton(video, videoData, isPlaying) {
        const button = videoData.controls.playButton;
        if (!button) return;

        const icon = button.querySelector('i');
        if (isPlaying) {
            icon.className = 'bi bi-pause-fill';
            button.setAttribute('aria-label', 'Pause video');
        } else {
            icon.className = 'bi bi-play-fill';
            button.setAttribute('aria-label', 'Play video');
        }
        
        // Only show when controls are visible
        if (videoData.controlsVisible) {
            button.style.opacity = '1';
        } else {
            button.style.opacity = '0';
        }
    }

    function updateMuteButton(video, videoData) {
        const button = videoData.controls.muteButton;
        if (!button) return;

        const icon = button.querySelector('i');
        if (video.muted) {
            icon.className = 'bi bi-volume-mute-fill';
            button.title = 'Unmute';
            button.setAttribute('aria-label', 'Unmute video');
        } else {
            icon.className = 'bi bi-volume-up-fill';
            button.title = 'Mute';
            button.setAttribute('aria-label', 'Mute video');
        }
    }

    function showLoadingSpinner(videoData) {
        if (videoData.controls.loadingSpinner) {
            videoData.controls.loadingSpinner.style.display = 'flex';
        }
    }

    function hideLoadingSpinner(videoData) {
        if (videoData.controls.loadingSpinner) {
            videoData.controls.loadingSpinner.style.display = 'none';
        }
    }

    function showErrorMessage(videoData) {
        const container = videoData.element.closest('[data-media-type="video"]');
        if (!container) return;

        const errorDiv = document.createElement('div');
        errorDiv.className = 'position-absolute text-center';
        errorDiv.style.cssText = `
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 10;
            color: var(--text-secondary);
        `;
        errorDiv.innerHTML = '<i class="bi bi-exclamation-circle" style="font-size: 32px;"></i><p class="mt-2 small">Video unavailable</p>';
        container.appendChild(errorDiv);
    }

    function showControls(videoData) {
        if (!videoData.controls.controlBar) return;
        videoData.controlsVisible = true;
        videoData.controls.controlBar.style.opacity = '1';
    }

    function hideControls(videoData) {
        if (!videoData.controls.controlBar) return;
        videoData.controlsVisible = false;
        videoData.controls.controlBar.style.opacity = '0';
    }

    function scheduleHide(videoData) {
        if (videoData.controlsTimeout) {
            clearTimeout(videoData.controlsTimeout);
        }
        videoData.controlsTimeout = setTimeout(() => {
            hideControls(videoData);
        }, 3000);
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

        // Remove controls
        Object.values(videoData.controls).forEach(control => {
            if (control && control.parentNode) {
                control.parentNode.removeChild(control);
            }
        });

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
    // UTILITY FUNCTIONS
    // ============================================================================

    function formatDuration(seconds) {
        if (isNaN(seconds)) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }
        return `${minutes}:${String(secs).padStart(2, '0')}`;
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
