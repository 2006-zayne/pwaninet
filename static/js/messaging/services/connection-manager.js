/**
 * Connection Manager
 * 
 * Manages WebSocket connections across multiple tabs/devices.
 * Prevents duplicate socket handling and tracks active user connections.
 */

class ConnectionManager {
    constructor() {
        this.tabId = this.generateTabId();
        this.isActive = false;
        this.connectionCount = 0;
        this.lastHeartbeat = Date.now();
        this.heartbeatInterval = null;
        this.broadcastChannel = null;
        
        // Storage keys
        this.STORAGE_KEY = 'pwaninet_connection_state';
        this.HEARTBEAT_KEY = 'pwaninet_heartbeat';
        
        // Broadcast channel for cross-tab communication
        this.BROADCAST_CHANNEL = 'pwaninet_connections';
        
        // Heartbeat interval (5 seconds)
        this.HEARTBEAT_INTERVAL = 5000;
        
        // Connection timeout (15 seconds)
        this.CONNECTION_TIMEOUT = 15000;
        
        this.init();
    }
    
    /**
     * Initialize connection manager
     */
    init() {
        // Setup broadcast channel
        this.setupBroadcastChannel();
        
        // Start heartbeat
        this.startHeartbeat();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => this.cleanup());
        
        // Listen for storage events (for cross-tab sync)
        window.addEventListener('storage', (event) => this.handleStorageEvent(event));
        
