/**
 * Store - Single Source of Truth (SOT) with Canonical Message Schema
 * ONLY module allowed to mutate application state
 * All mutations MUST go through explicit store methods
 */

import { CONNECTION_STATE, UI_STATE } from '../shared/constants.js';

// CANONICAL MESSAGE SCHEMA - All modules MUST conform to this
export const MESSAGE_SCHEMA = {
    id: 'string',                    // Unique identifier
    conversationId: 'number',         // Conversation identifier
    senderId: 'number',              // Sender identifier
    timestamp: 'string',             // ISO timestamp
    status: 'string',                // sent | delivered | read | failed
    content: 'string',               // Message content
    type: 'string',                  // text | media | system | emoji
    metadata: 'object',              // Additional data (media info, reactions, etc.)
    isOptimistic: 'boolean',         // Temporary optimistic state
    sortOrder: 'number'              // Deterministic ordering
};

export class Store {
    constructor() {
        // Private state - NO DIRECT ACCESS from outside
        this._state = {
            // Connection state
            connectionState: CONNECTION_STATE.DISCONNECTED,
            conversationId: null,
            currentUserId: null,
            isEncrypted: false,

            // Message state - ONLY canonical schema messages
            messages: new Map(), // messageId -> message (Map for O(1) operations)
            messageOrder: [],   // Array of messageIds for ordering
            processedMessageIds: new Set(), // For deduplication

            // UI state
            uiState: UI_STATE.IDLE,
            typingUsers: new Map(), // userId -> username

            // Theme state
            currentTheme: null,
            themeMode: 'light'
        };

        // Subscribers for state changes (UI controllers only)
        this._subscribers = new Set();

        // Debug mode flag
        this._debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

        // Mutation tracking for validation
        this._mutationLog = [];
        this._maxMutationLogSize = 100;
    }

    /**
     * Initialize store with configuration
     * @param {Object} config - Initial configuration
     */
    init(config) {
        this._logMutation('STORE_INIT', config);
        
        this._state.conversationId = config.conversationId;
        this._state.currentUserId = config.currentUserId;
        this._state.isEncrypted = config.isEncrypted || false;
        
        this._notifySubscribers();
    }

    /**
     * Subscribe to state changes (UI controllers only)
     * @param {Function} callback - Callback function
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
        this._subscribers.add(callback);
        
        // Return unsubscribe function
        return () => {
            this._subscribers.delete(callback);
        };
    }

    /**
     * Get current state (read-only snapshot)
     * @returns {Object} Current state snapshot
     */
    getState() {
        return {
            connectionState: this._state.connectionState,
            conversationId: this._state.conversationId,
            currentUserId: this._state.currentUserId,
            isEncrypted: this._state.isEncrypted,
            messages: this._getMessagesArray(),
            messageQueue: [], // Queue handled by message service
            processedMessageIds: new Set(this._state.processedMessageIds),
            uiState: this._state.uiState,
            typingUsers: new Map(this._state.typingUsers),
            currentTheme: this._state.currentTheme,
            themeMode: this._state.themeMode
        };
    }

    /**
     * Get messages as array (read-only, ordered)
     * @returns {Array} Messages array in order
     */
    getMessages() {
        return this._getMessagesArray();
    }

    /**
     * Get message by ID (read-only)
     * @param {string} messageId - Message ID
     * @returns {Object|null} Message or null
     */
    getMessageById(messageId) {
        const message = this._state.messages.get(messageId);
        return message ? { ...message } : null; // Return copy to prevent mutation
    }

    /**
     * Get connection state (read-only)
     * @returns {string} Connection state
     */
    getConnectionState() {
        return this._state.connectionState;
    }

    /**
     * Check if connected (read-only)
     * @returns {boolean} Is connected
     */
    isConnected() {
        return this._state.connectionState === CONNECTION_STATE.CONNECTED;
    }

    // === MUTATION METHODS (ONLY STORE CAN MUTATE STATE) ===

    /**
     * Set connection state
     * @param {string} state - New connection state
     */
    setConnectionState(state) {
        this._logMutation('SET_CONNECTION_STATE', { state });
        
        this._state.connectionState = state;
        this._notifySubscribers();
    }

    /**
     * Add message to store (canonical schema validation)
     * @param {Object} message - Message object
     */
    addMessage(message) {
        this._logMutation('ADD_MESSAGE', message);

        // Validate against canonical schema
        const validatedMessage = this._validateCanonicalMessage(message);
        if (!validatedMessage) {
            console.error('Store: Invalid message rejected - violates canonical schema', message);
            return;
        }

        // Check for duplicates
        if (this._state.processedMessageIds.has(validatedMessage.id)) {
            this._logMutation('DUPLICATE_MESSAGE_IGNORED', validatedMessage.id);
            return;
        }

        // Add to processed IDs
        this._state.processedMessageIds.add(validatedMessage.id);

        // Store message (immutable)
        this._state.messages.set(validatedMessage.id, validatedMessage);

        // Update order array for deterministic sorting
        this._updateMessageOrder(validatedMessage);

        this._notifySubscribers();
    }

