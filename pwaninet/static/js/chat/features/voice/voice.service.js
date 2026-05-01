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
    this.audioBlob = null;
    this.audioUrl = null;
    this.duration = 0;
    this.timerInterval = null;
  }

  /**
   * Initialize voice service
   */
  init() {
    this.setupEventListeners();
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    eventBus.on(EVENTS.VOICE_START, () => {
      this.startRecording();
    });

    eventBus.on(EVENTS.VOICE_STOP, () => {
      this.stopRecording();
    });

    eventBus.on(EVENTS.VOICE_SEND, () => {
      this.sendRecording();
    });
  }

  /**
   * Start recording
   */
  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (e) => {
        this.audioChunks.push(e.data);
      };

      this.mediaRecorder.onstop = () => {
        this.audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.audioUrl = URL.createObjectURL(this.audioBlob);
        eventBus.emit(EVENTS.VOICE_STOP, {
          blob: this.audioBlob,
          url: this.audioUrl,
          duration: this.duration,
        });
      };

      this.mediaRecorder.start();
      this.isRecording = true;
      this.duration = 0;
      this.startTimer();

      eventBus.emit(EVENTS.VOICE_START);
    } catch (error) {
      console.error('Voice recording error:', error);
      eventBus.emit(EVENTS.VOICE_ERROR, error);
    }
  }

  /**
   * Stop recording
   */
  stopRecording() {
    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop();
      this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
      this.isRecording = false;
      this.stopTimer();
    }
  }

  /**
   * Start timer
   */
  startTimer() {
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
   * Send recording
   */
  sendRecording() {
    if (this.audioBlob) {
      const file = new File([this.audioBlob], 'voice.webm', { type: 'audio/webm' });
      eventBus.emit(EVENTS.ATTACHMENT_SELECTED, file);
      this.discardRecording();
    }
  }

  /**
   * Discard recording
   */
  discardRecording() {
    this.audioBlob = null;
    this.audioChunks = [];
    if (this.audioUrl) {
      URL.revokeObjectURL(this.audioUrl);
      this.audioUrl = null;
    }
    this.duration = 0;
    eventBus.emit(EVENTS.VOICE_DISCARD);
  }

  /**
   * Get recording state
   * @returns {Object} Recording state
   */
  getState() {
    return {
      isRecording: this.isRecording,
      duration: this.duration,
      hasRecording: !!this.audioBlob,
    };
  }
}

// Create global instance
export const voiceService = new VoiceService();
