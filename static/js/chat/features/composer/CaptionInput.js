/**
 * CaptionInput - Handles global and per-media caption inputs
 * Switches between global and media-specific caption contexts
 */

export class CaptionInput {
    constructor(composer) {
        this.composer = composer;
        this.globalContainer = null;
        this.mediaContainer = null;
        this.globalInput = null;
        this.mediaInput = null;
        this.isGlobalMode = true;
        
        this.initialized = false;
    }
    
    /**
     * Initialize caption input
     */
    init() {
        this.globalContainer = document.getElementById('mediaComposerGlobalCaption');
        this.mediaContainer = document.getElementById('mediaComposerMediaCaption');
        
        if (this.globalContainer) {
            this.globalInput = this.globalContainer.querySelector('textarea');
            this.globalInput.addEventListener('input', (e) => {
                this.composer.updateGlobalCaption(e.target.value);
            });
        }
        
        if (this.mediaContainer) {
            this.mediaInput = this.mediaContainer.querySelector('textarea');
            this.mediaInput.addEventListener('input', (e) => {
                this.composer.updateMediaCaption(e.target.value);
            });
        }
        
        this.initialized = true;
        console.log('[CAPTION_INPUT] Caption input initialized');
    }
    
    /**
     * Set global caption
     * @param {string} caption - Global caption text
     */
    setGlobalCaption(caption) {
        if (this.globalInput) {
            this.globalInput.value = caption;
        }
    }
    
    /**
     * Set media caption
     * @param {string} caption - Media-specific caption text
     */
    setMediaCaption(caption) {
        if (this.mediaInput) {
            this.mediaInput.value = caption;
        }
    }
    
    /**
     * Switch to global caption mode
     */
    showGlobalCaption() {
        if (this.globalContainer) {
            this.globalContainer.style.display = 'block';
        }
        if (this.mediaContainer) {
            this.mediaContainer.style.display = 'none';
        }
        this.isGlobalMode = true;
    }
    
    /**
     * Switch to media caption mode
     */
    showMediaCaption() {
        if (this.globalContainer) {
            this.globalContainer.style.display = 'none';
        }
        if (this.mediaContainer) {
            this.mediaContainer.style.display = 'block';
        }
        this.isGlobalMode = false;
    }
    
    /**
     * Get current caption
     * @returns {string} Current caption text
     */
    getCurrentCaption() {
        if (this.isGlobalMode && this.globalInput) {
            return this.globalInput.value;
        } else if (!this.isGlobalMode && this.mediaInput) {
            return this.mediaInput.value;
        }
        return '';
    }
    
    /**
     * Clear all captions
     */
    clear() {
        if (this.globalInput) {
            this.globalInput.value = '';
        }
        if (this.mediaInput) {
            this.mediaInput.value = '';
        }
    }
    
    /**
     * Destroy caption input
     */
    destroy() {
        this.clear();
        this.initialized = false;
        console.log('[CAPTION_INPUT] Caption input destroyed');
    }
}
