/**
 * PwaniNet Share Manager
 * Unified sharing layer that works across:
 *  1. Capacitor native app  → @capacitor/share plugin  → OS share sheet
 *  2. Mobile browser / PWA  → navigator.share()        → OS share sheet
 *  3. Desktop browser       → platform link buttons     → WhatsApp web, Telegram, X
 *
 * Usage:
 *   window.pwaniShare(path, text)
 *   window.pwaniShareInit()   — called once on load to reveal the right UI
 */

(function () {
    'use strict';

    /* ── Helpers ───────────────────────────────────────────────────────── */

    function isCapacitor() {
        return !!(window.Capacitor && window.Capacitor.Plugins);
    }

    function hasCapacitorShare() {
        return isCapacitor() && !!(window.Capacitor.Plugins.Share);
    }

    function hasWebShare() {
        return !!(navigator && navigator.share);
    }

    function buildAbsoluteUrl(path) {
        if (!path) return window.location.href;
        if (path.startsWith('http://') || path.startsWith('https://')) return path;
        return window.location.origin + path;
    }

    function buildPlatformLinks(url, text) {
        var encodedUrl  = encodeURIComponent(url);
        var encodedText = encodeURIComponent(text || 'Check this out on PwaniNet!');
        return {
            whatsapp: 'https://wa.me/?text=' + encodedText + '%20' + encodedUrl,
            telegram: 'https://t.me/share/url?url=' + encodedUrl + '&text=' + encodedText,
            twitter:  'https://twitter.com/intent/tweet?text=' + encodedText + '&url=' + encodedUrl,
        };
    }

    /* ── Core share function ───────────────────────────────────────────── */

    /**
     * Share a post URL. Tries Capacitor → navigator.share → opens platform links.
     * @param {string} path     - Relative or absolute URL to the post
     * @param {string} [text]   - Optional description/preview text
     */
    async function pwaniShare(path, text) {
        var url   = buildAbsoluteUrl(path);
        var title = 'PwaniNet';
        var body  = text || 'Check this out on PwaniNet!';

        // 1. Capacitor native share sheet (highest fidelity on Android/iOS)
        if (hasCapacitorShare()) {
            try {
                await window.Capacitor.Plugins.Share.share({
                    title: title,
                    text: body,
                    url:  url,
                    dialogTitle: 'Share via',
                });
                return;
            } catch (err) {
                // User cancelled or plugin error — fall through
                if (err && err.message && err.message.toLowerCase().includes('cancel')) return;
            }
        }

        // 2. Web Share API (mobile browsers / installed PWA)
        if (hasWebShare()) {
            try {
                await navigator.share({ title: title, text: body, url: url });
                return;
            } catch (err) {
                if (err && err.name === 'AbortError') return; // User cancelled
            }
        }

        // 3. Fallback: open WhatsApp web (works everywhere, especially desktop)
        var links = buildPlatformLinks(url, body);
        // Try AndroidBridge for Capacitor without Share plugin (opens external browser)
        var bridge = window.AndroidBridge || window.PwaninetBridge;
        if (bridge && typeof bridge.openExternalUrl === 'function') {
            bridge.openExternalUrl(links.whatsapp);
        } else {
            window.open(links.whatsapp, '_blank', 'noopener,noreferrer');
        }
    }

    /* ── UI initialisation ─────────────────────────────────────────────── */

    /**
     * Reveal the correct share UI elements in all share modals on the page.
     * Called once on load (and on htmx:afterSettle for dynamically injected cards).
     */
    function initShareButtons() {
        var canNativeShare = hasCapacitorShare() || hasWebShare();

        // Native share buttons: show if share API is available
        document.querySelectorAll('[id^="native-share-btn-"]').forEach(function (btn) {
            if (canNativeShare) {
                btn.classList.remove('d-none');
            }
        });

        // Platform fallback links: show on desktop (no share API)
        document.querySelectorAll('[id^="platform-share-links-"]').forEach(function (container) {
            if (!canNativeShare) {
                container.classList.remove('d-none');
            }
        });

        // Wire up platform link hrefs
        document.querySelectorAll('.platform-share-btn').forEach(function (btn) {
            var shareUrl = btn.dataset.shareUrl;
            if (!shareUrl) return;
            var platform = btn.dataset.platform;
            var links = buildPlatformLinks(shareUrl, 'Check this out on PwaniNet!');
            if (links[platform]) {
                btn.href = links[platform];
                // In Capacitor: intercept click and use openExternalUrl bridge
                if (isCapacitor()) {
                    btn.addEventListener('click', function (e) {
                        e.preventDefault();
                        var bridge = window.AndroidBridge || window.PwaninetBridge;
                        if (bridge && typeof bridge.openExternalUrl === 'function') {
                            bridge.openExternalUrl(links[platform]);
                        } else {
                            window.open(links[platform], '_blank', 'noopener,noreferrer');
                        }
                    });
                }
            }
        });
    }

    /* ── Bootstrap ─────────────────────────────────────────────────────── */

    // Expose globals
    window.pwaniShare     = pwaniShare;
    window.pwaniShareInit = initShareButtons;

    // Run on initial page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initShareButtons);
    } else {
        initShareButtons();
    }

    // Re-run whenever HTMX injects new content (e.g. infinite scroll / SPA navigation)
    document.addEventListener('htmx:afterSettle', initShareButtons);

}());
