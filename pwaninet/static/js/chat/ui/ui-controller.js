/**
 * UIController - Read-only subscriber to store
 * Subscribes to store changes only, NEVER writes or mutates state
 * Coordinates UI rendering based on store state
 */

import { store } from '../core/store.js';
import { messageService } from '../core/message-service.js';
import { MessageRenderer } from './renderer.js';

export class UIController {
    constructor() {
        this.renderer = null;
        this.unsubscribe = null;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.lastState = null;
    }

    /**
     * Initialize UI controller (read-only consumer)
     */
    init() {
        this._log('UI_CONTROLLER_INIT');

        // Get state FIRST
        const initialState = store.getState();

        // Initialize renderer with valid currentUserId
        this.renderer = new MessageRenderer();
        this.renderer.init(initialState.currentUserId);
        window.__store = store;

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
            typingUsers: state.typingUsers.size
        });

        // Only render if state actually changed
        if (this._stateChanged(state, this.lastState)) {
            // Update connection status in UI
            this._updateConnectionStatus(state.connectionState);

            // Update typing indicators
            this._updateTypingIndicators(state.typingUsers);

            // Render messages (pure rendering)
            this.renderer.render(state.messages);

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
        // Message input handler
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendBtn');

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this._handleSendMessage(messageInput.value);
                }
                this._handleTyping();
            });

            messageInput.addEventListener('input', () => {
                // Auto-expand textarea (pure UI behavior)
                messageInput.style.height = 'auto';
                const newHeight = Math.min(messageInput.scrollHeight, 120);
                messageInput.style.height = newHeight + 'px';
            });
        }

        if (sendButton) {
            sendButton.addEventListener('click', () => {
                this._handleSendMessage(messageInput.value);
            });
        }

        // Connection status click to reconnect
        const statusElement = document.getElementById('chatStatus');
        if (statusElement) {
            statusElement.addEventListener('click', () => {
                if (!store.isConnected()) {
                    this._handleReconnect();
                }
            });
        }

        this._log('UI_EVENT_HANDLERS_SETUP');
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
        // Typing indicator would be handled by message service if needed
        // For now, we keep it simple as UI-only behavior
        this._log('TYPING_INDICATOR');
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
     * Update typing indicators (pure UI update)
     * @param {Map} typingUsers - Typing users map
     */
    _updateTypingIndicators(typingUsers) {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            const typingArray = Array.from(typingUsers.values());
            if (typingArray.length > 0) {
                indicator.textContent = `${typingArray[0]} is typing...`;
                indicator.style.display = 'block';
            } else {
                indicator.textContent = '';
                indicator.style.display = 'none';
            }
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
     * Check if state changed (pure comparison)
     * @param {Object} newState - New state
     * @param {Object} lastState - Last state
     * @returns {boolean} State changed
     */
    _stateChanged(newState, lastState) {
        if (!lastState) return true;

        return (
            newState.messages.length !== lastState.messagesLength ||
            newState.connectionState !== lastState.connectionState ||
            newState.typingUsers.size !== lastState.typingUsersSize ||
            newState.uiState !== lastState.uiState ||
            JSON.stringify(newState.currentTheme) !== JSON.stringify(lastState.currentTheme)
        );
    }

    /**
     * Create state snapshot for comparison (pure data transformation)
     * @param {Object} state - State to snapshot
     * @returns {Object} State snapshot
     */
    _createStateSnapshot(state) {
        return {
            messagesLength: state.messages.length,
            connectionState: state.connectionState,
            typingUsersSize: state.typingUsers.size,
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
