/**
 * Messaging API Service
 * Centralized API calls for messaging domain
 */

import { get, post, patch, del, handleResponse } from '../utils/api.js';

export const messagingAPI = {
  /**
   * Get all conversations
   */
  async getConversations() {
    const response = await get('/messaging/v1/conversations/');
    return handleResponse(response);
  },

  /**
   * Get conversation by ID
   * @param {number} conversationId - Conversation ID
   */
  async getConversation(conversationId) {
    const response = await get(`/messaging/v1/conversations/${conversationId}/`);
    return handleResponse(response);
  },

  /**
   * Create a new conversation
   * @param {object} data - Conversation data
   */
  async createConversation(data) {
    const response = await post('/messaging/v1/conversations/', data);
    return handleResponse(response);
  },

  /**
   * Get messages for a conversation
   * @param {number} conversationId - Conversation ID
   */
  async getMessages(conversationId) {
    const response = await get(`/messaging/v1/conversations/${conversationId}/messages/`);
    return handleResponse(response);
  },

  /**
   * Send a message
   * @param {number} conversationId - Conversation ID
   * @param {object} data - Message data
   */
  async sendMessage(conversationId, data) {
    const response = await post(`/messaging/v1/conversations/${conversationId}/messages/`, data);
    return handleResponse(response);
  },

  /**
   * Get theme for conversation
   * @param {number} conversationId - Conversation ID
   */
  async getTheme(conversationId) {
    const response = await get(`/api/messaging/themes/?conversation=${conversationId}`);
    return handleResponse(response);
  },

  /**
   * Save theme for conversation
   * @param {object} data - Theme data
   */
  async saveTheme(data) {
    const existingTheme = await this.getTheme(data.conversation);
    let url, method;
    
    if (existingTheme.results && existingTheme.results[0]) {
      url = `/api/messaging/themes/${existingTheme.results[0].id}/`;
      method = patch;
    } else {
      url = '/api/messaging/themes/';
      method = post;
    }
    
    const response = await method(url, data);
    return handleResponse(response);
  },

  /**
   * Mark conversation as read
   * @param {number} conversationId - Conversation ID
   */
  async markAsRead(conversationId) {
    const response = await post(`/messaging/v1/conversations/${conversationId}/mark_read/`, {});
    return handleResponse(response);
  },

  /**
   * Start typing indicator
   * @param {number} conversationId - Conversation ID
   */
  async startTyping(conversationId) {
    const response = await post(`/messaging/v1/conversations/${conversationId}/typing/`, { typing: true });
    return handleResponse(response);
  },

  /**
   * Stop typing indicator
   * @param {number} conversationId - Conversation ID
   */
  async stopTyping(conversationId) {
    const response = await post(`/messaging/v1/conversations/${conversationId}/typing/`, { typing: false });
    return handleResponse(response);
  }
};
