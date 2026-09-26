/**
 * PwaniNet Industry-Standard Adaptive Bitrate Streaming (ABTS) Engine
 *
 * Implements Instagram/TikTok-grade video playback:
 *   1. Cross-video Bandwidth Memory (PwaniBandwidthEstimator) across reels and page sessions.
 *   2. Smart ABR Level Selection (instant crisp HD on good networks, instant fast-start on poor networks).
 *   3. Viewport-driven lazy HLS attachment (eliminates 14+ background decoders competing for bandwidth).
 *   4. Quality Preference Controller (Auto, 720p HD, 480p Balanced, 360p, 240p Data Saver).
 *   5. Robust HLS-to-MP4 automatic failover and native iOS Safari AVPlayer delegation.
 */

(function () {
    'use strict';

    // ========================================================================
    // 1. SHARED BANDWIDTH MEMORY (PERSISTENT EWMA ACROSS REELS & FEED CARDS)
    // ========================================================================
    const BW_STORAGE_KEY = 'pwaninet_bw_estimate';
    const QUALITY_STORAGE_KEY = 'pwaninet_video_quality';

    const PwaniBandwidthEstimator = {
        _currentBps: null,

        get() {
            if (this._currentBps !== null) return this._currentBps;

            try {
                const stored = parseInt(localStorage.getItem(BW_STORAGE_KEY) || '0', 10);
                if (stored > 100000 && stored < 150000000) {
                    this._currentBps = stored;
                    return this._currentBps;
                }
            } catch (_) {}

            // Seed from Network Information API if available
            const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
            if (conn && typeof conn.downlink === 'number' && conn.downlink > 0) {
                this._currentBps = Math.round(conn.downlink * 1000000 * 0.85);
                return this._currentBps;
            }

            // Default fallback: 3.5 Mbps (fast crisp 720p HD on modern networks)
            this._currentBps = 3500000;
            return this._currentBps;
        },

        update(sampleBps) {
            if (!sampleBps || sampleBps <= 0) return;
            const prev = this.get();
            // Exponentially Weighted Moving Average (70% past, 30% sample)
            this._currentBps = Math.round(0.70 * prev + 0.30 * sampleBps);
            try {
                localStorage.setItem(BW_STORAGE_KEY, String(this._currentBps));
            } catch (_) {}
        }
    };
    window.PwaniBandwidthEstimator = PwaniBandwidthEstimator;

    // ========================================================================
    // 2. QUALITY PREFERENCE CONTROLLER
    // ========================================================================
    const PwaniVideoQualityManager = {
        getPreferredQuality() {
            try {
                return localStorage.getItem(QUALITY_STORAGE_KEY) || 'auto';
            } catch (_) {
                return 'auto';
            }
        },

        setPreferredQuality(quality) {
            try {
                localStorage.setItem(QUALITY_STORAGE_KEY, quality);
            } catch (_) {}

            // Apply immediately to all active HLS video instances in the DOM
            document.querySelectorAll('video').forEach(videoEl => {
                if (videoEl._hlsInstance) {
                    this.applyToHls(videoEl._hlsInstance, quality, videoEl);
                }
            });
            window.dispatchEvent(new CustomEvent('pwaniQualityPreferenceChanged', { detail: { quality } }));
        },

        applyToHls(hls, quality, videoEl = null) {
            if (!hls || !hls.levels || hls.levels.length === 0) return;
            quality = quality || this.getPreferredQuality();

            if (quality === 'auto') {
                hls.currentLevel = -1; // -1 enables automatic ABR
                hls.nextLevel = -1;
                hls.loadLevel = -1;
                hls.autoLevelCapping = -1;
                return;
            }

            const target = parseInt(quality, 10);
            if (isNaN(target)) {
                hls.currentLevel = -1;
                hls.nextLevel = -1;
                return;
            }

            // Match closest rendition based on minor dimension (min(w, h)) or height
            let bestIdx = -1;
            let minDiff = Infinity;
            hls.levels.forEach((lvl, idx) => {
                const minor = Math.min(lvl.width || 9999, lvl.height || 9999);
                const diff = Math.abs(minor - target);
                if (diff < minDiff) {
                    minDiff = diff;
                    bestIdx = idx;
                }
            });

            if (bestIdx !== -1) {
                hls.currentLevel = bestIdx;
                hls.nextLevel = bestIdx;
                hls.loadLevel = bestIdx;
                // Seamless: Do NOT flush forward buffer on quality switch; download future fragments smoothly
            }
        }
    };
    window.PwaniVideoQualityManager = PwaniVideoQualityManager;

    // ========================================================================
    // 3. HLS INITIALIZER PER VIDEO ELEMENT
    // ========================================================================
    function initHLSForElement(videoEl, options = {}) {
        if (!videoEl) return;
        const hlsUrl = videoEl.dataset.hlsUrl;
        if (!hlsUrl) return;

        // Skip if already configured and active
        if (videoEl.dataset.hlsReady === '1' && videoEl._hlsInstance) return;
        videoEl.dataset.hlsReady = '1';

        // Check Safari / iOS native HLS engine
        const isNativeHlsSupported = videoEl.canPlayType('application/vnd.apple.mpegurl');
        const isHlsJsSupported = typeof Hls !== 'undefined' && Hls.isSupported();

        if (!isHlsJsSupported && isNativeHlsSupported) {
            // Safari / iOS native AVPlayer HLS
            if (videoEl.src !== hlsUrl) {
                videoEl.src = hlsUrl;
            }
            return;
        }

        if (!isHlsJsSupported) {
            // Neither native nor HLS.js supported: fallback to MP4
            const fallback = videoEl.dataset.videoUrl;
            if (fallback && videoEl.src !== fallback) {
                videoEl.src = fallback;
            }
            return;
        }

        const estimatedBps = PwaniBandwidthEstimator.get();
        const preferredQuality = PwaniVideoQualityManager.getPreferredQuality();

        // Fast-start strategy:
        // On modern connections (>= 1.2 Mbps), startLevel: -1 selects optimal HD rendition immediately without blur.
        const startLevel = (preferredQuality === 'auto' && estimatedBps >= 1200000) ? -1 : 0;

        const isReel = videoEl.classList.contains('fullscreen-reel-video') ||
                       !!videoEl.closest('#reelsSnapViewport') ||
                       !!videoEl.closest('.reel-video-container');

        const hls = new Hls({
            startLevel: startLevel,
            abrEwmaDefaultEstimate: estimatedBps,
            // Never cap to unmeasured or small player sizes
            capLevelToPlayerSize: false,
            // Short-form reels use compact buffers (12s/16MB) to keep mobile RAM and GPU decoders lean.
            // Long-form feed videos use 30s/64MB.
            maxBufferLength: isReel ? 12 : 30,
            maxMaxBufferLength: isReel ? 20 : 60,
            backBufferLength: isReel ? 6 : 10,
            maxBufferSize: (isReel ? 16 : 64) * 1024 * 1024,
            // Fast segment recovery on cellular fluctuations
            fragLoadingTimeOut: 20000,
            fragLoadingMaxRetry: 5,
            fragLoadingRetryDelay: 600,
            levelLoadingTimeOut: 15000,
            levelLoadingMaxRetry: 4,
            enableWorker: true,
            lowLatencyMode: false,
        });

        hls.loadSource(hlsUrl);
        hls.attachMedia(videoEl);

        hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
            PwaniVideoQualityManager.applyToHls(hls, undefined, videoEl);

            // ONLY resume autoplay if explicitly requested by playback controller
            if (videoEl.dataset.wantsAutoplay === 'true') {
                const vm = window.videoManager || window.PwaniNetVideoManager;
                if (vm && typeof vm.playVideo === 'function') {
                    vm.playVideo(videoEl, true);
                } else {
                    videoEl.play().catch(() => {});
                }
            }
        });

        // Track bandwidth and update cross-video estimator on every loaded fragment
        hls.on(Hls.Events.FRAG_LOADED, (event, data) => {
            if (data && data.stats && data.stats.total && data.stats.loading) {
                const loadTimeSec = (data.stats.loading.end - data.stats.loading.start) / 1000;
                if (loadTimeSec > 0.05) {
                    const sampleBps = Math.round((data.stats.total * 8) / loadTimeSec);
                    PwaniBandwidthEstimator.update(sampleBps);
                }
            }
        });

        // Notify UI of quality switches (e.g. 360p -> 720p HD)
        hls.on(Hls.Events.LEVEL_SWITCHED, (event, data) => {
            const currentLevel = hls.levels[data.level];
            if (currentLevel) {
                const minor = Math.min(currentLevel.width || 0, currentLevel.height || 0);
                const label = `${minor}p${minor >= 720 ? ' HD' : ''}`;
                videoEl.dataset.currentQualityLabel = label;

                window.dispatchEvent(new CustomEvent('pwaniHlsLevelSwitched', {
                    detail: {
                        video: videoEl,
                        levelIndex: data.level,
                        height: currentLevel.height,
                        width: currentLevel.width,
                        bitrate: currentLevel.bitrate,
                        label: label,
                    }
                }));
            }
        });

        let networkRetries = 0;
        let mediaRetries = 0;

        hls.on(Hls.Events.ERROR, (event, data) => {
            if (!data.fatal) return;

            if (data.type === Hls.ErrorTypes.NETWORK_ERROR && networkRetries < 3) {
                networkRetries++;
                console.warn(`[HLS] Network error, recovering (${networkRetries}/3)...`, data);
                hls.startLoad();
            } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR && mediaRetries < 3) {
                mediaRetries++;
                console.warn(`[HLS] Media error, recovering (${mediaRetries}/3)...`, data);
                hls.recoverMediaError();
            } else {
                console.warn('[HLS] Unrecoverable fatal error, falling back to MP4:', data);
                hls.destroy();
                delete videoEl._hlsInstance;
                videoEl.dataset.hlsReady = '';

                const fallbackUrl = videoEl.dataset.videoUrl;
                if (fallbackUrl && videoEl.src !== fallbackUrl) {
                    videoEl.src = fallbackUrl;
                    videoEl.load();
                    if (videoEl.dataset.wantsAutoplay === 'true') {
                        videoEl.play().catch(() => {});
                    }
                }
            }
        });

        videoEl._hlsInstance = hls;
    }

    // ========================================================================
    // 4. VIEWPORT-AWARE LAZY INITIALIZATION (ZERO BACKGROUND COMPETITION)
    // ========================================================================
    let hlsIntersectionObserver = null;

    function destroyHLSForElement(videoEl) {
        if (!videoEl) return;
        if (videoEl._hlsInstance) {
            try {
                videoEl._hlsInstance.destroy();
            } catch (_) {}
            delete videoEl._hlsInstance;
        }
        videoEl.dataset.hlsReady = '';
        try {
            videoEl.removeAttribute('src');
            try { videoEl.src = ''; } catch (_) {}
            while (videoEl.firstChild) {
                videoEl.removeChild(videoEl.firstChild);
            }
            videoEl.load();
        } catch (_) {}
    }
    window.destroyHLSForElement = destroyHLSForElement;

    function createLazyHlsObserver() {
        if (hlsIntersectionObserver) return hlsIntersectionObserver;

        hlsIntersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const video = entry.target;
                if (entry.isIntersecting) {
                    // Do not eagerly load shelf carousel preview videos until clicked/focused
                    if (!video.classList.contains('reels-carousel-video') && !video.closest('.reels-carousel-shelf')) {
                        initHLSForElement(video);
                        if (video._hlsInstance && typeof video._hlsInstance.startLoad === 'function') {
                            video._hlsInstance.startLoad();
                        }
                    }
                } else {
                    // When feed video scrolls out of the 600px margin, pause HLS buffer loading to conserve network & memory
                    if (video._hlsInstance && typeof video._hlsInstance.stopLoad === 'function') {
                        video._hlsInstance.stopLoad();
                    }
                }
            });
        }, {
            root: null,
            rootMargin: '600px 0px', // Attach HLS when 600px near viewport
            threshold: 0.05
        });

        return hlsIntersectionObserver;
    }

    function initHLSInSubtree(root) {
        if (!root || !root.querySelectorAll) return;
        const observer = createLazyHlsObserver();
        const videos = root.querySelectorAll('video[data-hls-url]');

        videos.forEach(video => {
            // Fullscreen snap items are managed EXCLUSIVELY by VideoManager (only active N and preloaded N+1 attach)
            // DO NOT eagerly attach HLS to all fullscreen reel videos, which causes decoder and network exhaustion!
            if (video.classList.contains('fullscreen-reel-video') || video.closest('#reelsSnapViewport')) {
                return;
            }
            if (observer) {
                observer.observe(video);
            } else {
                initHLSForElement(video);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initHLSInSubtree(document));
    } else {
        initHLSInSubtree(document);
    }

    const domObserver = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    // Fullscreen reels and snap viewport manage their own media engines;
                    // skip subtree traversal inside them to eliminate main-thread stutter during streaming.
                    if (node.id === 'reelsSnapViewport' || node.id === 'fullscreenReelsOverlay' ||
                        (typeof node.closest === 'function' && node.closest('#reelsSnapViewport, #fullscreenReelsOverlay'))) {
                        continue;
                    }
                    if (node.matches && node.matches('video[data-hls-url]')) {
                        if (!node.classList.contains('fullscreen-reel-video') && !node.closest('#reelsSnapViewport')) {
                            initHLSInSubtree(node.parentElement || node);
                        }
                    } else {
                        initHLSInSubtree(node);
                    }
                }
            }
        }
    });

    domObserver.observe(document.body, { childList: true, subtree: true });

    document.addEventListener('htmx:afterSwap', (evt) => {
        initHLSInSubtree(evt.detail.target || document);
    });

    window.initHLSForElement = initHLSForElement;
    window.initHLSInSubtree  = initHLSInSubtree;
})();
