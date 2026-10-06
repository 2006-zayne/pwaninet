/**
 * CroppingEngine - Interactive image cropping engine with real-time preview,
 * multi-touch drag handles, rule-of-thirds grid, aspect ratio snapping,
 * and lossless canvas commit & full undo / reset capabilities.
 */

export class CroppingEngine {
    constructor(composer) {
        this.composer = composer;
        this.isActive = false;
        this.activeItem = null;

        // Normalized crop rectangle: { x: 0..1, y: 0..1, width: 0..1, height: 0..1 }
        this.cropRect = { x: 0.05, y: 0.05, width: 0.9, height: 0.9 };
        this.currentAspect = 'free'; // 'free', '1:1', '4:5', '16:9'

        // DOM elements
        this.overlay = null;
        this.cropBox = null;
        this.masks = {};
        this.dock = null;
        this.applyBtn = null;
        this.cancelBtn = null;
        this.resetBtn = null;
        this.aspectPills = [];

        // Drag tracking
        this.isDragging = false;
        this.dragType = null; // 'move', 'nw', 'ne', 'se', 'sw', 'n', 's', 'e', 'w'
        this.dragStart = { x: 0, y: 0 };
        this.initialCropRect = null;
        this.imageBounds = null;

        this._boundOnPointerMove = this._onPointerMove.bind(this);
        this._boundOnPointerUp = this._onPointerUp.bind(this);
    }

