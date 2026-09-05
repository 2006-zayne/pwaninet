/**
 * Upload Manager
 *
 * Single source of truth for all post uploads.
 * Owns session lifecycle, queue orchestration, progress, retries, cancellation,
 * preview cleanup, and UploadAPI communication.
 */

import { uploadEvents, UploadEventNames } from './upload_events.js';
import { UploadState, stateMachineFactory } from './upload_state_machine.js';
import { UploadValidator } from './upload_validator.js';
import { ImageCompressor } from './image_compression.js';
import { previewManager } from './preview_manager.js';
import { uploadAPI } from './upload_api.js';
import { uploadQueue } from './upload_queue.js';
import { progressManager } from './upload_progress.js';
import { UploadSession } from './upload_session.js';

class UploadManager {
    constructor() {
        this.uploads = new Map(); // uploadId -> UploadSession
        this.isInitialized = false;
    }

    initialize() {
        if (this.isInitialized) return;

        uploadEvents.on(UploadEventNames.UPLOAD_ADDED, (data) => {
            this.processUpload(data.id);
        });

        this.isInitialized = true;
    }

    createUpload(data) {
        const session = data instanceof UploadSession
            ? data
            : new UploadSession({
                id: uploadQueue.generateId(),
                files: data.files || [],
                caption: data.caption || data.content || '',
                visibility: data.visibility || 'public',
                metadata: {
                    unit: data.unit || data.metadata?.unit || null,
                    group: data.group || data.metadata?.group || null,
                    gradient_class: data.gradient_class || data.metadata?.gradient_class || 'none',
                    custom_gradient_text: data.custom_gradient_text || data.metadata?.custom_gradient_text || null,
                    custom_gradient_color1: data.custom_gradient_color1 || data.metadata?.custom_gradient_color1 || null,
                    custom_gradient_color2: data.custom_gradient_color2 || data.metadata?.custom_gradient_color2 || null,
                    custom_gradient_text_color: data.custom_gradient_text_color || data.metadata?.custom_gradient_text_color || null,
                },
            });

        this.uploads.set(session.id, session);
        stateMachineFactory.getMachine(session.id, UploadState.IDLE);
        progressManager.getTracker(session.id);

        uploadEvents.emit(UploadEventNames.UPLOAD_CREATED, {
            uploadId: session.id,
            session,
        });

        uploadQueue.addSession(session);
        return session.id;
    }

    async processUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        const progressTracker = progressManager.getTracker(uploadId);

