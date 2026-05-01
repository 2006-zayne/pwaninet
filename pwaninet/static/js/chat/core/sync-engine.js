/**
 * SyncEngine - Real-time synchronization engine
 * Ensures idempotent message handling and reconnection stability
 * No DOM manipulation, pure sync logic
 */

import { EVENTS, MESSAGE_DEDUP_WINDOW } from '../shared/constants.js';
import { eventBus } from './event-bus.js';
import { store } from './store.js';

export class SyncEngine {
  constructor() {
    this.messageTimestamps = new Map(); // messageId -> timestamp
    this.pendingOperations = new Map(); // operationId -> Promise
    this.operationCounter = 0;
  }

  /**
   * Initialize sync engine
   */
  init() {
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Listen for new messages
    eventBus.on(EVENTS.MESSAGE_NEW, (message) => {
      this.handleIncomingMessage(message);
    });

    // Listen for WebSocket reconnection
    eventBus.on(EVENTS.WEBSOCKET_CONNECTED, () => {
      this.handleReconnection();
    });

    // Listen for messages loaded
    eventBus.on(EVENTS.MESSAGES_LOADED, (messages) => {
      this.syncMessageTimestamps(messages);
    });
  }

  /**
   * Handle incoming message with deduplication
   * @param {Object} message - Message object
   */
  handleIncomingMessage(message) {
    if (!message.id) return;

    const now = Date.now();
    const existingTimestamp = this.messageTimestamps.get(message.id);

    // Check for duplicate within dedup window
    if (existingTimestamp && (now - existingTimestamp) < MESSAGE_DEDUP_WINDOW) {
      console.log('Duplicate message detected, ignoring:', message.id);
      return;
    }

    // Update timestamp
    this.messageTimestamps.set(message.id, now);

    // Clean up old timestamps
    this.cleanupOldTimestamps(now);
  }

  /**
   * Sync message timestamps from loaded messages
   * @param {Array} messages - Array of messages
   */
  syncMessageTimestamps(messages) {
    const now = Date.now();
    messages.forEach(message => {
      if (message.id) {
        this.messageTimestamps.set(message.id, now);
      }
    });
  }

  /**
   * Clean up old timestamps outside dedup window
   * @param {number} now - Current timestamp
   */
  cleanupOldTimestamps(now) {
    for (const [messageId, timestamp] of this.messageTimestamps.entries()) {
      if (now - timestamp > MESSAGE_DEDUP_WINDOW) {
        this.messageTimestamps.delete(messageId);
      }
    }
  }

  /**
   * Handle WebSocket reconnection
   */
  async handleReconnection() {
    console.log('SyncEngine: Handling reconnection');

    // Request full message sync
    await this.requestFullSync();

    // Resend any pending operations
    await this.resendPendingOperations();
  }

  /**
   * Request full message sync from server
   */
  async requestFullSync() {
    try {
      const response = await fetch(
        `/messaging/v1/conversations/${store.conversationId}/messages/`
      );

      if (response.ok) {
        const data = await response.json();
        const serverMessages = data.results || [];

        // Merge with local state
        this.mergeMessages(serverMessages);
      }
    } catch (error) {
      console.error('SyncEngine: Full sync failed:', error);
    }
  }

  /**
   * Merge server messages with local state
   * @param {Array} serverMessages - Messages from server
   */
  mergeMessages(serverMessages) {
    const localMessages = store.getMessages();
    const localMessageIds = new Set(localMessages.map(m => m.id));

    // Add new messages from server
    const newMessages = serverMessages.filter(m => !localMessageIds.has(m.id));

    if (newMessages.length > 0) {
      newMessages.forEach(message => {
        eventBus.emit(EVENTS.MESSAGE_NEW, message);
      });
    }

    // Update existing messages if server has newer data
    serverMessages.forEach(serverMessage => {
      const localMessage = localMessages.find(m => m.id === serverMessage.id);
      if (localMessage && this.isServerMessageNewer(localMessage, serverMessage)) {
        store.updateMessage(serverMessage.id, serverMessage);
      }
    });
  }

  /**
   * Check if server message is newer than local
   * @param {Object} localMessage - Local message
   * @param {Object} serverMessage - Server message
   * @returns {boolean} Is server message newer
   */
  isServerMessageNewer(localMessage, serverMessage) {
    const localTime = new Date(localMessage.updated_at || localMessage.created_at).getTime();
    const serverTime = new Date(serverMessage.updated_at || serverMessage.created_at).getTime();
    return serverTime > localTime;
  }

  /**
   * Register pending operation
   * @param {Promise} operation - Operation promise
   * @returns {string} Operation ID
   */
  registerPendingOperation(operation) {
    const operationId = `op_${this.operationCounter++}`;
    this.pendingOperations.set(operationId, operation);
    return operationId;
  }

  /**
   * Resend pending operations after reconnection
   */
  async resendPendingOperations() {
    console.log('SyncEngine: Resending pending operations');

    for (const [operationId, operation] of this.pendingOperations.entries()) {
      try {
        await operation;
        this.pendingOperations.delete(operationId);
      } catch (error) {
        console.error(`SyncEngine: Operation ${operationId} failed:`, error);
      }
    }
  }

  /**
   * Clear pending operations
   */
  clearPendingOperations() {
    this.pendingOperations.clear();
  }

  /**
   * Get sync status
   * @returns {Object} Sync status
   */
  getStatus() {
    return {
      messageTimestamps: this.messageTimestamps.size,
      pendingOperations: this.pendingOperations.size,
      isSynced: this.pendingOperations.size === 0,
    };
  }

  /**
   * Reset sync engine
   */
  reset() {
    this.messageTimestamps.clear();
    this.clearPendingOperations();
    this.operationCounter = 0;
  }
}

// Create global instance
export const syncEngine = new SyncEngine();
