/**
 * Upload Queue
 * 
 * Manages the upload queue with sequential processing.
 * Supports queue, cancel, retry, and remove failed upload operations.
 * Current upload behavior remains sequential (no parallel uploads yet).
 */

import { uploadEvents, UploadEventNames } from './upload_events.js';
import { UploadState } from './upload_state_machine.js';

class UploadItem {
    constructor(id, data) {
        this.id = id;
        this.data = data;
        this.state = UploadState.IDLE;
        this.progress = 0;
        this.errors = [];
        this.timestamps = {
            created: Date.now(),
            started: null,
            completed: null,
            failed: null,
        };
        this.retryCount = 0;
        this.maxRetries = 3;
    }

    updateProgress(value) {
        this.progress = Math.min(100, Math.max(0, value));
    }

    addError(error) {
        this.errors.push(error);
    }

    markStarted() {
        this.timestamps.started = Date.now();
    }

    markCompleted() {
        this.timestamps.completed = Date.now();
    }

    markFailed() {
        this.timestamps.failed = Date.now();
    }

    canRetry() {
        return this.retryCount < this.maxRetries;
    }

    incrementRetry() {
        this.retryCount++;
    }

    getDuration() {
        if (this.timestamps.completed) {
            return this.timestamps.completed - this.timestamps.started;
        }
        if (this.timestamps.failed) {
            return this.timestamps.failed - this.timestamps.started;
        }
        if (this.timestamps.started) {
            return Date.now() - this.timestamps.started;
        }
        return 0;
    }
}

class UploadQueue {
    constructor() {
        this.queue = [];
        this.currentUpload = null;
        this.isProcessing = false;
        this.isPaused = false;
        this.maxConcurrent = 1; // Sequential uploads only for now
    }

    /**
     * Add an upload to the queue
     * @param {object} data - Upload data
     * @returns {string} Upload ID
     */
    add(data, id = null) {
        const uploadId = id || this.generateId();
        const item = new UploadItem(uploadId, data);
        this.queue.push(item);

        uploadEvents.emit(UploadEventNames.UPLOAD_ADDED, {
            id: uploadId,
            data,
            queuePosition: this.queue.length,
        });

        // Start processing if not already processing
        if (!this.isProcessing) {
            this.processQueue();
        }

        return uploadId;
    }

    addSession(session) {
        return this.add(session, session.id);
    }

    /**
     * Remove an upload from the queue
     * @param {string} id - Upload ID
     * @returns {boolean}
     */
    remove(id) {
        const index = this.queue.findIndex(item => item.id === id);
        
        if (index === -1) {
            return false;
        }

        // Cannot remove currently processing upload
        if (this.currentUpload && this.currentUpload.id === id) {
            return false;
        }

        this.queue.splice(index, 1);
        
        uploadEvents.emit(UploadEventNames.UPLOAD_REMOVED, {
            id,
            queuePosition: index,
        });

        return true;
    }

    /**
     * Cancel an upload
     * @param {string} id - Upload ID
     * @returns {boolean}
     */
    cancel(id) {
        const item = this.queue.find(item => item.id === id);
        
        if (!item) {
            return false;
        }

        // If currently processing, mark as cancelled
        if (this.currentUpload && this.currentUpload.id === id) {
            item.state = UploadState.CANCELLED;
            item.markFailed();
            
            // Move to next upload
            this.currentUpload = null;
            this.processQueue();
            
            return true;
        }

        // Remove from queue if not processing
        return this.remove(id);
    }

    /**
     * Retry a failed upload
     * @param {string} id - Upload ID
     * @returns {boolean}
     */
    retry(id) {
        const item = this.queue.find(item => item.id === id);
        
        if (!item || !item.canRetry()) {
            return false;
        }

        item.incrementRetry();
        item.state = UploadState.QUEUED;
        item.progress = 0;
        item.errors = [];
        item.timestamps.started = null;
        item.timestamps.failed = null;

        // Move to end of queue
        this.queue = this.queue.filter(i => i.id !== id);
        this.queue.push(item);

        // Start processing if not already processing
        if (!this.isProcessing) {
            this.processQueue();
        }

        return true;
    }

    /**
     * Clear all uploads from queue
     */
    clear() {
        // Cannot clear if currently processing
        if (this.currentUpload) {
            return false;
        }

        this.queue = [];
        
        uploadEvents.emit(UploadEventNames.QUEUE_CLEARED, {});
        
        return true;
    }

    /**
     * Pause queue processing
     */
    pause() {
        this.isPaused = true;
        uploadEvents.emit(UploadEventNames.QUEUE_PAUSED, {});
    }

