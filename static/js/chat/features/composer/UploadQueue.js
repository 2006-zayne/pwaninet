/**
 * UploadQueue - Handles batch upload of media files
 * Manages upload progress, retry logic, and optimistic messaging
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';

export class UploadQueue {
    constructor(composer) {
        this.composer = composer;
        this.uploads = [];
        this.isUploading = false;
        
        this.initialized = false;
    }
    
    /**
     * Initialize upload queue
     */
    init() {
        this.initialized = true;
        console.log('[UPLOAD_QUEUE] Upload queue initialized');
    }
    
    /**
     * Upload media items
     * @param {Array} mediaItems - Media items to upload
     * @param {string} globalCaption - Global caption
     * @param {number} conversationId - Conversation ID
     */
    async upload(mediaItems, globalCaption, conversationId) {
        console.log('[UPLOAD_QUEUE] Upload called with:', mediaItems.length, 'items, conversation:', conversationId);
        
        if (this.isUploading) {
            console.warn('[UPLOAD_QUEUE] Upload already in progress');
            return;
        }
        
        this.isUploading = true;
        
        // Declare tempId outside try block for error handling
        let tempId;
        
        try {
            // Create optimistic message
            tempId = this._generateTempId();
            console.log('[UPLOAD_QUEUE] Generated tempId:', tempId);
            this._emitOptimisticMessage(tempId, mediaItems, globalCaption);
            
            // Prepare form data
            const formData = new FormData();
            formData.append('conversation_id', conversationId);
            formData.append('global_caption', globalCaption);
            
            // Add files
            mediaItems.forEach((item, index) => {
                console.log('[UPLOAD_QUEUE] Adding file:', index, item.file.name, item.type);
                formData.append('files', item.file);
            });
            
            // Add attachment metadata
            const attachmentsData = mediaItems.map((item, index) => ({
                caption: item.caption,
                order: index,
                size: item.size
            }));
            formData.append('attachments_data', JSON.stringify(attachmentsData));
            
            console.log('[UPLOAD_QUEUE] Starting upload to server...');
            
            // Upload to server
            const response = await fetch('/messaging/api/attachments/batch-upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': this._getCSRFToken(),
                },
            });
            
            console.log('[UPLOAD_QUEUE] Server response status:', response.status);
            
            if (response.ok) {
                const data = await response.json();
                console.log('[UPLOAD_QUEUE] Upload successful:', data);
                
                // Emit success event
                eventBus.emit(EVENTS.MESSAGE_UPLOAD_SUCCESS, {
                    tempId,
                    serverMessage: data
                });
            } else {
                const errorData = await response.json();
                console.error('[UPLOAD_QUEUE] Server error:', errorData);
                throw new Error(errorData.error || 'Upload failed');
            }
        } catch (error) {
            console.error('[UPLOAD_QUEUE] Upload failed:', error);
            
            // Emit error event
            eventBus.emit(EVENTS.MESSAGE_UPLOAD_FAILED, {
                tempId,
                error: error.message
            });
            
            throw error;
        } finally {
            this.isUploading = false;
        }
    }
    
    /**
     * Generate temporary ID for optimistic message
     * @returns {string} Temporary ID
     */
    _generateTempId() {
        return `temp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Emit optimistic message
     * @param {string} tempId - Temporary ID
     * @param {Array} mediaItems - Media items
     * @param {string} globalCaption - Global caption
     */
    _emitOptimisticMessage(tempId, mediaItems, globalCaption) {
        console.log('[UPLOAD_QUEUE] Emitting optimistic message:', tempId);
        console.log('[UPLOAD_QUEUE] [DEBUG] FULL OPTIMISTIC MESSAGE SHAPE:');
        console.log('[UPLOAD_QUEUE] [DEBUG] mediaItems count:', mediaItems.length);
        console.log('[UPLOAD_QUEUE] [DEBUG] global_caption:', globalCaption);
        
        const optimisticMessage = {
            id: tempId,
            temp_id: tempId,
            message_type: 'media_group',
            global_caption: globalCaption,
            content: '',
            sender: {
                id: null, // Will be filled by frontend
                username: 'You'
            },
            attachments: mediaItems.map((item, index) => ({
                id: `temp_attach_${index}`,
                file_url: item.previewUrl,
                file_type: item.type,
                caption: item.caption,
                order: index,
                size: item.size
            })),
            created_at: new Date().toISOString(),
            status: 'uploading'
        };
        
        console.log('[UPLOAD_QUEUE] [DEBUG] FULL MESSAGE:', JSON.stringify(optimisticMessage, null, 2));
        console.log('[UPLOAD_QUEUE] [DEBUG] ATTACHMENTS (top-level):', optimisticMessage.attachments);
        console.log('[UPLOAD_QUEUE] [DEBUG] ATTACHMENT COUNT:', optimisticMessage.attachments?.length);
        console.log('[UPLOAD_QUEUE] [DEBUG] METADATA:', optimisticMessage.metadata);
        console.log('[UPLOAD_QUEUE] [DEBUG] METADATA ATTACHMENTS:', optimisticMessage.metadata?.attachments);
        
        eventBus.emit(EVENTS.MESSAGE_OPTIMISTIC_ADD, optimisticMessage);
        console.log('[UPLOAD_QUEUE] Optimistic message emitted');
    }
    
    /**
     * Get CSRF token
     * @returns {string} CSRF token
     */
    _getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                const token = decodeURIComponent(value);
                console.log('[UPLOAD_QUEUE] CSRF token found:', token.substring(0, 10) + '...');
                return token;
            }
        }
        console.error('[UPLOAD_QUEUE] CSRF token not found');
        return '';
    }
    
    /**
     * Retry failed upload
     * @param {string} tempId - Temporary ID of failed message
     */
    async retry(tempId) {
        // In a full implementation, this would:
        // 1. Retrieve the failed message from local storage
        // 2. Re-upload the files
        // 3. Update the message with server response
        
        console.log('[UPLOAD_QUEUE] Retry upload for:', tempId);
    }
    
    /**
     * Cancel upload
     */
    cancel() {
        // In a full implementation, this would:
        // 1. Abort the fetch request
        // 2. Clean up temporary message
        // 3. Revert to draft state
        
        console.log('[UPLOAD_QUEUE] Cancel upload');
    }
    
    /**
     * Destroy upload queue
     */
    destroy() {
        this.uploads = [];
        this.isUploading = false;
        this.initialized = false;
        console.log('[UPLOAD_QUEUE] Upload queue destroyed');
    }
}
