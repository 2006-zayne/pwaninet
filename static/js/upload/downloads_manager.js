/**
 * Downloads Manager
 * 
 * Manages PwaniNet-managed downloads using Origin Private File System (OPFS)
 * when available, with IndexedDB Blob storage as fallback.
 * Maintains metadata in IndexedDB.
 * Supports Images, Videos, and Documents.
 * Each download supports Open, Delete, Share, Search, and Sorting.
 */

import { uploadEvents, UploadEventNames } from './upload_events.js';
import { downloadsMetadataManager } from './indexeddb_manager.js';

class DownloadsManager {
    constructor() {
        this.opfsRoot = null;
        this.useOPFS = false;
        this.isInitialized = false;
    }

    /**
     * Initialize the downloads manager
     */
    async initialize() {
        if (this.isInitialized) return;

        // Check if OPFS is available
        if ('storage' in navigator && 'getDirectory' in navigator.storage) {
            try {
                this.opfsRoot = await navigator.storage.getDirectory();
                this.useOPFS = true;
            } catch (error) {
                console.warn('OPFS not available, falling back to IndexedDB:', error);
                this.useOPFS = false;
            }
        }

        this.isInitialized = true;
    }

    /**
     * Check if OPFS is supported
     * @returns {boolean}
     */
    static isOPFSSupported() {
        return 'storage' in navigator && 'getDirectory' in navigator.storage;
    }

    /**
     * Check if IndexedDB is supported
     * @returns {boolean}
     */
    static isIndexedDBSupported() {
        return 'indexedDB' in window;
    }

