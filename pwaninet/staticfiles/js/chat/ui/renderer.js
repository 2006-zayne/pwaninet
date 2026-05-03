/**
 * MessageRenderer - Pure rendering only
 * NO logic, NO state ownership, NO business decisions
 * Pure DOM manipulation based on provided data
 */

import { formatDateLabel, formatTime, escapeHtml } from '../shared/utils.js';

export class MessageRenderer {
    constructor() {
        this.container = null;
        this.currentUserId = null;
        this.lastRenderedCount = 0;
        this.isRendering = false;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    }

    /**
     * Initialize renderer (pure setup)
     */
    init(currentUserId) {
        this._log('RENDERER_INIT');

        this.container = document.getElementById('messagesContainer');
        this.currentUserId = currentUserId;
        
        if (!this.container) {
            console.error('MessageRenderer: Messages container not found');
            return;
        }
        
        this._log('RENDERER_INITIALIZED');
    }

    /**
     * Render messages (pure rendering only)
     * @param {Array} messages - Messages array from store (canonical schema)
     */
    render(messages) {
        console.log("[RENDERER] RENDER CALLED - messages count:", messages?.length);
        
        if (this.isRendering) {
            console.log("[RENDERER] Already rendering, skipping");
            return;
        }

        this.isRendering = true;

        try {
            if (!this.container) {
                console.error('[RENDERER] ERROR: Container not initialized');
                return;
            }

            console.log("[RENDERER] Starting render with", messages?.length || 0, "messages");

            // Always FULL RENDER (no diffing inside renderer)
            this.container.innerHTML = '';

            const viewItems = this._buildView(messages || []);
            console.log("[RENDERER] Built view items:", viewItems?.length);

            for (const item of viewItems || []) {
                const viewType = item?.viewType;
                console.log("[RENDERER] Processing item viewType:", JSON.stringify(viewType), "id:", item?.id, "label:", item?.label);
                
                if (viewType === 'date') {
                    console.log("[RENDERER] Creating date element:", item.label);
                    this.container.appendChild(this._createDateElement(item.label));
                } else if (viewType === 'message') {
                    console.log("[RENDERER] >>> CREATING MESSAGE ELEMENT for:", item.id);
                    try {
                        const msgEl = this._createMessageElement(item);
                        console.log("[RENDERER] Message element created:", msgEl?.tagName, msgEl?.className);
                        this.container.appendChild(msgEl);
                        console.log("[RENDERER] Message appended successfully");
                    } catch (err) {
                        console.error("[RENDERER] ERROR creating message:", err, item);
                    }
                } else {
                    console.warn("[RENDERER] UNKNOWN item viewType:", viewType, item);
                }
            }
            console.log("[RENDERER] Render complete. Container children:", this.container?.children?.length);

            this.lastRenderedCount = messages.length;
            this._scrollToBottom();

        } finally {
            this.isRendering = false;
        }
    }
        /**
     * Build view from messages (pure data transformation)
     * @param {Array} messages - Messages array (canonical schema)
     * @returns {Array} View items
     */
    _buildView(messages) {
        const viewItems = [];
        let lastDate = null;
        let lastSenderId = null;

        const ownMessages = messages.filter(
            m => m.senderId === this.currentUserId
        );

        const lastOwnMessageId =
            ownMessages.length > 0
                ? ownMessages[ownMessages.length - 1].id
                : null;

        for (const message of messages) {
            const messageDate = new Date(message.timestamp).toDateString();
            const isOwn = message.senderId === this.currentUserId;

            if (messageDate !== lastDate) {
                viewItems.push({
                    viewType: 'date',
                    label: formatDateLabel(message.timestamp)
                });
                lastDate = messageDate;
            }

            const isConsecutive = lastSenderId === message.senderId;
            lastSenderId = message.senderId;

            viewItems.push({
                viewType: 'message',
                ...message,
                isOwn,
                isConsecutive,
                isLastSent: isOwn && message.id === lastOwnMessageId
            });
        }

        return viewItems;
    }

    /**
     * Create date separator element (pure DOM creation)
     * @param {string} label - Date label
     * @returns {HTMLElement} Date element
     */
    _createDateElement(label) {
        const element = document.createElement('div');
        element.className = 'date-separator';
        element.innerHTML = `<span>${escapeHtml(label)}</span>`;
        return element;
    }

