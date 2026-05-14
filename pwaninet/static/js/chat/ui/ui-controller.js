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
            // Initialize audio context on first user interaction (browser autoplay policy)
            const initAudioOnInteraction = () => {
                if (!this.audioInitialized) {
                    messageSoundManager.init().catch(err => {
                        console.warn('[UI_CONTROLLER] Failed to init audio:', err);
                    });
                    this.audioInitialized = true;
                }
            };

            // Keyboard events
            messageInput.addEventListener('keypress', (e) => {
                initAudioOnInteraction();
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleSendMessage(messageInput.value);
                }
                this._handleTyping();
            });

            messageInput.addEventListener('input', () => {
                initAudioOnInteraction();
                // Auto-expand textarea (pure UI behavior)
                messageInput.style.height = 'auto';
                const newHeight = Math.min(messageInput.scrollHeight, 120);
                messageInput.style.height = `${newHeight}px`;

                // Send typing indicator
                this._handleTyping();
            });

            // Touch events for mobile devices
            messageInput.addEventListener('touchstart', () => {
                initAudioOnInteraction();
                this._handleTyping();
            });

            messageInput.addEventListener('focus', () => {
                initAudioOnInteraction();
                this._handleTyping();
            });
        }
        
        if (sendButton) {
            sendButton.addEventListener('click', () => {
                // Initialize audio context on send button click
                if (!this.audioInitialized) {
                    messageSoundManager.init().catch(err => {
                        console.warn('[UI_CONTROLLER] Failed to init audio:', err);
                    });
                    this.audioInitialized = true;
                }
                this._handleSendMessage(messageInput.value);
            });
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

        // Clear input (pure UI behavior)
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = '';
            messageInput.style.height = 'auto';
        }

        // Send through message service (ONLY ingestion layer)
        await messageService.sendMessage(content.trim());
    }

    /**
     * Handle typing indicator (UI interaction only)
     */
    _handleTyping() {
        // Send typing indicator start
        messageService.sendTypingIndicator(true);

        // Debounce stop indicator
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        this.typingTimeout = setTimeout(() => {
            messageService.sendTypingIndicator(false);
        }, 1000); // Stop typing indicator after 1 second of inactivity

        this._log('TYPING_INDICATOR_SENT');
    }

    /**
     * Handle reconnect request (UI → AppController)
     */
    _handleReconnect() {
        this._log('RECONNECT_REQUESTED');
        
        // Trigger reconnection through app controller (orchestration only)
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
                'connected': 'Online',
                'connecting': 'Connecting...',
                'disconnected': 'Offline',
                'reconnecting': 'Reconnecting...',
                'error': 'Connection Error'
            };
            
            statusElement.textContent = statusMap[connectionState] || connectionState;
            statusElement.className = `chat-status ${connectionState}`;
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

        // Get the first peer (other user in conversation)
        const peer = peerArray.length > 0 ? peerArray[0][1] : null;
        const isPeerOnline = peer ? peer.isOnline : false;
        const lastSeen = peer ? peer.lastSeen : null;

        if (typingArray.length > 0) {
            // User is typing - show ghost bubble with animated dots
            const username = typingArray[0];
            this.renderer.showTypingIndicator(username);

            // Also show status text
            chatStatus.textContent = 'typing...';
            chatStatus.className = 'chat-status typing';
            if (chatAvatar) {
                chatAvatar.classList.remove('avatar-online');
            }
        } else {
            // User is not typing - hide ghost bubble
            this.renderer.hideTypingIndicator();

            if (isPeerOnline) {
                // User is online but not typing
                chatStatus.textContent = '';
                chatStatus.className = 'chat-status';
                if (chatAvatar) {
                    chatAvatar.classList.add('avatar-online');
                }
            } else {
                // User is offline
                chatStatus.textContent = '';
                chatStatus.className = 'chat-status';
                if (chatAvatar) {
                    chatAvatar.classList.remove('avatar-online');
                }
            }
        }
    }

    /**
     * Format last seen timestamp to human readable string
     * @param {number} timestamp - Last seen timestamp
     * @returns {string} Formatted string
     */
    _formatLastSeen(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (seconds < 60) {
            return 'just now';
        } else if (minutes < 60) {
            return `${minutes}m ago`;
        } else if (hours < 24) {
            return `${hours}h ago`;
        } else if (days < 7) {
            return `${days}d ago`;
        } else {
            const date = new Date(timestamp);
            return date.toLocaleDateString();
        }
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
            return true;
        }

        // Check message statuses (for read receipts)
        if (newState.messages.length > 0 && lastState.messagesChecksum) {
            const newChecksum = this._computeMessagesChecksum(newState.messages);
            if (newChecksum !== lastState.messagesChecksum) {
                return true;
            }
        }

        return (
            newState.connectionState !== lastState.connectionState ||
            newState.typingUsers.size !== lastState.typingUsersSize ||
            newState.peerOnlineStatus.size !== lastState.peerOnlineStatusSize ||
            newState.uiState !== lastState.uiState ||
            JSON.stringify(newState.currentTheme) !== JSON.stringify(lastState.currentTheme)
        );
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
