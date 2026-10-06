/**
 * UIController - Read-only subscriber to store
 * Subscribes to store changes only, NEVER writes or mutates state
 * Coordinates UI rendering based on store state
 */

import { store } from '../core/store.js';
import { messageService } from '../core/message-service.js';
import { MessageRenderer } from './renderer.js';
import { contextMenuService } from '../features/context-menu/context-menu.service.js';
import { messageSoundManager } from '../shared/message-sound.js';
import { eventBus } from '../core/event-bus.js';
import { EVENTS } from '../shared/constants.js';

export class UIController {
    constructor() {
        this.renderer = null;
        this.unsubscribe = null;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.lastState = null;
        this.audioInitialized = false;
    }

    /**
     * Initialize UI controller (read-only consumer)
     */
    init() {
        this._log('UI_CONTROLLER_INIT');

        // Get state FIRST
        const initialState = store.getState();
        this.currentUserId = initialState.currentUserId;

        // Initialize renderer with valid currentUserId
        this.renderer = new MessageRenderer();
        this.renderer.init(this.currentUserId);
        window.__store = store;

        // Setup read receipt observer
        this._setupReadReceiptObserver();

        // Subscribe to store changes (read-only consumer)
        this.unsubscribe = store.subscribe((state) => {
            this._handleStateChange(state);
        });

        // Setup UI event handlers (user interactions only)
        this._setupUIEventHandlers();

        // Initial render
        this._handleStateChange(initialState);

        this._log('UI_CONTROLLER_INITIALIZED');
        console.log("STATE UPDATE:", initialState.messages.length);
    }

    /**
     * Handle state change from store (read-only)
     * @param {Object} state - Current state from store
     */
    _handleStateChange(state) {
        this._log('STATE_CHANGE_RECEIVED', {
            messagesCount: state.messages.length,
            connectionState: state.connectionState,
            typingUsers: state.typingUsers.size,
            peerOnlineStatus: state.peerOnlineStatus.size
        });

        // Only render if state actually changed
        if (this._stateChanged(state, this.lastState)) {
            // Update connection status in UI
            this._updateConnectionStatus(state.connectionState);

            // Update typing indicators and peer status
            this._updateTypingIndicators(state.typingUsers, state.peerOnlineStatus);

            // Render messages (pure rendering)
            this.renderer.render(state.messages);

            // Attach context menu listeners to newly rendered messages
            setTimeout(() => {
                contextMenuService.attachToMessages();
            }, 50);

            // Observe received messages for read receipts (with small delay for DOM settling)
            setTimeout(() => {
                this._observeReceivedMessages();
            }, 100);

            // Update UI state
            this._updateUIState(state.uiState);

            // Update theme
            if (state.currentTheme) {
                this._applyTheme(state.currentTheme, state.themeMode);
            }

            this.lastState = this._createStateSnapshot(state);
        }
    }

