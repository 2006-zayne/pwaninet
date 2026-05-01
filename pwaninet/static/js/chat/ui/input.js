/**
 * InputHandler - Handles message input only
 * No business logic, pure input handling
 * Emits user actions via EventBus
 */

import { EVENTS } from '../shared/constants.js';

export class InputHandler {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.input = null;
    this.sendButton = null;
    this.typingTimeout = null;
  }

  /**
   * Initialize input handler
   */
  init() {
    this.input = document.getElementById('messageInput');
    this.sendButton = document.getElementById('sendBtn');

    if (!this.input) {
      console.error('Message input not found');
      return;
    }

    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Input keypress
    this.input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
      this.handleTyping();
    });

    // Auto-expand textarea
    this.input.addEventListener('input', () => {
      this.input.style.height = 'auto';
      const newHeight = Math.min(this.input.scrollHeight, 120);
      this.input.style.height = newHeight + 'px';
    });

    // Send button click
    if (this.sendButton) {
      this.sendButton.addEventListener('click', () => this.handleSend());
    }

    // Listen for emoji insertion
    this.eventBus.on(EVENTS.EMOJI_INSERT, (emoji) => {
      this.input.value += emoji;
      this.input.focus();
    });

    // Listen for attachment selection
    this.eventBus.on(EVENTS.ATTACHMENT_SELECTED, (file) => {
      this.handleAttachment(file);
    });
  }

  /**
   * Handle send
   */
  handleSend() {
    const content = this.input.value.trim();
    if (!content) return;

    this.eventBus.emit(EVENTS.MESSAGE_SEND, content);
    this.input.value = '';
    this.input.style.height = 'auto';
  }

  /**
   * Handle typing
   */
  handleTyping() {
    this.eventBus.emit(EVENTS.TYPING_START);

    clearTimeout(this.typingTimeout);
    this.typingTimeout = setTimeout(() => {
      this.eventBus.emit(EVENTS.TYPING_STOP);
    }, 500);
  }

  /**
   * Handle attachment
   * @param {File} file - File object
   */
  handleAttachment(file) {
    this.eventBus.emit(EVENTS.ATTACHMENT_UPLOAD, file);
  }

  /**
   * Get input value
   * @returns {string} Input value
   */
  getValue() {
    return this.input.value;
  }

  /**
   * Set input value
   * @param {string} value - Value to set
   */
  setValue(value) {
    this.input.value = value;
  }

  /**
   * Focus input
   */
  focus() {
    this.input.focus();
  }
}
