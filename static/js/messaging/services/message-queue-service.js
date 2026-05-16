/**
 * Message Queue Service
 * 
 * Manages persistent outgoing message queue with IndexedDB storage.
 * Handles state machine transitions, upload lifecycle, and offline resilience.
 */

class MessageQueueService {
    constructor() {
        this.dbName = 'PwaninetMessageQueue';
        this.dbVersion = 1;
        this.db = null;
        this.queue = new Map(); // In-memory cache
        this.uploadQueue = [];
        this.isProcessing = false;
        this.maxConcurrentUploads = 3;
        this.activeUploads = 0;
        
        // State machine states
        this.STATES = {
            DRAFT: 'draft',
            QUEUED: 'queued',
            UPLOADING: 'uploading',
            SENDING: 'sending',
            SENT: 'sent',
            DELIVERED: 'delivered',
            READ: 'read',
            FAILED: 'failed',
            RETRYING: 'retrying'
        };
        
        // Message types
        this.MESSAGE_TYPES = {
            TEXT: 'text',
            IMAGE: 'image',
            VIDEO: 'video',
            AUDIO: 'audio',
            DOCUMENT: 'document'
        };
    }
    
    /**
     * Initialize IndexedDB database
     */
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                this.loadQueueFromDB().then(() => resolve());
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create messages store
                if (!db.objectStoreNames.contains('messages')) {
                    const store = db.createObjectStore('messages', { keyPath: 'tempId' });
                    store.createIndex('status', 'status', { unique: false });
                    store.createIndex('conversationId', 'conversationId', { unique: false });
                    store.createIndex('created', 'created', { unique: false });
                    store.createIndex('status_created', ['status', 'created'], { unique: false });
                }
                
