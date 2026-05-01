/**
 * MessageRenderer - Handles message rendering only
 * No business logic, pure DOM manipulation
 * Listens to store changes via EventBus
 */

import { EVENTS } from '../shared/constants.js';
import { formatDateLabel, formatTime, escapeHtml } from '../shared/utils.js';

export class MessageRenderer {
  constructor(eventBus, store) {
    this.eventBus = eventBus;
    this.store = store;
    this.container = null;
    this.currentUserId = null;
    this.isRendering = false;
    this.lastMessage = null;
  }

  /**
   * Initialize renderer
   * @param {Object} config - Configuration
   */
  init(config) {
    this.container = document.getElementById('messagesContainer');
    this.currentUserId = config.currentUserId;

    if (!this.container) {
      console.error('Messages container not found');
      return;
    }

    // Listen for message updates from store
    this.eventBus.on(EVENTS.MESSAGES_CHANGED, (messages) => this.render(messages));
    this.eventBus.on(EVENTS.MESSAGE_NEW, (message) => this.appendMessage(message));
  }

    /**
     * Render all messages
     * @param {Array} messages - Array of message objects
     */
    render(messages) {
        if (this.isRendering) return;
        this.isRendering = true;

        try {
            this.container.innerHTML = '';
            this.lastMessage = null;
            const viewItems = this.buildView(messages);

            viewItems.forEach(item => {
                if (item.type === 'date') {
                    this.container.appendChild(this.createDateElement(item.label));
                } else if (item.type === 'message') {
                    this.container.appendChild(this.createMessageElement(item));
                    this.lastMessage = item;
                }
            });

            this.scrollToBottom();
        } finally {
            this.isRendering = false;
        }
    }

    /**
     * Append a single message
     * @param {Object} message - Message object
     */
    appendMessage(message) {
        const viewItem = this.buildView([message])[0];
        const messageElement = this.createMessageElement({
            ...viewItem,
            isConsecutive: this.isConsecutive(viewItem)
        });
        this.container.appendChild(messageElement);
        this.lastMessage = viewItem;
        this.scrollToBottom();
    }

    /**
     * Build view from messages
     * @param {Array} messages - Array of message objects
     * @returns {Array} View items
     */
    buildView(messages) {
        const viewItems = [];
        let lastDate = null;
        let lastSenderId = null;

        for (const message of messages) {
            const messageDate = new Date(message.created_at).toDateString();
            const isOwn = message.sender_id === this.currentUserId;

            // Add date separator
            if (messageDate !== lastDate) {
                viewItems.push({
                    type: 'date',
                    label: this.formatDateLabel(message.created_at)
                });
                lastDate = messageDate;
            }

            // Determine consecutive
            const isConsecutive = lastSenderId === message.sender_id;
            lastSenderId = message.sender_id;

            viewItems.push({
                type: 'message',
                ...message,
                isOwn,
                isConsecutive,
                isLastSent: isOwn && message === messages.filter(m => m.sender_id === this.currentUserId).pop()
            });
        }

        return viewItems;
    }

    /**
     * Create date separator element
     * @param {string} label - Date label
     * @returns {HTMLElement} Date element
     */
    createDateElement(label) {
        const element = document.createElement('div');
        element.className = 'date-separator';
        element.innerHTML = `<span>${label}</span>`;
        return element;
    }

    /**
     * Create message element
     * @param {Object} message - Message object with view properties
     * @returns {HTMLElement} Message element
     */
    createMessageElement(message) {
        // Create message bubble (no wrapper to match template structure)
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} ${message.isConsecutive ? 'consecutive-message' : 'first-in-group'} ${message.isLastSent ? 'last-sent' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.sender_id);
        messageDiv.setAttribute('data-read-status', message.read_status || 'sent');

        const readStatus = message.read_status || 'sent';
        messageDiv.innerHTML = `
            <p class="message-content">${this.escapeHtml(message.content || '')}</p>
            <div class="message-time">
                ${this.formatTime(message.created_at)}
                ${message.isOwn ? `
                <span class="message-read-receipt">${this.getReadReceiptIcon(readStatus)}</span>
                ` : ''}
            </div>
        `;

        return messageDiv;
    }

    /**
     * Format date label
     * @param {string} dateString - Date string
     * @returns {string} Formatted date
     */
    formatDateLabel(dateString) {
        const date = new Date(dateString);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Today';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        } else {
            return date.toLocaleDateString('en-GB', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric'
            }).replace(/\//g, '/');
        }
    }

    /**
     * Format time
     * @param {string} dateString - Date string
     * @returns {string} Formatted time
     */
    formatTime(dateString) {
        return new Date(dateString).toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Get read receipt icon
     * @param {string} status - Read status
     * @returns {string} Icon HTML
     */
    getReadReceiptIcon(status) {
        switch (status) {
            case 'sent': return '&#10003;';
            case 'delivered': return '&#10003;&#10003;';
            case 'online': return '&#10003;';
            default: return '&#10003;';
        }
    }

    /**
     * Check if message is consecutive
     * @param {Object} message - Message object
     * @returns {boolean} Is consecutive
     */
    isConsecutive(message) {
        if (!this.lastMessage) return false;
        const lastSenderId = this.lastMessage.sender?.id ?? this.lastMessage.sender_id;
        const currentSenderId = message.sender?.id ?? message.sender_id;
        return lastSenderId === currentSenderId;
    }

    /**
     * Scroll to bottom of container
     */
    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }

  /**
   * Escape HTML to prevent XSS
   * @param {string} text - Text to escape
   * @returns {string} Escaped text
   */
  escapeHtml(text) {
    return escapeHtml(text);
  }

  /**
   * Show typing indicator
   * @param {Array} users - Array of typing users
   */
  showTypingIndicator(users) {
    const indicator = document.getElementById('typingIndicator');
    if (indicator && users.length > 0) {
      indicator.textContent = `${users[0]} is typing...`;
    }
  }

  /**
   * Hide typing indicator
   */
  hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) {
      indicator.textContent = '';
    }
  }
}
