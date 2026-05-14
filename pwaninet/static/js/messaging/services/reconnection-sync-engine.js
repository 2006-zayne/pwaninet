/**
 * Reconnection Sync Engine
 * 
 * Handles synchronization when WebSocket reconnects:
 * - Restores pending message queue
 * - Retries failed uploads
 * - Syncs optimistic messages
 * - Fetches missed messages
 * - Reconciles temp IDs with server message IDs
 */

class ReconnectionSyncEngine {
    constructor(messageQueueService) {
        this.messageQueueService = messageQueueService;
        this.isSyncing = false;
        this.syncInProgress = false;
        this.lastSyncTimestamp = null;
        this.pendingSync = false;
        
        // Sync states
        this.SYNC_STATES = {
            IDLE: 'idle',
            RESTORING_QUEUE: 'restoring_queue',
            SYNCING_OPTIMISTIC: 'syncing_optimistic',
            FETCHING_MISSED: 'fetching_missed',
            RECONCILING: 'reconciling',
            COMPLETE: 'complete'
        };
        
        this.currentSyncState = this.SYNC_STATES.IDLE;
    }
    
    /**
     * Initialize sync engine
     */
    async init() {
        // Listen for WebSocket connection events
        this.setupWebSocketListeners();
        
        // Listen for message state changes
        this.messageQueueService.onStateChange((detail) => {
            this.handleMessageStateChange(detail);
        });
    }
    
    /**
     * Setup WebSocket event listeners
     */
    setupWebSocketListeners() {
        window.addEventListener('websocket:connected', () => {
            console.log('[RECONNECTION_SYNC] WebSocket connected, starting sync');
            this.onReconnect();
        });
        
        window.addEventListener('websocket:disconnected', () => {
            console.log('[RECONNECTION_SYNC] WebSocket disconnected');
            this.onDisconnect();
        });
        
        window.addEventListener('websocket:reconnecting', () => {
            console.log('[RECONNECTION_SYNC] WebSocket reconnecting');
        });
    }
    
    /**
     * Handle WebSocket reconnection
     */
    async onReconnect() {
        if (this.isSyncing) {
            console.log('[RECONNECTION_SYNC] Sync already in progress, queuing');
            this.pendingSync = true;
            return;
        }
        
        this.isSyncing = true;
        this.currentSyncState = this.SYNC_STATES.RESTORING_QUEUE;
        
        try {
            // Step 1: Restore pending queue
            await this.restorePendingQueue();
            
            // Step 2: Retry failed uploads
            await this.retryFailedUploads();
            
            // Step 3: Sync optimistic messages
            await this.syncOptimisticMessages();
            
            // Step 4: Fetch missed messages
            await this.fetchMissedMessages();
            
            // Step 5: Reconcile temp IDs
            await this.reconcileTempIds();
            
            this.currentSyncState = this.SYNC_STATES.COMPLETE;
            this.lastSyncTimestamp = Date.now();
            
            console.log('[RECONNECTION_SYNC] Sync complete');
            
            // Emit sync complete event
            this.emitSyncComplete();
            
        } catch (error) {
            console.error('[RECONNECTION_SYNC] Sync failed:', error);
            this.emitSyncError(error);
        } finally {
            this.isSyncing = false;
            
            // Process pending sync if any
            if (this.pendingSync) {
                this.pendingSync = false;
                setTimeout(() => this.onReconnect(), 1000);
            }
        }
    }
    
    /**
     * Handle WebSocket disconnection
     */
    onDisconnect() {
        console.log('[RECONNECTION_SYNC] Pausing sync operations');
        this.currentSyncState = this.SYNC_STATES.IDLE;
    }
    
    /**
     * Restore pending message queue from IndexedDB
     */
    async restorePendingQueue() {
        console.log('[RECONNECTION_SYNC] Restoring pending queue');
        this.currentSyncState = this.SYNC_STATES.RESTORING_QUEUE;
        
        // Reload queue from IndexedDB
        await this.messageQueueService.loadQueueFromDB();
        
        const stats = this.messageQueueService.getStats();
        console.log(`[RECONNECTION_SYNC] Queue restored: ${stats.total} messages`);
        
        this.emitSyncProgress('queue_restored', stats);
    }
    
