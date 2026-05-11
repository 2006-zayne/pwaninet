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
        this.typingIndicatorElement = null;
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
     * Show typing indicator (ghost bubble with animated dots)
     * @param {string} username - Username of person typing
     */
    showTypingIndicator(username) {
        this._log('SHOW_TYPING_INDICATOR', { username });

        // Remove existing indicator if present
        this.hideTypingIndicator();

        // Create ghost bubble typing indicator
        this.typingIndicatorElement = document.createElement('div');
        this.typingIndicatorElement.className = 'message-wrapper received-wrapper';
        this.typingIndicatorElement.id = 'typingIndicator';

        const bubble = document.createElement('div');
        bubble.className = 'message-bubble received typing-bubble';

        // Animated dots
        bubble.innerHTML = `
            <div class="typing-dots">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        `;

        this.typingIndicatorElement.appendChild(bubble);

        // Add to container at the end (where new messages appear)
        this.container.appendChild(this.typingIndicatorElement);

        // Scroll to bottom
        this.container.scrollTop = this.container.scrollHeight;
    }

    /**
     * Hide typing indicator
     */
    hideTypingIndicator() {
        this._log('HIDE_TYPING_INDICATOR');

        if (this.typingIndicatorElement) {
            this.typingIndicatorElement.remove();
            this.typingIndicatorElement = null;
        }

        // Also remove any existing indicator from DOM
        const existing = document.getElementById('typingIndicator');
        if (existing) {
            existing.remove();
        }
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

        // Find last message that was READ by the receiver (for avatar display)
        const readMessages = ownMessages.filter(m => m.status === 'read');
        const lastReadMessageId =
            readMessages.length > 0
                ? readMessages[readMessages.length - 1].id
                : null;

        // Find last message from receiver
        const receiverMessages = messages.filter(m => m.senderId !== this.currentUserId);
        const lastReceiverMessageId =
            receiverMessages.length > 0
                ? receiverMessages[receiverMessages.length - 1].id
                : null;

        // Determine if read receipt should float to receiver's last message
        // This happens when receiver sent a message after reading
        let floatingReadReceiptTargetId = null;
        if (lastReadMessageId && lastReceiverMessageId) {
            const lastReadMsg = messages.find(m => m.id === lastReadMessageId);
            const lastReceiverMsg = messages.find(m => m.id === lastReceiverMessageId);
            if (lastReadMsg && lastReceiverMsg) {
                const readTimestamp = new Date(lastReadMsg.timestamp).getTime();
                const receiverTimestamp = new Date(lastReceiverMsg.timestamp).getTime();
                if (receiverTimestamp > readTimestamp) {
                    floatingReadReceiptTargetId = lastReceiverMessageId;
                }
            }
        }

        for (let i = 0; i < messages.length; i++) {
            const message = messages[i];
            const messageDate = new Date(message.timestamp).toDateString();
            const isOwn = message.senderId === this.currentUserId;

            if (messageDate !== lastDate) {
                viewItems.push({
                    viewType: 'date',
                    label: formatDateLabel(message.timestamp)
                });
                lastDate = messageDate;
                // Reset sender tracking - date separator breaks the group
                lastSenderId = null;
            }

            const isConsecutive = lastSenderId === message.senderId;
            lastSenderId = message.senderId;

            // Determine group position
            const nextMessage = messages[i + 1];
            // Only count next message as same group if same sender AND same date
            const nextMessageDate = nextMessage ? new Date(nextMessage.timestamp).toDateString() : null;
            const isNextSameDate = nextMessageDate === messageDate;
            const isNextFromSameSender = nextMessage && isNextSameDate && nextMessage.senderId === message.senderId;

            let groupPosition = 'single';
            if (isConsecutive && isNextFromSameSender) {
                groupPosition = 'middle'; // Has prev and next from same sender
            } else if (isConsecutive && !isNextFromSameSender) {
                groupPosition = 'last'; // Has prev but no next from same sender
            } else if (!isConsecutive && isNextFromSameSender) {
                groupPosition = 'first'; // No prev but has next from same sender
            }

            const isLastRead = isOwn && message.id === lastReadMessageId;
            const hasFloatingReadReceipt = message.id === floatingReadReceiptTargetId;
            // Hide read receipt avatar on sender's message only when:
            // 1. There's a floating receipt on receiver's message, AND
            // 2. This is the sender's last message, AND
            // 3. This message is actually READ (not sent/delivered)
            // This ensures new unread messages show checkmarks, not hidden receipt
            const hideReadReceipt = floatingReadReceiptTargetId && isOwn && message.id === lastOwnMessageId && message.status === 'read';

            viewItems.push({
                viewType: 'message',
                ...message,
                isOwn,
                isConsecutive,
                isLastSent: isOwn && message.id === lastOwnMessageId,
                isLastRead,
                hasFloatingReadReceipt,
                hideReadReceipt,
                groupPosition
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
        // DEBUG: Log message type detection
        console.log('[RENDERER] Creating message element. ID:', message.id, 'Type:', message.type, 'Metadata:', message.metadata);
        
        if (message.type === 'system') {
        return this._createSystemMessage(message);
        }

        if (message.type === 'emoji') {
        return this._createEmojiMessage(message);
        }

        if (message.type === 'media') {
        return this._createMediaMessage(message);
        }

        if (message.type === 'link') {
        console.log('[RENDERER] Creating link message for:', message.id);
        return this._createLinkMessage(message);
        }
        // Build wrapper containing bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Create bubble (no timestamp/read receipt inside)
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} group-${message.groupPosition} ${message.isLastSent ? 'last-sent' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.senderId);
        messageDiv.setAttribute('data-status', message.status);
        messageDiv.setAttribute('data-group-position', message.groupPosition);

        // Apply custom bubble style if set
        this._applyBubbleStyle(messageDiv);

        // Use canonical schema fields
        const status = message.status || 'sent';

        // Bubble content
        messageDiv.innerHTML = `
            <p class="message-content">${escapeHtml(message.content || '')}</p>
        `;

        // Determine whether to render meta (timestamp + receipt): single messages or last in group
        const shouldRenderMeta = message.groupPosition === 'single' || message.groupPosition === 'last' || !!message.hasFloatingReadReceipt;
        if (shouldRenderMeta) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';

            const timeSpan = document.createElement('span');
            timeSpan.className = 'timestamp';
            timeSpan.textContent = formatTime(message.timestamp);
            metaDiv.appendChild(timeSpan);

            // Read receipt / status to appear next to timestamp
            if (message.isOwn) {
                if (message.status === 'read' && message.isLastRead) {
                    const receiverAvatar = document.body.dataset.receiverAvatar;
                    const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = 'message-read-receipt read-avatar-only';
                    receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                    metaDiv.appendChild(receiptSpan);
                } else if (message.isLastSent && !message.hideReadReceipt) {
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = `message-read-receipt status-${status}`;
                    receiptSpan.innerHTML = this._getStatusIcon(status);
                    metaDiv.appendChild(receiptSpan);
                }
            } else if (message.hasFloatingReadReceipt) {
                const receiverAvatar = document.body.dataset.receiverAvatar;
                const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                const receiptSpan = document.createElement('span');
                receiptSpan.className = 'message-read-receipt floating-read-receipt';
                receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                metaDiv.appendChild(receiptSpan);
            }

            wrapperDiv.appendChild(messageDiv);
            wrapperDiv.appendChild(metaDiv);
            return wrapperDiv;
        }

        return messageDiv;
    }

    /**
     * Get status icon (pure data transformation)
     * @param {string} status - Message status from canonical schema
     * @returns {string} Icon HTML - checkmark inside circle
     */
    _getStatusIcon(status) {
        // Single checkmark inside circle
        const singleCheck = '<span class="check-circle"><span class="check-mark">&#10003;</span></span>';
        // Double checkmark inside circle (for delivered/read before avatar)
        const doubleCheck = '<span class="check-circle"><span class="check-mark double">&#10003;&#10003;</span></span>';
        
        switch (status) {
            case 'sent': return singleCheck;
            case 'delivered': return doubleCheck;
            case 'read': return doubleCheck; // Will be replaced by avatar, but fallback
            case 'failed': return '<span class="check-circle error">&#10007;</span>';
            default: return singleCheck;
        }
    }

    /**
     * Apply custom bubble style from user preferences
     * @param {HTMLElement} bubble - Message bubble element
     */
    _applyBubbleStyle(bubble) {
        const currentStyle = document.body?.dataset?.bubbleStyle;
        // CSS handles the actual styling via data-bubble-shape attribute
        // We just need to ensure the document has the attribute set
        if (currentStyle && currentStyle !== 'default') {
            document.documentElement.dataset.bubbleShape = currentStyle;
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
        // Build wrapper containing emoji and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Create emoji element (no bubble styling)
        const emojiDiv = document.createElement('div');
        emojiDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} emoji-message group-${message.groupPosition}`;
        emojiDiv.setAttribute('data-message-id', message.id);
        emojiDiv.setAttribute('data-sender-id', message.senderId);
        emojiDiv.setAttribute('data-status', message.status);
        emojiDiv.setAttribute('data-group-position', message.groupPosition);
        
        emojiDiv.innerHTML = `<div class="emoji-content">${escapeHtml(message.content || '')}</div>`;

        // Determine whether to render meta (timestamp + receipt): single messages or last in group
        const shouldRenderMeta = message.groupPosition === 'single' || message.groupPosition === 'last' || !!message.hasFloatingReadReceipt;
        if (shouldRenderMeta) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';

            const timeSpan = document.createElement('span');
            timeSpan.className = 'timestamp';
            timeSpan.textContent = formatTime(message.timestamp);
            metaDiv.appendChild(timeSpan);

            // Read receipt / status to appear next to timestamp
            if (message.isOwn) {
                const status = message.status || 'sent';
                if (message.status === 'read' && message.isLastRead) {
                    const receiverAvatar = document.body.dataset.receiverAvatar;
                    const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = 'message-read-receipt read-avatar-only';
                    receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                    metaDiv.appendChild(receiptSpan);
                } else if (message.isLastSent && !message.hideReadReceipt) {
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = `message-read-receipt status-${status}`;
                    receiptSpan.innerHTML = this._getStatusIcon(status);
                    metaDiv.appendChild(receiptSpan);
                }
            } else if (message.hasFloatingReadReceipt) {
                const receiverAvatar = document.body.dataset.receiverAvatar;
                const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                const receiptSpan = document.createElement('span');
                receiptSpan.className = 'message-read-receipt floating-read-receipt';
                receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                metaDiv.appendChild(receiptSpan);
            }

            wrapperDiv.appendChild(emojiDiv);
            wrapperDiv.appendChild(metaDiv);
            return wrapperDiv;
        }

        return emojiDiv;
    }

    /**
     * Create media message element (pure DOM creation)
     * @param {Object} message - Media message object
     * @returns {HTMLElement} Media message element
     */
    _createMediaMessage(message) {
        // Build wrapper containing bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Create bubble
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} media-message group-${message.groupPosition}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.senderId);
        messageDiv.setAttribute('data-status', message.status);
        messageDiv.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(messageDiv);
        
        let mediaContent = '';
        const metadata = message.metadata || {};
        
        if (metadata.url) {
            const attachmentType = metadata.type || 'file';
            
            switch (attachmentType) {
                case 'image':
                    mediaContent = `<img src="${escapeHtml(metadata.url)}" alt="Image" class="media-image" loading="lazy">`;
                    break;
                case 'video':
                    mediaContent = `
                        <video controls class="media-video">
                            <source src="${escapeHtml(metadata.url)}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>`;
                    break;
                case 'audio':
                    mediaContent = `
                        <div class="media-audio-container">
                            <audio controls class="media-audio">
                                <source src="${escapeHtml(metadata.url)}" type="audio/mpeg">
                                Your browser does not support the audio tag.
                            </audio>
                        </div>`;
                    break;
                default:
                    // Document or other file types
                    const fileName = message.content || 'Attachment';
                    const fileIcon = this._getFileIcon(attachmentType);
                    mediaContent = `
                        <a href="${escapeHtml(metadata.url)}" target="_blank" class="media-link">
                            <div class="media-file">
                                <span class="file-icon">${fileIcon}</span>
                                <span class="file-name">${escapeHtml(fileName)}</span>
                            </div>
                        </a>`;
                    break;
            }
        } else {
            mediaContent = `<p class="message-content">${escapeHtml(message.content || '')}</p>`;
        }
        
        messageDiv.innerHTML = mediaContent;

        // Determine whether to render meta (timestamp + receipt)
        const shouldRenderMeta = message.groupPosition === 'single' || message.groupPosition === 'last' || !!message.hasFloatingReadReceipt;
        if (shouldRenderMeta) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';

            const timeSpan = document.createElement('span');
            timeSpan.className = 'timestamp';
            timeSpan.textContent = formatTime(message.timestamp);
            metaDiv.appendChild(timeSpan);

            // Read receipt / status to appear next to timestamp
            if (message.isOwn) {
                const status = message.status || 'sent';
                if (message.status === 'read' && message.isLastRead) {
                    const receiverAvatar = document.body.dataset.receiverAvatar;
                    const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = 'message-read-receipt read-avatar-only';
                    receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                    metaDiv.appendChild(receiptSpan);
                } else if (message.isLastSent && !message.hideReadReceipt) {
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = `message-read-receipt status-${status}`;
                    receiptSpan.innerHTML = this._getStatusIcon(status);
                    metaDiv.appendChild(receiptSpan);
                }
            } else if (message.hasFloatingReadReceipt) {
                const receiverAvatar = document.body.dataset.receiverAvatar;
                const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                const receiptSpan = document.createElement('span');
                receiptSpan.className = 'message-read-receipt floating-read-receipt';
                receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                metaDiv.appendChild(receiptSpan);
            }

            wrapperDiv.appendChild(messageDiv);
            wrapperDiv.appendChild(metaDiv);
            return wrapperDiv;
        }

        return messageDiv;
    }

    /**
     * Get file icon based on attachment type
     * @param {string} type - Attachment type
     * @returns {string} Icon HTML
     */
    _getFileIcon(type) {
        const icons = {
            'document': '📄',
            'pdf': '📕',
            'file': '📎'
        };
        return icons[type] || icons['file'];
    }

    /**
     * Create link message element (pure DOM creation)
     * @param {Object} message - Link message object
     * @returns {HTMLElement} Link message element
     */
    _createLinkMessage(message) {
        console.log('[RENDERER] _createLinkMessage called with:', message);
        
        // Build wrapper containing bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Create bubble
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} link-message group-${message.groupPosition}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.senderId);
        messageDiv.setAttribute('data-status', message.status);
        messageDiv.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(messageDiv);
        
        const metadata = message.metadata || {};
        const linkUrl = metadata.link_url;
        const linkTitle = metadata.link_title;
        const linkDescription = metadata.link_description;
        const linkImage = metadata.link_image;
        const linkType = metadata.link_type || 'link';
        
        let linkContent = '';
        
        // Check if this is an embed type (Facebook, YouTube, etc.)
        if (linkType === 'youtube') {
            linkContent = this._createYouTubeEmbed(linkUrl);
        } else if (linkType === 'facebook') {
            linkContent = this._createFacebookEmbed(linkUrl);
        } else {
            // Rich link preview card
            linkContent = `
                <a href="${escapeHtml(linkUrl)}" target="_blank" class="link-preview-card" rel="noopener noreferrer">
                    ${linkImage ? `<img src="${escapeHtml(linkImage)}" alt="Link preview" class="link-preview-image" loading="lazy">` : ''}
                    <div class="link-preview-content">
                        <div class="link-preview-title">${escapeHtml(linkTitle || linkUrl)}</div>
                        ${linkDescription ? `<div class="link-preview-description">${escapeHtml(linkDescription)}</div>` : ''}
                        <div class="link-preview-domain">${this._extractDomain(linkUrl)}</div>
                    </div>
                </a>
            `;
        }
        
        // Add text content if present
        const textContent = message.content ? `<p class="message-content">${escapeHtml(message.content)}</p>` : '';
        
        messageDiv.innerHTML = textContent + linkContent;

        // Determine whether to render meta (timestamp + receipt)
        const shouldRenderMeta = message.groupPosition === 'single' || message.groupPosition === 'last' || !!message.hasFloatingReadReceipt;
        if (shouldRenderMeta) {
            const metaDiv = document.createElement('div');
            metaDiv.className = 'message-meta';

            const timeSpan = document.createElement('span');
            timeSpan.className = 'timestamp';
            timeSpan.textContent = formatTime(message.timestamp);
            metaDiv.appendChild(timeSpan);

            // Read receipt / status to appear next to timestamp
            if (message.isOwn) {
                const status = message.status || 'sent';
                if (message.status === 'read' && message.isLastRead) {
                    const receiverAvatar = document.body.dataset.receiverAvatar;
                    const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = 'message-read-receipt read-avatar-only';
                    receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                    metaDiv.appendChild(receiptSpan);
                } else if (message.isLastSent && !message.hideReadReceipt) {
                    const receiptSpan = document.createElement('span');
                    receiptSpan.className = `message-read-receipt status-${status}`;
                    receiptSpan.innerHTML = this._getStatusIcon(status);
                    metaDiv.appendChild(receiptSpan);
                }
            } else if (message.hasFloatingReadReceipt) {
                const receiverAvatar = document.body.dataset.receiverAvatar;
                const avatarUrl = message.metadata?.read_avatar || receiverAvatar || '/static/images/default_pic1.jpg';
                const receiptSpan = document.createElement('span');
                receiptSpan.className = 'message-read-receipt floating-read-receipt';
                receiptSpan.innerHTML = `<img src="${escapeHtml(avatarUrl)}" alt="Read" class="read-avatar-img">`;
                metaDiv.appendChild(receiptSpan);
            }

            wrapperDiv.appendChild(messageDiv);
            wrapperDiv.appendChild(metaDiv);
            return wrapperDiv;
        }

        return messageDiv;
    }

    /**
     * Create YouTube embed
     * @param {string} url - YouTube URL
     * @returns {string} Embed HTML
     */
    _createYouTubeEmbed(url) {
        const videoId = this._extractYouTubeId(url);
        if (!videoId) {
            // Fallback to link preview if we can't extract video ID
            return `<a href="${escapeHtml(url)}" target="_blank" class="link-preview-card">${escapeHtml(url)}</a>`;
        }
        
        return `
            <div class="video-embed">
                <iframe
                    src="https://www.youtube.com/embed/${videoId}"
                    frameborder="0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowfullscreen
                    class="youtube-embed">
                </iframe>
            </div>
        `;
    }

    /**
     * Create Facebook embed
     * @param {string} url - Facebook URL
     * @returns {string} Embed HTML
     */
    _createFacebookEmbed(url) {
        // Facebook requires their embed SDK, so we'll use a link preview for now
        return `
            <a href="${escapeHtml(url)}" target="_blank" class="link-preview-card facebook-link" rel="noopener noreferrer">
                <div class="facebook-embed-placeholder">
                    <span class="facebook-icon">📘</span>
                    <span class="facebook-text">View on Facebook</span>
                </div>
            </a>
        `;
    }

    /**
     * Extract YouTube video ID from URL
     * @param {string} url - YouTube URL
     * @returns {string|null} Video ID
     */
    _extractYouTubeId(url) {
        const patterns = [
            /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
            /youtube\.com\/shorts\/([^&\n?#]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        
        return null;
    }

    /**
     * Extract domain from URL
     * @param {string} url - URL
     * @returns {string} Domain
     */
    _extractDomain(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname;
        } catch (e) {
            return url;
        }
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
