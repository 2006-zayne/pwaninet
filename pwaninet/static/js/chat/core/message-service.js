/**
 * MessageService - ONLY ingestion pipeline for all messages
 * Validates, normalizes, and forwards to store using canonical schema
 * NO direct state mutations, NO UI updates, NO business logic
 */

import { store } from './store.js';
import { webSocketManager } from './websocket.js';
import { getCSRFToken } from '../shared/utils.js';

export class MessageService {
    constructor() {
        this.e2eEncryption = null;
        this.initialized = false;
        this.recipientPublicKey = null;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.messageQueue = []; // Local queue for transport only
    }

    /**
     * Initialize message service
     */
    init() {
        this._log('MESSAGE_SERVICE_INIT');
        
        // Setup encryption if available
        if (typeof E2EEncryption !== 'undefined') {
            this.e2eEncryption = new E2EEncryption();
        }

        this._log('MESSAGE_SERVICE_INITIALIZED');
        this.initialized = true;
    }

    mapStatus(status) {
        const allowed = {
            sent: 'sent',
            delivered: 'delivered',
            read: 'read',
            seen: 'read',
            received: 'delivered',
            pending: 'sent',
            failed: 'failed'
        };

        return allowed[status] || 'sent';
    }

    mapType(type) {
        const media = ['image', 'video', 'audio', 'voice', 'file'];
        if (media.includes(type)) return 'media';
        if (type === 'emoji') return 'emoji';
        if (type === 'system') return 'system';
        return 'text';
    }

    normalizeServerMessage(raw) {
        const mappedStatus = this.mapStatus(raw.read_status || raw.status);
        console.log(`[MESSAGE_SERVICE] Normalizing message ${raw.id}: raw_status='${raw.read_status || raw.status}', mapped='${mappedStatus}'`);
        return this._createCanonicalMessage({
            id: String(raw.id),
            conversationId: Number(raw.conversation || raw.conversationId),
            senderId: Number(raw.sender?.id ?? raw.sender_id),
            timestamp: new Date(raw.created_at || raw.timestamp).toISOString(),
            status: mappedStatus,
            content: raw.content || raw.body || "",
            type: this.mapType(raw.message_type || raw.type),
            metadata: raw.metadata || {},
            isOptimistic: false,
            sortOrder: new Date(raw.created_at || raw.timestamp).getTime()
        });
    }

    async loadConversationHistory(conversationId) {
        console.log('[MESSAGE_SERVICE] Loading conversation history for:', conversationId);
        try {
            console.log('[MESSAGE_SERVICE] Fetching messages from API');
            const res = await fetch(`/messaging/v1/messages/?conversation=${conversationId}`, {
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            });

            console.log('[MESSAGE_SERVICE] Fetch response status:', res.status);
            if (!res.ok) throw new Error('HTTP error');

            const data = await res.json();
            console.log('[MESSAGE_SERVICE] Received data:', data);

            // DRF ViewSet returns array directly, not object with messages property
            const messages = Array.isArray(data) ? data : (data.results || data.messages || []);
            console.log('[MESSAGE_SERVICE] Processing', messages.length, 'messages');

            for (const raw of messages) {
                store.addMessage(this.normalizeServerMessage(raw));
            }
            console.log('[MESSAGE_SERVICE] All messages added to store');

        }
        catch (error) {
            console.error('[MESSAGE_SERVICE] History load failed:', error);
            console.error('[MESSAGE_SERVICE] Error stack:', error.stack);
            throw error;
        }
        console.log('[MESSAGE_SERVICE] loadConversationHistory completed');
    }


