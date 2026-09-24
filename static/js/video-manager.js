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
                if (!state.isFullScreenActive && isReelElement(video)) {
                    document.body.classList.add('has-active-reel');
                } else if (!isReelElement(video)) {
                    document.body.classList.remove('has-active-reel');
                }
            }).catch(err => {
                console.warn('[VideoManager] Play rejected:', err);
                if (isAutoplay && !video.muted) {
                    // Browser prevented unmuted autoplay: force muted and retry silently
                    video.muted = true;
                    video.play().then(() => {
                        state.currentPlayingVideo = video;
                        if (!state.isFullScreenActive && isReelElement(video)) {
                            document.body.classList.add('has-active-reel');
                        }
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
            document.body.classList.remove('has-active-reel');
        }
    }

    function pauseAllVideos() {
        document.querySelectorAll('video').forEach(vid => {
            pauseVideo(vid);
        });
        document.body.classList.remove('has-active-reel');
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
        const container = hitbox.closest('.reel-card-container') || hitbox.closest('.reel-fullscreen-content') || hitbox.closest('.reels-snap-item');
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
        const authorLink = card.querySelector('a[href*="profile"]');
        const authorAvatar = card.querySelector('.reel-author-avatar')?.getAttribute('src') || authorLink?.querySelector('img')?.getAttribute('src') || '/static/images/default-avatar.png';
        const authorName = card.querySelector('.reel-author-name')?.textContent?.trim() || authorLink?.textContent?.trim() || '@author';
        const authorHref = authorLink?.getAttribute('href') || '#';
        const timeAgo = card.querySelector('.reel-meta-row span')?.textContent?.trim() || '';

        // Extract caption
        const captionEl = card.querySelector('.reel-caption-text') || card.querySelector('.post-text-clamp-2') || card.querySelector('.post-content-text');
        const captionHtml = captionEl ? captionEl.innerHTML : '';
        const hasCaption = captionHtml.trim().length > 0;
        const isLongCaption = (captionEl?.textContent?.trim()?.length || 0) > 70;

        // Extract counts & state
        const likeBtn = card.querySelector('.like-button');
        const likeCount = card.querySelector('.reel-action-item .reel-action-label')?.textContent?.trim() || '0';
        const isLiked = likeBtn?.classList?.contains('liked') || false;

        const commentCount = card.querySelectorAll('.reel-action-item .reel-action-label')[1]?.textContent?.trim() || '0';
        const repostCount = card.querySelectorAll('.reel-action-item .reel-action-label')[2]?.textContent?.trim() || '0';

        // Extract badges & audio
        const unitBadge = card.querySelector('.reel-unit-badge')?.outerHTML || '';
        const dropdownMenu = card.querySelector('.dropdown')?.innerHTML || '';
        const audioTitle = card.querySelector('.reel-audio-title')?.textContent?.trim() || ('Original Audio • ' + authorName);

        const snapItem = document.createElement('div');
        snapItem.className = 'reels-snap-item';
        snapItem.dataset.postId = postId;

        snapItem.innerHTML = `
            <div class="reel-fullscreen-content position-relative overflow-hidden w-100 h-100 bg-black">
                <!-- Main Video Element -->
                <video class="fullscreen-reel-video feed-video w-100 h-100"
                       id="fs-video-${postId}"
                       playsinline loop preload="metadata"
                       poster="${poster}"
                       data-post-id="${postId}"
                       ${hlsUrl ? `data-hls-url="${hlsUrl}"` : ''}
                       data-video-url="${videoSrc}">
                    <source src="${videoSrc}" type="video/mp4">
                </video>

                <!-- Central Interactive Hitbox (Single tap play/pause, Double tap heart like) -->
                <button type="button"
                        class="reel-center-hitbox reel-tap-hitbox"
                        data-post-id="${postId}"
                        aria-label="Play or pause reel">
                </button>

                <!-- Transient Play/Pause HUD Indicator -->
                <div class="reel-play-hud" aria-hidden="true">
                    <i class="bi bi-play-fill"></i>
                </div>

                <!-- Heart Burst Animation Target -->
                <div class="reel-heart-burst" aria-hidden="true">
                    <i class="bi bi-heart-fill"></i>
                </div>

                <!-- Top Scrim -->
                <div class="reel-scrim-top position-absolute top-0 start-0 w-100 d-flex align-items-center justify-content-between px-2.5 pt-2 pb-1" style="z-index: 4;">
                    <div class="d-flex align-items-center gap-2" style="margin-left: 52px;">
                        ${unitBadge}
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        ${dropdownMenu ? `<div class="dropdown">${dropdownMenu}</div>` : ''}
                    </div>
                </div>

                <!-- Floating Right Engagement Stack -->
                <div class="reel-actions-stack">
                    <div class="reel-action-item">
                        <button type="button" class="reel-action-icon-btn fs-like-proxy-btn text-white ${isLiked ? 'liked text-danger' : ''}" data-post-id="${postId}" aria-label="Like reel">
                            <i class="bi ${isLiked ? 'bi-heart-fill text-danger' : 'bi-heart'}"></i>
                        </button>
                        <span class="reel-action-label">${likeCount}</span>
                    </div>

                    <div class="reel-action-item">
                        <a href="/posts/${postId}/" class="reel-action-icon-btn text-white text-decoration-none" aria-label="Comments">
                            <i class="bi bi-chat-dots-fill"></i>
                        </a>
                        <span class="reel-action-label">${commentCount}</span>
                    </div>

                    <div class="reel-action-item">
                        <button type="button"
                                class="reel-action-icon-btn text-white"
                                data-bs-toggle="modal"
                                data-bs-target="#globalRepostModal"
                                data-post-id="${postId}"
                                aria-label="Repost">
                            <i class="bi bi-repeat"></i>
                        </button>
                        <span class="reel-action-label">${repostCount}</span>
                    </div>

                    <div class="reel-action-item">
                        <button type="button"
                                class="reel-action-icon-btn text-white"
                                data-bs-toggle="modal"
                                data-bs-target="#globalShareModal"
                                data-post-id="${postId}"
                                aria-label="Share reel">
                            <i class="bi bi-send-fill"></i>
                        </button>
                    </div>

                    <div class="reel-action-item">
                        <button type="button" class="reel-action-icon-btn reel-mute-btn text-white" data-action="mute-toggle" aria-label="Toggle sound">
                            <i class="bi ${isGlobalMuted ? 'bi-volume-mute-fill' : 'bi-volume-up-fill'}"></i>
                        </button>
                    </div>
                </div>

                <!-- Bottom Scrim & Consolidated Author / Caption Overlay -->
                <div class="reel-scrim-bottom position-absolute bottom-0 start-0 w-100">
                    <div class="reel-bottom-content">
                        <!-- Author Row -->
                        <div class="d-flex align-items-center gap-2 mb-2">
                            <a href="${authorHref}" class="flex-shrink-0 text-decoration-none">
                                <img src="${authorAvatar}" class="rounded-circle border border-2 border-white shadow-sm reel-author-avatar" alt="${authorName}">
                            </a>
                            <div class="min-w-0 flex-grow-1">
                                <div class="d-flex align-items-center gap-1.5">
                                    <a href="${authorHref}" class="text-white fw-bold text-decoration-none reel-author-name text-truncate">
                                        ${authorName}
                                    </a>
                                </div>
                                <div class="text-white-50 d-flex align-items-center reel-meta-row">
                                    <span>${timeAgo}</span>
                                    <span class="mx-1">&middot;</span>
                                    <i class="bi bi-globe-americas" title="Public" aria-label="Public"></i>
                                </div>
                            </div>
                        </div>

                        <!-- Clamped Caption with Controlled Height & Composer Scroll -->
                        ${hasCaption ? `
                        <div class="reel-caption-wrap mb-2">
                            <div id="fs-caption-${postId}" class="reel-caption-text post-text-clamp-2">
                                ${captionHtml}
                            </div>
                            ${isLongCaption ? `
                            <button type="button" class="reel-caption-toggle" data-target="#fs-caption-${postId}" aria-expanded="false">
                                more
                            </button>` : ''}
                        </div>` : ''}

                        <!-- Animated Audio Track Pill -->
                        <div class="reel-audio-wrapper">
                            <div class="reel-audio-pill">
                                <div class="reel-audio-waves" aria-hidden="true">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                                <span class="reel-audio-title text-truncate">${audioTitle}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Video Playback Progress Bar Line -->
                    <div class="reel-progress-track">
                        <div class="reel-progress-bar" id="fs-progress-${postId}"></div>
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

        // Continuous infinite-scroll hook: when user scrolls near bottom of viewport, trigger feed load
        viewport.onscroll = function() {
            if (!state.isFullScreenActive) return;
            const remainingScroll = viewport.scrollHeight - (viewport.scrollTop + viewport.clientHeight);
            if (remainingScroll < viewport.clientHeight * 1.5) {
                const loadTrigger = document.getElementById('feed-load-trigger');
                if (loadTrigger && typeof htmx !== 'undefined') {
                    htmx.trigger(loadTrigger, 'revealed');
                }
            }
        };

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

            // Caption expand toggle
            const captionToggle = event.target.closest('.reel-caption-toggle');
            if (captionToggle) {
                event.preventDefault();
                event.stopPropagation();
                const targetSelector = captionToggle.dataset.target;
                const captionEl = document.querySelector(targetSelector);
                if (captionEl) {
                    const isExp = captionEl.classList.toggle('is-expanded');
                    captionToggle.textContent = isExp ? 'less' : 'more';
                    captionToggle.setAttribute('aria-expanded', isExp ? 'true' : 'false');
                }
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
                const label = fsLikeBtn.parentElement?.querySelector('.reel-action-label');
                if (label) {
                    let count = parseInt(label.textContent.trim(), 10) || 0;
                    count = wasLiked ? count + 1 : Math.max(0, count - 1);
                    label.textContent = count;
                }
                return;
            }
        });

        // Video scrubber progress update
        document.addEventListener('timeupdate', function(event) {
            const video = event.target;
            if (video.tagName !== 'VIDEO') return;
            if (!video.duration || isNaN(video.duration)) return;
            const percent = (video.currentTime / video.duration) * 100;
            const container = video.closest('.reel-card-container') || video.closest('.reels-snap-item');
            if (container) {
                const bar = container.querySelector('.reel-progress-bar');
                if (bar) {
                    bar.style.width = `${percent}%`;
                }
            }
        }, true);

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

        // Desktop firm reel-card scroll snap locking:
        // Guarantees desktop users never get stuck in an unclipped, half-visible reel position
        let desktopSnapTimeout = null;
        let isAutoSnapping = false;

        function checkAndSnapDesktopReel() {
            if (state.isFullScreenActive || window.innerWidth < 768 || isAutoSnapping) return;

            clearTimeout(desktopSnapTimeout);
            desktopSnapTimeout = setTimeout(() => {
                if (state.isFullScreenActive || isAutoSnapping) return;

                const reelCards = document.querySelectorAll('.reel-card-container');
                if (reelCards.length === 0) return;

                const navbarHeight = 56;
                const targetOffsetTop = navbarHeight + 8; // Snap position directly under navbar

                let bestCard = null;
                let minDistance = Infinity;

                reelCards.forEach(card => {
                    const rect = card.getBoundingClientRect();
                    const visibleHeight = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, targetOffsetTop);
                    if (visibleHeight > 0) {
                        const dist = Math.abs(rect.top - targetOffsetTop);
                        if (dist < minDistance) {
                            minDistance = dist;
                            bestCard = card;
                        }
                    }
                });

                // If a reel card is within snap attraction range and not yet perfectly aligned
                if (bestCard && minDistance > 6 && minDistance < window.innerHeight * 0.45) {
                    const rect = bestCard.getBoundingClientRect();
                    const deltaY = rect.top - targetOffsetTop;

                    isAutoSnapping = true;
                    window.scrollBy({
                        top: deltaY,
                        behavior: 'smooth'
                    });

                    setTimeout(() => {
                        isAutoSnapping = false;
                    }, 450);
                }
            }, 90);
        }

        window.addEventListener('scroll', checkAndSnapDesktopReel, { passive: true });
        if ('onscrollend' in window) {
            window.addEventListener('scrollend', checkAndSnapDesktopReel, { passive: true });
        }
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

        // If fullscreen is active, continuously append newly loaded reels into reelsSnapViewport
        if (state.isFullScreenActive) {
            const viewport = document.getElementById('reelsSnapViewport');
            if (viewport) {
                const currentPostIds = new Set(Array.from(viewport.querySelectorAll('.reels-snap-item')).map(c => c.dataset.postId));
                const allInlineReels = document.querySelectorAll('.reel-card-container');
                allInlineReels.forEach(card => {
                    const pid = card.dataset.postId || extractPostId(card);
                    if (pid && !currentPostIds.has(pid)) {
                        const newSnapItem = buildSnapItemFromReelCard(card);
                        if (newSnapItem) {
                            viewport.appendChild(newSnapItem);
                            if (state.fullscreenObserver) {
                                state.fullscreenObserver.observe(newSnapItem);
                            }
                            const v = newSnapItem.querySelector('video');
                            if (v) v.muted = isGlobalMuted;
                        }
                    }
                });
            }
        }
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
