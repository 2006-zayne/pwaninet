/**
 * Upload UI
 * 
 * Manages the global upload banner and UI components.
 * Displays current stage, overall progress, current file, files completed, 
 * and estimated remaining time. Smoothly animates between states.
 * No alert dialogs or blocking modals.
 */

import { uploadEvents, UploadEventNames } from './upload_events.js';
import { UploadState } from './upload_state_machine.js';
import { uploadManager } from './upload_manager.js';

class UploadBanner {
    constructor() {
        this.banner = null;
        this.isVisible = false;
        this.currentUploadId = null;
        this.bannerMode = 'cancel';
        this.autoHideTimer = null;
        this.currentStage = '';
        this.currentProgress = 0;
        this.currentFile = '';
        this.filesCompleted = 0;
        this.filesTotal = 0;
        this.estimatedTime = 0;
        this.isInitialized = false;
    }

    /**
     * Initialize the upload banner
     */
    initialize() {
        if (this.isInitialized) return;

        this.createBanner();
        this.setupEventListeners();
        this.isInitialized = true;
    }

    /**
     * Create the banner DOM element
     */
    createBanner() {
        // Check if banner already exists
        if (document.getElementById('upload-banner')) {
            this.banner = document.getElementById('upload-banner');
            return;
        }

        const banner = document.createElement('div');
        banner.id = 'upload-banner';
        banner.className = 'upload-banner';
        banner.innerHTML = `
            <div class="upload-banner-content">
                <div class="upload-banner-left">
                    <div class="upload-banner-icon">
                        <i class="bi bi-arrow-repeat" id="upload-banner-spinner"></i>
                    </div>
                    <div class="upload-banner-info">
                        <div class="upload-banner-stage" id="upload-banner-stage">Preparing</div>
                        <div class="upload-banner-details" id="upload-banner-details">
                            <span class="upload-banner-file" id="upload-banner-file"></span>
                            <span class="upload-banner-progress" id="upload-banner-progress">0%</span>
                        </div>
                    </div>
                </div>
                <div class="upload-banner-right">
                    <div class="upload-banner-stats">
                        <span class="upload-banner-files" id="upload-banner-files">0/0</span>
                        <span class="upload-banner-time" id="upload-banner-time"></span>
                    </div>
                    <button class="upload-banner-cancel" id="upload-banner-cancel" title="Cancel">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                <div class="upload-banner-progress-bar">
                    <div class="upload-banner-progress-fill" id="upload-banner-progress-fill"></div>
                </div>
            </div>
        `;

        document.body.appendChild(banner);
        this.banner = banner;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Cancel button
        const cancelBtn = document.getElementById('upload-banner-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => {
                if (this.bannerMode === 'retry') {
                    this.retryCurrentUpload();
                } else {
                    this.cancelCurrentUpload();
                }
            });
        }

        // Listen to upload events
        uploadEvents.on(UploadEventNames.STATE_CHANGED, (data) => {
            this.handleStateChange(data);
        });

        uploadEvents.on(UploadEventNames.PROGRESS_UPDATED, (data) => {
            this.handleProgressUpdate(data);
        });

        uploadEvents.on(UploadEventNames.COMPRESSION_PROGRESS, (data) => {
            this.handleCompressionProgress(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_PROGRESS, (data) => {
            this.handleUploadProgress(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_COMPLETED, (data) => {
            this.handleUploadCompleted(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_PUBLISHED, (data) => {
            this.handleUploadPublished(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_FAILED, (data) => {
            this.handleUploadFailed(data);
        });

        uploadEvents.on(UploadEventNames.QUEUE_CLEARED, () => {
            this.hide();
        });
    }

    /**
     * Handle state change
     * @param {object} data - State change data
     */
    handleStateChange(data) {
        const { uploadId, newState, metadata } = data;
        this.currentUploadId = uploadId;
        this.clearAutoHideTimer();
        
        this.updateStage(newState);
        
        if (newState === UploadState.PUBLISHED) {
            this.showCompletion();
        } else if (newState === UploadState.FAILED) {
            this.showError(metadata?.error || 'Upload failed', true);
        } else if (newState === UploadState.CANCELLED) {
            this.hide();
        }
    }

    /**
     * Handle progress update
     * @param {object} data - Progress data
     */
    handleProgressUpdate(data) {
        const { uploadId, stage, percent, status } = data;
        this.currentUploadId = uploadId || this.currentUploadId;
        
        this.updateProgress(percent);

        if (this.currentUploadId) {
            const progress = uploadManager.getUploadProgress(this.currentUploadId);
            const etaMs = progress?.estimatedTimeRemaining || 0;
            this.updateEstimatedTime(Math.round(etaMs / 1000));
        }
        
        if (status) {
            this.updateDetails(status);
        }
    }

    /**
     * Handle compression progress
     * @param {object} data - Compression progress data
     */
    handleCompressionProgress(data) {
        const { current, total, fileName, percent } = data;
        
        this.updateStage('Compressing Images');
        this.updateProgress(percent);
        this.updateFile(fileName);
        this.updateFiles(current, total);
    }

    /**
     * Handle upload progress
     * @param {object} data - Upload progress data
     */
    handleUploadProgress(data) {
        const { percent } = data;
        
        this.updateStage('Uploading');
        this.updateProgress(percent);
    }

    /**
     * Handle upload completed
     * @param {object} data - Upload completed data
     */
    handleUploadCompleted(data) {
        this.filesCompleted++;
        this.updateFiles(this.filesCompleted, this.filesTotal);
    }

    handleUploadPublished(data) {
        this.showCompletion();

        const feedRefreshTarget = document.querySelector('[data-upload-feed-refresh]');
        if (feedRefreshTarget && window.htmx) {
            const refreshUrl = feedRefreshTarget.getAttribute('data-upload-feed-refresh-url') || window.location.pathname;
            window.htmx.ajax('GET', refreshUrl, {
                target: '#main-content-area',
                swap: 'innerHTML',
            });
        }
    }

    /**
     * Handle upload failed
     * @param {object} data - Upload failed data
     */
    handleUploadFailed(data) {
        this.currentUploadId = data.uploadId || this.currentUploadId;
        this.clearAutoHideTimer();
        this.showError(data.error || 'Upload failed', data.canRetry === true);
    }

    /**
     * Show the banner
     */
    show() {
        if (!this.banner) return;
        this.setCancelMode();
        
        this.banner.classList.add('visible');
        this.isVisible = true;
    }

    /**
     * Hide the banner
     */
    hide() {
        if (!this.banner) return;
        this.clearAutoHideTimer();
        
        this.banner.classList.remove('visible');
        this.isVisible = false;
        
        // Reset after animation
        setTimeout(() => {
            this.reset();
        }, 300);
    }

    /**
     * Update stage display
     * @param {string} stage - Stage name
     */
    updateStage(stage) {
        const stageElement = document.getElementById('upload-banner-stage');
        if (stageElement) {
            const stageText = this.formatStage(stage);
            stageElement.textContent = stageText;
            this.currentStage = stageText;
        }
    }

    /**
     * Update progress display
     * @param {number} percent - Progress percentage
     */
    updateProgress(percent) {
        const progressElement = document.getElementById('upload-banner-progress');
        const progressFill = document.getElementById('upload-banner-progress-fill');
        
        if (progressElement) {
            progressElement.textContent = `${Math.round(percent)}%`;
        }
        
        if (progressFill) {
            progressFill.style.width = `${percent}%`;
        }
        
        this.currentProgress = percent;
    }

    /**
     * Update file display
     * @param {string} fileName - File name
     */
    updateFile(fileName) {
        const fileElement = document.getElementById('upload-banner-file');
        if (fileElement) {
            fileElement.textContent = fileName ? `• ${fileName}` : '';
            this.currentFile = fileName;
        }
    }

    /**
     * Update files count display
     * @param {number} completed - Completed count
     * @param {number} total - Total count
     */
    updateFiles(completed, total) {
        const filesElement = document.getElementById('upload-banner-files');
        if (filesElement) {
            filesElement.textContent = `${completed}/${total}`;
            this.filesCompleted = completed;
            this.filesTotal = total;
        }
    }

    /**
     * Update details display
     * @param {string} details - Details text
     */
    updateDetails(details) {
        const detailsElement = document.getElementById('upload-banner-details');
        if (detailsElement) {
            detailsElement.textContent = details;
        }
    }

    /**
     * Update estimated time display
     * @param {number} seconds - Estimated seconds
     */
    updateEstimatedTime(seconds) {
        const timeElement = document.getElementById('upload-banner-time');
        if (timeElement) {
            if (seconds > 0) {
                timeElement.textContent = this.formatTime(seconds);
            } else {
                timeElement.textContent = '';
            }
            this.estimatedTime = seconds;
        }
    }

    /**
     * Show completion state
     */
    showCompletion() {
        const spinner = document.getElementById('upload-banner-spinner');
        const stageElement = document.getElementById('upload-banner-stage');
        
        if (spinner) {
            spinner.innerHTML = '<i class="bi bi-check-lg"></i>';
            spinner.classList.add('success');
        }
        
        if (stageElement) {
            stageElement.textContent = 'Completed';
        }
        
        this.clearAutoHideTimer();
        this.autoHideTimer = setTimeout(() => {
            this.hide();
        }, 2000);
    }

    /**
     * Show error state
     * @param {string} message - Error message
     */
    showError(message, canRetry = false) {
        const spinner = document.getElementById('upload-banner-spinner');
        const stageElement = document.getElementById('upload-banner-stage');
        
        if (spinner) {
            spinner.innerHTML = '<i class="bi bi-exclamation-triangle"></i>';
            spinner.classList.add('error');
        }
        
        if (stageElement) {
            stageElement.textContent = message || 'Failed';
        }
        
        if (canRetry) {
            this.setRetryMode();
        } else {
            this.setCancelMode();
            this.clearAutoHideTimer();
            this.autoHideTimer = setTimeout(() => {
                this.hide();
            }, 3000);
        }
    }

    clearAutoHideTimer() {
        if (this.autoHideTimer) {
            clearTimeout(this.autoHideTimer);
            this.autoHideTimer = null;
        }
    }

    setCancelMode() {
        this.bannerMode = 'cancel';
        const cancelBtn = document.getElementById('upload-banner-cancel');
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
            cancelBtn.title = 'Cancel';
        }
    }

    setRetryMode() {
        this.bannerMode = 'retry';
        const cancelBtn = document.getElementById('upload-banner-cancel');
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="bi bi-arrow-clockwise"></i>';
            cancelBtn.title = 'Retry';
        }
    }

    retryCurrentUpload() {
        if (this.currentUploadId) {
            uploadManager.retryUpload(this.currentUploadId);
            this.setCancelMode();
            this.updateStage('QUEUED');
            this.updateProgress(0);
        }
    }

    /**
     * Cancel current upload
     */
    cancelCurrentUpload() {
        const currentUpload = uploadManager.getActiveUpload();
        
        if (currentUpload) {
            uploadManager.cancelUpload(currentUpload.id);
        }
    }

    /**
     * Reset banner state
     */
    reset() {
        const spinner = document.getElementById('upload-banner-spinner');
        const stageElement = document.getElementById('upload-banner-stage');
        const progressFill = document.getElementById('upload-banner-progress-fill');
        const progressElement = document.getElementById('upload-banner-progress');
        const fileElement = document.getElementById('upload-banner-file');
        const filesElement = document.getElementById('upload-banner-files');
        const timeElement = document.getElementById('upload-banner-time');
        
        if (spinner) {
            spinner.innerHTML = '<i class="bi bi-arrow-repeat"></i>';
            spinner.classList.remove('success', 'error');
        }

        this.setCancelMode();
        
        if (stageElement) {
            stageElement.textContent = 'Preparing';
        }
        
        if (progressFill) {
            progressFill.style.width = '0%';
        }
        
        if (progressElement) {
            progressElement.textContent = '0%';
        }
        
        if (fileElement) {
            fileElement.textContent = '';
        }
        
        if (filesElement) {
            filesElement.textContent = '0/0';
        }
        
        if (timeElement) {
            timeElement.textContent = '';
        }
        
        this.currentStage = '';
        this.currentProgress = 0;
        this.currentFile = '';
        this.filesCompleted = 0;
        this.filesTotal = 0;
        this.estimatedTime = 0;
    }

    /**
     * Format stage name for display
     * @param {string} stage - Stage name
     * @returns {string} Formatted stage name
     */
    formatStage(stage) {
        const stageMap = {
            [UploadState.IDLE]: 'Preparing',
            [UploadState.PREPARING]: 'Preparing',
            [UploadState.VALIDATING]: 'Validating',
            [UploadState.READING_MEDIA]: 'Reading Media',
            [UploadState.GENERATING_PREVIEW]: 'Generating Preview',
            [UploadState.COMPRESSING_IMAGES]: 'Compressing Images',
            [UploadState.READY]: 'Ready',
            [UploadState.QUEUED]: 'Queued',
            [UploadState.UPLOADING]: 'Uploading',
            [UploadState.SERVER_PROCESSING]: 'Server Processing',
            [UploadState.PUBLISHED]: 'Completed',
            [UploadState.FAILED]: 'Failed',
            [UploadState.CANCELLED]: 'Cancelled',
        };
        
        return stageMap[stage] || stage;
    }

    /**
     * Format time for display
     * @param {number} seconds - Seconds
     * @returns {string} Formatted time
     */
    formatTime(seconds) {
        if (seconds < 60) {
            return `${Math.round(seconds)}s`;
        }
        
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        
        if (minutes < 60) {
            return `${minutes}m ${remainingSeconds}s`;
        }
        
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        
        return `${hours}h ${remainingMinutes}m`;
    }

    /**
     * Check if banner is visible
     * @returns {boolean}
     */
    isBannerVisible() {
        return this.isVisible;
    }
}

class UploadUI {
    constructor() {
        this.banner = new UploadBanner();
        this.isInitialized = false;
    }

    /**
     * Initialize the upload UI
     */
    initialize() {
        if (this.isInitialized) return;

        this.banner.initialize();
        this.injectStyles();
        this.setupGlobalListeners();
        this.isInitialized = true;
    }

    /**
     * Inject CSS styles for the upload banner
     */
    injectStyles() {
        // Check if styles already exist
        if (document.getElementById('upload-banner-styles')) {
            return;
        }

        const style = document.createElement('style');
        style.id = 'upload-banner-styles';
        style.textContent = `
            .upload-banner {
                position: fixed;
                top: -100px;
                left: 0;
                right: 0;
                z-index: 9999;
                background: rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(8px);
                -webkit-backdrop-filter: blur(8px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                transition: top 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                pointer-events: none;
            }

            .upload-banner.visible {
                top: 65px;
                pointer-events: auto;
            }

            [data-theme="dark"] .upload-banner {
                background: rgba(0, 0, 0, 0.7);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }

            .upload-banner-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 12px 16px;
                max-width: 1200px;
                margin: 0 auto;
            }

            .upload-banner-left {
                display: flex;
                align-items: center;
                gap: 12px;
                flex: 1;
                min-width: 0;
            }

            .upload-banner-icon {
                width: 32px;
                height: 32px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 14px;
                flex-shrink: 0;
            }

            .upload-banner-icon i {
                animation: spin 1s linear infinite;
            }

            .upload-banner-icon.success i {
                animation: none;
            }

            .upload-banner-icon.error i {
                animation: none;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            .upload-banner-info {
                flex: 1;
                min-width: 0;
            }

            .upload-banner-stage {
                color: white;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 2px;
            }

            .upload-banner-details {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .upload-banner-file {
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .upload-banner-progress {
                font-weight: 600;
            }

            .upload-banner-right {
                display: flex;
                align-items: center;
                gap: 16px;
                flex-shrink: 0;
            }

            .upload-banner-stats {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
                gap: 2px;
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
            }

            .upload-banner-cancel {
                width: 32px;
                height: 32px;
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 50%;
                color: white;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }

            .upload-banner-cancel:hover {
                background: rgba(255, 255, 255, 0.3);
            }

            .upload-banner-progress-bar {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: rgba(255, 255, 255, 0.2);
            }

            .upload-banner-progress-fill {
                height: 100%;
                background: rgba(255, 255, 255, 0.8);
                transition: width 0.3s ease;
            }

            @media (max-width: 768px) {
                .upload-banner-content {
                    padding: 10px 12px;
                }

                .upload-banner-file {
                    max-width: 120px;
                }

                .upload-banner-stats {
                    display: none;
                }
            }
        `;

        document.head.appendChild(style);
    }

    /**
     * Setup global listeners
     */
    setupGlobalListeners() {
        // Show banner when upload is added
        uploadEvents.on(UploadEventNames.UPLOAD_ADDED, (data) => {
            this.banner.currentUploadId = data.id;
            const fileCount = Array.isArray(data.data?.files) ? data.data.files.length : 0;
            this.banner.updateFiles(0, fileCount);
            this.banner.show();
        });

        // Hide banner when queue is cleared
        uploadEvents.on(UploadEventNames.QUEUE_CLEARED, () => {
            this.banner.hide();
        });

        // Warn before leaving if an upload is in progress
        window.addEventListener('beforeunload', (e) => {
            if (window.uploadManager && window.uploadManager.getActiveUpload()) {
                e.preventDefault();
                e.returnValue = 'You have an active upload in progress. If you leave now, the upload will be cancelled.';
                return e.returnValue;
            }
        });
    }

    /**
     * Get banner instance
     * @returns {UploadBanner}
     */
    getBanner() {
        return this.banner;
    }
}

// Global upload UI instance
export const uploadUI = new UploadUI();

export {
    UploadBanner,
    UploadUI,
};

export default UploadUI;
