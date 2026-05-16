/**
 * Groups API Service
 * Centralized API calls for groups domain
 */

import { get, post, patch, del, handleResponse } from '../utils/api.js';

export const groupsAPI = {
  /**
   * Get all groups
   */
  async getGroups() {
    const response = await get('/api/groups/');
    return handleResponse(response);
  },

  /**
   * Get group by ID
   * @param {number} groupId - Group ID
   */
  async getGroup(groupId) {
    const response = await get(`/api/groups/${groupId}/`);
    return handleResponse(response);
  },

  /**
   * Create a new group
   * @param {object} data - Group data
   */
  async createGroup(data) {
    const response = await post('/api/groups/', data);
    return handleResponse(response);
  },

  /**
   * Update group
   * @param {number} groupId - Group ID
   * @param {object} data - Group data
   */
  async updateGroup(groupId, data) {
    const response = await patch(`/api/groups/${groupId}/`, data);
    return handleResponse(response);
  },

  /**
   * Delete group
   * @param {number} groupId - Group ID
   */
  async deleteGroup(groupId) {
    const response = await del(`/api/groups/${groupId}/`);
    return handleResponse(response);
  },

  /**
   * Get group posts
   * @param {number} groupId - Group ID
   */
  async getGroupPosts(groupId) {
    const response = await get(`/api/groups/${groupId}/posts/`);
    return handleResponse(response);
  },

  /**
   * Create group post
   * @param {number} groupId - Group ID
   * @param {object} data - Post data
   */
  async createGroupPost(groupId, data) {
    const response = await post(`/api/groups/${groupId}/posts/`, data);
    return handleResponse(response);
  },

  /**
   * Get group members
   * @param {number} groupId - Group ID
   */
  async getGroupMembers(groupId) {
    const response = await get(`/api/groups/${groupId}/members/`);
    return handleResponse(response);
  },

  /**
   * Add member to group
   * @param {number} groupId - Group ID
   * @param {number} userId - User ID
   */
  async addMember(groupId, userId) {
    const response = await post(`/api/groups/${groupId}/members/`, { user_id: userId });
    return handleResponse(response);
  },

  /**
   * Remove member from group
   * @param {number} groupId - Group ID
   * @param {number} membershipId - Membership ID
   */
  async removeMember(groupId, membershipId) {
    const response = await del(`/api/groups/${groupId}/members/${membershipId}/`);
    return handleResponse(response);
  },

  /**
   * Search users to invite
   * @param {number} groupId - Group ID
   * @param {string} query - Search query
   */
  async searchInviteCandidates(groupId, query) {
    const response = await get(`/api/groups/${groupId}/search/?q=${query}`);
    return handleResponse(response);
  }
};
