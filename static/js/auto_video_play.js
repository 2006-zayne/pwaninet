/**
 * Auto Video Play functionality for PwaniNet
 * Automatically plays videos when they come into view and pauses when not visible
 * Works across all pages: posts, profiles, group details, etc.
 */

class AutoVideoPlayer {
    constructor() {
        this.videos = new Map();
        this.intersectionObserver = null;
        this.isInitialized = false;
        this.init();
    }

    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    setup() {
        if (this.isInitialized) return;
        
        // Find all video elements
        this.findVideos();
        
        // Setup intersection observer for autoplay
        this.setupIntersectionObserver();
        
        // Setup video event listeners
        this.setupVideoListeners();
        
        // Observe all videos
        this.observeAllVideos();
        
        // Setup mutation observer for dynamic content
        this.setupMutationObserver();
        
        this.isInitialized = true;
        console.log('Auto Video Player initialized');
    }

    findVideos() {
        const videoElements = document.querySelectorAll('video[data-media-type="video"], video[id^="video-"], video');
        
        videoElements.forEach(video => {
            if (!this.videos.has(video)) {
                this.videos.set(video, {
                    element: video,
                    isVisible: false,
                    isPlaying: false,
                    hasStarted: false,
                    postId: this.extractPostId(video)
                });
            }
        });
    }

    extractPostId(video) {
        // Try to extract post ID from video ID or parent elements
        if (video.id && video.id.startsWith('video-')) {
            return video.id.replace('video-', '');
        }
        
        const parent = video.closest('[data-post-id]');
        if (parent) {
            return parent.dataset.postId;
        }
        
        return null;
    }

    setupIntersectionObserver() {
        const options = {
            root: null,
            rootMargin: '0px',
            threshold: [0.3, 0.7] // Start playing at 30% visible, stop at 70% visible
        };

        this.intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target;
                const videoData = this.videos.get(video);
                
                if (!videoData) return;

                if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
                    // Video is sufficiently visible
                    if (!videoData.isVisible) {
                        this.startVideo(video, videoData);
                    }
                } else if (!entry.isIntersecting || entry.intersectionRatio < 0.7) {
                    // Video is not sufficiently visible
                    if (videoData.isVisible) {
                        this.pauseVideo(video, videoData);
                    }
                }
            });
        }, options);
    }

    setupVideoListeners() {
        this.videos.forEach((videoData, video) => {
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
                // Loop the video if it has loop attribute
                if (video.loop) {
                    setTimeout(() => {
                        if (videoData.isVisible) {
                            video.play().catch(e => console.log('Auto-play prevented:', e));
                        }
                    }, 1000);
                }
            });

            // Error handling
            video.addEventListener('error', (e) => {
                console.error('Video error:', e);
                this.videos.delete(video);
            });

            // Muted state change (for user interaction)
            video.addEventListener('volumechange', () => {
                if (!video.muted && videoData.isPlaying) {
                    // User unmuted, keep playing
                    console.log('User unmuted video');
                }
            });
        });
    }

    observeAllVideos() {
        this.videos.forEach((videoData, video) => {
            if (this.intersectionObserver) {
                this.intersectionObserver.observe(video);
            }
        });
    }

    startVideo(video, videoData) {
        videoData.isVisible = true;
        
        // Check global audio preference (user-specific)
        const username = window.PwaniNetUsername || '';
        const storageKey = username ? `pwaninet_audio_preference_${username}` : 'pwaninet_audio_preference';
        const globalAudioPref = localStorage.getItem(storageKey) || window.PwaniNetUserAudioPreference || 'muted';
        video.muted = globalAudioPref === 'muted';
        
        // Only play if video hasn't been manually paused by user
        if (!videoData.hasStarted || videoData.isPlaying) {
            const playPromise = video.play();
            
            if (playPromise !== undefined) {
                playPromise.catch(error => {
                    // Auto-play was prevented, try muted autoplay
                    if (!video.muted) {
                        video.muted = true;
                        video.play().catch(e => console.log('Muted auto-play also prevented:', e));
                    } else {
                        console.log('Video auto-play prevented:', error);
                    }
                });
            }
        }
    }

    pauseVideo(video, videoData) {
        videoData.isVisible = false;
        
        if (videoData.isPlaying && !video.paused) {
            video.pause();
        }
    }

    setupMutationObserver() {
        // Watch for new videos being added to the page (infinite scroll, dynamic content)
        const observer = new MutationObserver((mutations) => {
            let hasNewVideos = false;
            
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check if the added node or its children contain videos
                        if (node.tagName === 'VIDEO' || node.querySelector('video')) {
                            hasNewVideos = true;
                        }
                    }
                });
            });
            
            if (hasNewVideos) {
                // Re-scan for videos after a short delay
                setTimeout(() => {
                    this.findVideos();
                    this.setupVideoListeners();
                    this.observeAllVideos();
                }, 100);
            }
        });

        // Start observing the document body
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Public methods for manual control
    playAll() {
        this.videos.forEach((videoData, video) => {
            if (!videoData.isPlaying) {
                video.play().catch(e => console.log('Play failed:', e));
            }
        });
    }

    pauseAll() {
        this.videos.forEach((videoData, video) => {
            if (videoData.isPlaying) {
                video.pause();
            }
        });
    }

    // Destroy method for cleanup
    destroy() {
        if (this.intersectionObserver) {
            this.intersectionObserver.disconnect();
        }
        this.videos.clear();
        this.isInitialized = false;
    }
}

// Initialize the auto video player
const autoVideoPlayer = new AutoVideoPlayer();

// Make it globally accessible for debugging
window.autoVideoPlayer = autoVideoPlayer;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AutoVideoPlayer;
}
