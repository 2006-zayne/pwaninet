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
        if (this.socket) {
            this.disconnect();
        }
    }

    /**
     * Resume WebSocket connection (after loading initial messages)
     */
    resume() {
        console.log('[WEBSOCKET] Resuming WebSocket');
        this.paused = false;
        this.connect();
    }

    /**
     * Connect to WebSocket
     */
    connect() {
        if (this.socket) {
            this.disconnect();
        }

        this.reconnectAttempts = 0;

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;

        try {
            this._log('WEBSOCKET_CONNECTING', { wsUrl });
            this.socket = new WebSocket(wsUrl);
            this.setupSocketHandlers();
        } catch (error) {
            this._log('WEBSOCKET_CONNECTION_ERROR', error);
            console.error('WebSocketManager: Connection error:', error);
            this._notifyConnectionChange(false);
        }
    }

    /**
     * Setup WebSocket event handlers (transport ONLY)
     */
    setupSocketHandlers() {
        this.socket.onopen = () => {
            this._log('WEBSOCKET_CONNECTED');
            this.reconnectAttempts = 0;
            this._notifyConnectionChange(true);
        };

        this.socket.onclose = (event) => {
            this._log('WEBSOCKET_DISCONNECTED', { code: event.code, reason: event.reason });
            this._notifyConnectionChange(false);
            this.handleReconnect();
        };

        this.socket.onerror = (error) => {
            this._log('WEBSOCKET_ERROR', error);
            console.error('WebSocketManager: Socket error:', error);
        };

        this.socket.onmessage = (event) => {
            this._log('WEBSOCKET_MESSAGE_RECEIVED');
            
            try {
                const data = JSON.parse(event.data);
                console.log('[WEBSOCKET] Received message:', data);
                
                // Forward to message service (ONLY ingestion layer)
                // NO direct state updates, NO UI updates, NO business logic
                if (this.messageCallback) {
                    this.messageCallback(data);
                } else {
                    this._log('NO_MESSAGE_CALLBACK_SET', data);
                }
                
            } catch (error) {
                this._log('WEBSOCKET_MESSAGE_PARSE_ERROR', { error, data: event.data });
                console.error('WebSocketManager: Failed to parse message:', error);
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
        this._log('WEBSOCKET_DISCONNECT');

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
        if (this.reconnectAttempts >= 5) {
            this._log('WEBSOCKET_RECONNECT_FAILED', 'Max attempts reached');
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
        this.reconnectAttempts++;

        this._log('WEBSOCKET_RECONNECT_SCHEDULED', { attempt: this.reconnectAttempts, delay });

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
