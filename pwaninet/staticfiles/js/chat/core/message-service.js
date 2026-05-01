/**
 * MessageService - Message operations and business logic
 * Pure service layer, no DOM manipulation
 */

import { EVENTS } from '../shared/constants.js';
import { eventBus } from './event-bus.js';
import { store } from './store.js';
import { webSocketManager } from './websocket.js';
import { getCSRFToken } from '../shared/utils.js';
import { optimisticUpdateService } from './optimistic-updates.js';

export class MessageService {
  constructor() {
    this.e2eEncryption = null;
    this.recipientPublicKey = null;
  }

  /**
   * Initialize message service
   */
  init() {
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Listen for send requests
    eventBus.on(EVENTS.MESSAGE_SEND, (content) => {
      this.sendMessage(content);
    });

    // Listen for WebSocket messages
    eventBus.on('message', (data) => {
      this.handleIncomingMessage(data);
    });

    // Listen for read receipts
    eventBus.on('read_receipt', (data) => {
      this.handleReadReceipt(data);
    });
  }

  /**
   * Send message
   * @param {string} content - Message content
   * @param {number|null} replyTo - Reply to message ID
   */
  async sendMessage(content, replyTo = null) {
    if (!content || !content.trim()) return;

    const cleanContent = content.trim();
    let messageData = {
      type: 'chat_message',
      content: cleanContent,
      reply_to: replyTo,
    };

    // Encrypt if E2E enabled
    if (store.isEncrypted && this.e2eEncryption && this.recipientPublicKey) {
      try {
        const encryptedContent = await this.e2eEncryption.encryptMessage(
          cleanContent,
          this.recipientPublicKey
        );
        messageData = {
          type: 'chat_message',
          content: null,
          encrypted_content: encryptedContent,
          is_encrypted: true,
          reply_to: replyTo,
        };
      } catch (error) {
        console.error('Encryption failed, sending plaintext:', error);
      }
    }

    // Create optimistic message for immediate UI feedback
    const optimisticMessage = optimisticUpdateService.createOptimisticMessage(cleanContent, replyTo);
    eventBus.emit(EVENTS.MESSAGE_OPTIMISTIC_ADD, optimisticMessage);

    // Try to send via WebSocket
    const sent = webSocketManager.send(messageData);

    if (sent) {
      eventBus.emit(EVENTS.MESSAGE_SENT, messageData);
    } else {
      // Queue message if not connected
      store.queueMessage(messageData);
    }
  }

  /**
   * Handle incoming message
   * @param {Object} data - Message data
   */
  async handleIncomingMessage(data) {
    // Decrypt if encrypted
    if (data.is_encrypted && this.e2eEncryption) {
      try {
        data.content = await this.e2eEncryption.decryptMessage(data.encrypted_content);
      } catch (error) {
        console.error('Failed to decrypt message:', error);
        data.content = '[Encrypted message - unable to decrypt]';
      }
    }

    // Normalize message
    const normalizedMessage = {
      ...data,
      sender_id: parseInt(data.sender_id || data.sender?.id),
      created_at: data.created_at || data.timestamp,
    };

    // Check if this is a confirmation of an optimistic message
    if (normalizedMessage.sender_id === store.currentUserId) {
      // This is our own message coming back from server
      // Emit confirmation event to let optimistic-updates handle it
      eventBus.emit(EVENTS.MESSAGE_CONFIRMED, normalizedMessage);
      // Don't emit MESSAGE_NEW to avoid duplicate
      return;
    }

    // Emit new message event for other users' messages
    eventBus.emit(EVENTS.MESSAGE_NEW, normalizedMessage);
  }

  /**
   * Handle read receipt
   * @param {Object} data - Read receipt data
   */
  handleReadReceipt(data) {
    const { message_id, status, user_avatar } = data;

    // Update message in store
    store.updateMessage(message_id, {
      read_status: status,
      read_avatar: user_avatar,
    });

    eventBus.emit(EVENTS.MESSAGE_READ_RECEIPT, data);
  }

  /**
   * Load initial messages from API
   */
  async loadInitialMessages() {
    try {
      const response = await fetch(
        `/messaging/v1/conversations/${store.conversationId}/messages/`
      );

      if (response.ok) {
        const data = await response.json();
        eventBus.emit(EVENTS.MESSAGES_LOADED, data.results || []);
      }
    } catch (error) {
      console.error('Error loading initial messages:', error);
    }
  }

  /**
   * Process queued messages
   */
  processQueue() {
    const queue = [...store.messageQueue];
    store.clearMessageQueue();

    queue.forEach(message => {
      const sent = webSocketManager.send(message);
      if (!sent) {
        store.queueMessage(message);
      }
    });
  }

  /**
   * Initialize E2E encryption
   */
  async initEncryption() {
    if (typeof E2EEncryption === 'undefined') {
      console.warn('E2EEncryption module not loaded');
      return;
    }

    try {
      this.e2eEncryption = new E2EEncryption();
      const { publicKey, privateKey, isNew } = await this.e2eEncryption.initForConversation(
        store.conversationId
      );

      if (isNew && publicKey) {
        await this.sendPublicKey(publicKey);
      }

      await this.loadRecipientPublicKey();
    } catch (error) {
      console.error('Error initializing E2E encryption:', error);
    }
  }

  /**
   * Send public key to server
   * @param {string} publicKey - Public key
   */
  async sendPublicKey(publicKey) {
    try {
      await fetch(`/messaging/v1/conversations/${store.conversationId}/set_public_key/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRFToken(),
        },
        body: JSON.stringify({ public_key: publicKey }),
      });
    } catch (error) {
      console.error('Error sending public key:', error);
    }
  }

  /**
   * Load recipient's public key
   */
  async loadRecipientPublicKey() {
    try {
      const response = await fetch(
        `/messaging/v1/conversations/${store.conversationId}/`
      );

      if (response.ok) {
        const conversation = await response.json();
        const otherMember = conversation.members?.find(m => m.user.id !== store.currentUserId);

        if (otherMember && otherMember.public_key) {
          this.recipientPublicKey = otherMember.public_key;
          await this.e2eEncryption.importPublicKey(this.recipientPublicKey);
        }
      }
    } catch (error) {
      console.error('Error loading recipient public key:', error);
    }
  }
}

// Create global instance
export const messageService = new MessageService();
