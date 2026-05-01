/**
 * UIController - UI layer coordinator
 * Listens to store changes, coordinates UI rendering
 * No business logic, pure UI coordination
 */

import { EVENTS } from '../shared/constants.js';
import { eventBus } from '../core/event-bus.js';
import { store } from '../core/store.js';
import { MessageRenderer } from './renderer.js';
import { InputHandler } from './input.js';
import { HeaderHandler } from './header.js';
import { ThemeHandler } from './theme.js';

export class UIController {
  constructor() {
    this.renderer = null;
    this.inputHandler = null;
    this.headerHandler = null;
    this.themeHandler = null;
  }

  /**
   * Initialize UI controller
   * @param {Object} config - Configuration
   */
  init(config) {
    // Initialize UI handlers
    this.renderer = new MessageRenderer(eventBus, store);
    this.inputHandler = new InputHandler(eventBus);
    this.headerHandler = new HeaderHandler(eventBus);
    this.themeHandler = new ThemeHandler(eventBus);

    // Initialize handlers
    this.renderer.init(config);
    this.inputHandler.init();
    this.headerHandler.init();
    this.themeHandler.init();

    // Setup store change listeners
    this.setupStoreListeners();
  }

  /**
   * Setup store change listeners
   */
  setupStoreListeners() {
    // Listen for message changes
    eventBus.on(EVENTS.MESSAGES_CHANGED, (messages) => {
      this.renderer.render(messages);
    });

    // Listen for connection changes
    eventBus.on(EVENTS.CONNECTION_CHANGED, (state) => {
      this.handleConnectionChange(state);
    });

    // Listen for typing indicators
    eventBus.on(EVENTS.TYPING_INDICATOR, (data) => {
      this.handleTypingIndicator(data);
    });

    // Listen for state changes
    eventBus.on(EVENTS.STATE_CHANGED, (state) => {
      this.handleStateChange(state);
    });
  }

  /**
   * Handle connection change
   * @param {string} state - Connection state
   */
  handleConnectionChange(state) {
    this.headerHandler.updateConnectionStatus(state);
  }

  /**
   * Handle typing indicator
   * @param {Object} data - Typing data
   */
  handleTypingIndicator(data) {
    if (data.isTyping) {
      this.renderer.showTypingIndicator(data.users);
    } else {
      this.renderer.hideTypingIndicator();
    }
  }

  /**
   * Handle state change
   * @param {Object} state - Application state
   */
  handleStateChange(state) {
    // Update UI based on state
    this.headerHandler.updateStatus(state.uiState);
  }

  /**
   * Get renderer instance
   * @returns {MessageRenderer} Renderer instance
   */
  getRenderer() {
    return this.renderer;
  }

  /**
   * Get input handler instance
   * @returns {InputHandler} Input handler instance
   */
  getInputHandler() {
    return this.inputHandler;
  }

  /**
   * Get header handler instance
   * @returns {HeaderHandler} Header handler instance
   */
  getHeaderHandler() {
    return this.headerHandler;
  }

  /**
   * Get theme handler instance
   * @returns {ThemeHandler} Theme handler instance
   */
  getThemeHandler() {
    return this.themeHandler;
  }
}

// Create global instance
export const uiController = new UIController();
