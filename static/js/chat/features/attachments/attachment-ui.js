/**
 * AttachmentUI - UI event handlers for attachment functionality
 * Connects UI elements to attachment service
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';
import { attachmentService } from './attachment.service.js';
import { cameraService } from '../camera/camera.service.js';
import { voiceService } from '../voice/voice.service.js';
import { voiceModalController } from '../voice/voice-modal-controller.js';

export class AttachmentUI {
    constructor() {
        this.initialized = false;
        this.attachmentModal = null;
        this.overlay = null;
        this.fileInput = null;
        this.cameraInput = null;
        this.voiceRecordingPreview = null;
    }

    /**
     * Initialize attachment UI
     */
    init() {
        console.log('[ATTACHMENT_UI] Attachment UI initializing...');
        if (this.initialized) {
            console.log('[ATTACHMENT_UI] Already initialized');
            return;
        }

        this._initializeElements();
        this._setupEventListeners();
        this._setupServiceListeners();
        
        // Initialize voice modal controller
        voiceModalController.init();

        this.initialized = true;
        console.log('[ATTACHMENT_UI] Attachment UI initialized');
    }

    /**
     * Initialize DOM elements
     */
    _initializeElements() {
        this.attachmentModal = document.getElementById('attachmentModal');
        this.overlay = document.getElementById('overlay');
        this.fileInput = document.getElementById('fileInput');
        this.cameraInput = document.getElementById('cameraInput');
        // Voice modal is now handled by voiceModalController
    }

    /**
     * Setup UI event listeners
     */
    _setupEventListeners() {
        // Attachment button
        const attachBtn = document.getElementById('attachBtn');
        if (attachBtn) {
            attachBtn.addEventListener('click', () => {
                this.showAttachmentModal();
            });
        }

        // Camera button
        const cameraBtn = document.getElementById('cameraBtn');
        if (cameraBtn) {
            cameraBtn.addEventListener('click', () => {
                this.handleCameraCapture();
            });
        }

        // Voice button listeners removed - now handled by UIController to prevent conflicts
        // and support the voice/send toggle logic.
        // Voice modal is now handled by voiceModalController

        // Close attachment modal
        const closeAttachmentModal = document.getElementById('closeAttachmentModal');
        if (closeAttachmentModal) {
            closeAttachmentModal.addEventListener('click', () => {
                this.hideAttachmentModal();
            });
        }

        // Attachment options
        const attachmentOptions = document.querySelectorAll('.attachment-option');
        attachmentOptions.forEach(option => {
            option.addEventListener('click', () => {
                const type = option.dataset.type;
                this.handleAttachmentOption(type);
            });
        });

        // File input change
        if (this.fileInput) {
            this.fileInput.addEventListener('change', (e) => {
                this.handleFileSelection(e.target.files);
            });
        }

        // Camera input change
        if (this.cameraInput) {
            this.cameraInput.addEventListener('change', (e) => {
                this.handleFileSelection(e.target.files);
            });
        }

        // Voice recording actions are now handled by voiceModalController

        // Overlay click to close modals
        if (this.overlay) {
            this.overlay.addEventListener('click', () => {
                this.hideAttachmentModal();
                // Voice modal overlay is handled by voiceModalController
            });
        }
    }

    /**
     * Setup service event listeners
     */
    _setupServiceListeners() {
        eventBus.on(EVENTS.ATTACHMENT_SELECTED, (data) => {
            this.handleAttachmentSelected(data);
        });

        eventBus.on(EVENTS.ATTACHMENT_UPLOAD_SUCCESS, (data) => {
            this.handleUploadSuccess(data);
        });

        eventBus.on(EVENTS.ATTACHMENT_ERROR, (error) => {
            this.handleUploadError(error);
        });

        // Voice events are now handled by voiceModalController
        // Removed old voice event listeners

        eventBus.on(EVENTS.CAMERA_ERROR, (error) => {
            console.error('Camera error:', error);
            this.fallbackToFileSelection('image');
        });
    }

    /**
     * Show attachment modal
     */
    showAttachmentModal() {
        if (this.attachmentModal && this.overlay) {
            this.attachmentModal.classList.add('show');
            this.overlay.classList.add('show');
        }
    }

    /**
     * Hide attachment modal
     */
    hideAttachmentModal() {
        if (this.attachmentModal && this.overlay) {
            this.attachmentModal.classList.remove('show');
            this.overlay.classList.remove('show');
        }
    }

    /**
     * Handle attachment option selection
     * @param {string} type - Attachment type
     */
    handleAttachmentOption(type) {
        this.hideAttachmentModal();

        switch (type) {
            case 'photos':
                this.triggerFileInput('image/*');
                break;
            case 'videos':
                this.triggerFileInput('video/*');
                break;
            case 'documents':
                this.triggerFileInput('.pdf,.doc,.docx,.txt');
                break;
            case 'audio':
                this.triggerFileInput('audio/*');
                break;
        }
    }

    /**
     * Trigger file input with specific accept type
     * @param {string} accept - File accept attribute
     */
    triggerFileInput(accept) {
        if (this.fileInput) {
            this.fileInput.accept = accept;
            this.fileInput.click();
        }
    }

    /**
     * Handle file selection
     * @param {FileList} files - Selected files
     */
    handleFileSelection(files) {
        if (files && files.length > 0) {
            const file = files[0];
            
            // Get conversation ID from the page
            const conversationId = this._getConversationId();
            if (!conversationId) {
                console.error('No conversation ID found');
                return;
            }

            // Create form data and upload
            const formData = new FormData();
            formData.append('file', file);
            formData.append('conversation_id', conversationId);

            // Upload through attachment service
            attachmentService.handleFileUpload(file, conversationId);
        }
    }

    /**
     * Handle camera capture
     */
    async handleCameraCapture() {
        try {
            // Try to use camera service first
            eventBus.emit(EVENTS.CAMERA_OPEN);
        } catch (error) {
            console.error('Camera capture failed:', error);
            // Fallback to file selection
            this.fallbackToFileSelection('image/*');
        }
    }

    /**
     * Fallback to file selection
     * @param {string} accept - File accept type
     */
    fallbackToFileSelection(accept) {
        if (this.cameraInput) {
            this.cameraInput.accept = accept;
            this.cameraInput.click();
        } else if (this.fileInput) {
            this.fileInput.accept = accept;
            this.fileInput.click();
        }
    }

    /**
     * Handle attachment selected event
     * @param {Object} data - Attachment data
     */
    handleAttachmentSelected(data) {
        console.log('Attachment selected:', data);
    }

    /**
     * Handle upload success
     * @param {Object} data - Upload response data
     */
    handleUploadSuccess(data) {
        console.log('Upload successful:', data);
        // The message will be automatically added to the chat via WebSocket
    }

    /**
     * Handle upload error
     * @param {Object} error - Error data
     */
    handleUploadError(error) {
        console.error('Upload error:', error);
        // Show error message to user
        alert('Failed to upload file: ' + (error.message || 'Unknown error'));
    }

    /**
     * Get conversation ID from the page
     * @returns {number|null} Conversation ID
     */
    _getConversationId() {
        const chatContainer = document.querySelector('.chat-container');
        if (chatContainer) {
            return parseInt(chatContainer.dataset.conversationId);
        }
        return null;
    }

    /**
     * Destroy attachment UI
     */
    destroy() {
        // Clean up event listeners
        this.initialized = false;
        console.log('[ATTACHMENT_UI] Destroyed');
    }
}

// Create and export singleton instance
export const attachmentUI = new AttachmentUI();
