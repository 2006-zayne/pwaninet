/**
 * VoiceService - Voice recording logic
 * Pure service layer, no DOM manipulation
 */

import { EVENTS } from '../../shared/constants.js';
import { eventBus } from '../../core/event-bus.js';

export class VoiceService {
  constructor() {
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.isRecording = false;
    this.isLocked = false;
    this.audioBlob = null;
    this.audioUrl = null;
    this.duration = 0;
    this.timerInterval = null;
    this.touchStartY = 0;
    this.touchCurrentY = 0;
    this.isSwipingUp = false;
    this.audioElement = null;
    this.isPlaying = false;
    this.audioContext = null;
    this.analyser = null;
    this.dataArray = null;
    this.source = null;
  }

  /**
   * Initialize voice service
   */
  init() {
    console.log('[VOICE_SERVICE] Voice service initializing...');
    this.setupEventListeners();
    console.log('[VOICE_SERVICE] Voice service initialized');
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    console.log('[VOICE_SERVICE] Setting up event listeners');
    eventBus.on(EVENTS.VOICE_START, () => {
      console.log('[VOICE_SERVICE] VOICE_START event received');
      this.startRecording();
    });

    eventBus.on(EVENTS.VOICE_STOP, () => {
      console.log('[VOICE_SERVICE] VOICE_STOP event received');
      this.stopRecording();
    });

    eventBus.on(EVENTS.VOICE_SEND, () => {
      console.log('[VOICE_SERVICE] VOICE_SEND event received');
      this.sendRecording();
    });

    eventBus.on(EVENTS.VOICE_LOCK, () => {
      console.log('[VOICE_SERVICE] VOICE_LOCK event received');
      this.lockRecording();
    });

    eventBus.on(EVENTS.VOICE_PLAY_PAUSE, () => {
      console.log('[VOICE_SERVICE] VOICE_PLAY_PAUSE event received');
      this.togglePlayPause();
    });
  }

  /**
   * Start recording
   */
  async startRecording() {
    console.log('[VOICE_SERVICE] startRecording() called');
    try {
      console.log('[VOICE_SERVICE] Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('[VOICE_SERVICE] Microphone access granted');
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      // Set up Web Audio API for frequency analysis
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.source = this.audioContext.createMediaStreamSource(stream);
      this.source.connect(this.analyser);
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      this.mediaRecorder.ondataavailable = (e) => {
        console.log('[VOICE_SERVICE] Audio data available');
        this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        console.log('[VOICE_SERVICE] Recording stopped');
        this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.audioUrl = URL.createObjectURL(this.audioBlob);
        this.cleanupAudioContext();
        eventBus.emit(EVENTS.VOICE_STOP, {
          blob: this.audioBlob,
          url: this.audioUrl,
          duration: this.duration,
        });
      };

      this.mediaRecorder.start();
      this.isRecording = true;
      this.isLocked = false;
      this.duration = 0;
      this.startTimer();
      this.startFrequencyAnalysis();

      console.log('[VOICE_SERVICE] Recording started successfully');
    } catch (error) {
      console.error('[VOICE_SERVICE] Voice recording error:', error);
      eventBus.emit(EVENTS.VOICE_ERROR, error);
    }
  }

  /**
   * Stop recording
   */
  stopRecording() {
    console.log('[VOICE_SERVICE] stopRecording() called, isRecording:', this.isRecording, 'isLocked:', this.isLocked);
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      this.isRecording = false;
      this.isLocked = false;
      this.stopTimer();
      this.stopFrequencyAnalysis();
    }
    console.log('[VOICE_SERVICE] Recording stopped');
  }

  /**
   * Lock recording (continue recording without holding)
   */
  lockRecording() {
    if (this.isRecording) {
      this.isLocked = true;
      eventBus.emit(EVENTS.VOICE_LOCKED);
    }
  }

  /**
   * Stop locked recording
   */
  stopLockedRecording() {
    this.stopRecording();
  }

  /**
   * Handle touch start for swipe detection
   */
  handleTouchStart(y) {
    this.touchStartY = y;
    this.touchCurrentY = y;
    this.isSwipingUp = false;
  }

  /**
   * Handle touch move for swipe detection
   */
  handleTouchMove(y) {
    this.touchCurrentY = y;
    const deltaY = this.touchStartY - this.touchCurrentY;
    
    // Swipe up detection (threshold of 50px)
    if (deltaY > 50 && !this.isSwipingUp && this.isRecording) {
      this.isSwipingUp = true;
      this.lockRecording();
    }
  }