    /**
     * Setup UI event handlers (user interactions only)
     */
    _setupUIEventHandlers() {
        this._log('SETUP_UI_EVENT_HANDLERS');

        // Message retry handler
        window.addEventListener('messageRetry', (event) => {
            this._log('MESSAGE_RETRY_EVENT', event.detail);
            this._handleMessageRetry(event.detail);
        });

        // Message input handler
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendBtn');

        if (messageInput) {
            // Unlock audio context on first user interaction (browser autoplay policy)
            const unlockAudioOnInteraction = () => {
                if (!this.audioInitialized) {
                    messageSoundManager.unlock().catch(err => {
                        console.warn('[UI_CONTROLLER] Failed to unlock audio:', err);
                    });
                    this.audioInitialized = true;
                }
            };

            // Keyboard events
            messageInput.addEventListener('keypress', (e) => {
                unlockAudioOnInteraction();
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleSendMessage(messageInput.value);
                }
                this._handleTyping();
            });

            messageInput.addEventListener('input', () => {
                unlockAudioOnInteraction();
                // Auto-expand textarea (pure UI behavior)
                messageInput.style.height = 'auto';
                const newHeight = Math.min(messageInput.scrollHeight, 120);
                messageInput.style.height = `${newHeight}px`;

                // Toggle voice/send button icon (pure UI behavior)
                this._toggleVoiceSendButton(messageInput.value);

                // Send typing indicator
                this._handleTyping();
            });

            // Touch events for mobile devices
            messageInput.addEventListener('touchstart', () => {
                unlockAudioOnInteraction();
                this._handleTyping();
            });

            messageInput.addEventListener('focus', () => {
                unlockAudioOnInteraction();
                this._handleTyping();
            });
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this._handleSendClick(messageInput);
            });
        }

        // Combined Voice / Send button logic
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn) {
            voiceBtn.addEventListener('click', (e) => {
                const isSendMode = voiceBtn.classList.contains('send-mode');
                if (isSendMode) {
                    this._handleSendClick(messageInput);
                }
            });
        }

        // Reply & Edit cancel button handlers
        const cancelReplyBtn = document.getElementById('cancelReplyBtn');
        if (cancelReplyBtn) {
            cancelReplyBtn.addEventListener('click', () => {
                this.replyToMessageId = null;
                const bar = document.getElementById('replyPreviewBar');
                if (bar) bar.classList.add('d-none');
            });
        }

        const cancelEditBtn = document.getElementById('cancelEditBtn');
        if (cancelEditBtn) {
            cancelEditBtn.addEventListener('click', () => {
                this.editingMessageId = null;
                const bar = document.getElementById('editPreviewBar');
                if (bar) bar.classList.add('d-none');
                const messageInput = document.getElementById('messageInput');
                if (messageInput) messageInput.value = '';
            });
        }

        // Context menu action handler (Reply, Edit, Copy, Delete)
        eventBus.on(EVENTS.CONTEXT_MENU_ACTION, (detail) => {
            this._handleContextMenuAction(detail);
        });



        const themeBtn = document.getElementById('themeBtn');
        if (themeBtn) {
            themeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                eventBus.emit(EVENTS.THEME_SELECTOR_SHOW);
                
                const themeModal = document.getElementById('themeModal');
                const overlay = document.getElementById('overlay');
                if (themeModal) themeModal.classList.add('show');
                if (overlay) overlay.classList.add('show');
            });
        }

        const cameraBtn = document.getElementById('cameraBtn');
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => {
                const cameraView = document.getElementById('cameraView');
                if (cameraView) cameraView.classList.add('show');
            });
        }
    }

    _handleContextMenuAction(detail) {
        const { action, messageId } = detail;
        const message = store.getMessageById(messageId);
        if (!message) return;

        if (action === 'reply') {
            this.replyToMessageId = messageId;
            this.editingMessageId = null;
            const editBar = document.getElementById('editPreviewBar');
            if (editBar) editBar.classList.add('d-none');

            const replyBar = document.getElementById('replyPreviewBar');
            const replySender = document.getElementById('replySenderName');
            const replyText = document.getElementById('replyTextSnippet');
            if (replyBar && replySender && replyText) {
                const currentUserId = store.getState().currentUserId;
                const isOwn = message.senderId === currentUserId;
                replySender.textContent = isOwn ? 'Replying to yourself' : 'Replying to message';
                replyText.textContent = message.content || '[Attachment]';
                replyBar.classList.remove('d-none');
            }
            const input = document.getElementById('messageInput');
            if (input) input.focus();

        } else if (action === 'edit') {
            const currentUserId = store.getState().currentUserId;
            if (message.senderId !== currentUserId) {
                alert('You can only edit your own messages.');
                return;
            }
            this.editingMessageId = messageId;
            this.replyToMessageId = null;
            const replyBar = document.getElementById('replyPreviewBar');
            if (replyBar) replyBar.classList.add('d-none');

            const editBar = document.getElementById('editPreviewBar');
            const editText = document.getElementById('editTextSnippet');
            if (editBar && editText) {
                editText.textContent = message.content;
                editBar.classList.remove('d-none');
            }
            const input = document.getElementById('messageInput');
            if (input) {
                input.value = message.content || '';
                input.focus();
                this._toggleVoiceSendButton(input.value);
            }

        } else if (action === 'copy') {
            if (message.content) {
                navigator.clipboard.writeText(message.content).then(() => {
                    const toast = document.createElement('div');
                    toast.className = 'position-fixed bottom-0 start-50 translate-middle-x bg-dark text-white px-3 py-2 rounded-pill shadow';
                    toast.style.zIndex = '9999';
                    toast.style.marginBottom = '80px';
                    toast.style.fontSize = '0.85rem';
                    toast.textContent = 'Message copied to clipboard';
                    document.body.appendChild(toast);
                    setTimeout(() => toast.remove(), 2000);
                });
            }

        } else if (action === 'delete') {
            const currentUserId = store.getState().currentUserId;
            if (message.senderId !== currentUserId) {
                alert('You can only delete your own messages.');
                return;
            }
            if (confirm('Delete this message for everyone?')) {
                import('../core/websocket.js').then(({ webSocketManager }) => {
                    webSocketManager.send({
                        type: 'delete_message',
                        message_id: parseInt(messageId, 10)
                    });
                });
                store.updateMessage(messageId, {
                    isDeleted: true,
                    content: 'This message was deleted'
                });
            }
        }
    }

    /**
     * Handle send click with audio unlock
     */
    _handleSendClick(messageInput) {
        if (!this.audioInitialized) {
            messageSoundManager.unlock().catch(err => {
                console.warn('[UI_CONTROLLER] Failed to unlock audio:', err);
            });
            this.audioInitialized = true;
        }
        if (messageInput) {
            this._handleSendMessage(messageInput.value);
            this._toggleVoiceSendButton('');
        }
    }

    /**
     * Toggle voice/send button icon
     * @param {string} content - Input content
     */
    _toggleVoiceSendButton(content) {
        const voiceBtn = document.getElementById('voiceBtn');
        const sendBtn = document.getElementById('sendBtn');
        const micWrapper = document.getElementById('micIconWrapper');
        const sendWrapper = document.getElementById('sendIconWrapper');
        const hasText = content && content.trim().length > 0;

        if (sendBtn) {
            if (hasText) {
                sendBtn.classList.add('is-active');
                sendBtn.removeAttribute('disabled');
            } else {
                sendBtn.classList.remove('is-active');
            }
        }

        if (voiceBtn) {
            if (hasText) {
                if (micWrapper) micWrapper.classList.add('d-none');
                if (sendWrapper) sendWrapper.classList.remove('d-none');
                voiceBtn.title = 'Send message';
                voiceBtn.setAttribute('aria-label', 'Send message');
                voiceBtn.classList.add('send-mode', 'is-active');
            } else {
                if (micWrapper) micWrapper.classList.remove('d-none');
                if (sendWrapper) sendWrapper.classList.add('d-none');
                voiceBtn.title = 'Voice message';
                voiceBtn.setAttribute('aria-label', 'Voice message');
                voiceBtn.classList.remove('send-mode', 'is-active');
            }
        }
    }
    
    /**
     * Handle message retry
     * @param {Object} detail - Event detail with messageId
     */
    async _handleMessageRetry(detail) {
        const { messageId } = detail;
        this._log('HANDLE_MESSAGE_RETRY', { messageId });
        
        try {
            await messageService.retryMessage(messageId);
        } catch (error) {
            console.error('[UI_CONTROLLER] Retry failed:', error);
        }
    }

    /**
     * Handle send message (UI → MessageService)
     * @param {string} content - Message content
     */
    async _handleSendMessage(content) {
        this._log('SEND_MESSAGE_CLICKED', { content });

        if (!content || !content.trim()) {
            return;
        }

        const clean = content.trim();

        // Clear input
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = '';
            messageInput.style.height = 'auto';
        }

        // Handle edit mode
        if (this.editingMessageId) {
            const editId = this.editingMessageId;
            this.editingMessageId = null;
            const editBar = document.getElementById('editPreviewBar');
            if (editBar) editBar.classList.add('d-none');

            import('../core/websocket.js').then(({ webSocketManager }) => {
                webSocketManager.send({
                    type: 'edit_message',
                    message_id: parseInt(editId, 10),
                    content: clean
                });
            });
            store.updateMessage(editId, {
                content: clean,
                editedAt: new Date().toISOString()
            });
            return;
        }

        // Handle reply mode
        const replyId = this.replyToMessageId;
        this.replyToMessageId = null;
        const replyBar = document.getElementById('replyPreviewBar');
        if (replyBar) replyBar.classList.add('d-none');

        await messageService.sendMessage(clean, {
            reply_to_id: replyId ? parseInt(replyId, 10) : null
        });
    }

    /**
     * Handle typing indicator (UI interaction only)
     */
    _handleTyping() {
        messageService.sendTypingIndicator(true);

        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        this.typingTimeout = setTimeout(() => {
            messageService.sendTypingIndicator(false);
        }, 1500);

        this._log('TYPING_INDICATOR_SENT');
    }

    /**
     * Handle reconnect request (UI → AppController)
     */
    _handleReconnect() {
        this._log('RECONNECT_REQUESTED');
        if (window.appController) {
            window.appController.handleReconnect();
        }
    }

    /**
     * Update connection status in UI (pure UI update)
     * @param {string} connectionState - Connection state
     */
    _updateConnectionStatus(connectionState) {
        const statusElement = document.getElementById('chatStatus');
        if (statusElement) {
            const statusMap = {
                'connected': 'Active now',
                'connecting': 'Connecting...',
                'disconnected': 'Waiting for network...',
                'reconnecting': 'Connecting...',
                'error': 'Connection error'
            };
            if (connectionState !== 'connected') {
                statusElement.textContent = statusMap[connectionState] || connectionState;
                statusElement.className = `chat-status ${connectionState} text-muted`;
            }
        }
    }

    /**
     * Update typing indicators and peer online status (pure UI update)
     * @param {Map} typingUsers - Typing users map
     * @param {Map} peerOnlineStatus - Peer online status map
     */
    _updateTypingIndicators(typingUsers, peerOnlineStatus) {
        const chatStatus = document.getElementById('chatStatus');
        const chatAvatar = document.querySelector('.chat-avatar');

        if (!chatStatus) return;

        const typingArray = Array.from(typingUsers.values());
        const peerArray = Array.from(peerOnlineStatus.entries());
        const state = store.getState();
        const recordingUsers = state.recordingUsers || new Map();
        const recordingArray = Array.from(recordingUsers.values());

        const peer = peerArray.length > 0 ? peerArray[0][1] : null;
        const isPeerOnline = peer ? peer.isOnline : false;
        const lastSeen = peer ? peer.lastSeen : null;

        if (typingArray.length > 0) {
            const username = typingArray[0];
            this.renderer.showTypingIndicator(username);
            chatStatus.textContent = 'typing...';
            chatStatus.className = 'chat-status typing text-primary fw-semibold';
            if (chatAvatar) chatAvatar.classList.remove('avatar-online');
        } else if (recordingArray.length > 0) {
            this.renderer.hideTypingIndicator();
            chatStatus.textContent = 'recording voice note...';
            chatStatus.className = 'chat-status text-danger fw-semibold';
            if (chatAvatar) chatAvatar.classList.remove('avatar-online');
        } else {
            this.renderer.hideTypingIndicator();
            if (isPeerOnline) {
                chatStatus.textContent = 'Active now';
                chatStatus.className = 'chat-status text-success fw-semibold';
                if (chatAvatar) chatAvatar.classList.add('avatar-online');
            } else {
                chatStatus.textContent = lastSeen ? this._formatLastSeen(lastSeen) : '';
                chatStatus.className = 'chat-status text-muted';
                if (chatAvatar) chatAvatar.classList.remove('avatar-online');
            }
        }
    }

    /**
     * Format last seen timestamp to human readable string
     * @param {number|string} timestamp - Last seen timestamp
     * @returns {string} Formatted string
     */
    _formatLastSeen(timestamp) {
        if (!timestamp) return '';
        const now = new Date();
        const lastSeen = new Date(timestamp);
        if (isNaN(lastSeen.getTime())) return '';
        const diffMs = now - lastSeen;
        const diffSeconds = Math.floor(diffMs / 1000);
        const diffMinutes = Math.floor(diffSeconds / 60);

        if (diffSeconds < 60) return 'last seen just now';
        if (diffMinutes < 60) return `last seen ${diffMinutes}m ago`;

        // Check if same day
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        const lastSeenDate = new Date(lastSeen);
        lastSeenDate.setHours(0, 0, 0, 0);

        if (lastSeenDate.getTime() === today.getTime()) {
            const timeStr = lastSeen.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
            return `last seen today at ${timeStr}`;
        }

        if (lastSeenDate.getTime() === yesterday.getTime()) {
            const timeStr = lastSeen.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
            return `last seen yesterday at ${timeStr}`;
        }

        const day = lastSeen.getDate();
        const month = lastSeen.toLocaleDateString('en-US', { month: 'short' });
        const timeStr = lastSeen.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
        return `last seen ${day} ${month} at ${timeStr}`;
    }

    /**
     * Update UI state (pure UI update)
     * @param {string} uiState - UI state
     */
    _updateUIState(uiState) {
        // Update UI based on state (pure UI behavior)
        const loadingElement = document.getElementById('chatLoading');
        if (loadingElement) {
            loadingElement.style.display = uiState === 'loading' ? 'block' : 'none';
        }
    }

    /**
     * Apply theme (pure UI update)
     * @param {Object} theme - Theme object
     * @param {string} mode - Theme mode
     */
    _applyTheme(theme, mode) {
        if (theme) {
            Object.entries(theme).forEach(([property, value]) => {
                document.documentElement.style.setProperty(property, value);
            });
        }
    }

    /**
     * Setup read receipt observer to detect when received messages become visible
     */
    _setupReadReceiptObserver() {
        this._log('SETUP_READ_RECEIPT_OBSERVER');

        // Cleanup existing observer
        if (this.readReceiptObserver) {
            this.readReceiptObserver.disconnect();
        }

        // Track already-read messages to avoid duplicate receipts
        this.readMessageIds = new Set();

        // Create intersection observer
        this.readReceiptObserver = new IntersectionObserver((entries) => {
            const messageIdsToMark = [];

            entries.forEach(entry => {
                console.log('[INTERSECTION_OBSERVER] Entry:', {
                    isIntersecting: entry.isIntersecting,
                    messageId: entry.target.getAttribute('data-message-id'),
                    senderId: entry.target.getAttribute('data-sender-id'),
                    currentUserId: this.currentUserId
                });

                if (entry.isIntersecting) {
                    const messageId = entry.target.getAttribute('data-message-id');
                    const senderId = entry.target.getAttribute('data-sender-id');

                    // Only mark received messages (not own messages) that haven't been read yet
                    if (messageId &&
                        senderId &&
                        String(senderId) !== String(this.currentUserId) &&
                        !this.readMessageIds.has(messageId)) {

                        console.log('[INTERSECTION_OBSERVER] Marking message as read:', messageId);
                        messageIdsToMark.push(messageId);
                        this.readMessageIds.add(messageId);

                        // Stop observing this message
                        this.readReceiptObserver.unobserve(entry.target);
                    } else {
                        console.log('[INTERSECTION_OBSERVER] Skipping message:', {
                            messageId,
                            hasMessageId: !!messageId,
                            hasSenderId: !!senderId,
                            isOwnMessage: senderId ? String(senderId) === String(this.currentUserId) : 'no sender',
                            alreadyRead: messageId ? this.readMessageIds.has(messageId) : 'no id'
                        });
                    }
                }
            });

            // Send read receipts for visible messages
            if (messageIdsToMark.length > 0) {
                console.log('[INTERSECTION_OBSERVER] Sending read receipts for visible messages:', messageIdsToMark);
                this._log('MESSAGES_BECAME_VISIBLE', { count: messageIdsToMark.length });
                messageService.markMessagesAsRead(messageIdsToMark);
            }
        }, {
            root: document.getElementById('messagesContainer'),
            threshold: 0.5 // Message must be 50% visible
        });

        this._log('READ_RECEIPT_OBSERVER_SETUP');
    }

    /**
     * Observe a message element for read receipt
     * @param {HTMLElement} element - Message element
     */
    _observeMessageForReadReceipt(element) {
        if (this.readReceiptObserver && element) {
            this.readReceiptObserver.observe(element);
        }
    }

    /**
     * Observe all received (non-own) messages in the container for read receipts
     * Also immediately marks visible messages as read (for real-time updates)
     */
    _observeReceivedMessages() {
        const container = document.getElementById('messagesContainer');
        if (!container || !this.readReceiptObserver) return;

        // Find all received message bubbles (not sent by current user)
        const receivedMessages = container.querySelectorAll('.message-bubble.received[data-message-id]');
        const immediatelyVisibleIds = [];

        receivedMessages.forEach(messageEl => {
            const messageId = messageEl.getAttribute('data-message-id');
            // Only observe if not already read
            if (messageId && !this.readMessageIds.has(messageId)) {
                this.readReceiptObserver.observe(messageEl);

                // Check if message is already visible in viewport (for real-time messages)
                if (this._isElementVisible(messageEl, container)) {
                    immediatelyVisibleIds.push(messageId);
                    this.readMessageIds.add(messageId);
                    this.readReceiptObserver.unobserve(messageEl);
                }
            }
        });

        // Immediately mark visible messages as read (don't wait for scroll)
        if (immediatelyVisibleIds.length > 0) {
            console.log('[READ_RECEIPTS] Sending immediate read receipts for:', immediatelyVisibleIds);
            this._log('MESSAGES_ALREADY_VISIBLE', { count: immediatelyVisibleIds.length });
            messageService.markMessagesAsRead(immediatelyVisibleIds);
        } else {
            console.log('[READ_RECEIPTS] No immediately visible messages found');
        }

        this._log('OBSERVING_RECEIVED_MESSAGES', {
            total: receivedMessages.length,
            newlyObserved: receivedMessages.length - immediatelyVisibleIds.length,
            immediatelyRead: immediatelyVisibleIds.length
        });
    }

    /**
     * Check if an element is visible in its container's viewport
     * @param {HTMLElement} element - Element to check
     * @param {HTMLElement} container - Container element
     * @returns {boolean} True if element is visible
     */
    _isElementVisible(element, container) {
        const containerRect = container.getBoundingClientRect();
        const elementRect = element.getBoundingClientRect();

        // More lenient visibility check - element should be at least partially visible
        // and not completely above or below the container
        const isVisible = (
            elementRect.bottom > containerRect.top &&  // Not completely above
            elementRect.top < containerRect.bottom &&   // Not completely below
            elementRect.height > 0
        );

        // Debug logging
        if (element.getAttribute('data-message-id')) {
            console.log('[VISIBILITY_CHECK]', {
                messageId: element.getAttribute('data-message-id'),
                isVisible,
                elementTop: elementRect.top,
                elementBottom: elementRect.bottom,
                containerTop: containerRect.top,
                containerBottom: containerRect.bottom
            });
        }

        return isVisible;
    }

    /**
     * Check if state changed (pure comparison)
     * @param {Object} newState - New state
     * @param {Object} lastState - Last state
     * @returns {boolean} State changed
     */
    _stateChanged(newState, lastState) {
        if (!lastState) return true;

        // Check message count
        if (newState.messages.length !== lastState.messagesLength) {
            console.log('[UI_CONTROLLER] State changed: message count', lastState.messagesLength, '->', newState.messages.length);
            return true;
        }

        // Check message statuses (for read receipts)
        if (newState.messages.length > 0) {
            const newChecksum = this._computeMessagesChecksum(newState.messages);
            if (lastState.messagesChecksum && newChecksum !== lastState.messagesChecksum) {
                console.log('[UI_CONTROLLER] State changed: message checksum', lastState.messagesChecksum, '->', newChecksum);
                return true;
            }
            // If no previous checksum but we have messages now, state changed
            if (!lastState.messagesChecksum && newState.messages.length > 0) {
                console.log('[UI_CONTROLLER] State changed: new messages appeared');
                return true;
            }
        }

        const changed = (
            newState.connectionState !== lastState.connectionState ||
            newState.typingUsers.size !== lastState.typingUsersSize ||
            newState.peerOnlineStatus.size !== lastState.peerOnlineStatusSize ||
            newState.uiState !== lastState.uiState ||
            JSON.stringify(newState.currentTheme) !== JSON.stringify(lastState.currentTheme)
        );

        if (changed) {
            console.log('[UI_CONTROLLER] State changed: other properties');
        }

        return changed;
    }

    /**
     * Compute a checksum of message statuses for detecting read receipt updates
     * @param {Array} messages - Messages array
     * @returns {string} Checksum string
     */
    _computeMessagesChecksum(messages) {
        // Create a simple checksum based on message IDs and statuses
        // This allows us to detect when a message status changes (e.g., sent -> read)
        return messages.map(m => `${m.id}:${m.status || 'sent'}`).join('|');
    }

    /**
     * Create state snapshot for comparison (pure data transformation)
     * @param {Object} state - State to snapshot
     * @returns {Object} State snapshot
     */
    _createStateSnapshot(state) {
        return {
            messagesLength: state.messages.length,
            messagesChecksum: state.messages.length > 0
                ? this._computeMessagesChecksum(state.messages)
                : null,
            connectionState: state.connectionState,
            typingUsersSize: state.typingUsers.size,
            peerOnlineStatusSize: state.peerOnlineStatus.size,
            uiState: state.uiState,
            currentTheme: state.currentTheme ? JSON.parse(JSON.stringify(state.currentTheme)) : null
        };
    }

    /**
     * Get UI controller status (read-only)
     * @returns {Object} Status
     */
    getStatus() {
        return {
            initialized: !!this.unsubscribe,
            rendererInitialized: !!this.renderer,
            subscribed: !!this.unsubscribe,
            lastState: this.lastState,
            isReadOnly: true // Explicitly mark as read-only
        };
    }

    /**
     * Destroy UI controller
     */
    destroy() {
        this._log('UI_CONTROLLER_DESTROY');

        if (this.unsubscribe) {
            this.unsubscribe();
            this.unsubscribe = null;
        }

        if (this.renderer) {
            this.renderer.destroy();
            this.renderer = null;
        }

        // Clean up read receipt observer
        if (this.readReceiptObserver) {
            this.readReceiptObserver.disconnect();
            this.readReceiptObserver = null;
        }

        if (this.readMessageIds) {
            this.readMessageIds.clear();
            this.readMessageIds = null;
        }

        this.lastState = null;
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[UI_CONTROLLER] ${action}:`, data);
        }
    }
}

// Create and export singleton instance
export const uiController = new UIController();
