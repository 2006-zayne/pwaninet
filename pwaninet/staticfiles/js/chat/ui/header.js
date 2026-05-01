/**
 * HeaderHandler - Handles header UI only
 * No business logic, pure header interactions
 * Emits user actions via EventBus
 */

import { EVENTS } from '../shared/constants.js';

export class HeaderHandler {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.header = null;
    this.themeButton = null;
    this.searchButton = null;
  }

  /**
   * Initialize header handler
   */
  init() {
    this.header = document.querySelector('.chat-header');
    this.themeButton = document.getElementById('themeBtn');
    this.searchButton = document.getElementById('searchBtn');

    if (!this.header) {
      console.error('Chat header not found');
      return;
    }

    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Theme button
    if (this.themeButton) {
      this.themeButton.addEventListener('click', () => {
        this.eventBus.emit(EVENTS.THEME_TOGGLE);
      });
    }

    // Search button
    if (this.searchButton) {
      this.searchButton.addEventListener('click', () => {
        this.eventBus.emit(EVENTS.SEARCH_TOGGLE);
      });
    }

    // Listen for status updates
    this.eventBus.on(EVENTS.HEADER_UPDATE_STATUS, (status) => {
      this.updateStatus(status);
    });
  }

  /**
   * Update status
   * @param {string} status - Status text
   */
  updateStatus(status) {
    const statusElement = document.getElementById('chatStatus');
    if (statusElement) {
      statusElement.textContent = status;
    }
  }

  /**
   * Update connection status
   * @param {string} state - Connection state
   */
  updateConnectionStatus(state) {
    const statusElement = document.getElementById('chatStatus');
    if (statusElement) {
      const statusMap = {
        'connected': 'Online',
        'connecting': 'Connecting...',
        'disconnected': 'Offline',
        'reconnecting': 'Reconnecting...',
        'error': 'Connection Error',
      };
      statusElement.textContent = statusMap[state] || state;
    }
  }
}