    /**
     * Update existing message (canonical schema validation)
     * @param {string} messageId - Message ID
     * @param {Object} updates - Message updates
     */
    updateMessage(messageId, updates) {
        this._logMutation('UPDATE_MESSAGE', { messageId, updates });

        const existingMessage = this._state.messages.get(messageId);
        if (!existingMessage) {
            console.error('Store: Message not found for update', messageId);
            return;
        }

        // Validate updates against canonical schema
        const updatedMessage = this._validateCanonicalMessage({
        ...existingMessage,
        ...updates,
        metadata: {
            ...existingMessage.metadata,
            ...(updates.metadata || {})
        },
        id: messageId
        });

        if (!updatedMessage) {
            console.error('Store: Invalid message update - violates canonical schema', updates);
            return;
        }

        // Update message (immutable)
        this._state.messages.set(messageId, updatedMessage);

        this._notifySubscribers();
    }

    /**
     * Replace message (for optimistic updates)
     * @param {string} tempId - Temporary message ID
     * @param {Object} actualMessage - Actual message
     */
    replaceMessage(tempId, actualMessage) {
        this._logMutation('REPLACE_MESSAGE', { tempId, actualMessage });

        // Validate actual message against canonical schema
        const validatedMessage = this._validateCanonicalMessage(actualMessage);
        if (!validatedMessage) {
            console.error('Store: Invalid replacement message - violates canonical schema', actualMessage);
            return;
        }

        const optimisticMessage = this._state.messages.get(tempId);
        if (!optimisticMessage) {
            console.error('Store: Optimistic message not found for replacement', tempId);
            return;
        }

        // Remove temp ID from processed and add actual ID
        this._state.processedMessageIds.delete(tempId);
        this._state.processedMessageIds.add(validatedMessage.id);

        // ✅ Remove stale tempId from order array
        const tempIndex = this._state.messageOrder.indexOf(tempId);
        if (tempIndex !== -1) {
            this._state.messageOrder.splice(tempIndex, 1);
        }

        // Add actual message
        this._state.messages.set(validatedMessage.id, validatedMessage);

        // Update order
        this._updateMessageOrder(validatedMessage);

        this._notifySubscribers();
    }

    /**
     * Remove message
     * @param {string} messageId - Message ID
     */
    removeMessage(messageId) {
        this._logMutation('REMOVE_MESSAGE', { messageId });

        const message = this._state.messages.get(messageId);
        if (!message) {
            console.error('Store: Message not found for removal', messageId);
            return;
        }

        this._state.messages.delete(messageId);
        this._state.processedMessageIds.delete(messageId);

        // Remove from order array
        const orderIndex = this._state.messageOrder.indexOf(messageId);
        if (orderIndex !== -1) {
            this._state.messageOrder.splice(orderIndex, 1);
        }

        this._notifySubscribers();
    }

    /**
     * Set typing indicator
     * @param {number} userId - User ID
     * @param {string} username - Username
     * @param {boolean} isTyping - Is typing
     */
    setTypingIndicator(userId, username, isTyping) {
        this._logMutation('SET_TYPING_INDICATOR', { userId, username, isTyping });

        if (isTyping) {
            this._state.typingUsers.set(userId, username);
        } else {
            this._state.typingUsers.delete(userId);
        }

        this._notifySubscribers();
    }

    /**
     * Set UI state
     * @param {string} state - UI state
     */
    setUIState(state) {
        this._logMutation('SET_UI_STATE', { state });

        this._state.uiState = state;
        this._notifySubscribers();
    }

    /**
     * Set theme
     * @param {Object} theme - Theme object
     * @param {string} mode - Theme mode
     */
    setTheme(theme, mode = 'light') {
        this._logMutation('SET_THEME', { theme, mode });

        this._state.currentTheme = theme;
        this._state.themeMode = mode;
        this._notifySubscribers();
    }

    /**
     * Reset store to initial state
     */
    reset() {
        this._logMutation('RESET_STORE');

        this._state.messages.clear();
        this._state.messageOrder = [];
        this._state.processedMessageIds.clear();
        this._state.typingUsers.clear();
        this._state.uiState = UI_STATE.IDLE;

        this._notifySubscribers();
    }

    // === PRIVATE METHODS ===

