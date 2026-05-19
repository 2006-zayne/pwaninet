/**
 * MessageService - ONLY ingestion pipeline for all messages
 * Validates, normalizes, and forwards to store using canonical schema
 * NO direct state mutations, NO UI updates, NO business logic
 */

import { store } from './store.js';
import { webSocketManager } from './websocket.js';
import { eventBus } from './event-bus.js';
import { getCSRFToken } from '../shared/utils.js';
import { EVENTS, MESSAGE_STATE, CONNECTION_STATE, isValidStateTransition } from '../shared/constants.js';
import { messageSoundManager } from '../shared/message-sound.js';

export class MessageService {
    constructor() {
        this.e2eEncryption = null;
        this.initialized = false;
        this.recipientPublicKey = null;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.messageQueue = []; // Local queue for transport only
        
        // Track message states by temp_id for transition validation
        this.messageStates = new Map();
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

        // Setup optimistic messaging event listeners
        this._setupOptimisticMessagingListeners();

        this._log('MESSAGE_SERVICE_INITIALIZED');
        this.initialized = true;
    }

    /**
     * Setup optimistic messaging event listeners
     */
    _setupOptimisticMessagingListeners() {
        // Handle optimistic message add (show temporary message while uploading)
        eventBus.on(EVENTS.MESSAGE_OPTIMISTIC_ADD, (message) => {
            this._handleOptimisticAdd(message);
        });

        // Handle upload success (replace optimistic message with server message)
        eventBus.on(EVENTS.MESSAGE_UPLOAD_SUCCESS, (data) => {
            this._handleUploadSuccess(data);
        });

        // Handle upload failure (mark optimistic message as failed)
        eventBus.on(EVENTS.MESSAGE_UPLOAD_FAILED, (data) => {
            this._handleUploadFailure(data);
        });
    }

    /**
     * Handle optimistic message add
     * @param {Object} message - Optimistic message
     */
    _handleOptimisticAdd(message) {
        console.log('[MESSAGE_SERVICE] Handling optimistic message add');
        console.log('[MESSAGE_SERVICE] [DEBUG] FULL INPUT MESSAGE:', JSON.stringify(message, null, 2));
        console.log('[MESSAGE_SERVICE] [DEBUG] INPUT ATTACHMENTS (top-level):', message.attachments);
        console.log('[MESSAGE_SERVICE] [DEBUG] INPUT METADATA:', message.metadata);
        console.log('[MESSAGE_SERVICE] [DEBUG] INPUT METADATA ATTACHMENTS:', message.metadata?.attachments);
        
        const state = store.getState();
        console.log('[MESSAGE_SERVICE] Current state:', state);
        
        if (!state.conversationId) {
            console.error('[MESSAGE_SERVICE] No conversation ID in state');
            return;
        }
        
        if (!state.currentUserId) {
            console.error('[MESSAGE_SERVICE] No current user ID in state');
            return;
        }
        
        const canonicalMessage = this._createCanonicalMessage({
            id: message.temp_id,
            conversationId: state.conversationId,
            senderId: state.currentUserId,
            timestamp: message.created_at,
            status: MESSAGE_STATE.UPLOADING,
            content: message.content || '',
            type: message.message_type || message.type || 'media_group',
            metadata: {
                attachments: message.attachments,
                global_caption: message.global_caption
            },
            isOptimistic: true,
            sortOrder: Date.now()
        });

        console.log('[MESSAGE_SERVICE] [DEBUG] CANONICAL MESSAGE CREATED:', JSON.stringify(canonicalMessage, null, 2));
        console.log('[MESSAGE_SERVICE] [DEBUG] CANONICAL ATTACHMENTS (top-level):', canonicalMessage.attachments);
        console.log('[MESSAGE_SERVICE] [DEBUG] CANONICAL METADATA:', canonicalMessage.metadata);
        console.log('[MESSAGE_SERVICE] [DEBUG] CANONICAL METADATA ATTACHMENTS:', canonicalMessage.metadata?.attachments);
        console.log('[MESSAGE_SERVICE] Adding canonical message to store');
        store.addMessage(canonicalMessage);
    }

