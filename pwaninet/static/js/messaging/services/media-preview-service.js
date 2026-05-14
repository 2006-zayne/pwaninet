/**
 * Media Preview Service
 * 
 * Handles media preview before sending:
 * - Images: crop, rotate, annotate, caption
 * - Videos: preview, trim, caption, thumbnail generation
 * - Audio: playback preview, discard/re-record, waveform
 * 
 * Media does NOT upload immediately after selection.
 */

class MediaPreviewService {
    constructor(messageQueueService) {
        this.messageQueueService = messageQueueService;
        
        // Preview state
        this.currentMedia = null;
        this.mediaType = null;
        this.previewUrl = null;
        this.editedMedia = null;
        
        // Image editing state
        this.imageEditor = {
            crop: null,
            rotation: 0,
            annotations: [],
            caption: ''
        };
        
        // Video editing state
        this.videoEditor = {
            trimStart: 0,
            trimEnd: 0,
            thumbnail: null,
            caption: ''
        };
        
        // Audio editing state
        this.audioEditor = {
            waveform: null,
            caption: ''
        };
    }
    
    /**
     * Load media for preview
     */
    async loadMedia(file) {
        const fileType = file.type;
        
        if (fileType.startsWith('image/')) {
            return await this.loadImage(file);
        } else if (fileType.startsWith('video/')) {
            return await this.loadVideo(file);
        } else if (fileType.startsWith('audio/')) {
            return await this.loadAudio(file);
        } else {
            throw new Error('Unsupported media type');
        }
    }
    
    /**
     * Load image for preview
     */
    async loadImage(file) {
        this.mediaType = 'image';
        this.currentMedia = file;
        
        // Create preview URL
        this.previewUrl = URL.createObjectURL(file);
        
        // Reset editor state
        this.imageEditor = {
            crop: null,
            rotation: 0,
            annotations: [],
            caption: ''
        };
        
        console.log('[MEDIA_PREVIEW] Image loaded for preview');
        this.emitMediaLoaded('image', { url: this.previewUrl });
        
        return { type: 'image', url: this.previewUrl, file };
    }
    
    /**
     * Load video for preview
     */
    async loadVideo(file) {
        this.mediaType = 'video';
        this.currentMedia = file;
        
        // Create preview URL
        this.previewUrl = URL.createObjectURL(file);
        
        // Get video duration
        const duration = await this.getVideoDuration(this.previewUrl);
        
        // Reset editor state
        this.videoEditor = {
            trimStart: 0,
            trimEnd: duration,
            thumbnail: null,
            caption: ''
        };
        
        // Generate thumbnail
        this.videoEditor.thumbnail = await this.generateVideoThumbnail(this.previewUrl);
        
        console.log('[MEDIA_PREVIEW] Video loaded for preview');
        this.emitMediaLoaded('video', { url: this.previewUrl, duration, thumbnail: this.videoEditor.thumbnail });
        
        return { type: 'video', url: this.previewUrl, file, duration };
    }
    
    /**
     * Load audio for preview
     */
    async loadAudio(file) {
        this.mediaType = 'audio';
        this.currentMedia = file;
        
        // Create preview URL
        this.previewUrl = URL.createObjectURL(file);
        
        // Get audio duration
        const duration = await this.getAudioDuration(this.previewUrl);
        
        // Reset editor state
        this.audioEditor = {
            waveform: null,
            caption: ''
        };
        
        // Generate waveform
        this.audioEditor.waveform = await this.generateWaveform(this.previewUrl);
        
        console.log('[MEDIA_PREVIEW] Audio loaded for preview');
        this.emitMediaLoaded('audio', { url: this.previewUrl, duration, waveform: this.audioEditor.waveform });
        
        return { type: 'audio', url: this.previewUrl, file, duration };
    }
    
    /**
     * Get video duration
     */
    getVideoDuration(url) {
        return new Promise((resolve) => {
            const video = document.createElement('video');
            video.onloadedmetadata = () => resolve(video.duration);
            video.onerror = () => resolve(0);
            video.src = url;
        });
    }
    
    /**
     * Get audio duration
     */
    getAudioDuration(url) {
        return new Promise((resolve) => {
            const audio = new Audio(url);
            audio.onloadedmetadata = () => resolve(audio.duration);
            audio.onerror = () => resolve(0);
            audio.src = url;
        });
    }
    
