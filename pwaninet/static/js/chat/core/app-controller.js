/**
 * AppController - Main application orchestrator
 * Wires all modules together following strict data flow
 */

import { EVENTS } from '../shared/constants.js';
import { eventBus } from './event-bus.js';
import { store } from './store.js';
import { webSocketManager } from './websocket.js';
import { messageService } from './message-service.js';

export class AppController {
  constructor() {
    this.initialized = false;
  }

  /**
   * Initialize application
   * @param {Object} config - Configuration object
   */
  init(config) {
    if (this.initialized) return;

    // Initialize store with config
    store.init(config);

    // Initialize services
    messageService.init();

    // Connect WebSocket
    webSocketManager.connect(config.conversationId);

    // Load initial messages
    messageService.loadInitialMessages();

    // Setup core event handlers
    this.setupEventHandlers();

    this.initialized = true;
    console.log('AppController initialized');
  }

  /**
   * Setup core event handlers
   */
  setupEventHandlers() {
    // Handle WebSocket connection
    eventBus.on(EVENTS.WEBSOCKET_CONNECTED, () => {
      messageService.processQueue();
    });

    // Handle typing
    eventBus.on(EVENTS.TYPING_START, () => {
      this.sendTypingIndicator(true);
    });

    eventBus.on(EVENTS.TYPING_STOP, () => {
      this.sendTypingIndicator(false);
    });

    // Handle encryption initialization
    if (store.isEncrypted) {
      messageService.initEncryption();
    }
  }

  /**
   * Send typing indicator
   * @param {boolean} isTyping - Is typing
   */
  sendTypingIndicator(isTyping) {
    webSocketManager.send({
      type: 'typing_indicator',
      is_typing: isTyping,
    });
  }

  /**
   * Get store instance
   * @returns {Store} Store instance
   */
  getStore() {
    return store;
  }

  /**
   * Get event bus instance
   * @returns {EventBus} EventBus instance
   */
  getEventBus() {
    return eventBus;
  }

  /**
   * Destroy application
   */
  destroy() {
    webSocketManager.disconnect();
    store.reset();
    eventBus.clear();
    this.initialized = false;
  }
}

// Create global instance
export const appController = new AppController();
