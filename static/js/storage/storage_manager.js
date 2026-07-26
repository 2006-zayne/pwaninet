/**
 * Storage Manager for PwaniNet
 * Coordinates all storage operations including downloads, cache, and temporary data
 */

class StorageManager {
    constructor() {
        this.initialized = false;
        this.downloadsManager = null;
        this.cacheManager = null;
        this.indexedDBManager = null;
    }

    /**
     * Initialize the storage manager
     */
    async init() {
        if (this.initialized) return;

        // Import managers
        const { downloadsManager } = await import('./downloads_manager.js');
        const { cacheManager } = await import('./cache_manager.js');
        const { indexedDBManager } = await import('./indexeddb.js');

        this.downloadsManager = downloadsManager;
        this.cacheManager = cacheManager;
        this.indexedDBManager = indexedDBManager;

        // Initialize all managers
        await Promise.all([
            this.downloadsManager.init(),
            this.cacheManager.init(),
            this.indexedDBManager.init()
        ]);

        this.initialized = true;
        console.log('Storage Manager initialized successfully');
    }

    /**
     * Get comprehensive storage statistics
     */
    async getStorageStats() {
        await this.init();

        const [downloadStats, cacheStats, storageEstimate] = await Promise.all([
            this.indexedDBManager.getStorageStats(),
            this.cacheManager.getCacheStats(),
            this.getStorageEstimate()
        ]);

        return {
            downloads: downloadStats.downloads,
            cache: {
                images: cacheStats.images,
                videos: cacheStats.videos,
                api: cacheStats.api,
                total: cacheStats.total
            },
            temporary: downloadStats.temporary,
            total: downloadStats.total + cacheStats.total,
            browserStorage: storageEstimate
        };
    }

    /**
     * Get browser storage estimate
     */
    async getStorageEstimate() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            try {
                const estimate = await navigator.storage.estimate();
                return {
                    usage: estimate.usage,
                    quota: estimate.quota,
                    percentage: estimate.quota ? (estimate.usage / estimate.quota) * 100 : 0,
                    available: estimate.quota ? estimate.quota - estimate.usage : null
                };
            } catch (error) {
                console.warn('Failed to get storage estimate:', error);
            }
        }

        return {
            usage: null,
            quota: null,
            percentage: null,
            available: null
        };
    }

    /**
     * Format bytes to human readable format
     */
    formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /**
     * Clear temporary data
     */
    async clearTemporaryData() {
        await this.init();
        await this.indexedDBManager.clearAllTemporaryData();
        return true;
    }

    /**
     * Clear specific temporary data type
     */
    async clearTemporaryDataType(type) {
        await this.init();
        await this.indexedDBManager.clearTemporaryDataByType(type);
        return true;
    }

    /**
     * Get offline content status
     */
    async getOfflineContent() {
        await this.init();

        // For now, return empty status
        // This can be expanded in the future for offline support
        return {
            available: false,
            items: [],
            size: 0
        };
    }

    /**
     * Check browser compatibility
     */
    checkBrowserCompatibility() {
        return {
            opfs: 'getDirectory' in navigator,
            indexedDB: 'indexedDB' in window,
            cacheAPI: 'caches' in window,
            webShare: 'share' in navigator,
            storageEstimate: 'storage' in navigator && 'estimate' in navigator.storage
        };
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const existingToast = document.querySelector('.toast-container');
        if (existingToast) {
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            existingToast.appendChild(toast);
            
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => toast.remove());
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }
}

// Export singleton instance
const storageManager = new StorageManager();
