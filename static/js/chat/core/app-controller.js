/**
 * AppController - Orchestration ONLY
 * Coordinates module communication following strict SOT data flow
 * MUST NOT compute or mutate state
 * MUST NOT bypass message-service or store
 */

import { store } from './store.js';
import { messageService } from './message-service.js';
import { webSocketManager } from './websocket.js';
import { uiController } from '../ui/ui-controller.js';
import { networkHealthTracker } from '../shared/network-health-tracker.js';

export class AppController {
    constructor() {
        this.initialized = false;
        this.config = null;
        this.debugMode = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
        this.connectionUnsubscribe = null;
    }

    /**
     * Initialize application with strict SOT flow
     * @param {Object} config - Configuration object
     */
    async init(config) {
        if (this.initialized) return;

        this._log('APP_CONTROLLER_INIT', config);
        this.config = config;
        window.__store = store;

        try {
            // Initialize network health tracker
            networkHealthTracker.init();
            
            this._validateSOTInitialization();
            this._setupDataFlowConnections();
            this._setupConnectionMonitoring();

            // We block until history is loaded
            await this._loadInitialMessages();

            this.initialized = true;
            this._log('APP_CONTROLLER_INITIALIZED');

        } catch (error) {
            this._log('APP_CONTROLLER_INIT_ERROR', error);
            console.error(error);
        }
    }

    /**
     * Handle connection change from websocket (orchestration only)
     * @param {boolean} isConnected - Connection status
     */
    handleConnectionChange(isConnected) {
        this._log('CONNECTION_CHANGE', { isConnected });

        // Update store connection state (ONLY store can mutate)
        if (isConnected) {
            store.setConnectionState('connected');
            // Process queued messages through message service
            messageService.processMessageQueue();
            // Send any queued read receipts
            messageService.sendQueuedReadReceipts();
        } else {
            store.setConnectionState('disconnected');
        }
    }

    /**
     * Handle reconnect request (orchestration only)
     */
    handleReconnect() {
        this._log('RECONNECT_REQUESTED');

        // Trigger websocket reconnection (transport ONLY)
        webSocketManager.connect();
    }

    /**
     * Validate SOT initialization order
     */
    _validateSOTInitialization() {
        // Store must be initialized first (SOT)
        if (!store || !store.getState()) {
            throw new Error('Store not initialized - SOT violation');
        }

        // Message service must be initialized (ONLY ingestion layer)
        if (!messageService || !messageService.getStatus().initialized) {
            throw new Error('Message service not initialized - ingestion layer violation');
        }

        // WebSocket must be initialized (transport ONLY)
        if (!webSocketManager) {
            throw new Error('WebSocket not initialized - transport layer violation');
        }

        // UI controller must be initialized (read-only consumer)
        if (!uiController || !uiController.getStatus().initialized) {
            throw new Error('UI controller not initialized - consumer layer violation');
        }

        this._log('SOT_INITIALIZATION_VALIDATED');
    }

    /**
     * Setup mandatory data flow connections
     */
    _setupDataFlowConnections() {
        // Init FIRST (so it doesn't wipe what we're about to set)
        webSocketManager.init(this.config.conversationId);

        // THEN set callbacks
        webSocketManager.setMessageCallback((data) => {
            messageService.processIncomingMessage(data);
        });

        webSocketManager.setConnectionCallback((isConnected) => {
            this.handleConnectionChange(isConnected);
        });

        this._log('DATA_FLOW_CONNECTIONS_SETUP');
    }