  /**
   * Play/pause audio recording
   */
  togglePlayPause() {
    if (!this.audioUrl) return;

    if (!this.audioElement) {
      this.audioElement = new Audio(this.audioUrl);
      this.audioElement.addEventListener('ended', () => {
        this.isPlaying = false;
        eventBus.emit(EVENTS.VOICE_PLAYBACK_ENDED);
      });
    }

    if (this.isPlaying) {
      this.audioElement.pause();
      this.isPlaying = false;
      eventBus.emit(EVENTS.VOICE_PAUSED);
    } else {
      this.audioElement.play();
      this.isPlaying = true;
      eventBus.emit(EVENTS.VOICE_PLAYING);
    }
  }

  /**
   * Stop audio playback
   */
  stopPlayback() {
    if (this.audioElement && this.isPlaying) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
      this.isPlaying = false;
      eventBus.emit(EVENTS.VOICE_PLAYBACK_STOPPED);
    }
  }

  /**
   * Start timer
   */
  startTimer() {
    // Clear any existing timer first
    this.stopTimer();
    this.duration = 0;
    this.timerInterval = setInterval(() => {
      this.duration++;
      eventBus.emit(EVENTS.VOICE_TIMER_UPDATE, this.duration);
    }, 1000);
  }

  /**
   * Stop timer
   */
  stopTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  /**
   * Start frequency analysis for waveform
   */
  startFrequencyAnalysis() {
    if (!this.analyser) return;
    
    const analyze = () => {
      if (!this.isRecording || !this.analyser) return;
      
      this.analyser.getByteFrequencyData(this.dataArray);
      
      // Calculate average frequency for waveform
      let sum = 0;
      for (let i = 0; i < this.dataArray.length; i++) {
        sum += this.dataArray[i];
      }
      const average = sum / this.dataArray.length;
      
      // Emit frequency data for waveform animation
      eventBus.emit(EVENTS.VOICE_FREQUENCY_UPDATE, {
        dataArray: this.dataArray,
        average: average
      });
      
      requestAnimationFrame(analyze);
    };
    
    analyze();
  }

  /**
   * Stop frequency analysis
   */
  stopFrequencyAnalysis() {
    // Frequency analysis stops automatically when isRecording is false
  }

  /**
   * Clean up audio context
   */
  cleanupAudioContext() {
    if (this.source) {
      this.source.disconnect();
      this.source = null;
    }
    if (this.analyser) {
      this.analyser.disconnect();
      this.analyser = null;
    }
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.dataArray = null;
  }

  /**
   * Send recording
   */
  sendRecording() {
    if (this.audioBlob) {
      const file = new File([this.audioBlob], 'voice.webm', { type: 'audio/webm' });
      
      // Get conversation ID and upload through attachment service
      const conversationId = this._getConversationId();
      if (conversationId) {
        // Import attachment service to avoid circular dependency
        import('../attachments/attachment.service.js').then(({ attachmentService }) => {
          attachmentService.handleFileUpload(file, conversationId);
        });
      }
      
      this.discardRecording();
    }
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
   * Discard recording
   */
  discardRecording() {
    console.log('[VOICE_SERVICE] discardRecording() called, isRecording:', this.isRecording);
    
    // Stop recording if currently recording
    if (this.isRecording && this.mediaRecorder) {
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      this.isRecording = false;
      this.stopTimer();
      this.stopFrequencyAnalysis();
    }
    
    this.cleanupAudioContext();
    this.stopPlayback();
    this.audioBlob = null;
    this.audioChunks = [];
    if (this.audioUrl) {
      URL.revokeObjectURL(this.audioUrl);
      this.audioUrl = null;
    }
    if (this.audioElement) {
      this.audioElement = null;
    }
    this.duration = 0;
    this.isLocked = false;
    this.isSwipingUp = false;
    eventBus.emit(EVENTS.VOICE_DISCARD);
  }

  /**
   * Get recording state
   * @returns {Object} Recording state
   */
  getState() {
    return {
      isRecording: this.isRecording,
      isLocked: this.isLocked,
      isPlaying: this.isPlaying,
      duration: this.duration,
      hasRecording: !!this.audioBlob,
    };
  }
}

// Create global instance
export const voiceService = new VoiceService();
