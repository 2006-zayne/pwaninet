/**
 * Users API Service
 * Centralized API calls for users domain
 */

import { get, post, patch, del, handleResponse } from '../utils/api.js';

export const usersAPI = {
  /**
   * Get user by ID
   * @param {number} userId - User ID
   */
  async getUser(userId) {
    const response = await get(`/api/users/${userId}/`);
    return handleResponse(response);
  },

  /**
   * Get current user profile
   */
  async getCurrentUser() {
    const response = await get('/api/users/me/');
    return handleResponse(response);
  },

  /**
   * Update user profile
   * @param {object} data - Profile data
   */
  async updateProfile(data) {
    const response = await patch('/api/users/me/', data);
    return handleResponse(response);
  },

  /**
   * Follow a user
   * @param {number} userId - User ID
   */
  async followUser(userId) {
    const response = await post(`/api/follows/${userId}/follow/`, {});
    return handleResponse(response);
  },

  /**
   * Unfollow a user
   * @param {number} userId - User ID
   */
  async unfollowUser(userId) {
    const response = await del(`/api/follows/${userId}/follow/`);
    return handleResponse(response);
  },

  /**
   * Get user's followers
   * @param {number} userId - User ID
   */
  async getFollowers(userId) {
    const response = await get(`/api/users/${userId}/followers/`);
    return handleResponse(response);
  },

  /**
   * Get user's following
   * @param {number} userId - User ID
   */
  async getFollowing(userId) {
    const response = await get(`/api/users/${userId}/following/`);
    return handleResponse(response);
  },

  /**
   * Search users
   * @param {string} query - Search query
   */
  async searchUsers(query) {
    const response = await get(`/api/users/?q=${query}`);
    return handleResponse(response);
  },

  /**
   * Block a user
   * @param {number} userId - User ID
   */
  async blockUser(userId) {
    const response = await post(`/api/users/${userId}/block/`, {});
    return handleResponse(response);
  },

  /**
   * Unblock a user
   * @param {number} userId - User ID
   */
  async unblockUser(userId) {
    const response = await del(`/api/users/${userId}/block/`);
    return handleResponse(response);
  }
};