    /**
     * Generate video thumbnail
     */
    async generateVideoThumbnail(url, time = 1) {
        return new Promise((resolve) => {
            const video = document.createElement('video');
            video.src = url;
            video.currentTime = time;
            video.muted = true;
            
            video.onloadeddata = () => {
                const canvas = document.createElement('canvas');
                canvas.width = 320;
                canvas.height = 180;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const thumbnail = canvas.toDataURL('image/jpeg', 0.8);
                resolve(thumbnail);
            };
            
            video.onerror = () => resolve(null);
        });
    }
    
    /**
     * Generate audio waveform
     */
    async generateWaveform(url) {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const response = await fetch(url);
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
            
            const channelData = audioBuffer.getChannelData(0);
            const samples = 100;
            const blockSize = Math.floor(channelData.length / samples);
            const waveform = [];
            
            for (let i = 0; i < samples; i++) {
                const start = i * blockSize;
                const end = start + blockSize;
                let sum = 0;
                
                for (let j = start; j < end; j++) {
                    sum += Math.abs(channelData[j]);
                }
                
                waveform.push(sum / blockSize);
            }
            
            return waveform;
        } catch (error) {
            console.error('[MEDIA_PREVIEW] Failed to generate waveform:', error);
            return null;
        }
    }
    
    /**
     * Image editing methods
     */
    async cropImage(cropRect) {
        if (this.mediaType !== 'image') return;
        
        const image = await this.loadImageElement(this.previewUrl);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = cropRect.width;
        canvas.height = cropRect.height;
        
        ctx.drawImage(
            image,
            cropRect.x, cropRect.y, cropRect.width, cropRect.height,
            0, 0, cropRect.width, cropRect.height
        );
        
        canvas.toBlob((blob) => {
            this.editedMedia = blob;
            this.imageEditor.crop = cropRect;
            this.emitImageEdited('crop', { cropRect });
        }, 'image/jpeg', 0.9);
    }
    
    async rotateImage(degrees) {
        if (this.mediaType !== 'image') return;
        
        const image = await this.loadImageElement(this.previewUrl);
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        
        const radians = degrees * Math.PI / 180;
        
        if (degrees === 90 || degrees === 270) {
            canvas.width = image.height;
            canvas.height = image.width;
        } else {
            canvas.width = image.width;
            canvas.height = image.height;
        }
        
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(radians);
        ctx.drawImage(image, -image.width / 2, -image.height / 2);
        
        canvas.toBlob((blob) => {
            this.editedMedia = blob;
            this.imageEditor.rotation = degrees;
            this.emitImageEdited('rotate', { degrees });
        }, 'image/jpeg', 0.9);
    }
    
    addAnnotation(annotation) {
        if (this.mediaType !== 'image') return;
        
        this.imageEditor.annotations.push(annotation);
        this.emitImageEdited('annotation', { annotation });
    }
    
    removeAnnotation(index) {
        if (this.mediaType !== 'image') return;
        
        this.imageEditor.annotations.splice(index, 1);
        this.emitImageEdited('annotation_removed', { index });
    }
    
    setImageCaption(caption) {
        if (this.mediaType !== 'image') return;
        
        this.imageEditor.caption = caption;
        this.emitImageEdited('caption', { caption });
    }
    
    /**
     * Video editing methods
     */
    setVideoTrim(start, end) {
        if (this.mediaType !== 'video') return;
        
        this.videoEditor.trimStart = start;
        this.videoEditor.trimEnd = end;
        this.emitVideoEdited('trim', { start, end });
    }
    
    setVideoCaption(caption) {
        if (this.mediaType !== 'video') return;
        
        this.videoEditor.caption = caption;
        this.emitVideoEdited('caption', { caption });
    }
    
    /**
     * Audio editing methods
     */
    setAudioCaption(caption) {
        if (this.mediaType !== 'audio') return;
        
        this.audioEditor.caption = caption;
        this.emitAudioEdited('caption', { caption });
    }
    
    /**
     * Discard current media
     */
    discardMedia() {
        if (this.previewUrl) {
            URL.revokeObjectURL(this.previewUrl);
        }
        
        this.currentMedia = null;
        this.mediaType = null;
        this.previewUrl = null;
        this.editedMedia = null;
        
        this.imageEditor = {
            crop: null,
            rotation: 0,
            annotations: [],
            caption: ''
        };
        
        this.videoEditor = {
            trimStart: 0,
            trimEnd: 0,
            thumbnail: null,
            caption: ''
        };
        
        this.audioEditor = {
            waveform: null,
            caption: ''
        };
        
        console.log('[MEDIA_PREVIEW] Media discarded');
        this.emitMediaDiscarded();
    }
    
    /**
     * Create message from current media
     */
    async createMessage(conversationId) {
        if (!this.currentMedia) {
            throw new Error('No media loaded');
        }
        
        const media = this.editedMedia || this.currentMedia;
        
        const messageData = {
            conversationId,
            messageType: this.mediaType,
            attachment: media,
            attachmentType: this.mediaType,
            mediaMetadata: {}
        };
        
        // Add type-specific metadata
        if (this.mediaType === 'image') {
            messageData.content = this.imageEditor.caption;
            messageData.mediaMetadata = {
                crop: this.imageEditor.crop,
                rotation: this.imageEditor.rotation,
                annotations: this.imageEditor.annotations
            };
        } else if (this.mediaType === 'video') {
            messageData.content = this.videoEditor.caption;
            messageData.mediaMetadata = {
                trimStart: this.videoEditor.trimStart,
                trimEnd: this.videoEditor.trimEnd,
                thumbnail: this.videoEditor.thumbnail
            };
        } else if (this.mediaType === 'audio') {
            messageData.content = this.audioEditor.caption;
            messageData.mediaMetadata = {
                waveform: this.audioEditor.waveform
            };
        }
        
        const message = await this.messageQueueService.createMessage(messageData);
        
        console.log(`[MEDIA_PREVIEW] Created message ${message.tempId} from media`);
        
        return message;
    }
    
    /**
     * Send media message
     */
    async sendMediaMessage(conversationId) {
        const message = await this.createMessage(conversationId);
        await this.messageQueueService.queueForUpload(message.tempId);
        
        // Cleanup after queuing
        this.discardMedia();
        
        return message;
    }
    
    /**
     * Helper: Load image element
     */
    loadImageElement(url) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = reject;
            image.src = url;
        });
    }
    
    /**
     * Get current preview state
     */
    getPreviewState() {
        return {
            mediaType: this.mediaType,
            hasMedia: !!this.currentMedia,
            previewUrl: this.previewUrl,
            hasEdits: !!this.editedMedia,
            imageEditor: this.imageEditor,
            videoEditor: this.videoEditor,
            audioEditor: this.audioEditor
        };
    }
    
    /**
     * Emit events
     */
    emitMediaLoaded(type, data) {
        const event = new CustomEvent('mediaLoaded', {
            detail: { type, data, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    emitImageEdited(action, data) {
        const event = new CustomEvent('imageEdited', {
            detail: { action, data, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    emitVideoEdited(action, data) {
        const event = new CustomEvent('videoEdited', {
            detail: { action, data, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    emitAudioEdited(action, data) {
        const event = new CustomEvent('audioEdited', {
            detail: { action, data, timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    emitMediaDiscarded() {
        const event = new CustomEvent('mediaDiscarded', {
            detail: { timestamp: Date.now() }
        });
        window.dispatchEvent(event);
    }
    
    /**
     * Event listeners
     */
    onMediaLoaded(callback) {
        window.addEventListener('mediaLoaded', (event) => {
            callback(event.detail);
        });
    }
    
    onImageEdited(callback) {
        window.addEventListener('imageEdited', (event) => {
            callback(event.detail);
        });
    }
    
    onVideoEdited(callback) {
        window.addEventListener('videoEdited', (event) => {
            callback(event.detail);
        });
    }
    
    onAudioEdited(callback) {
        window.addEventListener('audioEdited', (event) => {
            callback(event.detail);
        });
    }
    
    onMediaDiscarded(callback) {
        window.addEventListener('mediaDiscarded', (event) => {
            callback(event.detail);
        });
    }
}

// Export class
export default MediaPreviewService;