    /**
     * Download a file
     * @param {string} url - File URL
     * @param {object} metadata - Download metadata
     * @param {string} metadata.postId - Post ID
     * @param {string} metadata.mediaType - Media type ('image', 'video', 'audio', 'document')
     * @param {string} metadata.filename - File name
     * @param {string} metadata.category - Category ('image', 'video', 'audio', 'document')
     * @returns {Promise<string>} Download ID
     */
    async download(url, metadata = {}) {
        await this.initialize();

        const { postId, mediaType, filename, category } = metadata;

        try {
            // Fetch the file
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch file: ${response.statusText}`);
            }

            const blob = await response.blob();
            const size = blob.size;
            const mimeType = blob.type;

            // Generate filename if not provided
            const finalFilename = filename || url.split('/').pop() || `download_${Date.now()}`;

            // Save file
            let fileHandle;
            const isNative = window.hasOwnProperty('Capacitor');

            if (isNative && window.Capacitor.Plugins.Filesystem) {
                fileHandle = await this.saveToNative(finalFilename, blob);
            } else if (this.useOPFS) {
                fileHandle = await this.saveToOPFS(finalFilename, blob);
            } else {
                fileHandle = await this.saveToIndexedDB(finalFilename, blob);
            }

            // Save metadata
            const downloadId = await downloadsMetadataManager.addDownload({
                url,
                type: mediaType || 'document',
                filename: finalFilename,
                size,
                mimeType,
                postId,
                category: category || mediaType || 'document',
                downloadedAt: Date.now(),
            });

            uploadEvents.emit(UploadEventNames.DOWNLOAD_COMPLETED, {
                downloadId,
                filename,
                size,
                type,
            });

            return downloadId;
        } catch (error) {
            console.error('Download failed:', error);
            uploadEvents.emit(UploadEventNames.DOWNLOAD_FAILED, {
                url,
                error: error.message,
            });
            throw error;
        }
    }

    /**
     * Save file to Native Downloads folder (Capacitor only)
     * @param {string} filename - File name
     * @param {Blob} blob - File blob
     * @returns {Promise<string>} File path or name
     */
    async saveToNative(filename, blob) {
        try {
            const { Filesystem } = window.Capacitor.Plugins;
            const { Directory } = window.Capacitor.Plugins.Filesystem;

            // Convert blob to base64
            const reader = new FileReader();
            const base64Data = await new Promise((resolve, reject) => {
                reader.onload = () => {
                    const base64String = reader.result.split(',')[1];
                    resolve(base64String);
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });

            const result = await Filesystem.writeFile({
                path: filename,
                data: base64Data,
                directory: Directory.Documents, // Using Documents as primary user-visible storage
                recursive: true
            });

            console.log('[DownloadsManager] File saved to native storage:', result.uri);
            return result.uri;
        } catch (error) {
            console.error('Failed to save to native storage:', error);
            // Fallback to OPFS or IndexedDB if native fails
            if (this.useOPFS) return await this.saveToOPFS(filename, blob);
            return await this.saveToIndexedDB(filename, blob);
        }
    }

    /**
     * Save file to OPFS
     * @param {string} filename - File name
     * @param {Blob} blob - File blob
     * @returns {Promise<string>} File handle
     */
    async saveToOPFS(filename, blob) {
        try {
            const fileHandle = await this.opfsRoot.getFileHandle(filename, { create: true });
            const writable = await fileHandle.createWritable();
            await writable.write(blob);
            await writable.close();
            return fileHandle.name;
        } catch (error) {
            console.error('Failed to save to OPFS:', error);
            throw error;
        }
    }

    /**
     * Save file to IndexedDB
     * @param {string} filename - File name
     * @param {Blob} blob - File blob
     * @returns {Promise<string>} File ID
     */
    async saveToIndexedDB(filename, blob) {
        const fileId = `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Store in a separate IndexedDB store for blobs
        const db = await this.openBlobDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(['blobs'], 'readwrite');
            const store = transaction.objectStore('blobs');
            const request = store.put({ id: fileId, filename, blob });

            request.onsuccess = () => resolve(fileId);
            request.onerror = () => reject(new Error('Failed to save blob to IndexedDB'));
        });
    }

    /**
     * Open IndexedDB for blob storage
     * @returns {Promise<IDBDatabase>}
     */
    async openBlobDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('PwaniNetDownloads', 1);

            request.onerror = () => reject(new Error('Failed to open IndexedDB'));
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('blobs')) {
                    const store = db.createObjectStore('blobs', { keyPath: 'id' });
                    store.createIndex('filename', 'filename', { unique: true });
                }
            };
        });
    }

    /**
     * Open a downloaded file
     * @param {string} downloadId - Download ID
     * @returns {Promise<void>}
     */
    async open(downloadId) {
        await this.initialize();

        const metadata = await downloadsMetadataManager.getDownload(downloadId);
        if (!metadata) {
            throw new Error('Download not found');
        }

        try {
            let blob;
            const isNative = window.hasOwnProperty('Capacitor');

            if (this.useOPFS) {
                blob = await this.getFromOPFS(metadata.filename);
            } else {
                blob = await this.getFromIndexedDB(metadata.filename);
            }

            // If we have a blob and we're on mobile, we might want to "Share" instead of just opening
            if (isNative && window.Capacitor.Plugins.Filesystem) {
                // For native, we often prefer the system share sheet for "Opening" a file
                try {
                    await this.share(downloadId);
                    return;
                } catch (e) {
                    console.warn('[DownloadsManager] Native share failed, falling back to URL open', e);
                }
            }

            // Handle different media types
            const url = URL.createObjectURL(blob);
            const type = metadata.type || metadata.category || 'document';

            if (type === 'image') {
                // Open image in new tab
                window.open(url, '_blank');
            } else if (type === 'video') {
                // Open video in new tab
                window.open(url, '_blank');
            } else if (type === 'audio') {
                // Open audio in new tab
                window.open(url, '_blank');
            } else if (type === 'document') {
                // Download document
                const a = document.createElement('a');
                a.href = url;
                a.download = metadata.filename;
                a.click();
                URL.revokeObjectURL(url);
            } else {
                // Default: download
                const a = document.createElement('a');
                a.href = url;
                a.download = metadata.filename;
                a.click();
                URL.revokeObjectURL(url);
            }

        } catch (error) {
            console.error('Failed to open file:', error);
            throw error;
        }
    }

    /**
     * Get file from OPFS
     * @param {string} filename - File name
     * @returns {Promise<Blob>}
     */
    async getFromOPFS(filename) {
        try {
            const fileHandle = await this.opfsRoot.getFileHandle(filename);
            const file = await fileHandle.getFile();
            return file;
        } catch (error) {
            console.error('Failed to get from OPFS:', error);
            throw error;
        }
    }

    /**
     * Get file from IndexedDB
     * @param {string} filename - File name
     * @returns {Promise<Blob>}
     */
    async getFromIndexedDB(filename) {
        const db = await this.openBlobDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(['blobs'], 'readonly');
            const store = transaction.objectStore('blobs');
            const index = store.index('filename');
            const request = index.get(filename);

            request.onsuccess = () => {
                if (request.result) {
                    resolve(request.result.blob);
                } else {
                    reject(new Error('File not found in IndexedDB'));
                }
            };
            request.onerror = () => reject(new Error('Failed to get blob from IndexedDB'));
        });
    }

    /**
     * Delete a downloaded file
     * @param {string} downloadId - Download ID
     * @returns {Promise<void>}
     */
    async delete(downloadId) {
        await this.initialize();

        const metadata = await downloadsMetadataManager.getDownload(downloadId);
        if (!metadata) {
            throw new Error('Download not found');
        }

        try {
            // Delete file
            if (this.useOPFS) {
                await this.deleteFromOPFS(metadata.filename);
            } else {
                await this.deleteFromIndexedDB(metadata.filename);
            }

            // Delete metadata
            await downloadsMetadataManager.deleteDownload(downloadId);

            uploadEvents.emit(UploadEventNames.DOWNLOAD_DELETED, {
                downloadId,
                filename: metadata.filename,
            });

        } catch (error) {
            console.error('Failed to delete file:', error);
            throw error;
        }
    }

    /**
     * Delete file from OPFS
     * @param {string} filename - File name
     * @returns {Promise<void>}
     */
    async deleteFromOPFS(filename) {
        try {
            await this.opfsRoot.removeEntry(filename);
        } catch (error) {
            console.error('Failed to delete from OPFS:', error);
            throw error;
        }
    }

    /**
     * Delete file from IndexedDB
     * @param {string} filename - File name
     * @returns {Promise<void>}
     */
    async deleteFromIndexedDB(filename) {
        const db = await this.openBlobDB();
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction(['blobs'], 'readwrite');
            const store = transaction.objectStore('blobs');
            const index = store.index('filename');
            const request = index.openCursor(filename);

            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    cursor.delete();
                    resolve();
                } else {
                    reject(new Error('File not found in IndexedDB'));
                }
            };
            request.onerror = () => reject(new Error('Failed to delete blob from IndexedDB'));
        });
    }

    /**
     * Share a downloaded file
     * @param {string} downloadId - Download ID
     * @returns {Promise<void>}
     */
    async share(downloadId) {
        await this.initialize();

        const metadata = await downloadsMetadataManager.getDownload(downloadId);
        if (!metadata) {
            throw new Error('Download not found');
        }

        if (!navigator.share) {
            throw new Error('Web Share API not supported');
        }

        try {
            let blob;

            if (this.useOPFS) {
                blob = await this.getFromOPFS(metadata.filename);
            } else {
                blob = await this.getFromIndexedDB(metadata.filename);
            }

            const file = new File([blob], metadata.filename, { type: metadata.mimeType });

            await navigator.share({
                files: [file],
                title: 'Shared from PwaniNet',
            });

        } catch (error) {
            console.error('Failed to share file:', error);
            throw error;
        }
    }

    /**
     * Search downloads
     * @param {string} query - Search query
     * @returns {Promise<object[]>}
     */
    async search(query) {
        const downloads = await downloadsMetadataManager.getAllDownloads();
        const lowerQuery = query.toLowerCase();

        return downloads.filter(download => 
            download.filename.toLowerCase().includes(lowerQuery) ||
            download.type.toLowerCase().includes(lowerQuery)
        );
    }

    /**
     * Sort downloads
     * @param {object[]} downloads - Downloads to sort
     * @param {string} sortBy - Sort field ('filename', 'size', 'createdAt', 'type')
     * @param {string} order - Sort order ('asc', 'desc')
     * @returns {object[]}
     */
    sort(downloads, sortBy = 'createdAt', order = 'desc') {
        return [...downloads].sort((a, b) => {
            let comparison = 0;

            switch (sortBy) {
                case 'filename':
                    comparison = a.filename.localeCompare(b.filename);
                    break;
                case 'size':
                    comparison = (a.size || 0) - (b.size || 0);
                    break;
                case 'createdAt':
                    comparison = (a.createdAt || 0) - (b.createdAt || 0);
                    break;
                case 'type':
                    comparison = a.type.localeCompare(b.type);
                    break;
                default:
                    comparison = 0;
            }

            return order === 'desc' ? -comparison : comparison;
        });
    }

    /**
     * Get all downloads
     * @returns {Promise<object[]>}
     */
    async getAllDownloads() {
        return await downloadsMetadataManager.getAllDownloads();
    }

    /**
     * Get downloads by type
     * @param {string} type - Download type
     * @returns {Promise<object[]>}
     */
    async getDownloadsByType(type) {
        return await downloadsMetadataManager.getDownloadsByType(type);
    }

    /**
     * Get download statistics
     * @returns {Promise<object>}
     */
    async getStatistics() {
        const downloads = await this.getAllDownloads();

        const stats = {
            total: downloads.length,
            byType: {
                image: 0,
                video: 0,
                document: 0,
            },
            totalSize: 0,
        };

        downloads.forEach(download => {
            if (stats.byType[download.type] !== undefined) {
                stats.byType[download.type]++;
            }
            stats.totalSize += download.size || 0;
        });

        return stats;
    }

    /**
     * Format bytes for display
     * @param {number} bytes - Bytes
     * @returns {string} Formatted size
     */
    formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

// Global downloads manager instance
export const downloadsManager = new DownloadsManager();

// Initialize on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => downloadsManager.initialize());
} else {
    downloadsManager.initialize();
}

export {
    DownloadsManager,
};

export default DownloadsManager;
