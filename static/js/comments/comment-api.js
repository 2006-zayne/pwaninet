/**
 * Comment API Module
 * Handles all API calls for comments and replies
 */
const CommentApi = {
  /**
   * Create a new comment
   */
  async createComment(postId, content, parentCommentId = null, attachment = null, photoFile = null) {
    const url = parentCommentId 
      ? `/api/comments/${parentCommentId}/reply/`
      : '/api/comments/';
    
    const csrfToken = this.getCsrfToken();
    const file = photoFile || attachment?.file || attachment?.image_file;

    let response;
    if (file instanceof File || file instanceof Blob) {
      const formData = new FormData();
      formData.append('post', postId);
      formData.append('content', content || '');
      formData.append('attachment_image', file);
      formData.append('attachment_type', (attachment && attachment.type) ? attachment.type : 'image');
      if (parentCommentId) formData.append('parent_comment', parentCommentId);
      if (attachment?.url) formData.append('attachment_url', attachment.url);
      if (attachment?.meta) {
        formData.append('attachment_meta', typeof attachment.meta === 'string' ? attachment.meta : JSON.stringify(attachment.meta));
      }

      response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken
        },
        body: formData
      });
    } else {
      const payload = {
        post: postId,
        content: content || ''
      };

      if (attachment) {
        if (attachment.type) payload.attachment_type = attachment.type;
        if (attachment.url) payload.attachment_url = attachment.url;
        if (attachment.meta) payload.attachment_meta = attachment.meta;
      }

      response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(payload)
      });
    }
    
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
      const val = metaTag.getAttribute('content')?.trim();
      if (val && !val.includes('{{')) return val;
    }

    const formInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (formInput && formInput.value) return formInput.value;
    
    // Fallback to cookie
    try {
      if (document.cookie) {
        const cookies = document.cookie.split(';');
        let localToken = '';
        let defaultToken = '';
        for (let cookie of cookies) {
          const [name, value] = cookie.trim().split('=');
          if (name === 'pwaninet_local_csrftoken') {
            localToken = decodeURIComponent(value || '');
          } else if (name === 'csrftoken') {
            defaultToken = decodeURIComponent(value || '');
          }
        }
        if (localToken) return localToken;
        if (defaultToken) return defaultToken;
      }
    } catch (_) {}
    
    return '';
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommentApi;
}