    /**
     * Validate message against canonical schema
     * @param {Object} message - Message to validate
     * @returns {Object|null} Validated message or null
     */
    _validateCanonicalMessage(message) {
        if (!message || typeof message !== 'object') {
            return null;
        }

        // Required fields validation
        const required = ['id', 'conversationId', 'senderId', 'timestamp', 'status', 'content', 'type'];
        for (const field of required) {
            if (!(field in message)) {
                console.error(`Store: Missing required field: ${field}`);
                return null;
            }
        }

        // Type validation
        const validation = {
            id: typeof message.id === 'string',
            conversationId: typeof message.conversationId === 'number',
            senderId: typeof message.senderId === 'number',
            timestamp: typeof message.timestamp === 'string',
            status: ['sent', 'delivered', 'read', 'failed'].includes(message.status),
            content: typeof message.content === 'string',
            type: ['text', 'media', 'system', 'emoji'].includes(message.type),
            isOptimistic: typeof message.isOptimistic === 'boolean',
            sortOrder: typeof message.sortOrder === 'number'
        };

        for (const [field, isValid] of Object.entries(validation)) {
            if (!isValid) {
                console.error(`Store: Invalid field type: ${field}`);
                return null;
            }
        }

        // Return validated message with defaults
        return {
            id: message.id,
            conversationId: message.conversationId,
            senderId: message.senderId,
            timestamp: message.timestamp,
            status: message.status,
            content: message.content,
            type: message.type,
            metadata: message.metadata || {},
            isOptimistic: message.isOptimistic || false,
            sortOrder: message.sortOrder ?? Date.now()
        };
    }

    /**
     * Update message order for deterministic sorting
     * @param {Object} message - Message to add to order
     */
    _updateMessageOrder(message) {
        const existingIndex = this._state.messageOrder.indexOf(message.id);
        
        if (existingIndex === -1) {
            // New message - insert in correct position
            const insertIndex = this._state.messageOrder.findIndex(id => {
                const existingMessage = this._state.messages.get(id);
                return existingMessage && existingMessage.sortOrder > message.sortOrder;
            });

            if (insertIndex === -1) {
                this._state.messageOrder.push(message.id);
            } else {
                this._state.messageOrder.splice(insertIndex, 0, message.id);
            }
        } else {
            // Existing message - reorder if needed
            this._state.messageOrder.sort((a, b) => {
                const messageA = this._state.messages.get(a);
                const messageB = this._state.messages.get(b);
                return (messageA?.sortOrder || 0) - (messageB?.sortOrder || 0);
            });
        }
    }

    /**
     * Get messages as ordered array
     * @returns {Array} Ordered messages array
     */
    _getMessagesArray() {
        const orderedMessages = [];
        
        for (const messageId of this._state.messageOrder) {
            const message = this._state.messages.get(messageId);
            if (message) {
                orderedMessages.push({ ...message }); // Return copy
            }
        }

        return orderedMessages;
    }

    /**
     * Notify all subscribers of state change
     */
    _notifySubscribers() {
        const snapshot = this.getState();
        this._subscribers.forEach(callback => {
            try {
                callback(snapshot);
            } catch (error) {
                console.error('Store: Subscriber callback error', error);
            }
        });
    }

    /**
     * Log state mutation (debug mode only)
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _logMutation(action, data) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            action,
            data: structuredClone?.(data) ?? data // Deep clone
        };

        this._mutationLog.push(logEntry);

        // Keep log size manageable
        if (this._mutationLog.length > this._maxMutationLogSize) {
            this._mutationLog.shift();
        }

        if (this._debugMode) {
            console.log(`[STORE MUTATION] ${action}:`, data);
        }
    }

    /**
     * Get mutation log (for validation)
     * @returns {Array} Mutation log
     */
    getMutationLog() {
        return [...this._mutationLog];
    }

    /**
     * Validate message consistency
     * @returns {Object} Validation results
     */
    validateMessageConsistency() {
        const messages = this.getMessages();
        const messageIds = new Set();
        const duplicates = [];
        const invalidSchema = [];

        for (const message of messages) {
            // Check for duplicates
            if (messageIds.has(message.id)) {
                duplicates.push(message.id);
            } else {
                messageIds.add(message.id);
            }

            // Validate schema
            const validated = this._validateCanonicalMessage(message);
            if (!validated) {
                invalidSchema.push(message.id);
            }
        }

        return {
            totalMessages: messages.length,
            uniqueMessages: messageIds.size,
            duplicates,
            invalidSchema,
            isConsistent: duplicates.length === 0 && invalidSchema.length === 0
        };
    }
}

// Create and export singleton instance
export const store = new Store();
