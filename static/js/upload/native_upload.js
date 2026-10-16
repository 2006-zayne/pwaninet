/**
 * NativeUploads — Phase 4 JS bridge to the UploadManager Capacitor plugin.
 *
 * On Android the worker owns the bytes (app-private staging) and survives
 * app close, process kill, and reboot. On web it delegates to the Phase 3
 * ResumableUpload engine. Both sides speak the same /api/uploads/ contract.
 */
(function () {
    'use strict';

    function plugin() {
        const cap = window.Capacitor;
        if (!cap || typeof cap.isNativePlatform !== 'function' || !cap.isNativePlatform()) {
            return null;
        }
        const plugins = cap.Plugins || {};
        if (plugins.UploadManager) return plugins.UploadManager;
        // Capacitor 8+ custom-plugin access path.
        if (cap.Plugins && cap.registerPlugin) {
            try {
                return cap.registerPlugin('UploadManager');
            } catch (_) {
                return null;
            }
        }
        return null;
    }

    const NativeUploads = {
        isAvailable() {
            return !!plugin();
        },

        /** Hand a web-engine session to the native worker (bytes staged natively). */
        async enqueueNative(record, file, post, fileUri) {
            const p = plugin();
            if (!p) throw new Error('Native upload plugin unavailable');
            return p.ensureUpload({
                serverId: record.id,
                clientUploadId: record.client_upload_id,
                fileUri: fileUri || null,
                fileName: record.filename,
                mimeType: record.mime_type || (file && file.type) || '',
                fileSize: record.total_bytes || (file && file.size) || 0,
                partSize: record.session_part_size || 8388608,
                totalParts: record.session_total_parts || 1,
                protocol: record.session_protocol || 's3-multipart',
                baseUrl: window.location.origin,
                postContent: (post && post.content) || '',
                postVisibility: (post && post.visibility) || 'AUTHENTICATED',
            });
        },

        async getStatus(clientUploadId) {
            const p = plugin();
            if (!p) throw new Error('Native upload plugin unavailable');
            return p.getStatus({ clientUploadId });
        },

        async cancel(clientUploadId) {
            const p = plugin();
            if (!p) throw new Error('Native upload plugin unavailable');
            return p.cancelUpload({ clientUploadId });
        },

        /** Post-restart sweep: re-enqueue staged jobs with no live worker. */
        async resumePending() {
            const p = plugin();
            if (!p) return { resumed: 0, native: false };
            try {
                const ret = await p.resumePending();
                return { resumed: (ret && ret.resumed) || 0, native: true };
            } catch (_) {
                return { resumed: 0, native: true };
            }
        },
    };

    window.NativeUploads = NativeUploads;

    // On launch inside the native app, sweep staged jobs before the web
    // engine starts its own resume pass.
    document.addEventListener('DOMContentLoaded', () => {
        if (window.Capacitor && typeof window.Capacitor.isNativePlatform === 'function'
                && window.Capacitor.isNativePlatform()) {
            NativeUploads.resumePending().catch(() => {});
        }
    });
})();