    /**
     * Retry failed uploads
     */
    async retryFailedUploads() {
        console.log('[RECONNECTION_SYNC] Retrying failed uploads');
        this.currentSyncState = this.SYNC_STATES.RESTORING_QUEUE;
        
        const failedMessages = this.messageQueueService.getMessagesByStatus('failed');
        const retryingMessages = this.messageQueueService.getMessagesByStatus('retrying');
        
        const messagesToRetry = [...failedMessages, ...retryingMessages];
        
        console.log(`[RECONNECTION_SYNC] Found ${messagesToRetry.length} messages to retry`);
        
        for (const message of messagesToRetry) {
            if (message.retryCount < message.maxRetries) {
                await this.messageQueueService.transitionMessage(
                    message.tempId,
                    'queued',
                    { retryCount: 0, lastError: null }
                );
            }
        }
        
        // Trigger upload queue processing
        await this.messageQueueService.retryFailedMessages();
        
        this.emitSyncProgress('uploads_retried', { count: messagesToRetry.length });
    }
    
    /**
     * Sync optimistic messages with server
     */
    async syncOptimisticMessages() {
        console.log('[RECONNECTION_SYNC] Syncing optimistic messages');
        this.currentSyncState = this.SYNC_STATES.SYNCING_OPTIMISTIC;
        
        const sentMessages = this.messageQueueService.getMessagesByStatus('sent');
        const deliveredMessages = this.messageQueueService.getMessagesByStatus('delivered');
        const readMessages = this.messageQueueService.getMessagesByStatus('read');
        
        const optimisticMessages = [...sentMessages, ...deliveredMessages, ...readMessages];
        
        console.log(`[RECONNECTION_SYNC] Syncing ${optimisticMessages.length} optimistic messages`);
        
        // For each optimistic message, verify it exists on server
        for (const message of optimisticMessages) {
            if (message.serverMessageId) {
                await this.verifyMessageOnServer(message);
            }
        }
        
        this.emitSyncProgress('optimistic_synced', { count: optimisticMessages.length });
    }
    
