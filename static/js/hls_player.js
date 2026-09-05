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
                maxMaxBufferLength:   120,
                startLevel:          -1,
                capLevelToPlayerSize: true,
            });

            hls.loadSource(hlsUrl);
            hls.attachMedia(videoEl);

            hls.on(Hls.Events.ERROR, (event, data) => {
                if (data.fatal) {
                    console.warn('[HLS] Fatal error, falling back to MP4:', data);
                    hls.destroy();
                    videoEl.dataset.hlsReady = '';
                }
            });

            videoEl._hlsInstance = hls;

        } else if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
            // Safari / iOS native HLS
            videoEl.src = hlsUrl;
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
