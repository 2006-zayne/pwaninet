/**
 * Document Viewer System
 * Modular architecture for rendering multiple document types in the browser
 */

class DocumentViewer {
    constructor(container, fileUrl, fileType, fileName, documentId, fileId) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.fileType = fileType.toLowerCase();
        this.fileName = fileName;
        this.documentId = documentId;
        this.fileId = fileId;
        this.currentPage = 1;
        this.totalPages = null;
        this.viewer = null;
        this.toolbar = null;
        this.isLoading = false;
        this.isFullscreen = false;
        
        // Touch gesture support
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.minSwipeDistance = 50;
        
        // Pinch-to-zoom support
        this.initialPinchDistance = 0;
        this.currentScale = 1.0;
        this.isPinching = false;
        this.pinchCenterX = 0;
        this.pinchCenterY = 0;
        this.translateX = 0;
        this.translateY = 0;
        this.lastTranslateX = 0;
        this.lastTranslateY = 0;
        this.lastTouchX = 0;
        this.lastTouchY = 0;
    }

    async initialize() {
        this.showLoading();
        
        try {
            this.viewer = ViewerFactory.createViewer(this.fileType, this.container, this.fileUrl);
            await this.viewer.load();
            
            this.totalPages = this.viewer.getTotalPages();
            this.createToolbar();
            this.hideLoading();
            
            if (this.totalPages && this.totalPages > 1) {
                this.updatePageIndicator();
            }
            
            // Add touch gesture support
            this.addTouchGestures();
        } catch (error) {
            this.showError(error.message);
        }
    }

    showLoading() {
        this.container.innerHTML = `
            <div class="viewer-loading" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; gap: 16px;">
                <div class="spinner" style="width: 48px; height: 48px; border: 4px solid var(--border); border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite;"></div>
                <p style="color: var(--text-secondary); font-size: 1rem;">Loading document...</p>
            </div>
            <style>
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            </style>
        `;
    }

    hideLoading() {
        const loading = this.container.querySelector('.viewer-loading');
        if (loading) loading.remove();
    }

    showError(message) {
        this.container.innerHTML = `
            <div class="viewer-error" style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 600px; gap: 16px; text-align: center; padding: 32px;">
                <i class="bi bi-exclamation-triangle" style="font-size: 4rem; color: var(--error);"></i>
                <h3 style="font-size: 1.25rem; font-weight: 600; color: var(--text-dark); margin: 0;">Preview Unavailable</h3>
                <p style="color: var(--text-secondary); font-size: 1rem; max-width: 400px;">${message || 'Unable to load document preview. Please try downloading the file instead.'}</p>
                <a href="${this.fileUrl}" download="${this.fileName}" class="btn btn-primary" style="margin-top: 16px;">
                    <i class="bi bi-download" style="margin-right: 8px;"></i>Download File
                </a>
            </div>
        `;
    }

    createToolbar() {
        // Always create toolbar for all viewers
        this.toolbar = document.createElement('div');
        this.toolbar.className = 'viewer-toolbar';
        this.toolbar.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-bottom: none;
            border-radius: 12px 12px 0 0;
            flex-wrap: wrap;
            gap: 8px;
        `;

        const leftControls = document.createElement('div');
        leftControls.style.cssText = 'display: flex; align-items: center; gap: 8px; flex-wrap: wrap;';

        // Add page navigation only if viewer supports it
        if (this.viewer.needsPageNavigation()) {
            const prevButton = this.createButton('bi-chevron-left', 'Previous Page', () => this.previousPage());
            const nextButton = this.createButton('bi-chevron-right', 'Next Page', () => this.nextPage());
            
            prevButton.id = 'viewer-prev-btn';
            nextButton.id = 'viewer-next-btn';

            const pageIndicator = document.createElement('div');
            pageIndicator.className = 'viewer-page-indicator';
            pageIndicator.style.cssText = `
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9rem;
                color: var(--text-secondary);
                white-space: nowrap;
            `;
            pageIndicator.innerHTML = `
                <span id="viewer-current-page">${this.currentPage}</span>
                <span>of</span>
                <span id="viewer-total-pages">${this.totalPages || '?'}</span>
            `;

            leftControls.appendChild(prevButton);
            leftControls.appendChild(pageIndicator);
            leftControls.appendChild(nextButton);
        } else {
            // Show document type indicator instead
            const docTypeIndicator = document.createElement('div');
            docTypeIndicator.style.cssText = `
                font-size: 0.9rem;
                color: var(--text-secondary);
                font-weight: 500;
                white-space: nowrap;
            `;
            docTypeIndicator.textContent = this.fileType.toUpperCase() + ' Document';
            leftControls.appendChild(docTypeIndicator);
        }

        const rightControls = document.createElement('div');
        rightControls.style.cssText = 'display: flex; align-items: center; gap: 8px; flex-wrap: wrap;';

        // Add zoom controls only if viewer supports them
        if (this.viewer.needsZoom()) {
            const zoomOutButton = this.createButton('bi-dash', 'Zoom Out', async () => await this.viewer.zoomOut());
            const zoomInButton = this.createButton('bi-plus', 'Zoom In', async () => await this.viewer.zoomIn());
            
            const zoomIndicator = document.createElement('div');
            zoomIndicator.id = 'viewer-zoom-indicator';
            zoomIndicator.style.cssText = `
                font-size: 0.9rem;
                color: var(--text-secondary);
                font-weight: 500;
                min-width: 50px;
                text-align: center;
                white-space: nowrap;
            `;
            zoomIndicator.textContent = '100%';
            
            rightControls.appendChild(zoomOutButton);
            rightControls.appendChild(zoomIndicator);
            rightControls.appendChild(zoomInButton);
        }

        // Add scroll controls if viewer supports scrolling
        if (this.viewer.needsScroll()) {
            const scrollUpButton = this.createButton('bi-arrow-up', 'Scroll Up', () => this.viewer.scrollUp());
            const scrollDownButton = this.createButton('bi-arrow-down', 'Scroll Down', () => this.viewer.scrollDown());
            rightControls.appendChild(scrollUpButton);
            rightControls.appendChild(scrollDownButton);
        }

        const fullscreenButton = this.createButton('bi-arrows-fullscreen', 'Fullscreen', () => this.toggleFullscreen());
        const downloadButton = this.createButton('bi-download', 'Download', () => {
            this.trackAndDownload();
        });

        rightControls.appendChild(fullscreenButton);
        rightControls.appendChild(downloadButton);

        this.toolbar.appendChild(leftControls);
        this.toolbar.appendChild(rightControls);

        this.container.insertBefore(this.toolbar, this.container.firstChild);
        this.updateNavigationButtons();
    }

    createButton(icon, title, onClick) {
        const button = document.createElement('button');
        button.className = 'viewer-btn';
        button.title = title;
        button.style.cssText = `
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--card-bg);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
        `;
        button.innerHTML = `<i class="bi ${icon}" style="font-size: 1.1rem;"></i>`;
        button.onclick = onClick;
        
        button.onmouseenter = () => {
            button.style.borderColor = 'var(--primary)';
            button.style.color = 'var(--primary)';
        };
        button.onmouseleave = () => {
            button.style.borderColor = 'var(--border)';
            button.style.color = 'var(--text-secondary)';
        };

        return button;
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('viewer-prev-btn');
        const nextBtn = document.getElementById('viewer-next-btn');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
            prevBtn.style.opacity = this.currentPage <= 1 ? '0.5' : '1';
            prevBtn.style.cursor = this.currentPage <= 1 ? 'not-allowed' : 'pointer';
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.totalPages && this.currentPage >= this.totalPages;
            nextBtn.style.opacity = this.totalPages && this.currentPage >= this.totalPages ? '0.5' : '1';
            nextBtn.style.cursor = this.totalPages && this.currentPage >= this.totalPages ? 'not-allowed' : 'pointer';
        }
    }

    updatePageIndicator() {
        const currentPageEl = document.getElementById('viewer-current-page');
        const totalPagesEl = document.getElementById('viewer-total-pages');
        
        if (currentPageEl) currentPageEl.textContent = this.currentPage;
        if (totalPagesEl) totalPagesEl.textContent = this.totalPages || '?';
    }

    async nextPage() {
        if (this.totalPages && this.currentPage >= this.totalPages) return;
        
        this.currentPage++;
        await this.viewer.goToPage(this.currentPage);
        this.updatePageIndicator();
        this.updateNavigationButtons();
    }

    async previousPage() {
        if (this.currentPage <= 1) return;
        
        this.currentPage--;
        await this.viewer.goToPage(this.currentPage);
        this.updatePageIndicator();
        this.updateNavigationButtons();
    }

    toggleFullscreen() {
        this.isFullscreen = !this.isFullscreen;
        
        if (this.isFullscreen) {
            this.enterFullscreen();
        } else {
            this.exitFullscreen();
        }
    }

    enterFullscreen() {
        // Store current page state
        this.savedPage = this.currentPage;
        
        // Make container fullscreen
        this.container.requestFullscreen = this.container.requestFullscreen || 
                                          this.container.webkitRequestFullscreen || 
                                          this.container.msRequestFullscreen;
        
        if (this.container.requestFullscreen) {
            this.container.requestFullscreen();
        }
        
        // Add fullscreen styles
        this.container.style.position = 'fixed';
        this.container.style.top = '0';
        this.container.style.left = '0';
        this.container.style.width = '100vw';
        this.container.style.height = '100vh';
        this.container.style.zIndex = '9999';
        this.container.style.borderRadius = '0';
        
        // Update viewer container height
        const viewerContainer = this.container.querySelector('.pdf-viewer-container, .docx-viewer-container, .text-viewer-container, .image-viewer-container, .pptx-viewer-container, .unsupported-viewer-container');
        if (viewerContainer) {
            viewerContainer.style.height = 'calc(100vh - 60px)';
            
            // Remove width constraints in fullscreen mode
            const content = viewerContainer.querySelector('img, canvas, .pdf-viewer-container > div, .docx-viewer-container > div, .text-viewer-container > div');
            if (content) {
                content.style.maxWidth = 'none';
                content.style.maxHeight = 'none';
            }
        }
        
        // Update fullscreen button icon
        const fullscreenBtn = this.toolbar.querySelector('[title="Fullscreen"]');
        if (fullscreenBtn) {
            fullscreenBtn.innerHTML = '<i class="bi bi-arrows-angle-contract" style="font-size: 1.1rem;"></i>';
            fullscreenBtn.title = 'Exit Fullscreen';
        }
        
        // Listen for fullscreen exit
        this.fullscreenChangeHandler = () => {
            if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement) {
                this.isFullscreen = false;
                this.exitFullscreen();
            }
        };
        document.addEventListener('fullscreenchange', this.fullscreenChangeHandler);
        document.addEventListener('webkitfullscreenchange', this.fullscreenChangeHandler);
        document.addEventListener('msfullscreenchange', this.fullscreenChangeHandler);
    }

    exitFullscreen() {
        // Exit fullscreen mode
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        
        // Remove fullscreen styles
        this.container.style.position = '';
        this.container.style.top = '';
        this.container.style.left = '';
        this.container.style.width = '';
        this.container.style.height = '';
        this.container.style.zIndex = '';
        this.container.style.borderRadius = '';
        
        // Reset viewer container height
        const viewerContainer = this.container.querySelector('.pdf-viewer-container, .docx-viewer-container, .text-viewer-container, .image-viewer-container, .pptx-viewer-container, .unsupported-viewer-container');
        if (viewerContainer) {
            viewerContainer.style.height = '600px';
            
            // Restore width constraints when exiting fullscreen
            const content = viewerContainer.querySelector('img, canvas, .pdf-viewer-container > div, .docx-viewer-container > div, .text-viewer-container > div');
            if (content) {
                if (content.tagName === 'IMG') {
                    content.style.maxWidth = '100%';
                    content.style.maxHeight = '100%';
                } else if (content.tagName === 'CANVAS') {
                    content.style.maxWidth = '100%';
                    content.style.maxHeight = '100%';
                } else {
                    content.style.maxWidth = '90%';
                }
            }
        }
        
        // Update fullscreen button icon
        const fullscreenBtn = this.toolbar.querySelector('[title="Exit Fullscreen"]');
        if (fullscreenBtn) {
            fullscreenBtn.innerHTML = '<i class="bi bi-arrows-fullscreen" style="font-size: 1.1rem;"></i>';
            fullscreenBtn.title = 'Fullscreen';
        }
        
        // Remove event listeners
        document.removeEventListener('fullscreenchange', this.fullscreenChangeHandler);
        document.removeEventListener('webkitfullscreenchange', this.fullscreenChangeHandler);
        document.removeEventListener('msfullscreenchange', this.fullscreenChangeHandler);
    }

    addTouchGestures() {
        // Touch start
        this.container.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                // Pinch start
                this.isPinching = true;
                this.initialPinchDistance = this.getPinchDistance(e.touches);
                this.pinchCenterX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
                this.pinchCenterY = (e.touches[0].clientY + e.touches[1].clientY) / 2;
                this.lastTranslateX = this.translateX;
                this.lastTranslateY = this.translateY;
            } else if (e.touches.length === 1) {
                // Single touch - for swipe and pan
                this.touchStartX = e.touches[0].clientX;
                this.touchStartY = e.touches[0].clientY;
                this.lastTouchX = e.touches[0].clientX;
                this.lastTouchY = e.touches[0].clientY;
            }
        }, { passive: true });

        // Touch move
        this.container.addEventListener('touchmove', (e) => {
            if (this.isPinching && e.touches.length === 2) {
                // Pinch zoom
                e.preventDefault();
                const currentDistance = this.getPinchDistance(e.touches);
                const scale = currentDistance / this.initialPinchDistance;
                this.currentScale = Math.min(Math.max(scale, 0.5), 3.0);
                this.applyTransform();
            } else if (e.touches.length === 1 && this.currentScale > 1) {
                // Pan when zoomed
                e.preventDefault();
                const touch = e.touches[0];
                const deltaX = touch.clientX - this.lastTouchX;
                const deltaY = touch.clientY - this.lastTouchY;
                this.translateX += deltaX;
                this.translateY += deltaY;
                this.lastTouchX = touch.clientX;
                this.lastTouchY = touch.clientY;
                this.applyTransform();
            }
        }, { passive: false });

        // Touch end
        this.container.addEventListener('touchend', (e) => {
            if (e.touches.length === 0) {
                if (this.isPinching) {
                    this.isPinching = false;
                    this.lastTranslateX = this.translateX;
                    this.lastTranslateY = this.translateY;
                } else {
                    // Handle swipe
                    this.touchEndX = e.changedTouches[0].clientX;
                    this.touchEndY = e.changedTouches[0].clientY;
                    this.handleSwipe();
                }
            }
        }, { passive: true });
    }

    getPinchDistance(touches) {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    applyTransform() {
        const viewerContainer = this.container.querySelector('.image-viewer-container, .pdf-viewer-container, .docx-viewer-container, .text-viewer-container');
        if (viewerContainer) {
            const content = viewerContainer.querySelector('img, canvas, .pdf-viewer-container > div, .docx-viewer-container > div, .text-viewer-container > div');
            if (content) {
                // Use pinch center as transform origin during zoom for better UX
                const originX = this.isPinching ? `${this.pinchCenterX}px` : 'center';
                const originY = this.isPinching ? `${this.pinchCenterY}px` : 'center';
                
                content.style.transform = `translate(${this.translateX}px, ${this.translateY}px) scale(${this.currentScale})`;
                content.style.transformOrigin = `${originX} ${originY}`;
                content.style.transition = this.isPinching ? 'none' : 'transform 0.1s ease-out';
                
                // Remove max-width constraint when zoomed to allow proper scaling
                if (this.currentScale > 1) {
                    content.style.maxWidth = 'none';
                    content.style.maxHeight = 'none';
                } else {
                    // Reset transform when zoomed out
                    this.translateX = 0;
                    this.translateY = 0;
                    // Restore original constraints when zoomed out
                    if (content.tagName === 'IMG') {
                        content.style.maxWidth = '100%';
                        content.style.maxHeight = '100%';
                    }
                }
            }
        }
    }

    handleSwipe() {
        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;
        
        // Only handle swipe if not zoomed in (when zoomed, it's panning)
        if (this.currentScale <= 1) {
            // Check if horizontal swipe (more horizontal than vertical)
            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                // Horizontal swipe
                if (Math.abs(deltaX) > this.minSwipeDistance) {
                    if (deltaX > 0) {
                        // Swipe right - previous page
                        if (this.viewer.needsPageNavigation()) {
                            this.previousPage();
                        }
                    } else {
                        // Swipe left - next page
                        if (this.viewer.needsPageNavigation()) {
                            this.nextPage();
                        }
                    }
                }
            } else {
                // Vertical swipe - scroll
                if (Math.abs(deltaY) > this.minSwipeDistance) {
                    if (deltaY > 0) {
                        // Swipe down - scroll up
                        if (this.viewer.needsScroll()) {
                            this.viewer.scrollUp();
                        }
                    } else {
                        // Swipe up - scroll down
                        if (this.viewer.needsScroll()) {
                            this.viewer.scrollDown();
                        }
                    }
                }
            }
        }
    }

    trackAndDownload() {
        // Track the download via HTMX endpoint (async, don't block the download)
        if (this.documentId && this.fileId) {
            fetch('/documents/document/' + this.documentId + '/download/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: 'file_id=' + this.fileId
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update download count in UI
                    const downloadCountElement = document.querySelector('.doc-stats div:nth-child(1) p:first-child');
                    if (downloadCountElement) {
                        downloadCountElement.textContent = data.download_count;
                    }
                }
            })
            .catch(error => {
                console.error('Error tracking download:', error);
            });
        }
        // Open file in new tab
        window.open(this.fileUrl, '_blank');
    }

    getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    destroy() {
        if (this.isFullscreen) {
            this.exitFullscreen();
        }
        if (this.viewer) {
            this.viewer.destroy();
        }
        if (this.toolbar) {
            this.toolbar.remove();
        }
    }
}

/**
 * Viewer Factory - Creates appropriate viewer based on file type
 */
class ViewerFactory {
    static createViewer(fileType, container, fileUrl) {
        switch (fileType) {
            case 'pdf':
                return new PDFViewer(container, fileUrl);
            case 'docx':
            case 'doc':
                return new DOCXViewer(container, fileUrl);
            case 'pptx':
            case 'ppt':
                return new PPTXViewer(container, fileUrl);
            case 'txt':
            case 'md':
                return new TextViewer(container, fileUrl, fileType === 'md');
            case 'png':
            case 'jpg':
            case 'jpeg':
            case 'gif':
            case 'webp':
                return new ImageViewer(container, fileUrl);
            default:
                return new UnsupportedViewer(container, fileUrl, fileType);
        }
    }
}

/**
 * PDF Viewer using PDF.js
 */
class PDFViewer {
    constructor(container, fileUrl) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.pdfDoc = null;
        this.currentPage = 1;
        this.scale = 1.0;
        this.canvas = null;
    }

    async load() {
        // Load PDF.js from CDN
        if (typeof pdfjsLib === 'undefined') {
            await this.loadPDFJS();
        }

        const loadingTask = pdfjsLib.getDocument(this.fileUrl);
        this.pdfDoc = await loadingTask.promise;
        
        this.createCanvas();
        await this.renderPage(this.currentPage);
    }

    async loadPDFJS() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/vendor/pdfjs/pdf.min.js';
            script.onload = () => {
                pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/vendor/pdfjs/pdf.worker.min.js';
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.style.cssText = 'width: 100%; height: auto; display: block; max-width: 100%;';

        const viewerContainer = document.createElement('div');
        viewerContainer.className = 'pdf-viewer-container';

        // Responsive height based on viewport
        const viewportHeight = window.innerHeight;
        let minHeight = 280;
        if (viewportHeight <= 400) {
            minHeight = 200;
        } else if (viewportHeight <= 500) {
            minHeight = 220;
        } else if (viewportHeight <= 600) {
            minHeight = 250;
        }

        viewerContainer.style.cssText = `
            height: 70vh;
            min-height: ${minHeight}px;
            overflow: hidden;
            background: #525659;
            display: flex;
            justify-content: center;
            padding: 20px;
        `;

        const pageWrapper = document.createElement('div');
        pageWrapper.style.cssText = 'box-shadow: 0 2px 8px rgba(0,0,0,0.3); max-width: 100%; overflow: hidden;';
        pageWrapper.appendChild(this.canvas);

        viewerContainer.appendChild(pageWrapper);
        this.container.appendChild(viewerContainer);
    }

    async renderPage(pageNum) {
        const page = await this.pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale: this.scale });
        
        this.canvas.height = viewport.height;
        this.canvas.width = viewport.width;
        
        const renderContext = {
            canvasContext: this.canvas.getContext('2d'),
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
    }

    async goToPage(pageNum) {
        this.currentPage = pageNum;
        await this.renderPage(pageNum);
    }

    getTotalPages() {
        return this.pdfDoc ? this.pdfDoc.numPages : null;
    }

    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return true;
    }

    needsZoom() {
        return true;
    }

    needsScroll() {
        return false;
    }

    scrollUp() {}
    scrollDown() {}

    async zoomIn() {
        this.scale = Math.min(this.scale + 0.25, 3.0);
        await this.renderPage(this.currentPage);
        this.updateZoomIndicator();
        
        // Remove max-width constraint when zoomed
        const canvas = this.container.querySelector('canvas');
        if (canvas && this.scale > 1) {
            canvas.style.maxWidth = 'none';
            canvas.style.maxHeight = 'none';
        } else if (canvas) {
            canvas.style.maxWidth = '100%';
            canvas.style.maxHeight = '100%';
        }
    }

    async zoomOut() {
        this.scale = Math.max(this.scale - 0.25, 0.5);
        await this.renderPage(this.currentPage);
        this.updateZoomIndicator();
        
        // Remove max-width constraint when zoomed
        const canvas = this.container.querySelector('canvas');
        if (canvas && this.scale > 1) {
            canvas.style.maxWidth = 'none';
            canvas.style.maxHeight = 'none';
        } else if (canvas) {
            canvas.style.maxWidth = '100%';
            canvas.style.maxHeight = '100%';
        }
    }

    updateZoomIndicator() {
        const zoomIndicator = document.getElementById('viewer-zoom-indicator');
        if (zoomIndicator) {
            const percentage = Math.round(this.scale * 100);
            zoomIndicator.textContent = `${percentage}%`;
        }
    }

    destroy() {
        if (this.pdfDoc) {
            this.pdfDoc.destroy();
        }
    }
}

/**
 * DOCX Viewer using Mammoth.js
 */
class DOCXViewer {
    constructor(container, fileUrl) {
        this.container = container;
        this.fileUrl = fileUrl;
    }

    async load() {
        if (typeof mammoth === 'undefined') {
            await this.loadMammoth();
        }

        const response = await fetch(this.fileUrl);
        const arrayBuffer = await response.arrayBuffer();
        const result = await mammoth.convertToHtml({ arrayBuffer });
        
        this.createContent(result.value);
    }

    async loadMammoth() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/vendor/mammoth/mammoth.browser.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createContent(html) {
        const viewerContainer = document.createElement('div');
        viewerContainer.className = 'docx-viewer-container';

        // Responsive height based on viewport
        const viewportHeight = window.innerHeight;
        let minHeight = 280;
        if (viewportHeight <= 400) {
            minHeight = 200;
        } else if (viewportHeight <= 500) {
            minHeight = 220;
        } else if (viewportHeight <= 600) {
            minHeight = 250;
        }

        viewerContainer.style.cssText = `
            height: 70vh;
            min-height: ${minHeight}px;
            overflow: hidden;
            background: white;
            padding: 40px;
            border-radius: 0 0 12px 12px;
        `;

        viewerContainer.innerHTML = `
            <div style="max-width: 90%; margin: 0 auto; font-family: 'Times New Roman', serif; line-height: 1.6; overflow: hidden;">
                ${html}
            </div>
        `;

        this.container.appendChild(viewerContainer);
    }

    goToPage() {
        // DOCX is continuous scroll, no pagination
    }

    getTotalPages() {
        return null;
    }

    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return false;
    }

    needsZoom() {
        return true;
    }

    needsScroll() {
        return true;
    }

    scrollUp() {
        const container = this.container.querySelector('.docx-viewer-container');
        if (container) {
            container.scrollBy({ top: -200, behavior: 'smooth' });
        }
    }

    scrollDown() {
        const container = this.container.querySelector('.docx-viewer-container');
        if (container) {
            container.scrollBy({ top: 200, behavior: 'smooth' });
        }
    }

    async zoomIn() {
        const viewer = this.container.querySelector('.docx-viewer-container > div');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.min(currentScale + 0.25, 3.0);
            viewer.style.transform = `scale(${currentScale})`;

            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
            } else {
                viewer.style.maxWidth = '90%';
            }
        }
    }
    
    async zoomOut() {
        const viewer = this.container.querySelector('.docx-viewer-container > div');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.max(currentScale - 0.25, 0.5);
            viewer.style.transform = `scale(${currentScale})`;

            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
            } else {
                viewer.style.maxWidth = '90%';
            }
        }
    }

    destroy() {}
}

/**
 * PPTX Viewer - Shows slide count and download prompt
 */
class PPTXViewer {
    constructor(container, fileUrl) {
        this.container = container;
        this.fileUrl = fileUrl;
    }

    async load() {
        this.createContent();
    }

    createContent() {
        this.container.innerHTML = `
            <div class="pptx-viewer-container" style="height: 600px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: linear-gradient(135deg, #DC2626 0%, #B91C1C 100%); border-radius: 0 0 12px 12px; text-align: center; padding: 32px;">
                <i class="bi bi-file-earmark-play" style="font-size: 5rem; color: white; margin-bottom: 24px;"></i>
                <h3 style="font-size: 1.5rem; font-weight: 600; color: white; margin: 0 0 12px 0;">Presentation Preview</h3>
                <p style="font-size: 1rem; color: rgba(255,255,255,0.9); margin: 0 0 24px 0;">PowerPoint presentations cannot be previewed in the browser. Please download the file to view.</p>
                <a href="${this.fileUrl}" download class="btn btn-primary" style="background: white; color: #DC2626; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    <i class="bi bi-download" style="margin-right: 8px;"></i>Download Presentation
                </a>
            </div>
        `;
    }

    goToPage() {}
    getTotalPages() { return null; }
    
    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return false;
    }

    needsZoom() {
        return false;
    }

    needsScroll() {
        return false;
    }

    scrollUp() {}
    scrollDown() {}
    zoomIn() {}
    zoomOut() {}
    destroy() {}
}

/**
 * Text/Markdown Viewer
 */
class TextViewer {
    constructor(container, fileUrl, isMarkdown) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.isMarkdown = isMarkdown;
    }

    async load() {
        const response = await fetch(this.fileUrl);
        const text = await response.text();
        
        let content = text;
        if (this.isMarkdown && typeof marked !== 'undefined') {
            content = marked.parse(text);
        } else if (this.isMarkdown) {
            await this.loadMarked();
            content = marked.parse(text);
        }
        
        this.createContent(content);
    }

    async loadMarked() {
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/vendor/marked/marked.min.js';
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    createContent(content) {
        const viewerContainer = document.createElement('div');
        viewerContainer.className = 'text-viewer-container';
        viewerContainer.style.cssText = `
            height: 600px;
            overflow: hidden;
            background: white;
            padding: 40px;
            border-radius: 0 0 12px 12px;
        `;
        
        viewerContainer.innerHTML = `
            <div style="max-width: 800px; margin: 0 auto; font-family: 'Courier New', monospace; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; overflow: hidden;">
                ${this.isMarkdown ? content : this.escapeHtml(content)}
            </div>
        `;
        
        this.container.appendChild(viewerContainer);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    goToPage() {}
    getTotalPages() { return null; }
    
    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return false;
    }

    needsZoom() {
        return true;
    }

    needsScroll() {
        return true;
    }

    scrollUp() {
        const container = this.container.querySelector('.text-viewer-container');
        if (container) {
            container.scrollBy({ top: -200, behavior: 'smooth' });
        }
    }

    scrollDown() {
        const container = this.container.querySelector('.text-viewer-container');
        if (container) {
            container.scrollBy({ top: 200, behavior: 'smooth' });
        }
    }

    async zoomIn() {
        const viewer = this.container.querySelector('.text-viewer-container > div');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.min(currentScale + 0.25, 3.0);
            viewer.style.transform = `scale(${currentScale})`;
            
            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
            } else {
                viewer.style.maxWidth = '800px';
            }
        }
    }
    
    async zoomOut() {
        const viewer = this.container.querySelector('.text-viewer-container > div');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.max(currentScale - 0.25, 0.5);
            viewer.style.transform = `scale(${currentScale})`;
            
            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
            } else {
                viewer.style.maxWidth = '800px';
            }
        }
    }
    
    destroy() {}
}

/**
 * Image Viewer
 */
class ImageViewer {
    constructor(container, fileUrl) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.scale = 1.0;
    }

    async load() {
        this.createContent();
    }

    createContent() {
        const viewerContainer = document.createElement('div');
        viewerContainer.className = 'image-viewer-container';
        viewerContainer.style.cssText = `
            height: 600px;
            overflow: hidden;
            background: #f5f5f5;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            border-radius: 0 0 12px 12px;
            position: relative;
        `;
        
        const img = document.createElement('img');
        img.src = this.fileUrl;
        img.style.cssText = 'max-width: 100%; max-height: 100%; object-fit: contain; display: block;';
        img.alt = 'Document preview';
        
        viewerContainer.appendChild(img);
        this.container.appendChild(viewerContainer);
    }

    goToPage() {}
    getTotalPages() { return null; }
    
    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return false;
    }

    needsZoom() {
        return true;
    }

    needsScroll() {
        return false;
    }

    scrollUp() {}
    scrollDown() {}
    
    async zoomIn() {
        const viewer = this.container.querySelector('.image-viewer-container img');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.min(currentScale + 0.25, 3.0);
            viewer.style.transform = `scale(${currentScale})`;
            
            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
                viewer.style.maxHeight = 'none';
            } else {
                viewer.style.maxWidth = '100%';
                viewer.style.maxHeight = '100%';
            }
        }
    }
    
    async zoomOut() {
        const viewer = this.container.querySelector('.image-viewer-container img');
        if (viewer) {
            const currentTransform = viewer.style.transform || '';
            const scaleMatch = currentTransform.match(/scale\(([\d.]+)\)/);
            let currentScale = scaleMatch ? parseFloat(scaleMatch[1]) : 1.0;
            currentScale = Math.max(currentScale - 0.25, 0.5);
            viewer.style.transform = `scale(${currentScale})`;
            
            // Remove max-width constraint when zoomed
            if (currentScale > 1) {
                viewer.style.maxWidth = 'none';
                viewer.style.maxHeight = 'none';
            } else {
                viewer.style.maxWidth = '100%';
                viewer.style.maxHeight = '100%';
            }
        }
    }
    
    destroy() {}
}

/**
 * Unsupported Viewer - Fallback for unsupported file types
 */
class UnsupportedViewer {
    constructor(container, fileUrl, fileType) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.fileType = fileType;
    }

    async load() {
        this.createContent();
    }

    createContent() {
        this.container.innerHTML = `
            <div class="unsupported-viewer-container" style="height: 600px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: linear-gradient(135deg, var(--primary-light) 0%, var(--primary) 100%); border-radius: 0 0 12px 12px; text-align: center; padding: 32px;">
                <i class="bi bi-file-earmark" style="font-size: 5rem; color: white; margin-bottom: 24px;"></i>
                <h3 style="font-size: 1.5rem; font-weight: 600; color: white; margin: 0 0 12px 0;">Preview Unavailable</h3>
                <p style="font-size: 1rem; color: rgba(255,255,255,0.9); margin: 0 0 8px 0;">.${this.fileType.toUpperCase()} files cannot be previewed in the browser.</p>
                <p style="font-size: 0.9rem; color: rgba(255,255,255,0.8); margin: 0 0 24px 0;">Please download the file to view its contents.</p>
                <a href="${this.fileUrl}" download class="btn btn-primary" style="background: white; color: var(--primary); padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 600;">
                    <i class="bi bi-download" style="margin-right: 8px;"></i>Download File
                </a>
            </div>
        `;
    }

    goToPage() {}
    getTotalPages() { return null; }
    
    needsToolbar() {
        return true;
    }

    needsPageNavigation() {
        return false;
    }

    needsZoom() {
        return false;
    }

    needsScroll() {
        return false;
    }

    scrollUp() {}
    scrollDown() {}
    zoomIn() {}
    zoomOut() {}
    destroy() {}
}
