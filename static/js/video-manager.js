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
        hasLongPressed: false,
        isInitialized: false
    };

    // ============================================================================
    // UTILITY HELPERS
    // ============================================================================

    function extractPostId(element) {
        if (!element) return null;
        if (element.dataset && element.dataset.postId) {
            const id = String(element.dataset.postId).trim();
            if (id && id !== 'null' && id !== 'undefined') return id;
        }
        if (element.id) {
            if (element.id.startsWith('post-card-')) {
                const id = element.id.replace('post-card-', '').trim();
                if (id && id !== 'null' && id !== 'undefined') return id;
            }
            if (element.id.startsWith('video-')) {
                const id = element.id.replace('video-', '').trim();
                if (id && id !== 'null' && id !== 'undefined') return id;
            }
            if (element.id.startsWith('fs-video-')) {
                const id = element.id.replace('fs-video-', '').trim();
                if (id && id !== 'null' && id !== 'undefined') return id;
            }
            if (element.id.startsWith('reel-card-')) {
                const id = element.id.replace('reel-card-', '').trim();
                if (id && id !== 'null' && id !== 'undefined') return id;
            }
            if (element.id.startsWith('reel-hitbox-')) {
                const id = element.id.replace('reel-hitbox-', '').trim();
                if (id && id !== 'null' && id !== 'undefined') return id;
            }
        }
        const parent = element.closest('[data-post-id]');
        if (parent && parent.dataset && parent.dataset.postId) {
            const id = String(parent.dataset.postId).trim();
            if (id && id !== 'null' && id !== 'undefined') return id;
        }
        return null;
    }

    function isReelElement(video) {
        if (!video) return false;
        if (video.classList.contains('reel-video-element') || video.classList.contains('fullscreen-reel-video')) return true;
        if (video.closest('.reel-card-container, .reel-post-card, .reel-stage-container') || video.closest('.reels-snap-item')) return true;
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

        // Sync all video elements across feed and overlays (excluding carousel preview videos)
        document.querySelectorAll('video').forEach(vid => {
            if (vid.classList.contains('reels-carousel-video') || vid.closest('.reels-carousel-shelf')) {
                vid.muted = true;
                return;
            }
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

        // Apply global mute (carousel previews are always strictly muted)
        if (video.classList.contains('reels-carousel-video') || video.closest('.reels-carousel-shelf')) {
            video.muted = true;
            video.volume = 0;
        } else {
            video.muted = isGlobalMuted;
        }

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
        stopCarouselAutoplay();
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

            if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
                playVideo(video, true);
                const vinyl = snapItem.querySelector('.reel-vinyl-disc');
                if (vinyl) vinyl.classList.add('is-playing');

                // Near end of queue: append more videos dynamically
                checkAndAppendMoreFullscreenVideos(snapItem);

                // Update TikTok desktop rail and exterior engagement buttons
                updateDesktopSideRail(snapItem);
                updateFullscreenNavButtons(snapItem);
            } else if (!entry.isIntersecting || entry.intersectionRatio < 0.5) {
                if (video === state.currentPlayingVideo) {
                    pauseVideo(video);
                }
                const vinyl = snapItem.querySelector('.reel-vinyl-disc');
                if (vinyl) vinyl.classList.remove('is-playing');
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
            threshold: 0.5
        });
    }

    function appendNewVideosToFullscreenViewport() {
        if (!state.isFullScreenActive) return;
        const viewport = document.getElementById('reelsSnapViewport');
        if (!viewport) return;

        const existingIds = new Set(Array.from(viewport.children).map(item => String(item.dataset.postId).trim()));

        const cardSelectors = [
            '.reel-card-container',
            '.reel-post-card',
            '.reels-carousel-card',
            '.post-card',
            '.landscape-video-container'
        ];

        document.querySelectorAll(cardSelectors.join(', ')).forEach(card => {
            const vid = card.querySelector('video') || (card.tagName === 'VIDEO' ? card : null);
            if (!vid || card.classList.contains('reels-carousel-shelf')) return;

            const cardPostId = String(extractPostId(card) || vid.dataset.postId || card.dataset.postId || '').trim();
            if (!cardPostId || cardPostId === 'null' || cardPostId === 'undefined' || existingIds.has(cardPostId)) return;

            existingIds.add(cardPostId);
            const snapItem = buildSnapItemFromReelCard(card);
            if (snapItem) {
                viewport.appendChild(snapItem);
                if (state.fullscreenObserver) {
                    state.fullscreenObserver.observe(snapItem);
                }
            }
        });

        updateFullscreenNavButtons();
    }

    function checkAndAppendMoreFullscreenVideos(currentSnapItem) {
        if (!state.isFullScreenActive) return;
        const viewport = document.getElementById('reelsSnapViewport');
        if (!viewport) return;

        const items = Array.from(viewport.children);
        const idx = items.indexOf(currentSnapItem);

        if (idx >= items.length - 2) {
            appendNewVideosToFullscreenViewport();

            const trigger = document.getElementById('feed-load-trigger');
            if (trigger && typeof htmx !== 'undefined') {
                htmx.trigger(trigger, 'revealed');
            }
        }
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
        if (state.hasLongPressed) {
            state.hasLongPressed = false;
            return;
        }

        const container = hitbox.closest('.reel-card-container, .reel-post-card, .reel-stage-container, .reel-fullscreen-content, .reels-snap-item');
        if (!container) return;

        const video = container.querySelector('video');
        if (!video) return;

        const postId = extractPostId(container);

        // Double tap: heart burst animation + like (works in both feed and fullscreen)
        if (state.tapTimers.has(hitbox)) {
            clearTimeout(state.tapTimers.get(hitbox));
            state.tapTimers.delete(hitbox);

            triggerHeartBurst(container, event.clientX, event.clientY);

            const fsLikeBtn = container.querySelector('.fs-like-proxy-btn') ||
                              (postId ? document.querySelector(`.fs-like-proxy-btn[data-post-id="${postId}"]`) : null) ||
                              document.getElementById('fsDesktopLikeBtn');
            if (fsLikeBtn) {
                if (!fsLikeBtn.classList.contains('liked')) {
                    fsLikeBtn.click();
                }
            } else {
                const likeBtn = container.querySelector('.like-button') ||
                               (postId ? document.querySelector(`#reel-like-wrap-${postId} .like-button`) : null);
                if (likeBtn && !likeBtn.classList.contains('liked') && !likeBtn.classList.contains('text-danger')) {
                    likeBtn.click();
                }
            }
            return;
        }

        // Single tap: toggle play / pause (in both feed and fullscreen)
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
        const rawPostId = card.dataset.postId || extractPostId(card);
        const postId = rawPostId ? String(rawPostId).trim() : '';
        if (!postId || postId === 'null' || postId === 'undefined') return null;

        const video = card.querySelector('video');
        if (!video) return null;

        const videoSrc = video.dataset.videoUrl || (video.querySelector('source') ? video.querySelector('source').getAttribute('src') : '') || video.currentSrc || video.getAttribute('src') || '';
        const poster = video.getAttribute('poster') ||
                       card.querySelector('.reel-ambient-img')?.getAttribute('src') ||
                       card.querySelector('.media-download-btn')?.dataset?.thumbnail ||
                       '';
        const hlsUrl = video.dataset.hlsUrl || '';

        // Extract author avatar & details (supports datasets from carousel, reel cards, and standard postcards)
        const authorImg = card.querySelector('.fb-author-avatar-img') ||
                          card.querySelector('.reel-creator-row img') ||
                          card.querySelector('.fb-avatar-container img') ||
                          card.querySelector('.reel-scrim-bottom img') ||
                          card.querySelector('.post-avatar-img') ||
                          card.querySelector('.reel-vinyl-art');
        const authorAvatar = card.dataset.authorAvatar || authorImg?.getAttribute('src') || '/static/images/default-avatar.png';

        const authorLink = card.querySelector('.fb-author-name') ||
                           card.querySelector('.reel-creator-row a') ||
                           card.querySelector('.reel-scrim-bottom a[href*="profile"]') ||
                           card.querySelector('a[href*="/users/user/"]') ||
                           card.querySelector('a[href*="/users/profile/"]');
        const authorName = card.dataset.author || authorLink?.textContent?.trim() || card.querySelector('.reel-options-btn')?.dataset.author || 'Author';
        const profileUrlHref = authorLink?.getAttribute('href') || '';
        const hrefMatch = profileUrlHref.match(/\/users\/user\/([^\/]+)/) || profileUrlHref.match(/\/users\/profile\/([^\/]+)/);
        const authorUsername = card.dataset.authorUsername ||
                               (hrefMatch ? hrefMatch[1] : null) ||
                               card.querySelector('.fb-author-username')?.textContent?.replace(/^@/, '')?.trim() ||
                               (authorName.startsWith('@') ? authorName.slice(1) : authorName);
        const profileUrl = card.dataset.authorProfile ||
                           profileUrlHref ||
                           `/users/user/${authorUsername}/`;

        // Extract campus unit badge and time if present
        const unitBadge = card.querySelector('.reel-unit-badge') || card.querySelector('.fb-sub-meta .badge');
        const unitCode = card.dataset.unit || unitBadge?.textContent?.trim() || '';
        const unitHtml = unitCode ?
            `<span class="badge bg-white bg-opacity-25 text-white border border-white border-opacity-20 px-2 py-1 reel-unit-badge"><i class="bi bi-mortarboard-fill me-1"></i>${unitCode}</span>` : '';

        const timeAgo = card.dataset.time ||
                        card.querySelector('.fb-sub-meta span:not(.badge)')?.textContent?.trim() ||
                        card.querySelector('.reel-scrim-top .text-white-50')?.textContent?.trim() ||
                        '';

        // Extract or construct follow chip
        const isFollowing = card.dataset.isFollowing === 'true';
        const isSelf = card.dataset.isSelf === 'true';
        let followBtnHtml = '';
        if (!isSelf && !isFollowing && authorUsername && authorUsername !== 'Author') {
            const followUrl = card.dataset.followUrl || `/users/follow/${authorUsername}/`;
            followBtnHtml = `
                <button type="button"
                        class="reel-follow-chip"
                        hx-post="${followUrl}"
                        hx-swap="none"
                        title="Follow"
                        aria-label="Follow"
                        onclick="event.stopPropagation(); this.remove();">
                    Follow
                </button>
            `;
        }

        // Extract or construct creator row (Avatar + Name + Handle + Follow chip + Time)
        const creatorRow = card.querySelector('.reel-creator-row');
        let creatorRowHtml = '';
        if (creatorRow) {
            creatorRowHtml = creatorRow.outerHTML;
        } else {
            creatorRowHtml = `
                <div class="reel-creator-row d-flex align-items-center gap-2 mb-2">
                    <div class="position-relative flex-shrink-0">
                        <a href="${profileUrl}" class="d-block text-decoration-none">
                            <img src="${authorAvatar}"
                                 class="rounded-circle border border-2 border-white shadow-sm"
                                 style="width: 40px; height: 40px; object-fit: cover;"
                                 alt="${authorUsername}">
                        </a>
                    </div>
                    <div class="min-w-0">
                        <div class="d-flex align-items-center gap-2">
                            <a href="${profileUrl}"
                               class="text-white fw-bold text-decoration-none text-truncate d-inline-block mw-100"
                               style="font-size: 0.92rem; text-shadow: 0 1px 3px rgba(0,0,0,0.9);">
                                @${authorUsername}
                            </a>
                            ${followBtnHtml}
                        </div>
                        <div class="text-white-50 small text-truncate d-flex align-items-center gap-1" style="font-size: 11px; text-shadow: 0 1px 2px rgba(0,0,0,0.85); line-height: 1.2;">
                            <span>${timeAgo}</span>
                            <span>&middot;</span>
                            <i class="bi bi-globe-americas" style="font-size: 10px;" title="Public"></i>
                        </div>
                    </div>
                </div>
            `;
        }

        // Extract caption with expander
        const captionWrap = card.querySelector('.reel-caption-wrap');
        let captionHtml = '';
        if (captionWrap) {
            captionHtml = captionWrap.outerHTML;
        } else {
            const rawCaption = card.dataset.caption ||
                               card.querySelector('.reel-caption-text')?.innerHTML ||
                               card.querySelector('.post-content-text')?.innerHTML ||
                               card.querySelector('.post-text-body')?.innerHTML ||
                               '';
            const cleanText = rawCaption.trim();
            if (cleanText) {
                const needsMore = cleanText.length > 70;
                captionHtml = `
                    <div class="reel-caption-wrap mb-2">
                        <div id="fs-reel-caption-${postId}" class="reel-caption-text post-text-clamp-2">
                            ${cleanText}
                        </div>
                        ${needsMore ? `
                        <button type="button"
                                class="reel-caption-toggle"
                                onclick="event.stopPropagation(); (function(btn){
                                    var c = btn.parentElement.querySelector('.reel-caption-text');
                                    if (!c) return;
                                    var exp = c.classList.toggle('is-expanded');
                                    btn.textContent = exp ? 'less' : '... more';
                                })(this);">
                            ... more
                        </button>` : ''}
                    </div>
                `;
            }
        }

        // Audio pill
        let audioWrapHtml = '';
        const existingAudioWrap = card.querySelector('.reel-audio-wrap');
        if (existingAudioWrap) {
            audioWrapHtml = existingAudioWrap.outerHTML;
        } else {
            audioWrapHtml = `
                <div class="reel-audio-wrap d-inline-flex align-items-center">
                    <span class="badge bg-dark bg-opacity-60 rounded-pill text-white small px-2.5 py-1 d-inline-flex align-items-center gap-1.5 reel-audio-pill" style="font-size: 11px; backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.18);">
                        <i class="bi bi-music-note-beamed text-primary"></i>
                        <span class="text-truncate reel-audio-ticker-text" style="max-width: 220px;">Original Audio - ${authorUsername}</span>
                    </span>
                </div>
            `;
        }

        // Extract like count & state
        const likeBtn = card.querySelector('.like-button');
        const likeCount = card.dataset.likes ||
                          card.querySelector(`[id^="reel-like-count-"]`)?.textContent?.trim() ||
                          card.querySelector('.postcard-like-count')?.textContent?.trim() ||
                          card.querySelector('.like-count')?.textContent?.trim() ||
                          card.querySelector(`[id^="like-section-"] .fw-bold`)?.textContent?.trim() ||
                          '0';
        const isLiked = card.dataset.isLiked === 'true' ||
                        likeBtn?.classList?.contains('liked') ||
                        likeBtn?.classList?.contains('text-danger') ||
                        false;

        // Extract comment count
        const commentCount = card.dataset.comments ||
                             card.querySelector(`[id^="reel-comment-count-"]`)?.textContent?.trim() ||
                             card.querySelector(`[id^="comment-count-"]`)?.textContent?.trim() ||
                             card.querySelector('.postcard-comment-btn span')?.textContent?.trim() ||
                             '0';

        const snapItem = document.createElement('div');
        snapItem.className = 'reels-snap-item';
        snapItem.dataset.postId = postId;
        snapItem.dataset.authorName = authorName;
        snapItem.dataset.authorUsername = authorUsername;
        snapItem.dataset.authorAvatar = authorAvatar;
        snapItem.dataset.profileUrl = profileUrl;
        snapItem.dataset.unitCode = unitCode;
        snapItem.dataset.timeAgo = timeAgo;
        snapItem.dataset.likes = likeCount;
        snapItem.dataset.isLiked = isLiked ? 'true' : 'false';
        snapItem.dataset.comments = commentCount;
        snapItem.dataset.videoUrl = videoSrc;
        snapItem.dataset.poster = poster;
        const rawCaptionText = (card.dataset.caption || card.querySelector('.reel-caption-text')?.textContent || card.querySelector('.post-content-text')?.textContent || card.querySelector('.post-text-body')?.textContent || '').trim();
        snapItem.dataset.caption = rawCaptionText;

        snapItem.innerHTML = `
            <div class="reel-fullscreen-content">
                <!-- Ambient Backdrop -->
                <div class="reel-ambient-backdrop" aria-hidden="true">
                    ${poster ? `<img src="${poster}" class="reel-ambient-img" alt="">` : '<div class="w-100 h-100 bg-black"></div>'}
                </div>

                <!-- Video Element with direct src for instant media engine decoding -->
                <video class="fullscreen-reel-video w-100 h-100"
                       id="fs-video-${postId}"
                       src="${videoSrc}"
                       playsinline loop preload="auto"
                       poster="${poster}"
                       data-post-id="${postId}"
                       ${hlsUrl ? `data-hls-url="${hlsUrl}"` : ''}
                       data-video-url="${videoSrc}">
                    <source src="${videoSrc}" type="video/mp4">
                </video>

                <!-- Tap Hitbox for play/pause HUD and heart burst -->
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
                <div class="reel-scrim-top position-absolute top-0 start-0 w-100 d-flex align-items-center justify-content-between" style="z-index: 4;">
                    <div class="d-flex align-items-center gap-2 min-w-0">
                        ${unitHtml}
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <button type="button"
                                class="reel-top-action-btn reel-options-btn text-white p-1 border-0 bg-transparent"
                                data-post-id="${postId}"
                                data-author="${authorName}"
                                title="Options"
                                aria-label="Options">
                            <i class="bi bi-three-dots-vertical fs-5"></i>
                        </button>
                    </div>
                </div>

                <!-- Floating Right Engagement Rail (Pure floating icons, no backdrop bubbles) -->
                <div class="reel-actions-stack">
                    <div class="reel-action-unit text-center">
                        <button type="button" class="reel-action-btn fs-like-proxy-btn text-white ${isLiked ? 'liked text-danger' : ''}" data-post-id="${postId}">
                            <i class="bi ${isLiked ? 'bi-heart-fill text-danger' : 'bi-heart'}"></i>
                        </button>
                        <span class="reel-action-label" id="fs-reel-like-count-${postId}">${likeCount}</span>
                    </div>

                    <div class="reel-action-unit text-center">
                        <button type="button" class="reel-action-btn text-white reel-comment-trigger" data-post-id="${postId}">
                            <i class="bi bi-chat-dots-fill"></i>
                        </button>
                        <span class="reel-action-label" id="fs-reel-comment-count-${postId}">${commentCount}</span>
                    </div>

                    <div class="reel-action-unit text-center">
                        <button type="button" class="reel-action-btn text-white" data-bs-toggle="modal" data-bs-target="#globalShareModal" data-post-id="${postId}" data-post-url="/post/${postId}/" data-video-url="${videoSrc}" data-poster-url="${poster}" data-post-content="${rawCaptionText.replace(/"/g, '&quot;')}">
                            <i class="bi bi-share-fill"></i>
                        </button>
                        <span class="reel-action-label">Share</span>
                    </div>

                    <div class="reel-action-unit text-center">
                        <button type="button" class="reel-action-btn reel-mute-btn text-white" data-action="mute-toggle">
                            <i class="bi ${isGlobalMuted ? 'bi-volume-mute-fill' : 'bi-volume-up-fill'}"></i>
                        </button>
                        <span class="reel-action-label reel-mute-label">${isGlobalMuted ? 'Mute' : 'Sound'}</span>
                    </div>

                    <div class="reel-action-unit reel-vinyl-unit text-center mt-1">
                        <div class="reel-vinyl-disc" data-post-id="${postId}">
                            <img src="${authorAvatar}" class="reel-vinyl-art" alt="${authorName}">
                        </div>
                    </div>
                </div>

                <!-- Bottom Scrim: Creator Identity, Caption, and Audio Pill (Option C) -->
                <div class="reel-scrim-bottom position-absolute bottom-0 start-0 w-100 d-flex flex-column justify-content-end" style="pointer-events: none; z-index: 4;">
                    <div class="reel-scrim-content">
                        ${creatorRowHtml}
                        ${captionHtml}
                        ${audioWrapHtml}
                    </div>
                </div>

                <!-- Bottom Edge Micro-Scrubber -->
                <div class="reel-progress-container position-absolute bottom-0 start-0 w-100" data-post-id="${postId}">
                    <div class="reel-progress-bar" id="fs-reel-progress-${postId}"></div>
                </div>
            </div>
        `;

        adaptSnapItemOrientation(snapItem, card);
        return snapItem;
    }

    let currentDesktopRailPostId = null;
    let sideRailWebSocket = null;
    let sideRailWsPostId = null;

    function closeSideRailWebSocket() {
        if (sideRailWebSocket) {
            try {
                sideRailWebSocket.onclose = null;
                sideRailWebSocket.onerror = null;
                sideRailWebSocket.onmessage = null;
                sideRailWebSocket.close();
            } catch (e) {}
            sideRailWebSocket = null;
            sideRailWsPostId = null;
        }
    }

    function initSideRailWebSocket(postId) {
        postId = postId ? String(postId).trim() : '';
        if (!postId || postId === 'null' || postId === 'undefined') return;
        if (sideRailWebSocket && sideRailWsPostId === postId && sideRailWebSocket.readyState === WebSocket.OPEN) {
            return;
        }
        closeSideRailWebSocket();

        sideRailWsPostId = postId;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/post/${postId}/comments/`;

        try {
            const ws = new WebSocket(wsUrl);
            sideRailWebSocket = ws;

            ws.onopen = function() {
                console.log(`[DesktopSideRail] Live comments WebSocket connected for post ${postId}`);
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    handleSideRailWsMessage(data, postId);
                } catch (err) {
                    console.warn('[DesktopSideRail] WS message error:', err);
                }
            };

            ws.onerror = function(err) {
                console.warn('[DesktopSideRail] WS error for post', postId, err);
            };

            ws.onclose = function() {
                if (sideRailWsPostId === postId) {
                    sideRailWebSocket = null;
                }
            };
        } catch (e) {
            console.warn('[DesktopSideRail] Could not initialize WebSocket:', e);
        }
    }

    function handleSideRailWsMessage(data, postId) {
        if (!data) return;

        // 1. Comment Like Update
        if (data.type === 'comment_like_update' && data.comment_id) {
            const commentEl = document.getElementById(`comment-${data.comment_id}`);
            if (commentEl) {
                const likeBtn = commentEl.querySelector('[data-action="like"]');
                if (likeBtn) {
                    const countSpan = likeBtn.querySelector('span');
                    if (countSpan) countSpan.textContent = data.likes_count;
                }
            }
            return;
        }

        // 2. New Comment Live Push
        if (data.type === 'new_comment' && data.comment) {
            const comment = data.comment;
            if (document.getElementById(`comment-${comment.id}`)) {
                return; // Already rendered
            }

            const commentsList = document.getElementById('fsRailCommentsList');
            if (!commentsList) return;

            // Remove empty state if present
            const emptyState = commentsList.querySelector('.comments-empty');
            if (emptyState) emptyState.remove();

            if (comment.parent_comment_id) {
                // Threaded reply
                if (typeof CommentManager !== 'undefined' && typeof CommentManager.addReplyToDom === 'function') {
                    CommentManager.addReplyToDom(comment.parent_comment_id, comment);
                    if (typeof CommentManager.updateReplyCount === 'function') {
                        CommentManager.updateReplyCount(comment.parent_comment_id, 1);
                    }
                } else {
                    let repliesContainer = document.getElementById(`replies-${comment.parent_comment_id}`) ||
                                           commentsList.querySelector(`#replies-${comment.parent_comment_id}`);
                    if (!repliesContainer) {
                        const parentEl = document.getElementById(`comment-${comment.parent_comment_id}`);
                        if (parentEl) {
                            repliesContainer = document.createElement('div');
                            repliesContainer.id = `replies-${comment.parent_comment_id}`;
                            repliesContainer.className = 'comment-replies expanded ms-4 mt-2 ps-2 border-start';
                            parentEl.appendChild(repliesContainer);
                        }
                    }
                    if (repliesContainer) {
                        const replyHtml = renderSideRailCommentHtml(comment, true);
                        repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                    }
                }
            } else {
                // Top-level comment
                let stream = commentsList.querySelector('.comment-stream') || commentsList;
                const commentHtml = (typeof CommentRenderer !== 'undefined' && typeof CommentRenderer.renderComment === 'function')
                    ? CommentRenderer.renderComment(comment, { isReply: false, nestingLevel: 0 })
                    : renderSideRailCommentHtml(comment, false);

                stream.insertAdjacentHTML('afterbegin', commentHtml);
            }

            if (window.htmx) {
                window.htmx.process(commentsList);
            }
            initSheetCommentsInteractions(commentsList, postId);

            // Increment all comment counters
            const railCommentCount = document.getElementById('fsRailCommentCount');
            const fsCommentCount = document.getElementById('fsDesktopCommentCount');
            let curN = parseInt(railCommentCount?.textContent || '0', 10) || 0;
            let newN = curN + 1;
            if (railCommentCount) railCommentCount.textContent = newN;
            if (fsCommentCount) fsCommentCount.textContent = newN;

            const inlinePostCount = document.getElementById(`comment-count-${postId}`);
            const inlineReelCount = document.getElementById(`reel-comment-count-${postId}`);
            const fsReelCount = document.getElementById(`fs-reel-comment-count-${postId}`);
            if (inlinePostCount) inlinePostCount.textContent = newN;
            if (inlineReelCount) inlineReelCount.textContent = newN;
            if (fsReelCount) fsReelCount.textContent = newN;
        }
    }

    function renderSideRailCommentHtml(comment, isReply) {
        const authorName = comment.author?.full_name || comment.author?.username || 'User';
        const authorUsername = comment.author?.username || 'user';
        const avatar = comment.author?.profile_pic || '/static/images/default_avatar.png';
        const content = (comment.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        const timeAgo = 'just now';
        return `
            <div class="comment-item ${isReply ? 'comment-reply ms-4' : ''}" id="comment-${comment.id}"
                 data-comment-id="${comment.id}"
                 data-author-id="${comment.author?.id || ''}"
                 data-parent-comment-id="${comment.parent_comment_id || ''}"
                 data-reply-count="${comment.reply_count || 0}">
                <a href="/users/user/${authorUsername}/"
                   hx-get="/users/user/${authorUsername}/"
                   hx-target="#page-content-target"
                   hx-swap="innerHTML"
                   hx-push-url="true"
                   class="comment-avatar-link">
                    <img src="${avatar}" alt="${authorName}" class="comment-avatar" loading="lazy" onerror="this.src='/static/images/default_avatar.png'">
                </a>
                <div class="comment-content">
                    <div class="comment-header">
                        <a href="/users/user/${authorUsername}/"
                           hx-get="/users/user/${authorUsername}/"
                           hx-target="#page-content-target"
                           hx-swap="innerHTML"
                           hx-push-url="true"
                           class="comment-author-link fw-bold text-decoration-none">
                            ${authorName}
                        </a>
                        <span class="comment-timestamp">${timeAgo}</span>
                    </div>
                    <div class="comment-body" id="comment-body-${comment.id}">
                        ${content}
                    </div>
                    <div class="comment-actions">
                        <button class="comment-action" data-action="like" data-comment-id="${comment.id}" aria-label="Like comment">
                            <i class="bi bi-heart"></i>
                            <span>${comment.likes_count || 0}</span>
                        </button>
                        <button class="comment-action" data-action="reply" data-comment-id="${comment.id}" aria-label="Reply to comment">
                            <i class="bi bi-chat-dots"></i>
                            Reply
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    function toggleDesktopCommentRail(forceOpen) {
        const rail = document.getElementById('reelDesktopSideRail');
        if (!rail) return;

        const isCurrentlyCollapsed = rail.classList.contains('rail-collapsed');
        const shouldOpen = (typeof forceOpen === 'boolean') ? forceOpen : isCurrentlyCollapsed;

        if (shouldOpen) {
            rail.classList.remove('rail-collapsed');
            const input = document.getElementById('fsRailCommentInput');
            if (input) {
                setTimeout(() => input.focus(), 120);
            }
        } else {
            rail.classList.add('rail-collapsed');
        }

        // Smoothly adjust exterior action buttons positioning
        const repositionActive = () => {
            const viewport = document.getElementById('reelsSnapViewport');
            if (viewport) {
                const h = viewport.clientHeight || 1;
                const curIdx = Math.round(viewport.scrollTop / h);
                const activeSnap = viewport.children[curIdx] || viewport.firstElementChild;
                if (activeSnap) {
                    repositionDesktopActionsRail(activeSnap.querySelector('.reel-fullscreen-content'));
                }
            }
        };

        setTimeout(repositionActive, 100);
        setTimeout(repositionActive, 320);
    }

    function refreshDesktopSideRailComments() {
        const postId = currentDesktopRailPostId;
        if (!postId) return;

        const refreshBtn = document.getElementById('fsRailRefreshBtn');
        const icon = refreshBtn?.querySelector('i');
        if (icon) icon.classList.add('spinning');
        if (refreshBtn) refreshBtn.disabled = true;

        const commentsList = document.getElementById('fsRailCommentsList');
        const commentsLoading = document.getElementById('fsRailCommentsLoading');

        fetch(`/post/${postId}/?show_all=1`, {
            headers: { 'HX-Request': 'true' }
        })
        .then(res => res.text())
        .then(html => {
            if (icon) icon.classList.remove('spinning');
            if (refreshBtn) refreshBtn.disabled = false;
            if (commentsLoading) commentsLoading.style.display = 'none';

            if (commentsList) {
                delete commentsList.dataset.eventsBound;
                commentsList.innerHTML = html;
                if (window.htmx) {
                    htmx.process(commentsList);
                }
                initSheetCommentsInteractions(commentsList, postId);

                const countFromDom = commentsList.querySelectorAll('.comment-item:not(.comment-reply)').length;
                if (countFromDom > 0) {
                    const railCommentCount = document.getElementById('fsRailCommentCount');
                    const fsCommentCount = document.getElementById('fsDesktopCommentCount');
                    if (railCommentCount && parseInt(railCommentCount.textContent, 10) < countFromDom) {
                        railCommentCount.textContent = countFromDom;
                    }
                    if (fsCommentCount && parseInt(fsCommentCount.textContent, 10) < countFromDom) {
                        fsCommentCount.textContent = countFromDom;
                    }
                }
            }
        })
        .catch(err => {
            console.warn('[DesktopSideRail] Refresh comments error:', err);
            if (icon) icon.classList.remove('spinning');
            if (refreshBtn) refreshBtn.disabled = false;
        });
    }

    function repositionDesktopActionsRail(content) {
        if (window.innerWidth < 992) return;
        const rail = document.getElementById('reelDesktopActionsRail');
        const stage = document.querySelector('.reel-desktop-stage');
        if (!rail || !stage) return;

        const activeContent = content || document.querySelector('.reels-snap-item .reel-fullscreen-content');
        if (!activeContent) return;

        const contentRect = activeContent.getBoundingClientRect();
        const stageRect = stage.getBoundingClientRect();
        if (stageRect.width === 0) return;

        // Position rail 20px to the right of the active card
        const desiredLeft = contentRect.right - stageRect.left + 20;

        // Ensure it doesn't overlap the up/down nav group (docked at right: 28px)
        const maxLeft = stageRect.width - 85;
        const finalLeft = Math.max(16, Math.min(desiredLeft, maxLeft));

        rail.style.left = `${Math.round(finalLeft)}px`;
    }

    function adaptSnapItemOrientation(snapItem, initialCard) {
        if (!snapItem) return;
        const content = snapItem.querySelector('.reel-fullscreen-content');
        const video = snapItem.querySelector('video');
        if (!content || !video) return;

        // On mobile (<992px): ALWAYS full-bleed edge-to-edge 100% width and 100% height
        if (window.innerWidth < 992) {
            content.style.width = '';
            content.style.height = '';
            content.style.maxWidth = '';
            content.style.maxHeight = '';
            content.style.aspectRatio = '';
            content.classList.remove('is-portrait', 'is-landscape', 'is-square');
            return;
        }

        const isInitialLandscape = initialCard && (
            initialCard.classList.contains('landscape-video-container') ||
            initialCard.querySelector('.landscape-video-container') ||
            initialCard.querySelector('.landscape-video-wrapper')
        );

        if (isInitialLandscape) {
            content.classList.remove('is-portrait', 'is-square');
            content.classList.add('is-landscape');
        }

        function checkMetadata() {
            if (window.innerWidth < 992) {
                content.style.width = '';
                content.style.height = '';
                content.style.maxWidth = '';
                content.style.maxHeight = '';
                content.style.aspectRatio = '';
                content.classList.remove('is-portrait', 'is-landscape', 'is-square');
                return;
            }

            const vw = video.videoWidth;
            const vh = video.videoHeight;
            if (!vw || !vh) return;

            const ratio = vw / vh;
            content.classList.remove('is-portrait', 'is-landscape', 'is-square');
            if (ratio >= 1.15) {
                content.classList.add('is-landscape');
                content.style.aspectRatio = `${vw} / ${vh}`;
                content.style.width = 'min(calc(100% - 150px), 920px)';
                content.style.height = 'auto';
            } else if (ratio >= 0.88 && ratio < 1.15) {
                content.classList.add('is-square');
                content.style.aspectRatio = '1 / 1';
                const sz = 'min(calc(100vh - 40px), calc(100% - 150px), 720px)';
                content.style.width = sz;
                content.style.height = sz;
            } else {
                content.classList.add('is-portrait');
                content.style.aspectRatio = `${vw} / ${vh}`;
                content.style.height = 'min(calc(100vh - 40px), 940px)';
                content.style.width = `calc(min(calc(100vh - 40px), 940px) * ${vw} / ${vh})`;
                content.style.maxWidth = 'min(calc(100% - 150px), 940px)';
            }

            repositionDesktopActionsRail(content);
        }

        if (video.videoWidth && video.videoHeight) {
            checkMetadata();
        } else {
            video.addEventListener('loadedmetadata', checkMetadata, { once: true });
        }
    }

    function updateFullscreenNavButtons(target) {
        const viewport = document.getElementById('reelsSnapViewport');
        const navPrev = document.getElementById('reelsNavPrev');
        const navNext = document.getElementById('reelsNavNext');
        if (!viewport || !navPrev || !navNext) return;

        const items = Array.from(viewport.children);
        const total = items.length;
        if (total <= 1) {
            navPrev.classList.add('d-none');
            navNext.classList.add('d-none');
            return;
        }

        let currentIndex = 0;
        if (typeof target === 'number') {
            currentIndex = target;
        } else if (target && target instanceof Element) {
            const idx = items.indexOf(target);
            if (idx !== -1) {
                currentIndex = idx;
            } else {
                const h = viewport.clientHeight || 1;
                currentIndex = Math.round(viewport.scrollTop / h);
            }
        } else {
            const h = viewport.clientHeight || 1;
            currentIndex = Math.round(viewport.scrollTop / h);
        }

        currentIndex = Math.max(0, Math.min(total - 1, currentIndex));

        // If it's the first reel, hide the up button
        if (currentIndex <= 0) {
            navPrev.classList.add('d-none');
        } else {
            navPrev.classList.remove('d-none');
        }

        // If it's the last reel, hide the down button
        if (currentIndex >= total - 1) {
            navNext.classList.add('d-none');
        } else {
            navNext.classList.remove('d-none');
        }
    }

    function updateDesktopSideRail(activeItem) {
        if (activeItem) {
            updateFullscreenNavButtons(activeItem);
            repositionDesktopActionsRail(activeItem.querySelector('.reel-fullscreen-content'));
        }
        if (!activeItem || window.innerWidth < 992) return;

        const rawPostId = activeItem.dataset.postId || extractPostId(activeItem);
        const postId = rawPostId ? String(rawPostId).trim() : '';
        if (!postId || postId === 'null' || postId === 'undefined') return;

        const authorName = activeItem.dataset.authorName || 'Author';
        const authorUsername = activeItem.dataset.authorUsername || 'author';
        const authorAvatar = activeItem.dataset.authorAvatar || '/static/images/default_avatar.png';
        const profileUrl = activeItem.dataset.profileUrl || `/users/user/${authorUsername}/`;
        const unitCode = activeItem.dataset.unitCode || '';
        const timeAgo = activeItem.dataset.timeAgo || '';
        const likeCount = activeItem.dataset.likes || '0';
        const isLiked = activeItem.dataset.isLiked === 'true' || activeItem.querySelector('.fs-like-proxy-btn')?.classList.contains('liked');
        const commentCount = activeItem.dataset.comments ||
                             activeItem.querySelector('.reel-action-unit [id^="fs-reel-comment-count-"]')?.textContent?.trim() ||
                             '0';

        // 1. Update Exterior Engagement Stack (Desktop/Tablet Floating Rail)
        const fsLikeBtn = document.getElementById('fsDesktopLikeBtn');
        const fsLikeCount = document.getElementById('fsDesktopLikeCount');
        if (fsLikeBtn) {
            fsLikeBtn.dataset.postId = postId;
            fsLikeBtn.setAttribute('data-post-id', postId);
            fsLikeBtn.classList.toggle('liked', isLiked);
            const icon = fsLikeBtn.querySelector('i');
            if (icon) icon.className = isLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
        }
        if (fsLikeCount) {
            fsLikeCount.textContent = likeCount;
        }

        const fsCommentBtn = document.getElementById('fsDesktopCommentBtn');
        const fsCommentCount = document.getElementById('fsDesktopCommentCount');
        if (fsCommentBtn) {
            fsCommentBtn.dataset.postId = postId;
            fsCommentBtn.onclick = function(e) {
                if (e) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                toggleDesktopCommentRail();
            };
        }
        if (fsCommentCount) {
            fsCommentCount.textContent = commentCount;
        }

        const fsShareBtn = document.getElementById('fsDesktopShareBtn');
        if (fsShareBtn) {
            fsShareBtn.dataset.postId = postId;
            fsShareBtn.setAttribute('data-post-id', postId);
            fsShareBtn.setAttribute('data-post-url', `/post/${postId}/`);
            fsShareBtn.setAttribute('data-video-url', activeItem.dataset.videoUrl || '');
            fsShareBtn.setAttribute('data-poster-url', activeItem.dataset.poster || '');
            fsShareBtn.setAttribute('data-post-content', activeItem.dataset.caption || '');
        }

        const fsBookmarkBtn = document.getElementById('fsDesktopBookmarkBtn');
        const fsBookmarkLabel = document.getElementById('fsDesktopBookmarkLabel');
        if (fsBookmarkBtn) {
            fsBookmarkBtn.dataset.postId = postId;
            const isSaved = window.pwaniSavedPosts ? window.pwaniSavedPosts.isPostSaved(postId) : fsBookmarkBtn.classList.contains('active');
            fsBookmarkBtn.classList.toggle('active', isSaved);
            const icon = fsBookmarkBtn.querySelector('i');
            if (icon) icon.className = isSaved ? 'bi bi-bookmark-fill text-warning' : 'bi bi-bookmark';
            if (fsBookmarkLabel) fsBookmarkLabel.textContent = isSaved ? 'Saved' : 'Save';
            fsBookmarkBtn.onclick = function() {
                const nowSaved = window.pwaniSavedPosts ? window.pwaniSavedPosts.togglePostSaved(postId) : fsBookmarkBtn.classList.toggle('active');
                fsBookmarkBtn.classList.toggle('active', nowSaved);
                if (icon) icon.className = nowSaved ? 'bi bi-bookmark-fill text-warning' : 'bi bi-bookmark';
                if (fsBookmarkLabel) fsBookmarkLabel.textContent = nowSaved ? 'Saved' : 'Save';
            };
        }

        // 2. Update Right Side Rail Header
        const avatarEl = document.getElementById('fsRailAuthorAvatar');
        const nameLink = document.getElementById('fsRailAuthorNameLink');
        const profileLink = document.getElementById('fsRailAuthorProfileLink');
        const nameEl = document.getElementById('fsRailAuthorName');
        const handleEl = document.getElementById('fsRailAuthorHandle');
        const unitEl = document.getElementById('fsRailUnitBadge');
        const timeEl = document.getElementById('fsRailTime');
        const captionEl = document.getElementById('fsRailCaption');
        const soundTextEl = document.getElementById('fsRailSoundText');
        const optionsBtn = document.getElementById('fsRailOptionsBtn');
        const closeBtn = document.getElementById('fsRailCloseBtn');
        const refreshBtn = document.getElementById('fsRailRefreshBtn');

        if (avatarEl) avatarEl.src = authorAvatar;
        if (nameLink) {
            nameLink.href = profileUrl;
            nameLink.setAttribute('hx-get', profileUrl);
            nameLink.setAttribute('hx-target', '#page-content-target');
            nameLink.setAttribute('hx-swap', 'innerHTML');
            nameLink.setAttribute('hx-push-url', 'true');
        }
        if (profileLink) {
            profileLink.href = profileUrl;
            profileLink.setAttribute('hx-get', profileUrl);
            profileLink.setAttribute('hx-target', '#page-content-target');
            profileLink.setAttribute('hx-swap', 'innerHTML');
            profileLink.setAttribute('hx-push-url', 'true');
        }
        if (nameEl) nameEl.textContent = authorName;
        if (handleEl) handleEl.textContent = `@${authorUsername}`;
        if (timeEl) timeEl.textContent = timeAgo || 'recently';
        if (unitEl) {
            unitEl.innerHTML = unitCode ?
                `<span class="badge bg-primary bg-opacity-10 text-primary border-0 ms-1 px-1.5 py-0.5" style="font-size: 10px;">${unitCode}</span>` : '';
        }

        // Wire Rail Header Close Button
        if (closeBtn && !closeBtn.dataset.bound) {
            closeBtn.dataset.bound = 'true';
            closeBtn.onclick = function(e) {
                if (e) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                toggleDesktopCommentRail(false);
            };
        }

        // Wire Rail Comments Refresh Button
        if (refreshBtn && !refreshBtn.dataset.bound) {
            refreshBtn.dataset.bound = 'true';
            refreshBtn.onclick = function(e) {
                if (e) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                refreshDesktopSideRailComments();
            };
        }

        // Caption
        if (captionEl) {
            const rawCaptionHtml = activeItem.querySelector('.reel-caption-text')?.innerHTML ||
                                   activeItem.querySelector('.post-content-text')?.innerHTML ||
                                   activeItem.dataset.caption ||
                                   '';
            const plainText = (activeItem.dataset.caption || activeItem.querySelector('.reel-caption-text')?.textContent || '').trim();

            if (plainText.length > 110 || (plainText.match(/\n/g) || []).length >= 2) {
                captionEl.innerHTML = `
                    <div class="reel-rail-caption-clamp" id="fsRailCaptionInner">${rawCaptionHtml}</div>
                    <button type="button" class="btn btn-link btn-sm p-0 text-muted text-decoration-none mt-1 fw-semibold fs-rail-caption-toggle" style="font-size: 12px;">
                        ... See more
                    </button>
                `;
                const toggleBtn = captionEl.querySelector('.fs-rail-caption-toggle');
                const clampEl = captionEl.querySelector('#fsRailCaptionInner');
                if (toggleBtn && clampEl) {
                    toggleBtn.onclick = function() {
                        const isExp = clampEl.classList.toggle('is-expanded');
                        toggleBtn.textContent = isExp ? 'See less' : '... See more';
                    };
                }
            } else {
                captionEl.innerHTML = rawCaptionHtml;
            }
        }

        if (soundTextEl) {
            soundTextEl.textContent = `Original Audio - ${authorUsername}`;
        }

        if (optionsBtn) {
            optionsBtn.dataset.postId = postId;
            optionsBtn.dataset.author = authorName;
            optionsBtn.onclick = function() {
                openReelQuickTools(postId, optionsBtn);
            };
        }

        // Process HTMX on side rail header links
        const railHeader = document.querySelector('.reel-rail-header');
        if (railHeader && window.htmx) {
            htmx.process(railHeader);
        }

        // 3. Update Comments Stream in Side Rail
        const railCommentCount = document.getElementById('fsRailCommentCount');
        if (railCommentCount) railCommentCount.textContent = commentCount;

        if (currentDesktopRailPostId === postId) {
            initSideRailWebSocket(postId);
            return;
        }
        currentDesktopRailPostId = postId;
        initSideRailWebSocket(postId);

        const commentsList = document.getElementById('fsRailCommentsList');
        const commentsLoading = document.getElementById('fsRailCommentsLoading');
        const parentInput = document.getElementById('fsRailParentId');
        const replyBanner = document.getElementById('fsRailReplyBanner');
        const commentInput = document.getElementById('fsRailCommentInput');

        if (parentInput) parentInput.value = '';
        if (replyBanner) replyBanner.classList.add('d-none');
        if (commentInput) {
            commentInput.value = '';
            commentInput.placeholder = 'Add a comment...';
        }

        if (commentsLoading) commentsLoading.style.display = 'block';
        if (commentsList) {
            commentsList.innerHTML = '';
            delete commentsList.dataset.eventsBound;
        }

        fetch(`/post/${postId}/?show_all=1`, {
            headers: { 'HX-Request': 'true' }
        })
        .then(res => res.text())
        .then(html => {
            if (commentsLoading) commentsLoading.style.display = 'none';
            if (commentsList) {
                commentsList.innerHTML = html;
                if (window.htmx) {
                    htmx.process(commentsList);
                }
                initSheetCommentsInteractions(commentsList, postId);
                initSideRailWebSocket(postId);
            }
        })
        .catch(err => {
            console.warn('[DesktopSideRail] Failed to load comments:', err);
            if (commentsLoading) commentsLoading.style.display = 'none';
            if (commentsList) commentsList.innerHTML = '<div class="text-center py-4 text-muted small">Could not load comments.</div>';
        });

        // Bind desktop side rail comment form submission
        const formEl = document.getElementById('fsRailCommentForm');
        if (formEl && !formEl.dataset.bound) {
            formEl.dataset.bound = 'true';
            formEl.onsubmit = function(e) {
                e.preventDefault();
                if (formEl.dataset.submitting === 'true') return;

                const curPostId = currentDesktopRailPostId;
                if (!curPostId) return;

                const content = commentInput?.value?.trim();
                if (!content) return;

                formEl.dataset.submitting = 'true';
                const sendBtn = formEl.querySelector('button[type="submit"]');
                if (sendBtn) sendBtn.disabled = true;

                const targetParentId = (parentInput && parentInput.value) ? parentInput.value : '';

                const formData = new FormData();
                formData.append('content', content);
                formData.append('csrfmiddlewaretoken', getCsrfToken());
                if (targetParentId) {
                    formData.append('parent_id', targetParentId);
                }

                fetch(`/post/${curPostId}/comment/`, {
                    method: 'POST',
                    body: formData,
                    headers: { 'HX-Request': 'true' }
                })
                .then(res => res.text())
                .then(html => {
                    delete formEl.dataset.submitting;
                    if (sendBtn) sendBtn.disabled = false;
                    if (commentInput) commentInput.value = '';
                    if (parentInput) parentInput.value = '';
                    if (replyBanner) replyBanner.classList.add('d-none');

                    if (commentsList) {
                        delete commentsList.dataset.eventsBound;
                        commentsList.innerHTML = html;
                        if (window.htmx) {
                            htmx.process(commentsList);
                        }
                        initSheetCommentsInteractions(commentsList, curPostId);
                    }

                    // Update all comment counters
                    let curN = parseInt(railCommentCount?.textContent || '0', 10) || 0;
                    let newN = curN + 1;
                    if (railCommentCount) railCommentCount.textContent = newN;
                    if (fsCommentCount) fsCommentCount.textContent = newN;

                    const inlinePostCount = document.getElementById(`comment-count-${curPostId}`);
                    const inlineReelCount = document.getElementById(`reel-comment-count-${curPostId}`);
                    const fsReelCount = document.getElementById(`fs-reel-comment-count-${curPostId}`);
                    if (inlinePostCount) inlinePostCount.textContent = newN;
                    if (inlineReelCount) inlineReelCount.textContent = newN;
                    if (fsReelCount) fsReelCount.textContent = newN;

                    // Scroll to bottom
                    const scrollContainer = document.getElementById('fsRailCommentsBody');
                    if (scrollContainer) {
                        scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
                    }
                })
                .catch(err => {
                    delete formEl.dataset.submitting;
                    if (sendBtn) sendBtn.disabled = false;
                    console.error('[DesktopSideRail] Comment post error:', err);
                });
            };
        }

        // Cancel reply in side rail
        const cancelReplyBtn = document.getElementById('fsRailCancelReply');
        if (cancelReplyBtn && !cancelReplyBtn.dataset.bound) {
            cancelReplyBtn.dataset.bound = 'true';
            cancelReplyBtn.onclick = function() {
                if (parentInput) parentInput.value = '';
                if (replyBanner) replyBanner.classList.add('d-none');
                if (commentInput && /^@\w+\s*$/.test(commentInput.value)) {
                    commentInput.value = '';
                    commentInput.placeholder = 'Add a comment...';
                }
            };
        }
    }

    function openFullscreenReels(targetPostId) {
        const overlay = document.getElementById('fullscreenReelsOverlay');
        const viewport = document.getElementById('reelsSnapViewport');
        if (!overlay || !viewport) return;

        targetPostId = targetPostId ? String(targetPostId).trim() : null;
        if (targetPostId === 'null' || targetPostId === 'undefined' || targetPostId === '') {
            targetPostId = null;
        }

        // Pause feed playback and save scroll offset
        state.previousScrollY = window.scrollY;
        pauseAllVideos();

        state.isFullScreenActive = true;
        document.body.classList.add('reels-active');
        overlay.classList.remove('d-none');
        overlay.setAttribute('aria-hidden', 'false');

        // Clear previous snap tracks
        viewport.innerHTML = '';

        // Query all video cards on the page: vertical reels, carousel cards, and landscape video postcards
        const allVideoCards = [];
        const seenPostIds = new Set();

        const cardSelectors = [
            '.reel-card-container',
            '.reel-post-card',
            '.reels-carousel-card',
            '.post-card',
            '.landscape-video-container'
        ];

        document.querySelectorAll(cardSelectors.join(', ')).forEach(card => {
            const vid = card.querySelector('video') || (card.tagName === 'VIDEO' ? card : null);
            if (!vid || card.classList.contains('reels-carousel-shelf')) return;

            const cardPostId = String(extractPostId(card) || vid.dataset.postId || card.dataset.postId || '').trim();
            if (!cardPostId || cardPostId === 'null' || cardPostId === 'undefined' || seenPostIds.has(cardPostId)) return;

            seenPostIds.add(cardPostId);
            allVideoCards.push(card);
        });

        if (allVideoCards.length === 0) {
            console.warn('[VideoManager] No video cards found to populate fullscreen viewer');
            return;
        }

        createFullscreenObserver();

        let targetSnapItem = null;
        allVideoCards.forEach(card => {
            const snapItem = buildSnapItemFromReelCard(card);
            if (snapItem) {
                viewport.appendChild(snapItem);
                state.fullscreenObserver.observe(snapItem);

                const video = snapItem.querySelector('video');
                if (video) {
                    video.muted = isGlobalMuted;
                    // Trigger immediate media load
                    if (!video.currentSrc && video.getAttribute('src')) {
                        video.load();
                    }
                }

                if (targetPostId && String(snapItem.dataset.postId).trim() === targetPostId) {
                    targetSnapItem = snapItem;
                }
            }
        });

        // Initialize nav button visibility immediately
        updateFullscreenNavButtons(targetSnapItem || viewport.firstElementChild);

        // Request animation frame ensures DOM reflow is complete before scrolling/playing
        requestAnimationFrame(() => {
            const activeItem = targetSnapItem || viewport.firstElementChild;
            if (activeItem) {
                const items = Array.from(viewport.children);
                const targetIndex = items.indexOf(activeItem);
                if (targetIndex > 0) {
                    viewport.scrollTop = targetIndex * viewport.clientHeight;
                } else {
                    viewport.scrollTop = 0;
                }

                const activeVideo = activeItem.querySelector('video');
                if (activeVideo) {
                    playVideo(activeVideo, true);
                    const vinyl = activeItem.querySelector('.reel-vinyl-disc');
                    if (vinyl) vinyl.classList.add('is-playing');
                }
                updateDesktopSideRail(activeItem);
                updateFullscreenNavButtons(activeItem);
            } else {
                updateFullscreenNavButtons();
            }
        });

        console.log('[VideoManager] Fullscreen reels overlay opened at post:', targetPostId);
    }

    function closeFullscreenReels() {
        const overlay = document.getElementById('fullscreenReelsOverlay');
        const viewport = document.getElementById('reelsSnapViewport');
        if (!overlay) return;

        closeSideRailWebSocket();
        currentDesktopRailPostId = null;

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
    // REEL QUICK TOOLS & COMMENT HELPERS
    // ============================================================================

    function getCsrfToken() {
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : (document.querySelector('[name=csrfmiddlewaretoken]')?.value || '');
    }

    function openReelQuickTools(postId, targetEl) {
        postId = postId ? String(postId).trim() : '';
        if (!postId || postId === 'null' || postId === 'undefined') return;

        const modalEl = document.getElementById('reelQuickToolsModal');
        if (!modalEl || typeof bootstrap === 'undefined') return;

        const card = targetEl ? targetEl.closest('.reel-card-container, .reel-post-card, .reels-snap-item') : document.getElementById(`reel-card-${postId}`);
        if (!card) return;

        const optionsBtn = card.querySelector('.reel-options-btn');
        const authorUsername = card.dataset.authorUsername ||
                               optionsBtn?.dataset.authorUsername ||
                               card.querySelector('.fb-author-username')?.textContent?.replace(/^@/, '')?.trim() ||
                               (optionsBtn?.dataset.author || '').replace(/^@/, '') ||
                               'Author';
        const isAuthor = optionsBtn?.dataset.isAuthor === 'true';
        const shareUrl = optionsBtn?.dataset.shareUrl || (window.location.origin + `/post/${postId}/`);
        const videoUrl = optionsBtn?.dataset.videoUrl || '';
        const posterUrl = optionsBtn?.dataset.poster || '';
        const caption = card.dataset.caption || card.querySelector('.reel-caption-text')?.textContent?.trim() || '';

        // Update Modal Header
        const authorEl = document.getElementById('quickToolsAuthor');
        if (authorEl) authorEl.textContent = `@${authorUsername}`;

        // 1. Bookmark / Save Button
        const bookmarkBtn = document.getElementById('quickToolsBookmarkBtn');
        if (bookmarkBtn) {
            const isBookmarked = window.pwaniSavedPosts ? window.pwaniSavedPosts.isPostSaved(postId) : bookmarkBtn.classList.contains('active');
            bookmarkBtn.classList.toggle('active', isBookmarked);
            const icon = bookmarkBtn.querySelector('i');
            const label = bookmarkBtn.querySelector('.fw-semibold');
            if (icon) icon.className = isBookmarked ? 'bi bi-bookmark-fill text-warning' : 'bi bi-bookmark';
            if (label) label.textContent = isBookmarked ? 'Saved to Library' : 'Save to Library';

            bookmarkBtn.onclick = function() {
                const nowSaved = window.pwaniSavedPosts ? window.pwaniSavedPosts.togglePostSaved(postId) : bookmarkBtn.classList.toggle('active');
                bookmarkBtn.classList.toggle('active', nowSaved);
                if (icon) icon.className = nowSaved ? 'bi bi-bookmark-fill text-warning' : 'bi bi-bookmark';
                if (label) label.textContent = nowSaved ? 'Saved to Library' : 'Save to Library';
                bootstrap.Modal.getInstance(modalEl)?.hide();
            };
        }

        // 2. Repost Button
        const repostBtn = document.getElementById('quickToolsRepostBtn');
        if (repostBtn) {
            repostBtn.onclick = function() {
                bootstrap.Modal.getInstance(modalEl)?.hide();
                const repostModalEl = document.getElementById('globalRepostModal');
                if (repostModalEl) {
                    const hiddenInput = repostModalEl.querySelector('input[name="post_id"]');
                    if (hiddenInput) hiddenInput.value = postId;
                    const form = document.getElementById('globalRepostForm');
                    if (form) form.setAttribute('hx-post', `/api/posts/${postId}/repost/`);
                    new bootstrap.Modal(repostModalEl).show();
                }
            };
        }

        // 3. Share Button
        const shareBtn = document.getElementById('quickToolsShareBtn');
        if (shareBtn) {
            shareBtn.onclick = function() {
                bootstrap.Modal.getInstance(modalEl)?.hide();
                const shareModalEl = document.getElementById('globalShareModal');
                if (shareModalEl) {
                    shareModalEl.setAttribute('data-post-id', postId);
                    shareModalEl.setAttribute('data-post-url', `/post/${postId}/`);
                    shareModalEl.setAttribute('data-video-url', videoUrl || '');
                    shareModalEl.setAttribute('data-poster-url', posterUrl || '');
                    shareModalEl.setAttribute('data-post-content', caption || '');
                    const hiddenPostId = document.getElementById('globalSharePostId');
                    if (hiddenPostId) hiddenPostId.value = postId;
                    const inst = bootstrap.Modal.getInstance(shareModalEl) || new bootstrap.Modal(shareModalEl);
                    inst.show();
                    if (window.pwaniPrepareShareModal) {
                        window.pwaniPrepareShareModal(postId, shareModalEl);
                    }
                }
            };
        }

        // 4. Copy Link Button
        const copyBtn = document.getElementById('quickToolsCopyLinkBtn');
        if (copyBtn) {
            copyBtn.onclick = function() {
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(shareUrl).then(() => {
                        const label = copyBtn.querySelector('.fw-semibold');
                        if (label) label.textContent = 'Link Copied!';
                        setTimeout(() => {
                            if (label) label.textContent = 'Copy Link';
                            bootstrap.Modal.getInstance(modalEl)?.hide();
                        }, 800);
                    });
                }
            };
        }

        // 5. Download for Offline Button
        const downloadBtn = document.getElementById('quickToolsDownloadBtn');
        if (downloadBtn) {
            downloadBtn.onclick = function() {
                bootstrap.Modal.getInstance(modalEl)?.hide();
                if (window.downloadManager && videoUrl) {
                    window.downloadManager.startDownload({
                        id: postId,
                        url: videoUrl,
                        title: `Reel by ${authorName}`,
                        mediaType: 'video',
                        thumbnail: posterUrl
                    });
                } else if (videoUrl) {
                    const a = document.createElement('a');
                    a.href = videoUrl;
                    a.download = `reel_${postId}.mp4`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            };
        }

        // 6. Hide Button
        const hideBtn = document.getElementById('quickToolsHideBtn');
        if (hideBtn) {
            hideBtn.onclick = function() {
                bootstrap.Modal.getInstance(modalEl)?.hide();
                if (card) {
                    card.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'scale(0.95)';
                    setTimeout(() => card.remove(), 250);
                }
            };
        }

        // 7. Report Button
        const reportBtn = document.getElementById('quickToolsReportBtn');
        if (reportBtn) {
            reportBtn.onclick = function() {
                bootstrap.Modal.getInstance(modalEl)?.hide();
                const reportModalEl = document.getElementById('globalReportModal');
                if (reportModalEl) {
                    const hiddenInput = reportModalEl.querySelector('input[name="post"]');
                    if (hiddenInput) hiddenInput.value = postId;
                    new bootstrap.Modal(reportModalEl).show();
                }
            };
        }

        // 8. Delete Button (Author only)
        const deleteBtn = document.getElementById('quickToolsDeleteBtn');
        if (deleteBtn) {
            if (isAuthor) {
                deleteBtn.classList.remove('d-none');
                deleteBtn.onclick = function() {
                    if (confirm('Are you sure you want to delete this reel?')) {
                        bootstrap.Modal.getInstance(modalEl)?.hide();
                        fetch(`/api/posts/${postId}/`, {
                            method: 'DELETE',
                            headers: {
                                'X-CSRFToken': getCsrfToken()
                            }
                        }).then(() => {
                            card.remove();
                        });
                    }
                };
            } else {
                deleteBtn.classList.add('d-none');
            }
        }

        new bootstrap.Modal(modalEl).show();
    }

    let activeCommentsPostId = null;

    function closeAllSheetCommentMenus() {
        document.querySelectorAll('.comment-menu-dropdown').forEach(m => m.remove());
        document.querySelectorAll('.comment-item.menu-open').forEach(el => el.classList.remove('menu-open'));
        document.querySelectorAll('[data-action="menu"]').forEach(b => b.setAttribute('aria-expanded', 'false'));
    }

    function showCommentsToast(message) {
        let toast = document.getElementById('pwaninetCommentsToast');
        if (!toast) {
            toast = document.createElement('div');
            toast.id = 'pwaninetCommentsToast';
            toast.className = 'position-fixed bottom-0 start-50 translate-middle-x mb-4 px-3 py-2 rounded-pill shadow bg-dark text-white text-center';
            toast.style.zIndex = '10060';
            toast.style.fontSize = '13px';
            toast.style.pointerEvents = 'none';
            toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';
            document.body.appendChild(toast);
        }
        toast.textContent = message;
        toast.style.opacity = '1';
        toast.style.transform = 'translate(-50%, 0)';
        clearTimeout(toast._timeout);
        toast._timeout = setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translate(-50%, 10px)';
        }, 2200);
    }

    if (!window._commentMenuListenersBound) {
        window._commentMenuListenersBound = true;
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.comment-menu-dropdown') && !e.target.closest('[data-action="menu"]')) {
                closeAllSheetCommentMenus();
            }
        });
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                closeAllSheetCommentMenus();
            }
        });
    }

    function truncateLongComments(container) {
        if (!container) return;
        const bodies = container.querySelectorAll('.comment-body');
        bodies.forEach(body => {
            if (body.dataset.clampHandled === 'true') return;
            body.dataset.clampHandled = 'true';

            const text = body.textContent.trim();
            if (text.length > 130 || (text.match(/\n/g) || []).length >= 3) {
                body.classList.add('comment-body-clamped');
                const toggleBtn = document.createElement('button');
                toggleBtn.type = 'button';
                toggleBtn.className = 'btn btn-link btn-sm p-0 text-muted text-decoration-none fw-semibold comment-see-more-btn';
                toggleBtn.style.fontSize = '12px';
                toggleBtn.style.display = 'inline-block';
                toggleBtn.style.marginTop = '2px';
                toggleBtn.textContent = '... See more';
                toggleBtn.onclick = function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    const isExp = body.classList.toggle('is-expanded');
                    body.classList.toggle('comment-body-clamped', !isExp);
                    toggleBtn.textContent = isExp ? 'See less' : '... See more';
                };
                body.after(toggleBtn);
            }
        });
    }

    function initSheetCommentsInteractions(listEl, postId) {
        if (!listEl) return;
        truncateLongComments(listEl);
        if (listEl.dataset.eventsBound === 'true') return;
        listEl.dataset.eventsBound = 'true';

        listEl.addEventListener('click', async function(e) {
            // A. Comment Like
            const likeBtn = e.target.closest('[data-action="like"]');
            if (likeBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = likeBtn.dataset.commentId;
                if (!commentId) return;

                const icon = likeBtn.querySelector('i');
                const countSpan = likeBtn.querySelector('span');
                const wasLiked = likeBtn.classList.contains('liked');
                const curCount = parseInt(countSpan?.textContent || '0', 10);

                // Optimistic UI toggle
                likeBtn.classList.toggle('liked', !wasLiked);
                if (icon) {
                    icon.className = wasLiked ? 'bi bi-heart' : 'bi bi-heart-fill text-danger';
                }
                if (countSpan) {
                    countSpan.textContent = wasLiked ? Math.max(0, curCount - 1) : curCount + 1;
                }

                try {
                    const res = await fetch(`/api/comments/${commentId}/like/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCsrfToken(),
                            'Content-Type': 'application/json'
                        }
                    });
                    if (!res.ok) {
                        await fetch(`/comment/${commentId}/like/`, {
                            method: 'POST',
                            headers: {
                                'X-CSRFToken': getCsrfToken(),
                                'HX-Request': 'true'
                            }
                        });
                    }
                } catch (err) {
                    console.warn('[CommentsSheet] Like toggle error:', err);
                    likeBtn.classList.toggle('liked', wasLiked);
                    if (icon) icon.className = wasLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
                    if (countSpan) countSpan.textContent = curCount;
                }
                return;
            }

            // B. Comment Reply
            const replyBtn = e.target.closest('[data-action="reply"]');
            if (replyBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = replyBtn.dataset.commentId;
                const commentItem = replyBtn.closest('.comment-item');
                // Enforce 1-level maximum nesting: if replying to a reply, anchor to its root parent comment
                const rootParentId = commentItem?.dataset?.parentId || commentItem?.dataset?.parentCommentId || commentId;
                const authorLink = commentItem?.querySelector('.comment-author-link');
                const authorUsername = commentItem?.dataset?.authorUsername ||
                                       authorLink?.dataset?.username ||
                                       (authorLink?.getAttribute('href') || '').match(/\/users\/(?:user\/)?([^\/]+)/)?.[1] ||
                                       authorLink?.textContent?.trim() || '';

                const isRail = (listEl && listEl.id === 'fsRailCommentsList') || (listEl && listEl.closest('#fsRailCommentsBody, .reel-desktop-side-rail')) || Boolean(document.getElementById('fsRailCommentInput')?.offsetParent);

                const parentInput = isRail ? document.getElementById('fsRailParentId') : document.getElementById('commentsModalParentId');
                const replyBanner = isRail ? document.getElementById('fsRailReplyBanner') : document.getElementById('commentsModalReplyBanner');
                const replyUserSpan = isRail ? document.getElementById('fsRailReplyUser') : document.getElementById('commentsModalReplyUser');
                const inputEl = isRail ? document.getElementById('fsRailCommentInput') : document.getElementById('reelCommentInput');

                if (parentInput) parentInput.value = rootParentId;
                if (replyBanner && replyUserSpan) {
                    replyUserSpan.textContent = authorUsername ? `@${authorUsername}` : 'comment';
                    replyBanner.classList.remove('d-none');
                }
                if (inputEl) {
                    if (authorUsername && !inputEl.value.includes(`@${authorUsername}`)) {
                        inputEl.value = `@${authorUsername} `;
                    }
                    inputEl.focus();
                }
                return;
            }

            // C. Toggle Replies
            const toggleBtn = e.target.closest('[data-action="toggle-replies"]');
            if (toggleBtn) {
                e.preventDefault();
                e.stopPropagation();
                if (toggleBtn.dataset.loading === 'true') return;
                const commentId = toggleBtn.dataset.commentId;
                const parentComment = listEl.querySelector(`#comment-${commentId}`) || document.getElementById(`comment-${commentId}`);
                if (!parentComment) return;

                let repliesContainer = parentComment.querySelector('.replies-container') || parentComment.querySelector(`#replies-${commentId}`) || document.getElementById(`replies-${commentId}`);
                const isExpanded = toggleBtn.classList.contains('expanded');

                if (isExpanded) {
                    // Collapse
                    if (repliesContainer) {
                        repliesContainer.classList.remove('expanded');
                        repliesContainer.classList.add('collapsed');
                        repliesContainer.style.display = 'none';
                    }
                    toggleBtn.classList.remove('expanded');
                    const icon = toggleBtn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('bi-chevron-up');
                        icon.classList.add('bi-chevron-down');
                    }
                    const span = toggleBtn.querySelector('span');
                    if (span) span.textContent = `View ${toggleBtn.dataset.replyCount || ''} replies`;
                } else {
                    // Expand
                    if (repliesContainer && repliesContainer.children.length > 0) {
                        repliesContainer.classList.remove('collapsed');
                        repliesContainer.classList.add('expanded');
                        repliesContainer.style.display = 'block';
                    } else {
                        // Fetch replies from API
                        toggleBtn.dataset.loading = 'true';
                        try {
                            const res = await fetch(`/api/comments/${commentId}/replies/?page=1&page_size=20`);
                            if (res.ok) {
                                const data = await res.json();
                                if (!repliesContainer) {
                                    repliesContainer = document.createElement('div');
                                    repliesContainer.id = `replies-${commentId}`;
                                    repliesContainer.className = 'replies-container expanded ms-4 mt-2 ps-2 border-start';
                                    const contentDiv = parentComment.querySelector('.comment-content') || parentComment;
                                    contentDiv.appendChild(repliesContainer);
                                }
                                repliesContainer.innerHTML = '';
                                const results = data.results || (Array.isArray(data) ? data : []);
                                const seenIds = new Set();
                                results.forEach(reply => {
                                    if (seenIds.has(reply.id)) return;
                                    seenIds.add(reply.id);
                                    const replyAvatar = reply.author?.profile_pic || '/static/images/default-avatar.png';
                                    const replyAuthor = reply.author?.full_name || reply.author?.username || 'User';
                                    const replyUsername = reply.author?.username || '';
                                    const replyLiked = reply.is_liked ? 'liked text-danger' : '';
                                    const profilePath = `/users/user/${replyUsername}/`;
                                    const replyHtml = `
                                        <div class="comment-item reply-item py-2 border-bottom border-light" id="comment-${reply.id}" data-comment-id="${reply.id}" data-parent-id="${commentId}" data-author-id="${reply.author?.id || ''}" data-author-username="${replyUsername}">
                                            <div class="d-flex align-items-start gap-2">
                                                <a href="${profilePath}"
                                                   hx-get="${profilePath}"
                                                   hx-target="#page-content-target"
                                                   hx-swap="innerHTML"
                                                   hx-push-url="true"
                                                   class="text-decoration-none comment-avatar-link">
                                                    <img src="${replyAvatar}" class="rounded-circle border" style="width: 28px; height: 28px; object-fit: cover;" alt="${replyAuthor}">
                                                </a>
                                                <div class="flex-grow-1 min-w-0">
                                                    <div class="d-flex align-items-center justify-content-between">
                                                        <a href="${profilePath}"
                                                           hx-get="${profilePath}"
                                                           hx-target="#page-content-target"
                                                           hx-swap="innerHTML"
                                                           hx-push-url="true"
                                                           class="fw-bold text-dark text-decoration-none small comment-author-link" data-username="${replyUsername}">${replyAuthor}</a>
                                                        <span class="text-muted" style="font-size: 11px;">${reply.created_at ? new Date(reply.created_at).toLocaleDateString() : ''}</span>
                                                    </div>
                                                    <div class="small text-break mt-0.5 comment-body" id="comment-body-${reply.id}">${reply.content}</div>
                                                    <div class="comment-actions d-flex align-items-center gap-3 mt-1" style="font-size: 11px;">
                                                        <button type="button" class="btn btn-link p-0 text-muted text-decoration-none comment-action ${replyLiked}" data-action="like" data-comment-id="${reply.id}">
                                                            <i class="bi ${reply.is_liked ? 'bi-heart-fill text-danger' : 'bi-heart'}"></i>
                                                            <span class="ms-0.5">${reply.like_count || 0}</span>
                                                        </button>
                                                        <button type="button" class="btn btn-link p-0 text-muted text-decoration-none comment-action" data-action="reply" data-comment-id="${reply.id}">
                                                            <i class="bi bi-chat-dots"></i> Reply
                                                        </button>
                                                        <div class="comment-menu-wrapper position-relative d-inline-flex">
                                                            <button type="button" class="btn btn-link p-0 text-muted comment-menu-btn" data-action="menu" data-comment-id="${reply.id}" aria-label="More options" aria-expanded="false">
                                                                <i class="bi bi-three-dots"></i>
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    `;
                                    repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
                                });
                                if (window.htmx) {
                                    window.htmx.process(repliesContainer);
                                }
                                truncateLongComments(repliesContainer);
                                repliesContainer.style.display = 'block';
                            }
                        } catch (err) {
                            console.warn('[CommentsSheet] Failed to load replies:', err);
                        } finally {
                            toggleBtn.dataset.loading = 'false';
                        }
                    }
                    toggleBtn.classList.add('expanded');
                    const icon = toggleBtn.querySelector('i');
                    if (icon) {
                        icon.classList.remove('bi-chevron-down');
                        icon.classList.add('bi-chevron-up');
                    }
                    const span = toggleBtn.querySelector('span');
                    if (span) span.textContent = 'Hide replies';
                }
                return;
            }

            // D. Comment Context Menu (Three Dots)
            const menuBtn = e.target.closest('[data-action="menu"]');
            if (menuBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = menuBtn.dataset.commentId;
                if (!commentId) return;

                const existingMenu = document.getElementById(`menu-${commentId}`);
                closeAllSheetCommentMenus();
                if (existingMenu) return;

                const commentEl = document.getElementById(`comment-${commentId}`);
                if (!commentEl) return;

                const currentUserId = window.PwaniNetUserId;
                const currentUsername = window.PwaniNetUsername;
                const currentUserRole = window.PwaniNetUserRole;

                const authorId = commentEl.dataset.authorId;
                const authorLink = commentEl.querySelector('.comment-author-link');
                const authorUsername = commentEl.dataset.authorUsername ||
                                       authorLink?.dataset?.username ||
                                       (authorLink?.getAttribute('href') || '').match(/\/users\/(?:user\/)?([^\/]+)/)?.[1] ||
                                       '';

                const isOwner = (currentUserId && authorId && String(currentUserId) === String(authorId)) ||
                                (currentUsername && authorUsername && currentUsername.toLowerCase() === authorUsername.toLowerCase());
                const isModerator = ['admin', 'moderator', 'president', 'delegate'].includes((currentUserRole || '').toLowerCase());

                let menuHtml = '';
                if (typeof CommentRenderer !== 'undefined' && CommentRenderer.renderMenu) {
                    menuHtml = CommentRenderer.renderMenu(commentId, isOwner, isModerator);
                } else {
                    let items = '';
                    if (isOwner) {
                        items += `
                            <button type="button" class="comment-menu-item" data-action="edit" data-comment-id="${commentId}">
                                <i class="bi bi-pencil"></i> Edit
                            </button>
                            <button type="button" class="comment-menu-item danger" data-action="delete" data-comment-id="${commentId}">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                            <div class="comment-menu-divider"></div>
                        `;
                    } else if (isModerator) {
                        items += `
                            <button type="button" class="comment-menu-item danger" data-action="delete" data-comment-id="${commentId}">
                                <i class="bi bi-trash"></i> Delete
                            </button>
                            <div class="comment-menu-divider"></div>
                        `;
                    }
                    items += `
                        <button type="button" class="comment-menu-item" data-action="copy-text" data-comment-id="${commentId}">
                            <i class="bi bi-copy"></i> Copy text
                        </button>
                        <button type="button" class="comment-menu-item" data-action="copy-link" data-comment-id="${commentId}">
                            <i class="bi bi-link-45deg"></i> Copy link
                        </button>
                        <button type="button" class="comment-menu-item" data-action="view-profile" data-comment-id="${commentId}">
                            <i class="bi bi-person"></i> View profile
                        </button>
                    `;
                    menuHtml = `<div class="comment-menu-dropdown" id="menu-${commentId}" role="menu">${items}</div>`;
                }

                const wrapper = menuBtn.closest('.comment-menu-wrapper') || menuBtn.parentElement;
                commentEl.classList.add('menu-open');
                wrapper.insertAdjacentHTML('beforeend', menuHtml);
                menuBtn.setAttribute('aria-expanded', 'true');

                const menuEl = document.getElementById(`menu-${commentId}`);
                if (menuEl) {
                    const rect = menuEl.getBoundingClientRect();
                    const modalBody = document.getElementById('commentsModalBody') || window;
                    const bottomEdge = modalBody.getBoundingClientRect ? modalBody.getBoundingClientRect().bottom : window.innerHeight;
                    if (rect.bottom > bottomEdge - 20) {
                        menuEl.classList.add('menu-dropup');
                    }
                }
                return;
            }

            // E. Copy Comment Text
            const copyTextBtn = e.target.closest('[data-action="copy-text"]');
            if (copyTextBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = copyTextBtn.dataset.commentId;
                closeAllSheetCommentMenus();
                const bodyEl = document.getElementById(`comment-body-${commentId}`) ||
                               document.querySelector(`#comment-${commentId} .comment-body`);
                const text = bodyEl ? bodyEl.textContent.trim() : '';
                if (navigator.clipboard && text) {
                    navigator.clipboard.writeText(text).then(() => {
                        showCommentsToast('Comment text copied to clipboard');
                    }).catch(() => {
                        showCommentsToast('Failed to copy text');
                    });
                }
                return;
            }

            // F. Copy Comment Link
            const copyLinkBtn = e.target.closest('[data-action="copy-link"]');
            if (copyLinkBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = copyLinkBtn.dataset.commentId;
                closeAllSheetCommentMenus();
                const curPostId = activeCommentsPostId || postId;
                const url = `${window.location.origin}/posts/${curPostId}/#comment-${commentId}`;
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(url).then(() => {
                        showCommentsToast('Comment link copied to clipboard');
                    }).catch(() => {
                        showCommentsToast('Failed to copy link');
                    });
                }
                return;
            }

            // G. View Profile
            const viewProfileBtn = e.target.closest('[data-action="view-profile"]');
            if (viewProfileBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = viewProfileBtn.dataset.commentId;
                closeAllSheetCommentMenus();
                const commentEl = document.getElementById(`comment-${commentId}`);
                const profileLink = commentEl?.querySelector('.comment-author-link') || commentEl?.querySelector('.comment-avatar-link') || commentEl?.querySelector('a');
                if (profileLink && profileLink.href) {
                    window.location.href = profileLink.href;
                }
                return;
            }

            // H. Edit Comment Mode
            const editBtn = e.target.closest('[data-action="edit"]');
            if (editBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = editBtn.dataset.commentId;
                closeAllSheetCommentMenus();
                const bodyEl = document.getElementById(`comment-body-${commentId}`) ||
                               document.querySelector(`#comment-${commentId} .comment-body`);
                if (!bodyEl) return;
                if (document.getElementById(`edit-mode-${commentId}`)) return;

                const curText = bodyEl.textContent.trim();
                bodyEl.dataset.originalText = curText;
                bodyEl.style.display = 'none';

                const editHtml = `
                    <div class="comment-edit-mode mt-1" id="edit-mode-${commentId}">
                        <textarea class="form-control form-control-sm mb-1 edit-textarea" id="edit-input-${commentId}" rows="2" style="font-size: 13px;">${curText}</textarea>
                        <div class="d-flex justify-content-end gap-2">
                            <button type="button" class="btn btn-sm btn-light border py-0 px-2" data-action="cancel-edit" data-comment-id="${commentId}" style="font-size: 12px;">Cancel</button>
                            <button type="button" class="btn btn-sm btn-primary py-0 px-2" data-action="save-edit" data-comment-id="${commentId}" style="font-size: 12px;">Save</button>
                        </div>
                    </div>
                `;
                bodyEl.insertAdjacentHTML('afterend', editHtml);
                const textarea = document.getElementById(`edit-input-${commentId}`);
                if (textarea) textarea.focus();
                return;
            }

            // I. Cancel Edit Mode
            const cancelEditBtn = e.target.closest('[data-action="cancel-edit"]');
            if (cancelEditBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = cancelEditBtn.dataset.commentId;
                const editMode = document.getElementById(`edit-mode-${commentId}`);
                const bodyEl = document.getElementById(`comment-body-${commentId}`) ||
                               document.querySelector(`#comment-${commentId} .comment-body`);
                if (bodyEl) bodyEl.style.display = '';
                if (editMode) editMode.remove();
                return;
            }

            // J. Save Edit
            const saveEditBtn = e.target.closest('[data-action="save-edit"]');
            if (saveEditBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = saveEditBtn.dataset.commentId;
                const textarea = document.getElementById(`edit-input-${commentId}`);
                const newText = textarea ? textarea.value.trim() : '';
                if (!newText) return;

                saveEditBtn.disabled = true;
                saveEditBtn.textContent = 'Saving...';

                try {
                    const res = await fetch(`/api/comments/${commentId}/`, {
                        method: 'PATCH',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken()
                        },
                        body: JSON.stringify({ content: newText })
                    });
                    if (res.ok) {
                        const data = await res.json();
                        const bodyEl = document.getElementById(`comment-body-${commentId}`) ||
                                       document.querySelector(`#comment-${commentId} .comment-body`);
                        if (bodyEl) {
                            bodyEl.textContent = data.content || newText;
                            bodyEl.style.display = '';
                        }
                        const editMode = document.getElementById(`edit-mode-${commentId}`);
                        if (editMode) editMode.remove();
                        showCommentsToast('Comment updated');
                    } else {
                        saveEditBtn.disabled = false;
                        saveEditBtn.textContent = 'Save';
                        showCommentsToast('Failed to update comment');
                    }
                } catch (err) {
                    console.error('[CommentsSheet] Save edit error:', err);
                    saveEditBtn.disabled = false;
                    saveEditBtn.textContent = 'Save';
                    showCommentsToast('Failed to update comment');
                }
                return;
            }

            // K. Delete Comment
            const deleteBtn = e.target.closest('[data-action="delete"]');
            if (deleteBtn) {
                e.preventDefault();
                e.stopPropagation();
                const commentId = deleteBtn.dataset.commentId;
                closeAllSheetCommentMenus();

                if (!confirm('Are you sure you want to delete this comment?')) {
                    return;
                }

                try {
                    const res = await fetch(`/api/comments/${commentId}/`, {
                        method: 'DELETE',
                        headers: {
                            'X-CSRFToken': getCsrfToken()
                        }
                    });
                    if (res.ok) {
                        const commentEl = document.getElementById(`comment-${commentId}`);
                        if (commentEl) {
                            const parentId = commentEl.dataset.parentId;

                            commentEl.style.transition = 'all 0.25s ease';
                            commentEl.style.opacity = '0';
                            commentEl.style.transform = 'translateX(20px)';
                            setTimeout(() => {
                                commentEl.remove();

                                // If reply, decrement parent reply count
                                if (parentId) {
                                    const parentComment = document.getElementById(`comment-${parentId}`);
                                    const toggle = parentComment?.querySelector('[data-action="toggle-replies"]');
                                    if (toggle) {
                                        let rCount = Math.max(0, (parseInt(toggle.dataset.replyCount, 10) || 1) - 1);
                                        toggle.dataset.replyCount = rCount;
                                        const span = toggle.querySelector('span');
                                        if (rCount === 0) {
                                            toggle.style.display = 'none';
                                        } else if (span) {
                                            span.textContent = `View ${rCount} ${rCount === 1 ? 'reply' : 'replies'}`;
                                        }
                                    }
                                }

                                // Decrement total comment counter
                                const countEl = document.getElementById('commentsModalCount');
                                let curN = Math.max(0, (parseInt(countEl?.textContent || '1', 10) || 1) - 1);
                                if (countEl) countEl.textContent = curN;

                                const curPostId = activeCommentsPostId || postId;
                                const inlinePostCount = document.getElementById(`comment-count-${curPostId}`);
                                const inlineReelCount = document.getElementById(`reel-comment-count-${curPostId}`);
                                const fsReelCount = document.getElementById(`fs-reel-comment-count-${curPostId}`);
                                if (inlinePostCount) inlinePostCount.textContent = curN;
                                if (inlineReelCount) inlineReelCount.textContent = curN;
                                if (fsReelCount) fsReelCount.textContent = curN;
                            }, 250);
                        }
                        showCommentsToast('Comment deleted');
                    } else {
                        showCommentsToast('Could not delete comment');
                    }
                } catch (err) {
                    console.error('[CommentsSheet] Delete error:', err);
                    showCommentsToast('Could not delete comment');
                }
                return;
            }
        });
    }

    function openCommentsSheet(postId) {
        postId = postId ? String(postId).trim() : '';
        if (!postId || postId === 'null' || postId === 'undefined') {
            console.warn('[CommentsSheet] Aborting openCommentsSheet on invalid postId:', postId);
            return;
        }
        activeCommentsPostId = postId;

        const modalEl = document.getElementById('commentsModal');
        if (!modalEl || typeof bootstrap === 'undefined') {
            console.warn('[CommentsSheet] Comments modal or bootstrap is unavailable.');
            return;
        }

        const countEl = document.getElementById('commentsModalCount');
        const loadingEl = document.getElementById('commentsModalLoading');
        const listEl = document.getElementById('commentsModalList');
        const formEl = document.getElementById('reelCommentForm');
        const inputEl = document.getElementById('reelCommentInput');
        const parentInput = document.getElementById('commentsModalParentId');
        const replyBanner = document.getElementById('commentsModalReplyBanner');

        // Reset reply state
        if (parentInput) parentInput.value = '';
        if (replyBanner) replyBanner.classList.add('d-none');
        if (inputEl) {
            inputEl.value = '';
            inputEl.placeholder = 'Add a comment...';
        }

        if (loadingEl) loadingEl.style.display = 'block';
        if (listEl) {
            listEl.innerHTML = '';
            delete listEl.dataset.eventsBound;
        }

        // Read current count from postcard or reelcard
        const curCount = document.getElementById(`comment-count-${postId}`)?.textContent ||
                         document.getElementById(`reel-comment-count-${postId}`)?.textContent ||
                         document.getElementById(`fs-reel-comment-count-${postId}`)?.textContent ||
                         document.getElementById('fsRailCommentCount')?.textContent || '0';
        if (countEl) countEl.textContent = curCount.trim();

        // Fetch comments dynamically without navigating away
        fetch(`/post/${postId}/?show_all=1`, {
            headers: { 'HX-Request': 'true' }
        })
        .then(res => res.text())
        .then(html => {
            if (loadingEl) loadingEl.style.display = 'none';
            if (listEl) {
                listEl.innerHTML = html;
                if (window.htmx) {
                    htmx.process(listEl);
                }
                initSheetCommentsInteractions(listEl, postId);
            }
        })
        .catch(err => {
            console.warn('[CommentsSheet] Error loading comments:', err);
            if (loadingEl) loadingEl.style.display = 'none';
            if (listEl) listEl.innerHTML = '<div class="text-center py-4 text-muted small">Could not load comments.</div>';
        });

        // Bind comment submission with double-submission protection
        if (formEl && !formEl.dataset.bound) {
            formEl.dataset.bound = 'true';
            formEl.onsubmit = function(e) {
                e.preventDefault();
                if (formEl.dataset.submitting === 'true') return;

                const curPostId = activeCommentsPostId;
                if (!curPostId) return;

                const content = inputEl?.value?.trim();
                if (!content) return;

                formEl.dataset.submitting = 'true';
                const sendBtn = formEl.querySelector('button[type="submit"]');
                if (sendBtn) sendBtn.disabled = true;

                const targetParentId = (parentInput && parentInput.value) ? parentInput.value : '';

                const formData = new FormData();
                formData.append('content', content);
                formData.append('csrfmiddlewaretoken', getCsrfToken());
                if (targetParentId) {
                    formData.append('parent_id', targetParentId);
                }

                fetch(`/post/${curPostId}/comment/`, {
                    method: 'POST',
                    body: formData,
                    headers: { 'HX-Request': 'true' }
                })
                .then(res => res.text())
                .then(html => {
                    delete formEl.dataset.submitting;
                    if (sendBtn) sendBtn.disabled = false;
                    if (inputEl) inputEl.value = '';
                    if (parentInput) parentInput.value = '';
                    if (replyBanner) replyBanner.classList.add('d-none');

                    if (listEl) {
                        delete listEl.dataset.eventsBound;
                        listEl.innerHTML = html;
                        if (window.htmx) {
                            htmx.process(listEl);
                        }
                        initSheetCommentsInteractions(listEl, curPostId);
                    }

                    // Update all counters
                    let curN = parseInt(countEl?.textContent || '0', 10) || 0;
                    let newN = curN + 1;
                    if (countEl) countEl.textContent = newN;

                    const inlinePostCount = document.getElementById(`comment-count-${curPostId}`);
                    const inlineReelCount = document.getElementById(`reel-comment-count-${curPostId}`);
                    const fsReelCount = document.getElementById(`fs-reel-comment-count-${curPostId}`);
                    if (inlinePostCount) inlinePostCount.textContent = newN;
                    if (inlineReelCount) inlineReelCount.textContent = newN;
                    if (fsReelCount) fsReelCount.textContent = newN;

                    // If it was a reply, auto-expand that parent comment's replies thread
                    if (targetParentId) {
                        const parentEl = document.getElementById(`comment-${targetParentId}`);
                        const toggleBtn = parentEl?.querySelector('[data-action="toggle-replies"]');
                        if (toggleBtn) {
                            toggleBtn.click();
                            setTimeout(() => {
                                parentEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }, 250);
                        }
                    } else {
                        // Scroll to bottom of comments list to view new comment
                        const modalBody = document.getElementById('commentsModalBody');
                        if (modalBody) {
                            modalBody.scrollTo({ top: modalBody.scrollHeight, behavior: 'smooth' });
                        }
                    }
                })
                .catch(err => {
                    delete formEl.dataset.submitting;
                    if (sendBtn) sendBtn.disabled = false;
                    console.error('[CommentsSheet] Comment post error:', err);
                });
            };
        }

        // Cancel reply button
        const cancelReplyBtn = document.getElementById('commentsModalCancelReply');
        if (cancelReplyBtn && !cancelReplyBtn.dataset.bound) {
            cancelReplyBtn.dataset.bound = 'true';
            cancelReplyBtn.onclick = function() {
                if (parentInput) parentInput.value = '';
                if (replyBanner) replyBanner.classList.add('d-none');
                if (inputEl && /^@\w+\s*$/.test(inputEl.value)) {
                    inputEl.value = '';
                    inputEl.placeholder = 'Add a comment...';
                }
            };
        }

        bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }

    const openReelComments = openCommentsSheet;

    // ============================================================================
    // SCRUBBER DRAG & JUMP CONTROLLER
    // ============================================================================

    const scrubberState = {
        isDragging: false,
        activeContainer: null,
        activeVideo: null,
        wasPlaying: false
    };

    function updateScrubPosition(clientX) {
        if (!scrubberState.isDragging || !scrubberState.activeContainer) return;

        const rect = scrubberState.activeContainer.getBoundingClientRect();
        if (rect.width === 0) return;

        const ratio = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));

        const bar = scrubberState.activeContainer.querySelector('.reel-progress-bar');
        if (bar) {
            bar.style.width = `${ratio * 100}%`;
        }

        if (scrubberState.activeVideo && scrubberState.activeVideo.duration) {
            scrubberState.activeVideo.currentTime = ratio * scrubberState.activeVideo.duration;
        }
    }

    function startScrubbing(container, clientX) {
        const card = container.closest('.reel-card-container, .reel-post-card, .reels-snap-item');
        const video = card?.querySelector('video');
        if (!video) return;

        scrubberState.isDragging = true;
        scrubberState.activeContainer = container;
        scrubberState.activeVideo = video;
        scrubberState.wasPlaying = !video.paused;

        if (scrubberState.wasPlaying) {
            pauseVideo(video);
        }

        container.classList.add('is-dragging');
        updateScrubPosition(clientX);
    }

    function stopScrubbing() {
        if (!scrubberState.isDragging) return;

        if (scrubberState.activeContainer) {
            scrubberState.activeContainer.classList.remove('is-dragging');
        }

        if (scrubberState.activeVideo && scrubberState.wasPlaying) {
            playVideo(scrubberState.activeVideo, false);
        }

        scrubberState.isDragging = false;
        scrubberState.activeContainer = null;
        scrubberState.activeVideo = null;
        scrubberState.wasPlaying = false;
    }

    function handleScrubberClick(container, event) {
        const rect = container.getBoundingClientRect();
        if (rect.width === 0) return;
        const clickX = event.clientX - rect.left;
        const ratio = Math.max(0, Math.min(1, clickX / rect.width));
        const card = container.closest('.reel-card-container, .reel-post-card, .reels-snap-item');
        const video = card?.querySelector('video');
        if (video && video.duration) {
            video.currentTime = ratio * video.duration;
            const bar = container.querySelector('.reel-progress-bar');
            if (bar) bar.style.width = `${ratio * 100}%`;
        }
    }

    // ============================================================================
    // INITIALIZATION & EVENT DELEGATION
    // ============================================================================

    function setupDelegatedListeners() {
        // Tap and Hitbox handling
        document.addEventListener('click', function(event) {
            // Hitbox single vs. double tap (pauses/plays or likes)
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

            // Carousel Card Click -> Open Fullscreen Reel
            const carouselCard = event.target.closest('.reels-carousel-card');
            if (carouselCard) {
                event.preventDefault();
                event.stopPropagation();
                const postId = carouselCard.dataset.postId || extractPostId(carouselCard);
                openFullscreenReels(postId);
                return;
            }

            // Carousel View All Link Click -> Open Fullscreen Reel
            const viewAllLink = event.target.closest('.reels-view-all-link');
            if (viewAllLink) {
                event.preventDefault();
                event.stopPropagation();
                const shelf = viewAllLink.closest('.reels-carousel-shelf');
                const firstCard = shelf?.querySelector('.reels-carousel-card');
                const postId = firstCard ? (firstCard.dataset.postId || extractPostId(firstCard)) : null;
                openFullscreenReels(postId);
                return;
            }

            // Expand to Fullscreen Reel (Only clicking this button opens fullscreen mode)
            const expandBtn = event.target.closest('.reel-expand-btn, [data-action="fullscreen"]');
            if (expandBtn) {
                event.preventDefault();
                event.stopPropagation();
                const postId = extractPostId(expandBtn);
                openFullscreenReels(postId);
                return;
            }

            // Desktop Next / Previous Reel buttons
            const navNext = event.target.closest('#reelsNavNext');
            if (navNext) {
                event.preventDefault();
                event.stopPropagation();
                const viewport = document.getElementById('reelsSnapViewport');
                if (viewport && viewport.children.length > 0) {
                    const h = viewport.clientHeight;
                    const curIdx = Math.round(viewport.scrollTop / h);
                    const nextIdx = Math.min(viewport.children.length - 1, curIdx + 1);
                    viewport.scrollTo({ top: nextIdx * h, behavior: 'smooth' });
                    updateFullscreenNavButtons(nextIdx);
                }
                return;
            }

            const navPrev = event.target.closest('#reelsNavPrev');
            if (navPrev) {
                event.preventDefault();
                event.stopPropagation();
                const viewport = document.getElementById('reelsSnapViewport');
                if (viewport && viewport.children.length > 0) {
                    const h = viewport.clientHeight;
                    const curIdx = Math.round(viewport.scrollTop / h);
                    const prevIdx = Math.max(0, curIdx - 1);
                    viewport.scrollTo({ top: prevIdx * h, behavior: 'smooth' });
                    updateFullscreenNavButtons(prevIdx);
                }
                return;
            }

            // Comment trigger button (both reels and postcards)
            const commentBtn = event.target.closest('.reel-comment-trigger, .postcard-comment-btn, [data-action="open-comments"], #fsDesktopCommentBtn');
            if (commentBtn) {
                event.preventDefault();
                event.stopPropagation();
                if (state.isFullScreenActive && window.innerWidth >= 992) {
                    const sideInput = document.getElementById('fsRailCommentInput');
                    if (sideInput) sideInput.focus();
                    return;
                }
                const rawPostId = commentBtn.dataset.postId || extractPostId(commentBtn);
                const postId = rawPostId ? String(rawPostId).trim() : '';
                if (!postId || postId === 'null' || postId === 'undefined') return;
                openCommentsSheet(postId);
                return;
            }

            // Options trigger button
            const optionsBtn = event.target.closest('.reel-options-btn');
            if (optionsBtn) {
                event.preventDefault();
                event.stopPropagation();
                const rawPostId = optionsBtn.dataset.postId || extractPostId(optionsBtn);
                const postId = rawPostId ? String(rawPostId).trim() : '';
                if (!postId || postId === 'null' || postId === 'undefined') return;
                openReelQuickTools(postId, optionsBtn);
                return;
            }

            // Micro-scrubber click (instant jump if not dragged)
            const scrubber = event.target.closest('.reel-progress-container');
            if (scrubber) {
                event.preventDefault();
                event.stopPropagation();
                handleScrubberClick(scrubber, event);
                return;
            }

            // Close Fullscreen Reel
            const closeBtn = event.target.closest('#closeReelsOverlay, .close-fs-reels-btn');
            if (closeBtn) {
                event.preventDefault();
                event.stopPropagation();
                closeFullscreenReels();
                return;
            }

            // Proxy like button in fullscreen modal -> triggers inline like button & updates counter
            const fsLikeBtn = event.target.closest('.fs-like-proxy-btn');
            if (fsLikeBtn) {
                event.preventDefault();
                event.stopPropagation();
                const postId = fsLikeBtn.dataset.postId || currentDesktopRailPostId;
                if (!postId) return;
                const inlineLikeBtn = document.querySelector(`#reel-like-wrap-${postId} .like-button`) ||
                                      document.querySelector(`.like-button[data-post-id="${postId}"]`);
                if (inlineLikeBtn) {
                    inlineLikeBtn.click();
                }
                const wasLiked = fsLikeBtn.classList.toggle('liked');
                fsLikeBtn.classList.toggle('text-danger', wasLiked);
                const icon = fsLikeBtn.querySelector('i');
                if (icon) {
                    icon.className = wasLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
                }

                // Sync desktop exterior like button
                const desktopLikeBtn = document.getElementById('fsDesktopLikeBtn');
                if (desktopLikeBtn && desktopLikeBtn !== fsLikeBtn) {
                    desktopLikeBtn.classList.toggle('liked', wasLiked);
                    const dIcon = desktopLikeBtn.querySelector('i');
                    if (dIcon) dIcon.className = wasLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
                }

                // Sync in-video proxy like button
                const inVideoLikeBtn = document.querySelector(`.reels-snap-item[data-post-id="${postId}"] .fs-like-proxy-btn`);
                if (inVideoLikeBtn && inVideoLikeBtn !== fsLikeBtn) {
                    inVideoLikeBtn.classList.toggle('liked', wasLiked);
                    inVideoLikeBtn.classList.toggle('text-danger', wasLiked);
                    const ivIcon = inVideoLikeBtn.querySelector('i');
                    if (ivIcon) ivIcon.className = wasLiked ? 'bi bi-heart-fill text-danger' : 'bi bi-heart';
                }

                const fsCountEl = document.getElementById(`fs-reel-like-count-${postId}`);
                const desktopCountEl = document.getElementById('fsDesktopLikeCount');
                const inlineCountEl = document.getElementById(`reel-like-count-${postId}`);
                let cur = parseInt(fsCountEl?.textContent || desktopCountEl?.textContent || inlineCountEl?.textContent || '0', 10) || 0;
                let newCount = wasLiked ? cur + 1 : Math.max(0, cur - 1);
                if (fsCountEl) fsCountEl.textContent = newCount;
                if (desktopCountEl) desktopCountEl.textContent = newCount;
                if (inlineCountEl) inlineCountEl.textContent = newCount;

                const activeSnapItem = document.querySelector(`.reels-snap-item[data-post-id="${postId}"]`);
                if (activeSnapItem) {
                    activeSnapItem.dataset.isLiked = wasLiked ? 'true' : 'false';
                    activeSnapItem.dataset.likes = newCount;
                }
                return;
            }
        });

        // Scrubber Dragging Listeners (Desktop Mouse Drag & Mobile Touch Scrubbing)
        document.addEventListener('mousedown', function(event) {
            const scrubber = event.target.closest('.reel-progress-container');
            if (scrubber) {
                event.preventDefault();
                event.stopPropagation();
                startScrubbing(scrubber, event.clientX);
            }
        });

        document.addEventListener('touchstart', function(event) {
            const scrubber = event.target.closest('.reel-progress-container');
            if (scrubber && event.touches.length > 0) {
                event.stopPropagation();
                startScrubbing(scrubber, event.touches[0].clientX);
            }
        }, { passive: false });

        document.addEventListener('mousemove', function(event) {
            if (scrubberState.isDragging) {
                event.preventDefault();
                updateScrubPosition(event.clientX);
            }
        });

        document.addEventListener('touchmove', function(event) {
            if (scrubberState.isDragging && event.touches.length > 0) {
                event.preventDefault();
                updateScrubPosition(event.touches[0].clientX);
            }
        }, { passive: false });

        document.addEventListener('mouseup', function() {
            if (scrubberState.isDragging) {
                stopScrubbing();
            }
        });

        document.addEventListener('touchend', function() {
            if (scrubberState.isDragging) {
                stopScrubbing();
            }
        });

        document.addEventListener('touchcancel', function() {
            if (scrubberState.isDragging) {
                stopScrubbing();
            }
        });

        // Long-press detection on reel cards and hitboxes
        let longPressTimer = null;
        let touchStartX = 0;
        let touchStartY = 0;

        document.addEventListener('touchstart', function(event) {
            const hitbox = event.target.closest('.reel-center-hitbox, .reel-tap-hitbox, .reel-stage-container, .reel-card-container');
            if (!hitbox) return;

            const touch = event.touches[0];
            touchStartX = touch.clientX;
            touchStartY = touch.clientY;
            state.hasLongPressed = false;

            longPressTimer = setTimeout(() => {
                state.hasLongPressed = true;
                if (navigator.vibrate) navigator.vibrate(35);
                const postId = extractPostId(hitbox);
                if (postId) {
                    openReelQuickTools(postId, hitbox);
                }
            }, 480);
        }, { passive: true });

        document.addEventListener('touchmove', function(event) {
            if (!longPressTimer) return;
            const touch = event.touches[0];
            if (Math.abs(touch.clientX - touchStartX) > 12 || Math.abs(touch.clientY - touchStartY) > 12) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        }, { passive: true });

        document.addEventListener('touchend', function() {
            if (longPressTimer) {
                clearTimeout(longPressTimer);
                longPressTimer = null;
            }
        }, { passive: true });

        // Right click context menu on desktop -> opens quick tools
        document.addEventListener('contextmenu', function(event) {
            const card = event.target.closest('.reel-stage-container, .reel-card-container, .reel-post-card, .reels-carousel-card');
            if (card) {
                event.preventDefault();
                const postId = extractPostId(card);
                if (postId) openReelQuickTools(postId, card);
            }
        });

        // Fullscreen keyboard navigation (Escape, Up/Down arrows, Page Up/Down, Space play/pause, M mute)
        document.addEventListener('keydown', function(event) {
            if (!state.isFullScreenActive) return;

            // Don't intercept typing in inputs/textareas
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.isContentEditable) {
                return;
            }

            if (event.key === 'Escape') {
                event.preventDefault();
                closeFullscreenReels();
                return;
            }

            const viewport = document.getElementById('reelsSnapViewport');
            if (!viewport) return;

            if (event.key === 'ArrowDown' || event.key === 'PageDown' || event.key.toLowerCase() === 'j') {
                event.preventDefault();
                const h = viewport.clientHeight || 1;
                const curIdx = Math.round(viewport.scrollTop / h);
                const nextIdx = Math.min(viewport.children.length - 1, curIdx + 1);
                viewport.scrollTo({ top: nextIdx * h, behavior: 'smooth' });
                updateFullscreenNavButtons(nextIdx);
                return;
            }

            if (event.key === 'ArrowUp' || event.key === 'PageUp' || event.key.toLowerCase() === 'k') {
                event.preventDefault();
                const h = viewport.clientHeight || 1;
                const curIdx = Math.round(viewport.scrollTop / h);
                const prevIdx = Math.max(0, curIdx - 1);
                viewport.scrollTo({ top: prevIdx * h, behavior: 'smooth' });
                updateFullscreenNavButtons(prevIdx);
                return;
            }

            if (event.key === ' ' || event.code === 'Space') {
                event.preventDefault();
                if (state.currentPlayingVideo) {
                    const snapItem = state.currentPlayingVideo.closest('.reels-snap-item');
                    if (state.currentPlayingVideo.paused) {
                        playVideo(state.currentPlayingVideo, false);
                        if (snapItem) triggerPlayHud(snapItem, true);
                    } else {
                        pauseVideo(state.currentPlayingVideo);
                        if (snapItem) triggerPlayHud(snapItem, false);
                    }
                }
                return;
            }

            if (event.key.toLowerCase() === 'm') {
                event.preventDefault();
                toggleGlobalMute();
                return;
            }
        });

        // Timeupdate to sync micro-scrubber progress bars
        document.addEventListener('timeupdate', function(event) {
            const video = event.target;
            if (video.tagName !== 'VIDEO') return;
            if (!video.duration) return;

            const pct = (video.currentTime / video.duration) * 100;
            const card = video.closest('.reel-card-container, .reel-post-card, .reels-snap-item');
            if (card) {
                const bar = card.querySelector('.reel-progress-bar');
                if (bar) {
                    bar.style.width = `${pct}%`;
                }
            }
        }, true);

        // Sync vinyl disc animation on play
        document.addEventListener('play', function(event) {
            const video = event.target;
            if (video.tagName !== 'VIDEO') return;

            if (state.currentPlayingVideo && state.currentPlayingVideo !== video) {
                pauseVideo(state.currentPlayingVideo);
            }
            state.currentPlayingVideo = video;

            const card = video.closest('.reel-card-container, .reel-post-card, .reels-snap-item');
            if (card) {
                const vinyl = card.querySelector('.reel-vinyl-disc');
                if (vinyl) vinyl.classList.add('is-playing');
            }
        }, true);

        // Sync vinyl disc animation on pause
        document.addEventListener('pause', function(event) {
            const video = event.target;
            if (video.tagName !== 'VIDEO') return;

            const card = video.closest('.reel-card-container, .reel-post-card, .reels-snap-item');
            if (card) {
                const vinyl = card.querySelector('.reel-vinyl-disc');
                if (vinyl) vinyl.classList.remove('is-playing');
            }
        }, true);

        // Pause on visibility change
        document.addEventListener('visibilitychange', function() {
            if (document.hidden && state.currentPlayingVideo) {
                pauseVideo(state.currentPlayingVideo);
            }
        });

        // Passive scroll listener on snap viewport to synchronize Up/Down buttons
        const snapViewportEl = document.getElementById('reelsSnapViewport');
        if (snapViewportEl) {
            let scrollNavTimer = null;
            snapViewportEl.addEventListener('scroll', function() {
                if (!state.isFullScreenActive) return;
                clearTimeout(scrollNavTimer);
                scrollNavTimer = setTimeout(() => {
                    updateFullscreenNavButtons();
                }, 40);
            }, { passive: true });
        }

        window.addEventListener('resize', function() {
            if (state.isFullScreenActive) {
                const viewport = document.getElementById('reelsSnapViewport');
                if (viewport) {
                    const h = viewport.clientHeight || 1;
                    const curIdx = Math.round(viewport.scrollTop / h);
                    const activeSnap = viewport.children[curIdx] || viewport.firstElementChild;
                    if (activeSnap) {
                        const content = activeSnap.querySelector('.reel-fullscreen-content');
                        if (window.innerWidth < 992) {
                            if (content) {
                                content.style.width = '';
                                content.style.height = '';
                                content.style.maxWidth = '';
                                content.style.maxHeight = '';
                                content.style.aspectRatio = '';
                                content.classList.remove('is-portrait', 'is-landscape', 'is-square');
                            }
                        } else {
                            adaptSnapItemOrientation(activeSnap);
                            repositionDesktopActionsRail(content);
                        }
                    }
                }
            }
        });
    }

    // ============================================================================
    // REELS CAROUSEL STICK-AUTOPLAY ENGINE
    // ============================================================================

    let carouselShelfObserver = null;
    let activeCarouselCard = null;
    let carouselStickDebounceTimer = null;

    function stopCarouselAutoplay(resetActive = true) {
        if (carouselStickDebounceTimer) {
            clearTimeout(carouselStickDebounceTimer);
            carouselStickDebounceTimer = null;
        }

        if (activeCarouselCard) {
            const vid = activeCarouselCard.querySelector('video.reels-carousel-video');
            if (vid) {
                try {
                    vid.pause();
                    vid.currentTime = 0;
                    vid.style.opacity = '0';
                } catch (e) {}
            }
            if (resetActive) {
                activeCarouselCard = null;
            }
        }
    }

    function playCarouselCard(card) {
        if (!card || state.isFullScreenActive) return;
        if (activeCarouselCard === card) {
            const vid = card.querySelector('video.reels-carousel-video');
            if (vid && !vid.paused) return; // already playing
        }

        stopCarouselAutoplay(false);

        const video = card.querySelector('video.reels-carousel-video');
        if (!video) return;

        activeCarouselCard = card;
        video.muted = true;
        video.volume = 0;
        video.style.opacity = '1';

        const playPromise = video.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {
                video.muted = true;
                video.volume = 0;
                video.play().catch(() => {});
            });
        }
    }

    function findCenterCarouselCard(track) {
        if (!track) return null;
        const cards = Array.from(track.querySelectorAll('.reels-carousel-card'));
        if (cards.length === 0) return null;

        const trackRect = track.getBoundingClientRect();
        const centerLine = trackRect.left + trackRect.width / 2;

        let closestCard = null;
        let minDiff = Infinity;

        cards.forEach(card => {
            const rect = card.getBoundingClientRect();
            if (rect.right < trackRect.left || rect.left > trackRect.right) return;

            const cardCenter = rect.left + rect.width / 2;
            const diff = Math.abs(cardCenter - centerLine);
            if (diff < minDiff) {
                minDiff = diff;
                closestCard = card;
            }
        });

        return closestCard || cards[0];
    }

    function scheduleCarouselStickCheck(shelf, delayMs = 1200) {
        if (state.isFullScreenActive) return;
        if (carouselStickDebounceTimer) {
            clearTimeout(carouselStickDebounceTimer);
        }

        carouselStickDebounceTimer = setTimeout(() => {
            if (state.isFullScreenActive) return;
            if (!shelf || !shelf.isConnected) return;

            const rect = shelf.getBoundingClientRect();
            const vh = window.innerHeight || document.documentElement.clientHeight;
            const visibleHeight = Math.min(rect.bottom, vh) - Math.max(rect.top, 0);
            if (visibleHeight <= 0 || visibleHeight / rect.height < 0.4) {
                stopCarouselAutoplay();
                return;
            }

            const track = shelf.querySelector('.reels-carousel-track');
            const targetCard = findCenterCarouselCard(track);
            if (targetCard) {
                playCarouselCard(targetCard);
            }
        }, delayMs);
    }

    function initializeCarouselShelves(container = document.body) {
        const shelves = container.querySelectorAll('.reels-carousel-shelf');
        if (shelves.length === 0) return;

        if (!carouselShelfObserver) {
            carouselShelfObserver = new IntersectionObserver((entries) => {
                if (state.isFullScreenActive) return;
                entries.forEach(entry => {
                    const shelf = entry.target;
                    if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
                        shelf.dataset.inView = 'true';
                        scheduleCarouselStickCheck(shelf, 1200);
                    } else if (!entry.isIntersecting || entry.intersectionRatio < 0.35) {
                        shelf.dataset.inView = 'false';
                        if (activeCarouselCard && activeCarouselCard.closest('.reels-carousel-shelf') === shelf) {
                            stopCarouselAutoplay();
                        }
                    }
                });
            }, {
                root: null,
                threshold: [0.1, 0.35, 0.5, 0.7]
            });
        }

        shelves.forEach(shelf => {
            if (shelf.dataset.carouselInit === 'true') return;
            shelf.dataset.carouselInit = 'true';

            carouselShelfObserver.observe(shelf);

            const track = shelf.querySelector('.reels-carousel-track');
            if (track) {
                track.addEventListener('scroll', () => {
                    if (activeCarouselCard) {
                        stopCarouselAutoplay(false);
                    }
                    if (shelf.dataset.inView === 'true') {
                        scheduleCarouselStickCheck(shelf, 1000);
                    }
                }, { passive: true });
            }

            const cards = shelf.querySelectorAll('.reels-carousel-card');
            cards.forEach(card => {
                let hoverTimer = null;
                card.addEventListener('mouseenter', () => {
                    if (window.matchMedia && window.matchMedia('(pointer: coarse)').matches) return;
                    hoverTimer = setTimeout(() => {
                        playCarouselCard(card);
                    }, 350);
                });

                card.addEventListener('mouseleave', () => {
                    if (hoverTimer) {
                        clearTimeout(hoverTimer);
                        hoverTimer = null;
                    }
                    if (activeCarouselCard === card) {
                        stopCarouselAutoplay();
                        if (shelf.dataset.inView === 'true') {
                            scheduleCarouselStickCheck(shelf, 800);
                        }
                    }
                });
            });
        });
    }

    // Scroll listener on window: debounces stick timer and stops video if shelf leaves viewport
    window.addEventListener('scroll', () => {
        if (state.isFullScreenActive) return;
        if (activeCarouselCard) {
            const shelf = activeCarouselCard.closest('.reels-carousel-shelf');
            if (shelf) {
                const r = shelf.getBoundingClientRect();
                const vh = window.innerHeight || document.documentElement.clientHeight;
                if (r.bottom < 60 || r.top > vh - 60) {
                    stopCarouselAutoplay();
                }
            }
        }
        const visibleShelf = document.querySelector('.reels-carousel-shelf[data-in-view="true"]');
        if (visibleShelf) {
            scheduleCarouselStickCheck(visibleShelf, 1200);
        }
    }, { passive: true });

    function initializeVideos(container = document.body) {
        if (!state.feedObserver) {
            createFeedObserver();
        }

        const videos = container.querySelectorAll('video');
        videos.forEach(video => {
            if (!video.dataset.pwaniObserved) {
                video.dataset.pwaniObserved = 'true';
                video.muted = isGlobalMuted;

                // Carousel videos are controlled exclusively by the carousel stick-autoplay engine
                if (video.classList.contains('reels-carousel-video') || video.closest('.reels-carousel-shelf')) {
                    video.dataset.autoplay = 'false';
                    return;
                }

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

        // Initialize carousel shelves inside this container
        initializeCarouselShelves(container);

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
            const target = event.detail?.target;
            if (state.isFullScreenActive && target) {
                const isPageNavigation = target.id === 'page-content-target' ||
                                         target.tagName === 'BODY' ||
                                         target.tagName === 'MAIN';
                if (isPageNavigation) {
                    closeFullscreenReels();
                }
            }
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
                if (state.isFullScreenActive) {
                    appendNewVideosToFullscreenViewport();
                }
            }
        });

        document.addEventListener('htmx:load', function(event) {
            const elt = event.detail?.elt || document.body;
            if (elt && elt.querySelector && elt.querySelector('video')) {
                initializeVideos(elt);
                if (state.isFullScreenActive) {
                    appendNewVideosToFullscreenViewport();
                }
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

    window.openCommentsSheet = openCommentsSheet;
    window.openReelComments = openCommentsSheet;

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
        openCommentsSheet,
        openReelComments,
        get isGlobalMuted() { return isGlobalMuted; },
        get state() { return state; }
    };

    window.videoManager = window.PwaniNetVideoManager;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
