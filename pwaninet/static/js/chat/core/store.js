/**
 * Store - Single source of truth for application state
 * Emits change events via EventBus
 */

import { EVENTS, CONNECTION_STATE, UI_STATE } from '../shared/constants.js';
import { eventBus } from './event-bus.js';

export class Store {
  constructor() {
    // Connection state
    this.connectionState = CONNECTION_STATE.DISCONNECTED;
    this.conversationId = null;
    this.currentUserId = null;
    this.isEncrypted = false;

    // Message state
    this.messages = [];
    this.messageQueue = [];
    this.processedMessageIds = new Set(); // For deduplication

    // UI state
    this.uiState = UI_STATE.IDLE;
    this.typingUsers = new Map(); // userId -> username

    // Theme state
    this.currentTheme = null;
    this.themeMode = 'light';

    // Subscribe to events from other modules
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Listen for WebSocket events
    eventBus.on(EVENTS.WEBSOCKET_CONNECTED, () => {
      this.setConnectionState(CONNECTION_STATE.CONNECTED);
    });

    eventBus.on(EVENTS.WEBSOCKET_DISCONNECTED, () => {
      this.setConnectionState(CONNECTION_STATE.DISCONNECTED);
    });

    eventBus.on(EVENTS.WEBSOCKET_RECONNECTING, () => {
      this.setConnectionState(CONNECTION_STATE.RECONNECTING);
    });

    eventBus.on(EVENTS.WEBSOCKET_ERROR, () => {
      this.setConnectionState(CONNECTION_STATE.ERROR);
    });

    // Listen for message events
    eventBus.on(EVENTS.MESSAGE_NEW, (message) => {
      this.addMessage(message);
    });

    eventBus.on(EVENTS.MESSAGES_LOADED, (messages) => {
      this.setMessages(messages);
    });

    // Listen for typing events
    eventBus.on(EVENTS.TYPING_INDICATOR, (data) => {
      this.handleTypingIndicator(data);
    });
  }

  /**
   * Initialize store with configuration
   * @param {Object} config - Configuration object
   */
  init(config) {
    this.conversationId = config.conversationId;
    this.currentUserId = config.currentUserId;
    this.isEncrypted = config.isEncrypted;
    
    this.emitStateChange();
  }

  /**
   * Set connection state
   * @param {string} state - Connection state
   */
  setConnectionState(state) {
    if (this.connectionState === state) return;
    
    this.connectionState = state;
    eventBus.emit(EVENTS.CONNECTION_CHANGED, state);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Set messages
   * @param {Array} messages - Array of messages
   */
  setMessages(messages) {
    this.messages = messages;
    this.processedMessageIds = new Set(messages.map(m => m.id));
    
    eventBus.emit(EVENTS.MESSAGES_CHANGED, this.messages);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Add message to state
   * @param {Object} message - Message object
   */
  addMessage(message) {
    // Deduplication check
    if (this.processedMessageIds.has(message.id)) {
      return;
    }

    this.processedMessageIds.add(message.id);
    this.messages.push(message);
    
    // Sort by timestamp
    this.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    
    eventBus.emit(EVENTS.MESSAGES_CHANGED, this.messages);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Update message in state
   * @param {number} messageId - Message ID
   * @param {Object} updates - Updates to apply
   */
  updateMessage(messageId, updates) {
    const messageIndex = this.messages.findIndex(m => m.id === messageId);
    if (messageIndex === -1) return;

    this.messages[messageIndex] = {
      ...this.messages[messageIndex],
      ...updates,
    };

    eventBus.emit(EVENTS.MESSAGES_CHANGED, this.messages);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Handle typing indicator
   * @param {Object} data - Typing data
   */
  handleTypingIndicator(data) {
    if (data.user_id === this.currentUserId) return;

    if (data.is_typing) {
      this.typingUsers.set(data.user_id, data.username);
    } else {
      this.typingUsers.delete(data.user_id);
    }

    eventBus.emit(EVENTS.TYPING_INDICATOR, {
      isTyping: this.typingUsers.size > 0,
      users: Array.from(this.typingUsers.values()),
    });
  }

  /**
   * Set UI state
   * @param {string} state - UI state
   */
  setUIState(state) {
    if (this.uiState === state) return;
    
    this.uiState = state;
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Set theme
   * @param {Object} theme - Theme object
   */
  setTheme(theme) {
    this.currentTheme = theme;
    eventBus.emit(EVENTS.THEME_APPLY, theme);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Set theme mode
   * @param {string} mode - Theme mode (light/dark)
   */
  setThemeMode(mode) {
    this.themeMode = mode;
    eventBus.emit(EVENTS.THEME_APPLY, this.currentTheme);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Add message to queue
   * @param {Object} message - Message object
   */
  queueMessage(message) {
    this.messageQueue.push(message);
    eventBus.emit(EVENTS.MESSAGE_QUEUED, message);
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Remove message from queue
   * @param {Object} message - Message object
   */
  dequeueMessage(message) {
    const index = this.messageQueue.indexOf(message);
    if (index > -1) {
      this.messageQueue.splice(index, 1);
      eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
    }
  }

  /**
   * Clear message queue
   */
  clearMessageQueue() {
    this.messageQueue = [];
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Get current state
   * @returns {Object} Current state
   */
  getState() {
    return {
      connection: this.connectionState,
      conversationId: this.conversationId,
      currentUserId: this.currentUserId,
      isEncrypted: this.isEncrypted,
      messages: [...this.messages],
      messageQueue: [...this.messageQueue],
      uiState: this.uiState,
      typingUsers: Array.from(this.typingUsers.entries()),
      theme: this.currentTheme,
      themeMode: this.themeMode,
    };
  }

  /**
   * Get messages
   * @returns {Array} Messages
   */
  getMessages() {
    return [...this.messages];
  }

  /**
   * Get message by ID
   * @param {number} messageId - Message ID
   * @returns {Object|null} Message or null
   */
  getMessageById(messageId) {
    return this.messages.find(m => m.id === messageId) || null;
  }

  /**
   * Get connection state
   * @returns {string} Connection state
   */
  getConnectionState() {
    return this.connectionState;
  }

  /**
   * Check if connected
   * @returns {boolean} Is connected
   */
  isConnected() {
    return this.connectionState === CONNECTION_STATE.CONNECTED;
  }

  /**
   * Emit state change event
   */
  emitStateChange() {
    eventBus.emit(EVENTS.STATE_CHANGED, this.getState());
  }

  /**
   * Reset store to initial state
   */
  reset() {
    this.connectionState = CONNECTION_STATE.DISCONNECTED;
    this.messages = [];
    this.messageQueue = [];
    this.processedMessageIds.clear();
    this.uiState = UI_STATE.IDLE;
    this.typingUsers.clear();
    this.currentTheme = null;
    
    this.emitStateChange();
  }
}

// Create global instance
export const store = new Store();
