/**
 * PwaniNet Unified Video Manager (Phase 4)
 * 
 * Features:
 * - Single feed IntersectionObserver (threshold: 0.65)
 * - Strict playback policy:
 *     * Autoplays portrait reels (>=65% visible), exactly one playing at any time
 *     * Landscape videos require manual play tap and pause active reels
 * - Global mute state synchronized across all feed & fullscreen videos
 * - Delegated single tap (play/pause + transient HUD) vs. double tap (heart burst + like)
 * - Progressive vertical video promotion (legacy backfill fallback)
 * - Dedicated Full-Screen Reels Overlay Mode with vertical 100dvh snap-scrolling
 * - Full HTMX lifecycle integration with memory leak prevention
 */

(function() {
    'use strict';

    // ============================================================================
    // STATE & CONFIGURATION
    // ============================================================================

    const username = window.PwaniNetUsername || '';
    const storageKey = username ? `pwaninet_audio_preference_${username}` : 'pwaninet_audio_preference';
    let isGlobalMuted = (localStorage.getItem(storageKey) || window.PwaniNetUserAudioPreference || 'muted') === 'muted';

    const state = {
        videos: new Map(), // video element -> video metadata
        feedObserver: null,
        fullscreenObserver: null,
        mutationObserver: null,
        currentPlayingVideo: null,
        isFullScreenActive: false,
        previousScrollY: 0,
        tapTimers: new Map(), // element -> timer id
        isInitialized: false
    };

    // ============================================================================
    // UTILITY HELPERS
    // ============================================================================

    function extractPostId(element) {
        if (!element) return null;
        if (element.dataset && element.dataset.postId) return element.dataset.postId;
        if (element.id && element.id.startsWith('video-')) return element.id.replace('video-', '');
        if (element.id && element.id.startsWith('fs-video-')) return element.id.replace('fs-video-', '');
        const parent = element.closest('[data-post-id]');
        return parent ? parent.dataset.postId : null;
    }

    function isReelElement(video) {
        if (!video) return false;
        if (video.classList.contains('reel-video-element') || video.classList.contains('fullscreen-reel-video')) return true;
        if (video.closest('.reel-card-container') || video.closest('.reels-snap-item')) return true;
        if (video.dataset && video.dataset.reel === 'true') return true;
        return false;
    }

    function isLandscapeVideo(video) {
        if (!video) return false;
        if (video.closest('.landscape-video-container')) return true;
        return !isReelElement(video);
    }

    // ============================================================================
    // GLOBAL MUTE SYNCHRONIZATION
    // ============================================================================

    function syncMuteButtons() {
        const muteButtons = document.querySelectorAll('.reel-mute-btn, .video-mute-toggle, [data-action="mute-toggle"]');
        muteButtons.forEach(btn => {
            const icon = btn.querySelector('i');
            if (icon) {
                if (isGlobalMuted) {
                    icon.className = 'bi bi-volume-mute-fill';
                } else {
                    icon.className = 'bi bi-volume-up-fill';
                }
            }
            const label = btn.parentElement?.querySelector('.reel-mute-label');
            if (label) {
                label.textContent = isGlobalMuted ? 'Mute' : 'Sound';
            }
        });
    }

    function setGlobalMute(muted) {
        isGlobalMuted = !!muted;
        try {
            localStorage.setItem(storageKey, isGlobalMuted ? 'muted' : 'unmuted');
        } catch (e) {
            console.warn('[VideoManager] LocalStorage unavailable for audio preference', e);
        }

        // Sync all video elements across feed and overlays
        document.querySelectorAll('video').forEach(vid => {
            vid.muted = isGlobalMuted;
        });

        syncMuteButtons();
        console.log('[VideoManager] Global mute toggled to:', isGlobalMuted);
    }

    function toggleGlobalMute() {
        setGlobalMute(!isGlobalMuted);
    }

    // ============================================================================
    // PLAYBACK CONTROLLER
    // ============================================================================

    function playVideo(video, isAutoplay = false) {
        if (!video) return;

        // Enforce single active video playback
        if (state.currentPlayingVideo && state.currentPlayingVideo !== video) {
            pauseVideo(state.currentPlayingVideo);
        }

        // Apply global mute
        video.muted = isGlobalMuted;

        // Resume HLS buffer loading if active
        if (video._hlsInstance && typeof video._hlsInstance.startLoad === 'function') {
            video._hlsInstance.startLoad();
        }

        const playPromise = video.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                state.currentPlayingVideo = video;
            }).catch(err => {
                console.warn('[VideoManager] Play rejected:', err);
                if (isAutoplay && !video.muted) {
                    // Browser prevented unmuted autoplay: force muted and retry silently
                    video.muted = true;
                    video.play().then(() => {
                        state.currentPlayingVideo = video;
                    }).catch(silentErr => {
                        console.log('[VideoManager] Muted retry also rejected:', silentErr);
                    });
                }
            });
        }
    }

    function pauseVideo(video) {
        if (!video) return;

        if (video._hlsInstance && typeof video._hlsInstance.stopLoad === 'function') {
            video._hlsInstance.stopLoad();
        }

        try {
            video.pause();
        } catch (e) {
            // Ignore pause errors
        }

        if (state.currentPlayingVideo === video) {
            state.currentPlayingVideo = null;
        }
    }

    function pauseAllVideos() {
        document.querySelectorAll('video').forEach(vid => {
            pauseVideo(vid);
        });
    }

    function cleanupVideo(video) {
        if (!video) return;

        try {
            video.pause();
        } catch (e) {}

        if (state.feedObserver) {
            try {
                state.feedObserver.unobserve(video);
            } catch (e) {}
        }
        if (state.fullscreenObserver) {
            try {
                state.fullscreenObserver.unobserve(video);
            } catch (e) {}
        }

        if (video._hlsInstance && typeof video._hlsInstance.destroy === 'function') {
            try {
                video._hlsInstance.destroy();
            } catch (e) {}
            video._hlsInstance = null;
        }

        if (state.currentPlayingVideo === video) {
            state.currentPlayingVideo = null;
        }

        state.videos.delete(video);

        // Free decoder memory on unmount/teardown
        try {
            video.removeAttribute('src');
            while (video.firstChild) {
                video.removeChild(video.firstChild);
            }
            video.load();
        } catch (e) {}
    }

    // ============================================================================
    // INTERSECTION OBSERVERS (FEED & FULLSCREEN)
    // ============================================================================

    function handleFeedIntersection(entries) {
        if (state.isFullScreenActive) return; // Fullscreen overlay has priority

        entries.forEach(entry => {
            const video = entry.target;
            const isReel = isReelElement(video);

            if (entry.isIntersecting && entry.intersectionRatio >= 0.65) {
                // Autoplay reels when >= 65% visible
                if (isReel && video.dataset.autoplay !== 'false') {
                    playVideo(video, true);
                }
            } else if (!entry.isIntersecting || entry.intersectionRatio < 0.65) {
                // Pause when visibility drops below 65%
                if (video === state.currentPlayingVideo) {
                    pauseVideo(video);
                }
            }
        });
    }

    function handleFullscreenIntersection(entries) {
        if (!state.isFullScreenActive) return;

        entries.forEach(entry => {
            const snapItem = entry.target;
            const video = snapItem.querySelector('video');
            if (!video) return;

            if (entry.isIntersecting && entry.intersectionRatio >= 0.65) {
                playVideo(video, true);
            } else if (!entry.isIntersecting || entry.intersectionRatio < 0.65) {
                if (video === state.currentPlayingVideo) {
                    pauseVideo(video);
                }
            }
        });
    }

    function createFeedObserver() {
        if (state.feedObserver) {
            state.feedObserver.disconnect();
        }
        state.feedObserver = new IntersectionObserver(handleFeedIntersection, {
            root: null,
            rootMargin: '0px',
            threshold: 0.65
        });
    }

    function createFullscreenObserver() {
        if (state.fullscreenObserver) {
            state.fullscreenObserver.disconnect();
        }
        state.fullscreenObserver = new IntersectionObserver(handleFullscreenIntersection, {
            root: document.getElementById('reelsSnapViewport') || null,
            rootMargin: '0px',
            threshold: 0.65
        });
    }

    // ============================================================================
    // HITBOX INTERACTIONS (SINGLE TAP HUD VS. DOUBLE TAP HEART BURST)
    // ============================================================================

    function triggerHeartBurst(container, clientX, clientY) {
        if (!container) return;
        const heart = container.querySelector('.reel-heart-burst');
        if (!heart) return;

        heart.classList.remove('animate');
        // Force reflow
        void heart.offsetWidth;
        heart.classList.add('animate');

        setTimeout(() => {
            heart.classList.remove('animate');
        }, 650);
    }

    function triggerPlayHud(container, isPlaying) {
        if (!container) return;
        const hud = container.querySelector('.reel-play-hud');
        if (!hud) return;

        const icon = hud.querySelector('i');
        if (icon) {
            icon.className = isPlaying ? 'bi bi-play-fill' : 'bi bi-pause-fill';
        }

        hud.classList.remove('show');
        void hud.offsetWidth;
        hud.classList.add('show');

        setTimeout(() => {
            hud.classList.remove('show');
        }, 550);
    }

    function handleHitboxTap(hitbox, event) {
        const isInlineReel = hitbox.closest('.reel-card-container') && !hitbox.closest('.reel-fullscreen-content') && !hitbox.closest('.reels-snap-item');
        if (isInlineReel) {
            // Clicking an inline feed ReelCard opens the Fullscreen Reels Player
            const container = hitbox.closest('.reel-card-container');
            const postId = extractPostId(container);
            if (postId) {
                openFullscreenReels(postId);
            }
            return;
        }

        const container = hitbox.closest('.reel-fullscreen-content') || hitbox.closest('.reels-snap-item');
        if (!container) return;

        const video = container.querySelector('video');
        if (!video) return;

        const postId = extractPostId(container);

        // Check if pending single tap timer exists -> this is a double tap
        if (state.tapTimers.has(hitbox)) {
            clearTimeout(state.tapTimers.get(hitbox));
            state.tapTimers.delete(hitbox);

            // Double tap: heart burst animation
            triggerHeartBurst(container, event.clientX, event.clientY);

            // Trigger like button inside this card or sync with inline card
            const likeBtn = container.querySelector('.like-button') ||
                           (postId ? document.querySelector(`#reel-like-wrap-${postId} .like-button`) : null);
            if (likeBtn) {
                likeBtn.click();
            }
            return;
        }

        // Single tap: start 220ms delay before toggling play/pause
        const timer = setTimeout(() => {
            state.tapTimers.delete(hitbox);

            if (video.paused) {
                playVideo(video, false);
                triggerPlayHud(container, true);
            } else {
                pauseVideo(video);
                triggerPlayHud(container, false);
            }
        }, 220);

        state.tapTimers.set(hitbox, timer);
    }

    // ============================================================================
    // PROGRESSIVE FALLBACK FOR LEGACY PORTRAIT VIDEOS
    // ============================================================================

    function checkAndPromoteLegacyVideo(video) {
        if (!video) return;

        const inspectAndApply = () => {
            if (!video.videoWidth || !video.videoHeight) return;
            const isPortrait = video.videoHeight > video.videoWidth;
            if (!isPortrait) return;

            const landscapeContainer = video.closest('.landscape-video-container');
            if (landscapeContainer && !landscapeContainer.classList.contains('is-promoted-reel')) {
                landscapeContainer.classList.remove('ratio-16x9');
                landscapeContainer.classList.add('ratio-9x16', 'is-promoted-reel');
                const wrapper = landscapeContainer.closest('.landscape-video-wrapper');
                if (wrapper) {
                    wrapper.classList.add('is-promoted-reel-wrapper');
                }
                console.log('[VideoManager] Promoted legacy vertical video to reel aspect ratio:', video.id);
            }
        };

        if (video.readyState >= 1) {
            inspectAndApply();
        } else {
            video.addEventListener('loadedmetadata', inspectAndApply, { once: true });
        }
    }

    // ============================================================================
    // FULL-SCREEN REELS OVERLAY MODE
    // ============================================================================

    function buildSnapItemFromReelCard(card) {
        const postId = card.dataset.postId || extractPostId(card);
        const video = card.querySelector('video');
        if (!video) return null;

        const videoSrc = video.getAttribute('src') || (video.querySelector('source') ? video.querySelector('source').getAttribute('src') : '') || video.dataset.videoUrl || '';
        const poster = video.getAttribute('poster') || '';
        const hlsUrl = video.dataset.hlsUrl || '';

        // Extract author info
        const authorLink = card.querySelector('.reel-scrim-top a[href*="profile"]') || card.querySelector('a[href*="profile"]');
        const authorAvatar = authorLink?.querySelector('img')?.getAttribute('src') || '/static/images/default-avatar.png';
        const authorName = authorLink?.textContent?.trim() || 'Author';
        const authorHref = authorLink?.getAttribute('href') || '#';

        // Extract caption
        const captionEl = card.querySelector('.post-text-clamp-2') || card.querySelector('.post-content-text');
        const captionHtml = captionEl ? captionEl.innerHTML : '';

        // Extract like count & state
        const likeBtn = card.querySelector('.like-button');
        const likeCount = card.querySelector('.reel-action-item .reel-action-label')?.textContent?.trim() || '0';
        const isLiked = likeBtn?.classList?.contains('liked') || false;

        // Extract comment count
        const commentCount = card.querySelectorAll('.reel-action-item .reel-action-label')[1]?.textContent?.trim() || '0';

        const snapItem = document.createElement('div');
        snapItem.className = 'reels-snap-item';
        snapItem.dataset.postId = postId;

        snapItem.innerHTML = `
            <div class="reel-fullscreen-content">
                <video class="fullscreen-reel-video w-100 h-100"
                       id="fs-video-${postId}"
                       playsinline loop preload="metadata"
                       poster="${poster}"
                       data-post-id="${postId}"
                       ${hlsUrl ? `data-hls-url="${hlsUrl}"` : ''}
                       data-video-url="${videoSrc}">
                    <source src="${videoSrc}" type="video/mp4">
                </video>

                <button type="button"
                        class="reel-center-hitbox reel-tap-hitbox"
                        data-post-id="${postId}"
                        aria-label="Play or pause reel">
                </button>

                <div class="reel-play-hud" aria-hidden="true">
                    <i class="bi bi-play-fill"></i>
                </div>

                <div class="reel-heart-burst">
                    <i class="bi bi-heart-fill"></i>
                </div>

                <!-- Top Scrim -->
                <div class="reel-scrim-top position-absolute top-0 start-0 w-100 d-flex align-items-center justify-content-between p-3" style="z-index: 4;">
                    <div class="d-flex align-items-center gap-2 min-w-0">
                        <a href="${authorHref}" class="flex-shrink-0 text-decoration-none">
                            <img src="${authorAvatar}" class="rounded-circle border border-2 border-white shadow-sm" style="width: 38px; height: 38px; object-fit: cover;" alt="${authorName}">
                        </a>
                        <div class="min-w-0">
                            <a href="${authorHref}" class="text-white fw-bold text-decoration-none small text-truncate d-inline-block mw-100" style="text-shadow: 0 1px 3px rgba(0,0,0,0.85);">
                                ${authorName}
                            </a>
                        </div>
                    </div>
                    <button type="button" class="btn btn-icon-hitbox text-white fs-4 close-fs-reels-btn" title="Close" aria-label="Close">
                        <i class="bi bi-x-lg" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.8));"></i>
                    </button>
                </div>

                <!-- Floating Right Engagement Stack -->
                <div class="reel-actions-stack">
                    <div class="reel-action-item">
                        <button type="button" class="reel-action-btn fs-like-proxy-btn text-white ${isLiked ? 'liked text-danger' : ''}" data-post-id="${postId}">
                            <i class="bi ${isLiked ? 'bi-heart-fill text-danger' : 'bi-heart'}"></i>
                        </button>
                        <span class="reel-action-label">${likeCount}</span>
                    </div>

                    <div class="reel-action-item">
                        <a href="/posts/${postId}/" class="reel-action-btn text-white text-decoration-none">
                            <i class="bi bi-chat-dots-fill"></i>
                        </a>
                        <span class="reel-action-label">${commentCount}</span>
                    </div>

                    <div class="reel-action-item">
                        <button type="button" class="reel-action-btn text-white" data-bs-toggle="modal" data-bs-target="#globalShareModal" data-post-id="${postId}">
                            <i class="bi bi-share-fill"></i>
                        </button>
                        <span class="reel-action-label">Share</span>
                    </div>

                    <div class="reel-action-item">
                        <button type="button" class="reel-action-btn reel-mute-btn text-white" data-action="mute-toggle">
                            <i class="bi ${isGlobalMuted ? 'bi-volume-mute-fill' : 'bi-volume-up-fill'}"></i>
                        </button>
                        <span class="reel-action-label reel-mute-label">${isGlobalMuted ? 'Mute' : 'Sound'}</span>
                    </div>
                </div>

                <!-- Bottom Scrim & Caption -->
                <div class="reel-scrim-bottom position-absolute bottom-0 start-0 w-100 p-3 d-flex flex-column justify-content-end" style="pointer-events: none; z-index: 4;">
                    <div style="pointer-events: auto; max-width: calc(100% - 64px);">
                        <div class="post-text-clamp-2 fs-6 mb-2" onclick="this.classList.toggle('is-expanded');">
                            ${captionHtml}
                        </div>
                    </div>
                </div>
            </div>
        `;

        return snapItem;
    }

    function openFullscreenReels(targetPostId) {
        const overlay = document.getElementById('fullscreenReelsOverlay');
        const viewport = document.getElementById('reelsSnapViewport');
        if (!overlay || !viewport) return;

        // Pause feed playback and save scroll offset
        state.previousScrollY = window.scrollY;
        pauseAllVideos();

        state.isFullScreenActive = true;
        document.body.classList.add('reels-active');
        overlay.classList.remove('d-none');
        overlay.setAttribute('aria-hidden', 'false');

        // Clear previous snap tracks
        viewport.innerHTML = '';

        // Query all inline reels
        const inlineReels = document.querySelectorAll('.reel-card-container');
        if (inlineReels.length === 0) {
            console.warn('[VideoManager] No inline reels found to populate fullscreen viewer');
            return;
        }

        createFullscreenObserver();

        let targetSnapItem = null;
        inlineReels.forEach(card => {
            const snapItem = buildSnapItemFromReelCard(card);
            if (snapItem) {
                viewport.appendChild(snapItem);
                state.fullscreenObserver.observe(snapItem);

                const video = snapItem.querySelector('video');
                if (video) {
                    video.muted = isGlobalMuted;
                }

                if (snapItem.dataset.postId === String(targetPostId)) {
                    targetSnapItem = snapItem;
                }
            }
        });

        // Scroll to target reel and start playback
        if (targetSnapItem) {
            setTimeout(() => {
                targetSnapItem.scrollIntoView({ behavior: 'instant', block: 'start' });
                const targetVideo = targetSnapItem.querySelector('video');
                if (targetVideo) {
                    playVideo(targetVideo, true);
                }
            }, 50);
        } else if (viewport.firstElementChild) {
            const firstVideo = viewport.firstElementChild.querySelector('video');
            if (firstVideo) playVideo(firstVideo, true);
        }

        console.log('[VideoManager] Fullscreen reels overlay opened at post:', targetPostId);
    }

    function closeFullscreenReels() {
        const overlay = document.getElementById('fullscreenReelsOverlay');
        const viewport = document.getElementById('reelsSnapViewport');
        if (!overlay) return;

        // Pause active fullscreen video
        pauseAllVideos();

        if (state.fullscreenObserver) {
            state.fullscreenObserver.disconnect();
        }

        if (viewport) {
            const fsVideos = viewport.querySelectorAll('video');
            fsVideos.forEach(v => cleanupVideo(v));
            viewport.innerHTML = '';
        }

        overlay.classList.add('d-none');
        overlay.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('reels-active');
        state.isFullScreenActive = false;

        // Restore exact previous scroll position
        window.scrollTo({
            top: state.previousScrollY,
            behavior: 'instant'
        });

        console.log('[VideoManager] Fullscreen reels overlay closed. Restored scroll:', state.previousScrollY);
    }

    // ============================================================================
    // INITIALIZATION & EVENT DELEGATION
    // ============================================================================

    function setupDelegatedListeners() {
        // Tap and Hitbox handling
        document.addEventListener('click', function(event) {
            // Hitbox single vs. double tap
            const hitbox = event.target.closest('.reel-center-hitbox, .reel-tap-hitbox');
            if (hitbox) {
                event.preventDefault();
                event.stopPropagation();
                handleHitboxTap(hitbox, event);
                return;
            }

            // Mute toggle button
            const muteBtn = event.target.closest('.reel-mute-btn, .video-mute-toggle, [data-action="mute-toggle"]');
            if (muteBtn) {
                event.preventDefault();
                event.stopPropagation();
                toggleGlobalMute();
                return;
            }

            // Expand to Fullscreen Reel
            const expandBtn = event.target.closest('.reel-expand-btn, [data-action="fullscreen"]');
            if (expandBtn) {
                event.preventDefault();
                event.stopPropagation();
                const postId = extractPostId(expandBtn);
                openFullscreenReels(postId);
                return;
            }

            // Feed Reel Card Click -> open fullscreen reels (if clicked outside interactive buttons/links)
            const inlineReelCard = event.target.closest('.reel-card-container');
            if (inlineReelCard && !inlineReelCard.closest('#fullscreenReelsOverlay') && !inlineReelCard.closest('.reels-snap-item')) {
                const isInteractive = event.target.closest('a, button, [data-bs-toggle], [data-action], input, textarea, .like-button');
                if (!isInteractive) {
                    event.preventDefault();
                    event.stopPropagation();
                    const postId = extractPostId(inlineReelCard);
                    if (postId) {
                        openFullscreenReels(postId);
                    }
                    return;
                }
            }

            // Close Fullscreen Reel
            const closeBtn = event.target.closest('#closeReelsOverlay, .close-fs-reels-btn');
            if (closeBtn) {
                event.preventDefault();
                event.stopPropagation();
                closeFullscreenReels();
                return;
            }

            // Proxy like button in fullscreen modal -> triggers inline like button
            const fsLikeBtn = event.target.closest('.fs-like-proxy-btn');
            if (fsLikeBtn) {
                event.preventDefault();
                event.stopPropagation();
                const postId = fsLikeBtn.dataset.postId;
                const inlineLikeBtn = document.querySelector(`#reel-like-wrap-${postId} .like-button`);
                if (inlineLikeBtn) {
                    inlineLikeBtn.click();
                }
                const icon = fsLikeBtn.querySelector('i');
                const wasLiked = fsLikeBtn.classList.toggle('liked');
                fsLikeBtn.classList.toggle('text-danger', wasLiked);
                if (icon) {
                    icon.className = wasLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
                }
                return;
            }
        });

        // Close fullscreen on ESC key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape' && state.isFullScreenActive) {
                closeFullscreenReels();
            }
        });

        // Manual play on landscape video -> pause any active reel
        document.addEventListener('play', function(event) {
            const video = event.target;
            if (video.tagName !== 'VIDEO') return;

            if (state.currentPlayingVideo && state.currentPlayingVideo !== video) {
                pauseVideo(state.currentPlayingVideo);
            }
            state.currentPlayingVideo = video;
        }, true);

        // Pause on visibility change
        document.addEventListener('visibilitychange', function() {
            if (document.hidden && state.currentPlayingVideo) {
                pauseVideo(state.currentPlayingVideo);
            }
        });
    }

    function initializeVideos(container = document.body) {
        if (!state.feedObserver) {
            createFeedObserver();
        }

        const videos = container.querySelectorAll('video');
        videos.forEach(video => {
            if (!video.dataset.pwaniObserved) {
                video.dataset.pwaniObserved = 'true';
                video.muted = isGlobalMuted;

                const isReel = isReelElement(video);
                if (isReel) {
                    // Feed observer tracks reels for 65% visibility autoplay
                    state.feedObserver.observe(video);
                } else {
                    // Landscape videos: strictly require manual play
                    video.dataset.autoplay = 'false';
                    video.controls = true;
                    // Check if vertical video trapped in landscape container
                    checkAndPromoteLegacyVideo(video);
                }
            }
        });

        syncMuteButtons();
    }

    function setupMutationObserver() {
        if (state.mutationObserver) {
            state.mutationObserver.disconnect();
        }

        state.mutationObserver = new MutationObserver(mutations => {
            let hasNewVideos = false;
            mutations.forEach(mutation => {
                mutation.addedNodes.forEach(node => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.tagName === 'VIDEO' || (node.querySelector && node.querySelector('video'))) {
                            hasNewVideos = true;
                        }
                    }
                });
            });

            if (hasNewVideos) {
                initializeVideos(document.body);
            }
        });

        state.mutationObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    function initHTMXIntegration() {
        document.addEventListener('htmx:beforeSwap', function(event) {
            if (state.isFullScreenActive) {
                closeFullscreenReels();
            }
            const target = event.detail.target;
            if (target && target.querySelectorAll) {
                const oldVideos = target.querySelectorAll('video');
                oldVideos.forEach(v => cleanupVideo(v));
            }
        });

        document.addEventListener('htmx:beforeCleanupElement', function(event) {
            const elt = event.target;
            if (elt && elt.querySelectorAll) {
                const oldVideos = elt.querySelectorAll('video');
                oldVideos.forEach(v => cleanupVideo(v));
            }
        });

        document.addEventListener('htmx:afterSwap', function(event) {
            const target = event.detail.target;
            if (target && target.querySelector && target.querySelector('video')) {
                initializeVideos(target);
            }
        });

        document.addEventListener('htmx:load', function(event) {
            const elt = event.detail?.elt || document.body;
            if (elt && elt.querySelector && elt.querySelector('video')) {
                initializeVideos(elt);
            }
        });
    }

    function init() {
        if (state.isInitialized) return;

        createFeedObserver();
        setupDelegatedListeners();
        setupMutationObserver();
        initHTMXIntegration();
        initializeVideos(document.body);

        state.isInitialized = true;
        console.log('[VideoManager] Unified video playback engine initialized');
    }

    // ============================================================================
    // PUBLIC API
    // ============================================================================

    window.PwaniNetVideoManager = {
        init,
        playVideo,
        pauseVideo,
        pauseAllVideos,
        cleanupVideo,
        setGlobalMute,
        toggleGlobalMute,
        checkAndPromoteLegacyVideo,
        openFullscreenReels,
        closeFullscreenReels,
        get isGlobalMuted() { return isGlobalMuted; },
        get state() { return state; }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
