/**
 * DeviceMediaStore - Unified Local Storage for Chat Media
 * Coordinates:
 *   - Native Capacitor direct-to-disk storage (@capacitor/filesystem on Android / iOS)
 *   - Web / Desktop IndexedDB binary Blob storage (pwaninet_downloads_v1)
 *   - Persistent storage protection via navigator.storage.persist()
 *   - Local source resolution (Capacitor.convertFileSrc vs URL.createObjectURL)
 *   - Browser blob downloads to disk for desktop users
 */

import { downloadStorage } from '../../downloads/download_storage.js';

class DeviceMediaStore {
    constructor() {
        this.storage = downloadStorage;
        this.isInitialized = false;
        this.blobUrlCache = new Map(); // messageId -> objectUrl
    }

    /**
     * Check if running in native Capacitor environment with Filesystem plugin
     */
    isNative() {
        return typeof window !== 'undefined' &&
               Boolean(window.Capacitor && 
                       typeof window.Capacitor.isNativePlatform === 'function' &&
                       window.Capacitor.isNativePlatform() &&
                       window.Capacitor.Plugins &&
                       window.Capacitor.Plugins.Filesystem);
    }

    /**
     * Initialize media storage and request persistent quota on Web
     */
    async init() {
        if (this.isInitialized) return;

        // Request persistent storage on Web/PWA to prevent browser eviction
        if (typeof navigator !== 'undefined' && navigator.storage && typeof navigator.storage.persist === 'function') {
            try {
                const isPersisted = await navigator.storage.persisted();
                if (!isPersisted) {
                    const granted = await navigator.storage.persist();
                    console.log('[DEVICE_MEDIA_STORE] Persistent storage requested, granted:', granted);
                }
            } catch (e) {
                console.warn('[DEVICE_MEDIA_STORE] Storage persist request failed:', e);
            }
        }

        try {
            await this.storage.init();
            this.isInitialized = true;
            console.log('[DEVICE_MEDIA_STORE] Initialized. Native platform:', this.isNative());
        } catch (err) {
            console.error('[DEVICE_MEDIA_STORE] Init failed:', err);
        }
    }

    /**
     * Check if a message's media is already downloaded or stored locally
     */
    hasMedia(messageId) {
        if (!messageId) return false;
        try {
            return localStorage.getItem(`media_dl_${messageId}`) === 'true';
        } catch (_) {
            return false;
        }
    }

    /**
     * Save sender's original media blob locally so they never have to download what they sent
     */
    async saveSenderMedia(tempId, blob, filename = 'media') {
        if (!tempId || !blob) return null;
        await this.init();

        try {
            const safeKey = `chat_${tempId}`;
            if (this.isNative()) {
                // On Capacitor, write directly to native app data directory
                const { Filesystem } = window.Capacitor.Plugins;
                const Directory = window.Capacitor.Plugins.Filesystem.Directory || { Data: 'DATA' };
                const safeName = filename.replace(/[^a-zA-Z0-9._-]/g, '_');
                const relativePath = `pwaninet_chat_media/${tempId}_${safeName}`;

                try {
                    await Filesystem.mkdir({
                        path: 'pwaninet_chat_media',
                        directory: Directory.Data,
                        recursive: true
                    });
                } catch (_) {}

                // Convert blob to base64 for native write
                const reader = new FileReader();
                const base64Data = await new Promise((resolve, reject) => {
                    reader.onloadend = () => {
                        const res = reader.result;
                        const base64 = typeof res === 'string' ? res.split(',')[1] : '';
                        resolve(base64);
                    };
                    reader.onerror = reject;
                    reader.readAsDataURL(blob);
                });

                await Filesystem.writeFile({
                    path: relativePath,
                    data: base64Data,
                    directory: Directory.Data,
                    recursive: true
                });

                const uriRes = await Filesystem.getUri({
                    path: relativePath,
                    directory: Directory.Data
                });

                await this.storage.saveMetadata({
                    id: safeKey,
                    isNative: true,
                    nativePath: relativePath,
                    nativeUri: uriRes.uri,
                    filename: safeName,
                    size: blob.size,
                    downloadedAt: Date.now()
                });

                localStorage.setItem(`media_dl_${tempId}`, 'true');
                return window.Capacitor.convertFileSrc(uriRes.uri);
            } else {
                // On Web, save binary blob directly into IndexedDB
                await this.storage.saveBlob(safeKey, blob);
                await this.storage.saveMetadata({
                    id: safeKey,
                    isNative: false,
                    filename,
                    size: blob.size,
                    downloadedAt: Date.now()
                });

                const objUrl = URL.createObjectURL(blob);
                this.blobUrlCache.set(String(tempId), objUrl);
                localStorage.setItem(`media_dl_${tempId}`, 'true');
                return objUrl;
            }
        } catch (err) {
            console.error('[DEVICE_MEDIA_STORE] Save sender media error:', err);
            return null;
        }
    }

    /**
     * Transfer stored media from optimistic tempId to permanent messageId
     */
    async rekeyMedia(tempId, messageId) {
        if (!tempId || !messageId || tempId === messageId) return;
        await this.init();

        try {
            const oldKey = `chat_${tempId}`;
            const newKey = `chat_${messageId}`;

            const meta = await this.storage.getMetadata(oldKey);
            if (meta) {
                meta.id = newKey;
                await this.storage.saveMetadata(meta);
            }

            const blob = await this.storage.getBlob(oldKey);
            if (blob) {
                await this.storage.saveBlob(newKey, blob);
            }

            // Update in-memory cache
            if (this.blobUrlCache.has(String(tempId))) {
                this.blobUrlCache.set(String(messageId), this.blobUrlCache.get(String(tempId)));
            }

            localStorage.setItem(`media_dl_${messageId}`, 'true');
        } catch (err) {
            console.warn('[DEVICE_MEDIA_STORE] Rekey media error:', err);
        }
    }

