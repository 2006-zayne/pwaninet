/**
 * PwaniNet Unified Download Queue
 * Manages FIFO download queue with concurrency limit (default: 2),
 * automated trigger of next item upon completion/failure,
 * progress tracking, cancellation, and event broadcasting.
 */

export const DownloadStatus = {
    QUEUED: 'QUEUED',
    DOWNLOADING: 'DOWNLOADING',
    COMPLETED: 'COMPLETED',
    FAILED: 'FAILED',
    CANCELLED: 'CANCELLED'
};

export class DownloadQueueItem {
    constructor(options) {
        this.id = options.id || `dl_${Date.now()}_${Math.random().toString(36).substr(2, 8)}`;
        this.url = options.url;
        this.filename = options.filename || this.extractFilename(options.url);
        this.category = options.category || this.detectCategory(this.filename, options.mimeType);
        this.mimeType = options.mimeType || '';
        this.postId = options.postId || null;
        this.mediaId = options.mediaId || null;
        this.thumbnail = options.thumbnail || null;
        
        this.status = DownloadStatus.QUEUED;
        this.progress = 0; // 0 - 100
        this.bytesDownloaded = 0;
        this.totalBytes = options.size || 0;
        this.error = null;
        this.cancelController = new AbortController();
        this.nativeTaskId = null; // For Capacitor Filesystem download task if applicable
        
        this.createdAt = Date.now();
        this.startedAt = null;
        this.completedAt = null;
    }

    extractFilename(url) {
        try {
            const cleanUrl = url.split('?')[0].split('#')[0];
            const name = cleanUrl.substring(cleanUrl.lastIndexOf('/') + 1);
            return decodeURIComponent(name) || `download_${Date.now()}`;
        } catch (e) {
            return `download_${Date.now()}`;
        }
    }

    detectCategory(filename, mimeType) {
        const ext = (filename.split('.').pop() || '').toLowerCase();
        if (['mp4', 'webm', 'mov', 'mkv', 'avi', 'm4v'].includes(ext) || (mimeType && mimeType.startsWith('video/'))) {
            return 'video';
        }
        if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'heic'].includes(ext) || (mimeType && mimeType.startsWith('image/'))) {
            return 'image';
        }
        if (['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'].includes(ext) || (mimeType && mimeType.startsWith('audio/'))) {
            return 'audio';
        }
        return 'document';
    }
}

class DownloadQueue {
    constructor(maxConcurrent = 2) {
        this.items = new Map(); // id -> DownloadQueueItem
        this.maxConcurrent = maxConcurrent;
        this.runner = null; // Execution callback function set by DownloadManager
    }

    /**
     * Register executor callback
     * @param {Function} runner async function(item)
     */
    setRunner(runner) {
        this.runner = runner;
    }

    /**
     * Add download to queue
     * @param {Object} options 
     * @returns {DownloadQueueItem}
     */
    enqueue(options) {
        // Prevent duplicate queuing of same URL if already queued or downloading
        for (const existing of this.items.values()) {
            if (existing.url === options.url && 
               (existing.status === DownloadStatus.QUEUED || existing.status === DownloadStatus.DOWNLOADING)) {
                this.emitEvent('pwaninet:download-already-active', existing);
                return existing;
            }
        }

        const item = new DownloadQueueItem(options);
        this.items.set(item.id, item);

        this.emitEvent('pwaninet:download-queued', item);
        this.processQueue();
        return item;
    }

    /**
     * Process queue up to max concurrent limit
     */
    async processQueue() {
        const activeCount = this.getActiveDownloads().length;
        const availableSlots = this.maxConcurrent - activeCount;

        if (availableSlots <= 0 || !this.runner) return;

        const queuedItems = this.getQueuedDownloads();
        const toStart = queuedItems.slice(0, availableSlots);

        for (const item of toStart) {
            item.status = DownloadStatus.DOWNLOADING;
            item.startedAt = Date.now();
            this.emitEvent('pwaninet:download-started', item);

            // Run asynchronously without awaiting to let concurrent tasks execute
            (async () => {
                try {
                    await this.runner(item);
                } catch (err) {
                    console.error('[DownloadQueue] Execution error for item:', item.id, err);
                    if (item.status !== DownloadStatus.CANCELLED) {
                        this.markFailed(item.id, err.message || 'Download failed');
                    }
                }
            })();
        }
    }

    /**
     * Update progress of an active item
     */
    updateProgress(id, { progress, bytesDownloaded, totalBytes }) {
        const item = this.items.get(id);
        if (!item || item.status !== DownloadStatus.DOWNLOADING) return;

        item.progress = Math.min(100, Math.max(0, Math.round(progress)));
        if (bytesDownloaded !== undefined) item.bytesDownloaded = bytesDownloaded;
        if (totalBytes !== undefined && totalBytes > 0) item.totalBytes = totalBytes;

        this.emitEvent('pwaninet:download-progress', item);
    }

    /**
     * Mark item as completed and trigger next in queue
     */
    markCompleted(id, resultMetadata = {}) {
        const item = this.items.get(id);
        if (!item) return;

        item.status = DownloadStatus.COMPLETED;
        item.progress = 100;
        item.completedAt = Date.now();
        Object.assign(item, resultMetadata);

        this.emitEvent('pwaninet:download-completed', item);

        // Auto-trigger next item in queue
        setTimeout(() => this.processQueue(), 50);
    }

    /**
     * Mark item as failed and trigger next in queue
     */
    markFailed(id, errorMessage) {
        const item = this.items.get(id);
        if (!item) return;

        item.status = DownloadStatus.FAILED;
        item.error = errorMessage;
        this.emitEvent('pwaninet:download-failed', item);

        // Auto-trigger next item in queue
        setTimeout(() => this.processQueue(), 50);
    }

    /**
     * Cancel an active or queued download
     */
    cancel(id) {
        const item = this.items.get(id);
        if (!item) return;

        item.status = DownloadStatus.CANCELLED;
        if (item.cancelController) {
            item.cancelController.abort();
        }

        this.emitEvent('pwaninet:download-cancelled', item);

        // Auto-trigger next item in queue
        setTimeout(() => this.processQueue(), 50);
    }

    getActiveDownloads() {
        return Array.from(this.items.values()).filter(it => it.status === DownloadStatus.DOWNLOADING);
    }

    getQueuedDownloads() {
        return Array.from(this.items.values()).filter(it => it.status === DownloadStatus.QUEUED);
    }

    getAll() {
        return Array.from(this.items.values());
    }

    getItem(id) {
        return this.items.get(id) || null;
    }

    /**
     * Broadcast DOM event on window
     */
    emitEvent(name, detail) {
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent(name, { detail }));
        }
    }
}

export const downloadQueue = new DownloadQueue(2);