    /**
     * Handle upload success
     * @param {Object} data - Upload success data with tempId and serverMessage
     */
    _handleUploadSuccess(data) {
        console.log('[MESSAGE_SERVICE] Handling upload success:', data);
        
        const { tempId, serverMessage } = data;
        
        if (!tempId) {
            console.error('[MESSAGE_SERVICE] No tempId in upload success data');
            return;
        }
        
        if (!serverMessage) {
            console.error('[MESSAGE_SERVICE] No serverMessage in upload success data');
            return;
        }
        
        // Remove optimistic message
        console.log('[MESSAGE_SERVICE] Removing optimistic message:', tempId);
        store.removeMessage(tempId);
        
        // Add server message
        console.log('[MESSAGE_SERVICE] Adding server message:', serverMessage);
        const normalizedMessage = this.normalizeServerMessage(serverMessage);
        store.addMessage(normalizedMessage);
    }

    /**
     * Handle upload failure
     * @param {Object} data - Upload failure data with tempId and error
     */
    _handleUploadFailure(data) {
        console.log('[MESSAGE_SERVICE] Handling upload failure:', data);
        
        const { tempId, error } = data;
        
        if (!tempId) {
            console.error('[MESSAGE_SERVICE] No tempId in upload failure data');
            return;
        }
        
        // Update optimistic message status to failed
        console.log('[MESSAGE_SERVICE] Updating message status to failed:', tempId);
        store.updateMessageStatus(tempId, MESSAGE_STATE.FAILED_UPLOAD, {
            error: error
        });
    }

    mapStatus(status) {
        // Map legacy/alternative status names to unified MESSAGE_STATE
        const allowed = {
            draft: MESSAGE_STATE.DRAFT,
            queued: MESSAGE_STATE.QUEUED,
            processing: MESSAGE_STATE.PROCESSING,
            uploading: MESSAGE_STATE.UPLOADING,
            sending: MESSAGE_STATE.SENDING,
            sent: MESSAGE_STATE.SENT,
            delivered: MESSAGE_STATE.DELIVERED,
            read: MESSAGE_STATE.READ,
            seen: MESSAGE_STATE.READ,
            received: MESSAGE_STATE.DELIVERED,
            pending: MESSAGE_STATE.QUEUED,
            failed: MESSAGE_STATE.FAILED_SEND, // Default failed to failed_send
            failed_upload: MESSAGE_STATE.FAILED_UPLOAD,
            failed_send: MESSAGE_STATE.FAILED_SEND,
            retrying: MESSAGE_STATE.RETRYING,
            cancelled: MESSAGE_STATE.CANCELLED
        };

        const mapped = allowed[status];
        if (mapped) {
            console.log('[MESSAGE_SERVICE] mapStatus:', status, '->', mapped);
            return mapped;
        }
        console.log('[MESSAGE_SERVICE] mapStatus: unknown status', status, 'defaulting to SENT');
        return MESSAGE_STATE.SENT;
    }

    mapType(type) {
        const media = ['image', 'video', 'audio', 'voice', 'file'];
        if (media.includes(type)) return 'media';
        if (type === 'emoji') return 'emoji';
        if (type === 'system') return 'system';
        if (type === 'link') return 'link';
        return 'text';
    }

