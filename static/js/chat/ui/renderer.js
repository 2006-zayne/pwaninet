/**
 * MessageRenderer - Pure rendering only
 * NO logic, NO state ownership, NO business decisions
 * Pure DOM manipulation based on provided data
 */

import { formatDateLabel, formatTime, formatPreciseTime, escapeHtml } from '../shared/utils.js';
import { renderMessageStatus } from '../shared/message-status-renderer.js';
import { linkPreviewRenderer } from '../features/link-preview/link-preview-renderer.js';
import { EVENTS } from '../shared/constants.js';
import { eventBus } from '../core/event-bus.js';
import { deviceMediaStore } from '../core/device-media-store.js';

export class MessageRenderer {
    constructor() {
        this.container = null;
        this.currentUserId = null;
        this.lastRenderedCount = 0;
        this.isRendering = false;
        this.typingIndicatorElement = null;
        this.downloadedMediaIds = new Set();
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    }

    /**
     * Initialize renderer (pure setup)
     */
    init(currentUserId) {
        this._log('RENDERER_INIT');

        this.container = document.getElementById('messagesContainer');
        this.currentUserId = currentUserId;

        // Initialize device media store (Capacitor filesystem or IndexedDB)
        deviceMediaStore.init().catch(err => console.warn('[RENDERER] DeviceMediaStore init error:', err));

        if (!this.container) {
            console.error('MessageRenderer: Messages container not found');
            return;
        }

        this._attachEmptyStateListeners();
        this._setupDelegatedEventListeners();

        // Listen for live upload progress updates
        eventBus.on(EVENTS.MESSAGE_UPLOAD_PROGRESS, (data) => {
            if (data?.tempId) {
                this._updateUploadProgress(data.tempId, data.progress);
            }
        });

        this._log('RENDERER_INITIALIZED');
    }

    /**
     * Set up container-level delegated event listeners for resilient control handling
     */
    _setupDelegatedEventListeners() {
        if (!this.container || this._delegatedListenersAttached) return;
        this._delegatedListenersAttached = true;

        this.container.addEventListener('click', (e) => {
            // Speed button handler delegation
            const speedBtn = e.target.closest('.vn-speed-btn');
            if (speedBtn) {
                e.preventDefault();
                e.stopPropagation();
                const bubble = speedBtn.closest('.voice-note-bubble');
                const audio = bubble?.querySelector('.vn-audio-el');
                const cur = parseFloat(speedBtn.dataset.speed || '1');
                const next = cur === 1 ? 1.5 : (cur === 1.5 ? 2 : 1);
                speedBtn.dataset.speed = String(next);
                speedBtn.textContent = `${next}x`;
                if (audio) {
                    audio.defaultPlaybackRate = next;
                    audio.playbackRate = next;
                }
                return;
            }

            // Play button handler delegation
            const playBtn = e.target.closest('.vn-play-btn');
            if (playBtn) {
                e.preventDefault();
                e.stopPropagation();
                const bubble = playBtn.closest('.voice-note-bubble');
                const audio = bubble?.querySelector('.vn-audio-el');
                const playIcon = bubble?.querySelector('.vn-play-icon');
                if (!audio) return;

                if (audio.paused) {
                    document.querySelectorAll('.vn-audio-el, .track-audio-el').forEach(other => {
                        if (other !== audio && !other.paused) {
                            other.pause();
                            other.currentTime = 0;
                            const otherBubble = other.closest('.voice-note-bubble, .audio-track-bubble');
                            otherBubble?.querySelector('.vn-play-icon, .track-play-icon')?.classList.replace('bi-pause-fill', 'bi-play-fill');
                            otherBubble?.querySelectorAll('.vn-bar')?.forEach(b => b.classList.remove('is-played'));
                        }
                    });

                    const currentSpeed = parseFloat(bubble?.querySelector('.vn-speed-btn')?.dataset.speed || '1');
                    audio.defaultPlaybackRate = currentSpeed;
                    audio.playbackRate = currentSpeed;

                    audio.play().then(() => {
                        playIcon?.classList.replace('bi-play-fill', 'bi-pause-fill');
                    }).catch(err => console.warn('[VOICE_NOTE] Delegated play blocked:', err));
                } else {
                    audio.pause();
                    playIcon?.classList.replace('bi-pause-fill', 'bi-play-fill');
                }
                return;
            }

            // Waveform scrubber delegation
            const waveform = e.target.closest('.vn-waveform');
            if (waveform) {
                e.preventDefault();
                e.stopPropagation();
                const bubble = waveform.closest('.voice-note-bubble');
                const audio = bubble?.querySelector('.vn-audio-el');
                if (!audio || !audio.duration) return;

                const rect = waveform.getBoundingClientRect();
                const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                audio.currentTime = ratio * audio.duration;
                return;
            }

            // Media on-demand download button delegation
            const dlBtn = e.target.closest('.media-download-pill, .media-download-overlay');
            if (dlBtn) {
                e.preventDefault();
                e.stopPropagation();
                const bubble = dlBtn.closest('.media-bubble');
                const messageId = dlBtn.getAttribute('data-message-id') || bubble?.getAttribute('data-message-id');
                if (messageId && bubble) {
                    this._handleMediaDownload(messageId, bubble);
                }
                return;
            }
        });
    }

    /**
     * Check if media is downloaded locally
     */
    _isMediaDownloaded(messageId) {
        if (!messageId) return true;
        if (this.downloadedMediaIds.has(String(messageId))) return true;
        if (deviceMediaStore.hasMedia(messageId)) return true;
        try {
            return localStorage.getItem(`media_dl_${messageId}`) === 'true';
        } catch (_) {
            return false;
        }
    }

    /**
     * Update live upload progress in DOM
     */
    _updateUploadProgress(tempId, progress) {
        if (!this.container) return;
        const msgEl = this.container.querySelector(`[data-message-id="${tempId}"]`);
        if (!msgEl) return;
        const overlay = msgEl.querySelector('.media-upload-overlay');
        if (!overlay) return;
        const circleBar = overlay.querySelector('.upload-circle-bar');
        const textEl = overlay.querySelector('.upload-progress-text');
        if (circleBar) {
            const circumference = 94.25;
            const offset = Math.max(0, circumference * (1 - progress / 100));
            circleBar.style.strokeDashoffset = offset.toFixed(1);
        }
        if (textEl) {
            textEl.textContent = `${progress}%`;
        }
        if (progress >= 100) {
            overlay.classList.add('upload-complete');
        }
    }

