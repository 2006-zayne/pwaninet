/**
 * PreviewCanvas - Displays active media item in the composer
 * Handles image display, video playback, and zoom functionality
 */

export class PreviewCanvas {
    constructor(composer) {
        this.composer = composer;
        this.container = null;
        this.currentMedia = null;
        this.zoomLevel = 1;
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        this.position = { x: 0, y: 0 };
        
        this.initialized = false;
    }
    
    /**
     * Initialize preview canvas
     */
    init() {
        this.container = document.getElementById('mediaComposerPreview');
        this._setupEventListeners();
        this.initialized = true;
        console.log('[PREVIEW_CANVAS] Preview canvas initialized');
    }
    
    /**
     * Setup event listeners
     */
    _setupEventListeners() {
        if (!this.container) return;
        
        // Zoom with wheel
        this.container.addEventListener('wheel', (e) => this._handleWheel(e), { passive: false });
        
        // Drag to pan
        this.container.addEventListener('mousedown', (e) => this._handleMouseDown(e));
        this.container.addEventListener('mousemove', (e) => this._handleMouseMove(e));
        this.container.addEventListener('mouseup', () => this._handleMouseUp());
        this.container.addEventListener('mouseleave', () => this._handleMouseUp());
        
        // Touch events for mobile
        this.container.addEventListener('touchstart', (e) => this._handleTouchStart(e), { passive: false });
        this.container.addEventListener('touchmove', (e) => this._handleTouchMove(e), { passive: false });
        this.container.addEventListener('touchend', () => this._handleTouchEnd());
    }
    
    /**
     * Render media item
     * @param {Object} mediaItem - Media item to render
     */
    render(mediaItem) {
        if (!this.container) return;
        
        this.currentMedia = mediaItem;
        this._resetTransform();
        
        this.container.innerHTML = '';
        
        switch (mediaItem.type) {
            case 'image':
                this._renderImage(mediaItem);
                break;
            case 'video':
                this._renderVideo(mediaItem);
                break;
            case 'audio':
                this._renderAudio(mediaItem);
                break;
            case 'document':
                this._renderDocument(mediaItem);
                break;
        }
    }
    
    /**
     * Render image
     * @param {Object} mediaItem - Image media item
     */
    _renderImage(mediaItem) {
        const img = document.createElement('img');
        img.src = mediaItem.previewUrl;
        img.alt = mediaItem.file.name;
        img.className = 'media-preview-image';
        img.style.transform = `scale(${this.zoomLevel}) translate(${this.position.x}px, ${this.position.y}px)`;
        
        img.onload = () => {
            mediaItem.width = img.naturalWidth;
            mediaItem.height = img.naturalHeight;
        };
        
        this.container.appendChild(img);
    }
    
    /**
     * Render video
     * @param {Object} mediaItem - Video media item
     */
    _renderVideo(mediaItem) {
        const video = document.createElement('video');
        video.src = mediaItem.previewUrl;
        video.controls = true;
        video.className = 'media-preview-video';
        video.style.transform = `scale(${this.zoomLevel}) translate(${this.position.x}px, ${this.position.y}px)`;
        
        video.onloadedmetadata = () => {
            mediaItem.width = video.videoWidth;
            mediaItem.height = video.videoHeight;
            mediaItem.duration = video.duration;
        };
        
        this.container.appendChild(video);
    }
    
    /**
     * Render audio
     * @param {Object} mediaItem - Audio media item
     */
    _renderAudio(mediaItem) {
        const wrapper = document.createElement('div');
        wrapper.className = 'media-preview-audio';
        
        const icon = document.createElement('div');
        icon.className = 'audio-icon';
        icon.innerHTML = `
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 18V5l12-2v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
            </svg>
        `;
        
        const audio = document.createElement('audio');
        audio.src = mediaItem.previewUrl;
        audio.controls = true;
        audio.className = 'audio-player';
        
        const info = document.createElement('div');
        info.className = 'audio-info';
        info.textContent = mediaItem.file.name;
        
        wrapper.appendChild(icon);
        wrapper.appendChild(audio);
        wrapper.appendChild(info);
        this.container.appendChild(wrapper);
    }
    