    /**
     * Create message element (pure DOM creation)
     * @param {Object} message - Message object with view properties (canonical schema)
     * @returns {HTMLElement} Message element
     */
    _createMessageElement(message) {
        if (message.type === 'system') {
        return this._createSystemMessage(message);
        }

        if (message.type === 'emoji') {
        return this._createEmojiMessage(message);
        }

        if (message.type === 'media') {
        return this._createMediaMessage(message);
        }
        // Create message bubble (pure DOM manipulation)
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} ${message.isConsecutive ? 'consecutive-message' : 'first-in-group'} ${message.isLastSent ? 'last-sent' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.senderId);
        messageDiv.setAttribute('data-status', message.status);

        // Use canonical schema fields
        const status = message.status || 'sent';
        
        // Build message content (pure HTML generation)
        let messageHTML = `
            <p class="message-content">${escapeHtml(message.content || '')}</p>
            <div class="message-time">
                ${formatTime(message.timestamp)}
        `;

        if (message.isOwn) {
            messageHTML += `<span class="message-read-receipt">${this._getStatusIcon(status)}</span>`;
        }
        

        messageHTML += `
            </div>
        `;

        messageDiv.innerHTML = messageHTML;
        return messageDiv;
    }

    /**
     * Get status icon (pure data transformation)
     * @param {string} status - Message status from canonical schema
     * @returns {string} Icon HTML
     */
    _getStatusIcon(status) {
        switch (status) {
            case 'sent': return '&#10003;';
            case 'delivered': return '&#10003;&#10003;';
            case 'read': return '&#10003;&#10003;';
            case 'failed': return '❌';
            default: return '&#10003;';
        }
    }

    /**
     * Create system message element (pure DOM creation)
     * @param {Object} message - System message object
     * @returns {HTMLElement} System message element
     */
    _createSystemMessage(message) {
        const element = document.createElement('div');
        element.className = 'system-message';
        element.innerHTML = `<span class="system-text">${escapeHtml(message.content || '')}</span>`;
        return element;
    }

    /**
     * Create emoji message element (pure DOM creation)
     * @param {Object} message - Emoji message object
     * @returns {HTMLElement} Emoji message element
     */
    _createEmojiMessage(message) {
        const element = document.createElement('div');
        element.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} emoji-message`;
        element.setAttribute('data-message-id', message.id);
        element.innerHTML = `
            <div class="emoji-content">${escapeHtml(message.content || '')}</div>
            <div class="message-time">${formatTime(message.timestamp)}</div>
        `;
        return element;
    }

    /**
     * Create media message element (pure DOM creation)
     * @param {Object} message - Media message object
     * @returns {HTMLElement} Media message element
     */
    _createMediaMessage(message) {
        const element = document.createElement('div');
        element.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} media-message`;
        element.setAttribute('data-message-id', message.id);
        
        let mediaContent = '';
        const metadata = message.metadata || {};
        
        if (metadata.url) {
            if (message.content?.includes('image') || metadata.type?.includes('image')) {
                mediaContent = `<img src="${escapeHtml(metadata.url)}" alt="Image" class="media-image">`;
            } else {
                mediaContent = `<a href="${escapeHtml(metadata.url)}" target="_blank" class="media-link">${escapeHtml(message.content || 'Attachment')}</a>`;
            }
        } else {
            mediaContent = `<p class="message-content">${escapeHtml(message.content || '')}</p>`;
        }
        
        element.innerHTML = `
            ${mediaContent}
            <div class="message-time">${formatTime(message.timestamp)}</div>
        `;
        return element;
    }

    /**
     * Scroll to bottom of container (pure DOM manipulation)
     */
    _scrollToBottom() {
        if (this.container) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    /**
     * Update current user ID (if store changes)
     * @param {number} userId - User ID
     */
    updateCurrentUserId(userId) {
        this.currentUserId = userId;
        this._log('CURRENT_USER_ID_UPDATED', { userId });
    }

    /**
     * Get renderer status (read-only)
     * @returns {Object} Status
     */
    getStatus() {
        return {
            initialized: !!this.container,
            currentUserId: this.currentUserId,
            isRendering: this.isRendering,
            containerExists: !!this.container,
            isPureRendering: true // Explicitly mark as pure rendering
        };
    }

    /**
     * Destroy renderer
     */
    destroy() {
        this._log('RENDERER_DESTROY');
        
        this.container = null;
        this.currentUserId = null;
        this.isRendering = false;
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[RENDERER] ${action}:`, data);
        }
    }
}
