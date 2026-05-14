/**
 * Message Sound Manager
 * Handles subtle send confirmation sounds for messaging
 * Only plays when queued/sending → sent transition occurs
 * 
 * Architecture:
 * - Preloads audio buffer during initialization
 * - Unlocks audio context on first user interaction
 * - Plays preloaded sound instantly on valid transitions
 * - Prevents replay during reconciliation/hydration
 */

export class MessageSoundManager {
    constructor() {
        this.audioContext = null;
        this.audioBuffer = null;
        this.enabled = true;
        this.initialized = false;
        this.unlocked = false;
        this.playedMessageIds = new Set(); // Track played messages to prevent replay
    }

    /**
     * Initialize audio context and preload sound buffer
     * Should be called during app initialization
     */
    async init() {
        if (this.initialized) return;

        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Preload the sound buffer
            this.audioBuffer = this._createSendSoundBuffer();
            
            this.initialized = true;
            console.log('[MESSAGE_SOUND] Audio context initialized and sound buffer preloaded');
        } catch (error) {
            console.warn('[MESSAGE_SOUND] Audio context not supported:', error);
            this.enabled = false;
        }
    }

    /**
     * Unlock audio context on first user interaction
     * Must be called after user interaction (click, keyboard, etc.)
     */
    async unlock() {
        if (!this.initialized || this.unlocked) return;

        try {
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            this.unlocked = true;
            console.log('[MESSAGE_SOUND] Audio context unlocked');
        } catch (error) {
            console.warn('[MESSAGE_SOUND] Failed to unlock audio context:', error);
        }
    }

    /**
     * Create preloaded audio buffer for send sound
     * Subtle, tactile pop-like sound (~60ms duration)
     * @returns {AudioBuffer} Preloaded audio buffer
     */
    _createSendSoundBuffer() {
        if (!this.audioContext) return null;

        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.06; // 60ms
        const frameCount = sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, frameCount, sampleRate);
        const data = buffer.getChannelData(0);

        // Generate subtle pop sound
        for (let i = 0; i < frameCount; i++) {
            const t = i / sampleRate;
            
            // Frequency sweep from 800Hz to 400Hz
            const frequency = 800 * Math.exp(-t * 20);
            
            // Envelope: quick attack, exponential decay
            let envelope = 0;
            if (t < 0.01) {
                envelope = t / 0.01; // Attack
            } else if (t < 0.05) {
                envelope = 0.15 * Math.exp(-(t - 0.01) * 40); // Decay
            } else {
                envelope = 0;
            }
            
            data[i] = Math.sin(2 * Math.PI * frequency * t) * envelope;
        }

        return buffer;
    }

    /**
     * Play preloaded send sound instantly
     * @param {string} messageId - Optional message ID to prevent replay
     */
    playSendSound(messageId = null) {
        if (!this.enabled || !this.initialized || !this.audioBuffer) {
            return;
        }

        // Prevent replay for the same message
        if (messageId && this.playedMessageIds.has(messageId)) {
            return;
        }

        try {
            const source = this.audioContext.createBufferSource();
            source.buffer = this.audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();

            // Track message ID to prevent replay
            if (messageId) {
                this.playedMessageIds.add(messageId);
                // Clean up old entries after 5 seconds
                setTimeout(() => {
                    this.playedMessageIds.delete(messageId);
                }, 5000);
            }

            console.log('[MESSAGE_SOUND] Send sound played');
        } catch (error) {
            console.warn('[MESSAGE_SOUND] Failed to play sound:', error);
        }
    }

    /**
     * Check if sound should play for a state transition
     * Only plays when: previousState !== "sent" AND newState === "sent"
     * @param {string} fromState - Previous state
     * @param {string} toState - New state
     * @returns {boolean} True if sound should play
     */
    shouldPlaySound(fromState, toState) {
        // Only play when transitioning TO sent state
        if (toState !== 'sent') {
            return false;
        }

        // Don't play if already in sent state (prevents replay)
        if (fromState === 'sent') {
            return false;
        }

        // Only play from valid pre-sent states
        const validFromStates = ['queued', 'sending', 'uploading', 'processing', 'draft'];
        return validFromStates.includes(fromState);
    }

    /**
     * Enable/disable sounds
     * @param {boolean} enabled - Whether sounds are enabled
     */
    setEnabled(enabled) {
        this.enabled = enabled;
    }

    /**
     * Check if sounds are enabled
     * @returns {boolean}
     */
    isEnabled() {
        return this.enabled;
    }

    /**
     * Check if audio is unlocked and ready to play
     * @returns {boolean}
     */
    isReady() {
        return this.initialized && this.unlocked;
    }
}

// Export singleton instance
export const messageSoundManager = new MessageSoundManager();
