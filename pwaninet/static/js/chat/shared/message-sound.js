/**
 * Message Sound Manager
 * Handles subtle send confirmation sounds for messaging
 * Only plays when queued/sending → sent transition occurs
 */

export class MessageSoundManager {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.initialized = false;
    }

    /**
     * Initialize audio context (must be called after user interaction)
     */
    async init() {
        if (this.initialized) return;

        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.initialized = true;
            console.log('[MESSAGE_SOUND] Audio context initialized');
        } catch (error) {
            console.warn('[MESSAGE_SOUND] Audio context not supported:', error);
            this.enabled = false;
        }
    }

    /**
     * Play subtle send confirmation sound
     * Soft, tactile pop-like sound
     */
    async playSendSound() {
        if (!this.enabled || !this.audioContext) {
            await this.init();
            if (!this.enabled) return;
        }

        try {
            // Resume audio context if suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            const now = this.audioContext.currentTime;

            // Create oscillator for the pop sound
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);

            // Configure the sound - soft, short, tactile pop
            oscillator.type = 'sine';
            oscillator.frequency.setValueAtTime(800, now);
            oscillator.frequency.exponentialRampToValueAtTime(400, now + 0.05);

            // Envelope for subtle pop
            gainNode.gain.setValueAtTime(0, now);
            gainNode.gain.linearRampToValueAtTime(0.15, now + 0.01);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.05);
            gainNode.gain.setValueAtTime(0, now + 0.06);

            oscillator.start(now);
            oscillator.stop(now + 0.06);

            console.log('[MESSAGE_SOUND] Send sound played');
        } catch (error) {
            console.warn('[MESSAGE_SOUND] Failed to play sound:', error);
        }
    }

    /**
     * Check if sound should play for a state transition
     * Only plays for: queued/sending → sent
     * @param {string} fromState - Previous state
     * @param {string} toState - New state
     * @returns {boolean} True if sound should play
     */
    shouldPlaySound(fromState, toState) {
        const validTransitions = [
            { from: 'queued', to: 'sent' },
            { from: 'sending', to: 'sent' }
        ];

        return validTransitions.some(
            transition => transition.from === fromState && transition.to === toState
        );
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
}

// Export singleton instance
export const messageSoundManager = new MessageSoundManager();
