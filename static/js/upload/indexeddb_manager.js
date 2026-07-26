/**
 * IndexedDB Manager
 * 
 * Manages browser database storage for drafts, downloads metadata,
 * and temporary data. Provides a clean API for IndexedDB operations.
 */

class IndexedDBManager {
    constructor(dbName = 'PwaniNetDB', version = 1) {
        this.dbName = dbName;
        this.version = version;
        this.db = null;
        this.isInitialized = false;
    }

    /**
     * Initialize IndexedDB
     * @returns {Promise<IDBDatabase>}
     */
    async initialize() {
        if (this.isInitialized && this.db) {
            return this.db;
        }

        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => {
                reject(new Error('Failed to open IndexedDB'));
            };

            request.onsuccess = () => {
                this.db = request.result;
                this.isInitialized = true;
                resolve(this.db);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Create stores
                if (!db.objectStoreNames.contains('drafts')) {
                    const draftStore = db.createObjectStore('drafts', { keyPath: 'id' });
                    draftStore.createIndex('createdAt', 'createdAt', { unique: false });
                }

                if (!db.objectStoreNames.contains('downloads')) {
                    const downloadStore = db.createObjectStore('downloads', { keyPath: 'id' });
                    downloadStore.createIndex('type', 'type', { unique: false });
                    downloadStore.createIndex('createdAt', 'createdAt', { unique: false });
                }

                if (!db.objectStoreNames.contains('tempData')) {
                    const tempStore = db.createObjectStore('tempData', { keyPath: 'id' });
                    tempStore.createIndex('expiresAt', 'expiresAt', { unique: false });
                }
            };
        });
    }

    /**
     * Add item to a store
     * @param {string} storeName - Store name
     * @param {object} item - Item to add
     * @returns {Promise<any>}
     */
    async add(storeName, item) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.add(item);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to add item'));
        });
    }

    /**
     * Get item from a store
     * @param {string} storeName - Store name
     * @param {any} key - Item key
     * @returns {Promise<any>}
     */
    async get(storeName, key) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.get(key);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to get item'));
        });
    }

    /**
     * Update item in a store
     * @param {string} storeName - Store name
     * @param {object} item - Item to update
     * @returns {Promise<any>}
     */
    async update(storeName, item) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.put(item);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to update item'));
        });
    }

    /**
     * Delete item from a store
     * @param {string} storeName - Store name
     * @param {any} key - Item key
     * @returns {Promise<void>}
     */
    async delete(storeName, key) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.delete(key);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(new Error('Failed to delete item'));
        });
    }

    /**
     * Get all items from a store
     * @param {string} storeName - Store name
     * @returns {Promise<any[]>}
     */
    async getAll(storeName) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to get all items'));
        });
    }

    /**
     * Clear a store
     * @param {string} storeName - Store name
     * @returns {Promise<void>}
     */
    async clearStore(storeName) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(new Error('Failed to clear store'));
        });
    }

    /**
     * Get items by index
     * @param {string} storeName - Store name
     * @param {string} indexName - Index name
     * @param {any} value - Index value
     * @returns {Promise<any[]>}
     */
    async getByIndex(storeName, indexName, value) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const index = store.index(indexName);
            const request = index.getAll(value);

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to get items by index'));
        });
    }

    /**
     * Count items in a store
     * @param {string} storeName - Store name
     * @returns {Promise<number>}
     */
    async count(storeName) {
        await this.initialize();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            const request = store.count();

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(new Error('Failed to count items'));
        });
    }

    /**
     * Check if IndexedDB is supported
     * @returns {boolean}
     */
    static isSupported() {
        return 'indexedDB' in window;
    }

    /**
     * Close the database connection
     */
    close() {
        if (this.db) {
            this.db.close();
            this.db = null;
            this.isInitialized = false;
        }
    }
}

// Draft-specific operations
class DraftManager extends IndexedDBManager {
    constructor() {
        super('PwaniNetDB', 1);
    }

    /**
     * Save a draft
     * @param {object} draft - Draft data
     * @returns {Promise<string>} Draft ID
     */
    async saveDraft(draft) {
        const draftData = {
            id: draft.id || `draft_${Date.now()}`,
            caption: draft.caption || '',
            mediaFiles: draft.mediaFiles || [],
            unit: draft.unit || null,
            group: draft.group || null,
            gradientClass: draft.gradientClass || 'none',
            createdAt: draft.createdAt || Date.now(),
            updatedAt: Date.now(),
        };

        await this.add('drafts', draftData);
        return draftData.id;
    }

    /**
     * Get a draft
     * @param {string} id - Draft ID
     * @returns {Promise<object|null>}
     */
    async getDraft(id) {
        return await this.get('drafts', id);
    }

    /**
     * Get all drafts
     * @returns {Promise<object[]>}
     */
    async getAllDrafts() {
        return await this.getAll('drafts');
    }

    /**
     * Update a draft
     * @param {string} id - Draft ID
     * @param {object} updates - Updates to apply
     * @returns {Promise<void>}
     */
    async updateDraft(id, updates) {
        const draft = await this.getDraft(id);
        if (draft) {
            const updatedDraft = { ...draft, ...updates, updatedAt: Date.now() };
            await this.update('drafts', updatedDraft);
        }
    }

