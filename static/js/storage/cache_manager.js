/**
 * Cache Manager for PwaniNet
 * Handles browser cache management using Cache API
 */

class CacheManager {
    constructor() {
        this.cacheName = 'PwaniNetCache';
        this.indexedDBManager = null;
        this.initialized = false;
    }

    /**
     * Initialize the cache manager
     */
    async init() {
        if (this.initialized) return;

        // Initialize IndexedDB manager
        const { indexedDBManager } = await import('./indexeddb.js');
        this.indexedDBManager = indexedDBManager;
        await this.indexedDBManager.init();

        this.initialized = true;
    }

    /**
     * Get cache statistics
     */
    async getCacheStats() {
        await this.init();

        if ('caches' in window) {
            try {
                const cache = await caches.open(this.cacheName);
                const keys = await cache.keys();
                
                let imageCount = 0;
                let videoCount = 0;
                let apiCount = 0;
                let totalSize = 0;

                for (const request of keys) {
                    const response = await cache.match(request);
                    if (response) {
                        const blob = await response.blob();
                        const size = blob.size;
                        totalSize += size;

                        const url = request.url.toLowerCase();
                        if (url.match(/\.(jpg|jpeg|png|gif|webp)$/)) {
                            imageCount++;
                        } else if (url.match(/\.(mp4|webm|mov)$/)) {
                            videoCount++;
                        } else {
                            apiCount++;
                        }
                    }
                }

                return {
                    images: { count: imageCount, size: 0 },
                    videos: { count: videoCount, size: 0 },
                    api: { count: apiCount, size: 0 },
                    total: totalSize
                };
            } catch (error) {
                console.warn('Failed to get cache stats:', error);
            }
        }

        // Fallback to IndexedDB cache stats
        const stats = await this.indexedDBManager.getStorageStats();
        return stats.cache;
    }

    /**
     * Clear image cache
     */
    async clearImageCache() {
        await this.init();

        if ('caches' in window) {
            try {
                const cache = await caches.open(this.cacheName);
                const keys = await cache.keys();
                
                for (const request of keys) {
                    const url = request.url.toLowerCase();
                    if (url.match(/\.(jpg|jpeg|png|gif|webp)$/)) {
                        await cache.delete(request);
                    }
                }

                // Update IndexedDB
                await this.indexedDBManager.clearCacheByType('image');
                
                return true;
            } catch (error) {
                console.warn('Failed to clear image cache:', error);
            }
        }

        // Fallback to IndexedDB only
        await this.indexedDBManager.clearCacheByType('image');
        return true;
    }

    /**
     * Clear video cache
     */
    async clearVideoCache() {
        await this.init();

        if ('caches' in window) {
            try {
                const cache = await caches.open(this.cacheName);
                const keys = await cache.keys();
                
                for (const request of keys) {
                    const url = request.url.toLowerCase();
                    if (url.match(/\.(mp4|webm|mov)$/)) {
                        await cache.delete(request);
                    }
                }

                // Update IndexedDB
                await this.indexedDBManager.clearCacheByType('video');
                
                return true;
            } catch (error) {
                console.warn('Failed to clear video cache:', error);
            }
        }

        // Fallback to IndexedDB only
        await this.indexedDBManager.clearCacheByType('video');
        return true;
    }

    /**
     * Clear API cache
     */
    async clearAPICache() {
        await this.init();

        if ('caches' in window) {
            try {
                const cache = await caches.open(this.cacheName);
                const keys = await cache.keys();
                
                for (const request of keys) {
                    const url = request.url.toLowerCase();
                    if (!url.match(/\.(jpg|jpeg|png|gif|webp|mp4|webm|mov)$/)) {
                        await cache.delete(request);
                    }
                }

                // Update IndexedDB
                await this.indexedDBManager.clearCacheByType('api');
                
                return true;
            } catch (error) {
                console.warn('Failed to clear API cache:', error);
            }
        }

        // Fallback to IndexedDB only
        await this.indexedDBManager.clearCacheByType('api');
        return true;
    }

    /**
     * Clear all cache
     */
    async clearAllCache() {
        await this.init();

        if ('caches' in window) {
            try {
                await caches.delete(this.cacheName);
                // Update IndexedDB
                await this.indexedDBManager.clearAllCache();
                return true;
            } catch (error) {
                console.warn('Failed to clear all cache:', error);
            }
        }

        // Fallback to IndexedDB only
        await this.indexedDBManager.clearAllCache();
        return true;
    }

    /**
     * Estimate cache size
     */
    async estimateCacheSize() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            try {
                const estimate = await navigator.storage.estimate();
                return {
                    usage: estimate.usage,
                    quota: estimate.quota,
                    percentage: estimate.quota ? (estimate.usage / estimate.quota) * 100 : 0
                };
            } catch (error) {
                console.warn('Failed to estimate storage:', error);
            }
        }

        // Fallback: calculate from cache stats
        const stats = await this.getCacheStats();
        return {
            usage: stats.total,
            quota: null,
            percentage: null
        };
    }

    /**
     * Check if cache API is available
     */
    isCacheAPIAvailable() {
        return 'caches' in window;
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
const cacheManager = new CacheManager();
