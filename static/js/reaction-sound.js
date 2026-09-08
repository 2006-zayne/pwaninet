/**
 * Reaction Sound Manager
 * Handles subtle sound feedback for post likes and other reactions
 * 
 * Architecture:
 * - Uses Web Audio API (no external audio files)
 * - Generates sounds programmatically
 * - Unlocks audio context on first user interaction with silent oscillator
 * - Forces context resume before each playback (mobile fix)
 * - Handles PWA resume events
 * - Prevents duplicate playback with cooldown
 * - Respects accessibility preferences
 * - Failure-safe (never breaks core functionality)
 */

class ReactionSoundManager {
    constructor() {
        this.audioContext = null;
        this.audioBuffer = null;
        this.enabled = true;
        this.initialized = false;
        this.unlocked = false;
        this.lastPlayed = 0;
        this.cooldownMs = 150; // Prevent rapid duplicate sounds
    }

    /**
     * Initialize audio context and preload sound buffer
     * Should be called during app initialization
     */
    async init() {
        if (this.initialized) return;

        // Check for reduced motion preference
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            console.log('[REACTION_SOUND] Sounds disabled due to reduced motion preference');
            this.enabled = false;
            return;
        }

        // Check for user settings override
        if (window.PwaniSettings && window.PwaniSettings.soundsEnabled === false) {
            console.log('[REACTION_SOUND] Sounds disabled via user settings');
            this.enabled = false;
            return;
        }

        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            console.log('[REACTION_SOUND] Audio context created, state:', this.audioContext.state);
            
            // Preload Like sound buffer
            this.audioBuffer = this._createLikeSoundBuffer();
            