    /**
     * Send outgoing message (UI → MessageService → WebSocket → Store)
     * @param {string} content - Message content
     * @param {Object} options - Additional options
     */
    async sendMessage(content, options = {}) {
        this._log('SEND_MESSAGE', { content, options });

        const state = store.getState();
        
        if (!content || !content.trim()) {
            this._log('SEND_MESSAGE_REJECTED', 'Empty content');
            return false;
        }

        const cleanContent = content.trim();

        // Create optimistic message with canonical schema
        const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const optimisticMessage = this._createCanonicalMessage({
            id: tempId,
            conversationId: state.conversationId,
            senderId: state.currentUserId,
            timestamp: new Date().toISOString(),
            status: 'sent',
            content: cleanContent,
            type: options.type || 'text',
            metadata: options.metadata || {},
            isOptimistic: true,
            sortOrder: Date.now()
        });

        // Add optimistic update to store (ONLY store mutates)
        store.addMessage(optimisticMessage);

        // Prepare message data for WebSocket (transport only);
        let messageData = {
            type: 'chat_message',
            temp_id : tempId,
            content: cleanContent,
            message_type: options.type || 'text',
            metadata: options.metadata || {}
        };

        // Handle encryption if needed
        if (state.isEncrypted && this.e2eEncryption && this.recipientPublicKey) {
            try {
                const encryptedContent = await this.e2eEncryption.encryptMessage(
                    cleanContent, 
                    this.recipientPublicKey
                );
                messageData = {
                    type: 'chat_message',
                    content: null,
                    temp_id: tempId,
                    encrypted_content: encryptedContent,
                    is_encrypted: true,
                    message_type: options.type || 'text',
                    metadata: options.metadata || {}
                };
                this._log('MESSAGE_ENCRYPTED', { tempId });
            } catch (error) {
                this._log('ENCRYPTION_FAILED', error);
                console.error('MessageService: Encryption failed, sending plaintext:', error);
            }
        }

        // Send via WebSocket (transport ONLY)
        const sent = await webSocketManager.send(messageData);

        if (!sent) {
            // WebSocket down - try REST API fallback
            this._log('WEBSOCKET_FAILED_TRYING_REST', { tempId });
            try {
                const response = await fetch('/messaging/v1/messages/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        conversation: state.conversationId,
                        content: cleanContent
                    })
                });

                if (!response.ok) throw new Error('HTTP error');

                const savedMessage = await response.json();