    /**
     * Verify message exists on server
     */
    async verifyMessageOnServer(message) {
        try {
            const response = await fetch(`/messaging/api/v1/messages/${message.serverMessageId}/`, {
                headers: {
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            if (!response.ok) {
                console.warn(`[RECONNECTION_SYNC] Message ${message.serverMessageId} not found on server`);
                // Mark as failed for retry
                await this.messageQueueService.transitionMessage(message.tempId, 'failed', {
                    lastError: 'Message not found on server'
                });
            }
        } catch (error) {
            console.error(`[RECONNECTION_SYNC] Failed to verify message ${message.serverMessageId}:`, error);
        }
    }
    
    /**
     * Fetch missed messages from server
     */
    async fetchMissedMessages() {
        console.log('[RECONNECTION_SYNC] Fetching missed messages');
        this.currentSyncState = this.SYNC_STATES.FETCHING_MISSED;
        
        // Get the last known message timestamp from the queue
        const allMessages = Array.from(this.messageQueueService.queue.values());
        const lastMessage = allMessages.sort((a, b) => b.created - a.created)[0];
        
        if (!lastMessage) {
            console.log('[RECONNECTION_SYNC] No messages in queue, skipping missed fetch');
            return;
        }
        
        // Fetch messages since last sync
        const conversations = new Set(allMessages.map(m => m.conversationId));
        
        for (const conversationId of conversations) {
            await this.fetchConversationMessages(conversationId, lastMessage.created);
        }
        
        this.emitSyncProgress('missed_fetched', { conversations: Array.from(conversations) });
    }
    
    /**
     * Fetch messages for a specific conversation
     */
    async fetchConversationMessages(conversationId, sinceTimestamp) {
        try {
            const sinceDate = new Date(sinceTimestamp).toISOString();
            
            const response = await fetch(
                `/messaging/api/v1/messages/paginated/?conversation_id=${conversationId}&limit=50`,
                {
                    headers: {
                        'X-CSRFToken': this.getCSRFToken()
                    }
                }
            );
            
            if (!response.ok) {
                throw new Error(`Failed to fetch messages: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Emit event for UI to handle new messages
            this.emitMessagesFetched(conversationId, data.results);
            
        } catch (error) {
            console.error(`[RECONNECTION_SYNC] Failed to fetch messages for conversation ${conversationId}:`, error);
        }
    }
    
    /**
     * Reconcile temp IDs with server message IDs
     */
    async reconcileTempIds() {
        console.log('[RECONNECTION_SYNC] Reconciling temp IDs');
        this.currentSyncState = this.SYNC_STATES.RECONCILING;
        
        const allMessages = Array.from(this.messageQueueService.queue.values());
        const messagesWithoutServerId = allMessages.filter(m => !m.serverMessageId && m.status === 'sent');
        
        console.log(`[RECONNECTION_SYNC] Found ${messagesWithoutServerId.length} messages without server ID`);
        
        // For messages marked as sent but without server ID, try to find them by temp_id
        for (const message of messagesWithoutServerId) {
            await this.findMessageByTempId(message);
        }
        
        // Clean up old sent/delivered/read messages (older than 7 days)
        await this.cleanupOldMessages();
        
        this.emitSyncProgress('reconciled', { count: messagesWithoutServerId.length });
    }
    
    /**
     * Find message by temp ID on server
     */
    async findMessageByTempId(message) {
        try {
            // This would require a server endpoint to search by temp_id
            // For now, we'll mark it as failed if it doesn't have a server ID
            const messageAge = Date.now() - message.created;
            
            if (messageAge > 3600000) { // 1 hour old
                console.warn(`[RECONNECTION_SYNC] Message ${message.tempId} is old without server ID, marking as failed`);
                await this.messageQueueService.transitionMessage(message.tempId, 'failed', {
                    lastError: 'Message too old without server ID'
                });
            }
        } catch (error) {
            console.error(`[RECONNECTION_SYNC] Failed to find message ${message.tempId}:`, error);
        }
    }
    
    /**
     * Clean up old messages from queue
     */
    async cleanupOldMessages() {
        const allMessages = Array.from(this.messageQueueService.queue.values());
        const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
        
        const oldMessages = allMessages.filter(m => 
            m.created < oneWeekAgo && 
            ['sent', 'delivered', 'read'].includes(m.status)
        );
        
        console.log(`[RECONNECTION_SYNC] Cleaning up ${oldMessages.length} old messages`);
        
        for (const message of oldMessages) {
            await this.messageQueueService.deleteMessage(message.tempId);
        }
        
        this.emitSyncProgress('cleaned_up', { count: oldMessages.length });
    }
    
    /**
     * Handle message state changes
     */
    handleMessageStateChange(detail) {
        const { tempId, oldStatus, newStatus, message } = detail;
        
        // If message transitions to sent/delivered/read, update last sync timestamp
        if (['sent', 'delivered', 'read'].includes(newStatus)) {
            this.lastSyncTimestamp = Date.now();
        }
        
        // If message fails during sync, handle it
        if (this.isSyncing && newStatus === 'failed') {
            console.log(`[RECONNECTION_SYNC] Message ${tempId} failed during sync`);
        }
    }
    
    /**
     * Get current sync state
     */
    getSyncState() {
        return {
            isSyncing: this.isSyncing,
            currentSyncState: this.currentSyncState,
            lastSyncTimestamp: this.lastSyncTimestamp,
            pendingSync: this.pendingSync
        };
    }
    
    /**
     * Force a full sync
     */
    async forceSync() {
        console.log('[RECONNECTION_SYNC] Forcing full sync');
        this.pendingSync = false;
        await this.onReconnect();
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
     * Emit sync progress event
     */
    emitSyncProgress(stage, data) {
        const event = new CustomEvent('syncProgress', {
            detail: { stage, data, state: this.currentSyncState }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Emit sync complete event
     */
    emitSyncComplete() {
        const event = new CustomEvent('syncComplete', {
            detail: { timestamp: this.lastSyncTimestamp }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Emit sync error event
     */
    emitSyncError(error) {
        const event = new CustomEvent('syncError', {
            detail: { error, state: this.currentSyncState }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Emit messages fetched event
     */
    emitMessagesFetched(conversationId, messages) {
        const event = new CustomEvent('messagesFetched', {
            detail: { conversationId, messages }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Listen for sync events
     */
    onSyncProgress(callback) {
        window.addEventListener('syncProgress', (event) => {
            callback(event.detail);
        });
    }
    
    onSyncComplete(callback) {
        window.addEventListener('syncComplete', (event) => {
            callback(event.detail);
        });
    }
    
    onSyncError(callback) {
        window.addEventListener('syncError', (event) => {
            callback(event.detail);
        });
    }
    
    onMessagesFetched(callback) {
        window.addEventListener('messagesFetched', (event) => {
            callback(event.detail);
        });
    }
}

// Export class
export default ReconnectionSyncEngine;
