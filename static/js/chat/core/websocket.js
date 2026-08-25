/**
 * WebSocketManager - Pure transport layer
 * NO business logic, NO state awareness, NO UI interaction
 * Pure WebSocket connection and message forwarding only
 */

export class WebSocketManager {
    constructor() {
        this.socket = null;
        this.conversationId = null;
        this.customWsUrl = null;
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
        this.lastHeartbeatTime = Date.now();
        this.reconnectInProgress = false;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.HEARTBEAT_TIMEOUT_MS = 90000; // 90 seconds - allow some buffer beyond server's 60s timeout
        this.HEARTBEAT_SEND_INTERVAL_MS = 25000; // 25 seconds - send proactive heartbeat
        this.proactiveHeartbeatInterval = null;
    }

    /**
     * Initialize WebSocket connection
     * @param {number} conversationId - Conversation ID
     * @param {string} customWsUrl - Optional custom WebSocket URL (for group chats)
     */
    init(conversationId, customWsUrl = null) {
        this._log('WEBSOCKET_INIT', { conversationId, customWsUrl });
        
        this.conversationId = conversationId;
        this.customWsUrl = customWsUrl;
        
        this.connect();
    }


    startHeartbeat() {
        this.stopHeartbeat();

        // Start proactive heartbeat sender (client-initiated)
        this.proactiveHeartbeatInterval = setInterval(() => {
            if (!this.isConnected()) return;

            // Send proactive heartbeat to server for presence tracking
            this.send({ type: 'heartbeat' });
            this._log('HEARTBEAT_SENT');
        }, this.HEARTBEAT_SEND_INTERVAL_MS);

        // Start heartbeat monitor (check for server ping/pong)
        this.heartbeatInterval = setInterval(() => {
            if (!this.isConnected()) return;

            const now = Date.now();
            const heartbeatAge = now - this.lastHeartbeatTime;

            // Check if heartbeat is lost (3-minute timeout)
            if (heartbeatAge > this.HEARTBEAT_TIMEOUT_MS) {
                this._log('HEARTBEAT_LOST', { heartbeatAge });
                console.warn('[WS] Heartbeat lost — reconnecting');
                this.disconnect();
                setTimeout(() => {
                    this.connect();
                }, 500);
                return;
            }

        }, 10000);
    }

    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
        if (this.proactiveHeartbeatInterval) {
            clearInterval(this.proactiveHeartbeatInterval);
            this.proactiveHeartbeatInterval = null;
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
        
        // Use custom WebSocket URL for group chats, otherwise use default direct chat URL
        const wsUrl = this.customWsUrl 
            ? `${this.customWsUrl}`
            : `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;

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
            this.reconnectInProgress = false;

            this.lastMessageTime = Date.now();
            this.lastHeartbeatTime = Date.now();
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
                console.group('[WEBSOCKET] ========== MESSAGE RECEIVED ==========');
                console.log('[WEBSOCKET] Raw data:', event.data);
                console.log('[WEBSOCKET] Parsed data:', JSON.stringify(data, null, 2));

                this.lastMessageTime = Date.now();

                // Handle ping/pong heartbeat
                if (data.type === 'ping') {
                    this.send({ type: 'pong' });
                    this.lastHeartbeatTime = Date.now();
                    this._log('HEARTBEAT_RECEIVED');
                    console.groupEnd();
                    return;
                }

                console.log('[WEBSOCKET] Calling messageCallback:', !!this.messageCallback);
                if (this.messageCallback) {
                    // Fault tolerance: Wrap callback in try-catch to prevent pipeline crashes
                    try {
                        this.messageCallback(data);
                    } catch (error) {
                        console.error('[WEBSOCKET] CRITICAL: Message callback failed:', error);
                        console.error('[WEBSOCKET] Error stack:', error.stack);
                        console.error('[WEBSOCKET] Message data that caused error:', data);
                        // WebSocket connection survives - never crash the pipeline
                    }
                } else {
                    console.error('[WEBSOCKET] ERROR: messageCallback is not set!');
                }
            } catch (err) {
                console.error('[WEBSOCKET] ERROR parsing message:', err, event.data);
                this._log('INVALID_JSON_MESSAGE', event.data);
                // WebSocket connection survives parsing errors
            } finally {
                console.groupEnd();
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
     * Destroy WebSocket manager
     */
    destroy() {
        this._log('WEBSOCKET_DESTROY');
        this.disconnect();
        this.messageCallback = null;
        this.connectionCallback = null;
        this.conversationId = null;
    }

    /**
     * Handle reconnection logic (transport only)
     */

    handleReconnect() {
        if (this.reconnectInProgress) return;
        if (this.reconnectAttempts >= 5) return;

        this.reconnectInProgress = true;
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
