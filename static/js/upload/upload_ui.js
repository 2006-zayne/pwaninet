/**
 * Upload UI
 * 
 * Manages the global upload banner and UI components.
 * Displays current stage, overall progress, current file, files completed, 
 * and estimated remaining time. Smoothly animates between states.
 * No alert dialogs or blocking modals.
 */

import { uploadEvents, UploadEventNames } from './upload_events.js?v=20261011-16';
import { UploadState } from './upload_state_machine.js?v=20261011-16';
import { uploadManager } from './upload_manager.js?v=20261011-16';

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
     * Create the banner DOM element - subtle donut spinner with count
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
            <div class="upload-donut-container">
                <svg class="upload-donut" viewBox="0 0 32 32">
                    <circle class="upload-donut-bg" cx="16" cy="16" r="14" fill="none" />
                    <circle class="upload-donut-progress" id="upload-donut-progress" cx="16" cy="16" r="14" fill="none" 
                            stroke-dasharray="0, 88" stroke-dashoffset="0" />
                </svg>
                <div class="upload-count" id="upload-count">0</div>
            </div>
            <button class="upload-cancel-btn" id="upload-banner-cancel" title="Cancel">
                <i class="bi bi-x-lg"></i>
            </button>
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
            cancelBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.cancelCurrentUpload();
            });
        }

        // Click on banner to navigate to uploads page
        this.banner.addEventListener('click', (e) => {
            if (e.target.closest('.upload-cancel-btn')) return; // Don't navigate if clicking cancel
            window.location.href = '/uploads/';
        });

        // Upload state machine events
        uploadEvents.on(UploadEventNames.UPLOAD_CREATED, (data) => {
            this.handleUploadCreated(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_STARTED, (data) => {
            this.handleUploadStarted(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_PUBLISHED, (data) => {
            this.handleUploadPublished(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_COMPLETED, (data) => {
            this.handleUploadCompleted(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_FAILED, (data) => {
            this.handleUploadFailed(data);
        });

        uploadEvents.on(UploadEventNames.UPLOAD_CANCELLED, (data) => {
            this.handleUploadCancelled(data);
        });

        // Listen to resumable upload progress events
        window.addEventListener('resumable-upload-progress', (e) => {
            this.handleResumableProgress(e.detail);
        });
    }

    /**
     * Handle upload created
     */
    handleUploadCreated(data) {
        console.log('[UploadUI] Upload created:', data);
        this.activeUploadCount = (this.activeUploadCount || 0) + 1;
        this.updateCount();
        this.show();
    }

    /**
     * Handle upload started
     */
    handleUploadStarted(data) {
        this.currentUploadId = data.uploadId;
        this.show();
    }

    /**
     * Handle resumable upload progress
     */
    handleResumableProgress(detail) {
        console.log('[UploadUI] Resumable progress:', detail);
        if (detail && detail.total) {
            const percent = Math.round((100 * detail.loaded) / detail.total);
            this.updateDonutProgress(percent);
        }
    }

    /**
     * Handle post published
     */
    handleUploadPublished(data) {
        this.hasVideo = Boolean(data.hasVideo);
        this.updateDonutProgress(100);

        if (!this.hasVideo) {
            // Non-video: hide after short delay
            setTimeout(() => {
                this.activeUploadCount = Math.max(0, (this.activeUploadCount || 1) - 1);
                this.updateCount();
                if (this.activeUploadCount === 0) {
                    this.hide();
                }
            }, 2000);
        }
        // Video: stay visible during processing
    }

    /**
     * Handle upload completed
     */
    handleUploadCompleted(data) {
        this.activeUploadCount = Math.max(0, (this.activeUploadCount || 1) - 1);
        this.updateCount();
        if (this.activeUploadCount === 0) {
            setTimeout(() => this.hide(), 1500);
        }
    }

    /**
     * Handle upload failed
     */
    handleUploadFailed(data) {
        this.activeUploadCount = Math.max(0, (this.activeUploadCount || 1) - 1);
        this.updateCount();
        if (this.activeUploadCount === 0) {
            setTimeout(() => this.hide(), 3000);
        }
    }

    /**
     * Handle upload cancelled
     */
    handleUploadCancelled(data) {
        this.activeUploadCount = Math.max(0, (this.activeUploadCount || 1) - 1);
        this.updateCount();
        if (this.activeUploadCount === 0) {
            this.hide();
        }
    }

    /**
     * Update donut progress
     */
    updateDonutProgress(percent) {
        const progressEl = document.getElementById('upload-donut-progress');
        if (progressEl) {
            // circumference ≈ 88 for radius 14
            // offset = 88 - (percent/100 * 88)
            const circumference = 88;
            const offset = circumference - (percent / 100 * circumference);
            progressEl.setAttribute('stroke-dashoffset', offset);
        }
    }

    /**
     * Update upload count
     */
    updateCount() {
        const countEl = document.getElementById('upload-count');
        if (countEl) {
            countEl.textContent = this.activeUploadCount || 0;
        }
    }

    /**
     * Show the banner
     */
    show() {
        if (!this.banner) return;
        this.banner.classList.add('visible');
        this.isVisible = true;
    }

    /**
     * Hide the banner
     */
    hide() {
        if (!this.banner) return;
        this.banner.classList.remove('visible');
        this.isVisible = false;
        this.activeUploadCount = 0;
        this.updateCount();
        this.updateDonutProgress(0);
    }

    /**
     * Cancel current upload
     */
    cancelCurrentUpload() {
        const currentUpload = uploadManager.getActiveUpload();
        if (currentUpload) {
            uploadManager.cancelUpload(currentUpload.id);
        } else if (this.currentUploadId) {
            uploadManager.cancelUpload(this.currentUploadId);
        }
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
        this.restoreBannerOnLoad();
        this.isInitialized = true;
    }

    /**
     * Check for ongoing uploads on page load and restore banner
     */
    async restoreBannerOnLoad() {
        try {
            // Check if resumable engine has any active sessions
            if (window.resumableUpload && typeof window.resumableUpload.getAllSessions === 'function') {
                const sessions = await window.resumableUpload.getAllSessions();
                const activeSessions = sessions.filter(s => !s.done);
                if (activeSessions.length > 0) {
                    this.banner.activeUploadCount = activeSessions.length;
                    this.banner.updateCount();
                    this.banner.show();
                }
            }
        } catch (e) {
            console.error('[UploadUI] Failed to restore banner:', e);
        }
    }

    /**
     * Inject CSS styles for the upload banner - subtle donut spinner
     */
    injectStyles() {
        if (document.getElementById('upload-banner-styles')) return;

        const style = document.createElement('style');
        style.id = 'upload-banner-styles';
        style.textContent = `
            /* ================================================================
               Subtle Donut Upload Spinner
               ================================================================ */

            .upload-banner {
                position: fixed;
                z-index: 9995;
                display: flex;
                align-items: center;
                gap: 8px;
                opacity: 0;
                pointer-events: none;
                transition: opacity 0.3s ease;
            }

            .upload-banner.visible {
                opacity: 1;
                pointer-events: auto;
            }

            /* Mobile: left side, slightly on top of bottom nav bar */
            @media (max-width: 767.98px) {
                .upload-banner {
                    bottom: calc(72px + var(--vasto-safe-area-bottom, env(safe-area-inset-bottom, 0px)));
                    left: 12px;
                }
            }

            /* Make donut clickable for navigation */
            .upload-donut-container {
                cursor: pointer;
            }

            /* Desktop: floats where current banner was (bottom-right) */
            @media (min-width: 768px) {
                .upload-banner {
                    bottom: 24px;
                    right: 28px;
                }
            }

            /* Donut Container */
            .upload-donut-container {
                position: relative;
                width: 32px;
                height: 32px;
            }

            /* SVG Donut */
            .upload-donut {
                width: 100%;
                height: 100%;
                transform: rotate(-90deg);
            }

            .upload-donut-bg {
                fill: none;
                stroke: var(--border, #3a3b3c);
                stroke-width: 2.5;
            }

            [data-theme="light"] .upload-donut-bg {
                stroke: var(--border, #e2e8f0);
            }

            .upload-donut-progress {
                fill: none;
                stroke: #3b82f6;
                stroke-width: 2.5;
                stroke-linecap: round;
                stroke-dasharray: 88, 88; /* 2 * PI * 14 ≈ 88 */
                stroke-dashoffset: 88;
                transition: stroke-dashoffset 0.3s ease;
            }

            /* Count in center */
            .upload-count {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 11px;
                font-weight: 700;
                color: var(--text-dark, #e4e6eb);
                font-variant-numeric: tabular-nums;
            }

            [data-theme="light"] .upload-count {
                color: var(--text-dark, #0f172a);
            }

            /* Cancel Button */
            .upload-cancel-btn {
                background: transparent;
                border: none;
                color: var(--text-muted, #b0b3b8);
                width: 24px;
                height: 24px;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 12px;
                transition: background 0.15s, color 0.15s;
            }

            .upload-cancel-btn:hover {
                background: var(--border, #3a3b3c);
                color: var(--text-dark, #e4e6eb);
            }

            [data-theme="light"] .upload-cancel-btn {
                color: var(--text-muted, #64748b);
            }
            [data-theme="light"] .upload-cancel-btn:hover {
                background: var(--border, #e2e8f0);
                color: var(--text-dark, #0f172a);
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
            this.banner.show();
        });

        // Hide banner when queue clears
        uploadEvents.on(UploadEventNames.QUEUE_CLEARED, () => {
            this.banner.hide();
        });

        // No beforeunload warning needed - resumable engine survives refresh
    }

    /**
     * Get banner instance
     * @returns {UploadBanner}
     */
    getBanner() {
        return this.banner;
    }

    // Direct proxy methods to inner banner
    show() { return this.banner.show(); }
    hide() { return this.banner.hide(); }
    reset() { return this.banner.reset(); }
    setHeaderTitle(text, phaseClass) { return this.banner.setHeaderTitle(text, phaseClass); }
    setTitle(text) { return this.banner.setTitle(text); }
    setSubtitle(text) { return this.banner.setSubtitle(text); }
    updateProgress(percent) { return this.banner.updateProgress(percent); }
    setProgressFillClass(className) { return this.banner.setProgressFillClass(className); }
    updateMiniText(text) { return this.banner.updateMiniText(text); }
    showError(message, canRetry) { return this.banner.showError(message, canRetry); }
    showCompletion() { return this.banner.showCompletion(); }
    handleUploadProgress(data) { return this.banner.handleUploadProgress(data); }
}

// Global upload UI instance
export const uploadUI = new UploadUI();

export {
    UploadBanner,
    UploadUI,
};

export default UploadUI;
