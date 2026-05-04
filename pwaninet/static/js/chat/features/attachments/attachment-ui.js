/**
 * AttachmentUI - UI event handlers for attachment functionality
 * Connects UI elements to attachment service
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';
import { attachmentService } from './attachment.service.js';
import { cameraService } from '../camera/camera.service.js';
import { voiceService } from '../voice/voice.service.js';

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
        this.voiceRecordingPreview = document.getElementById('voiceRecordingPreview');
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

        // Voice button
        const voiceBtn = document.getElementById('voiceBtn');
        console.log('[ATTACHMENT_UI] Voice button found:', !!voiceBtn);
        if (voiceBtn) {
            console.log('[ATTACHMENT_UI] Setting up voice button event listeners');
            // Mouse events for desktop
            voiceBtn.addEventListener('mousedown', (e) => {
                console.log('[ATTACHMENT_UI] Voice button mousedown triggered');
                e.preventDefault();
                this.startVoiceRecording();
            });
            
            voiceBtn.addEventListener('mouseup', () => {
                this.stopVoiceRecording();
            });
            
            voiceBtn.addEventListener('mouseleave', () => {
                this.stopVoiceRecording();
            });
            
            // Touch events for mobile with swipe detection
            voiceBtn.addEventListener('touchstart', (e) => {
                console.log('[ATTACHMENT_UI] Voice button touchstart triggered');
                e.preventDefault();
                const touch = e.touches[0];
                this.handleVoiceTouchStart(touch.clientY);
            });
            
            voiceBtn.addEventListener('touchmove', (e) => {
                e.preventDefault();
                const touch = e.touches[0];
                this.handleVoiceTouchMove(touch.clientY);
            });
            
            voiceBtn.addEventListener('touchend', (e) => {
                e.preventDefault();
                this.handleVoiceTouchEnd();
            });
        }

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

        // Voice recording actions
        const voiceSend = document.getElementById('voiceSend');
        const voiceDelete = document.getElementById('voiceDelete');
        const voicePlayPause = document.getElementById('voicePlayPause');
        const voiceStop = document.getElementById('voiceStop');
        const voiceClose = document.getElementById('voiceClose');

        if (voiceSend) {
            voiceSend.addEventListener('click', () => {
                this.sendVoiceRecording();
            });
        }

        if (voiceDelete) {
            voiceDelete.addEventListener('click', () => {
                this.discardVoiceRecording();
            });
        }

        if (voicePlayPause) {
            voicePlayPause.addEventListener('click', () => {
                this.playPauseVoiceRecording();
            });
        }

        if (voiceStop) {
            voiceStop.addEventListener('click', () => {
                this.stopLockedVoiceRecording();
            });
        }

        if (voiceClose) {
            voiceClose.addEventListener('click', () => {
                this.closeVoiceRecordingPreview();
            });
        }

        // Overlay click to close modals
        if (this.overlay) {
            this.overlay.addEventListener('click', () => {
                this.hideAttachmentModal();
                this.hideVoiceRecordingPreview();
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

        eventBus.on(EVENTS.VOICE_START, () => {
            this.showVoiceRecordingPreview();
            this.updateVoiceStatus('Recording...');
        });

        eventBus.on(EVENTS.VOICE_STOP, (data) => {
            this.updateVoiceRecordingPreview(data);
            this.updateVoiceStatus('Tap to play');
            this.showStopButton(false);
        });

        eventBus.on(EVENTS.VOICE_DISCARD, () => {
            this.hideVoiceRecordingPreview();
            this.resetVoiceButton();
        });

        eventBus.on(EVENTS.VOICE_LOCKED, () => {
            this.updateVoiceRecordingUI();
            this.updateVoiceStatus('Recording locked - Swipe up or tap stop');
            this.showStopButton(true);
        });

        eventBus.on(EVENTS.VOICE_PLAYING, () => {
            this.updatePlayPauseButton(true);
        });

        eventBus.on(EVENTS.VOICE_PAUSED, () => {
            this.updatePlayPauseButton(false);
        });

        eventBus.on(EVENTS.VOICE_PLAYBACK_ENDED, () => {
            this.updatePlayPauseButton(false);
        });

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
     * Start voice recording
     */
    startVoiceRecording() {
        console.log('[ATTACHMENT_UI] startVoiceRecording called');
        eventBus.emit(EVENTS.VOICE_START);
    }

    /**
     * Stop voice recording
     */
    stopVoiceRecording() {
        eventBus.emit(EVENTS.VOICE_STOP);
    }

    /**
     * Handle voice touch start
     */
    handleVoiceTouchStart(clientY) {
        console.log('[ATTACHMENT_UI] handleVoiceTouchStart called with clientY:', clientY);
        this.startVoiceRecording();
        // Forward touch position to voice service for swipe detection
        if (window.voiceService) {
            window.voiceService.handleTouchStart(clientY);
        }
    }

    /**
     * Handle voice touch move
     */
    handleVoiceTouchMove(clientY) {
        // Forward touch position to voice service for swipe detection
        if (window.voiceService) {
            window.voiceService.handleTouchMove(clientY);
        }
    }

    /**
     * Handle voice touch end
     */
    handleVoiceTouchEnd() {
        // Check if recording is locked, if not, stop it
        if (window.voiceService && !window.voiceService.isLocked) {
            this.stopVoiceRecording();
        }
    }

    /**
     * Send voice recording
     */
    sendVoiceRecording() {
        eventBus.emit(EVENTS.VOICE_SEND);
    }

    /**
     * Discard voice recording
     */
    discardVoiceRecording() {
        eventBus.emit(EVENTS.VOICE_DISCARD);
    }

    /**
     * Play/pause voice recording
     */
    playPauseVoiceRecording() {
        eventBus.emit(EVENTS.VOICE_PLAY_PAUSE);
    }

    /**
     * Show voice recording preview
     */
    showVoiceRecordingPreview() {
        if (this.voiceRecordingPreview && this.overlay) {
            this.voiceRecordingPreview.classList.add('show');
            this.overlay.classList.add('show');
        }
    }

    /**
     * Hide voice recording preview
     */
    hideVoiceRecordingPreview() {
        if (this.voiceRecordingPreview && this.overlay) {
            this.voiceRecordingPreview.classList.remove('show');
            this.overlay.classList.remove('show');
        }
    }

    /**
     * Update voice recording preview
     * @param {Object} data - Voice recording data
     */
    updateVoiceRecordingPreview(data) {
        const voiceTimer = document.getElementById('voiceTimer');
        if (voiceTimer && data.duration) {
            const minutes = Math.floor(data.duration / 60);
            const seconds = data.duration % 60;
            voiceTimer.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }

        // Generate waveform visualization
        this.generateWaveform();
    }

    /**
     * Stop locked voice recording
     */
    stopLockedVoiceRecording() {
        if (window.voiceService) {
            window.voiceService.stopLockedRecording();
        }
    }

    /**
     * Close voice recording preview
     */
    closeVoiceRecordingPreview() {
        if (window.voiceService && window.voiceService.isRecording) {
            // If still recording, discard it
            this.discardVoiceRecording();
        } else {
            // If not recording, just close the preview
            this.hideVoiceRecordingPreview();
        }
    }

    /**
     * Update voice status text
     */
    updateVoiceStatus(status) {
        const voiceStatus = document.getElementById('voiceStatus');
        if (voiceStatus) {
            voiceStatus.textContent = status;
        }
    }

    /**
     * Show/hide stop button
     */
    showStopButton(show) {
        const voiceStop = document.getElementById('voiceStop');
        if (voiceStop) {
            voiceStop.style.display = show ? 'flex' : 'none';
        }
    }

    /**
     * Reset voice button state
     */
    resetVoiceButton() {
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn) {
            voiceBtn.innerHTML = '<i class="bi bi-mic"></i>';
            voiceBtn.style.color = '';
        }
    }

    /**
     * Update voice recording UI for locked state
     */
    updateVoiceRecordingUI() {
        const voiceBtn = document.getElementById('voiceBtn');
        if (voiceBtn && window.voiceService && window.voiceService.isLocked) {
            voiceBtn.innerHTML = '<i class="bi bi-lock-fill"></i>';
            voiceBtn.style.color = '#dc3545';
        }
    }

    /**
     * Update play/pause button
     * @param {boolean} isPlaying - Whether audio is playing
     */
    updatePlayPauseButton(isPlaying) {
        const voicePlayPause = document.getElementById('voicePlayPause');
        if (voicePlayPause) {
            const icon = voicePlayPause.querySelector('i');
            if (isPlaying) {
                icon.className = 'bi bi-pause-fill';
            } else {
                icon.className = 'bi bi-play-fill';
            }
        }
    }

    /**
     * Generate waveform visualization
     */
    generateWaveform() {
        const waveformContainer = document.getElementById('voiceWaveformContainer');
        if (!waveformContainer) return;

        // Clear existing bars
        waveformContainer.innerHTML = '';

        // Generate random waveform bars
        const barCount = 30;
        for (let i = 0; i < barCount; i++) {
            const bar = document.createElement('div');
            bar.className = 'voice-recording-bar';
            bar.style.height = Math.random() * 40 + 10 + 'px';
            waveformContainer.appendChild(bar);
        }

        // Animate waveform bars
        this.animateWaveform();
    }

    /**
     * Animate waveform bars
     */
    animateWaveform() {
        const bars = document.querySelectorAll('.voice-recording-bar');
        if (bars.length === 0) return;

        const animate = () => {
            bars.forEach(bar => {
                if (window.voiceService && window.voiceService.isRecording) {
                    const currentHeight = parseInt(bar.style.height);
                    const newHeight = Math.random() * 40 + 10;
                    bar.style.height = newHeight + 'px';
                }
            });

            if (window.voiceService && window.voiceService.isRecording) {
                requestAnimationFrame(animate);
            }
        };

        animate();
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
