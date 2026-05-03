/**
 * Offline Cache Management for PwaniNet Messaging
 * Handles IndexedDB storage for conversations, messages, and outbox
 */

class OfflineCache {
    constructor() {
        this.dbName = 'pwaninet_chat';
        this.dbVersion = 1;
        this.db = null;
    }

    async init() {
        try {
            this.db = await this.openDatabase();
            console.log('Offline cache initialized successfully');
        } catch (error) {
            console.error('Failed to initialize offline cache:', error);
        }
    }

    async openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Create object stores
                if (!db.objectStoreNames.contains('conversations')) {
                    const conversationStore = db.createObjectStore('conversations', { keyPath: 'id' });
                    conversationStore.createIndex('updated_at', 'updated_at');
                    conversationStore.createIndex('participant_id', 'participant_id');
                }

                if (!db.objectStoreNames.contains('messages')) {
                    const messageStore = db.createObjectStore('messages', { keyPath: 'id' });
                    messageStore.createIndex('conversation_id', 'conversation_id');
                    messageStore.createIndex('timestamp', 'timestamp');
                    messageStore.createIndex('created_at', 'created_at');
                }

                if (!db.objectStoreNames.contains('outbox')) {
                    const outboxStore = db.createObjectStore('outbox', { keyPath: 'id', autoIncrement: true });
                    outboxStore.createIndex('conversation_id', 'conversation_id');
                    outboxStore.createIndex('created_at', 'created_at');
                }

                if (!db.objectStoreNames.contains('users')) {
                    const userStore = db.createObjectStore('users', { keyPath: 'id' });
                    userStore.createIndex('username', 'username');
                }
            };
        });
    }

    // CONVERSATIONS
    async saveConversation(conversation) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['conversations'], 'readwrite');
        const store = transaction.objectStore('conversations');
        
        // Add cache timestamp
        conversation.cached_at = new Date().toISOString();
        
        return store.put(conversation);
    }

    async getConversations(limit = 50) {
        if (!this.db) return [];
        
        const transaction = this.db.transaction(['conversations'], 'readonly');
        const store = transaction.objectStore('conversations');
        const index = store.index('updated_at');
        
        return new Promise((resolve, reject) => {
            const request = index.openCursor(null, 'prev');
            const results = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor && results.length < limit) {
                    results.push(cursor.value);
                    cursor.continue();
                } else {
                    resolve(results);
                }
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    async getConversation(conversationId) {
        if (!this.db) return null;
        
        const transaction = this.db.transaction(['conversations'], 'readonly');
        const store = transaction.objectStore('conversations');
        
        return new Promise((resolve, reject) => {
            const request = store.get(conversationId);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // MESSAGES
    async saveMessage(message) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['messages'], 'readwrite');
        const store = transaction.objectStore('messages');
        
        // Add cache timestamp
        message.cached_at = new Date().toISOString();
        
        return store.put(message);
    }

    async saveMessages(messages) {
        if (!this.db || !messages.length) return;
        
        const transaction = this.db.transaction(['messages'], 'readwrite');
        const store = transaction.objectStore('messages');
        
        for (const message of messages) {
            message.cached_at = new Date().toISOString();
            store.put(message);
        }
        
        return transaction.complete;
    }

    async getMessages(conversationId, limit = 100, offset = 0) {
        if (!this.db) return [];
        
        const transaction = this.db.transaction(['messages'], 'readonly');
        const store = transaction.objectStore('messages');
        const index = store.index('conversation_id');
        
        return new Promise((resolve, reject) => {
            const request = index.openCursor(IDBKeyRange.only(conversationId), 'prev');
            const results = [];
            let skipped = 0;
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor && results.length < limit) {
                    if (skipped < offset) {
                        skipped++;
                        cursor.continue();
                    } else {
                        results.push(cursor.value);
                        cursor.continue();
                    }
                } else {
                    resolve(results.reverse()); // Reverse to show oldest first
                }
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    async getMessage(messageId) {
        if (!this.db) return null;
        
        const transaction = this.db.transaction(['messages'], 'readonly');
        const store = transaction.objectStore('messages');
        
        return new Promise((resolve, reject) => {
            const request = store.get(messageId);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // OUTBOX (pending messages)
    async saveToOutbox(message) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['outbox'], 'readwrite');
        const store = transaction.objectStore('outbox');
        
        const outboxMessage = {
            ...message,
            created_at: new Date().toISOString(),
            status: 'pending'
        };
        
        return store.add(outboxMessage);
    }

    async getOutboxMessages(conversationId = null) {
        if (!this.db) return [];
        
        const transaction = this.db.transaction(['outbox'], 'readonly');
        const store = transaction.objectStore('outbox');
        
        return new Promise((resolve, reject) => {
            let request;
            if (conversationId) {
                const index = store.index('conversation_id');
                request = index.openCursor(IDBKeyRange.only(conversationId));
            } else {
                request = store.openCursor();
            }
            
            const results = [];
            
            request.onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    results.push(cursor.value);
                    cursor.continue();
                } else {
                    resolve(results);
                }
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    async removeFromOutbox(outboxId) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['outbox'], 'readwrite');
        const store = transaction.objectStore('outbox');
        
        return new Promise((resolve, reject) => {
            const request = store.delete(outboxId);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    // USERS
    async saveUser(user) {
        if (!this.db) return;
        
        const transaction = this.db.transaction(['users'], 'readwrite');
        const store = transaction.objectStore('users');
        
        user.cached_at = new Date().toISOString();
        
        return store.put(user);
    }

    async getUser(userId) {
        if (!this.db) return null;
        
        const transaction = this.db.transaction(['users'], 'readonly');
        const store = transaction.objectStore('users');
        
        return new Promise((resolve, reject) => {
            const request = store.get(userId);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    // UTILITY
    async clearCache() {
        if (!this.db) return;
        
        const stores = ['conversations', 'messages', 'outbox', 'users'];
        
        for (const storeName of stores) {
            const transaction = this.db.transaction([storeName], 'readwrite');
            const store = transaction.objectStore(storeName);
            store.clear();
        }
        
        console.log('Offline cache cleared');
    }

    async getCacheSize() {
        if (!this.db) return 0;
        
        let totalSize = 0;
        const stores = ['conversations', 'messages', 'outbox', 'users'];
        
        for (const storeName of stores) {
            const transaction = this.db.transaction([storeName], 'readonly');
            const store = transaction.objectStore(storeName);
            
            const count = await new Promise((resolve) => {
                const request = store.count();
                request.onsuccess = () => resolve(request.result);
            });
            
            totalSize += count;
        }
        
        return totalSize;
    }
}

// Global instance
window.offlineCache = new OfflineCache();
