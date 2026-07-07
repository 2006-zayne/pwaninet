/**
 * Comment Renderer Module
 * Handles rendering of comments and replies
 */
const CommentRenderer = {
  /**
   * Render a single comment
   */
  renderComment(commentData, options = {}) {
    const {
      isReply = false,
      nestingLevel = 0,
      showActions = true,
      currentUser = null
    } = options;

    const isOwner = currentUser && commentData.author.id === currentUser.id;
    const avatarUrl = commentData.author.profile_pic || '/static/images/default_user.jpg';
    const authorName = commentData.author.full_name || commentData.author.username;
    const timestamp = this.formatTimestamp(commentData.created_at);
    const replyCount = commentData.reply_count || 0;

    const commentHtml = `
      <div class="comment-item ${isReply ? 'reply-item' : ''} ${nestingLevel > 1 ? `reply-item--level-${nestingLevel}` : ''}" 
           id="comment-${commentData.id}"
           data-comment-id="${commentData.id}"
           data-parent-id="${commentData.parent_comment_id || ''}"
           data-reply-count="${replyCount}">
        
        <a href="/users/${commentData.author.username}/" class="comment-avatar-link">
          <img src="${avatarUrl}" 
               alt="${authorName}" 
               class="comment-avatar"
               loading="lazy">
        </a>
        
        <div class="comment-content">
          <div class="comment-header">
            <a href="/users/${commentData.author.username}/" class="comment-author-link">
              ${authorName}
            </a>
            <span class="comment-timestamp">${timestamp}</span>
          </div>
          
          <div class="comment-body" id="comment-body-${commentData.id}">
            ${this.escapeHtml(commentData.content)}
          </div>
          
          ${showActions ? this.renderActions(commentData, isOwner, replyCount) : ''}
          
          ${replyCount > 0 ? this.renderReplyToggle(commentData.id, replyCount) : ''}
        </div>
      </div>
    `;

    return commentHtml;
  },

  /**
   * Render comment actions
   */
  renderActions(commentData, isOwner, replyCount) {
    const likeClass = commentData.is_liked ? 'liked' : '';
    const likeIcon = commentData.is_liked ? 'bi-heart-fill' : 'bi-heart';

    return `
      <div class="comment-actions">
        <button class="comment-action ${likeClass}" 
                data-action="like"
                data-comment-id="${commentData.id}"
                aria-label="Like comment">
          <i class="bi ${likeIcon}"></i>
          <span>${commentData.like_count || 0}</span>
        </button>
        
        <button class="comment-action" 
                data-action="reply"
                data-comment-id="${commentData.id}"
                aria-label="Reply to comment">
          <i class="bi bi-chat-dots"></i>
          Reply
        </button>
        
        <button class="comment-menu-btn" 
                data-action="menu"
                data-comment-id="${commentData.id}"
                aria-label="More options"
                aria-expanded="false">
          <i class="bi bi-three-dots"></i>
        </button>
      </div>
    `;
  },

  /**
   * Render reply toggle button
   */
  renderReplyToggle(commentId, replyCount) {
    return `
      <button class="reply-toggle" 
              data-action="toggle-replies"
              data-comment-id="${commentId}"
              aria-expanded="false"
              aria-controls="replies-${commentId}">
        <i class="bi bi-chevron-down"></i>
        <span>View ${replyCount} ${replyCount === 1 ? 'reply' : 'replies'}</span>
      </button>
    `;
  },

  /**
   * Render inline composer
   */
  renderComposer(commentId, parentAuthorName) {
    return `
      <div class="comment-composer" id="composer-${commentId}">
        <div class="composer-header">
          Replying to <span>${this.escapeHtml(parentAuthorName)}</span>
          <button class="composer-close" data-action="close-composer" aria-label="Cancel reply">
            <i class="bi bi-x-lg"></i>
          </button>
        </div>
        <textarea class="composer-input" 
                  id="composer-input-${commentId}"
                  placeholder="Write your reply..."
                  rows="3"
                  aria-label="Reply content"></textarea>
        <div class="composer-actions">
          <div class="composer-tools">
            <button class="composer-tool-btn" data-action="emoji" aria-label="Add emoji" title="Emoji (coming soon)">
              <i class="bi bi-emoji-smile"></i>
            </button>
            <button class="composer-tool-btn" data-action="attachment" aria-label="Add attachment" title="Attachment (coming soon)">
              <i class="bi bi-paperclip"></i>
            </button>
          </div>
          <button class="composer-send" 
                  data-action="send-reply"
                  data-comment-id="${commentId}"
                  disabled>
            Send
          </button>
        </div>
      </div>
    `;
  },

  /**
   * Render edit mode
   */
  renderEditMode(commentId, currentContent) {
    return `
      <div class="comment-edit-mode" id="edit-mode-${commentId}">
        <textarea class="edit-textarea" 
                  id="edit-input-${commentId}"
                  rows="3"
                  aria-label="Edit comment">${this.escapeHtml(currentContent)}</textarea>
        <div class="edit-actions">
          <button class="edit-cancel" 
                  data-action="cancel-edit"
                  data-comment-id="${commentId}">
            Cancel
          </button>
          <button class="edit-save" 
                  data-action="save-edit"
                  data-comment-id="${commentId}">
            Save
          </button>
        </div>
      </div>
    `;
  },

  /**
   * Render overflow menu
   */
  renderMenu(commentId, isOwner, isModerator) {
    let menuItems = '';

    if (isOwner) {
      menuItems += `
        <button class="comment-menu-item" data-action="edit" data-comment-id="${commentId}">
          <i class="bi bi-pencil"></i> Edit
        </button>
        <button class="comment-menu-item" data-action="delete" data-comment-id="${commentId}">
          <i class="bi bi-trash"></i> Delete
        </button>
        <div class="comment-menu-divider"></div>
      `;
    }

    menuItems += `
      <button class="comment-menu-item" data-action="copy-text" data-comment-id="${commentId}">
        <i class="bi bi-copy"></i> Copy text
      </button>
      <button class="comment-menu-item" data-action="copy-link" data-comment-id="${commentId}">
        <i class="bi bi-link-45deg"></i> Copy link
      </button>
      <button class="comment-menu-item" data-action="view-profile" data-comment-id="${commentId}">
        <i class="bi bi-person"></i> View profile
      </button>
    `;

    if (isModerator) {
      menuItems += `
        <div class="comment-menu-divider"></div>
        <button class="comment-menu-item" data-action="pin" data-comment-id="${commentId}">
          <i class="bi bi-pin"></i> Pin comment
        </button>
        <button class="comment-menu-item" data-action="hide" data-comment-id="${commentId}">
          <i class="bi bi-eye-slash"></i> Hide comment
        </button>
      `;
    }

    return `
      <div class="comment-menu-dropdown" id="menu-${commentId}" role="menu">
        ${menuItems}
      </div>
    `;
  },

  /**
   * Render empty state
   */
  renderEmptyState() {
    return `
      <div class="comments-empty">
        <i class="bi bi-chat-dots"></i>
        <p>No comments yet. Be the first to comment.</p>
      </div>
    `;
  },

  /**
   * Render loading state
   */
  renderLoadingState() {
    return `
      <div class="comments-loading">
        <i class="bi bi-arrow-repeat"></i>
        <p>Loading comments...</p>
      </div>
    `;
  },

  /**
   * Format timestamp
   */
  formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (seconds < 60) {
      return 'just now';
    } else if (minutes < 60) {
      return `${minutes}m ago`;
    } else if (hours < 24) {
      return `${hours}h ago`;
    } else if (days < 7) {
      return `${days}d ago`;
    } else {
      return date.toLocaleDateString();
    }
  },

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommentRenderer;
}