    /**
     * Load initial messages through message service
     */
    async _loadInitialMessages() {
        this._log('LOADING_INITIAL_MESSAGES');

        try {
            // 1. stop interference
            console.log('[APP_CONTROLLER] Pausing WebSocket before loading messages');
            webSocketManager.pause();

            // 2. reset store FIRST
            console.log('[APP_CONTROLLER] Resetting store');
            store.reset();

            // 3. load history
            console.log('[APP_CONTROLLER] Loading conversation history for ID:', this.config.conversationId);
            await messageService.loadConversationHistory(
                this.config.conversationId
            );
            console.log('[APP_CONTROLLER] Messages loaded successfully');
            console.log("STATE SNAPSHOT:", store.getState().messages);

            // 4. resume live stream
            console.log('[APP_CONTROLLER] Resuming WebSocket after loading messages');
            webSocketManager.resume();

            this._log('INITIAL_MESSAGES_LOADED');

        } catch (error) {
            console.error('[APP_CONTROLLER] ERROR loading initial messages:', error);
            console.error('[APP_CONTROLLER] Error stack:', error.stack);
            // Still try to resume WebSocket even if loading fails
            console.log('[APP_CONTROLLER] Attempting to resume WebSocket despite error');
            webSocketManager.resume();
        }
    }

    /**
     * Setup connection monitoring (orchestration only)
     */
    _setupConnectionMonitoring() {
        // Monitor connection state changes from store
        this.connectionUnsubscribe = store.subscribe((state) => {
            this._log('STORE_STATE_UPDATE', {
                connectionState: state.connectionState,
                messagesCount: state.messages.length
            });
        });

        this._log('CONNECTION_MONITORING_SETUP');
    }

    /**
     * Get application status (orchestration only)
     * @returns {Object} Application status
     */
    getStatus() {
        return {
            initialized: this.initialized,
            config: this.config,
            sotValidation: this._validateSOTArchitecture(),
            dataFlow: this._validateDataFlow()
        };
    }

    /**
     * Validate SOT architecture (orchestration only)
     * @returns {Object} Validation results
     */
    _validateSOTArchitecture() {
        const results = {
            store: !!store && !!store.getState(),
            messageService: !!messageService && messageService.getStatus().initialized,
            websocket: !!webSocketManager,
            uiController: !!uiController && uiController.getStatus().initialized,
            dataFlowValid: false
        };

        results.dataFlowValid = Object.values(results).every(Boolean);
        return results;
    }

    /**
     * Validate data flow (orchestration only)
     * @returns {Object} Data flow validation
     */
    _validateDataFlow() {
        return {
            websocketToMessageService: !!webSocketManager && typeof webSocketManager.getMessageCallback() === 'function',
            messageServiceToStore: !!messageService && !!store,
            storeToUIController: !!store && !!uiController && !!uiController.getStatus().subscribed,
            uiControllerToRenderer: !!uiController && !!uiController.renderer
        };
    }

    /**
     * Get store (for debugging only)
     * @returns {Object} Store instance
     */
    getStore() {
        return store;
    }

    /**
     * Get message service (for debugging only)
     * @returns {Object} Message service instance
     */
    getMessageService() {
        return messageService;
    }

    /**
     * Get websocket manager (for debugging only)
     * @returns {Object} WebSocket manager instance
     */
    getWebSocketManager() {
        return webSocketManager;
    }

    /**
     * Get UI controller (for debugging only)
     * @returns {Object} UI controller instance
     */
    getUIController() {
        return uiController;
    }

    /**
     * Validate message consistency (orchestration only)
     * @returns {Object} Validation results
     */
    validateMessageConsistency() {
        return messageService.validateConsistency();
    }

    /**
     * Destroy application (orchestration only)
     */
    destroy() {
        this._log('APP_CONTROLLER_DESTROY');

        if (this.connectionUnsubscribe) {
            this.connectionUnsubscribe();
            this.connectionUnsubscribe = null;
        }

        // Destroy components in reverse order
        if (uiController) {
            uiController.destroy();
        }

        if (webSocketManager) {
            webSocketManager.destroy();
        }

        this.initialized = false;
        this.config = null;

        this._log('APP_CONTROLLER_DESTROYED');
    }

    /**
     * Log debug information
     * @param {string} action - Action type
     * @param {*} data - Action data
     */
    _log(action, data) {
        if (this.debugMode) {
            console.log(`[APP_CONTROLLER] ${action}:`, data);
        }
    }
}

// Create and export singleton instance
export const appController = new AppController();
