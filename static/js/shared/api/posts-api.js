/**
 * Posts API Service
 * Centralized API calls for posts domain
 */

import { get, post, patch, del, handleResponse } from '../utils/api.js';

export const postsAPI = {
  /**
   * Get all posts
   */
  async getPosts() {
    const response = await get('/api/posts/');
    return handleResponse(response);
  },

  /**
   * Get post by ID
   * @param {number} postId - Post ID
   */
  async getPost(postId) {
    const response = await get(`/api/posts/${postId}/`);
    return handleResponse(response);
  },

  /**
   * Create a new post
   * @param {object} data - Post data
   */
  async createPost(data) {
    const response = await post('/api/posts/', data);
    return handleResponse(response);
  },

  /**
   * Update post
   * @param {number} postId - Post ID
   * @param {object} data - Post data
   */
  async updatePost(postId, data) {
    const response = await patch(`/api/posts/${postId}/`, data);
    return handleResponse(response);
  },

  /**
   * Delete post
   * @param {number} postId - Post ID
   */
  async deletePost(postId) {
    const response = await del(`/api/posts/${postId}/`);
    return handleResponse(response);
  },

  /**
   * Like post
   * @param {number} postId - Post ID
   */
  async likePost(postId) {
    const response = await post(`/api/posts/${postId}/like/`, {});
    return handleResponse(response);
  },

  /**
   * Unlike post
   * @param {number} postId - Post ID
   */
  async unlikePost(postId) {
    const response = await del(`/api/posts/${postId}/like/`);
    return handleResponse(response);
  },

  /**
   * Get post comments
   * @param {number} postId - Post ID
   */
  async getComments(postId) {
    const response = await get(`/api/posts/${postId}/comments/`);
    return handleResponse(response);
  },

  /**
   * Add comment to post
   * @param {number} postId - Post ID
   * @param {object} data - Comment data
   */
  async addComment(postId, data) {
    const response = await post(`/api/posts/${postId}/comments/`, data);
    return handleResponse(response);
  },

  /**
   * Share post
   * @param {number} postId - Post ID
   * @param {object} data - Share data
   */
  async sharePost(postId, data) {
    const response = await post(`/api/posts/${postId}/share/`, data);
    return handleResponse(response);
  },

  /**
   * Save post (bookmark)
   * @param {number} postId - Post ID
   */
  async savePost(postId) {
    const response = await post(`/api/posts/${postId}/save/`, {});
    return handleResponse(response);
  },

  /**
   * Unsave post
   * @param {number} postId - Post ID
   */
  async unsavePost(postId) {
    const response = await del(`/api/posts/${postId}/save/`);
    return handleResponse(response);
  }
};
