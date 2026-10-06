/**
 * CaptionInput - Handles unified floating caption input in the media composer
 */

export class CaptionInput {
    constructor(composer) {
        this.composer = composer;
        this.unifiedInput = null;
        this.globalContainer = null;
        this.mediaContainer = null;
        this.globalInput = null;
        this.mediaInput = null;
        this.isGlobalMode = false;
        this.initialized = false;
    }
    
    /**
     * Initialize caption input
     */
    init() {
        this.unifiedInput = document.getElementById('mediaCaptionInput');
        this.globalContainer = document.getElementById('mediaComposerGlobalCaption');
        this.mediaContainer = document.getElementById('mediaComposerMediaCaption');
        
        if (this.unifiedInput) {
            this.unifiedInput.addEventListener('input', (e) => {
                this.composer.updateMediaCaption(e.target.value);
                this.composer.updateGlobalCaption(e.target.value);
            });
        }
        
        if (this.globalContainer) {
            this.globalInput = this.globalContainer.querySelector('textarea');
            if (this.globalInput) {
                this.globalInput.addEventListener('input', (e) => {
                    this.composer.updateGlobalCaption(e.target.value);
                });
            }
        }
        
        if (this.mediaContainer) {
            this.mediaInput = this.mediaContainer.querySelector('textarea');
            if (this.mediaInput) {
                this.mediaInput.addEventListener('input', (e) => {
                    this.composer.updateMediaCaption(e.target.value);
                });
            }
        }
        
        this.initialized = true;
        console.log('[CAPTION_INPUT] Unified caption input initialized');
    }
    
    /**
     * Set global caption
     * @param {string} caption - Global caption text
     */
    setGlobalCaption(caption) {
        if (this.unifiedInput && !this.unifiedInput.value) {
            this.unifiedInput.value = caption || '';
        }
        if (this.globalInput) {
            this.globalInput.value = caption || '';
        }
    }
    
    /**
     * Set media caption
     * @param {string} caption - Media-specific caption text
     */
    setMediaCaption(caption) {
        if (this.unifiedInput) {
            this.unifiedInput.value = caption || '';
        }
        if (this.mediaInput) {
            this.mediaInput.value = caption || '';
        }
    }
    
    /**
     * Switch to global caption mode
     */
    showGlobalCaption() {
        this.isGlobalMode = true;
    }
    
    /**
     * Switch to media caption mode
     */
    showMediaCaption() {
        this.isGlobalMode = false;
    }
    
    /**
     * Get current caption
     * @returns {string} Current caption text
     */
    getCurrentCaption() {
        if (this.unifiedInput) {
            return this.unifiedInput.value;
        }
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
        if (this.unifiedInput) {
            this.unifiedInput.value = '';
        }
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