    init() {
        this.dock = document.getElementById('mediaCropActionsDock');
        this.applyBtn = document.getElementById('mediaCropApplyBtn');
        this.cancelBtn = document.getElementById('mediaCropCancelBtn');
        this.resetBtn = document.getElementById('mediaResetBtn');

        if (this.dock) {
            this.aspectPills = this.dock.querySelectorAll('.crop-aspect-pill');
            this.aspectPills.forEach(pill => {
                pill.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const aspect = pill.dataset.aspect || 'free';
                    this.setAspectRatio(aspect);
                });
            });
        }

        if (this.applyBtn) {
            this.applyBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.applyCrop();
            });
        }

        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.closeCrop();
            });
        }

        if (this.resetBtn) {
            this.resetBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.resetAllEdits();
            });
        }

        // Global resize listener to recompute crop box positioning if viewport changes
        window.addEventListener('resize', () => {
            if (this.isActive) {
                this._updateOverlayGeometry();
            }
        });
    }

    /**
     * Open interactive cropping mode for an image item
     */
    openCrop(item) {
        if (!item || item.type !== 'image') return;

        this.activeItem = item;
        this.isActive = true;
        this.currentAspect = item.cropAspect || 'free';

        // Prepare or restore normalized crop rectangle
        if (item.cropRect) {
            this.cropRect = { ...item.cropRect };
        } else {
            this.cropRect = { x: 0.05, y: 0.05, width: 0.9, height: 0.9 };
            if (this.currentAspect !== 'free') {
                this._fitAspectToRect(this.currentAspect);
            }
        }

        this._ensureOverlayElements();
        this._updateOverlayGeometry();
        this._updateAspectPillsUI(this.currentAspect);

        if (this.dock) {
            this.dock.classList.remove('d-none');
        }

        if (this.composer?.overlay) {
            this.composer.overlay.classList.add('is-cropping');
        }

        if (this.composer?.cropBtn) {
            this.composer.cropBtn.classList.add('active');
        }
    }

    /**
     * Close cropping mode without applying
     */
    closeCrop() {
        this.isActive = false;
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
            this.cropBox = null;
        }

        if (this.dock) {
            this.dock.classList.add('d-none');
        }

        if (this.composer?.overlay) {
            this.composer.overlay.classList.remove('is-cropping');
        }

        if (this.composer?.cropBtn) {
            this.composer.cropBtn.classList.remove('active');
        }
        if (this.composer?.cropDropdown) {
            this.composer.cropDropdown.classList.add('d-none');
        }
    }

    /**
     * Change aspect ratio and re-center crop box
     */
    setAspectRatio(aspect) {
        this.currentAspect = aspect;
        if (this.activeItem) {
            this.activeItem.cropAspect = aspect;
        }
        this._updateAspectPillsUI(aspect);
        if (this.composer?._updateCropDropdownUI) {
            this.composer._updateCropDropdownUI(aspect);
        }

        this._fitAspectToRect(aspect);
        this._renderCropBox();
    }

    /**
     * Fit crop rectangle to the specified aspect ratio
     */
    _fitAspectToRect(aspect) {
        if (aspect === 'free' || !this.imageBounds) {
            return;
        }

        let targetRatio = 1;
        if (aspect === '1:1') targetRatio = 1;
        else if (aspect === '4:5') targetRatio = 4 / 5;
        else if (aspect === '16:9') targetRatio = 16 / 9;

        const imgWidth = this.imageBounds.width || 1;
        const imgHeight = this.imageBounds.height || 1;
        const imgAspect = imgWidth / imgHeight;

        // Desired ratio in normalized coordinates: normW / normH = targetRatio / imgAspect
        const normRatio = targetRatio / imgAspect;

        let w = 0.85;
        let h = w / normRatio;

        if (h > 0.85) {
            h = 0.85;
            w = h * normRatio;
        }

        w = Math.max(0.15, Math.min(0.95, w));
        h = Math.max(0.15, Math.min(0.95, h));

        const x = (1 - w) / 2;
        const y = (1 - h) / 2;

        this.cropRect = { x, y, width: w, height: h };
    }

    /**
     * Apply crop: renders slice onto offscreen canvas, produces new File & preview Blob
     */
    async applyCrop() {
        const item = this.activeItem;
        if (!item || item.type !== 'image') {
            this.closeCrop();
            return;
        }

        try {
            // Load source image
            const sourceUrl = item.originalPreviewUrl || item.previewUrl;
            const img = new Image();
            img.crossOrigin = 'anonymous';

            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = sourceUrl;
            });

            const natW = img.naturalWidth;
            const natH = img.naturalHeight;

            const sx = Math.max(0, Math.floor(this.cropRect.x * natW));
            const sy = Math.max(0, Math.floor(this.cropRect.y * natH));
            const sw = Math.min(natW - sx, Math.ceil(this.cropRect.width * natW));
            const sh = Math.min(natH - sy, Math.ceil(this.cropRect.height * natH));

            if (sw <= 10 || sh <= 10) {
                this.closeCrop();
                return;
            }

            const canvas = document.createElement('canvas');
            canvas.width = sw;
            canvas.height = sh;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);

            const mime = item.file?.type || 'image/jpeg';
            const blob = await new Promise(resolve => canvas.toBlob(resolve, mime, 0.95));

            if (!blob) {
                this.closeCrop();
                return;
            }

            const croppedFile = new File([blob], item.file?.name || 'cropped_image.jpg', { type: mime });

            // Preserve original file & url for pristine undo/reset
            if (!item.originalFile) item.originalFile = item.file;
            if (!item.originalPreviewUrl) item.originalPreviewUrl = item.previewUrl;

            item.file = croppedFile;
            item.previewUrl = URL.createObjectURL(blob);
            item.width = sw;
            item.height = sh;
            item.size = blob.size;
            item.cropRect = { ...this.cropRect };
            item.cropAspect = this.currentAspect;
            item.isEdited = true;

            // Update previews immediately
            if (this.composer?.previewCanvas) {
                this.composer.previewCanvas.render(item);
            }
            if (this.composer?.thumbnailStrip) {
                this.composer.thumbnailStrip.render(this.composer.mediaItems);
            }
            if (this.composer?.updateEditsState) {
                this.composer.updateEditsState();
            }

            this.closeCrop();
        } catch (err) {
            console.error('[CROPPING_ENGINE] Error applying crop:', err);
            this.closeCrop();
        }
    }

    /**
     * Undo & clean all edits for active item
     */
    resetAllEdits(targetItem = null) {
        const item = targetItem || this.composer?.mediaItems[this.composer?.activeMediaIndex];
        if (!item) return;

        // Restore pristine file & previewUrl
        if (item.originalFile) {
            if (item.previewUrl && item.previewUrl !== item.originalPreviewUrl) {
                URL.revokeObjectURL(item.previewUrl);
            }
            item.file = item.originalFile;
            item.previewUrl = item.originalPreviewUrl;
            delete item.originalFile;
            delete item.originalPreviewUrl;
        }

        item.rotation = 0;
        item.cropRect = null;
        item.cropAspect = 'free';
        item.isEdited = false;

        if (item.type === 'video') {
            item.trimStart = 0;
            item.trimEnd = item.duration;
            if (this.composer?._getGlobalMuteState) {
                item.isMuted = this.composer._getGlobalMuteState();
            }
            if (this.composer?._updateTrimmerUI) {
                this.composer._updateTrimmerUI(item);
            }
            if (this.composer?._updateMuteUI) {
                this.composer._updateMuteUI(item);
            }
        }

        this.closeCrop();

        if (this.composer?.previewCanvas) {
            this.composer.previewCanvas.render(item);
        }
        if (this.composer?.thumbnailStrip) {
            this.composer.thumbnailStrip.render(this.composer.mediaItems);
        }
        if (this.composer?.updateEditsState) {
            this.composer.updateEditsState();
        }
    }

    // =========================================================================
    // OVERLAY & INTERACTIVE HANDLES
    // =========================================================================

    _ensureOverlayElements() {
        if (this.overlay) this.overlay.remove();

        const previewContainer = this.composer?.previewCanvas?.container;
        if (!previewContainer) return;

        const overlay = document.createElement('div');
        overlay.className = 'media-crop-overlay';

        // 4 Backdrop masks
        const maskTop = document.createElement('div');
        maskTop.className = 'crop-backdrop-mask mask-top';
        const maskBottom = document.createElement('div');
        maskBottom.className = 'crop-backdrop-mask mask-bottom';
        const maskLeft = document.createElement('div');
        maskLeft.className = 'crop-backdrop-mask mask-left';
        const maskRight = document.createElement('div');
        maskRight.className = 'crop-backdrop-mask mask-right';

        overlay.appendChild(maskTop);
        overlay.appendChild(maskBottom);
        overlay.appendChild(maskLeft);
        overlay.appendChild(maskRight);

        // Crop bounding box
        const cropBox = document.createElement('div');
        cropBox.className = 'media-crop-box';

        // Rule-of-thirds grid
        cropBox.innerHTML = `
            <div class="crop-grid-line grid-h1"></div>
            <div class="crop-grid-line grid-h2"></div>
            <div class="crop-grid-line grid-v1"></div>
            <div class="crop-grid-line grid-v2"></div>
            <div class="crop-handle handle-nw" data-handle="nw"></div>
            <div class="crop-handle handle-ne" data-handle="ne"></div>
            <div class="crop-handle handle-se" data-handle="se"></div>
            <div class="crop-handle handle-sw" data-handle="sw"></div>
            <div class="crop-handle handle-n" data-handle="n"></div>
            <div class="crop-handle handle-s" data-handle="s"></div>
            <div class="crop-handle handle-w" data-handle="w"></div>
            <div class="crop-handle handle-e" data-handle="e"></div>
        `;

        overlay.appendChild(cropBox);
        previewContainer.appendChild(overlay);

        this.overlay = overlay;
        this.cropBox = cropBox;
        this.masks = { top: maskTop, bottom: maskBottom, left: maskLeft, right: maskRight };

        this._setupDragListeners();
    }

    _updateOverlayGeometry() {
        const previewContainer = this.composer?.previewCanvas?.container;
        const img = previewContainer?.querySelector('.media-preview-image');
        if (!img || !this.overlay) return;

        const containerRect = previewContainer.getBoundingClientRect();
        const imgRect = img.getBoundingClientRect();

        // Exact positioning directly over the visible rendered image
        const left = imgRect.left - containerRect.left;
        const top = imgRect.top - containerRect.top;
        const width = imgRect.width;
        const height = imgRect.height;

        this.overlay.style.position = 'absolute';
        this.overlay.style.left = `${left}px`;
        this.overlay.style.top = `${top}px`;
        this.overlay.style.width = `${width}px`;
        this.overlay.style.height = `${height}px`;

        this.imageBounds = { left, top, width, height };

        this._renderCropBox();
    }

    _renderCropBox() {
        if (!this.cropBox || !this.masks.top) return;

        const { x, y, width, height } = this.cropRect;

        const leftPct = x * 100;
        const topPct = y * 100;
        const widthPct = width * 100;
        const heightPct = height * 100;

        this.cropBox.style.left = `${leftPct}%`;
        this.cropBox.style.top = `${topPct}%`;
        this.cropBox.style.width = `${widthPct}%`;
        this.cropBox.style.height = `${heightPct}%`;

        // Update 4 surrounding dark masks
        this.masks.top.style.top = '0';
        this.masks.top.style.left = '0';
        this.masks.top.style.right = '0';
        this.masks.top.style.height = `${topPct}%`;

        this.masks.bottom.style.top = `${topPct + heightPct}%`;
        this.masks.bottom.style.left = '0';
        this.masks.bottom.style.right = '0';
        this.masks.bottom.style.bottom = '0';

        this.masks.left.style.top = `${topPct}%`;
        this.masks.left.style.height = `${heightPct}%`;
        this.masks.left.style.left = '0';
        this.masks.left.style.width = `${leftPct}%`;

        this.masks.right.style.top = `${topPct}%`;
        this.masks.right.style.height = `${heightPct}%`;
        this.masks.right.style.left = `${leftPct + widthPct}%`;
        this.masks.right.style.right = '0';
    }

    _setupDragListeners() {
        if (!this.cropBox) return;

        this.cropBox.addEventListener('pointerdown', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const handle = e.target.closest('.crop-handle');
            this.dragType = handle ? handle.dataset.handle : 'move';
            this.isDragging = true;
            this.dragStart = { x: e.clientX, y: e.clientY };
            this.initialCropRect = { ...this.cropRect };

            window.addEventListener('pointermove', this._boundOnPointerMove);
            window.addEventListener('pointerup', this._boundOnPointerUp);
            window.addEventListener('pointercancel', this._boundOnPointerUp);
        });
    }

    _onPointerMove(e) {
        if (!this.isDragging || !this.imageBounds || !this.initialCropRect) return;

        const dx = (e.clientX - this.dragStart.x) / this.imageBounds.width;
        const dy = (e.clientY - this.dragStart.y) / this.imageBounds.height;

        const init = this.initialCropRect;
        const minSize = 0.12;

        if (this.dragType === 'move') {
            const newX = Math.max(0, Math.min(1 - init.width, init.x + dx));
            const newY = Math.max(0, Math.min(1 - init.height, init.y + dy));
            this.cropRect.x = newX;
            this.cropRect.y = newY;
        } else {
            // Resize with handles
            let { x, y, width, height } = { ...init };

            if (this.dragType.includes('e')) {
                width = Math.max(minSize, Math.min(1 - x, init.width + dx));
            }
            if (this.dragType.includes('s')) {
                height = Math.max(minSize, Math.min(1 - y, init.height + dy));
            }
            if (this.dragType.includes('w')) {
                const maxDx = init.width - minSize;
                const clampedDx = Math.max(-init.x, Math.min(maxDx, dx));
                x = init.x + clampedDx;
                width = init.width - clampedDx;
            }
            if (this.dragType.includes('n')) {
                const maxDy = init.height - minSize;
                const clampedDy = Math.max(-init.y, Math.min(maxDy, dy));
                y = init.y + clampedDy;
                height = init.height - clampedDy;
            }

            // Aspect ratio constraint if not free
            if (this.currentAspect !== 'free') {
                let targetRatio = 1;
                if (this.currentAspect === '1:1') targetRatio = 1;
                else if (this.currentAspect === '4:5') targetRatio = 4 / 5;
                else if (this.currentAspect === '16:9') targetRatio = 16 / 9;

                const imgAspect = (this.imageBounds.width || 1) / (this.imageBounds.height || 1);
                const normRatio = targetRatio / imgAspect;

                // Adjust height to match normalized aspect
                if (this.dragType.includes('e') || this.dragType.includes('w')) {
                    height = Math.max(minSize, Math.min(1 - y, width / normRatio));
                } else {
                    width = Math.max(minSize, Math.min(1 - x, height * normRatio));
                }
            }

            this.cropRect = { x, y, width, height };
        }

        this._renderCropBox();
    }

    _onPointerUp() {
        this.isDragging = false;
        this.dragType = null;
        window.removeEventListener('pointermove', this._boundOnPointerMove);
        window.removeEventListener('pointerup', this._boundOnPointerUp);
        window.removeEventListener('pointercancel', this._boundOnPointerUp);
    }

    _updateAspectPillsUI(aspect) {
        if (!this.aspectPills) return;
        this.aspectPills.forEach(pill => {
            const isMatch = pill.dataset.aspect === aspect;
            pill.classList.toggle('active', isMatch);
        });
    }
}
