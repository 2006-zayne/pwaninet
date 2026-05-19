/**
 * ThumbnailStrip - Bottom navigation strip for media items
 * Displays thumbnails, handles selection and reordering
 */

export class ThumbnailStrip {
    constructor(composer) {
        this.composer = composer;
        this.container = null;
        this.mediaItems = [];
        this.activeIndex = 0;
        
        this.initialized = false;
    }
    
    /**
     * Initialize thumbnail strip
     */
    init() {
        this.container = document.getElementById('mediaComposerThumbnails');
        this.initialized = true;
        console.log('[THUMBNAIL_STRIP] Thumbnail strip initialized');
    }
    
    /**
     * Render thumbnails
     * @param {Array} mediaItems - Media items to render
     */
    render(mediaItems) {
        if (!this.container) return;
        
        this.mediaItems = mediaItems;
        this.container.innerHTML = '';
        
        mediaItems.forEach((item, index) => {
            const thumbnail = this._createThumbnail(item, index);
            this.container.appendChild(thumbnail);
        });
        
        // Add "add more" button
        const addBtn = this._createAddButton();
        this.container.appendChild(addBtn);
        
        this._scrollToActive();
    }
    
    /**
     * Create thumbnail element
     * @param {Object} item - Media item
     * @param {number} index - Item index
     * @returns {HTMLElement} Thumbnail element
     */
    _createThumbnail(item, index) {
        const thumbnail = document.createElement('div');
        thumbnail.className = `media-thumbnail ${index === this.activeIndex ? 'active' : ''}`;
        thumbnail.dataset.index = index;
        
        const content = this._createThumbnailContent(item);
        thumbnail.appendChild(content);
        
        // Remove button
        const removeBtn = document.createElement('button');
        removeBtn.className = 'thumbnail-remove';
        removeBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
        removeBtn.onclick = (e) => {
            e.stopPropagation();
            this.composer.removeMediaItem(index);
        };
        thumbnail.appendChild(removeBtn);
        
        // Click to activate
        thumbnail.onclick = () => {
            this.composer.setActiveMedia(index);
        };
        
        return thumbnail;
    }
    
    /**
     * Create thumbnail content based on media type
     * @param {Object} item - Media item
     * @returns {HTMLElement} Thumbnail content
     */
    _createThumbnailContent(item) {
        const content = document.createElement('div');
        content.className = 'thumbnail-content';
        
        switch (item.type) {
            case 'image':
                const img = document.createElement('img');
                img.src = item.previewUrl;
                img.alt = item.file.name;
                img.className = 'thumbnail-image';
                content.appendChild(img);
                break;
                
            case 'video':
                const videoThumb = document.createElement('div');
                videoThumb.className = 'thumbnail-video';
                
                if (item.previewUrl) {
                    const video = document.createElement('video');
                    video.src = item.previewUrl;
                    video.className = 'thumbnail-video-element';
                    video.muted = true;
                    video.onloadeddata = () => {
                        video.currentTime = 1; // Get frame at 1 second
                    };
                    videoThumb.appendChild(video);
                }
                
                const playIcon = document.createElement('div');
                playIcon.className = 'thumbnail-play-icon';
                playIcon.innerHTML = `
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <polygon points="5,3 19,12 5,21"></polygon>
                    </svg>
                `;
                videoThumb.appendChild(playIcon);
                
                content.appendChild(videoThumb);
                break;
                
            case 'audio':
                const audioThumb = document.createElement('div');
                audioThumb.className = 'thumbnail-audio';
                audioThumb.innerHTML = `
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M9 18V5l12-2v13"></path>
                        <circle cx="6" cy="18" r="3"></circle>
                        <circle cx="18" cy="16" r="3"></circle>
                    </svg>
                `;
                content.appendChild(audioThumb);
                break;
                
            case 'document':
                const docThumb = document.createElement('div');
                docThumb.className = 'thumbnail-document';
                const extension = item.file.name.split('.').pop().toUpperCase();
                docThumb.textContent = extension;
                content.appendChild(docThumb);
                break;
        }
        
        return content;
    }
    
    /**
     * Create add more button
     * @returns {HTMLElement} Add button element
     */
    _createAddButton() {
        const addBtn = document.createElement('div');
        addBtn.className = 'media-thumbnail add-more';
        addBtn.innerHTML = `
            <div class="thumbnail-content">
                <div class="thumbnail-add-icon">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                </div>
            </div>
        `;
        
        addBtn.onclick = () => {
            this.composer.triggerFileInput();
        };
        
        return addBtn;
    }
    
    /**
     * Set active thumbnail
     * @param {number} index - Active index
     */
    setActive(index) {
        this.activeIndex = index;
        
        const thumbnails = this.container.querySelectorAll('.media-thumbnail:not(.add-more)');
        thumbnails.forEach((thumb, i) => {
            if (i === index) {
                thumb.classList.add('active');
            } else {
                thumb.classList.remove('active');
            }
        });
        
        this._scrollToActive();
    }
    
    /**
     * Scroll to active thumbnail
     */
    _scrollToActive() {
        const activeThumb = this.container.querySelector('.media-thumbnail.active');
        if (activeThumb) {
            activeThumb.scrollIntoView({ behavior: 'smooth', inline: 'center' });
        }
    }
    
    /**
     * Destroy thumbnail strip
     */
    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.mediaItems = [];
        this.initialized = false;
        console.log('[THUMBNAIL_STRIP] Thumbnail strip destroyed');
    }
}
