/**
 * Comment API Module
 * Handles all API calls for comments and replies
 */
const CommentApi = {
  /**
   * Create a new comment
   */
  async createComment(postId, content, parentCommentId = null) {
    const url = parentCommentId 
      ? `/api/comments/${parentCommentId}/reply/`
      : '/api/comments/';
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken()
      },
      body: JSON.stringify({
        post: postId,
        content: content
      })
    });
    
    if (!response.ok) {
      throw new Error('Failed to create comment');
    }
    
    return response.json();
  },

  /**
   * Get replies for a comment
   */
  async getReplies(commentId, page = 1, pageSize = 10) {
    const url = `/api/comments/${commentId}/replies/?page=${page}&page_size=${pageSize}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error('Failed to load replies');
    }
    
    return response.json();
  },

  /**
   * Toggle like on a comment
   */
  async toggleLike(commentId) {
    const response = await fetch(`/api/comments/${commentId}/like/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': this.getCsrfToken()
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to toggle like');
    }
    
    return response.json();
  },

  /**
   * Update a comment
   */
  async updateComment(commentId, content) {
    const response = await fetch(`/api/comments/${commentId}/`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCsrfToken()
      },
      body: JSON.stringify({ content })
    });
    
    if (!response.ok) {
      throw new Error('Failed to update comment');
    }
    
    return response.json();
  },

  /**
   * Delete a comment
   */
  async deleteComment(commentId) {
    const response = await fetch(`/api/comments/${commentId}/`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': this.getCsrfToken()
      }
    });
    
    if (!response.ok) {
      throw new Error('Failed to delete comment');
    }
    
    return true;
  },

  /**
   * Get CSRF token from meta tag or cookie
   */
  getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) {
      return metaTag.getAttribute('content');
    }
    
    // Fallback to cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') {
        return decodeURIComponent(value);
      }
    }
    
    return '';
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommentApi;
}