    /**
     * Delete a draft
     * @param {string} id - Draft ID
     * @returns {Promise<void>}
     */
    async deleteDraft(id) {
        await this.delete('drafts', id);
    }

    /**
     * Clear all drafts
     * @returns {Promise<void>}
     */
    async clearDrafts() {
        await this.clearStore('drafts');
    }
}

// Downloads metadata operations
class DownloadsMetadataManager extends IndexedDBManager {
    constructor() {
        super('PwaniNetDB', 1);
    }

    /**
     * Add download metadata
     * @param {object} metadata - Download metadata
     * @returns {Promise<string>} Download ID
     */
    async addDownload(metadata) {
        const downloadData = {
            id: metadata.id || `download_${Date.now()}`,
            url: metadata.url,
            type: metadata.type, // 'image', 'video', 'document', 'audio'
            filename: metadata.filename,
            size: metadata.size,
            mimeType: metadata.mimeType,
            postId: metadata.postId || null,
            category: metadata.category || metadata.type || 'document', // 'image', 'video', 'audio', 'document'
            createdAt: Date.now(),
            downloadedAt: metadata.downloadedAt || null,
        };

        await this.add('downloads', downloadData);
        return downloadData.id;
    }

    /**
     * Get download metadata
     * @param {string} id - Download ID
     * @returns {Promise<object|null>}
     */
    async getDownload(id) {
        return await this.get('downloads', id);
    }

    /**
     * Get all downloads
     * @returns {Promise<object[]>}
     */
    async getAllDownloads() {
        return await this.getAll('downloads');
    }

    /**
     * Get downloads by type
     * @param {string} type - Download type
     * @returns {Promise<object[]>}
     */
    async getDownloadsByType(type) {
        return await this.getByIndex('downloads', 'type', type);
    }

    /**
     * Update download metadata
     * @param {string} id - Download ID
     * @param {object} updates - Updates to apply
     * @returns {Promise<void>}
     */
    async updateDownload(id, updates) {
        const download = await this.getDownload(id);
        if (download) {
            const updatedDownload = { ...download, ...updates };
            await this.update('downloads', updatedDownload);
        }
    }

    /**
     * Delete download metadata
     * @param {string} id - Download ID
     * @returns {Promise<void>}
     */
    async deleteDownload(id) {
        await this.delete('downloads', id);
    }

    /**
     * Clear all downloads metadata
     * @returns {Promise<void>}
     */
    async clearDownloads() {
        await this.clearStore('downloads');
    }
}

// Temporary data operations
class TempDataManager extends IndexedDBManager {
    constructor() {
        super('PwaniNetDB', 1);
    }

    /**
     * Add temporary data
     * @param {object} data - Temporary data
     * @param {number} ttl - Time to live in milliseconds
     * @returns {Promise<string>} Data ID
     */
    async addTempData(data, ttl = 3600000) {
        const tempData = {
            id: data.id || `temp_${Date.now()}`,
            data: data,
            expiresAt: Date.now() + ttl,
            createdAt: Date.now(),
        };

        await this.add('tempData', tempData);
        return tempData.id;
    }

    /**
     * Get temporary data
     * @param {string} id - Data ID
     * @returns {Promise<object|null>}
     */
    async getTempData(id) {
        const data = await this.get('tempData', id);
        
        // Check if expired
        if (data && data.expiresAt < Date.now()) {
            await this.deleteTempData(id);
            return null;
        }
        
        return data;
    }

    /**
     * Get all temporary data
     * @returns {Promise<object[]>}
     */
    async getAllTempData() {
        const allData = await this.getAll('tempData');
        
        // Filter out expired data
        const validData = allData.filter(item => item.expiresAt >= Date.now());
        
        // Clean up expired data
        for (const item of allData) {
            if (item.expiresAt < Date.now()) {
                await this.deleteTempData(item.id);
            }
        }
        
        return validData;
    }

    /**
     * Delete temporary data
     * @param {string} id - Data ID
     * @returns {Promise<void>}
     */
    async deleteTempData(id) {
        await this.delete('tempData', id);
    }

    /**
     * Clear all temporary data
     * @returns {Promise<void>}
     */
    async clearTempData() {
        await this.clearStore('tempData');
    }

    /**
     * Clean up expired temporary data
     * @returns {Promise<number>} Number of items cleaned up
     */
    async cleanupExpired() {
        const allData = await this.getAll('tempData');
        const expiredData = allData.filter(item => item.expiresAt < Date.now());
        
        for (const item of expiredData) {
            await this.deleteTempData(item.id);
        }
        
        return expiredData.length;
    }
}

// Global instances
export const indexedDBManager = new IndexedDBManager();
export const draftManager = new DraftManager();
export const downloadsMetadataManager = new DownloadsMetadataManager();
export const tempDataManager = new TempDataManager();

export {
    IndexedDBManager,
    DraftManager,
    DownloadsMetadataManager,
    TempDataManager,
};

export default IndexedDBManager;
