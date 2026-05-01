/**
 * OptimisticUpdateService - Optimistic UI updates for better UX
 * Implements optimistic rendering with rollback on error
 */

import { EVENTS } from '../shared/constants.js';
import { eventBus } from './event-bus.js';
import { store } from './store.js';

export class OptimisticUpdateService {
  constructor() {
    this.pendingUpdates = new Map(); // messageId -> { originalMessage, optimisticMessage }
    this.pendingReactions = new Map(); // reactionId -> { originalState, optimisticState }
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Listen for optimistic message creation
    eventBus.on(EVENTS.MESSAGE_OPTIMISTIC_ADD, (message) => {
      this.handleOptimisticMessage(message);
    });

    // Listen for server confirmation
    eventBus.on(EVENTS.MESSAGE_CONFIRMED, (message) => {
      this.confirmMessage(message);
    });

    // Listen for message failed
    eventBus.on(EVENTS.MESSAGE_FAILED, (messageId) => {
      this.rollbackMessage(messageId);
    });

    // Listen for optimistic reactions
    eventBus.on(EVENTS.REACTION_OPTIMISTIC_ADD, (data) => {
      this.handleOptimisticReaction(data);
    });

    // Listen for reaction confirmed
    eventBus.on(EVENTS.REACTION_CONFIRMED, (data) => {
      this.confirmReaction(data);
    });
  }

  /**
   * Create optimistic message with temporary ID
   * @param {string} content - Message content
   * @param {number} replyTo - Reply to message ID
   * @returns {Object} Optimistic message object
   */
  createOptimisticMessage(content, replyTo = null) {
    const tempId = `temp_${Date.now()}_${Math.random()}`;
    const now = new Date().toISOString();

    const optimisticMessage = {
      id: tempId,
      conversation: store.conversationId,
      sender: {
        id: store.currentUserId,
        username: store.currentUsername || 'You',
        profile_pic: store.currentUserPic,
      },
      content: content,
      encrypted_content: null,
      is_encrypted: false,
      attachment: null,
      attachment_type: null,
      reply_to: replyTo,
      reactions: [],
      read_receipts: [],
      created_at: now,
      edited_at: null,
      is_deleted: false,
      is_pending: true, // Mark as pending in UI
      is_optimistic: true, // Mark as optimistic for UI styling
    };

    return optimisticMessage;
  }

  /**
   * Handle optimistic message - add to store immediately
   * @param {Object} message - Optimistic message
   */
  handleOptimisticMessage(message) {
    const tempId = message.id;

    // Store for later confirmation
    this.pendingUpdates.set(tempId, {
      optimisticMessage: message,
      confirmed: false,
      timestamp: Date.now(),
    });

    // Add to store immediately (UI renders this)
    store.addMessage(message);

    // Emit event so UI can highlight as pending
    eventBus.emit(EVENTS.UI_MESSAGE_PENDING, { messageId: tempId });
  }

  /**
   * Confirm optimistic message with server response
   * @param {Object} serverMessage - Confirmed message from server
   */
  confirmMessage(serverMessage) {
    // Find pending message by content/timestamp
    let tempId = null;

    for (const [id, data] of this.pendingUpdates.entries()) {
      if (
        data.optimisticMessage.content === serverMessage.content &&
        !data.confirmed
      ) {
        tempId = id;
        break;
      }
    }

    if (tempId) {
      const pending = this.pendingUpdates.get(tempId);

      // Replace optimistic message with server version
      store.replaceMessage(tempId, serverMessage);

      // Mark as confirmed
      pending.confirmed = true;

      // Remove from pending after 5 seconds
      setTimeout(() => this.pendingUpdates.delete(tempId), 5000);

      // Emit confirmation event
      eventBus.emit(EVENTS.UI_MESSAGE_CONFIRMED, { 
        tempId, 
        actualId: serverMessage.id 
      });
    }
  }

  /**
   * Rollback optimistic message on error
   * @param {string} messageId - Temporary message ID
   */
  rollbackMessage(messageId) {
    const pending = this.pendingUpdates.get(messageId);

    if (pending) {
      // Remove from store
      store.removeMessage(messageId);

      // Remove from pending
      this.pendingUpdates.delete(messageId);

      // Emit error event for UI
      eventBus.emit(EVENTS.UI_MESSAGE_FAILED, { messageId });
    }
  }

  /**
   * Handle optimistic reaction
   * @param {Object} data - { messageId, emoji, userId }
   */
  handleOptimisticReaction(data) {
    const reactionId = `reaction_${data.messageId}_${data.emoji}_${data.userId}`;

    // Store original state
    const message = store.getMessage(data.messageId);
    const originalReaction = message?.reactions?.find(
      r => r.emoji === data.emoji && r.user.id === data.userId
    );

    this.pendingReactions.set(reactionId, {
      messageId: data.messageId,
      emoji: data.emoji,
      userId: data.userId,
      originalState: originalReaction,
      confirmed: false,
      timestamp: Date.now(),
    });

    // Add reaction to message optimistically
    if (!originalReaction) {
      store.addReactionToMessage(data.messageId, {
        id: reactionId,
        emoji: data.emoji,
        user: { id: data.userId, username: 'You' },
        created_at: new Date().toISOString(),
        is_optimistic: true,
      });
    }

    eventBus.emit(EVENTS.UI_REACTION_PENDING, data);
  }

  /**
   * Confirm optimistic reaction
   * @param {Object} data - Server reaction data
   */
  confirmReaction(data) {
    // Find and confirm pending reaction
    for (const [reactionId, pending] of this.pendingReactions.entries()) {
      if (
        pending.messageId === data.messageId &&
        pending.emoji === data.emoji &&
        !pending.confirmed
      ) {
        pending.confirmed = true;

        // Update reaction with server ID if needed
        store.updateReaction(data.messageId, data.emoji, {
          ...data,
          is_optimistic: false,
        });

        // Remove from pending after 5 seconds
        setTimeout(() => this.pendingReactions.delete(reactionId), 5000);

        eventBus.emit(EVENTS.UI_REACTION_CONFIRMED, data);
        break;
      }
    }
  }

  /**
   * Get pending updates for debugging/monitoring
   */
  getPendingUpdates() {
    return {
      messages: Array.from(this.pendingUpdates.entries()),
      reactions: Array.from(this.pendingReactions.entries()),
    };
  }

  /**
   * Clear old pending updates (older than 1 minute)
   */
  cleanupStaleUpdates() {
    const now = Date.now();
    const timeout = 60000; // 1 minute

    // Clean messages
    for (const [id, data] of this.pendingUpdates.entries()) {
      if (now - data.timestamp > timeout) {
        this.rollbackMessage(id);
      }
    }

    // Clean reactions
    for (const [id, data] of this.pendingReactions.entries()) {
      if (now - data.timestamp > timeout) {
        this.pendingReactions.delete(id);
        eventBus.emit(EVENTS.UI_REACTION_TIMEOUT, {
          messageId: data.messageId,
          emoji: data.emoji,
        });
      }
    }
  }
}

// Export singleton
export const optimisticUpdateService = new OptimisticUpdateService();
