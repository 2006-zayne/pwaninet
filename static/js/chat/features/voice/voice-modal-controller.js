/**
 * Voice Modal Controller
 * Simplified controller for the voice recording modal
 * Handles UI state transitions and user interactions
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';

export class VoiceModalController {
    constructor() {
        this.modal = null;
        this.overlay = null;
        this.closeBtn = null;
        
        // State elements
        this.recordingState = null;
        this.previewState = null;
        this.lockedState = null;
        
        // Timer elements
        this.timer = null;
        this.previewDuration = null;
        this.lockedTimer = null;
        
        // Waveform elements
        this.waveform = null;
        this.staticWaveform = null;
        this.lockedWaveform = null;
        
        // Control buttons
        this.deleteBtn = null;
        this.playPauseBtn = null;
        this.sendBtn = null;
        this.lockedDeleteBtn = null;
        this.lockedStopBtn = null;
        this.recordingDeleteBtn = null;
        this.recordingStopBtn = null;
        
        // Animation frame for waveform
        this.waveformAnimation = null;
        
        this.initialized = false;
    }
    
    /**
     * Initialize the voice modal controller
     */
    init() {
        if (this.initialized) return;
        
        this._initializeElements();
        this._setupEventListeners();
        this._setupServiceListeners();
        
        this.initialized = true;
        console.log('[VOICE_MODAL] Voice modal controller initialized');
    }
    
    /**
     * Initialize DOM elements
     */
    _initializeElements() {
        this.modal = document.getElementById('voiceModal');
        this.overlay = document.getElementById('voiceModalOverlay');
        this.closeBtn = document.getElementById('voiceModalClose');
        
        // State elements
        this.recordingState = document.getElementById('voiceRecordingState');
        this.previewState = document.getElementById('voicePreviewState');
        this.lockedState = document.getElementById('voiceLockedState');
        
        // Timer elements
        this.timer = document.getElementById('voiceTimer');
        this.previewDuration = document.getElementById('voicePreviewDuration');
        this.lockedTimer = document.getElementById('voiceLockedTimer');
        
        // Waveform elements
        this.waveform = document.getElementById('voiceWaveform');
        this.staticWaveform = document.getElementById('voiceWaveformStatic');
        this.lockedWaveform = document.getElementById('voiceLockedWaveform');
        
        // Control buttons
        this.deleteBtn = document.getElementById('voiceDelete');
        this.playPauseBtn = document.getElementById('voicePlayPause');
        this.sendBtn = document.getElementById('voiceSend');
        this.lockedDeleteBtn = document.getElementById('voiceLockedDelete');
        this.lockedStopBtn = document.getElementById('voiceLockedStop');
        this.recordingDeleteBtn = document.getElementById('voiceRecordingDelete');
        this.recordingStopBtn = document.getElementById('voiceRecordingStop');
    }
    
    /**
     * Setup UI event listeners
     */
    _setupEventListeners() {
        // Close button
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_DISCARD);
            });
        }
        
        // Overlay click
        if (this.overlay) {
            this.overlay.addEventListener('click', () => this.closeModal());
        }
        
        // Preview state controls
        if (this.deleteBtn) {
            this.deleteBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_DISCARD);
            });
        }
        
        if (this.playPauseBtn) {
            this.playPauseBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_PLAY_PAUSE);
            });
        }
        
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_SEND);
            });
        }
        
        // Locked state controls
        if (this.lockedDeleteBtn) {
            this.lockedDeleteBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_DISCARD);
            });
        }
        
        if (this.lockedStopBtn) {
            this.lockedStopBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_STOP);
            });
        }
        
        // Recording state controls
        if (this.recordingDeleteBtn) {
            this.recordingDeleteBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_DISCARD);
            });
        }
        
        if (this.recordingStopBtn) {
            this.recordingStopBtn.addEventListener('click', () => {
                eventBus.emit(EVENTS.VOICE_STOP);
            });
        }
    }
    
    /**
     * Setup service event listeners
     */
    _setupServiceListeners() {
        eventBus.on(EVENTS.VOICE_START, () => {
            this.showModal();
            this.showRecordingState();
            this.startWaveformAnimation();
        });
        
        eventBus.on(EVENTS.VOICE_STOP, (data) => {
            this.stopWaveformAnimation();
            this.showPreviewState(data?.duration || 0);
        });
        
        eventBus.on(EVENTS.VOICE_LOCK, () => {
            this.showLockedState();
        });
        
        eventBus.on(EVENTS.VOICE_LOCKED, () => {
            this.showLockedState();
        });
        
        eventBus.on(EVENTS.VOICE_TIMER_UPDATE, (duration) => {
            this.updateTimer(duration);
        });
        
        eventBus.on(EVENTS.VOICE_DISCARD, () => {
            this.closeModal();
            this.resetModal();
        });
        
        eventBus.on(EVENTS.VOICE_SEND, () => {
            this.closeModal();
            this.resetModal();
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
        
        eventBus.on(EVENTS.VOICE_FREQUENCY_UPDATE, (data) => {
            this.updateWaveformFromAudio(data);
        });
    }
    
    /**
     * Show the modal
     */
    showModal() {
        if (this.modal) {
            this.modal.classList.add('show');
        }
    }
    
    /**
     * Close the modal
     */
    closeModal() {
        if (this.modal) {
            this.modal.classList.remove('show');
        }
        this.stopWaveformAnimation();
    }
    
    /**
     * Reset the modal to initial state
     */
    resetModal() {
        this.stopWaveformAnimation();
        
        // Hide all states
        if (this.recordingState) this.recordingState.style.display = 'none';
        if (this.previewState) this.previewState.style.display = 'none';
        if (this.lockedState) this.lockedState.style.display = 'none';
        
        // Reset timers
        if (this.timer) this.timer.textContent = '0:00';
        if (this.previewDuration) this.previewDuration.textContent = '0:00';
        if (this.lockedTimer) this.lockedTimer.textContent = '0:00';
        
        // Reset play/pause button
        this.updatePlayPauseButton(false);
        
        // Clear waveforms
        if (this.waveform) this.waveform.innerHTML = '';
        if (this.staticWaveform) this.staticWaveform.innerHTML = '';
        if (this.lockedWaveform) this.lockedWaveform.innerHTML = '';
    }
    
    /**
     * Show recording state
     */
    showRecordingState() {
        this.hideAllStates();
        if (this.recordingState) {
            this.recordingState.style.display = 'flex';
        }
        this.generateWaveform(this.waveform);
    }
    
    /**
     * Show preview state
     */
    showPreviewState(duration) {
        this.hideAllStates();
        if (this.previewState) {
            this.previewState.style.display = 'flex';
        }
        if (this.previewDuration) {
            this.previewDuration.textContent = this.formatTime(duration);
        }
        this.generateStaticWaveform();
    }
    
    /**
     * Show locked state
     */
    showLockedState() {
        this.hideAllStates();
        if (this.lockedState) {
            this.lockedState.style.display = 'flex';
        }
        this.generateWaveform(this.lockedWaveform);
    }
    
    /**
     * Hide all states
     */
    hideAllStates() {
        if (this.recordingState) this.recordingState.style.display = 'none';
        if (this.previewState) this.previewState.style.display = 'none';
        if (this.lockedState) this.lockedState.style.display = 'none';
    }
    
    /**
     * Update timer display
     */
    updateTimer(duration) {
        const formatted = this.formatTime(duration);
        if (this.timer) this.timer.textContent = formatted;
        if (this.lockedTimer) this.lockedTimer.textContent = formatted;
    }
    
    /**
     * Format time as MM:SS
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }
    
    /**
     * Generate waveform bars
     */
    generateWaveform(container) {
        if (!container) return;
        container.innerHTML = '';
        
        const barCount = 40;
        for (let i = 0; i < barCount; i++) {
            const bar = document.createElement('div');
            bar.className = 'voice-waveform-bar';
            bar.style.height = Math.random() * 60 + 20 + 'px';
            container.appendChild(bar);
        }
    }
    
    /**
     * Generate static waveform for preview
     */
    generateStaticWaveform() {
        if (!this.staticWaveform) return;
        this.staticWaveform.innerHTML = '';
        
        const barCount = 40;
        for (let i = 0; i < barCount; i++) {
            const bar = document.createElement('div');
            bar.className = 'voice-waveform-bar';
            bar.style.height = Math.random() * 50 + 15 + 'px';
            this.staticWaveform.appendChild(bar);
        }
    }
    
    /**
     * Start waveform animation
     * Waveform is now driven by actual frequency data from voice service
     */
    startWaveformAnimation() {
        // Waveform animation is now driven by VOICE_FREQUENCY_UPDATE events
        // No need for random animation loop
    }
    
    /**
     * Stop waveform animation
     */
    stopWaveformAnimation() {
        if (this.waveformAnimation) {
            cancelAnimationFrame(this.waveformAnimation);
            this.waveformAnimation = null;
        }
    }
    
    /**
     * Update play/pause button icon
     */
    updatePlayPauseButton(isPlaying) {
        if (!this.playPauseBtn) return;
        
        const icon = this.playPauseBtn.querySelector('i');
        if (icon) {
            if (isPlaying) {
                icon.className = 'bi bi-pause-fill';
            } else {
                icon.className = 'bi bi-play-fill';
            }
        }
    }
    
    /**
     * Update waveform from actual audio frequency data
     */
    updateWaveformFromAudio(data) {
        const bars = document.querySelectorAll('.voice-waveform .voice-waveform-bar');
        if (!bars.length || !data.dataArray) return;
        
        const dataArray = data.dataArray;
        const step = Math.floor(dataArray.length / bars.length);
        
        bars.forEach((bar, index) => {
            const dataIndex = index * step;
            const value = dataArray[dataIndex] || 0;
            // Scale the value to a reasonable height (0-80px)
            const height = Math.max(5, (value / 255) * 80);
            bar.style.height = height + 'px';
        });
    }
    
    /**
     * Destroy the controller
     */
    destroy() {
        this.stopWaveformAnimation();
        this.initialized = false;
        console.log('[VOICE_MODAL] Voice modal controller destroyed');
    }
}

// Create and export singleton instance
export const voiceModalController = new VoiceModalController();
