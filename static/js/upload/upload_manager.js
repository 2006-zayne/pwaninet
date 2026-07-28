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

            this.transitionState(uploadId, UploadState.SERVER_PROCESSING);
            tracker.updateServerProcessingProgress(1, 3, 'Processing media...');
            await this.simulateServerProcessing(uploadId);
            tracker.completeServerProcessing();

            this.transitionState(uploadId, UploadState.PUBLISHED);
            tracker.updatePublicationProgress(100);
            tracker.completePublication();

            uploadQueue.uploadCompleted(uploadId);
            uploadEvents.emit(UploadEventNames.UPLOAD_COMPLETED, { uploadId, session });
            uploadEvents.emit(UploadEventNames.UPLOAD_PUBLISHED, { uploadId, session, postId: response?.id });

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

    async simulateServerProcessing(uploadId) {
        const tracker = progressManager.getTracker(uploadId);

        await new Promise((resolve) => setTimeout(resolve, 500));
        tracker.updateServerProcessingProgress(2, 3, 'Saving to database...');

        await new Promise((resolve) => setTimeout(resolve, 500));
        tracker.updateServerProcessingProgress(3, 3, 'Finalizing...');
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
