/**
 * Comment Manager Module
 * Main controller for comment system
 */
const CommentManager = {
  postId: null,
  currentUser: null,
  activeComposer: null,
  draftContent: new Map(),
  expandedReplies: new Set(),

  /**
   * Initialize comment manager
   */
  init(postId, currentUser) {
    this.postId = postId;
    this.currentUser = currentUser;
    this.bindEvents();
    this.initWebSocket();
  },

  /**
   * Bind global events
   */
  bindEvents() {
    document.addEventListener('click', (e) => this.handleClick(e));
    document.addEventListener('keydown', (e) => this.handleKeydown(e));
    document.addEventListener('input', (e) => this.handleInput(e));
  },

  /**
   * Handle click events
   */
  handleClick(e) {
    const target = e.target.closest('[data-action]');
    if (!target) return;

    const action = target.dataset.action;
    const commentId = target.dataset.commentId;

    switch (action) {
      case 'like':
        e.preventDefault();
        this.handleLike(commentId);
        break;
      case 'reply':
        e.preventDefault();
        this.handleReply(commentId);
        break;
      case 'menu':
        e.preventDefault();
        this.handleMenu(commentId, target);
        break;
      case 'toggle-replies':
        e.preventDefault();
        this.handleToggleReplies(commentId, target);
        break;
      case 'close-composer':
        e.preventDefault();
        this.closeComposer(commentId);
        break;
      case 'send-reply':
        e.preventDefault();
        this.sendReply(commentId);
        break;
      case 'edit':
        e.preventDefault();
        this.handleEdit(commentId);
        break;
      case 'cancel-edit':
        e.preventDefault();
        this.cancelEdit(commentId);
        break;
      case 'save-edit':
        e.preventDefault();
        this.saveEdit(commentId);
        break;
      case 'delete':
        e.preventDefault();
        this.handleDelete(commentId);
        break;
      case 'copy-text':
        e.preventDefault();
        this.copyText(commentId);
        break;
      case 'copy-link':
        e.preventDefault();
        this.copyLink(commentId);
        break;
      case 'view-profile':
        e.preventDefault();
        this.viewProfile(commentId);
        break;
    }

    // Close menu when clicking outside
    if (!target.closest('.comment-menu-dropdown') && !target.closest('[data-action="menu"]')) {
      this.closeAllMenus();
    }
  },

  /**
   * Handle keyboard events
   */
  handleKeydown(e) {
    const target = e.target;
    
    // Escape to close composer or menu
    if (e.key === 'Escape') {
      this.closeAllComposers();
      this.closeAllMenus();
      this.cancelEdit(target.dataset.commentId);
    }
    
    // Ctrl/Cmd + Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      if (target.classList.contains('composer-input')) {
        const commentId = target.id.replace('composer-input-', '');
        this.sendReply(commentId);
      } else if (target.classList.contains('edit-textarea')) {
        const commentId = target.id.replace('edit-input-', '');
        this.saveEdit(commentId);
      }
    }
  },

  /**
   * Handle input events
   */
  handleInput(e) {
    const target = e.target;
    
    if (target.classList.contains('composer-input')) {
      const commentId = target.id.replace('composer-input-', '');
      const sendBtn = document.querySelector(`[data-action="send-reply"][data-comment-id="${commentId}"]`);
      if (sendBtn) {
        sendBtn.disabled = !target.value.trim();
      }
      
      // Save draft
      this.draftContent.set(commentId, target.value);
    }
  },

  /**
   * Handle like toggle
   */
  async handleLike(commentId) {
    try {
      const button = document.querySelector(`[data-action="like"][data-comment-id="${commentId}"]`);
      const icon = button.querySelector('i');
      const countSpan = button.querySelector('span');
      
      // Optimistic update
      const wasLiked = button.classList.contains('liked');
      const currentCount = parseInt(countSpan.textContent);
      
      button.classList.toggle('liked');
      icon.classList.toggle('bi-heart-fill');
      icon.classList.toggle('bi-heart');
      countSpan.textContent = wasLiked ? currentCount - 1 : currentCount + 1;
      
      // Play like sound when liking (not unliking)
      if (!wasLiked) {
        this.playLikeSound();
      }
      
      const result = await CommentApi.toggleLike(commentId);
      
      // Update with actual result
      if (result.detail === 'Post unliked.') {
        button.classList.remove('liked');
        icon.classList.remove('bi-heart-fill');
        icon.classList.add('bi-heart');
        countSpan.textContent = currentCount - 1;
      } else {
        button.classList.add('liked');
        icon.classList.remove('bi-heart');
        icon.classList.add('bi-heart-fill');
        countSpan.textContent = currentCount + 1;
      }
    } catch (error) {
      console.error('Failed to toggle like:', error);
      // Revert optimistic update on error
      const button = document.querySelector(`[data-action="like"][data-comment-id="${commentId}"]`);
      const icon = button.querySelector('i');
      const countSpan = button.querySelector('span');
      button.classList.toggle('liked');
      icon.classList.toggle('bi-heart-fill');
      icon.classList.toggle('bi-heart');
    }
  },

  /**
   * Play like sound effect using Web Audio API
   */
  playLikeSound() {
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Create a pleasant "ding" sound
      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(1200, audioContext.currentTime + 0.1);
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.error('Failed to play like sound:', error);
    }
  },

  /**
   * Handle reply button click
   */
  handleReply(commentId) {
    // Close existing composer
    if (this.activeComposer && this.activeComposer !== commentId) {
      this.closeComposer(this.activeComposer, true);
    }
    
    const commentEl = document.getElementById(`comment-${commentId}`);
    if (!commentEl) return;
    
    // Check if composer already exists
    let composer = document.getElementById(`composer-${commentId}`);
    
    if (composer) {
      // Focus existing composer
      const input = document.getElementById(`composer-input-${commentId}`);
      input.focus();
      this.activeComposer = commentId;
      return;
    }
    
    // Get parent author name
    const authorName = commentEl.querySelector('.comment-author-link').textContent;
    
    // Create composer
    const composerHtml = CommentRenderer.renderComposer(commentId, authorName);
    const contentDiv = commentEl.querySelector('.comment-content');
    contentDiv.insertAdjacentHTML('beforeend', composerHtml);
    
    // Focus input
    const input = document.getElementById(`composer-input-${commentId}`);
    input.focus();
    
    // Restore draft if exists
    if (this.draftContent.has(commentId)) {
      input.value = this.draftContent.get(commentId);
    }
    
    this.activeComposer = commentId;
  },

  /**
   * Close composer
   */
  closeComposer(commentId, preserveDraft = true) {
    const composer = document.getElementById(`composer-${commentId}`);
    if (!composer) return;
    
    if (preserveDraft) {
      const input = document.getElementById(`composer-input-${commentId}`);
      if (input && input.value.trim()) {
        this.draftContent.set(commentId, input.value);
      }
    }
    
    composer.remove();
    
    if (this.activeComposer === commentId) {
      this.activeComposer = null;
    }
  },

  /**
   * Send reply
   */
  async sendReply(commentId) {
    const input = document.getElementById(`composer-input-${commentId}`);
    const content = input.value.trim();
    
    if (!content) return;
    
    const sendBtn = document.querySelector(`[data-action="send-reply"][data-comment-id="${commentId}"]`);
    sendBtn.disabled = true;
    sendBtn.textContent = 'Sending...';
    
    try {
      const reply = await CommentApi.createComment(this.postId, content, commentId);
      
      // Clear draft
      this.draftContent.delete(commentId);
      
      // Close composer
      this.closeComposer(commentId, false);
      
      // Add reply to DOM
      this.addReplyToDom(commentId, reply);
      
      // Update reply count
      this.updateReplyCount(commentId, 1);
      
    } catch (error) {
      console.error('Failed to send reply:', error);
      sendBtn.disabled = false;
      sendBtn.textContent = 'Send';
      alert('Failed to send reply. Please try again.');
    }
  },

  /**
   * Add reply to DOM
   */
  addReplyToDom(parentCommentId, replyData) {
    const parentComment = document.getElementById(`comment-${parentCommentId}`);
    if (!parentComment) return;
    
    // Check if replies container exists
    let repliesContainer = document.getElementById(`replies-${parentCommentId}`);
    
    if (!repliesContainer) {
      // Create replies container
      repliesContainer = document.createElement('div');
      repliesContainer.id = `replies-${parentCommentId}`;
      repliesContainer.className = 'replies-container';
      
      const contentDiv = parentComment.querySelector('.comment-content');
      contentDiv.appendChild(repliesContainer);
    }
    
    // Add thread line
    if (!repliesContainer.querySelector('.thread-line')) {
      const threadLine = document.createElement('div');
      threadLine.className = 'thread-line';
      repliesContainer.appendChild(threadLine);
    }
    
    // Render and append reply
    const replyHtml = CommentRenderer.renderComment(replyData, {
      isReply: true,
      nestingLevel: 1,
      currentUser: this.currentUser
    });
    
    repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
    
    // Expand if collapsed
    repliesContainer.classList.add('expanded');
    repliesContainer.classList.remove('collapsed');
  },

  /**
   * Update reply count
   */
  updateReplyCount(commentId, delta) {
    const commentEl = document.getElementById(`comment-${commentId}`);
    if (!commentEl) return;
    
    const currentCount = parseInt(commentEl.dataset.replyCount) || 0;
    const newCount = currentCount + delta;
    
    commentEl.dataset.replyCount = newCount;
    
    // Update or create toggle button
    let toggle = commentEl.querySelector(`[data-action="toggle-replies"][data-comment-id="${commentId}"]`);
    
    if (!toggle && newCount > 0) {
      // Create toggle button if it doesn't exist
      const contentDiv = commentEl.querySelector('.comment-content');
      const toggleHtml = CommentRenderer.renderReplyToggle(commentId, newCount);
      contentDiv.insertAdjacentHTML('beforeend', toggleHtml);
      
      // Get the newly created toggle
      toggle = commentEl.querySelector(`[data-action="toggle-replies"][data-comment-id="${commentId}"]`);
      
      // Auto-expand replies when first reply is added
      const repliesContainer = document.getElementById(`replies-${commentId}`);
      if (repliesContainer) {
        toggle.classList.add('expanded');
        toggle.querySelector('i').classList.remove('bi-chevron-down');
        toggle.querySelector('i').classList.add('bi-chevron-up');
        toggle.querySelector('span').textContent = 'Hide replies';
        toggle.setAttribute('aria-expanded', 'true');
        this.expandedReplies.add(commentId);
      }
    } else if (toggle) {
      // Update existing toggle
      const span = toggle.querySelector('span');
      const repliesContainer = document.getElementById(`replies-${commentId}`);
      
      if (repliesContainer && repliesContainer.classList.contains('expanded')) {
        span.textContent = 'Hide replies';
      } else {
        span.textContent = `View ${newCount} ${newCount === 1 ? 'reply' : 'replies'}`;
      }
    }
  },

  /**
   * Handle toggle replies
   */
  async handleToggleReplies(commentId, button) {
    const repliesContainer = document.getElementById(`replies-${commentId}`);
    const isExpanded = button.classList.contains('expanded');
    
    if (isExpanded) {
      // Collapse
      if (repliesContainer) {
        repliesContainer.classList.remove('expanded');
        repliesContainer.classList.add('collapsed');
      }
      button.classList.remove('expanded');
      button.querySelector('i').classList.remove('bi-chevron-up');
      button.querySelector('i').classList.add('bi-chevron-down');
      button.querySelector('span').textContent = `View ${button.dataset.replyCount} replies`;
      button.setAttribute('aria-expanded', 'false');
      this.expandedReplies.delete(commentId);
    } else {
      // Expand
      if (repliesContainer && repliesContainer.children.length > 0) {
        // Already loaded, just show
        repliesContainer.classList.remove('collapsed');
        repliesContainer.classList.add('expanded');
      } else {
        // Load replies
        await this.loadReplies(commentId);
      }
      
      button.classList.add('expanded');
      button.querySelector('i').classList.remove('bi-chevron-down');
      button.querySelector('i').classList.add('bi-chevron-up');
      button.querySelector('span').textContent = 'Hide replies';
      button.setAttribute('aria-expanded', 'true');
      this.expandedReplies.add(commentId);
    }
  },

  /**
   * Load replies
   */
  async loadReplies(commentId) {
    try {
      const data = await CommentApi.getReplies(commentId);
      
      const parentComment = document.getElementById(`comment-${commentId}`);
      if (!parentComment) return;
      
      // Create replies container
      let repliesContainer = document.getElementById(`replies-${commentId}`);
      if (!repliesContainer) {
        repliesContainer = document.createElement('div');
        repliesContainer.id = `replies-${commentId}`;
        repliesContainer.className = 'replies-container';
        
        const contentDiv = parentComment.querySelector('.comment-content');
        contentDiv.appendChild(repliesContainer);
      }
      
      // Add thread line
      const threadLine = document.createElement('div');
      threadLine.className = 'thread-line';
      repliesContainer.appendChild(threadLine);
      
      // Render replies
      data.results.forEach(reply => {
        const replyHtml = CommentRenderer.renderComment(reply, {
          isReply: true,
          nestingLevel: 1,
          currentUser: this.currentUser
        });
        repliesContainer.insertAdjacentHTML('beforeend', replyHtml);
      });
      
      repliesContainer.classList.add('expanded');
      
    } catch (error) {
      console.error('Failed to load replies:', error);
    }
  },

  /**
   * Handle menu
   */
  handleMenu(commentId, button) {
    const existingMenu = document.getElementById(`menu-${commentId}`);
    
    // Close other menus
    this.closeAllMenus();
    
    if (existingMenu) {
      existingMenu.remove();
      button.setAttribute('aria-expanded', 'false');
      return;
    }
    
    const commentEl = document.getElementById(`comment-${commentId}`);
    const isOwner = this.currentUser && commentEl.dataset.authorId == this.currentUser.id;
    const isModerator = this.currentUser && ['admin', 'moderator'].includes(this.currentUser.role);
    
    const menuHtml = CommentRenderer.renderMenu(commentId, isOwner, isModerator);
    const contentDiv = commentEl.querySelector('.comment-content');
    contentDiv.insertAdjacentHTML('beforeend', menuHtml);
    
    button.setAttribute('aria-expanded', 'true');
  },

  /**
   * Close all menus
   */
  closeAllMenus() {
    document.querySelectorAll('.comment-menu-dropdown').forEach(menu => {
      menu.remove();
    });
    document.querySelectorAll('[data-action="menu"]').forEach(btn => {
      btn.setAttribute('aria-expanded', 'false');
    });
  },

  /**
   * Close all composers
   */
  closeAllComposers() {
    document.querySelectorAll('.comment-composer').forEach(composer => {
      const commentId = composer.id.replace('composer-', '');
      this.closeComposer(commentId, true);
    });
  },

  /**
   * Handle edit
   */
  handleEdit(commentId) {
    this.closeAllMenus();
    
    const commentEl = document.getElementById(`comment-${commentId}`);
    const bodyEl = document.getElementById(`comment-body-${commentId}`);
    const currentContent = bodyEl.textContent;
    
    // Hide body
    bodyEl.style.display = 'none';
    
    // Insert edit mode
    const editHtml = CommentRenderer.renderEditMode(commentId, currentContent);
    bodyEl.insertAdjacentHTML('afterend', editHtml);
    
    // Focus textarea
    const textarea = document.getElementById(`edit-input-${commentId}`);
    textarea.focus();
  },

  /**
   * Cancel edit
   */
  cancelEdit(commentId) {
    const editMode = document.getElementById(`edit-mode-${commentId}`);
    if (!editMode) return;
    
    const bodyEl = document.getElementById(`comment-body-${commentId}`);
    bodyEl.style.display = '';
    editMode.remove();
  },

  /**
   * Save edit
   */
  async saveEdit(commentId) {
    const textarea = document.getElementById(`edit-input-${commentId}`);
    const content = textarea.value.trim();
    
    if (!content) return;
    
    try {
      const updated = await CommentApi.updateComment(commentId, content);
      
      const bodyEl = document.getElementById(`comment-body-${commentId}`);
      bodyEl.textContent = updated.content;
      bodyEl.style.display = '';
      
      const editMode = document.getElementById(`edit-mode-${commentId}`);
      editMode.remove();
      
    } catch (error) {
      console.error('Failed to save edit:', error);
      alert('Failed to save edit. Please try again.');
    }
  },

  /**
   * Handle delete
   */
  async handleDelete(commentId) {
    this.closeAllMenus();
    
    if (!confirm('Are you sure you want to delete this comment?')) {
      return;
    }
    
    try {
      await CommentApi.deleteComment(commentId);
      
      const commentEl = document.getElementById(`comment-${commentId}`);
      commentEl.classList.add('removing');
      
      setTimeout(() => {
        commentEl.remove();
        
        // Update parent reply count if this is a reply
        const parentId = commentEl.dataset.parentId;
        if (parentId) {
          this.updateReplyCount(parentId, -1);
        }
      }, 300);
      
    } catch (error) {
      console.error('Failed to delete comment:', error);
      alert('Failed to delete comment. Please try again.');
    }
  },

  /**
   * Copy text
   */
  copyText(commentId) {
    this.closeAllMenus();
    
    const commentEl = document.getElementById(`comment-${commentId}`);
    const bodyEl = document.getElementById(`comment-body-${commentId}`);
    const text = bodyEl.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
      alert('Comment text copied to clipboard');
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  },

  /**
   * Copy link
   */
  copyLink(commentId) {
    this.closeAllMenus();
    
    const url = `${window.location.origin}${window.location.pathname}#comment-${commentId}`;
    
    navigator.clipboard.writeText(url).then(() => {
      alert('Comment link copied to clipboard');
    }).catch(err => {
      console.error('Failed to copy link:', err);
    });
  },

  /**
   * View profile
   */
  viewProfile(commentId) {
    this.closeAllMenus();
    
    const commentEl = document.getElementById(`comment-${commentId}`);
    const profileLink = commentEl.querySelector('.comment-avatar-link');
    
    if (profileLink) {
      window.location.href = profileLink.href;
    }
  },

  /**
   * Initialize WebSocket for real-time updates
   */
  initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/post/${this.postId}/comments/`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_comment') {
        this.handleNewComment(data.comment);
      } else if (data.type === 'comment_like_update') {
        this.handleLikeUpdate(data);
      }
    };
  },

  /**
   * Handle new comment via WebSocket
   */
  handleNewComment(commentData) {
    // Check if comment already exists
    if (document.getElementById(`comment-${commentData.id}`)) {
      return;
    }
    
    // If this is a reply, add it to the parent's replies container
    if (commentData.parent_comment_id) {
      this.addReplyToDom(commentData.parent_comment_id, commentData);
      this.updateReplyCount(commentData.parent_comment_id, 1);
      return;
    }
    
    // Otherwise, add as top-level comment
    const stream = document.querySelector('.comment-stream');
    if (!stream) return;
    
    const commentHtml = CommentRenderer.renderComment(commentData, {
      currentUser: this.currentUser
    });
    
    // Remove empty state if present
    const emptyState = stream.querySelector('.comments-empty');
    if (emptyState) {
      emptyState.remove();
    }
    
    stream.insertAdjacentHTML('afterbegin', commentHtml);
  },

  /**
   * Handle like update via WebSocket
   */
  handleLikeUpdate(data) {
    const button = document.querySelector(`[data-action="like"][data-comment-id="${data.comment_id}"]`);
    if (!button) return;
    
    const countSpan = button.querySelector('span');
    countSpan.textContent = data.likes_count;
  }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CommentManager;
}
