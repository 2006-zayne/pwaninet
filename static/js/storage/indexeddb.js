/**
 * IndexedDB Manager for PwaniNet Storage System
 * Handles metadata storage for downloads, cache, and temporary data
 */

class IndexedDBManager {
    constructor() {
        this.dbName = 'PwaniNetStorage';
        this.dbVersion = 1;
        this.db = null;
        this.stores = {
            downloads: 'downloads',
            cache: 'cache',
            temporary: 'temporary'
        };
    }

    /**
     * Initialize IndexedDB database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => {
                console.error('IndexedDB error:', request.error);
                reject(request.error);
            };

            request.onsuccess = () => {
                this.db = request.result;
                console.log('IndexedDB initialized successfully');
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Downloads store
                if (!db.objectStoreNames.contains(this.stores.downloads)) {
                    const downloadsStore = db.createObjectStore(this.stores.downloads, { keyPath: 'id' });
                    downloadsStore.createIndex('postId', 'postId', { unique: false });
                    downloadsStore.createIndex('mediaId', 'mediaId', { unique: false });
                    downloadsStore.createIndex('category', 'category', { unique: false });
                    downloadsStore.createIndex('downloadDate', 'downloadDate', { unique: false });
                    downloadsStore.createIndex('sourceURL', 'sourceURL', { unique: true });
                }

                // Cache store
                if (!db.objectStoreNames.contains(this.stores.cache)) {
                    const cacheStore = db.createObjectStore(this.stores.cache, { keyPath: 'url' });
                    cacheStore.createIndex('type', 'type', { unique: false });
                    cacheStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Temporary data store
                if (!db.objectStoreNames.contains(this.stores.temporary)) {
                    const tempStore = db.createObjectStore(this.stores.temporary, { keyPath: 'key' });
                    tempStore.createIndex('type', 'type', { unique: false });
                    tempStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }

    /**
     * Add or update a download record
     */
    async addDownload(metadata) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readwrite');
            const store = transaction.objectStore(this.stores.downloads);
            const request = store.put(metadata);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get a download by ID
     */
    async getDownload(id) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readonly');
            const store = transaction.objectStore(this.stores.downloads);
            const request = store.get(id);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get all downloads
     */
    async getAllDownloads() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readonly');
            const store = transaction.objectStore(this.stores.downloads);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get downloads by category
     */
    async getDownloadsByCategory(category) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readonly');
            const store = transaction.objectStore(this.stores.downloads);
            const index = store.index('category');
            const request = index.getAll(category);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Check if a download exists by source URL
     */
    async downloadExists(sourceURL) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readonly');
            const store = transaction.objectStore(this.stores.downloads);
            const index = store.index('sourceURL');
            const request = index.get(sourceURL);

            request.onsuccess = () => resolve(!!request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Delete a download
     */
    async deleteDownload(id) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readwrite');
            const store = transaction.objectStore(this.stores.downloads);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear all downloads
     */
    async clearDownloads() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.downloads], 'readwrite');
            const store = transaction.objectStore(this.stores.downloads);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Add cache entry
     */
    async addCacheEntry(entry) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.cache], 'readwrite');
            const store = transaction.objectStore(this.stores.cache);
            const request = store.put(entry);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get cache entries by type
     */
    async getCacheByType(type) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.cache], 'readonly');
            const store = transaction.objectStore(this.stores.cache);
            const index = store.index('type');
            const request = index.getAll(type);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear cache by type
     */
    async clearCacheByType(type) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.cache], 'readwrite');
            const store = transaction.objectStore(this.stores.cache);
            const index = store.index('type');
            const request = index.openCursor(IDBKeyRange.only(type));

            const deletes = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    deletes.push(cursor.delete());
                    cursor.continue();
                } else {
                    Promise.all(deletes).then(() => resolve()).catch(reject);
                }
            };

            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear all cache
     */
    async clearAllCache() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.cache], 'readwrite');
            const store = transaction.objectStore(this.stores.cache);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Add temporary data entry
     */
    async addTemporaryData(entry) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.temporary], 'readwrite');
            const store = transaction.objectStore(this.stores.temporary);
            const request = store.put(entry);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get temporary data by type
     */
    async getTemporaryDataByType(type) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.temporary], 'readonly');
            const store = transaction.objectStore(this.stores.temporary);
            const index = store.index('type');
            const request = index.getAll(type);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear temporary data by type
     */
    async clearTemporaryDataByType(type) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.temporary], 'readwrite');
            const store = transaction.objectStore(this.stores.temporary);
            const index = store.index('type');
            const request = index.openCursor(IDBKeyRange.only(type));

            const deletes = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    deletes.push(cursor.delete());
                    cursor.continue();
                } else {
                    Promise.all(deletes).then(() => resolve()).catch(reject);
                }
            };

            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Clear all temporary data
     */
    async clearAllTemporaryData() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.stores.temporary], 'readwrite');
            const store = transaction.objectStore(this.stores.temporary);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    /**
     * Get storage statistics
     */
    async getStorageStats() {
        if (!this.db) await this.init();

        const downloads = await this.getAllDownloads();
        const imageCache = await this.getCacheByType('image');
        const videoCache = await this.getCacheByType('video');
        const apiCache = await this.getCacheByType('api');
        const tempData = await this.getTemporaryDataByType('*');

        const downloadsSize = downloads.reduce((sum, d) => sum + (d.size || 0), 0);
        const imageCacheSize = imageCache.reduce((sum, c) => sum + (c.size || 0), 0);
        const videoCacheSize = videoCache.reduce((sum, c) => sum + (c.size || 0), 0);
        const apiCacheSize = apiCache.reduce((sum, c) => sum + (c.size || 0), 0);
        const tempDataSize = tempData.reduce((sum, t) => sum + (t.size || 0), 0);

        return {
            downloads: {
                count: downloads.length,
                size: downloadsSize,
                images: downloads.filter(d => d.category === 'image').length,
                videos: downloads.filter(d => d.category === 'video').length,
                documents: downloads.filter(d => d.category === 'document').length
            },
            cache: {
                images: { count: imageCache.length, size: imageCacheSize },
                videos: { count: videoCache.length, size: videoCacheSize },
                api: { count: apiCache.length, size: apiCacheSize }
            },
            temporary: {
                count: tempData.length,
                size: tempDataSize
            },
            total: downloadsSize + imageCacheSize + videoCacheSize + apiCacheSize + tempDataSize
        };
    }
}

// Export singleton instance
const indexedDBManager = new IndexedDBManager();
