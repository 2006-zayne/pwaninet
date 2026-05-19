/**
 * MediaComposer - Fullscreen media composition interface
 * Handles multi-file selection, preview, editing, and batch upload
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';
import { PreviewCanvas } from './PreviewCanvas.js';
import { ThumbnailStrip } from './ThumbnailStrip.js';
import { CaptionInput } from './CaptionInput.js';
import { ToolRail } from './ToolRail.js';
import { UploadQueue } from './UploadQueue.js';

export class MediaComposer {
    constructor() {
        this.overlay = null;
        this.isOpen = false;
        
        // State
        this.mediaItems = [];
        this.activeMediaIndex = 0;
        this.globalCaption = '';
        this.conversationId = null;
        
        // Sub-components
        this.previewCanvas = null;
        this.thumbnailStrip = null;
        this.captionInput = null;
        this.toolRail = null;
        this.uploadQueue = null;
        
        // DOM elements
        this.header = null;
        this.main = null;
        this.footer = null;
        this.sendBtn = null;
        this.closeBtn = null;
        this.addMoreBtn = null;
        
        this.initialized = false;
    }
    
    /**
     * Initialize the media composer
     */
    init() {
        if (this.initialized) return;
        
        this._initializeElements();
        this._setupEventListeners();
        this._initializeComponents();
        
        this.initialized = true;
        console.log('[MEDIA_COMPOSER] Media composer initialized');
    }
    
    /**
     * Initialize DOM elements
     */
    _initializeElements() {
        console.log('[MEDIA_COMPOSER] Initializing DOM elements');
        
        this.overlay = document.getElementById('mediaComposerOverlay');
        this.header = document.getElementById('mediaComposerHeader');
        this.main = document.getElementById('mediaComposerMain');
        this.footer = document.getElementById('mediaComposerFooter');
        this.sendBtn = document.getElementById('mediaComposerSend');
        this.closeBtn = document.getElementById('mediaComposerClose');
        this.addMoreBtn = document.getElementById('mediaComposerAddMore');
        
        console.log('[MEDIA_COMPOSER] DOM elements:', {
            overlay: !!this.overlay,
            header: !!this.header,
            main: !!this.main,
            footer: !!this.footer,
            sendBtn: !!this.sendBtn,
            closeBtn: !!this.closeBtn,
            addMoreBtn: !!this.addMoreBtn
        });
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        console.log('[MEDIA_COMPOSER] Setting up event listeners');
        
        // Close button
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
            console.log('[MEDIA_COMPOSER] Close button listener set up');
        }
        
        // Send button
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.send());
            console.log('[MEDIA_COMPOSER] Send button listener set up');
        } else {
            console.error('[MEDIA_COMPOSER] Send button not found');
        }
        
        // Add more files button
        if (this.addMoreBtn) {
            this.addMoreBtn.addEventListener('click', () => this.triggerFileInput());
            console.log('[MEDIA_COMPOSER] Add more button listener set up');
        }
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => this._handleKeydown(e));
        
        // Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }
    
    /**
     * Initialize sub-components
     */
    _initializeComponents() {
        console.log('[MEDIA_COMPOSER] Initializing sub-components');
        
        this.previewCanvas = new PreviewCanvas(this);
        this.thumbnailStrip = new ThumbnailStrip(this);
        this.captionInput = new CaptionInput(this);
        this.toolRail = new ToolRail(this);
        this.uploadQueue = new UploadQueue(this);
        
        this.previewCanvas.init();
        this.thumbnailStrip.init();
        this.captionInput.init();
        this.toolRail.init();
        this.uploadQueue.init();
        
        console.log('[MEDIA_COMPOSER] Sub-components initialized');
    }
    
    /**
     * Open the media composer
     * @param {FileList|Array} files - Files to compose
     * @param {number} conversationId - Conversation ID
     */
    open(files, conversationId) {
        console.log('[MEDIA_COMPOSER] Opening with files:', files.length, 'conversation:', conversationId);
        
        this.conversationId = conversationId;
        this.mediaItems = this._processFiles(files);
        this.activeMediaIndex = 0;
        this.globalCaption = '';
        
        console.log('[MEDIA_COMPOSER] Processed media items:', this.mediaItems.length);
        
        // Restore draft if exists
        this._restoreDraft();
        
        // Show overlay
        if (this.overlay) {
            this.overlay.classList.add('show');
            console.log('[MEDIA_COMPOSER] Overlay shown');
        }
        
        this.isOpen = true;
        
        // Enable send button
        if (this.sendBtn) {
            this.sendBtn.disabled = false;
            this.sendBtn.textContent = 'Send';
            console.log('[MEDIA_COMPOSER] Send button enabled');
        } else {
            console.error('[MEDIA_COMPOSER] Send button not found');
        }
        
        // Render components
        this.previewCanvas.render(this.mediaItems[0]);
        this.thumbnailStrip.render(this.mediaItems);
        this.captionInput.setGlobalCaption(this.globalCaption);
        this.toolRail.updateTools(this.mediaItems[0]);
        
        // Save draft
        this._saveDraft();
        
        console.log('[MEDIA_COMPOSER] Composer opened successfully');
    }
    
    /**
     * Close composer
     */
    close() {
        // Save draft before closing
        this._saveDraft();
        
        // Clean up object URLs
        this.mediaItems.forEach(item => {
            if (item.previewUrl) {
                URL.revokeObjectURL(item.previewUrl);
            }
        });
        
        // Hide overlay
        if (this.overlay) {
            this.overlay.classList.remove('show');
        }
        
        this.isOpen = false;
        this.mediaItems = [];
        this.activeMediaIndex = 0;
        this.globalCaption = '';
        
        console.log('[MEDIA_COMPOSER] Composer closed');
    }
    
    /**
     * Process files into media items
     * @param {FileList|Array} files - Files to process
     * @returns {Array} Media items
     */
    _processFiles(files) {
        console.log('[MEDIA_COMPOSER] Processing files:', files.length);
        const items = [];
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const fileType = this._getFileType(file);
            const previewUrl = this._createPreviewUrl(file);
            
            console.log('[MEDIA_COMPOSER] Processing file:', i, file.name, fileType);
            
            items.push({
                file: file,
                type: fileType,
                previewUrl: previewUrl,
                caption: '',
                size: file.size,
                name: file.name
            });
        }
        
        console.log('[MEDIA_COMPOSER] Processed items:', items.length);
        return items;
    }
    
    /**
     * Get file type
     * @param {File} file - File to check
     * @returns {string} File type
     */
    _getFileType(file) {
        if (file.type.startsWith('image/')) return 'image';
        if (file.type.startsWith('video/')) return 'video';
        if (file.type.startsWith('audio/')) return 'audio';
        return 'document';
    }
    
    /**
     * Create preview URL for file
     * @param {File} file - File to create preview for
     * @returns {string} Preview URL
     */
    _createPreviewUrl(file) {
        if (file.type.startsWith('image/') || file.type.startsWith('video/')) {
            return URL.createObjectURL(file);
        }
        return null;
    }
    
    /**
     * Set active media item
     * @param {number} index - Index of media item
     */
    setActiveMedia(index) {
        if (index < 0 || index >= this.mediaItems.length) return;
        
        this.activeMediaIndex = index;
        this.previewCanvas.render(this.mediaItems[index]);
        this.thumbnailStrip.setActive(index);
        this.captionInput.setMediaCaption(this.mediaItems[index].caption);
        this.toolRail.updateTools(this.mediaItems[index]);
    }
    
    /**
     * Update media item caption
     * @param {string} caption - Caption text
     */
    updateMediaCaption(caption) {
        if (this.mediaItems[this.activeMediaIndex]) {
            this.mediaItems[this.activeMediaIndex].caption = caption;
        }
    }
    
    /**
     * Update global caption
     * @param {string} caption - Global caption text
     */
    updateGlobalCaption(caption) {
        this.globalCaption = caption;
    }
    
    /**
     * Remove media item
     * @param {number} index - Index of media item to remove
     */
    removeMediaItem(index) {
        if (this.mediaItems.length <= 1) {
            this.close();
            return;
        }
        
        // Clean up preview URL
        if (this.mediaItems[index].previewUrl) {
            URL.revokeObjectURL(this.mediaItems[index].previewUrl);
        }
        
        this.mediaItems.splice(index, 1);
        
        // Adjust active index if needed
        if (this.activeMediaIndex >= this.mediaItems.length) {
            this.activeMediaIndex = this.mediaItems.length - 1;
        }
        
        this.thumbnailStrip.render(this.mediaItems);
        this.setActiveMedia(this.activeMediaIndex);
    }
    
    /**
     * Add more files
     * @param {FileList|Array} files - Files to add
     */
    addFiles(files) {
        const newItems = this._processFiles(files);
        this.mediaItems = [...this.mediaItems, ...newItems];
        this.thumbnailStrip.render(this.mediaItems);
    }
    
    /**
     * Trigger file input for adding more files
     */
    triggerFileInput() {
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = 'image/*,video/*,audio/*,.pdf,.doc,.docx,.txt';
        
        input.onchange = (e) => {
            if (e.target.files.length > 0) {
                this.addFiles(e.target.files);
            }
        };
        
        input.click();
    }
    
    /**
     * Send media group
     */
    async send() {
        console.log('[MEDIA_COMPOSER] Send button clicked');
        if (this.mediaItems.length === 0) {
            console.warn('[MEDIA_COMPOSER] No media items to send');
            return;
        }
        
        console.log('[MEDIA_COMPOSER] Sending media items:', this.mediaItems.length, 'conversation:', this.conversationId);
        
        // Disable send button
        if (this.sendBtn) {
            this.sendBtn.disabled = true;
            this.sendBtn.textContent = 'Sending...';
        }
        
        try {
            await this.uploadQueue.upload(
                this.mediaItems,
                this.globalCaption,
                this.conversationId
            );
            
            console.log('[MEDIA_COMPOSER] Upload successful');
            
            // Clear draft on successful send
            this._clearDraft();
            this.close();
        } catch (error) {
            console.error('[MEDIA_COMPOSER] Send failed:', error);
            
            // Re-enable send button
            if (this.sendBtn) {
                this.sendBtn.disabled = false;
                this.sendBtn.textContent = 'Send';
            }
        }
    }
    
    /**
     * Handle keyboard navigation
     * @param {KeyboardEvent} e - Keyboard event
     */
    _handleKeydown(e) {
        if (!this.isOpen) return;
        
        // Arrow keys for navigation
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            this.setActiveMedia(this.activeMediaIndex - 1);
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            this.setActiveMedia(this.activeMediaIndex + 1);
        }
    }
    
    /**
     * Save draft to session storage
     */
    _saveDraft() {
        if (!this.conversationId) return;
        
        const draft = {
            conversationId: this.conversationId,
            globalCaption: this.globalCaption,
            mediaCount: this.mediaItems.length,
            timestamp: Date.now()
        };
        
        // Note: We can't save actual files to session storage due to size limits
        // In a real implementation, you'd use IndexedDB for file storage
        sessionStorage.setItem(`media_draft_${this.conversationId}`, JSON.stringify(draft));
    }
    
    /**
     * Restore draft from session storage
     */
    _restoreDraft() {
        if (!this.conversationId) return;
        
        const draftKey = `media_draft_${this.conversationId}`;
        const draft = sessionStorage.getItem(draftKey);
        
        if (draft) {
            const parsed = JSON.parse(draft);
            const age = Date.now() - parsed.timestamp;
            
            // Only restore if draft is less than 1 hour old
            if (age < 3600000) {
                this.globalCaption = parsed.globalCaption || '';
                this.captionInput.setGlobalCaption(this.globalCaption);
                console.log('[MEDIA_COMPOSER] Draft restored');
            }
        }
    }
    
    /**
     * Clear draft
     */
    _clearDraft() {
        if (!this.conversationId) return;
        
        sessionStorage.removeItem(`media_draft_${this.conversationId}`);
    }
    
    /**
     * Destroy composer
     */
    destroy() {
        // Clean up components
        if (this.previewCanvas) this.previewCanvas.destroy();
        if (this.thumbnailStrip) this.thumbnailStrip.destroy();
        if (this.captionInput) this.captionInput.destroy();
        if (this.toolRail) this.toolRail.destroy();
        if (this.uploadQueue) this.uploadQueue.destroy();
        
        // Clean up object URLs
        this.mediaItems.forEach(item => {
            if (item.previewUrl) {
                URL.revokeObjectURL(item.previewUrl);
            }
        });
        
        this.initialized = false;
        console.log('[MEDIA_COMPOSER] Composer destroyed');
    }
}

// Create and export singleton instance
export const mediaComposer = new MediaComposer();
