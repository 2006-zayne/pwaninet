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
        this.isMinimized = false;
        this.currentUploadId = null;
        this.bannerMode = 'cancel'; // 'cancel' | 'retry'
        this.autoHideTimer = null;
        this.phaseTransitionTimer = null;
        this.currentProgress = 0;
        this.activeThumbnailUrls = [];
        this.hasVideo = false;
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
        if (document.getElementById('upload-banner')) {
            this.banner = document.getElementById('upload-banner');
            return;
        }

        const banner = document.createElement('div');
        banner.id = 'upload-banner';
        banner.className = 'upload-banner';
        banner.innerHTML = `
            <!-- Header Bar -->
            <div class="upload-banner-header" id="upload-banner-header">
                <div class="upload-banner-badge-wrapper">
                    <span class="upload-header-dot" id="upload-header-dot"></span>
                    <span class="upload-header-title" id="upload-header-title">POSTING MEDIA</span>
                </div>
                <div class="upload-header-actions">
                    <button class="upload-action-btn upload-minimize-btn" id="upload-banner-minimize" title="Minimize / Expand">
                        <i class="bi bi-dash-lg" id="upload-minimize-icon"></i>
                    </button>
                    <button class="upload-action-btn upload-cancel-btn" id="upload-banner-cancel" title="Cancel">
                        <i class="bi bi-x-lg" id="upload-cancel-icon"></i>
                    </button>
                </div>
            </div>

            <!-- Expanded Body -->
            <div class="upload-banner-body" id="upload-banner-body">
                <div class="upload-banner-thumb-box" id="upload-banner-thumb-box">
                    <div class="upload-banner-thumb" id="upload-banner-thumb">
                        <i class="bi bi-cloud-arrow-up" id="upload-thumb-fallback"></i>
                    </div>
                    <span class="upload-thumb-duration" id="upload-thumb-duration" style="display: none;"></span>
                </div>
                <div class="upload-banner-info-col">
                    <div class="upload-banner-title-row">
                        <span class="upload-primary-title" id="upload-banner-title">Uploading post…</span>
                        <span class="upload-progress-number" id="upload-banner-progress">0%</span>
                    </div>
                    <div class="upload-banner-sub-row" id="upload-banner-sub">
                        Preparing media…
                    </div>
                    <div class="upload-quality-pills" id="upload-quality-pills" style="display: none;">
                        <span class="quality-pill" id="pill-240p">240p</span>
                        <span class="quality-pill" id="pill-360p">360p</span>
                        <span class="quality-pill" id="pill-480p">480p</span>
                        <span class="quality-pill" id="pill-720p">720p HD</span>
                    </div>
                </div>
            </div>

            <!-- Progress Track -->
            <div class="upload-banner-progress-track" id="upload-banner-progress-track">
                <div class="upload-banner-progress-fill phase-upload" id="upload-banner-progress-fill"></div>
            </div>

            <!-- Minimized View (Visible when .is-minimized is set) -->
            <div class="upload-mini-content" id="upload-mini-content" style="display: none;">
                <div class="upload-mini-left">
                    <span class="upload-mini-icon" id="upload-mini-icon">
                        <i class="bi bi-arrow-repeat spin-icon"></i>
                    </span>
                    <span class="upload-mini-text" id="upload-mini-text">Uploading (0%)</span>
                </div>
                <button class="upload-action-btn upload-mini-expand-btn" id="upload-mini-expand" title="Expand">
                    <i class="bi bi-chevron-up"></i>
                </button>
            </div>
        `;

        document.body.appendChild(banner);
        this.banner = banner;
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Cancel / Retry button
        const cancelBtn = document.getElementById('upload-banner-cancel');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.bannerMode === 'retry') {
                    this.retryCurrentUpload();
                } else {
                    this.cancelCurrentUpload();
                }
            });
        }

        // Minimize / Expand button
        const minimizeBtn = document.getElementById('upload-banner-minimize');
        if (minimizeBtn) {
            minimizeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMinimize();
            });
        }

        // Minimized bar click to expand
        const miniContent = document.getElementById('upload-mini-content');
        if (miniContent) {
            miniContent.addEventListener('click', () => {
                if (this.isMinimized) {
                    this.toggleMinimize(false);
                }
            });
        }

        const miniExpandBtn = document.getElementById('upload-mini-expand');
        if (miniExpandBtn) {
            miniExpandBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMinimize(false);
            });
        }

        // Upload state machine events
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
     * Setup thumbnail preview client-side immediately
     */
    setThumbnail(files) {
        if (!files || !files.length) return;

        const thumbContainer = document.getElementById('upload-banner-thumb');
        const durationBadge = document.getElementById('upload-thumb-duration');
        if (!thumbContainer) return;

        this.cleanupThumbnails();

        const videoFile = files.find((f) =>
            f.type?.startsWith('video/') || /\.(mp4|mov|webm|mkv|avi)$/i.test(f.name ?? '')
        );
        const imageFile = files.find((f) => f.type?.startsWith('image/'));

        if (videoFile) {
            this.hasVideo = true;
            try {
                const objectUrl = URL.createObjectURL(videoFile);
                this.activeThumbnailUrls.push(objectUrl);

                thumbContainer.innerHTML = `
                    <video src="${objectUrl}#t=0.1" preload="metadata" muted playsinline class="upload-thumb-media"></video>
                    <div class="upload-thumb-play-icon"><i class="bi bi-play-fill"></i></div>
                `;

                // Read duration metadata
                const tempVideo = document.createElement('video');
                tempVideo.preload = 'metadata';
                tempVideo.src = objectUrl;
                tempVideo.onloadedmetadata = () => {
                    if (tempVideo.duration && durationBadge) {
                        durationBadge.textContent = this.formatDuration(tempVideo.duration);
                        durationBadge.style.display = 'block';
                    }
                };
            } catch (err) {
                thumbContainer.innerHTML = '<i class="bi bi-camera-video-fill upload-thumb-icon"></i>';
            }
        } else if (imageFile) {
            this.hasVideo = false;
            try {
                const objectUrl = URL.createObjectURL(imageFile);
                this.activeThumbnailUrls.push(objectUrl);
                thumbContainer.innerHTML = `<img src="${objectUrl}" class="upload-thumb-media" alt="Upload Preview" />`;
            } catch (err) {
                thumbContainer.innerHTML = '<i class="bi bi-image-fill upload-thumb-icon"></i>';
            }
            if (durationBadge) durationBadge.style.display = 'none';
        } else {
            this.hasVideo = false;
            thumbContainer.innerHTML = '<i class="bi bi-file-earmark-text-fill upload-thumb-icon"></i>';
            if (durationBadge) durationBadge.style.display = 'none';
        }
    }

    cleanupThumbnails() {
        this.activeThumbnailUrls.forEach((url) => {
            try {
                URL.revokeObjectURL(url);
            } catch (e) {}
        });
        this.activeThumbnailUrls = [];
    }

    /**
     * Toggle minimized floating chip mode
     */
    toggleMinimize(forceState = null) {
        this.isMinimized = forceState !== null ? forceState : !this.isMinimized;
        if (!this.banner) return;

        const body = document.getElementById('upload-banner-body');
        const header = document.getElementById('upload-banner-header');
        const miniContent = document.getElementById('upload-mini-content');
        const minimizeIcon = document.getElementById('upload-minimize-icon');

        if (this.isMinimized) {
            this.banner.classList.add('is-minimized');
            if (body) body.style.display = 'none';
            if (header) header.style.display = 'none';
            if (miniContent) miniContent.style.display = 'flex';
            if (minimizeIcon) minimizeIcon.className = 'bi bi-chevron-up';
        } else {
            this.banner.classList.remove('is-minimized');
            if (body) body.style.display = 'flex';
            if (header) header.style.display = 'flex';
            if (miniContent) miniContent.style.display = 'none';
            if (minimizeIcon) minimizeIcon.className = 'bi bi-dash-lg';
        }
    }

    /**
     * Handle state machine state changes
     */
    handleStateChange(data) {
        const { uploadId, newState, metadata } = data;
        this.currentUploadId = uploadId;
        this.clearAutoHideTimer();

        if (newState === UploadState.UPLOADING) {
            this.setHeaderTitle('POSTING MEDIA', 'phase-upload');
            this.setTitle('Uploading post…');
            this.setProgressFillClass('phase-upload');
            this.setCancelMode();
        } else if (newState === UploadState.SERVER_PROCESSING) {
            if (this.hasVideo) {
                this.setHeaderTitle('OPTIMIZING VIDEO', 'phase-transcoding');
                this.setTitle('Processing HD video…');
                this.setProgressFillClass('phase-transcoding');
                this.showQualityPills(true);
            } else {
                this.setHeaderTitle('SAVING', 'phase-upload');
                this.setTitle('Saving to feed…');
            }
        } else if (newState === UploadState.PUBLISHED) {
            this.showCompletion();
        } else if (newState === UploadState.FAILED) {
            this.showError(metadata?.error || 'Upload failed', true);
        } else if (newState === UploadState.CANCELLED) {
            this.hide();
        }
    }

    /**
     * Handle upload byte transfer progress
     */
    handleUploadProgress(data) {
        const { loaded, total, percent, speed, estimatedTimeRemaining } = data;
        this.updateProgress(percent);

        let speedText = '';
        if (speed > 0) {
            speedText = ` • ${this.formatSpeed(speed)}`;
        }

        let timeText = '';
        if (estimatedTimeRemaining > 0) {
            timeText = ` • ~${this.formatTime(Math.round(estimatedTimeRemaining))} left`;
        }

        const loadedFormatted = this.formatBytes(loaded);
        const totalFormatted = this.formatBytes(total);
        const detailString = `${Math.round(percent)}% • ${loadedFormatted} of ${totalFormatted}${speedText}${timeText}`;

        this.setSubtitle(detailString);
        this.updateMiniText(`Uploading (${Math.round(percent)}%)`);
    }

    /**
     * Handle generic progress update (e.g. transcoding percentage via WS)
     */
    handleProgressUpdate(data) {
        const { stage, percent, status } = data;
        this.updateProgress(percent);

        if (stage === 'serverProcessing') {
            this.setSubtitle(status || 'Optimizing video qualities…');
            this.updateMiniText(`HD Processing (${Math.round(percent)}%)`);
            this.updateQualityPills(percent);
        } else if (status) {
            this.setSubtitle(status);
        }
    }

    /**
     * Handle image compression progress
     */
    handleCompressionProgress(data) {
        const { current, total, percent } = data;
        this.setHeaderTitle('OPTIMIZING IMAGES', 'phase-upload');
        this.setTitle(`Compressing ${current}/${total}`);
        this.updateProgress(percent);
        this.setSubtitle(`${Math.round(percent)}% complete`);
    }

    /**
     * Handle single upload completed in queue
     */
    handleUploadCompleted() {
        // Queue progress indicator
    }

    /**
     * Handle post published confirmation (HTTP 201 received)
     */
    handleUploadPublished(data) {
        const { hasVideo } = data;
        this.hasVideo = Boolean(hasVideo);

        // Immediate confirmation
        this.setHeaderTitle('POST PUBLISHED', 'phase-published');
        this.setTitle('Post published!');
        this.setSubtitle('Your post is live in your feed');
        this.updateProgress(100);
        this.setProgressFillClass('phase-published');
        this.updateMiniText('Post published! ✓');

        // Trigger HTMX feed refresh if feed container exists
        const feedRefreshTarget = document.querySelector('[data-upload-feed-refresh]');
        if (feedRefreshTarget && window.htmx) {
            const refreshUrl = feedRefreshTarget.getAttribute('data-upload-feed-refresh-url') || window.location.pathname;
            window.htmx.ajax('GET', refreshUrl, {
                target: '#main-content-area',
                swap: 'innerHTML',
            });
        }

        if (!this.hasVideo) {
            // Non-video post: celebrate and auto-hide
            this.clearAutoHideTimer();
            this.autoHideTimer = setTimeout(() => {
                this.hide();
            }, 2600);
        } else {
            // Video post: show Published badge for 1.8s then transition to HD transcoding telemetry
            if (this.phaseTransitionTimer) clearTimeout(this.phaseTransitionTimer);
            this.phaseTransitionTimer = setTimeout(() => {
                this.setHeaderTitle('OPTIMIZING VIDEO', 'phase-transcoding');
                this.setTitle('Processing HD video…');
                this.setSubtitle('Preparing multi-bitrate HLS streams…');
                this.setProgressFillClass('phase-transcoding');
                this.showQualityPills(true);
                this.updateProgress(5);
            }, 1800);
        }
    }

    /**
     * Handle upload failure
     */
    handleUploadFailed(data) {
        this.currentUploadId = data.uploadId || this.currentUploadId;
        this.clearAutoHideTimer();
        this.showError(data.error || 'Upload interrupted', data.canRetry === true);
    }

    /**
     * Show completion state (transcoding done)
     */
    showCompletion() {
        this.setHeaderTitle('ALL SET', 'phase-published');
        this.setTitle(this.hasVideo ? 'Video ready in HD!' : 'Post published!');
        this.setSubtitle('All video qualities are active');
        this.updateProgress(100);
        this.setProgressFillClass('phase-published');
        this.updateMiniText('Ready in HD! ✓');
        this.updateQualityPills(100);

        this.clearAutoHideTimer();
        this.autoHideTimer = setTimeout(() => {
            this.hide();
        }, 3600);
    }

    /**
     * Show error state
     */
    showError(message, canRetry = false) {
        this.setHeaderTitle('UPLOAD FAILED', 'phase-error');
        this.setTitle('Upload interrupted');
        this.setSubtitle(message || 'Network disconnected • Tap to retry');
        this.setProgressFillClass('phase-error');
        this.updateMiniText('Upload failed ✕');

        if (canRetry) {
            this.setRetryMode();
        } else {
            this.setCancelMode();
            this.clearAutoHideTimer();
            this.autoHideTimer = setTimeout(() => {
                this.hide();
            }, 5000);
        }
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
        if (this.phaseTransitionTimer) clearTimeout(this.phaseTransitionTimer);

        this.banner.classList.remove('visible');
        this.isVisible = false;

        setTimeout(() => {
            this.reset();
        }, 350);
    }

    /**
     * Reset banner state
     */
    reset() {
        this.cleanupThumbnails();
        this.toggleMinimize(false);
        this.hasVideo = false;
        this.currentProgress = 0;
        this.setCancelMode();

        this.setHeaderTitle('POSTING MEDIA', 'phase-upload');
        this.setTitle('Uploading post…');
        this.setSubtitle('Preparing media…');
        this.updateProgress(0);
        this.showQualityPills(false);
        this.setProgressFillClass('phase-upload');

        const thumb = document.getElementById('upload-banner-thumb');
        if (thumb) thumb.innerHTML = '<i class="bi bi-cloud-arrow-up" id="upload-thumb-fallback"></i>';

        const duration = document.getElementById('upload-thumb-duration');
        if (duration) duration.style.display = 'none';
    }

    // --- UI Helper setters ----------------------------------------------------

    setHeaderTitle(text, phaseClass = '') {
        const titleEl = document.getElementById('upload-header-title');
        const dotEl = document.getElementById('upload-header-dot');
        if (titleEl) titleEl.textContent = text;
        if (dotEl) {
            dotEl.className = 'upload-header-dot';
            if (phaseClass) dotEl.classList.add(phaseClass);
        }
    }

    setTitle(text) {
        const titleEl = document.getElementById('upload-banner-title');
        if (titleEl) titleEl.textContent = text;
    }

    setSubtitle(text) {
        const subEl = document.getElementById('upload-banner-sub');
        if (subEl) subEl.textContent = text;
    }

    updateProgress(percent) {
        const numEl = document.getElementById('upload-banner-progress');
        const fillEl = document.getElementById('upload-banner-progress-fill');
        const clamped = Math.min(100, Math.max(0, Math.round(percent)));

        if (numEl) numEl.textContent = `${clamped}%`;
        if (fillEl) fillEl.style.width = `${clamped}%`;
        this.currentProgress = clamped;
    }

    setProgressFillClass(className) {
        const fillEl = document.getElementById('upload-banner-progress-fill');
        if (fillEl) {
            fillEl.className = `upload-banner-progress-fill ${className}`;
        }
    }

    updateMiniText(text) {
        const miniTextEl = document.getElementById('upload-mini-text');
        if (miniTextEl) miniTextEl.textContent = text;
    }

    showQualityPills(show) {
        const pillsEl = document.getElementById('upload-quality-pills');
        if (pillsEl) pillsEl.style.display = show ? 'flex' : 'none';
    }

    updateQualityPills(percent) {
        const p240 = document.getElementById('pill-240p');
        const p360 = document.getElementById('pill-360p');
        const p480 = document.getElementById('pill-480p');
        const p720 = document.getElementById('pill-720p');

        if (p240) {
            p240.className = percent >= 22 ? 'quality-pill ready' : 'quality-pill encoding';
        }
        if (p360) {
            p360.className = percent >= 45 ? 'quality-pill ready' : percent >= 22 ? 'quality-pill encoding' : 'quality-pill';
        }
        if (p480) {
            p480.className = percent >= 67 ? 'quality-pill ready' : percent >= 45 ? 'quality-pill encoding' : 'quality-pill';
        }
        if (p720) {
            p720.className = percent >= 90 ? 'quality-pill ready' : percent >= 67 ? 'quality-pill encoding' : 'quality-pill';
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
            cancelBtn.innerHTML = '<i class="bi bi-x-lg" id="upload-cancel-icon"></i>';
            cancelBtn.title = 'Cancel';
        }
    }

    setRetryMode() {
        this.bannerMode = 'retry';
        const cancelBtn = document.getElementById('upload-banner-cancel');
        if (cancelBtn) {
            cancelBtn.innerHTML = '<i class="bi bi-arrow-clockwise" id="upload-cancel-icon"></i>';
            cancelBtn.title = 'Retry upload';
        }
    }

    retryCurrentUpload() {
        if (this.currentUploadId) {
            uploadManager.retryUpload(this.currentUploadId);
            this.setCancelMode();
            this.setHeaderTitle('POSTING MEDIA', 'phase-upload');
            this.setTitle('Retrying upload…');
            this.updateProgress(0);
        }
    }

    cancelCurrentUpload() {
        const currentUpload = uploadManager.getActiveUpload();
        if (currentUpload) {
            uploadManager.cancelUpload(currentUpload.id);
        } else if (this.currentUploadId) {
            uploadManager.cancelUpload(this.currentUploadId);
        }
    }

    // --- Formatters -----------------------------------------------------------

    formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 MB';
        const mb = bytes / (1024 * 1024);
        return `${mb.toFixed(1)} MB`;
    }

    formatSpeed(bytesPerSec) {
        if (!bytesPerSec || bytesPerSec <= 0) return '';
        const mbPerSec = bytesPerSec / (1024 * 1024);
        if (mbPerSec >= 1) {
            return `${mbPerSec.toFixed(1)} MB/s`;
        }
        const kbPerSec = bytesPerSec / 1024;
        return `${Math.round(kbPerSec)} KB/s`;
    }

    formatDuration(seconds) {
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return `${m}:${s < 10 ? '0' : ''}${s}`;
    }

    formatTime(seconds) {
        if (seconds < 60) return `${Math.round(seconds)}s`;
        const m = Math.floor(seconds / 60);
        const s = Math.round(seconds % 60);
        return `${m}m ${s}s`;
    }

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
        if (document.getElementById('upload-banner-styles')) return;

        const style = document.createElement('style');
        style.id = 'upload-banner-styles';
        style.textContent = `
            /* ================================================================
               Pwaninet Professional Upload Banner & Floating Dock
               ================================================================ */

            .upload-banner {
                position: fixed;
                z-index: 9995;
                background: rgba(18, 20, 26, 0.88);
                backdrop-filter: blur(18px) saturate(180%);
                -webkit-backdrop-filter: blur(18px) saturate(180%);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
                box-shadow: 0 16px 40px -4px rgba(0, 0, 0, 0.4), 0 4px 12px rgba(0, 0, 0, 0.15);
                overflow: hidden;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                            transform 0.28s cubic-bezier(0.16, 1, 0.3, 1),
                            width 0.25s ease;
                font-family: inherit;
            }

            /* Light theme support */
            [data-theme="light"] .upload-banner {
                background: rgba(255, 255, 255, 0.92);
                border-color: rgba(0, 0, 0, 0.1);
                box-shadow: 0 16px 36px -4px rgba(0, 0, 0, 0.15), 0 4px 12px rgba(0, 0, 0, 0.05);
            }

            /* Mobile positioning: centered floating pill right above bottom navigation bar */
            @media (max-width: 767.98px) {
                .upload-banner {
                    bottom: calc(82px + var(--pwaninet-safe-area-bottom, env(safe-area-inset-bottom, 0px)));
                    left: 50%;
                    transform: translateX(-50%) translateY(24px) scale(0.96);
                    width: calc(100% - 24px);
                    max-width: 420px;
                }
                .upload-banner.visible {
                    opacity: 1;
                    pointer-events: auto;
                    transform: translateX(-50%) translateY(0) scale(1);
                }
                .upload-banner-thumb {
                    width: 42px !important;
                    height: 42px !important;
                }
                .upload-quality-pills {
                    display: none !important;
                }
            }

            /* Desktop positioning: bottom-right floating dock */
            @media (min-width: 768px) {
                .upload-banner {
                    bottom: 24px;
                    right: 28px;
                    left: auto;
                    transform: translateY(24px) scale(0.96);
                    width: 380px;
                    max-width: 380px;
                }
                .upload-banner.visible {
                    opacity: 1;
                    pointer-events: auto;
                    transform: translateY(0) scale(1);
                }
                .upload-banner.visible.is-minimized {
                    width: 290px;
                }
                .upload-banner-thumb {
                    width: 60px;
                    height: 38px;
                }
            }

            /* Header */
            .upload-banner-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 10px 14px 6px 14px;
            }

            .upload-banner-badge-wrapper {
                display: flex;
                align-items: center;
                gap: 7px;
            }

            .upload-header-dot {
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #3b82f6;
                box-shadow: 0 0 8px #3b82f6;
                transition: background 0.3s, box-shadow 0.3s;
            }

            .upload-header-dot.phase-upload {
                background: #3b82f6;
                box-shadow: 0 0 8px #3b82f6;
                animation: dot-pulse 1.6s ease-in-out infinite;
            }

            .upload-header-dot.phase-published {
                background: #10b981;
                box-shadow: 0 0 8px #10b981;
                animation: none;
            }

            .upload-header-dot.phase-transcoding {
                background: #8b5cf6;
                box-shadow: 0 0 8px #8b5cf6;
                animation: dot-pulse 1.4s ease-in-out infinite;
            }

            .upload-header-dot.phase-error {
                background: #ef4444;
                box-shadow: 0 0 8px #ef4444;
                animation: none;
            }

            @keyframes dot-pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.4; transform: scale(0.85); }
            }

            .upload-header-title {
                font-size: 10.5px;
                font-weight: 700;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: rgba(255, 255, 255, 0.65);
            }

            [data-theme="light"] .upload-header-title {
                color: rgba(0, 0, 0, 0.55);
            }

            .upload-header-actions {
                display: flex;
                align-items: center;
                gap: 6px;
            }

            .upload-action-btn {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 0.65);
                width: 26px;
                height: 26px;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 13px;
                transition: background 0.15s, color 0.15s;
            }

            .upload-action-btn:hover {
                background: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }

            [data-theme="light"] .upload-action-btn {
                color: rgba(0, 0, 0, 0.55);
            }
            [data-theme="light"] .upload-action-btn:hover {
                background: rgba(0, 0, 0, 0.06);
                color: #000000;
            }

            /* Body */
            .upload-banner-body {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 4px 14px 12px 14px;
            }

            /* Thumbnail */
            .upload-banner-thumb-box {
                position: relative;
                flex-shrink: 0;
            }

            .upload-banner-thumb {
                border-radius: 9px;
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.1);
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }

            [data-theme="light"] .upload-banner-thumb {
                background: rgba(0, 0, 0, 0.04);
                border-color: rgba(0, 0, 0, 0.08);
            }

            .upload-thumb-media {
                width: 100%;
                height: 100%;
                object-fit: cover;
                display: block;
            }

            .upload-thumb-icon {
                font-size: 18px;
                color: rgba(255, 255, 255, 0.6);
            }

            [data-theme="light"] .upload-thumb-icon {
                color: rgba(0, 0, 0, 0.5);
            }

            .upload-thumb-play-icon {
                position: absolute;
                inset: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(0, 0, 0, 0.28);
                color: white;
                font-size: 13px;
                pointer-events: none;
            }

            .upload-thumb-duration {
                position: absolute;
                bottom: 2px;
                right: 3px;
                background: rgba(0, 0, 0, 0.75);
                color: white;
                font-size: 9px;
                font-weight: 600;
                padding: 1px 3px;
                border-radius: 3px;
                line-height: 1.1;
                pointer-events: none;
            }

            /* Info Column */
            .upload-banner-info-col {
                flex: 1;
                min-width: 0;
                display: flex;
                flex-direction: column;
                gap: 2px;
            }

            .upload-banner-title-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 8px;
            }

            .upload-primary-title {
                font-size: 13.5px;
                font-weight: 600;
                color: #ffffff;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            [data-theme="light"] .upload-primary-title {
                color: #111827;
            }

            .upload-progress-number {
                font-size: 12px;
                font-weight: 700;
                color: rgba(255, 255, 255, 0.9);
                font-variant-numeric: tabular-nums;
            }

            [data-theme="light"] .upload-progress-number {
                color: #374151;
            }

            .upload-banner-sub-row {
                font-size: 11.5px;
                color: rgba(255, 255, 255, 0.65);
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            [data-theme="light"] .upload-banner-sub-row {
                color: #6b7280;
            }

            /* Quality Pills */
            .upload-quality-pills {
                display: flex;
                align-items: center;
                gap: 5px;
                margin-top: 3px;
            }

            .quality-pill {
                font-size: 9.5px;
                font-weight: 600;
                padding: 1px 6px;
                border-radius: 4px;
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.08);
                transition: background 0.2s, color 0.2s;
            }

            [data-theme="light"] .quality-pill {
                background: rgba(0, 0, 0, 0.04);
                color: rgba(0, 0, 0, 0.45);
                border-color: rgba(0, 0, 0, 0.06);
            }

            .quality-pill.encoding {
                background: rgba(139, 92, 246, 0.18);
                color: #c4b5fd;
                border-color: rgba(139, 92, 246, 0.3);
                animation: pill-pulse 1.2s ease-in-out infinite;
            }

            .quality-pill.ready {
                background: rgba(16, 185, 129, 0.18);
                color: #6ee7b7;
                border-color: rgba(16, 185, 129, 0.3);
                animation: none;
            }

            @keyframes pill-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.55; }
            }

            /* Progress Bar */
            .upload-banner-progress-track {
                height: 3px;
                background: rgba(255, 255, 255, 0.1);
                position: relative;
                width: 100%;
            }

            [data-theme="light"] .upload-banner-progress-track {
                background: rgba(0, 0, 0, 0.08);
            }

            .upload-banner-progress-fill {
                height: 100%;
                width: 0%;
                transition: width 0.22s ease-out;
            }

            .upload-banner-progress-fill.phase-upload {
                background: linear-gradient(90deg, #2563eb, #38bdf8);
            }

            .upload-banner-progress-fill.phase-published {
                background: linear-gradient(90deg, #10b981, #34d399);
            }

            .upload-banner-progress-fill.phase-transcoding {
                background: linear-gradient(90deg, #7c3aed, #a855f7);
                background-size: 24px 24px;
                background-image: linear-gradient(
                    45deg,
                    rgba(255, 255, 255, 0.15) 25%,
                    transparent 25%,
                    transparent 50%,
                    rgba(255, 255, 255, 0.15) 50%,
                    rgba(255, 255, 255, 0.15) 75%,
                    transparent 75%,
                    transparent
                );
                animation: progress-shimmer 1.2s linear infinite;
            }

            .upload-banner-progress-fill.phase-error {
                background: #ef4444;
            }

            @keyframes progress-shimmer {
                from { background-position: 24px 0; }
                to { background-position: 0 0; }
            }

            /* Minimized View */
            .upload-mini-content {
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 8px 14px;
                cursor: pointer;
            }

            .upload-mini-left {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .upload-mini-icon {
                color: #38bdf8;
                font-size: 13px;
                display: flex;
                align-items: center;
            }

            .upload-mini-icon .spin-icon {
                animation: spin 1s linear infinite;
            }

            .upload-mini-text {
                font-size: 12.5px;
                font-weight: 600;
                color: #ffffff;
            }

            [data-theme="light"] .upload-mini-text {
                color: #111827;
            }

            .upload-mini-expand-btn {
                width: 22px;
                height: 22px;
                font-size: 12px;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }
        `;

        document.head.appendChild(style);
    }

    setupGlobalListeners() {
        // Show banner and set preview as soon as upload is registered
        uploadEvents.on(UploadEventNames.UPLOAD_ADDED, (data) => {
            this.banner.currentUploadId = data.id;
            const files = Array.isArray(data.data?.files)
                ? data.data.files
                : Array.isArray(data.session?.files)
                ? data.session.files
                : [];
            this.banner.setThumbnail(files);
            this.banner.show();
        });

        // Hide banner when queue clears
        uploadEvents.on(UploadEventNames.QUEUE_CLEARED, () => {
            this.banner.hide();
        });

        // Warn if user attempts to leave during active byte upload
        window.addEventListener('beforeunload', (e) => {
            if (window.uploadManager && window.uploadManager.getActiveUpload()) {
                e.preventDefault();
                e.returnValue = 'You have an upload in progress. Leaving will cancel the upload.';
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