        try {
            progressTracker.start();

            this.transitionState(uploadId, UploadState.PREPARING);
            await this.prepareUpload(uploadId);

            this.transitionState(uploadId, UploadState.VALIDATING);
            uploadEvents.emit(UploadEventNames.VALIDATION_STARTED, { uploadId });
            const validationResult = await this.validateUpload(uploadId);
            if (!validationResult.isValid) {
                throw new Error(validationResult.errors[0]?.message || 'Validation failed');
            }
            uploadEvents.emit(UploadEventNames.VALIDATION_COMPLETED, { uploadId });
            progressTracker.completeValidation();

            this.transitionState(uploadId, UploadState.READING_MEDIA);
            await this.readMedia(uploadId);

            this.transitionState(uploadId, UploadState.GENERATING_PREVIEW);
            await this.generatePreviews(uploadId);

            this.transitionState(uploadId, UploadState.COMPRESSING_IMAGES);
            await this.compressImages(uploadId);

            this.transitionState(uploadId, UploadState.READY);
            this.transitionState(uploadId, UploadState.QUEUED);

            this.waitForQueueTurn(uploadId);
        } catch (error) {
            this.failUpload(uploadId, error);
        }
    }

    transitionState(uploadId, newState, metadata = {}) {
        const session = this.uploads.get(uploadId);
        const machine = stateMachineFactory.getMachine(uploadId);
        if (!session || !machine) return false;

        const transitioned = machine.transitionTo(newState, metadata);
        if (transitioned) {
            session.setState(newState);
        }
        return transitioned;
    }

    async prepareUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;
    }

    async validateUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) {
            throw new Error('Upload session not found');
        }

        const tracker = progressManager.getTracker(uploadId);
        tracker.updateValidationProgress(0, session.files.length);

        const validationResult = await UploadValidator.validateUpload({
            files: session.files,
            caption: session.caption,
        });

        tracker.updateValidationProgress(session.files.length, session.files.length);
        return validationResult;
    }

    async readMedia(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;
    }

    async generatePreviews(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        const previews = await previewManager.generatePreviews(session.files, uploadId);
        session.previewUrls = previews.map((preview) => preview.objectUrl).filter(Boolean);
    }

    async compressImages(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        const tracker = progressManager.getTracker(uploadId);
        uploadEvents.emit(UploadEventNames.COMPRESSION_STARTED, { uploadId });

        const compressionResults = await ImageCompressor.compressMultiple(session.files);
        session.files = compressionResults.map((result) => result.compressedFile || result.originalFile);
        tracker.completeCompression();
    }

    waitForQueueTurn(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        const checkQueue = () => {
            const currentUpload = uploadQueue.getCurrentUpload();
            if (currentUpload && currentUpload.id === uploadId) {
                this.performUpload(uploadId);
            } else if (this.uploads.has(uploadId)) {
                setTimeout(checkQueue, 100);
            }
        };

        checkQueue();
    }

    async performUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        const tracker = progressManager.getTracker(uploadId);

        try {
            this.transitionState(uploadId, UploadState.UPLOADING);
            uploadEvents.emit(UploadEventNames.UPLOAD_STARTED, { uploadId, session });

            const response = await uploadAPI.upload(session, (progress) => {
                tracker.updateUploadProgress(progress.loaded, progress.total);
            });

            tracker.completeUpload();

            // Determine whether this post has a video file so we know
            // whether to wait for live HLS transcoding progress.
            const postId   = response?.id ?? null;
            const hasVideo = session.files?.some(
                (f) => f.type?.startsWith('video/') || /\.(mp4|mov|webm|mkv|avi)$/i.test(f.name ?? '')
            ) ?? false;

            // Immediately notify UI and feed that post has been created
            uploadEvents.emit(UploadEventNames.UPLOAD_PUBLISHED, { uploadId, session, postId, hasVideo });

            if (hasVideo && postId) {
                this.transitionState(uploadId, UploadState.SERVER_PROCESSING, { hasVideo: true, postId });
                await this.waitForServerProcessing(uploadId, postId, hasVideo);
                tracker.completeServerProcessing();
            } else {
                tracker.updateServerProcessingProgress(100, 100, 'Published!');
                tracker.completeServerProcessing();
            }

            this.transitionState(uploadId, UploadState.PUBLISHED);
            tracker.updatePublicationProgress(100);
            tracker.completePublication();

            uploadQueue.uploadCompleted(uploadId);
            uploadEvents.emit(UploadEventNames.UPLOAD_COMPLETED, { uploadId, session, postId });

            this.cleanupUpload(uploadId);
        } catch (error) {
            this.failUpload(uploadId, error);
        }
    }

    failUpload(uploadId, error) {
        const session = this.uploads.get(uploadId);
        if (!session) return;

        this.transitionState(uploadId, UploadState.FAILED, { error: error.message });
        uploadQueue.uploadFailed(uploadId, error);

        uploadEvents.emit(UploadEventNames.UPLOAD_FAILED, {
            uploadId,
            session,
            error: error.message,
            canRetry: session.canRetry(),
        });
        uploadEvents.emit(UploadEventNames.ERROR_OCCURRED, {
            uploadId,
            error: error.message,
        });
    }

    /**
     * Wait for the server to finish processing a post.
     *
     * For video posts we listen to the feed WebSocket for ``video_progress``
     * messages emitted by the Celery HLS transcoding task.  For image / text
     * posts (or when no WebSocket is available) we fall back to a fast
     * two-step synthetic update so the banner disappears promptly.
     *
     * @param {string} uploadId
     * @param {number|string|null} postId   – returned by the API (null for non-video)
     * @param {boolean} hasVideo
     * @returns {Promise<void>}
     */
    async waitForServerProcessing(uploadId, postId, hasVideo) {
        const tracker = progressManager.getTracker(uploadId);
        if (!tracker) return;

        // ----------------------------------------------------------------
        // Non-video posts: quick synthetic update, done immediately.
        // ----------------------------------------------------------------
        if (!hasVideo || !postId) {
            tracker.updateServerProcessingProgress(50, 100, 'Saving to database…');
            await new Promise((r) => setTimeout(r, 400));
            tracker.updateServerProcessingProgress(100, 100, 'Published!');
            return;
        }

        // ----------------------------------------------------------------
        // Video posts: subscribe to live Celery progress via feed WS.
        // ----------------------------------------------------------------
        const TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes hard cap

        return new Promise((resolve) => {
            let resolved = false;
            const finish = () => {
                if (resolved) return;
                resolved = true;
                window.removeEventListener('feedVideoProgress', onProgress);
                resolve();
            };

            const timeoutHandle = setTimeout(() => {
                tracker.updateServerProcessingProgress(100, 100, 'Processing…');
                finish();
            }, TIMEOUT_MS);

            const onProgress = (evt) => {
                const { post_id, status, progress, message } = evt.detail;
                // Only handle messages for this specific post
                if (String(post_id) !== String(postId)) return;

                tracker.updateServerProcessingProgress(
                    progress ?? 0,
                    100,
                    message || 'Processing video…'
                );

                if (status === 'ready' || status === 'failed') {
                    clearTimeout(timeoutHandle);
                    finish();
                }
            };

            // feedVideoProgress is dispatched by base.html's feed WS handler
            window.addEventListener('feedVideoProgress', onProgress);

            // Seed the UI immediately so the banner doesn't sit blank
            tracker.updateServerProcessingProgress(5, 100, 'Video received — starting transcoding…');
        });
    }

    /** @deprecated  Replaced by waitForServerProcessing — kept for safety. */
    async simulateServerProcessing(uploadId) {
        await this.waitForServerProcessing(uploadId, null, false);
    }


    cancelUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        const stateMachine = stateMachineFactory.peekMachine(uploadId);
        if (!session || !stateMachine || !stateMachine.canCancel()) {
            return false;
        }

        session.cancel();
        this.transitionState(uploadId, UploadState.CANCELLED);
        uploadQueue.cancel(uploadId);

        uploadEvents.emit(UploadEventNames.UPLOAD_CANCELLED, { uploadId, session });
        this.cleanupUpload(uploadId);
        return true;
    }

    retryUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        if (!session || !session.canRetry()) {
            return false;
        }

        session.incrementRetry();
        uploadQueue.retry(uploadId);

        uploadEvents.emit(UploadEventNames.UPLOAD_RETRIED, {
            uploadId,
            session,
            retryCount: session.retryCount,
        });

        this.transitionState(uploadId, UploadState.QUEUED);
        this.waitForQueueTurn(uploadId);
        return true;
    }

    cleanupUpload(uploadId) {
        const session = this.uploads.get(uploadId);
        previewManager.revokePreviews(uploadId);

        if (session) {
            session.cleanup();
        }

        progressManager.removeTracker(uploadId);
        stateMachineFactory.removeMachine(uploadId);

        setTimeout(() => {
            this.uploads.delete(uploadId);
        }, 5000);
    }

    async createDraftPreviews(draftId, files) {
        previewManager.revokePreviews(draftId);
        return previewManager.generatePreviews(files, draftId);
    }

    clearDraftPreviews(draftId) {
        previewManager.revokePreviews(draftId);
    }

    getUpload(uploadId) {
        return this.uploads.get(uploadId);
    }

    getAllUploads() {
        return Array.from(this.uploads.values());
    }

    getActiveUpload() {
        return this.getAllUploads().find((session) => {
            return ![UploadState.PUBLISHED, UploadState.FAILED, UploadState.CANCELLED].includes(session.state);
        }) || null;
    }

    getUploadState(uploadId) {
        const stateMachine = stateMachineFactory.peekMachine(uploadId);
        return stateMachine ? stateMachine.getState() : undefined;
    }

    getUploadProgress(uploadId) {
        const tracker = progressManager.getTracker(uploadId);
        return tracker ? tracker.getSummary() : undefined;
    }

    getOverallProgress() {
        return progressManager.getOverallProgress();
    }

    getQueueStatistics() {
        return uploadQueue.getStatistics();
    }
}

export const uploadManager = new UploadManager();

export default UploadManager;
