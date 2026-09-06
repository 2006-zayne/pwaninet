/**
 * HLS Player Initialiser
 *
 * Scans the page for <video data-hls-url="…"> elements and sets up
 * adaptive bitrate streaming via hls.js.
 *
 * Browser matrix:
 *   - Chromium / Firefox / Android: hls.js loads the HLS master playlist.
 *   - Safari / iOS:                 native HLS is used (hls.js defers to it).
 *   - No HLS data attribute:        element plays as plain MP4 (backward compat).
 *
 * The MutationObserver at the bottom re-runs initHLSForElement whenever
 * HTMX or the infinite-scroll loader injects new post cards.
 */

(function () {
    'use strict';

    function initHLSForElement(videoEl) {
        const hlsUrl = videoEl.dataset.hlsUrl;
        if (!hlsUrl || videoEl.dataset.hlsReady) return;
        videoEl.dataset.hlsReady = '1';

        if (typeof Hls === 'undefined') return;

        if (Hls.isSupported()) {
            const hls = new Hls({
                // Fast-start on poor connections: start on lowest rendition (240p/360p)
                startLevel:             0,
                abrEwmaDefaultEstimate: 400000, // 400 kbps initial estimate
                capLevelToPlayerSize:   true,   // Limit resolution to element display size

                // Feed-optimized buffering: prevents bandwidth waste & memory bloat
                maxBufferLength:        12,     // 12s forward buffer
                maxMaxBufferLength:     24,     // 24s max buffer
                backBufferLength:       10,     // Evict watched segments to preserve RAM
                maxBufferSize:          30 * 1024 * 1024, // 30 MB max buffer size

                // Network resilience for fluctuating connections
                fragLoadingTimeOut:     20000,  // 20s timeout before segment retry
                fragLoadingMaxRetry:    5,      // Up to 5 retries on flaky cellular
                fragLoadingRetryDelay:  1000,
                levelLoadingTimeOut:    15000,
                levelLoadingMaxRetry:   4,
            });

            hls.loadSource(hlsUrl);
            hls.attachMedia(videoEl);

            let networkRetries = 0;
            let mediaRetries = 0;

            hls.on(Hls.Events.ERROR, (event, data) => {
                if (!data.fatal) return;

                if (data.type === Hls.ErrorTypes.NETWORK_ERROR && networkRetries < 3) {
                    networkRetries++;
                    console.warn(`[HLS] Fatal network error. Recovering (${networkRetries}/3)...`, data);
                    hls.startLoad();
                } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR && mediaRetries < 3) {
                    mediaRetries++;
                    console.warn(`[HLS] Fatal media error. Recovering (${mediaRetries}/3)...`, data);
                    hls.recoverMediaError();
                } else {
                    console.warn('[HLS] Unrecoverable fatal error, falling back to MP4:', data);
                    hls.destroy();
                    delete videoEl._hlsInstance;
                    videoEl.dataset.hlsReady = '';

                    // Fall back cleanly to MP4 if fallback URL exists
                    const fallbackUrl = videoEl.dataset.videoUrl;
                    if (fallbackUrl) {
                        videoEl.src = fallbackUrl;
                        videoEl.load();
                        videoEl.play().catch(() => {});
                    }
                }
            });

            videoEl._hlsInstance = hls;

        } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari / iOS native HLS
            if (videoEl.src !== hlsUrl) {
                videoEl.src = hlsUrl;
            }
        }
    }

    function initHLSInSubtree(root) {
        const videos = root.querySelectorAll
            ? root.querySelectorAll('video[data-hls-url]')
            : [];
        videos.forEach(initHLSForElement);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => initHLSInSubtree(document));
    } else {
        initHLSInSubtree(document);
    }

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    if (node.matches('video[data-hls-url]')) initHLSForElement(node);
                    initHLSInSubtree(node);
                }
            }
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });

    document.addEventListener('htmx:afterSwap', (evt) => {
        initHLSInSubtree(evt.detail.target || document);
    });

    window.initHLSForElement = initHLSForElement;
    window.initHLSInSubtree  = initHLSInSubtree;
})();
