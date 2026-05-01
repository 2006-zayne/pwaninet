/**
 * WebSocket - WebSocket connection management
 * ONLY handles socket lifecycle, emits events via EventBus
 * NO DOM or UI manipulation
 */

import { EVENTS, RECONNECT_CONFIG } from '../shared/constants.js';
import { eventBus } from './event-bus.js';

export class WebSocketManager {
  constructor() {
    this.socket = null;
    this.conversationId = null;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
  }

  /**
   * Initialize WebSocket connection
   * @param {number} conversationId - Conversation ID
   */
  connect(conversationId) {
    if (this.socket) {
      this.disconnect();
    }

    this.conversationId = conversationId;
    this.reconnectAttempts = 0;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${this.conversationId}/`;

    try {
      this.socket = new WebSocket(wsUrl);
      this.setupSocketHandlers();
    } catch (error) {
      console.error('WebSocket connection error:', error);
      eventBus.emit(EVENTS.WEBSOCKET_ERROR, error);
    }
  }

  /**
   * Setup WebSocket event handlers
   */
  setupSocketHandlers() {
    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      eventBus.emit(EVENTS.WEBSOCKET_CONNECTED);
    };

    this.socket.onmessage = (event) => {
      this.handleMessage(event.data);
    };

    this.socket.onclose = (event) => {
      eventBus.emit(EVENTS.WEBSOCKET_DISCONNECTED, { code: event.code, reason: event.reason });
      this.scheduleReconnect();
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      eventBus.emit(EVENTS.WEBSOCKET_ERROR, error);
    };
  }

  /**
   * Handle incoming WebSocket message
   * @param {string} data - Message data
   */
  handleMessage(data) {
    try {
      const parsed = JSON.parse(data);
      eventBus.emit(parsed.type, parsed.data || parsed);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Send message via WebSocket
   * @param {Object} data - Data to send
   */
  send(data) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket not connected, message queued');
      return false;
    }

    try {
      this.socket.send(JSON.stringify(data));
      return true;
    } catch (error) {
      console.error('Failed to send WebSocket message:', error);
      return false;
    }
  }

  /**
   * Schedule reconnection attempt
   */
  scheduleReconnect() {
    if (this.reconnectAttempts >= RECONNECT_CONFIG.MAX_ATTEMPTS) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      RECONNECT_CONFIG.BASE_DELAY * Math.pow(RECONNECT_CONFIG.BACKOFF_MULTIPLIER, this.reconnectAttempts - 1),
      RECONNECT_CONFIG.MAX_DELAY
    );

    eventBus.emit(EVENTS.WEBSOCKET_RECONNECTING, { attempt: this.reconnectAttempts, delay });

    this.reconnectTimer = setTimeout(() => {
      this.connect(this.conversationId);
    }, delay);
  }

  /**
   * Cancel reconnection
   */
  cancelReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    this.cancelReconnect();

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }

    this.reconnectAttempts = 0;
  }

  /**
   * Get connection state
   * @returns {string} Connection state
   */
  getState() {
    if (!this.socket) return 'CLOSED';

    switch (this.socket.readyState) {
      case WebSocket.CONNECTING:
        return 'CONNECTING';
      case WebSocket.OPEN:
        return 'OPEN';
      case WebSocket.CLOSING:
        return 'CLOSING';
      case WebSocket.CLOSED:
        return 'CLOSED';
      default:
        return 'UNKNOWN';
    }
  }

  /**
   * Check if connected
   * @returns {boolean} Is connected
   */
  isConnected() {
    return this.socket && this.socket.readyState === WebSocket.OPEN;
  }
}

// Create global instance
export const webSocketManager = new WebSocketManager();