    normalizeServerMessage(raw) {
        const mappedStatus = this.mapStatus(raw.read_status || raw.status);
        console.log(`[MESSAGE_SERVICE] Normalizing message ${raw.id}: raw_status='${raw.read_status || raw.status}', mapped='${mappedStatus}'`);
        console.log(`[MESSAGE_SERVICE] Raw data - link_url:`, raw.link_url, 'link_type:', raw.link_type, 'attachment_url:', raw.attachment_url);
        
        // Build metadata with attachment information if present
        const metadata = raw.metadata || {};
        if (raw.attachment_url) {
            metadata.url = raw.attachment_url;
            metadata.type = raw.attachment_type || 'file';
        }
        
        // Add link metadata if present
        if (raw.link_url) {
            console.log('[MESSAGE_SERVICE] Link metadata found:', raw.link_url);
            metadata.link_url = raw.link_url;
            metadata.link_title = raw.link_title;
            metadata.link_description = raw.link_description;
            metadata.link_image = raw.link_image;
            metadata.link_type = raw.link_type;
        }
        
        // Determine message type based on attachment, media_group, or link
        let messageType = this.mapType(raw.message_type || raw.type);
        if (raw.message_type === 'media_group') {
            messageType = 'media_group';
        } else if (raw.attachment_type) {
            messageType = 'media';
        } else if (raw.link_url) {
            console.log('[MESSAGE_SERVICE] Setting message type to link');
            messageType = 'link';
        }
        
        // Add attachments to metadata if present
        if (raw.attachments && Array.isArray(raw.attachments)) {
            metadata.attachments = raw.attachments;
        }
        
        // Add global caption to metadata if present
        if (raw.global_caption) {
            metadata.global_caption = raw.global_caption;
        }
        
        return this._createCanonicalMessage({
            id: String(raw.id),
            conversationId: Number(raw.conversation || raw.conversationId),
            senderId: Number(raw.sender?.id ?? raw.sender_id),
            timestamp: new Date(raw.created_at || raw.timestamp).toISOString(),
            status: mappedStatus,
            content: raw.content || raw.body || "",
            type: messageType,
            metadata: metadata,
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
        
        // Create temp ID
        const tempId = `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Initialize message state as DRAFT
        this.messageStates.set(tempId, {
            status: MESSAGE_STATE.DRAFT,
            retryCount: 0,
            lastError: null,
            createdAt: Date.now()
        });
        
        // Detect URLs in content and fetch metadata
        const urls = this.extractUrls(cleanContent);
        let linkMetadata = null;
        
        if (urls.length > 0) {
            // Use the first URL found
            const url = urls[0];
            try {
                linkMetadata = await this.fetchLinkMetadata(url);
                this._log('LINK_METADATA_FETCHED', linkMetadata);
            } catch (error) {
                this._log('LINK_METADATA_FETCH_FAILED', error);
                console.error('Failed to fetch link metadata:', error);
            }
        }

        // Create optimistic message with DRAFT status
        const optimisticMessage = this._createCanonicalMessage({
            id: tempId,
            conversationId: state.conversationId,
            senderId: state.currentUserId,
            timestamp: new Date().toISOString(),
            status: MESSAGE_STATE.DRAFT,
            content: cleanContent,
            type: options.type || 'text',
            metadata: options.metadata || {},
            isOptimistic: true,
            sortOrder: Date.now()
        });

        // Add optimistic update to store (ONLY store mutates)
        store.addMessage(optimisticMessage);
        console.log('[MESSAGE_SERVICE] Message added to store with status:', optimisticMessage.status);

        // Transition to QUEUED (with delay for UI to render)
        setTimeout(() => {
            this._transitionMessageState(tempId, MESSAGE_STATE.QUEUED);
            store.updateMessage(tempId, { 
                status: MESSAGE_STATE.QUEUED,
                metadata: { ...options.metadata, queuedAt: Date.now() }
            });
            console.log('[MESSAGE_SERVICE] Status updated to QUEUED for:', tempId);
        }, 3000);

        // Prepare message data for WebSocket (transport only)
        let messageData = {
            type: 'chat_message',
            temp_id : tempId,
            content: cleanContent,
            message_type: options.type || 'text',
            metadata: options.metadata || {}
        };
        
        // Add link metadata if available
        if (linkMetadata) {
            messageData.link_url = linkMetadata.url;
            messageData.link_title = linkMetadata.title;
            messageData.link_description = linkMetadata.description;
            messageData.link_image = linkMetadata.image;
            messageData.link_type = linkMetadata.type;
        }

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

        // Transition to SENDING (with delay for UI to render)
        setTimeout(() => {
            this._transitionMessageState(tempId, MESSAGE_STATE.SENDING);
            store.updateMessage(tempId, { status: MESSAGE_STATE.SENDING });
            console.log('[MESSAGE_SERVICE] Status updated to SENDING for:', tempId);

            // Send via WebSocket (transport ONLY)
            webSocketManager.send(messageData).then(sent => {
                if (!sent) {
                    // WebSocket down - try REST API fallback
                    this._log('WEBSOCKET_FAILED_TRYING_REST', { tempId });
                    fetch('/messaging/v1/messages/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCSRFToken()
                        },
                        body: JSON.stringify({
                            conversation: state.conversationId,
                            content: cleanContent
                        })
                    }).then(response => {
                        if (!response.ok) throw new Error('HTTP error');
                        return response.json();
                    }).then(savedMessage => {
                        // Transition to SENT with delay
                        setTimeout(() => {
                            this._transitionMessageState(tempId, MESSAGE_STATE.SENT);
                            console.log('[MESSAGE_SERVICE] Status updated to SENT for:', tempId);
                            
                            // Replace optimistic with confirmed message
                            store.replaceOptimisticMessage(tempId, this.normalizeServerMessage(savedMessage));
                            this._log('MESSAGE_SENT_VIA_REST', { tempId, id: savedMessage.id });
                        }, 2000);
                    }).catch(restError => {
                        // Transition to FAILED
                        this._transitionMessageState(tempId, MESSAGE_STATE.FAILED_SEND, restError.message);
                        store.updateMessage(tempId, { status: MESSAGE_STATE.FAILED_SEND });
                        console.log('[MESSAGE_SERVICE] Status updated to FAILED for:', tempId);

                        // Queue message for retry
                        this.messageQueue.push({
                            ...messageData,
                            tempId,
                            timestamp: new Date().toISOString()
                        });
                        this._log('MESSAGE_QUEUED', { tempId, reason: 'REST failed' });
                        console.error('MessageService: REST fallback failed:', restError);
                    });
                } else {
                    // WebSocket sent successfully, transition to SENT with delay
                    setTimeout(() => {
                        this._transitionMessageState(tempId, MESSAGE_STATE.SENT);
                        store.updateMessage(tempId, { status: MESSAGE_STATE.SENT });
                        console.log('[MESSAGE_SERVICE] Status updated to SENT for:', tempId);
                    }, 2000);
                }
            });
        }, 3000);

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
                case 'message_delivered':
                    this._processMessageDelivered(data);
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

        // DEBUG: Check for link data
        console.log('[MESSAGE_SERVICE] Processing message:', messageData.id, 'Link URL:', messageData.link_url, 'Link Type:', messageData.link_type);

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

        // DEBUG: Log canonical message type
        console.log('[MESSAGE_SERVICE] Canonical message type:', canonicalMessage.type, 'Metadata:', canonicalMessage.metadata);

        // Send delivery acknowledgement if this is an incoming message (not from current user)
        const state = store.getState();
        if (canonicalMessage.senderId !== state.currentUserId) {
            this._sendDeliveryAcknowledgement(canonicalMessage.id);
        }

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
            status: MESSAGE_STATE.READ,
            metadata: {
                read_avatar: data.read_avatar
            }
        });
        console.log('[MESSAGE_SERVICE] Updated message', data.message_id, 'to read status with avatar:', data.read_avatar);
    }

    /**
     * Process message delivered status from WebSocket
     * @param {Object} data - Message delivered data
     */
    _processMessageDelivered(data) {
        console.log('[MESSAGE_SERVICE] Processing message delivered:', data);
        this._log('PROCESS_MESSAGE_DELIVERED', data);

        const state = store.getState();
        const message = store.getMessageById(data.message_id);

        // Only update if message hasn't been read yet (keep read status if it exists)
        if (message && message.status === 'sent') {
            store.updateMessage(data.message_id, {
                status: 'delivered'
            });
            console.log('[MESSAGE_SERVICE] Updated message', data.message_id, 'to delivered status');
        }
    }

    /**
     * Process user online/offline status
     * @param {Object} data - User status data
     */
    _processUserStatus(data) {
        this._log('PROCESS_USER_STATUS', data);

        const state = store.getState();

        console.log('[MESSAGE SERVICE] Received user_status', data);

        // Only process if it's not the current user
        if (data.user_id !== state.currentUserId) {
            // Update peer online status in store (ONLY store mutates)
            console.log('[MESSAGE SERVICE] Updating peer status', data.user_id, data.is_online, data.last_seen);
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
                const tempId = queuedMessage.tempId;
                
                // Transition to RETRYING
                this._transitionMessageState(tempId, MESSAGE_STATE.RETRYING);
                store.updateMessage(tempId, { status: MESSAGE_STATE.RETRYING });
                
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
                    // Transition back to FAILED_SEND
                    this._transitionMessageState(tempId, MESSAGE_STATE.FAILED_SEND, 'Retry failed');
                    store.updateMessage(tempId, { status: MESSAGE_STATE.FAILED_SEND });
                } else {
                    // Transition to SENT
                    this._transitionMessageState(tempId, MESSAGE_STATE.SENT);
                    this._log('QUEUED_MESSAGE_SENT', { tempId });
                }
            } catch (error) {
                this._log('QUEUE_SEND_ERROR', { error, queuedMessage });
                // Re-queue on error
                this.messageQueue.push(queuedMessage);
            }
        }
    }
    
    /**
     * Transition message state with validation
     * @param {string} tempId - Temporary message ID
     * @param {string} newState - New state
     * @param {string} error - Error message if transitioning to FAILED state
     */
    _transitionMessageState(tempId, newState, error = null) {
        const currentState = this.messageStates.get(tempId);
        if (!currentState) {
            console.warn('[MESSAGE_SERVICE] No state found for tempId:', tempId);
            return;
        }
        
        const oldState = currentState.status;
        
        // Validate transition
        if (!isValidStateTransition(oldState, newState)) {
            console.error('[MESSAGE_SERVICE] Invalid state transition:', {
                tempId,
                from: oldState,
                to: newState,
                error
            });
            // Reject invalid transition
            return;
        }
        
        // Update state
        currentState.status = newState;
        if (error) {
            currentState.lastError = error;
            currentState.retryCount++;
        }
        
        this.messageStates.set(tempId, currentState);
        this._log('STATE_TRANSITION', { tempId, from: oldState, to: newState, error });
        
        // Play sound for queued/sending → sent transitions
        if (messageSoundManager.shouldPlaySound(oldState, newState)) {
            messageSoundManager.playSendSound(tempId);
        }
        
        // Clean up old states for sent/delivered/read messages
        if ([MESSAGE_STATE.SENT, MESSAGE_STATE.DELIVERED, MESSAGE_STATE.READ].includes(newState)) {
            // Keep state for a while, then clean up
            setTimeout(() => {
                this.messageStates.delete(tempId);
            }, 60000); // 1 minute
        }
    }
    
    /**
     * Retry a failed message
     * @param {string} tempId - Temporary message ID
     */
    async retryMessage(tempId) {
        this._log('RETRY_MESSAGE', { tempId });
        
        const messageState = this.messageStates.get(tempId);
        if (!messageState) {
            console.warn('[MESSAGE_SERVICE] No state found for retry:', tempId);
            return false;
        }
        
        if (messageState.status !== MESSAGE_STATE.FAILED_SEND && messageState.status !== MESSAGE_STATE.FAILED_UPLOAD) {
            console.warn('[MESSAGE_SERVICE] Cannot retry message in state:', messageState.status);
            return false;
        }
        
        // Find the message in the queue
        const queuedMessage = this.messageQueue.find(m => m.tempId === tempId);
        if (!queuedMessage) {
            console.warn('[MESSAGE_SERVICE] No queued message found for retry:', tempId);
            return false;
        }
        
        // Transition to RETRYING
        this._transitionMessageState(tempId, MESSAGE_STATE.RETRYING);
        store.updateMessage(tempId, { status: MESSAGE_STATE.RETRYING });
        
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
            
            if (sent) {
                // Transition to SENT
                this._transitionMessageState(tempId, MESSAGE_STATE.SENT);
                store.updateMessage(tempId, { status: MESSAGE_STATE.SENT });
                
                // Remove from queue
                this.messageQueue = this.messageQueue.filter(m => m.tempId !== tempId);
                
                this._log('RETRY_SUCCESS', { tempId });
                return true;
            } else {
                // Transition back to FAILED_SEND
                this._transitionMessageState(tempId, MESSAGE_STATE.FAILED_SEND, 'Retry failed');
                store.updateMessage(tempId, { status: MESSAGE_STATE.FAILED_SEND });
                this._log('RETRY_FAILED', { tempId });
                return false;
            }
        } catch (error) {
            // Transition back to FAILED_SEND
            this._transitionMessageState(tempId, MESSAGE_STATE.FAILED_SEND, error.message);
            store.updateMessage(tempId, { status: MESSAGE_STATE.FAILED_SEND });
            this._log('RETRY_ERROR', { tempId, error });
            return false;
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
     * Send typing indicator to backend
     * @param {boolean} isTyping - Whether user is typing
     */
    sendTypingIndicator(isTyping) {
        this._log('SEND_TYPING_INDICATOR', { isTyping });
        console.log('[MESSAGE_SERVICE] Sending typing indicator:', isTyping);

        // Send via WebSocket (transport ONLY)
        const sent = webSocketManager.send({
            type: 'typing_indicator',
            is_typing: isTyping
        });

        console.log('[MESSAGE_SERVICE] Typing indicator sent:', sent);
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

    /**
     * Extract URLs from text
     * @param {string} text - Text to search for URLs
     * @returns {Array} Array of URLs found
     */
    extractUrls(text) {
        const urlPattern = /(https?:\/\/[^\s]+)/g;
        const matches = text.match(urlPattern);
        return matches || [];
    }

    /**
     * Fetch link metadata from backend
     * @param {string} url - URL to fetch metadata for
     * @returns {Object} Link metadata
     */
    async fetchLinkMetadata(url) {
        try {
            const response = await fetch('/messaging/api/links/fetch-metadata/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ url })
            });

            if (!response.ok) {
                throw new Error('Failed to fetch link metadata');
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching link metadata:', error);
            throw error;
        }
    }
}

// Create and export singleton instance
export const messageService = new MessageService();