    /**
     * Render document
     * @param {Object} mediaItem - Document media item
     */
    _renderDocument(mediaItem) {
        const wrapper = document.createElement('div');
        wrapper.className = 'media-preview-document';
        
        const icon = document.createElement('div');
        icon.className = 'document-icon';
        
        const extension = mediaItem.file.name.split('.').pop().toUpperCase();
        icon.textContent = extension;
        
        const info = document.createElement('div');
        info.className = 'document-info';
        info.innerHTML = `
            <div class="document-name">${mediaItem.file.name}</div>
            <div class="document-size">${this._formatFileSize(mediaItem.size)}</div>
        `;
        
        wrapper.appendChild(icon);
        wrapper.appendChild(info);
        this.container.appendChild(wrapper);
    }
    
    /**
     * Handle wheel zoom
     * @param {WheelEvent} e - Wheel event
     */
    _handleWheel(e) {
        if (!this.currentMedia || this.currentMedia.type !== 'image') return;
        
        e.preventDefault();
        
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        this.zoomLevel = Math.max(0.5, Math.min(5, this.zoomLevel + delta));
        
        this._applyTransform();
    }
    
    /**
     * Handle mouse down for drag
     * @param {MouseEvent} e - Mouse event
     */
    _handleMouseDown(e) {
        if (!this.currentMedia || this.currentMedia.type !== 'image') return;
        if (this.zoomLevel <= 1) return;
        
        this.isDragging = true;
        this.dragStart = { x: e.clientX - this.position.x, y: e.clientY - this.position.y };
        this.container.style.cursor = 'grabbing';
    }
    
    /**
     * Handle mouse move for drag
     * @param {MouseEvent} e - Mouse event
     */
    _handleMouseMove(e) {
        if (!this.isDragging) return;
        
        this.position.x = e.clientX - this.dragStart.x;
        this.position.y = e.clientY - this.dragStart.y;
        
        this._applyTransform();
    }
    
    /**
     * Handle mouse up
     */
    _handleMouseUp() {
        this.isDragging = false;
        this.container.style.cursor = 'default';
    }
    
    /**
     * Handle touch start for pinch zoom
     * @param {TouchEvent} e - Touch event
     */
    _handleTouchStart(e) {
        if (!this.currentMedia || this.currentMedia.type !== 'image') return;
        if (e.touches.length === 2) {
            e.preventDefault();
            this._handlePinchZoom(e);
        }
    }
    
    /**
     * Handle touch move
     * @param {TouchEvent} e - Touch event
     */
    _handleTouchMove(e) {
        if (!this.currentMedia || this.currentMedia.type !== 'image') return;
        if (e.touches.length === 2) {
            e.preventDefault();
            this._handlePinchZoom(e);
        }
    }
    
    /**
     * Handle touch end
     */
    _handleTouchEnd() {
        // Reset pinch zoom state
    }
    
    /**
     * Handle pinch zoom
     * @param {TouchEvent} e - Touch event
     */
    _handlePinchZoom(e) {
        const touch1 = e.touches[0];
        const touch2 = e.touches[1];
        const distance = Math.hypot(touch2.clientX - touch1.clientX, touch2.clientY - touch1.clientY);
        
        // Calculate zoom based on distance change
        // This is a simplified implementation
        if (this.lastPinchDistance) {
            const delta = (distance - this.lastPinchDistance) * 0.01;
            this.zoomLevel = Math.max(0.5, Math.min(5, this.zoomLevel + delta));
            this._applyTransform();
        }
        
        this.lastPinchDistance = distance;
    }
    
    /**
     * Apply transform to media element
     */
    _applyTransform() {
        const media = this.container.querySelector('img, video');
        if (media) {
            media.style.transform = `scale(${this.zoomLevel}) translate(${this.position.x}px, ${this.position.y}px)`;
        }
    }
    
    /**
     * Reset transform
     */
    _resetTransform() {
        this.zoomLevel = 1;
        this.position = { x: 0, y: 0 };
        this.lastPinchDistance = null;
    }
    
    /**
     * Format file size
     * @param {number} bytes - File size in bytes
     * @returns {string} Formatted file size
     */
    _formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    /**
     * Destroy preview canvas
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.initialized = false;
        console.log('[PREVIEW_CANVAS] Preview canvas destroyed');
    }
}