                // Create media store for large files
                if (!db.objectStoreNames.contains('media')) {
                    const mediaStore = db.createObjectStore('media', { keyPath: 'tempId' });
                    mediaStore.createIndex('messageId', 'messageId', { unique: false });
                }
            };
        });
    }
    
    /**
     * Load queue from IndexedDB into memory
     */
    async loadQueueFromDB() {
        const transaction = this.db.transaction(['messages'], 'readonly');
        const store = transaction.objectStore('messages');
        const request = store.getAll();
        
        return new Promise((resolve, reject) => {
            request.onsuccess = () => {
                const messages = request.result;
                this.queue.clear();
                messages.forEach(msg => {
                    this.queue.set(msg.tempId, msg);
                });
                console.log(`[MESSAGE_QUEUE] Loaded ${messages.length} messages from IndexedDB`);
                resolve(messages);
            };
            request.onerror = () => reject(request.error);
        });
    }
    
    /**
     * Generate unique temporary ID
     */
    generateTempId() {
        return `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Create a new message in the queue
     */
    async createMessage(messageData) {
        const tempId = this.generateTempId();
        const now = Date.now();
        
        const message = {
            tempId,
            conversationId: messageData.conversationId,
            messageType: messageData.messageType || this.MESSAGE_TYPES.TEXT,
            content: messageData.content || null,
            encryptedContent: messageData.encryptedContent || null,
            isEncrypted: messageData.isEncrypted || false,
            replyToId: messageData.replyToId || null,
            attachment: messageData.attachment || null,
            attachmentType: messageData.attachmentType || null,
            attachmentUrl: messageData.attachmentUrl || null,
            mediaMetadata: messageData.mediaMetadata || {},
            linkUrl: messageData.linkUrl || null,
            linkTitle: messageData.linkTitle || null,
            linkDescription: messageData.linkDescription || null,
            linkImage: messageData.linkImage || null,
            linkType: messageData.linkType || null,
            status: this.STATES.DRAFT,
            retryCount: 0,
            maxRetries: 3,
            lastError: null,
            serverMessageId: null,
            syncedAt: null,
            created: now,
            updated: now,
            queuedAt: null,
            sentAt: null
        };
        
        // Store in IndexedDB
        await this.saveMessage(message);
        
        // Add to in-memory queue
        this.queue.set(tempId, message);
        
        console.log(`[MESSAGE_QUEUE] Created message ${tempId} in DRAFT state`);
        return message;
    }
    
    /**
     * Save message to IndexedDB
     */
    async saveMessage(message) {
        const transaction = this.db.transaction(['messages'], 'readwrite');
        const store = transaction.objectStore('messages');
        
        return new Promise((resolve, reject) => {
            const request = store.put(message);
            request.onsuccess = () => resolve(message);
            request.onerror = () => reject(request.error);
        });
    }
    
    /**
     * Get message by temp ID
     */
    getMessage(tempId) {
        return this.queue.get(tempId);
    }
    
    /**
     * Get all messages for a conversation
     */
    getConversationMessages(conversationId) {
        return Array.from(this.queue.values())
            .filter(msg => msg.conversationId === conversationId)
            .sort((a, b) => a.created - b.created);
    }
    
    /**
     * Get messages by status
     */
    getMessagesByStatus(status) {
        return Array.from(this.queue.values())
            .filter(msg => msg.status === status)
            .sort((a, b) => a.created - b.created);
    }
    
    /**
     * Transition message to new state
     */
    async transitionMessage(tempId, newStatus, metadata = {}) {
        const message = this.queue.get(tempId);
        if (!message) {
            console.error(`[MESSAGE_QUEUE] Message ${tempId} not found`);
            return null;
        }
        
        const oldStatus = message.status;
        message.status = newStatus;
        message.updated = Date.now();
        
        // Update timestamps based on state
        if (newStatus === MESSAGE_STATE.QUEUED && !message.queuedAt) {
            message.queuedAt = Date.now();
        } else if (newStatus === MESSAGE_STATE.SENT && !message.sentAt) {
            message.sentAt = Date.now();
        } else if ([MESSAGE_STATE.SENT, MESSAGE_STATE.DELIVERED, MESSAGE_STATE.READ].includes(newStatus) && !message.syncedAt) {
            message.syncedAt = Date.now();
        }
        
        // Apply metadata
        Object.assign(message, metadata);
        
        // Save to IndexedDB
        await this.saveMessage(message);
        
        console.log(`[MESSAGE_QUEUE] Message ${tempId} transitioned ${oldStatus} -> ${newStatus}`);
        
        // Emit event for UI updates
        this.emitStateChange(tempId, oldStatus, newStatus, message);
        
        return message;
    }
    
    /**
     * Queue message for upload
     */
    async queueForUpload(tempId) {
        const message = await this.transitionMessage(tempId, MESSAGE_STATE.QUEUED);
        if (message) {
            this.uploadQueue.push(tempId);
            this.processUploadQueue();
        }
        return message;
    }
    
    /**
     * Process upload queue
     */
    async processUploadQueue() {
        if (this.isProcessing || this.activeUploads >= this.maxConcurrentUploads) {
            return;
        }
        
        this.isProcessing = true;
        
        while (this.uploadQueue.length > 0 && this.activeUploads < this.maxConcurrentUploads) {
            const tempId = this.uploadQueue.shift();
            this.activeUploads++;
            
            this.uploadMessage(tempId)
                .finally(() => {
                    this.activeUploads--;
                    if (this.uploadQueue.length > 0) {
                        this.processUploadQueue();
                    } else {
                        this.isProcessing = false;
                    }
                });
        }
    }
    
    /**
     * Upload a single message
     */
    async uploadMessage(tempId) {
        const message = this.queue.get(tempId);
        if (!message) return;
        
        try {
            // Transition to uploading state
            await this.transitionMessage(tempId, MESSAGE_STATE.UPLOADING);

            // If message has attachment, upload it first
            if (message.attachment && !message.attachmentUrl) {
                const attachmentUrl = await this.uploadAttachment(message);
                message.attachmentUrl = attachmentUrl;
                await this.saveMessage(message);
            }

            // Transition to sending state
            await this.transitionMessage(tempId, MESSAGE_STATE.SENDING);

            // Send message to server
            const serverMessage = await this.sendToServer(message);

            // Update with server message ID
            await this.transitionMessage(tempId, MESSAGE_STATE.SENT, {
                serverMessageId: serverMessage.id
            });
            
            console.log(`[MESSAGE_QUEUE] Message ${tempId} sent successfully`);
            
        } catch (error) {
            console.error(`[MESSAGE_QUEUE] Failed to upload message ${tempId}:`, error);
            
            // Check if can retry
            if (message.retryCount < message.maxRetries) {
                await this.transitionMessage(tempId, MESSAGE_STATE.RETRYING, {
                    retryCount: message.retryCount + 1,
                    lastError: error.message
                });

                // Retry after delay
                setTimeout(() => {
                    this.uploadQueue.push(tempId);
                    this.processUploadQueue();
                }, 2000 * (message.retryCount + 1)); // Exponential backoff

            } else {
                // Determine failure type based on context
                const failedState = message.attachment && !message.attachmentUrl
                    ? MESSAGE_STATE.FAILED_UPLOAD
                    : MESSAGE_STATE.FAILED_SEND;
                await this.transitionMessage(tempId, failedState, {
                    lastError: error.message
                });
            }
        }
    }
    
    /**
     * Upload attachment to server
     */
    async uploadAttachment(message) {
        const formData = new FormData();
        formData.append('file', message.attachment);
        formData.append('conversation_id', message.conversationId);
        
        const response = await fetch('/messaging/api/attachments/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': this.getCSRFToken()
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const data = await response.json();
        return data.attachment_url;
    }
    
    /**
     * Send message to server
     */
    async sendToServer(message) {
        const payload = {
            conversation: message.conversationId,
            content: message.content,
            encrypted_content: message.encryptedContent,
            is_encrypted: message.isEncrypted,
            reply_to: message.replyToId,
            attachment: message.attachmentUrl,
            attachment_type: message.attachmentType,
            link_url: message.linkUrl,
            link_title: message.linkTitle,
            link_description: message.linkDescription,
            link_image: message.linkImage,
            link_type: message.linkType,
            temp_id: message.tempId
        };
        
        const response = await fetch('/messaging/api/v1/messages/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken()
            },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`Send failed: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Update message status from server (delivered, read, etc.)
     */
    async updateMessageStatus(tempId, status) {
        const message = this.queue.get(tempId);
        if (!message) return;
        
        await this.transitionMessage(tempId, status);
    }
    
    /**
     * Delete message from queue
     */
    async deleteMessage(tempId) {
        const transaction = this.db.transaction(['messages'], 'readwrite');
        const store = transaction.objectStore('messages');
        
        return new Promise((resolve, reject) => {
            const request = store.delete(tempId);
            request.onsuccess = () => {
                this.queue.delete(tempId);
                console.log(`[MESSAGE_QUEUE] Deleted message ${tempId}`);
                resolve();
            };
            request.onerror = () => reject(request.error);
        });
    }
    
    /**
     * Retry failed messages
     */
    async retryFailedMessages() {
        const failedUploadMessages = this.getMessagesByStatus(MESSAGE_STATE.FAILED_UPLOAD);
        const failedSendMessages = this.getMessagesByStatus(MESSAGE_STATE.FAILED_SEND);
        const failedMessages = [...failedUploadMessages, ...failedSendMessages];
        console.log(`[MESSAGE_QUEUE] Retrying ${failedMessages.length} failed messages`);

        for (const message of failedMessages) {
            if (message.canRetry !== false) {
                await this.transitionMessage(message.tempId, MESSAGE_STATE.QUEUED, {
                    retryCount: 0,
                    lastError: null
                });
                this.uploadQueue.push(message.tempId);
            }
        }

        this.processUploadQueue();
    }
    
    /**
     * Clear all messages (for testing or logout)
     */
    async clearQueue() {
        const transaction = this.db.transaction(['messages'], 'readwrite');
        const store = transaction.objectStore('messages');
        
        return new Promise((resolve, reject) => {
            const request = store.clear();
            request.onsuccess = () => {
                this.queue.clear();
                this.uploadQueue = [];
                console.log('[MESSAGE_QUEUE] Cleared all messages');
                resolve();
            };
            request.onerror = () => reject(request.error);
        });
    }
    
    /**
     * Get queue statistics
     */
    getStats() {
        const messages = Array.from(this.queue.values());
        return {
            total: messages.length,
            byStatus: {
                draft: messages.filter(m => m.status === MESSAGE_STATE.DRAFT).length,
                queued: messages.filter(m => m.status === MESSAGE_STATE.QUEUED).length,
                processing: messages.filter(m => m.status === MESSAGE_STATE.PROCESSING).length,
                uploading: messages.filter(m => m.status === MESSAGE_STATE.UPLOADING).length,
                sending: messages.filter(m => m.status === MESSAGE_STATE.SENDING).length,
                sent: messages.filter(m => m.status === MESSAGE_STATE.SENT).length,
                delivered: messages.filter(m => m.status === MESSAGE_STATE.DELIVERED).length,
                read: messages.filter(m => m.status === MESSAGE_STATE.READ).length,
                failed_upload: messages.filter(m => m.status === MESSAGE_STATE.FAILED_UPLOAD).length,
                failed_send: messages.filter(m => m.status === MESSAGE_STATE.FAILED_SEND).length,
                retrying: messages.filter(m => m.status === MESSAGE_STATE.RETRYING).length,
                cancelled: messages.filter(m => m.status === MESSAGE_STATE.CANCELLED).length
            }
        };
    }
    
    /**
     * Get CSRF token
     */
    getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }
        return '';
    }
    
    /**
     * Emit state change event
     */
    emitStateChange(tempId, oldStatus, newStatus, message) {
        const event = new CustomEvent('messageStateChange', {
            detail: { tempId, oldStatus, newStatus, message }
        });
        window.dispatchEvent(event);
    }

    /**
     * Listen for state changes
     */
    onStateChange(callback) {
        window.addEventListener('messageStateChange', (event) => {
            callback(event.detail);
        });
    }
}

// Export singleton instance
const messageQueueService = new MessageQueueService();
