/**
 * Network Health Tracker
 * 
 * Tracks network health state for premium UX decisions.
 * Considers multiple factors: websocket state, heartbeat failures, reconnect attempts, offline status.
 * Used to determine when to show queued icon vs hide it for fast transitions.
 */

export class NetworkHealthTracker {
    constructor() {
        this.isOnline = navigator.onLine;
        this.isWebSocketConnected = false;
        this.isReconnecting = false;
        this.heartbeatFailed = false;
        this.reconnectAttempts = 0;
        this.lastHeartbeatTime = Date.now();
        this.highLatency = false;
        
        // Thresholds
        this.HEARTBEAT_TIMEOUT_MS = 30000; // 30 seconds
        this.HIGH_LATENCY_THRESHOLD_MS = 2000; // 2 seconds
    }

    /**
     * Initialize tracker with event listeners
     */
    init() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            this.isOnline = true;
            this._log('NETWORK_ONLINE');
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            this._log('NETWORK_OFFLINE');
        });

        // Listen for WebSocket events
        window.addEventListener('websocket:connected', () => {
            this.isWebSocketConnected = true;
            this.isReconnecting = false;
            this.reconnectAttempts = 0;
            this.heartbeatFailed = false;
            this.lastHeartbeatTime = Date.now();
            this._log('WEBSOCKET_CONNECTED');
        });

        window.addEventListener('websocket:disconnected', () => {
            this.isWebSocketConnected = false;
            this._log('WEBSOCKET_DISCONNECTED');
        });

        window.addEventListener('websocket:reconnecting', () => {
            this.isReconnecting = true;
            this.reconnectAttempts++;
            this._log('WEBSOCKET_RECONNECTING', { attempts: this.reconnectAttempts });
        });

        // Listen for heartbeat events (if any)
        window.addEventListener('heartbeat:received', () => {
            this.lastHeartbeatTime = Date.now();
            this.heartbeatFailed = false;
        });

        window.addEventListener('heartbeat:failed', () => {
            this.heartbeatFailed = true;
            this._log('HEARTBEAT_FAILED');
        });
    }

    /**
     * Check if network is healthy for fast transitions
     * @returns {boolean} True if network is healthy
     */
    isNetworkHealthy() {
        // If offline, not healthy
        if (!this.isOnline) {
            return false;
        }

        // If websocket disconnected, not healthy
        if (!this.isWebSocketConnected) {
            return false;
        }

        // If reconnecting, not healthy
        if (this.isReconnecting) {
            return false;
        }

        // If heartbeat failed, not healthy
        if (this.heartbeatFailed) {
            return false;
        }

        // Check heartbeat age
        const heartbeatAge = Date.now() - this.lastHeartbeatTime;
        if (heartbeatAge > this.HEARTBEAT_TIMEOUT_MS) {
            return false;
        }

        // If high latency, not healthy
        if (this.highLatency) {
            return false;
        }

        // If multiple reconnect attempts, not healthy
        if (this.reconnectAttempts > 2) {
            return false;
        }

        return true;
    }

    /**
     * Check if queued icon should be visible
     * @param {number} queuedDurationMs - Duration in queued state (ms)
     * @returns {boolean} True if queued icon should be visible
     */
    shouldShowQueuedIcon(queuedDurationMs) {
        // If network is unhealthy, always show queued icon
        if (!this.isNetworkHealthy()) {
            return true;
        }

        // If network is healthy, only show if queued duration exceeds threshold
        return queuedDurationMs >= this.SHOW_QUEUE_ICON_AFTER_MS || 400;
    }

    /**
     * Update high latency state
     * @param {boolean} isHighLatency - Whether latency is high
     */
    setHighLatency(isHighLatency) {
        this.highLatency = isHighLatency;
        this._log('HIGH_LATENCY', { isHighLatency });
    }

    /**
     * Update heartbeat time manually
     * @param {number} timestamp - Heartbeat timestamp
     */
    updateHeartbeat(timestamp) {
        this.lastHeartbeatTime = timestamp;
    }

    /**
     * Get current health status
     * @returns {Object} Health status object
     */
    getHealthStatus() {
        return {
            isOnline: this.isOnline,
            isWebSocketConnected: this.isWebSocketConnected,
            isReconnecting: this.isReconnecting,
            heartbeatFailed: this.heartbeatFailed,
            reconnectAttempts: this.reconnectAttempts,
            heartbeatAge: Date.now() - this.lastHeartbeatTime,
            highLatency: this.highLatency,
            isHealthy: this.isNetworkHealthy()
        };
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.log(`[NETWORK_HEALTH] ${action}:`, data);
        }
    }
}

// Export singleton instance
export const networkHealthTracker = new NetworkHealthTracker();
