/**
 * MessageRenderer - Pure rendering only
 * NO logic, NO state ownership, NO business decisions
 * Pure DOM manipulation based on provided data
 */

import { formatDateLabel, formatTime, formatPreciseTime, escapeHtml } from '../shared/utils.js';
import { renderMessageStatus } from '../shared/message-status-renderer.js';

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

            // Group consecutive message items by sender into message-groups
            let currentGroup = null;

            const flushGroup = () => {
                if (!currentGroup || currentGroup.messages.length === 0) return;
                try {
                    const groupEl = this._createMessageGroup(currentGroup);
                    this.container.appendChild(groupEl);
                } catch (err) {
                    console.error("[RENDERER] ERROR creating message group:", err);
                }
                currentGroup = null;
            };

            for (const item of viewItems || []) {
                const viewType = item?.viewType;

                if (viewType === 'date') {
                    flushGroup();
                    this.container.appendChild(this._createDateElement(item.label));
                } else if (viewType === 'time') {
                    flushGroup();
                    this.container.appendChild(this._createTimeElement(item.label, item.preciseLabel));
                } else if (viewType === 'message') {
                    // Check if this message belongs to the current group
                    if (currentGroup && currentGroup.senderId === item.senderId && currentGroup.isOwn === item.isOwn) {
                        currentGroup.messages.push(item);
                    } else {
                        flushGroup();
                        currentGroup = {
                            senderId: item.senderId,
                            isOwn: item.isOwn,
                            messages: [item]
                        };
                    }
                } else {
                    flushGroup();
                    console.warn("[RENDERER] UNKNOWN item viewType:", viewType, item);
                }
            }
            flushGroup();

            console.log("[RENDERER] Render complete. Container children:", this.container?.children?.length);

            this.lastRenderedCount = messages.length;
            this._scrollToBottom();

            // Add event listeners for retry buttons
            this._attachRetryButtonListeners();

        } finally {
            this.isRendering = false;
        }
    }

    /**
     * Create a message group element containing avatar, bubble group, and meta
     * @param {Object} group - { senderId, isOwn, messages: [...] }
     * @returns {HTMLElement} Message group element
     */
    _createMessageGroup(group) {
        const { senderId, isOwn, messages } = group;
        const lastMessage = messages[messages.length - 1];

        const groupDiv = document.createElement('div');
        groupDiv.className = `message-group ${isOwn ? 'sent-group' : 'received-group'}`;

        // Avatar for received messages — appears once per group, aligned to bottom
        if (!isOwn) {
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'group-avatar';
            const avatarUrl = this._getSenderAvatar(senderId);
            const avatarImg = document.createElement('img');
            avatarImg.className = 'message-avatar';
            avatarImg.src = avatarUrl;
            avatarImg.alt = 'Avatar';
            avatarDiv.appendChild(avatarImg);
            groupDiv.appendChild(avatarDiv);
        }

        // Content column: bubble-group + meta
        const contentDiv = document.createElement('div');
        contentDiv.className = 'group-content';

        const bubbleGroupDiv = document.createElement('div');
        bubbleGroupDiv.className = 'bubble-group';

        for (const message of messages) {
            try {
                const bubbleEl = this._createBubbleElement(message);
                bubbleGroupDiv.appendChild(bubbleEl);
            } catch (err) {
                console.error("[RENDERER] ERROR creating bubble:", err, message);
            }
        }

        contentDiv.appendChild(bubbleGroupDiv);

        // Meta row (timestamp + read receipt) — once per group, below bubbles
        const metaDiv = this._createGroupMeta(lastMessage);
        if (metaDiv) {
            contentDiv.appendChild(metaDiv);
        }

        groupDiv.appendChild(contentDiv);
        return groupDiv;
    }

    /**
     * Create the meta row for a message group (timestamp + read receipt)
     * @param {Object} message - The last message in the group
     * @returns {HTMLElement|null} Meta element or null
     */
    _createGroupMeta(message) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'timestamp';
        timeSpan.textContent = formatTime(message.timestamp);
        metaDiv.appendChild(timeSpan);

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
                receiptSpan.innerHTML = this._getStatusIcon(status, message.id, message);
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

        return metaDiv;
    }

    /**
     * Create a bubble element for a single message (no wrapper/avatar/meta)
     * @param {Object} message - Message with view properties
     * @returns {HTMLElement} Bubble element
     */
    _createBubbleElement(message) {
        if (message.type === 'system') {
            return this._createSystemMessage(message);
        }
        if (message.type === 'emoji') {
            return this._createEmojiBubble(message);
        }
        if (message.type === 'media') {
            return this._createMediaBubble(message);
        }
        if (message.type === 'link') {
            return this._createLinkBubble(message);
        }
        return this._createTextBubble(message);
    }

    /**
     * Create a text bubble (no wrapper)
     * @param {Object} message - Message object
     * @returns {HTMLElement} Bubble element
     */
    _createTextBubble(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} group-${message.groupPosition} ${message.isLastSent ? 'last-sent' : ''}`;
        messageDiv.setAttribute('data-message-id', message.id);
        messageDiv.setAttribute('data-sender-id', message.senderId);
        messageDiv.setAttribute('data-status', message.status);
        messageDiv.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(messageDiv);

        messageDiv.innerHTML = `<p class="message-content">${escapeHtml(message.content || '')}</p>`;
        return messageDiv;
    }

    /**
     * Create an emoji bubble (no wrapper)
     * @param {Object} message - Emoji message object
     * @returns {HTMLElement} Bubble element
     */
    _createEmojiBubble(message) {
        const emojiDiv = document.createElement('div');
        emojiDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} emoji-message group-${message.groupPosition}`;
        emojiDiv.setAttribute('data-message-id', message.id);
        emojiDiv.setAttribute('data-sender-id', message.senderId);
        emojiDiv.setAttribute('data-status', message.status);
        emojiDiv.setAttribute('data-group-position', message.groupPosition);
        emojiDiv.innerHTML = `<div class="emoji-content">${escapeHtml(message.content || '')}</div>`;
        return emojiDiv;
    }

    /**
     * Create a media bubble (no wrapper)
     * @param {Object} message - Media message object
     * @returns {HTMLElement} Bubble element
     */
    _createMediaBubble(message) {
        const metadata = message.metadata || {};
        const attachmentType = metadata.type || 'file';
        const isImageOrVideo = attachmentType === 'image' || attachmentType === 'video';

        let messageDiv;
        let mediaContent = '';

        if (isImageOrVideo && metadata.url) {
            messageDiv = document.createElement('div');
            messageDiv.className = `media-bubble-wrapper ${message.isOwn ? 'sent' : 'received'} group-${message.groupPosition}`;
            messageDiv.setAttribute('data-message-id', message.id);
            messageDiv.setAttribute('data-sender-id', message.senderId);
            messageDiv.setAttribute('data-status', message.status);
            messageDiv.setAttribute('data-group-position', message.groupPosition);

            if (attachmentType === 'image') {
                mediaContent = `<img src="${escapeHtml(metadata.url)}" alt="Image" class="media-image" loading="lazy">`;
            } else {
                mediaContent = `
                    <video controls class="media-video">
                        <source src="${escapeHtml(metadata.url)}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>`;
            }
            messageDiv.innerHTML = mediaContent;

            // Wrap with caption if present
            if (message.content && message.content.trim()) {
                const wrapper = document.createElement('div');
                wrapper.className = 'media-with-caption';
                wrapper.appendChild(messageDiv);
                const captionDiv = document.createElement('div');
                captionDiv.className = 'media-caption';
                captionDiv.textContent = message.content;
                wrapper.appendChild(captionDiv);
                return wrapper;
            }
        } else {
            messageDiv = document.createElement('div');
            messageDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} media-message group-${message.groupPosition}`;
            messageDiv.setAttribute('data-message-id', message.id);
            messageDiv.setAttribute('data-sender-id', message.senderId);
            messageDiv.setAttribute('data-status', message.status);
            messageDiv.setAttribute('data-group-position', message.groupPosition);
            this._applyBubbleStyle(messageDiv);

            if (metadata.url) {
                switch (attachmentType) {
                    case 'audio':
                        mediaContent = `
                            <div class="media-audio-container">
                                <audio controls class="media-audio">
                                    <source src="${escapeHtml(metadata.url)}" type="audio/mpeg">
                                    Your browser does not support the audio tag.
                                </audio>
                            </div>`;
                        break;
                    default: {
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
                }
            } else {
                mediaContent = `<p class="message-content">${escapeHtml(message.content || '')}</p>`;
            }
            messageDiv.innerHTML = mediaContent;
        }

        return messageDiv;
    }

    /**
     * Create a link bubble (no wrapper)
     * @param {Object} message - Link message object
     * @returns {HTMLElement} Bubble element
     */
    _createLinkBubble(message) {
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

        if (linkType === 'youtube') {
            linkContent = this._createYouTubeEmbed(linkUrl);
        } else if (linkType === 'facebook') {
            linkContent = this._createFacebookEmbed(linkUrl);
        } else {
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

        const textContent = message.content ? `<p class="message-content">${escapeHtml(message.content)}</p>` : '';
        messageDiv.innerHTML = textContent + linkContent;
        return messageDiv;
    }
    
    /**
     * Attach event listeners for retry buttons
     */
    _attachRetryButtonListeners() {
        const retryButtons = this.container.querySelectorAll('.retry-button');
        retryButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const messageId = button.getAttribute('data-message-id');
                this._log('RETRY_BUTTON_CLICKED', { messageId });
                
                // Emit event for UI controller to handle retry
                const event = new CustomEvent('messageRetry', {
                    detail: { messageId }
                });
                window.dispatchEvent(event);
            });
        });
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
        let lastTimestamp = null;

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
            const messageTimestamp = new Date(message.timestamp).getTime();
            const isOwn = message.senderId === this.currentUserId;

            if (messageDate !== lastDate) {
                viewItems.push({
                    viewType: 'date',
                    label: formatDateLabel(message.timestamp)
                });
                lastDate = messageDate;
                // Reset sender tracking - date separator breaks the group
                lastSenderId = null;
                // Reset timestamp tracking - date separator resets time grouping
                lastTimestamp = null;
            }

            // Check for micro time separator (15-minute gap)
            // Only insert if not the first message after a date separator
            if (lastTimestamp !== null) {
                const timeGapMinutes = (messageTimestamp - lastTimestamp) / (1000 * 60);
                if (timeGapMinutes >= 15) {
                    viewItems.push({
                        viewType: 'time',
                        label: formatTime(message.timestamp),
                        preciseLabel: formatPreciseTime(message.timestamp)
                    });
                    // Reset sender tracking - time separator breaks the group
                    lastSenderId = null;
                }
            }

            // Check if messages should be grouped (same sender, within 5 minutes)
            let shouldGroup = false;
            if (lastSenderId === message.senderId && lastTimestamp !== null) {
                const timeGapMinutes = (messageTimestamp - lastTimestamp) / (1000 * 60);
                shouldGroup = timeGapMinutes < 5;
            }

            const isConsecutive = lastSenderId === message.senderId && shouldGroup;
            lastSenderId = message.senderId;
            lastTimestamp = messageTimestamp;

            // Determine group position
            const nextMessage = messages[i + 1];
            // Only count next message as same group if same sender AND same date AND within 5 minutes
            let isNextFromSameSender = false;
            if (nextMessage) {
                const nextMessageDate = new Date(nextMessage.timestamp).toDateString();
                const nextMessageTimestamp = new Date(nextMessage.timestamp).getTime();
                const isNextSameDate = nextMessageDate === messageDate;
                const timeGapToNextMinutes = (nextMessageTimestamp - messageTimestamp) / (1000 * 60);
                isNextFromSameSender = isNextSameDate && 
                                      nextMessage.senderId === message.senderId && 
                                      timeGapToNextMinutes < 5;
            }

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
     * Create micro time separator element (pure DOM creation)
     * @param {string} label - Time label (e.g., "2:31 PM")
     * @param {string} preciseLabel - Precise time label for hover (e.g., "Today at 2:31:44 PM")
     * @returns {HTMLElement} Time separator element
     */
    _createTimeElement(label, preciseLabel) {
        const element = document.createElement('div');
        element.className = 'time-separator';
        element.setAttribute('data-precise-time', escapeHtml(preciseLabel));
        element.innerHTML = `<span class="time-label">${escapeHtml(label)}</span>`;
        return element;
    }

    /**
     * Create message element (legacy entry point, delegates to _createBubbleElement)
     * @param {Object} message - Message object with view properties (canonical schema)
     * @returns {HTMLElement} Message element
     */
    _createMessageElement(message) {
        return this._createBubbleElement(message);
    }

    /**
     * Get status icon (pure data transformation)
     * @param {string} status - Message status from canonical schema
     * @param {string} messageId - Message ID for retry button
     * @param {Object} message - Full message object for context (optional)
     * @returns {string} Icon HTML - checkmark inside circle
     * @deprecated Use renderMessageStatus from message-status-renderer.js instead
     */
    _getStatusIcon(status, messageId, message = null) {
        const context = {};
        
        // Pass queuedAt timestamp if available for delayed visibility logic
        if (message && message.metadata) {
            if (message.metadata.queuedAt) {
                context.queuedAt = message.metadata.queuedAt;
            }
        }
        
        return renderMessageStatus(status, messageId, null, context);
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

    /* _createEmojiMessage removed — replaced by _createEmojiBubble + _createMessageGroup */

    /* _createMediaMessage removed — replaced by _createMediaBubble + _createMessageGroup */

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

    /* _createLinkMessage removed — replaced by _createLinkBubble + _createMessageGroup */

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
     * Get sender avatar URL
     * @param {number} senderId - Sender user ID
     * @returns {string} Avatar URL
     */
    _getSenderAvatar(senderId) {
        // Try to get avatar from dataset (set by template)
        const receiverAvatar = document.body.dataset.receiverAvatar;
        if (receiverAvatar) {
            return receiverAvatar;
        }
        // Fallback to default avatar
        return '/static/images/default_pic1.jpg';
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