    /**
     * Handle on-demand download for received media
     */
    async _handleMediaDownload(messageId, bubble) {
        if (!bubble || bubble.dataset.isDownloading === 'true') return;
        bubble.dataset.isDownloading = 'true';

        const pill = bubble.querySelector('.media-download-pill');
        const dlIcon = pill?.querySelector('.dl-icon');
        const spinner = pill?.querySelector('.download-spinner');
        const sizeText = pill?.querySelector('.media-download-size');

        if (dlIcon) dlIcon.classList.add('d-none');
        if (spinner) spinner.classList.remove('d-none');
        if (sizeText) sizeText.textContent = 'Saving...';

        try {
            const imgs = Array.from(bubble.querySelectorAll('img'));
            const vids = Array.from(bubble.querySelectorAll('video'));
            const mediaEls = [...imgs, ...vids];

            // Save all media elements permanently to device storage
            for (const el of mediaEls) {
                const src = el.getAttribute('src');
                if (src && !src.startsWith('blob:') && !src.startsWith('capacitor:') && !src.startsWith('http://localhost/_capacitor_file_')) {
                    const filename = src.split('/').pop()?.split('?')[0] || `media_${messageId}`;
                    const localUrl = await deviceMediaStore.downloadMedia(messageId, src, filename);
                    if (localUrl) {
                        el.src = localUrl;
                    }
                }
            }

            // Mark as downloaded locally
            this.downloadedMediaIds.add(String(messageId));
            try {
                localStorage.setItem(`media_dl_${messageId}`, 'true');
            } catch (_) {}

            // Smooth reveal
            bubble.classList.remove('not-downloaded');
            delete bubble.dataset.isDownloading;

            const overlay = bubble.querySelector('.media-download-overlay');
            if (overlay) {
                overlay.style.opacity = '0';
                setTimeout(() => overlay.remove(), 250);
            }
        } catch (err) {
            console.error('[MEDIA_DOWNLOAD] Failed:', err);
            delete bubble.dataset.isDownloading;
            if (dlIcon) dlIcon.classList.remove('d-none');
            if (spinner) spinner.classList.add('d-none');
            if (sizeText) sizeText.textContent = 'Retry';
        }
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

            if (!messages || messages.length === 0) {
                const storeState = window.__store?.getState?.();
                if (storeState && storeState.isInitialHistoryLoaded === false) {
                    console.log("[RENDERER] Initial history loading in progress, deferring empty state");
                    return;
                }
                this.container.innerHTML = '';
                this._renderEmptyState();
                this.lastRenderedCount = 0;
                return;
            }

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
                } else if (viewType === 'time') {
                    console.log("[RENDERER] Creating time element:", item.label);
                    this.container.appendChild(this._createTimeElement(item.label, item.preciseLabel));
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

            // Add event listeners for retry buttons
            this._attachRetryButtonListeners();

        } finally {
            this.isRendering = false;
        }
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
     * Render empty state if template exists
     */
    _renderEmptyState() {
        const template = document.getElementById('emptyStateTemplate');
        if (template && this.container) {
            const clone = template.content.cloneNode(true);
            this.container.appendChild(clone);
            this._attachEmptyStateListeners();
        }
    }