            this.initialized = true;
            console.log('[REACTION_SOUND] Audio context initialized and sound buffer preloaded');
        } catch (error) {
            console.warn('[REACTION_SOUND] Audio context not supported:', error);
            this.enabled = false;
        }
    }

    /**
     * Unlock audio context on first user interaction
     * Uses silent oscillator technique to establish audio permission
     * Must be called after user interaction (click, touch, keyboard)
     */
    async unlock() {
        if (!this.initialized || this.unlocked) {
            console.log('[REACTION_SOUND] Unlock skipped - initialized:', this.initialized, 'unlocked:', this.unlocked);
            return;
        }

        try {
            console.log('[REACTION_SOUND] Unlock event fired, current state:', this.audioContext.state);
            
            // Resume context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
                console.log('[REACTION_SOUND] Context resumed, state:', this.audioContext.state);
            }

            // Play silent oscillator to establish audio permission
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            // Very low volume, inaudible
            gainNode.gain.value = 0.001;
            oscillator.frequency.value = 440;
            
            oscillator.start();
            oscillator.stop(this.audioContext.currentTime + 0.01); // 10ms silent play
            
            this.unlocked = true;
            console.log('[REACTION_SOUND] Audio context unlocked with silent oscillator');
        } catch (error) {
            console.warn('[REACTION_SOUND] Failed to unlock audio context:', error);
        }
    }

    /**
     * Create preloaded audio buffer for Like sound
     * TEMPORARY: Increased parameters for testing
     * Duration: 120ms (was 70ms)
     * Gain: 0.4 (was 0.15)
     * Frequency: 1000Hz (was 600-900Hz)
     * @returns {AudioBuffer} Preloaded audio buffer
     */
    _createLikeSoundBuffer() {
        if (!this.audioContext) return null;

        const sampleRate = this.audioContext.sampleRate;
        const duration = 0.12; // 120ms (TEMPORARY for testing)
        const frameCount = sampleRate * duration;
        const buffer = this.audioContext.createBuffer(1, frameCount, sampleRate);
        const data = buffer.getChannelData(0);

        // Generate pop with upward pitch sweep
        for (let i = 0; i < frameCount; i++) {
            const t = i / sampleRate;
            
            // Frequency sweep from 800Hz to 1200Hz (TEMPORARY for testing)
            const frequency = 800 + (400 * (t / duration));
            
            // Envelope: quick attack, exponential decay
            let envelope = 0;
            if (t < 0.01) {
                envelope = t / 0.01; // Attack (10ms)
            } else if (t < 0.1) {
                envelope = 0.4 * Math.exp(-(t - 0.01) * 30); // Decay (90ms)
            } else {
                envelope = 0;
            }
            
            data[i] = Math.sin(2 * Math.PI * frequency * t) * envelope;
        }

        return buffer;
    }

    /**
     * Play Like sound
     * Enforces cooldown to prevent duplicate playback
     * Forces context resume before playback (mobile fix)
     */
    async playLike() {
        console.log('[REACTION_SOUND] ===== playLike called =====');
        console.log('[REACTION_SOUND] enabled:', this.enabled);
        console.log('[REACTION_SOUND] initialized:', this.initialized);
        console.log('[REACTION_SOUND] unlocked:', this.unlocked);
        console.log('[REACTION_SOUND] audioContext exists:', !!this.audioContext);
        console.log('[REACTION_SOUND] audioBuffer exists:', !!this.audioBuffer);
        
        if (this.audioContext) {
            console.log('[REACTION_SOUND] audioContext.state:', this.audioContext.state);
        }
        
        if (!this.enabled || !this.initialized || !this.audioBuffer) {
            console.log('[REACTION_SOUND] playLike ABORTED - prerequisites not met');
            return;
        }

        // Check cooldown
        const now = Date.now();
        if (now - this.lastPlayed < this.cooldownMs) {
            console.log('[REACTION_SOUND] playLike ABORTED - cooldown active');
            return;
        }

        // Trigger subtle tactile haptic feedback
        if (window.Haptics && typeof window.Haptics.impactLight === 'function') {
            window.Haptics.impactLight();
        }

        try {
            // Force context resume before playback (mobile browsers suspend frequently)
            console.log('[REACTION_SOUND] Audio state before resume:', this.audioContext.state);
            if (this.audioContext.state === 'suspended') {
                console.log('[REACTION_SOUND] Attempting to resume audio context...');
                await this.audioContext.resume();
                console.log('[REACTION_SOUND] Audio context resumed, state:', this.audioContext.state);
            }

            console.log('[REACTION_SOUND] Creating oscillator source...');
            const source = this.audioContext.createBufferSource();
            source.buffer = this.audioBuffer;
            
            // Create gain node for volume control
            const gainNode = this.audioContext.createGain();
            gainNode.gain.value = 0.4; // TEMPORARY: Increased for testing (was 0.15)
            
            // Connect: source -> gain -> destination
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            console.log('[REACTION_SOUND] Starting oscillator...');
            source.start();
            console.log('[REACTION_SOUND] Oscillator started successfully');
            
            // Update last played timestamp
            this.lastPlayed = now;

            console.log('[REACTION_SOUND] ===== Like sound played successfully =====');
        } catch (error) {
            console.error('[REACTION_SOUND] ===== FAILED to play sound =====');
            console.error('[REACTION_SOUND] Error:', error);
            console.error('[REACTION_SOUND] Error stack:', error.stack);
        }
    }

    /**
     * Handle PWA resume - attempt to resume audio context
     */
    async handleResume() {
        if (!this.initialized) return;
        
        try {
            console.log('[REACTION_SOUND] PWA resume detected, audio state:', this.audioContext.state);
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
                console.log('[REACTION_SOUND] Audio context resumed on PWA resume');
            }
        } catch (error) {
            console.warn('[REACTION_SOUND] Failed to resume audio on PWA resume:', error);
        }
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
const ReactionSound = new ReactionSoundManager();

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    ReactionSound.init();
});

// Unlock audio context on first user interaction
// Expanded event list for better mobile coverage
const unlockEvents = ['click', 'touchstart', 'keydown', 'pointerdown', 'pointerup', 'touchend', 'mousedown'];
const unlockHandler = function() {
    console.log('[REACTION_SOUND] Unlock event triggered:', event.type);
    ReactionSound.unlock();
    // Remove listeners after first unlock
    unlockEvents.forEach(evt => {
        document.removeEventListener(evt, unlockHandler);
    });
};

unlockEvents.forEach(eventType => {
    document.addEventListener(eventType, unlockHandler, { once: true, passive: true });
});

// Handle PWA resume events
['visibilitychange', 'pageshow', 'focus'].forEach(eventType => {
    window.addEventListener(eventType, function() {
        if (eventType === 'visibilitychange' && !document.hidden) {
            // Page became visible again
            ReactionSound.handleResume();
        } else if (eventType === 'pageshow' || eventType === 'focus') {
            // Page shown or window focused
            ReactionSound.handleResume();
        }
    });
});

// Make available globally for HTMX integration
window.ReactionSound = ReactionSound;
