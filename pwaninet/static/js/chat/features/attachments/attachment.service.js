/**
 * AttachmentService - File attachment logic
 * Pure service layer, no DOM manipulation
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';
import { isImageFile, isVideoFile, isAudioFile } from '../../shared/utils.js';

export class AttachmentService {
  constructor() {
    this.selectedFile = null;
  }

  /**
   * Initialize attachment service
   */
  init() {
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    eventBus.on(EVENTS.ATTACHMENT_SELECTED, (file) => {
      this.handleFileSelection(file);
    });

    eventBus.on(EVENTS.ATTACHMENT_UPLOAD, (file) => {
      this.handleFileUpload(file);
    });

    eventBus.on(EVENTS.ATTACHMENT_MODAL_TOGGLE, (show) => {
      eventBus.emit(EVENTS.ATTACHMENT_MODAL_TOGGLE, show);
    });
  }

  /**
   * Handle file selection
   * @param {File} file - Selected file
   */
  handleFileSelection(file) {
    this.selectedFile = file;

    const fileType = this.getFileType(file);
    eventBus.emit(EVENTS.ATTACHMENT_SELECTED, {
      file,
      type: fileType,
    });
  }

  /**
   * Handle file upload
   * @param {File} file - File to upload
   * @param {number} conversationId - Conversation ID
   */
  async handleFileUpload(file, conversationId) {
    // Validate file
    if (!this.validateFile(file)) {
      eventBus.emit(EVENTS.ATTACHMENT_ERROR, { message: 'Invalid file' });
      return;
    }

    if (!conversationId) {
      eventBus.emit(EVENTS.ATTACHMENT_ERROR, { message: 'Conversation ID is required' });
      return;
    }

    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);

    try {
      // Emit upload start event
      eventBus.emit(EVENTS.ATTACHMENT_UPLOAD_START, { file });

      // Upload file to messaging app endpoint
      const response = await fetch('/messaging/api/attachments/upload/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': this.getCSRFToken(),
        },
      });

      if (response.ok) {
        const data = await response.json();
        eventBus.emit(EVENTS.ATTACHMENT_UPLOAD_SUCCESS, data);
      } else {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Attachment upload error:', error);
      eventBus.emit(EVENTS.ATTACHMENT_ERROR, error);
    }
  }

  /**
   * Get file type
   * @param {File} file - File object
   * @returns {string} File type
   */
  getFileType(file) {
    if (isImageFile(file.name)) return 'image';
    if (isVideoFile(file.name)) return 'video';
    if (isAudioFile(file.name)) return 'audio';
    return 'document';
  }

  /**
   * Validate file
   * @param {File} file - File to validate
   * @returns {boolean} Is valid
   */
  validateFile(file) {
    // Size limit: 50MB
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      return false;
    }

    // Allowed types
    const allowedTypes = [
      'image/jpeg',
      'image/png',
      'image/gif',
      'image/webp',
      'video/mp4',
      'video/webm',
      'audio/mpeg',
      'audio/wav',
      'audio/webm',
      'application/pdf',
      'text/plain',
    ];

    return allowedTypes.includes(file.type);
  }

  /**
   * Get CSRF token
   * @returns {string} CSRF token
   */
  getCSRFToken() {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') return decodeURIComponent(value);
    }
    return '';
  }

  /**
   * Clear selected file
   */
  clearSelection() {
    this.selectedFile = null;
  }

  /**
   * Get selected file
   * @returns {File|null} Selected file
   */
  getSelectedFile() {
    return this.selectedFile;
  }
}

// Create global instance
export const attachmentService = new AttachmentService();