    /**
     * Resume queue processing
     */
    resume() {
        this.isPaused = false;
        uploadEvents.emit(UploadEventNames.QUEUE_RESUMED, {});
        
        if (!this.isProcessing) {
            this.processQueue();
        }
    }

    /**
     * Process the queue
     */
    async processQueue() {
        if (this.isProcessing || this.isPaused) {
            return;
        }

        this.isProcessing = true;

        while (this.queue.length > 0 && !this.isPaused) {
            const item = this.queue[0];

            // Skip if already completed or cancelled
            if (item.state === UploadState.PUBLISHED || item.state === UploadState.CANCELLED) {
                this.queue.shift();
                continue;
            }

            // Process the upload
            this.currentUpload = item;
            item.state = UploadState.UPLOADING;
            item.markStarted();

            // The actual upload will be handled by UploadManager
            // This method just manages the queue state
            // UploadManager will call uploadCompleted or uploadFailed
            // when the upload is done
            
            // Wait for upload to complete (handled by UploadManager callbacks)
            await this.waitForUploadCompletion(item);

            this.currentUpload = null;
            this.queue.shift();
        }

        this.isProcessing = false;
    }

    /**
     * Wait for upload completion
     * @param {UploadItem} item - Upload item
     * @returns {Promise<void>}
     */
    waitForUploadCompletion(item) {
        return new Promise((resolve) => {
            const checkCompletion = () => {
                if (item.state === UploadState.PUBLISHED || 
                    item.state === UploadState.FAILED || 
                    item.state === UploadState.CANCELLED) {
                    resolve();
                } else {
                    setTimeout(checkCompletion, 100);
                }
            };
            checkCompletion();
        });
    }

    /**
     * Mark upload as completed
     * @param {string} id - Upload ID
     */
    uploadCompleted(id) {
        const item = this.queue.find(item => item.id === id);
        if (item) {
            item.state = UploadState.PUBLISHED;
            item.progress = 100;
            item.markCompleted();
        }
    }

    /**
     * Mark upload as failed
     * @param {string} id - Upload ID
     * @param {Error} error - Error that caused failure
     */
    uploadFailed(id, error) {
        const item = this.queue.find(item => item.id === id);
        if (item) {
            item.state = UploadState.FAILED;
            item.addError(error);
            item.markFailed();
        }
    }

    /**
     * Get upload by ID
     * @param {string} id - Upload ID
     * @returns {UploadItem|undefined}
     */
    getUpload(id) {
        return this.queue.find(item => item.id === id);
    }

    /**
     * Get all uploads
     * @returns {UploadItem[]}
     */
    getAllUploads() {
        return [...this.queue];
    }

    /**
     * Get pending uploads
     * @returns {UploadItem[]}
     */
    getPendingUploads() {
        return this.queue.filter(item => 
            item.state === UploadState.IDLE || 
            item.state === UploadState.QUEUED
        );
    }

    /**
     * Get failed uploads
     * @returns {UploadItem[]}
     */
    getFailedUploads() {
        return this.queue.filter(item => item.state === UploadState.FAILED);
    }

    /**
     * Get completed uploads
     * @returns {UploadItem[]}
     */
    getCompletedUploads() {
        return this.queue.filter(item => item.state === UploadState.PUBLISHED);
    }

    /**
     * Get queue statistics
     * @returns {object}
     */
    getStatistics() {
        return {
            total: this.queue.length,
            pending: this.getPendingUploads().length,
            failed: this.getFailedUploads().length,
            completed: this.getCompletedUploads().length,
            processing: this.currentUpload ? 1 : 0,
            isProcessing: this.isProcessing,
            isPaused: this.isPaused,
        };
    }

    /**
     * Generate unique upload ID
     * @returns {string}
     */
    generateId() {
        return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * Get current upload
     * @returns {UploadItem|null}
     */
    getCurrentUpload() {
        return this.currentUpload;
    }

    /**
     * Check if queue is empty
     * @returns {boolean}
     */
    isEmpty() {
        return this.queue.length === 0;
    }

    /**
     * Get estimated time remaining
     * @returns {number} Estimated milliseconds
     */
    getEstimatedTimeRemaining() {
        if (!this.currentUpload || this.queue.length === 0) {
            return 0;
        }

        // Calculate average upload time from completed uploads
        const completedUploads = this.getCompletedUploads();
        if (completedUploads.length === 0) {
            return 0;
        }

        const avgDuration = completedUploads.reduce((sum, item) => sum + item.getDuration(), 0) / completedUploads.length;
        const remainingUploads = this.getPendingUploads().length + (this.currentUpload ? 1 : 0);

        return avgDuration * remainingUploads;
    }
}

// Global upload queue instance
export const uploadQueue = new UploadQueue();

export {
    UploadQueue,
    UploadItem,
};

export default UploadQueue;