                // Replace optimistic with confirmed message
                store.replaceOptimisticMessage(tempId, this.normalizeServerMessage(savedMessage));
                this._log('MESSAGE_SENT_VIA_REST', { tempId, id: savedMessage.id });

            } catch (restError) {
                // Queue message if REST also fails
                this.messageQueue.push({
                    ...messageData,
                    tempId,
                    timestamp: new Date().toISOString()
                });
                this._log('MESSAGE_QUEUED', { tempId, reason: 'REST failed' });
                console.error('MessageService: REST fallback failed:', restError);
            }
        }

        return tempId;
    }

    /**
     * Process incoming WebSocket message (WebSocket → MessageService → Store)
     * @param {Object} data - WebSocket message data
     */
    async processIncomingMessage(data) {
        this._log('PROCESS_INCOMING_MESSAGE', data);

        try {
            switch (data.type) {
                case 'message':
                    await this._processChatMessage(data.data);
                    break;
                case 'typing':
                    this._processTypingIndicator(data);
                    break;
                case 'read_receipt':
                    this._processReadReceipt(data);
                    break;
                case 'user_status':
                    this._processUserStatus(data);
                    break;
                default:
                    this._log('UNKNOWN_MESSAGE_TYPE', data.type);
            }
        } catch (error) {
            this._log('INCOMING_MESSAGE_ERROR', { error, data });
            console.error('MessageService: Error processing incoming message:', error, data);
        }
    }

    /**
     * Process chat message with canonical schema validation
     * @param {Object} messageData - Message data
     */
    async _processChatMessage(messageData) {
        this._log('PROCESS_CHAT_MESSAGE', messageData);

        // Decrypt message if encrypted
        let content = messageData.content;

        if (messageData.is_encrypted && this.e2eEncryption) {
            try {
                content = await this.e2eEncryption.decryptMessage(messageData.encrypted_content);
                this._log('MESSAGE_DECRYPTED', { messageId: messageData.id });
            } catch (error) {
                this._log('DECRYPTION_FAILED', error);
                console.error('MessageService: Failed to decrypt message:', error);
                content = '[Encrypted message - unable to decrypt]';
            }
        }

        // Normalize to canonical schema
        const canonicalMessage = this.normalizeServerMessage({
            ...messageData,
            content
        });


        // Check if this is a confirmation of an optimistic message

        const tempId = messageData.temp_id;

        if (tempId) {
            this._handleMessageConfirmation(canonicalMessage, tempId);
        } else {
            store.addMessage(canonicalMessage);
        }
    }

    /**
     * Handle message confirmation for optimistic updates
     * @param {Object} confirmedMessage - Confirmed message from server
     */
    _handleMessageConfirmation(confirmedMessage, tempId) {
        this._log('HANDLE_MESSAGE_CONFIRMATION', confirmedMessage);

        const messages = store.getMessages();

        // Find optimistic message to replace
        const optimisticMessage = messages.find(m => m.id === tempId);
        
        if (optimisticMessage) {
            this._log('REPLACING_OPTIMISTIC_MESSAGE', {
                tempId: optimisticMessage.id,
                actualId: confirmedMessage.id
            });
            
            // Replace optimistic message with confirmed message (ONLY store mutates)
            store.replaceMessage(optimisticMessage.id, confirmedMessage);
        } else {
            // No optimistic message found, just add the confirmed one
            store.addMessage(confirmedMessage);
        }
    }

    /**
     * Process typing indicator
     * @param {Object} data - Typing data
     */
    _processTypingIndicator(data) {
        this._log('PROCESS_TYPING_INDICATOR', data);

        const state = store.getState();
        
        if (data.user_id !== state.currentUserId) {
            // Update typing indicator in store (ONLY store mutates)
            store.setTypingIndicator(data.user_id, data.username, data.is_typing);
        }
    }

    /**
     * Process read receipt from WebSocket
     * @param {Object} data - Read receipt data
     */
    _processReadReceipt(data) {
        console.log('[MESSAGE_SERVICE] Processing read receipt:', data);
        this._log('PROCESS_READ_RECEIPT', data);

        // Update message read status in store (ONLY store mutates)
        store.updateMessage(data.message_id, {
            status: 'read',
            metadata: {
                read_avatar: data.read_avatar
            }
        });
        console.log('[MESSAGE_SERVICE] Updated message', data.message_id, 'to read status with avatar:', data.read_avatar);
    }

    /**
     * Process user online/offline status
     * @param {Object} data - User status data
     */
    _processUserStatus(data) {
        this._log('PROCESS_USER_STATUS', data);

        const state = store.getState();

        // Only process if it's not the current user
        if (data.user_id !== state.currentUserId) {
            // Update peer online status in store (ONLY store mutates)
            store.setPeerOnlineStatus(data.user_id, data.is_online, data.last_seen);
        }
    }

    /**
     * Process message queue (resend queued messages)
     */
    async processMessageQueue() {
        this._log('PROCESS_MESSAGE_QUEUE');

        const queue = [...this.messageQueue];
        this.messageQueue = []; // Clear queue
        
        for (const queuedMessage of queue) {
            try {
                const messageData = {
                    type: queuedMessage.type,
                    temp_id: queuedMessage.tempId,
                    content: queuedMessage.content,
                    encrypted_content: queuedMessage.encrypted_content,
                    is_encrypted: queuedMessage.is_encrypted,
                    message_type: queuedMessage.message_type,
                    metadata: queuedMessage.metadata
                };

                const sent = await webSocketManager.send(messageData);

                if (!sent) {
                    // Re-queue if still not sent
                    this.messageQueue.push(queuedMessage);
                } else {
                    this._log('QUEUED_MESSAGE_SENT', { tempId: queuedMessage.tempId });
                }
            } catch (error) {
                this._log('QUEUE_SEND_ERROR', { error, queuedMessage });
                // Re-queue on error
                this.messageQueue.push(queuedMessage);
            }
        }
    }

    /**
     * Create canonical message object
     * @param {Object} data - Message data
     * @returns {Object} Canonical message
     */
    _createCanonicalMessage(data) {
        return {
            id: data.id,
            conversationId: data.conversationId,
            senderId: data.senderId,
            timestamp: data.timestamp,
            status: data.status,
            content: data.content,
            type: data.type,
            metadata: data.metadata || {},
            isOptimistic: data.isOptimistic || false,
            sortOrder: data.sortOrder ?? Date.now()
        };
    }

    /**
     * Set recipient public key for encryption
     * @param {string} publicKey - Recipient's public key
     */
    setRecipientPublicKey(publicKey) {
        this._log('SET_RECIPIENT_PUBLIC_KEY');
        this.recipientPublicKey = publicKey;
    }

    /**
     * Send read receipt for a message
     * @param {string} messageId - Message ID to mark as read
     */
    sendReadReceipt(messageId) {
        console.log('[MESSAGE_SERVICE] Sending read receipt for message:', messageId);
        this._log('SEND_READ_RECEIPT', { messageId });

        if (!messageId) {
            console.log('[MESSAGE_SERVICE] No messageId provided, skipping read receipt');
            return false;
        }

        // Send via WebSocket (transport ONLY)
        const sent = webSocketManager.send({
            type: 'read_receipt',
            message_id: messageId
        });

        if (sent) {
            console.log('[MESSAGE_SERVICE] Read receipt sent successfully for:', messageId);
            this._log('READ_RECEIPT_SENT', { messageId });
        } else {
            console.log('[MESSAGE_SERVICE] Read receipt FAILED for:', messageId, '- WebSocket not connected, queuing...');
            this._log('READ_RECEIPT_FAILED', { messageId });
            
            // Queue the read receipt for when WebSocket reconnects
            this.queueReadReceipt(messageId);
        }

        return sent;
    }

    /**
     * Queue a read receipt to send later when WebSocket reconnects
     * @param {string} messageId - Message ID to queue
     */
    queueReadReceipt(messageId) {
        // Add to read receipt queue (avoid duplicates)
        if (!this.readReceiptQueue) {
            this.readReceiptQueue = new Set();
        }
        this.readReceiptQueue.add(messageId);
        console.log('[MESSAGE_SERVICE] Queued read receipt for:', messageId, 'Queue size:', this.readReceiptQueue.size);
    }

    /**
     * Send all queued read receipts when WebSocket reconnects
     */
    sendQueuedReadReceipts() {
        if (!this.readReceiptQueue || this.readReceiptQueue.size === 0) {
            return;
        }

        console.log('[MESSAGE_SERVICE] Sending', this.readReceiptQueue.size, 'queued read receipts');
        const messageIds = Array.from(this.readReceiptQueue);
        this.readReceiptQueue.clear();
        
        // Send all queued read receipts
        messageIds.forEach(messageId => {
            webSocketManager.send({
                type: 'read_receipt',
                message_id: messageId
            });
        });
    }

    /**
     * Mark multiple messages as read (batch operation)
     * @param {Array} messageIds - Array of message IDs to mark as read
     */
    markMessagesAsRead(messageIds) {
        if (!Array.isArray(messageIds) || messageIds.length === 0) {
            console.log('[MESSAGE_SERVICE] No message IDs to mark as read');
            return;
        }

        console.log('[MESSAGE_SERVICE] Marking', messageIds.length, 'messages as read:', messageIds);
        this._log('MARK_MESSAGES_AS_READ', { count: messageIds.length });

        // Send read receipt for each message
        messageIds.forEach(messageId => {
            this.sendReadReceipt(messageId);
        });
    }

    /**
     * Get service status
     * @returns {Object} Service status
     */
    getStatus() {
        return {
            initialized: this.initialized,
            encryptionEnabled: !!this.e2eEncryption,
            hasRecipientKey: !!this.recipientPublicKey,
            queueSize: this.messageQueue.length
        };
    }

    /**
     * Validate message consistency
     * @returns {Object} Validation results
     */
    validateConsistency() {
        return store.validateMessageConsistency();
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[MESSAGE_SERVICE] ${action}:`, data);
        }
    }
}

// Create and export singleton instance
export const messageService = new MessageService();