    /**
     * Download media from CDN/server and save permanently to local device storage
     */
    async downloadMedia(messageId, url, filename = 'download') {
        if (!url) throw new Error('Download URL is required');
        await this.init();

        const safeKey = `chat_${messageId}`;
        const safeFilename = (filename || 'download').replace(/[^a-zA-Z0-9._-]/g, '_');

        if (this.isNative()) {
            // Native Capacitor direct-to-disk background download
            const { Filesystem } = window.Capacitor.Plugins;
            const Directory = window.Capacitor.Plugins.Filesystem.Directory || { Data: 'DATA' };
            const relativePath = `pwaninet_chat_media/${messageId}_${safeFilename}`;

            try {
                await Filesystem.mkdir({
                    path: 'pwaninet_chat_media',
                    directory: Directory.Data,
                    recursive: true
                });
            } catch (_) {}

            const absoluteUrl = new URL(url, window.location.href).href;
            await Filesystem.downloadFile({
                url: absoluteUrl,
                path: relativePath,
                directory: Directory.Data,
                recursive: true
            });

            const uriRes = await Filesystem.getUri({
                path: relativePath,
                directory: Directory.Data
            });

            await this.storage.saveMetadata({
                id: safeKey,
                isNative: true,
                nativePath: relativePath,
                nativeUri: uriRes.uri,
                url,
                filename: safeFilename,
                downloadedAt: Date.now()
            });

            localStorage.setItem(`media_dl_${messageId}`, 'true');
            return window.Capacitor.convertFileSrc(uriRes.uri);
        } else {
            // Web / Desktop IndexedDB blob download
            const res = await fetch(url, { mode: 'cors' });
            if (!res.ok) throw new Error(`HTTP ${res.status} fetching media`);

            const blob = await res.blob();
            await this.storage.saveBlob(safeKey, blob);
            await this.storage.saveMetadata({
                id: safeKey,
                isNative: false,
                url,
                filename: safeFilename,
                size: blob.size,
                downloadedAt: Date.now()
            });

            const objUrl = URL.createObjectURL(blob);
            this.blobUrlCache.set(String(messageId), objUrl);
            localStorage.setItem(`media_dl_${messageId}`, 'true');
            return objUrl;
        }
    }

    /**
     * Get local source URL for a media item if stored locally
     */
    async getLocalMediaUrl(messageId) {
        if (!messageId) return null;
        if (this.blobUrlCache.has(String(messageId))) {
            return this.blobUrlCache.get(String(messageId));
        }

        await this.init();
        const safeKey = `chat_${messageId}`;

        try {
            const meta = await this.storage.getMetadata(safeKey);
            if (meta && meta.isNative && meta.nativeUri) {
                if (window.Capacitor && typeof window.Capacitor.convertFileSrc === 'function') {
                    return window.Capacitor.convertFileSrc(meta.nativeUri);
                }
                return meta.nativeUri;
            }

            const blob = await this.storage.getBlob(safeKey);
            if (blob) {
                const objUrl = URL.createObjectURL(blob);
                this.blobUrlCache.set(String(messageId), objUrl);
                return objUrl;
            }
        } catch (e) {
            console.warn('[DEVICE_MEDIA_STORE] Get local media error:', e);
        }

        return null;
    }

    /**
     * Download to Desktop / Mobile Device Disk (Chrome blob download or native share)
     * Triggers file download straight into the user's Downloads folder
     */
    async downloadToDevice(blobOrUrl, filename = 'download') {
        const safeFilename = filename.replace(/[^a-zA-Z0-9._-]/g, '_');

        if (this.isNative()) {
            // Native Capacitor: share sheet or save
            if (window.Capacitor.Plugins && window.Capacitor.Plugins.Share) {
                try {
                    await window.Capacitor.Plugins.Share.share({
                        title: safeFilename,
                        url: typeof blobOrUrl === 'string' ? blobOrUrl : undefined
                    });
                    return;
                } catch (e) {
                    console.warn('[DEVICE_MEDIA_STORE] Native share failed:', e);
                }
            }
        }

        // Desktop / Web: Chrome blob download to user's PC Downloads folder
        try {
            let blobUrl = '';
            let shouldRevoke = false;

            if (blobOrUrl instanceof Blob) {
                blobUrl = URL.createObjectURL(blobOrUrl);
                shouldRevoke = true;
            } else if (typeof blobOrUrl === 'string') {
                if (blobOrUrl.startsWith('blob:')) {
                    blobUrl = blobOrUrl;
                } else {
                    const res = await fetch(blobOrUrl, { mode: 'cors' });
                    const blob = await res.blob();
                    blobUrl = URL.createObjectURL(blob);
                    shouldRevoke = true;
                }
            }

            if (!blobUrl) return;

            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = blobUrl;
            a.download = safeFilename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            if (shouldRevoke) {
                setTimeout(() => URL.revokeObjectURL(blobUrl), 2000);
            }
        } catch (err) {
            console.error('[DEVICE_MEDIA_STORE] Download to device failed:', err);
            // Fallback: standard link navigation
            if (typeof blobOrUrl === 'string') {
                window.open(blobOrUrl, '_blank');
            }
        }
    }
}

export const deviceMediaStore = new DeviceMediaStore();