        console.log(`[CONNECTION_MANAGER] Initialized with tab ID: ${this.tabId}`);
    }
    
    /**
     * Generate unique tab ID
     */
    generateTabId() {
        return `tab_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Setup broadcast channel for cross-tab communication
     */
    setupBroadcastChannel() {
        if ('BroadcastChannel' in window) {
            this.broadcastChannel = new BroadcastChannel(this.BROADCAST_CHANNEL);
            
            this.broadcastChannel.onmessage = (event) => {
                this.handleBroadcastMessage(event.data);
            };
        }
    }
    
    /**
     * Handle broadcast messages from other tabs
     */
    handleBroadcastMessage(data) {
        const { type, tabId, payload } = data;
        
        // Ignore messages from this tab
        if (tabId === this.tabId) return;
        
        switch (type) {
            case 'heartbeat':
                this.handleRemoteHeartbeat(tabId, payload);
                break;
            case 'connection_request':
                this.handleConnectionRequest(tabId, payload);
                break;
            case 'connection_granted':
                this.handleConnectionGranted(tabId, payload);
                break;
            case 'connection_denied':
                this.handleConnectionDenied(tabId, payload);
                break;
            case 'tab_closed':
                this.handleTabClosed(tabId);
                break;
        }
    }
    
    /**
     * Handle storage events
     */
    handleStorageEvent(event) {
        if (event.key === this.HEARTBEAT_KEY) {
            this.handleRemoteHeartbeat(null, JSON.parse(event.newValue));
        }
    }
    
    /**
     * Start heartbeat to signal this tab is active
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            this.sendHeartbeat();
        }, this.HEARTBEAT_INTERVAL);
        
        // Send initial heartbeat
        this.sendHeartbeat();
    }
    
    /**
     * Send heartbeat signal
     */
    sendHeartbeat() {
        const heartbeat = {
            tabId: this.tabId,
            timestamp: Date.now(),
            isActive: this.isActive,
            connectionCount: this.connectionCount
        };
        
        // Store in localStorage (fallback for browsers without BroadcastChannel)
        localStorage.setItem(this.HEARTBEAT_KEY, JSON.stringify(heartbeat));
        
        // Send via broadcast channel
        if (this.broadcastChannel) {
            this.broadcastChannel.postMessage({
                type: 'heartbeat',
                tabId: this.tabId,
                payload: heartbeat
            });
        }
        
        this.lastHeartbeat = Date.now();
    }
    
    /**
     * Handle heartbeat from remote tab
     */
    handleRemoteHeartbeat(tabId, heartbeat) {
        // Update connection state
        this.updateConnectionState(heartbeat);
        
        // Check if this tab should be active
        this.checkTabPriority();
    }
    
    /**
     * Update connection state from remote heartbeat
     */
    updateConnectionState(heartbeat) {
        const state = this.getConnectionState();
        
        // Update or add this tab's heartbeat
        state.tabs[heartbeat.tabId] = {
            timestamp: heartbeat.timestamp,
            isActive: heartbeat.isActive,
            connectionCount: heartbeat.connectionCount
        };
        
        // Clean up stale tabs
        const now = Date.now();
        Object.keys(state.tabs).forEach(tabId => {
            if (now - state.tabs[tabId].timestamp > this.CONNECTION_TIMEOUT) {
                delete state.tabs[tabId];
            }
        });
        
        state.lastUpdated = now;
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
    }
    
    /**
     * Get connection state from localStorage
     */
    getConnectionState() {
        try {
            const state = localStorage.getItem(this.STORAGE_KEY);
            return state ? JSON.parse(state) : { tabs: {}, lastUpdated: Date.now() };
        } catch (error) {
            console.error('[CONNECTION_MANAGER] Failed to get connection state:', error);
            return { tabs: {}, lastUpdated: Date.now() };
        }
    }
    
    /**
     * Check if this tab should be the active connection
     */
    checkTabPriority() {
        const state = this.getConnectionState();
        const tabs = Object.keys(state.tabs);
        
        if (tabs.length === 0) {
            // No other tabs, this tab should be active
            this.setActive(true);
            return;
        }
        
        // Find the oldest active tab
        let oldestTab = null;
        let oldestTimestamp = Infinity;
        
        for (const tabId of tabs) {
            const tab = state.tabs[tabId];
            if (tab.isActive && tab.timestamp < oldestTimestamp) {
                oldestTimestamp = tab.timestamp;
                oldestTab = tabId;
            }
        }
        
        // This tab should be active if it's the oldest
        this.setActive(oldestTab === this.tabId || !oldestTab);
    }
    
    /**
     * Set this tab as active/inactive
     */
    setActive(isActive) {
        if (this.isActive === isActive) return;
        
        this.isActive = isActive;
        
        if (isActive) {
            console.log('[CONNECTION_MANAGER] This tab is now the active connection');
            this.emitConnectionGranted();
        } else {
            console.log('[CONNECTION_MANAGER] This tab is now passive');
            this.emitConnectionDenied();
        }
        
        // Update heartbeat
        this.sendHeartbeat();
    }
    
    /**
     * Request to become the active connection
     */
    requestActiveConnection() {
        if (this.broadcastChannel) {
            this.broadcastChannel.postMessage({
                type: 'connection_request',
                tabId: this.tabId,
                payload: { timestamp: Date.now() }
            });
        }
        
        // Check priority immediately
        this.checkTabPriority();
    }
    
    /**
     * Handle connection request from another tab
     */
    handleConnectionRequest(tabId, payload) {
        // This tab will handle this via the heartbeat mechanism
        // No explicit response needed
    }
    
    /**
     * Handle connection granted
     */
    handleConnectionGranted(tabId, payload) {
        console.log(`[CONNECTION_MANAGER] Connection granted by tab ${tabId}`);
    }
    
    /**
     * Handle connection denied
     */
    handleConnectionDenied(tabId, payload) {
        console.log(`[CONNECTION_MANAGER] Connection denied by tab ${tabId}`);
    }
    
    /**
     * Handle tab closed
     */
    handleTabClosed(tabId) {
        const state = this.getConnectionState();
        delete state.tabs[tabId];
        state.lastUpdated = Date.now();
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
        
        // Check if this tab should become active
        this.checkTabPriority();
    }
    
    /**
     * Increment connection count
     */
    incrementConnectionCount() {
        this.connectionCount++;
        this.sendHeartbeat();
    }
    
    /**
     * Decrement connection count
     */
    decrementConnectionCount() {
        this.connectionCount = Math.max(0, this.connectionCount - 1);
        this.sendHeartbeat();
    }
    
    /**
     * Get total connection count across all tabs
     */
    getTotalConnectionCount() {
        const state = this.getConnectionState();
        let total = 0;
        
        for (const tabId in state.tabs) {
            total += state.tabs[tabId].connectionCount || 0;
        }
        
        return total;
    }
    
    /**
     * Get active tab count
     */
    getActiveTabCount() {
        const state = this.getConnectionState();
        let count = 0;
        
        for (const tabId in state.tabs) {
            if (state.tabs[tabId].isActive) {
                count++;
            }
        }
        
        return count;
    }
    
    /**
     * Check if this tab is the active connection
     */
    isTabActive() {
        return this.isActive;
    }
    
    /**
     * Get connection manager state
     */
    getState() {
        const state = this.getConnectionState();
        return {
            tabId: this.tabId,
            isActive: this.isActive,
            connectionCount: this.connectionCount,
            totalConnections: this.getTotalConnectionCount(),
            activeTabs: this.getActiveTabCount(),
            allTabs: state.tabs
        };
    }
    
    /**
     * Emit connection granted event
     */
    emitConnectionGranted() {
        const event = new CustomEvent('connectionGranted', {
            detail: { tabId: this.tabId }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Emit connection denied event
     */
    emitConnectionDenied() {
        const event = new CustomEvent('connectionDenied', {
            detail: { tabId: this.tabId }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Emit connection state change event
     */
    emitStateChange() {
        const event = new CustomEvent('connectionStateChange', {
            detail: this.getState()
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Listen for connection events
     */
    onConnectionGranted(callback) {
        window.addEventListener('connectionGranted', (event) => {
            callback(event.detail);
        });
    }
    
    onConnectionDenied(callback) {
        window.addEventListener('connectionDenied', (event) => {
            callback(event.detail);
        });
    }
    
    onStateChange(callback) {
        window.addEventListener('connectionStateChange', (event) => {
            callback(event.detail);
        });
    }
    
    /**
     * Cleanup resources
     */
    cleanup() {
        // Stop heartbeat
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
        
        // Remove this tab from connection state
        const state = this.getConnectionState();
        delete state.tabs[this.tabId];
        state.lastUpdated = Date.now();
        localStorage.setItem(this.STORAGE_KEY, JSON.stringify(state));
        
        // Notify other tabs
        if (this.broadcastChannel) {
            this.broadcastChannel.postMessage({
                type: 'tab_closed',
                tabId: this.tabId,
                payload: {}
            });
            this.broadcastChannel.close();
        }
        
        console.log('[CONNECTION_MANAGER] Cleanup complete');
    }
}

// Export singleton instance
const connectionManager = new ConnectionManager();
export default connectionManager;