    /**
     * Attach click listeners to greeting chips
     */
    _attachEmptyStateListeners() {
        if (!this.container) return;
        const chips = this.container.querySelectorAll('.empty-greeting-chip');
        chips.forEach(chip => {
            chip.addEventListener('click', (e) => {
                e.preventDefault();
                const text = chip.getAttribute('data-text') || chip.textContent.trim();
                const input = document.getElementById('messageInput');
                if (input) {
                    input.value = text;
                    input.focus();
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
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

        if (message.type === 'media' || message.type === 'audio' || message.type === 'voice_note' || message.type === 'document') {
            return this._createMediaMessage(message);
        }

        if (message.type === 'media_group' || (message.attachments && message.attachments.length > 1)) {
            return this._createMediaGroupMessage(message);
        }

        if (message.type === 'link') {
        console.log('[RENDERER] Creating link message for:', message.id);
        return this._createLinkMessage(message);
        }
        // Build wrapper containing avatar, bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Add avatar for received messages (only on last/single in group)
        if (!message.isOwn) {
            const shouldShowAvatar = message.groupPosition === 'single' || message.groupPosition === 'last';
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `message-avatar-container ${shouldShowAvatar ? '' : 'hidden'}`;
            
            if (shouldShowAvatar) {
                const avatarUrl = this._getSenderAvatar(message.senderId);
                const avatarImg = document.createElement('img');
                avatarImg.className = 'message-avatar';
                avatarImg.src = avatarUrl;
                avatarImg.alt = 'Avatar';
                avatarContainer.appendChild(avatarImg);
            }
            
            wrapperDiv.appendChild(avatarContainer);
        }

        // Content wrapper for bubble and meta
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

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

        // Render reply quote if present
        let replyHtml = '';
        const replyDetails = message.metadata?.reply_to_details;
        if (replyDetails) {
            const senderName = replyDetails.sender?.username || (replyDetails.senderId === this.currentUserId ? 'You' : 'User');
            const snippet = escapeHtml(replyDetails.content || (replyDetails.type === 'media' ? '[Media]' : 'Message'));
            replyHtml = `
                <div class="message-reply-quote" onclick="document.querySelector('[data-message-id=\\'${replyDetails.id}\\']')?.scrollIntoView({ behavior: 'smooth', block: 'center' })" style="cursor: pointer; padding: 4px 8px; margin-bottom: 6px; border-left: 3px solid var(--brand); background: rgba(0,0,0,0.06); border-radius: 4px; font-size: 0.8rem;">
                    <div class="fw-bold" style="color: var(--brand); font-size: 0.75rem;">${escapeHtml(senderName)}</div>
                    <div class="text-truncate text-muted" style="max-width: 260px;">${snippet}</div>
                </div>
            `;
        }

        // Render edited tag if edited
        let editedHtml = '';
        if (message.metadata?.edited_at) {
            editedHtml = `<span class="edited-tag text-muted ms-1" style="font-size: 0.72rem; font-style: italic;">(edited)</span>`;
        }

        // Render reactions if present
        let reactionsHtml = '';
        const reactions = message.metadata?.reactions;
        if (reactions && Array.isArray(reactions) && reactions.length > 0) {
            const counts = {};
            reactions.forEach(r => {
                const em = r.emoji || (typeof r === 'string' ? r : null);
                if (em) counts[em] = (counts[em] || 0) + (r.count || 1);
            });
            const badges = Object.entries(counts).map(([em, cnt]) => `
                <span class="reaction-badge badge bg-light text-dark border rounded-pill px-2 py-1 me-1 shadow-sm" style="font-size: 0.75rem;">
                    ${em} ${cnt > 1 ? cnt : ''}
                </span>
            `).join('');
            reactionsHtml = `
                <div class="message-reactions-container d-flex flex-wrap mt-1">
                    ${badges}
                </div>
            `;
        }

        // Bubble content
        messageDiv.innerHTML = `
            ${replyHtml}
            <p class="message-content">${escapeHtml(message.content || '')}${editedHtml}</p>
            ${reactionsHtml}
        `;

        // Render link preview if available
        if (message.link_preview && message.link_preview.url) {
            console.log("[LINK_PREVIEW] Rendering preview for message:", message.id);
            const previewCard = linkPreviewRenderer.render(message.link_preview);
            if (previewCard) {
                messageDiv.appendChild(previewCard);
                messageDiv.classList.add('link-message');
            }
        }

        contentWrapper.appendChild(messageDiv);

        // Always render meta (timestamp + receipt) on all messages
        const metaDiv = document.createElement('div');
        metaDiv.className = 'message-meta d-flex align-items-center justify-content-end';
        metaDiv.style.gap = '4px';

        const timeSpan = document.createElement('span');
        timeSpan.className = 'timestamp';
        timeSpan.textContent = formatTime(message.timestamp);
        metaDiv.appendChild(timeSpan);

        // WhatsApp-style status checkmarks for all sent messages
        if (message.isOwn) {
            const receiptSpan = document.createElement('span');
            receiptSpan.className = `message-read-receipt status-${status}`;
            receiptSpan.innerHTML = this._getStatusIcon(status, message.id, null, message);
            metaDiv.appendChild(receiptSpan);
        }

        contentWrapper.appendChild(metaDiv);

        wrapperDiv.appendChild(contentWrapper);
        return wrapperDiv;
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

    /**
     * Create emoji message element (pure DOM creation)
     * @param {Object} message - Emoji message object
     * @returns {HTMLElement} Emoji message element
     */
    _createEmojiMessage(message) {
        // Build wrapper containing avatar, emoji and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Add avatar for received messages (only on last/single in group)
        if (!message.isOwn) {
            const shouldShowAvatar = message.groupPosition === 'single' || message.groupPosition === 'last';
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `message-avatar-container ${shouldShowAvatar ? '' : 'hidden'}`;
            
            if (shouldShowAvatar) {
                const avatarUrl = this._getSenderAvatar(message.senderId);
                const avatarImg = document.createElement('img');
                avatarImg.className = 'message-avatar';
                avatarImg.src = avatarUrl;
                avatarImg.alt = 'Avatar';
                avatarContainer.appendChild(avatarImg);
            }
            
            wrapperDiv.appendChild(avatarContainer);
        }

        // Content wrapper for emoji and meta
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

        // Create emoji element (no bubble styling)
        const emojiDiv = document.createElement('div');
        emojiDiv.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} emoji-message group-${message.groupPosition}`;
        emojiDiv.setAttribute('data-message-id', message.id);
        emojiDiv.setAttribute('data-sender-id', message.senderId);
        emojiDiv.setAttribute('data-status', message.status);
        emojiDiv.setAttribute('data-group-position', message.groupPosition);
        
        emojiDiv.innerHTML = `<div class="emoji-content">${escapeHtml(message.content || '')}</div>`;

        contentWrapper.appendChild(emojiDiv);

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

            contentWrapper.appendChild(metaDiv);
        }

        wrapperDiv.appendChild(contentWrapper);
        return wrapperDiv;
    }

    /**
     * Render single media bubble (Telegram-style)
     * Media itself becomes the bubble - NOT reusing text bubbles
     * @param {Object} message - Media message object
     * @returns {HTMLElement} Single media bubble element
     */
    renderSingleMediaBubble(message) {
        console.log('[MEDIA_BUBBLE] Rendering single media bubble for:', message.id);

        const metadata = message.metadata || {};
        const attachmentType = metadata.type || 'image';
        const mediaUrl = metadata.url || '';
        const caption = message.content || '';
        const isUploading = message.status === 'uploading' || message.status === 'sending' || message.isOptimistic;
        const isNotDownloaded = !message.isOwn && !isUploading && !this._isMediaDownloaded(message.id);

        const bubble = document.createElement('div');
        bubble.className = `media-bubble single-media ${message.isOwn ? 'sent' : 'received'} group-${message.groupPosition}`;
        if (isNotDownloaded) {
            bubble.classList.add('not-downloaded');
        }
        bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sender-id', message.senderId);
        bubble.setAttribute('data-status', message.status);
        bubble.setAttribute('data-group-position', message.groupPosition);

        let mediaContent = '';

        if (attachmentType === 'image' && mediaUrl) {
            mediaContent = `<img src="${escapeHtml(mediaUrl)}" alt="Image" loading="lazy">`;
        } else if (attachmentType === 'video' && mediaUrl) {
            mediaContent = `
                <div class="video-play-overlay">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                        <polygon points="5,3 19,12 5,21"></polygon>
                    </svg>
                </div>
                <video src="${escapeHtml(mediaUrl)}" muted preload="metadata" playsinline tabindex="-1" style="pointer-events: none;"></video>
            `;
        }

        bubble.innerHTML = mediaContent;

        // Asynchronously check and use locally stored device media if available
        if (!isNotDownloaded && !isUploading) {
            deviceMediaStore.getLocalMediaUrl(message.id).then(localUrl => {
                if (localUrl) {
                    const el = bubble.querySelector('img, video');
                    if (el && el.src !== localUrl) {
                        el.src = localUrl;
                    }
                }
            }).catch(() => {});
        }

        // 1. Sender optimistic upload progress overlay
        if (isUploading) {
            const initialProgress = metadata.uploadProgress || 0;
            const circumference = 94.25;
            const initialOffset = Math.max(0, circumference * (1 - initialProgress / 100)).toFixed(1);
            const uploadOverlay = document.createElement('div');
            uploadOverlay.className = 'media-upload-overlay';
            uploadOverlay.setAttribute('data-upload-id', message.id);
            uploadOverlay.innerHTML = `
                <div class="upload-progress-widget">
                    <svg class="upload-progress-circle" width="44" height="44" viewBox="0 0 38 38">
                        <circle class="upload-circle-bg" cx="19" cy="19" r="15" stroke="rgba(255,255,255,0.25)" stroke-width="2.5" fill="none"/>
                        <circle class="upload-circle-bar" cx="19" cy="19" r="15" stroke="#ffffff" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-dasharray="94.25" stroke-dashoffset="${initialOffset}"/>
                    </svg>
                    <span class="upload-progress-text">${initialProgress}%</span>
                </div>
            `;
            bubble.appendChild(uploadOverlay);
        }

        // 2. Receiver on-demand download overlay with actual file size
        if (isNotDownloaded) {
            const fileSize = this._formatFileSize(metadata.size || 0);
            const downloadOverlay = document.createElement('div');
            downloadOverlay.className = 'media-download-overlay';
            downloadOverlay.setAttribute('data-message-id', message.id);
            downloadOverlay.innerHTML = `
                <button type="button" class="media-download-pill" title="Download media">
                    <div class="download-icon-wrap">
                        <svg class="dl-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <svg class="download-spinner d-none" width="20" height="20" viewBox="0 0 38 38">
                            <circle cx="19" cy="19" r="15" stroke="rgba(255,255,255,0.3)" stroke-width="3" fill="none"/>
                            <circle class="dl-spinner-bar" cx="19" cy="19" r="15" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-dasharray="94.25" stroke-dashoffset="60"/>
                        </svg>
                    </div>
                    <span class="media-download-size">${fileSize || 'Download'}</span>
                </button>
            `;
            bubble.appendChild(downloadOverlay);
        }

        // Add caption if present (inside the bubble)
        if (caption && caption.trim()) {
            const captionDiv = document.createElement('div');
            captionDiv.className = 'media-caption';
            captionDiv.textContent = caption;
            bubble.appendChild(captionDiv);
        }

        // Click handler: if not downloaded, trigger download; if downloaded, open fullscreen viewer
        bubble.addEventListener('click', (e) => {
            if (bubble.classList.contains('not-downloaded')) {
                e.stopPropagation();
                this._handleMediaDownload(message.id, bubble);
                return;
            }
            if (isUploading) return;
            console.log('[MEDIA_VIEWER] Opening attachment:', message.id);
            this.renderFullscreenMediaViewer([{
                id: message.id,
                type: attachmentType,
                url: mediaUrl,
                caption: caption
            }], 0);
        });

        console.log('[MEDIA_BUBBLE] Single media bubble created');
        return bubble;
    }

    /**
     * Render media group bubble (Telegram-style)
     * Dedicated media group bubble - NOT reusing text bubbles
     * @param {Object} message - Media group message object
     * @returns {HTMLElement} Media group bubble element
     */
    renderMediaGroupBubble(message) {
        console.log('[MEDIA_GROUP] Rendering media group bubble for:', message.id);

        const attachments = message.attachments || message.metadata?.attachments || [];
        const globalCaption = message.global_caption || message.metadata?.global_caption || '';
        const attachmentCount = attachments.length;
        const isUploading = message.status === 'uploading' || message.status === 'sending' || message.isOptimistic;
        const isNotDownloaded = !message.isOwn && !isUploading && !this._isMediaDownloaded(message.id);

        const bubble = document.createElement('div');
        bubble.className = `media-bubble media-group ${message.isOwn ? 'sent' : 'received'} group-${message.groupPosition}`;
        if (isNotDownloaded) {
            bubble.classList.add('not-downloaded');
        }
        bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sender-id', message.senderId);
        bubble.setAttribute('data-status', message.status);
        bubble.setAttribute('data-group-position', message.groupPosition);

        // Create media content grid
        const contentDiv = document.createElement('div');
        contentDiv.className = `media-content ${this._getTelegramLayoutClass(attachmentCount)}`;

        // Determine visible attachments (max 4 for chat view)
        const visibleLimit = 4;
        const visibleAttachments = attachments.slice(0, visibleLimit);
        const hiddenCount = attachmentCount - visibleLimit;

        // Render each media tile
        visibleAttachments.forEach((attachment, index) => {
            const tile = this._renderMediaTile(attachment, index, attachmentCount, hiddenCount);
            contentDiv.appendChild(tile);
        });

        bubble.appendChild(contentDiv);

        // 1. Sender optimistic upload progress overlay
        if (isUploading) {
            const initialProgress = message.metadata?.uploadProgress || 0;
            const circumference = 94.25;
            const initialOffset = Math.max(0, circumference * (1 - initialProgress / 100)).toFixed(1);
            const uploadOverlay = document.createElement('div');
            uploadOverlay.className = 'media-upload-overlay group-upload-overlay';
            uploadOverlay.setAttribute('data-upload-id', message.id);
            uploadOverlay.innerHTML = `
                <div class="upload-progress-widget">
                    <svg class="upload-progress-circle" width="48" height="48" viewBox="0 0 38 38">
                        <circle class="upload-circle-bg" cx="19" cy="19" r="15" stroke="rgba(255,255,255,0.25)" stroke-width="2.5" fill="none"/>
                        <circle class="upload-circle-bar" cx="19" cy="19" r="15" stroke="#ffffff" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-dasharray="94.25" stroke-dashoffset="${initialOffset}"/>
                    </svg>
                    <span class="upload-progress-text">${initialProgress}%</span>
                </div>
            `;
            bubble.appendChild(uploadOverlay);
        }

        // 2. Receiver bundle download overlay with combined bundle size
        if (isNotDownloaded) {
            const bundleSize = attachments.reduce((acc, att) => acc + (att.size || 0), 0);
            const formattedBundleSize = this._formatFileSize(bundleSize);
            const downloadOverlay = document.createElement('div');
            downloadOverlay.className = 'media-download-overlay group-download-overlay';
            downloadOverlay.setAttribute('data-message-id', message.id);
            downloadOverlay.innerHTML = `
                <button type="button" class="media-download-pill group-download-pill" title="Download bundle">
                    <div class="download-icon-wrap">
                        <svg class="dl-icon" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <svg class="download-spinner d-none" width="22" height="22" viewBox="0 0 38 38">
                            <circle cx="19" cy="19" r="15" stroke="rgba(255,255,255,0.3)" stroke-width="3" fill="none"/>
                            <circle class="dl-spinner-bar" cx="19" cy="19" r="15" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-dasharray="94.25" stroke-dashoffset="60"/>
                        </svg>
                    </div>
                    <div class="group-dl-text">
                        <span class="group-dl-label">Download all</span>
                        <span class="media-download-size">${formattedBundleSize || ''}</span>
                    </div>
                </button>
            `;
            bubble.appendChild(downloadOverlay);
        }

        // Add global caption if present (inside the bubble)
        if (globalCaption && globalCaption.trim()) {
            const captionDiv = document.createElement('div');
            captionDiv.className = 'media-caption';
            captionDiv.textContent = globalCaption;
            bubble.appendChild(captionDiv);
        }

        // Click handler: if not downloaded, trigger download; if downloaded, open fullscreen viewer
        bubble.addEventListener('click', (e) => {
            if (bubble.classList.contains('not-downloaded')) {
                e.stopPropagation();
                this._handleMediaDownload(message.id, bubble);
                return;
            }
            if (isUploading) return;
            const clickedTile = e.target.closest('.media-tile');
            let startIndex = 0;
            if (clickedTile) {
                const tiles = Array.from(bubble.querySelectorAll('.media-tile'));
                const idx = tiles.indexOf(clickedTile);
                if (idx !== -1) startIndex = idx;
            }
            console.log('[MEDIA_VIEWER] Opening media group:', message.id, 'startIndex:', startIndex);
            this.renderFullscreenMediaViewer(attachments, startIndex);
        });

        console.log('[MEDIA_GROUP] Media group bubble created');
        return bubble;
    }

    /**
     * Render media tile for group
     * @param {Object} attachment - Attachment object
     * @param {number} index - Attachment index
     * @param {number} total - Total attachments
     * @param {number} hiddenCount - Number of hidden attachments
     * @returns {HTMLElement} Media tile element
     */
    _renderMediaTile(attachment, index, total, hiddenCount) {
        console.log('[MEDIA_TILE] Rendering tile', index, 'of', total);

        const tile = document.createElement('div');
        tile.className = 'media-tile';

        const fileType = attachment.file_type || attachment.type || 'image';
        const fileUrl = attachment.file_url || attachment.file || attachment.url || '';
        const caption = attachment.caption || '';

        // Add video class if applicable
        if (fileType === 'video') {
            tile.classList.add('video-tile');
        }

        let tileContent = '';

        switch (fileType) {
            case 'image':
                tileContent = `<img src="${escapeHtml(fileUrl)}" alt="Image" loading="lazy">`;
                break;
            case 'video':
                tileContent = `
                    <div class="tile-play-icon">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <polygon points="5,3 19,12 5,21"></polygon>
                        </svg>
                    </div>
                    <video src="${escapeHtml(fileUrl)}" muted preload="metadata" playsinline tabindex="-1" style="pointer-events: none;"></video>
                `;
                break;
            default:
                tileContent = `<div class="tile-placeholder">${fileType.toUpperCase()}</div>`;
        }

        tile.innerHTML = tileContent;

        // Add overlay count for last visible tile if there are hidden items
        if (hiddenCount > 0 && index === 3) {
            console.log('[MEDIA_OVERLAY] Adding overlay count:', hiddenCount);
            const overlay = document.createElement('div');
            overlay.className = 'media-overlay';
            overlay.textContent = `+${hiddenCount}`;
            tile.appendChild(overlay);
        }

        return tile;
    }

    /**
     * Get Telegram-style layout class based on attachment count
     * @param {number} count - Number of attachments
     * @returns {string} Layout class
     */
    _getTelegramLayoutClass(count) {
        if (count === 1) return 'media-group--1';
        if (count === 2) return 'media-group--2';
        if (count === 3) return 'media-group--3';
        if (count === 4) return 'media-group--4';
        return 'media-group--many';
    }

    /**
     * Render fullscreen immersive media viewer
     * @param {Array} attachments - Array of attachment objects
     * @param {number} startIndex - Index of attachment to show first
     */
    renderFullscreenMediaViewer(attachments, startIndex = 0) {
        console.log('[MEDIA_VIEWER] Opening fullscreen viewer');
        console.log('[MEDIA_VIEWER] Total attachments:', attachments.length);
        console.log('[MEDIA_VIEWER] Starting at index:', startIndex);

        // Remove existing viewer if present
        const existingViewer = document.querySelector('.media-viewer-overlay');
        if (existingViewer) {
            existingViewer.remove();
        }

        // Create viewer overlay
        const overlay = document.createElement('div');
        overlay.className = 'media-viewer-overlay';

        // Create viewer container
        const container = document.createElement('div');
        container.className = 'media-viewer-container';

        let currentIndex = startIndex;

        // Create header with download and close button
        const header = document.createElement('div');
        header.className = 'media-viewer-header';

        const downloadButton = document.createElement('button');
        downloadButton.className = 'media-viewer-btn media-viewer-download';
        downloadButton.title = 'Save to device / Download';
        downloadButton.innerHTML = `
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
        `;
        downloadButton.addEventListener('click', (e) => {
            e.stopPropagation();
            const currentItem = attachments[currentIndex];
            if (currentItem) {
                const url = currentItem.file_url || currentItem.file || currentItem.url || '';
                const filename = currentItem.filename || currentItem.name || url.split('/').pop()?.split('?')[0] || `media_${Date.now()}`;
                deviceMediaStore.downloadToDevice(url, filename);
            }
        });

        const closeButton = document.createElement('button');
        closeButton.className = 'media-viewer-close';
        closeButton.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
        closeButton.addEventListener('click', () => {
            overlay.classList.remove('show');
            setTimeout(() => overlay.remove(), 300);
        });

        header.appendChild(downloadButton);
        header.appendChild(closeButton);

        // Create main content area
        const main = document.createElement('div');
        main.className = 'media-viewer-main';

        // Create navigation buttons
        const prevButton = document.createElement('button');
        prevButton.className = 'media-viewer-nav prev';
        prevButton.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15,18 9,12 15,6"></polyline>
            </svg>
        `;

        const nextButton = document.createElement('button');
        nextButton.className = 'media-viewer-nav next';
        nextButton.innerHTML = `
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9,18 15,12 9,6"></polyline>
            </svg>
        `;

        // Create content element
        const content = document.createElement('div');
        content.className = 'media-viewer-content';

        // Create footer with counter and caption
        const footer = document.createElement('div');
        footer.className = 'media-viewer-footer';

        const counter = document.createElement('div');
        counter.className = 'media-viewer-counter';
        counter.textContent = `${startIndex + 1} / ${attachments.length}`;

        const caption = document.createElement('div');
        caption.className = 'media-viewer-caption';
        caption.textContent = attachments[startIndex]?.caption || '';

        footer.appendChild(counter);
        footer.appendChild(caption);

        // Assemble viewer
        main.appendChild(prevButton);
        main.appendChild(content);
        main.appendChild(nextButton);
        container.appendChild(header);
        container.appendChild(main);
        container.appendChild(footer);
        overlay.appendChild(container);

        // Add to DOM
        document.body.appendChild(overlay);

        // Trigger animation
        requestAnimationFrame(() => {
            overlay.classList.add('show');
        });

        // Current index state
        currentIndex = startIndex;

        // Function to render current attachment
        const renderAttachment = (index) => {
            console.log('[MEDIA_VIEWER] Rendering attachment at index:', index);
            const attachment = attachments[index];
            if (!attachment) return;

            const fileType = attachment.file_type || attachment.type || 'image';
            const fileUrl = attachment.file_url || attachment.url || '';

            if (fileType === 'video') {
                content.innerHTML = `
                    <video class="media-viewer-video" controls autoplay>
                        <source src="${escapeHtml(fileUrl)}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                `;
            } else {
                content.innerHTML = `<img src="${escapeHtml(fileUrl)}" alt="Media" class="media-viewer-content">`;
            }

            // Update counter and caption
            counter.textContent = `${index + 1} / ${attachments.length}`;
            caption.textContent = attachment.caption || '';

            // Update navigation buttons visibility
            prevButton.style.display = index > 0 ? 'flex' : 'none';
            nextButton.style.display = index < attachments.length - 1 ? 'flex' : 'none';
        };

        // Navigation handlers
        prevButton.addEventListener('click', () => {
            if (currentIndex > 0) {
                currentIndex--;
                renderAttachment(currentIndex);
            }
        });

        nextButton.addEventListener('click', () => {
            if (currentIndex < attachments.length - 1) {
                currentIndex++;
                renderAttachment(currentIndex);
            }
        });

        // Keyboard navigation
        const handleKeydown = (e) => {
            if (e.key === 'Escape') {
                overlay.classList.remove('show');
                setTimeout(() => overlay.remove(), 300);
                document.removeEventListener('keydown', handleKeydown);
            } else if (e.key === 'ArrowLeft' && currentIndex > 0) {
                currentIndex--;
                renderAttachment(currentIndex);
            } else if (e.key === 'ArrowRight' && currentIndex < attachments.length - 1) {
                currentIndex++;
                renderAttachment(currentIndex);
            }
        };

        document.addEventListener('keydown', handleKeydown);

        // Initial render
        renderAttachment(currentIndex);

        console.log('[MEDIA_VIEWER] Fullscreen viewer opened successfully');
    }

    /**
     * Create media group message element (pure DOM creation)
     * @param {Object} message - Media group message object
     * @returns {HTMLElement} Media group message element
     */
    _createMediaGroupMessage(message) {
        console.log('[RENDERER] [MEDIA_GROUP] Creating media group message for:', message.id);
        console.log('[RENDERER] [MEDIA_GROUP] [DEBUG] FULL MESSAGE:', JSON.stringify(message, null, 2));
        console.log('[RENDERER] [MEDIA_GROUP] [DEBUG] ATTACHMENTS (top-level):', message.attachments);
        console.log('[RENDERER] [MEDIA_GROUP] [DEBUG] METADATA:', message.metadata);
        console.log('[RENDERER] [MEDIA_GROUP] [DEBUG] METADATA ATTACHMENTS:', message.metadata?.attachments);

        // Build wrapper containing avatar, bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Add avatar for received messages (only on last/single in group)
        if (!message.isOwn) {
            const shouldShowAvatar = message.groupPosition === 'single' || message.groupPosition === 'last';
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `message-avatar-container ${shouldShowAvatar ? '' : 'hidden'}`;

            if (shouldShowAvatar) {
                const avatarUrl = this._getSenderAvatar(message.senderId);
                const avatarImg = document.createElement('img');
                avatarImg.className = 'message-avatar';
                avatarImg.src = avatarUrl;
                avatarImg.alt = 'Avatar';
                avatarContainer.appendChild(avatarImg);
            }

            wrapperDiv.appendChild(avatarContainer);
        }

        // Content wrapper for media grid and meta
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

        // Use new Telegram-style media group bubble
        const mediaBubble = this.renderMediaGroupBubble(message);
        contentWrapper.appendChild(mediaBubble);

        console.log('[RENDERER] [MEDIA_GROUP] Message bubble created with Telegram-style architecture');

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

            contentWrapper.appendChild(metaDiv);
        }

        wrapperDiv.appendChild(contentWrapper);
        return wrapperDiv;
    }

    /**
     * Create media message element (pure DOM creation)
     * @param {Object} message - Media message object
     * @returns {HTMLElement} Media message element
     */
    _createMediaMessage(message) {
        console.log('[RENDERER] [MEDIA] Creating media message for:', message.id);

        const metadata = message.metadata || {};
        const attachmentType = metadata.type || 'file';
        const isImageOrVideo = attachmentType === 'image' || attachmentType === 'video';

        // Build wrapper containing avatar, bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Add avatar for received messages (only on last/single in group)
        if (!message.isOwn) {
            const shouldShowAvatar = message.groupPosition === 'single' || message.groupPosition === 'last';
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `message-avatar-container ${shouldShowAvatar ? '' : 'hidden'}`;

            if (shouldShowAvatar) {
                const avatarUrl = this._getSenderAvatar(message.senderId);
                const avatarImg = document.createElement('img');
                avatarImg.className = 'message-avatar';
                avatarImg.src = avatarUrl;
                avatarImg.alt = 'Avatar';
                avatarContainer.appendChild(avatarImg);
            }

            wrapperDiv.appendChild(avatarContainer);
        }

        // Content wrapper for media and meta
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

        // For images/videos, use new Telegram-style single media bubble
        // For other types, use traditional bubble
        if (isImageOrVideo && metadata.url) {
            console.log('[RENDERER] [MEDIA] Using Telegram-style single media bubble');
            const mediaBubble = this.renderSingleMediaBubble(message);
            contentWrapper.appendChild(mediaBubble);
        } else if (metadata.is_voice_note || attachmentType === 'voice_note' || message.is_voice_note) {
            console.log('[RENDERER] [VOICE_NOTE] Using Voice Note bubble with waveform');
            const voiceBubble = this.renderVoiceNoteBubble(message, metadata);
            contentWrapper.appendChild(voiceBubble);
        } else if (attachmentType === 'audio') {
            console.log('[RENDERER] [AUDIO] Using Audio Track bubble');
            const audioBubble = this.renderAudioTrackBubble(message, metadata);
            contentWrapper.appendChild(audioBubble);
        } else {
            console.log('[RENDERER] [DOC] Using Document card bubble');
            const docBubble = this.renderDocumentBubble(message, metadata);
            contentWrapper.appendChild(docBubble);
        }

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

            contentWrapper.appendChild(metaDiv);
        }

        wrapperDiv.appendChild(contentWrapper);
        return wrapperDiv;
    }

    /**
     * Render distinct document card bubble
     */
    renderDocumentBubble(message, metadata = {}) {
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} document-bubble group-${message.groupPosition}`;
        bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sender-id', message.senderId);
        bubble.setAttribute('data-status', message.status);
        bubble.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(bubble);

        const fileUrl = metadata.url || '';
        const rawName = metadata.file_name || message.content || 'Document';
        const fileName = rawName.split('/').pop().split('\\').pop();
        const ext = (fileName.split('.').pop() || 'doc').toLowerCase();
        const fileSizeFormatted = this._formatFileSize(metadata.size);
        const docStyles = this._getDocumentTypeInfo(ext);

        bubble.innerHTML = `
            <div class="document-card-inner">
                <div class="document-badge ${docStyles.badgeClass}">
                    <i class="bi ${docStyles.icon}"></i>
                    <span class="document-ext-pill">${ext.toUpperCase().slice(0, 4)}</span>
                </div>
                <div class="document-details">
                    <div class="document-filename" title="${escapeHtml(fileName)}">${escapeHtml(fileName)}</div>
                    <div class="document-meta-row">
                        ${fileSizeFormatted ? `<span class="document-size-label">${fileSizeFormatted}</span><span class="document-dot">•</span>` : ''}
                        <span class="document-type-label">${docStyles.label}</span>
                    </div>
                </div>
                <a href="${escapeHtml(fileUrl)}" download="${escapeHtml(fileName)}" target="_blank" rel="noopener" class="document-download-btn" title="Download ${escapeHtml(fileName)}" aria-label="Download">
                    <i class="bi bi-arrow-down"></i>
                </a>
            </div>
        `;

        return bubble;
    }

    /**
     * Render distinct voice note bubble with interactive waveform and speed toggle
     */
    renderVoiceNoteBubble(message, metadata = {}) {
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} voice-note-bubble group-${message.groupPosition}`;
        bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sender-id', message.senderId);
        bubble.setAttribute('data-status', message.status);
        bubble.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(bubble);

        const audioUrl = metadata.url || '';

        // Generate 26 balanced waveform bars
        const barHeights = [25, 45, 70, 50, 85, 60, 95, 75, 40, 70, 90, 35, 55, 80, 100, 65, 45, 85, 60, 75, 40, 65, 50, 80, 55, 30];
        const barsHtml = barHeights.map((h, i) => `<span class="vn-bar" data-idx="${i}" style="height: ${h}%;"></span>`).join('');

        bubble.innerHTML = `
            <div class="voice-note-inner">
                <button type="button" class="vn-play-btn" aria-label="Play voice note">
                    <i class="bi bi-play-fill vn-play-icon"></i>
                </button>
                <div class="vn-content">
                    <div class="vn-waveform" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                        ${barsHtml}
                    </div>
                    <div class="vn-meta-row">
                        <span class="vn-timer">0:00</span>
                        <span class="vn-dot">•</span>
                        <span class="vn-mic-indicator"><i class="bi bi-mic-fill"></i> Voice Note</span>
                    </div>
                </div>
                <button type="button" class="vn-speed-btn" title="Playback speed" data-speed="1">1x</button>
                <audio src="${escapeHtml(audioUrl)}" preload="metadata" class="d-none vn-audio-el"></audio>
            </div>
        `;

        this._bindVoiceNoteEvents(bubble);
        return bubble;
    }

    /**
     * Bind interactive voice note events (play/pause, seek, 1x/1.5x/2x speed)
     */
    _bindVoiceNoteEvents(bubble) {
        const playBtn = bubble.querySelector('.vn-play-btn');
        const playIcon = bubble.querySelector('.vn-play-icon');
        const audio = bubble.querySelector('.vn-audio-el');
        const timer = bubble.querySelector('.vn-timer');
        const speedBtn = bubble.querySelector('.vn-speed-btn');
        const waveform = bubble.querySelector('.vn-waveform');
        const bars = bubble.querySelectorAll('.vn-bar');

        if (!playBtn || !audio) return;

        playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (audio.paused) {
                // Pause all other playing audio on the page
                document.querySelectorAll('.vn-audio-el, .track-audio-el').forEach(other => {
                    if (other !== audio && !other.paused) {
                        other.pause();
                        other.currentTime = 0;
                        const otherBubble = other.closest('.voice-note-bubble, .audio-track-bubble');
                        otherBubble?.querySelector('.vn-play-icon, .track-play-icon')?.classList.replace('bi-pause-fill', 'bi-play-fill');
                        otherBubble?.querySelectorAll('.vn-bar')?.forEach(b => b.classList.remove('is-played'));
                    }
                });

                const currentSpeed = parseFloat(speedBtn?.dataset.speed || '1');
                audio.defaultPlaybackRate = currentSpeed;
                audio.playbackRate = currentSpeed;

                audio.play().then(() => {
                    playIcon.classList.replace('bi-play-fill', 'bi-pause-fill');
                }).catch(err => console.warn('[VOICE_NOTE] Play blocked:', err));
            } else {
                audio.pause();
                playIcon.classList.replace('bi-pause-fill', 'bi-play-fill');
            }
        });

        audio.addEventListener('play', () => {
            const currentSpeed = parseFloat(speedBtn?.dataset.speed || '1');
            audio.defaultPlaybackRate = currentSpeed;
            audio.playbackRate = currentSpeed;
        });

        audio.addEventListener('playing', () => {
            const currentSpeed = parseFloat(speedBtn?.dataset.speed || '1');
            audio.defaultPlaybackRate = currentSpeed;
            audio.playbackRate = currentSpeed;
        });

        audio.addEventListener('timeupdate', () => {
            if (timer) timer.textContent = this._formatAudioDuration(audio.currentTime);
            const duration = audio.duration || 1;
            const pct = audio.currentTime / duration;
            const activeCount = Math.floor(pct * bars.length);
            bars.forEach((bar, idx) => {
                if (idx <= activeCount) {
                    bar.classList.add('is-played');
                } else {
                    bar.classList.remove('is-played');
                }
            });
        });

        audio.addEventListener('ended', () => {
            playIcon.classList.replace('bi-pause-fill', 'bi-play-fill');
            bars.forEach(b => b.classList.remove('is-played'));
            if (timer) timer.textContent = '0:00';
            audio.currentTime = 0;
        });

        if (speedBtn) {
            speedBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const cur = parseFloat(speedBtn.dataset.speed || '1');
                const next = cur === 1 ? 1.5 : (cur === 1.5 ? 2 : 1);
                speedBtn.dataset.speed = String(next);
                speedBtn.textContent = `${next}x`;
                audio.defaultPlaybackRate = next;
                audio.playbackRate = next;
            });
        }

        if (waveform) {
            waveform.addEventListener('click', (e) => {
                e.stopPropagation();
                if (!audio.duration) return;
                const rect = waveform.getBoundingClientRect();
                const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                audio.currentTime = ratio * audio.duration;
            });
        }
    }

    /**
     * Render distinct audio track card bubble
     */
    renderAudioTrackBubble(message, metadata = {}) {
        const bubble = document.createElement('div');
        bubble.className = `message-bubble ${message.isOwn ? 'sent' : 'received'} audio-track-bubble group-${message.groupPosition}`;
        bubble.setAttribute('data-message-id', message.id);
        bubble.setAttribute('data-sender-id', message.senderId);
        bubble.setAttribute('data-status', message.status);
        bubble.setAttribute('data-group-position', message.groupPosition);
        this._applyBubbleStyle(bubble);

        const audioUrl = metadata.url || '';
        const rawName = metadata.file_name || message.content || 'Audio Track';
        const fileName = rawName.split('/').pop().split('\\').pop();
        const sizeStr = this._formatFileSize(metadata.size);

        bubble.innerHTML = `
            <div class="audio-track-inner">
                <button type="button" class="audio-track-play-btn" aria-label="Play track">
                    <i class="bi bi-play-fill track-play-icon"></i>
                </button>
                <div class="audio-track-details">
                    <div class="audio-track-title" title="${escapeHtml(fileName)}">${escapeHtml(fileName)}</div>
                    <div class="audio-track-scrubber-track">
                        <div class="audio-track-scrubber-fill" style="width: 0%;"></div>
                    </div>
                    <div class="audio-track-meta-row">
                        <span class="audio-track-time">0:00</span>
                        ${sizeStr ? `<span class="audio-track-dot">•</span><span class="audio-track-size">${sizeStr}</span>` : ''}
                    </div>
                </div>
                <div class="audio-track-badge">
                    <i class="bi bi-music-note-beamed"></i>
                </div>
                <audio src="${escapeHtml(audioUrl)}" preload="metadata" class="d-none track-audio-el"></audio>
            </div>
        `;

        this._bindAudioTrackEvents(bubble);
        return bubble;
    }

    /**
     * Bind audio track playback and scrubber events
     */
    _bindAudioTrackEvents(bubble) {
        const playBtn = bubble.querySelector('.audio-track-play-btn');
        const playIcon = bubble.querySelector('.track-play-icon');
        const audio = bubble.querySelector('.track-audio-el');
        const timer = bubble.querySelector('.audio-track-time');
        const fill = bubble.querySelector('.audio-track-scrubber-fill');
        const track = bubble.querySelector('.audio-track-scrubber-track');

        if (!playBtn || !audio) return;

        playBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (audio.paused) {
                // Pause all other audio
                document.querySelectorAll('.vn-audio-el, .track-audio-el').forEach(other => {
                    if (other !== audio && !other.paused) {
                        other.pause();
                        other.currentTime = 0;
                        const otherBubble = other.closest('.voice-note-bubble, .audio-track-bubble');
                        otherBubble?.querySelector('.vn-play-icon, .track-play-icon')?.classList.replace('bi-pause-fill', 'bi-play-fill');
                    }
                });

                audio.play().then(() => {
                    playIcon.classList.replace('bi-play-fill', 'bi-pause-fill');
                }).catch(err => console.warn('[AUDIO_TRACK] Play blocked:', err));
            } else {
                audio.pause();
                playIcon.classList.replace('bi-pause-fill', 'bi-play-fill');
            }
        });

        audio.addEventListener('timeupdate', () => {
            if (timer) timer.textContent = this._formatAudioDuration(audio.currentTime);
            const duration = audio.duration || 1;
            const pct = Math.min(100, (audio.currentTime / duration) * 100);
            if (fill) fill.style.width = `${pct}%`;
        });

        audio.addEventListener('ended', () => {
            playIcon.classList.replace('bi-pause-fill', 'bi-play-fill');
            if (fill) fill.style.width = '0%';
            if (timer) timer.textContent = '0:00';
            audio.currentTime = 0;
        });

        if (track) {
            track.addEventListener('click', (e) => {
                e.stopPropagation();
                if (!audio.duration) return;
                const rect = track.getBoundingClientRect();
                const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                audio.currentTime = ratio * audio.duration;
            });
        }
    }

    _formatAudioDuration(seconds) {
        if (isNaN(seconds) || seconds < 0) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    _formatFileSize(bytes) {
        if (!bytes || isNaN(bytes) || bytes <= 0) return '';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
    }

    _getDocumentTypeInfo(ext) {
        const cleanExt = (ext || '').toLowerCase().replace('.', '');
        switch (cleanExt) {
            case 'pdf':
                return { icon: 'bi-file-earmark-pdf-fill', badgeClass: 'doc-badge-pdf', label: 'PDF Document' };
            case 'doc':
            case 'docx':
                return { icon: 'bi-file-earmark-word-fill', badgeClass: 'doc-badge-word', label: 'Word Document' };
            case 'xls':
            case 'xlsx':
            case 'csv':
                return { icon: 'bi-file-earmark-excel-fill', badgeClass: 'doc-badge-excel', label: 'Spreadsheet' };
            case 'ppt':
            case 'pptx':
                return { icon: 'bi-file-earmark-ppt-fill', badgeClass: 'doc-badge-ppt', label: 'Presentation' };
            case 'zip':
            case 'rar':
            case '7z':
            case 'tar':
            case 'gz':
                return { icon: 'bi-file-earmark-zip-fill', badgeClass: 'doc-badge-zip', label: 'Archive' };
            case 'txt':
            case 'py':
            case 'js':
            case 'html':
            case 'css':
            case 'json':
                return { icon: 'bi-file-earmark-code-fill', badgeClass: 'doc-badge-code', label: 'Code File' };
            default:
                return { icon: 'bi-file-earmark-fill', badgeClass: 'doc-badge-generic', label: 'Document' };
        }
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
        
        // Build wrapper containing avatar, bubble and meta (timestamp + read receipt)
        const wrapperDiv = document.createElement('div');
        wrapperDiv.className = `message-wrapper ${message.isOwn ? 'sent-wrapper' : 'received-wrapper'} group-${message.groupPosition}`;
        wrapperDiv.setAttribute('data-message-id', message.id);
        wrapperDiv.setAttribute('data-sender-id', message.senderId);
        wrapperDiv.setAttribute('data-status', message.status);
        wrapperDiv.setAttribute('data-group-position', message.groupPosition);

        // Add avatar for received messages (only on last/single in group)
        if (!message.isOwn) {
            const shouldShowAvatar = message.groupPosition === 'single' || message.groupPosition === 'last';
            const avatarContainer = document.createElement('div');
            avatarContainer.className = `message-avatar-container ${shouldShowAvatar ? '' : 'hidden'}`;
            
            if (shouldShowAvatar) {
                const avatarUrl = this._getSenderAvatar(message.senderId);
                const avatarImg = document.createElement('img');
                avatarImg.className = 'message-avatar';
                avatarImg.src = avatarUrl;
                avatarImg.alt = 'Avatar';
                avatarContainer.appendChild(avatarImg);
            }
            
            wrapperDiv.appendChild(avatarContainer);
        }

        // Content wrapper for link and meta
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'message-content-wrapper';

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
        contentWrapper.appendChild(messageDiv);

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

            contentWrapper.appendChild(metaDiv);
        }

        wrapperDiv.appendChild(contentWrapper);
        return wrapperDiv;
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
