/**
 * ToolRail - Contextual editing tools for media items
 * TikTok-style vertical tool rail that shows tools based on media type
 */

export class ToolRail {
    constructor(composer) {
        this.composer = composer;
        this.container = null;
        this.currentMediaType = null;
        
        // Tool configurations
        this.TOOLSETS = {
            image: [
                { id: 'crop', icon: 'crop', label: 'Crop' },
                { id: 'draw', icon: 'pencil', label: 'Draw' },
                { id: 'text', icon: 'type', label: 'Text' },
                { id: 'sticker', icon: 'smile', label: 'Sticker' },
                { id: 'emoji', icon: 'emoji-smile', label: 'Emoji' },
                { id: 'rotate', icon: 'arrow-clockwise', label: 'Rotate' },
                { id: 'adjust', icon: 'sliders', label: 'Adjust' },
            ],
            video: [
                { id: 'trim', icon: 'scissors', label: 'Trim' },
                { id: 'mute', icon: 'volume-x', label: 'Mute' },
                { id: 'cover', icon: 'image', label: 'Cover' },
                { id: 'speed', icon: 'gauge', label: 'Speed' },
                { id: 'text', icon: 'type', label: 'Text' },
            ],
            audio: [
                { id: 'waveform', icon: 'sound-wave', label: 'Waveform' },
                { id: 'trim', icon: 'scissors', label: 'Trim' },
                { id: 'rename', icon: 'type', label: 'Rename' },
            ],
            document: [
                { id: 'preview', icon: 'eye', label: 'Preview' },
                { id: 'rename', icon: 'type', label: 'Rename' },
            ]
        };
        
        this.initialized = false;
    }
    
    /**
     * Initialize tool rail
     */
    init() {
        this.container = document.getElementById('mediaComposerTools');
        this.initialized = true;
        console.log('[TOOL_RAIL] Tool rail initialized');
    }
    
    /**
     * Update tools based on media type
     * @param {Object} mediaItem - Current media item
     */
    updateTools(mediaItem) {
        if (!this.container) return;
        
        this.currentMediaType = mediaItem.type;
        const tools = this.TOOLSETS[mediaItem.type] || [];
        
        this.container.innerHTML = '';
        
        tools.forEach(tool => {
            const toolBtn = this._createToolButton(tool);
            this.container.appendChild(toolBtn);
        });
    }
    
    /**
     * Create tool button
     * @param {Object} tool - Tool configuration
     * @returns {HTMLElement} Tool button element
     */
    _createToolButton(tool) {
        const button = document.createElement('button');
        button.className = 'tool-button';
        button.dataset.tool = tool.id;
        button.title = tool.label;
        
        button.innerHTML = `
            <div class="tool-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${this._getIconPath(tool.icon)}
                </svg>
            </div>
            <div class="tool-label">${tool.label}</div>
        `;
        
        button.onclick = () => this._handleToolClick(tool.id);
        
        return button;
    }
    
    /**
     * Get icon path for Bootstrap icon
     * @param {string} iconName - Bootstrap icon name
     * @returns {string} SVG path
     */
    _getIconPath(iconName) {
        const icons = {
            'crop': '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="9" y1="3" x2="9" y2="21"></line><line x1="15" y1="3" x2="15" y2="21"></line>',
            'pencil': '<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"></path>',
            'type': '<polyline points="4 7 4 4 20 4 20 7"></polyline><line x1="9" y1="20" x2="15" y2="20"></line><line x1="12" y1="4" x2="12" y2="20"></line>',
            'smile': '<circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line>',
            'emoji-smile': '<circle cx="12" cy="12" r="10"></circle><path d="M8 14s1.5 2 4 2 4-2 4-2"></path><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="15" y1="9" x2="15.01" y2="9"></line>',
            'arrow-clockwise': '<polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>',
            'sliders': '<line x1="4" y1="21" x2="4" y2="14"></line><line x1="4" y1="10" x2="4" y2="3"></line><line x1="12" y1="21" x2="12" y2="12"></line><line x1="12" y1="8" x2="12" y2="3"></line><line x1="20" y1="21" x2="20" y2="16"></line><line x1="20" y1="12" x2="20" y2="3"></line><line x1="1" y1="14" x2="7" y2="14"></line><line x1="9" y1="8" x2="15" y2="8"></line><line x1="17" y1="16" x2="23" y2="16"></line>',
            'scissors': '<circle cx="6" cy="6" r="3"></circle><circle cx="6" cy="18" r="3"></circle><line x1="20" y1="4" x2="8.12" y2="15.88"></line><line x1="14.47" y1="14.48" x2="20" y2="20"></line><line x1="8.12" y1="8.12" x2="12" y2="12"></line>',
            'volume-x': '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line>',
            'image': '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline>',
            'gauge': '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"></path><circle cx="12" cy="12" r="3"></circle>',
            'sound-wave': '<path d="M2 12h3l2-9 4 18 4-18 2 9h3"></path>',
            'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle>'
        };
        
        return icons[iconName] || icons['type'];
    }
    
    /**
     * Handle tool button click
     * @param {string} toolId - Tool identifier
     */
    _handleToolClick(toolId) {
        console.log('[TOOL_RAIL] Tool clicked:', toolId);
        
        // Emit event for tool activation
        // This would be handled by specific tool modules in a full implementation
        // For now, we'll just log it
        
        // Example: eventBus.emit(EVENTS.MEDIA_TOOL_ACTIVATE, { toolId, mediaItem: this.composer.mediaItems[this.composer.activeMediaIndex] });
    }
    
    /**
     * Destroy tool rail
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.initialized = false;
        console.log('[TOOL_RAIL] Tool rail destroyed');
    }
}
