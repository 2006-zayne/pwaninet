/**
 * WebSocketManager - Pure transport layer
 * NO business logic, NO state awareness, NO UI interaction
 * Pure WebSocket connection and message forwarding only
 */

export class WebSocketManager {
    constructor() {
        this.socket = null;
        this.conversationId = null;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.messageCallback = null;
        this.connectionCallback = null;
        this.isStale = false;
        this.shouldReconnect = true;
        this.paused = false;
        this.currentSocketId = 0;
        this.heartbeatInterval = null;
        this.lastMessageTime = Date.now();
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    }

    /**
     * Initialize WebSocket connection
     * @param {number} conversationId - Conversation ID
     */
    init(conversationId) {
        this._log('WEBSOCKET_INIT', { conversationId });
        
        this.conversationId = conversationId;
        
        this.connect();
    }


    startHeartbeat() {
        this.stopHeartbeat();

        this.heartbeatInterval = setInterval(() => {
            if (!this.isConnected()) return;

            const now = Date.now();
            const silence = now - this.lastMessageTime;

            // send ping
            this.send({ type: 'ping' });

            // FIRST STAGE: mark stale ONLY
            if (silence > 60000 && !this.isStale) {
                this.isStale = true;
                this._log('CONNECTION_STALE_MARKED', { silence });
                return;
            }

            // SECOND STAGE: only reconnect if STILL stale after grace period
            if (this.isStale && silence > 90000) {
                this._log('CONNECTION_RECONNECTING', { silence });

                this.isStale = false;

                this.disconnect();
                setTimeout(() => {
                    this.connect();
                }, 500);
            }

        }, 25000);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Set message callback (for forwarding to message service)
     * @param {Function} callback - Message callback
     */
    setMessageCallback(callback) {
        this.messageCallback = callback;
    }

    /**
     * Set connection callback (for notifying app controller)
     * @param {Function} callback - Connection callback
     */
    setConnectionCallback(callback) {
        this.connectionCallback = callback;
    }

    /**
     * Pause WebSocket connection (for loading initial messages)
     */
    pause() {
        console.log('[WEBSOCKET] Pausing WebSocket');
        this.paused = true;
        this.disconnect();
    }

    /**
     * Resume WebSocket connection (after loading initial messages)
     */

    resume() {
        this._log('WEBSOCKET_RESUME');

        this.paused = false;

        if (this.isConnected()) {
            this._log('ALREADY_CONNECTED_SKIP_RESUME');
            return;
        }

        this.connect();
    }

    /**
     * Connect to WebSocket
     */

    connect() {
        if (this.paused) return;

        this.shouldReconnect = true;

        if (this.socket) {
            this._forceClose();
        }

        const socketId = ++this.currentSocketId;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;

        this.socket = new WebSocket(wsUrl);

        this.setupSocketHandlers(socketId);
    }


    /**
     * Setup WebSocket event handlers (transport ONLY)
     */

    setupSocketHandlers(socketId) {
        const socket = this.socket;

        socket.onopen = () => {
            if (socketId !== this.currentSocketId) return;

            this.reconnectAttempts = 0;

            this.lastMessageTime = Date.now();
            this.startHeartbeat();
            this._notifyConnectionChange(true);
        };

        socket.onclose = () => {
            if (socketId !== this.currentSocketId) return;

            this.stopHeartbeat();
            this._notifyConnectionChange(false);

            if (this.shouldReconnect && !this.paused) {
                this.handleReconnect();
            }
        };

        socket.onerror = () => {
            if (socketId !== this.currentSocketId) return;
        };

        socket.onmessage = (event) => {
            if (socketId !== this.currentSocketId) return;

            try {
                const data = JSON.parse(event.data);

                this.lastMessageTime = Date.now();

                if (this.messageCallback) {
                    this.messageCallback(data);
                }
            } catch (err) {
                this._log('INVALID_JSON_MESSAGE', event.data);
            }
        };
    }


    /**
     * Send message via WebSocket (transport ONLY)
     * @param {Object} messageData - Message data to send
     * @returns {boolean} Send success
     */
    send(messageData) {
        this._log('WEBSOCKET_SEND', messageData);

        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            this._log('WEBSOCKET_SEND_FAILED', 'Socket not connected');
            return false;
        }

        try {
            this.socket.send(JSON.stringify(messageData));
            this._log('WEBSOCKET_SEND_SUCCESS');
            return true;
        } catch (error) {
            this._log('WEBSOCKET_SEND_ERROR', error);
            console.error('WebSocketManager: Send error:', error);
            return false;
        }
    }

    /**
     * Disconnect WebSocket
     */
    disconnect() {
        this.shouldReconnect = false;

        this.stopHeartbeat();

        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }

        this._notifyConnectionChange(false);
    }

    /**
     * Handle reconnection logic (transport only)
     */

    handleReconnect() {
        if (this.reconnectAttempts >= 5) return;

        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        this.reconnectAttempts++;

        this.reconnectTimer = setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Get connection status (transport only)
     * @returns {boolean} Is connected
     */
    isConnected() {
        return this.socket && this.socket.readyState === WebSocket.OPEN;
    }

    /**
     * Get ready state (transport only)
     * @returns {number} WebSocket ready state
     */
    getReadyState() {
        return this.socket ? this.socket.readyState : WebSocket.CLOSED;
    }

    /**
     * Notify connection change (transport only)
     * @param {boolean} isConnected - Connection status
     */
    _notifyConnectionChange(isConnected) {
        // Forward to app controller (orchestration only)
        // NO state mutations here
        if (this.connectionCallback) {
            this.connectionCallback(isConnected);
        }
    }

    _forceClose() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[WEBSOCKET] ${action}:`, data);
        }
    }

    /**
     * Get WebSocket status (transport only)
     * @returns {Object} Status information
     */
    getStatus() {
        return {
            connected: this.isConnected(),
            readyState: this.getReadyState(),
            conversationId: this.conversationId,
            reconnectAttempts: this.reconnectAttempts,
            hasReconnectTimer: !!this.reconnectTimer,
            hasMessageCallback: !!this.messageCallback,
            hasConnectionCallback: !!this.connectionCallback
        };
    }

    /**
     * Destroy WebSocket manager
     */
    destroy() {
        this._log('WEBSOCKET_DESTROY');
        this.disconnect();
        this.messageCallback = null;
        this.connectionCallback = null;
        this.conversationId = null;
    }
}



// Create and export singleton instance
export const webSocketManager = new WebSocketManager();
