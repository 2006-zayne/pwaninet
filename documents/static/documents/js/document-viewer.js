/**
 * Document Viewer System
 * Modular architecture for rendering multiple document types in the browser
 */

class DocumentViewer {
    constructor(container, fileUrl, fileType, fileName) {
        this.container = container;
        this.fileUrl = fileUrl;
        this.fileType = fileType.toLowerCase();
        this.fileName = fileName;
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
        `;

        const leftControls = document.createElement('div');
        leftControls.style.cssText = 'display: flex; align-items: center; gap: 12px;';

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
            `;
            docTypeIndicator.textContent = this.fileType.toUpperCase() + ' Document';
            leftControls.appendChild(docTypeIndicator);
        }

        const rightControls = document.createElement('div');
        rightControls.style.cssText = 'display: flex; align-items: center; gap: 12px;';

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
            window.location.href = this.fileUrl;
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
            this.touchStartX = e.changedTouches[0].screenX;
            this.touchStartY = e.changedTouches[0].screenY;
        }, { passive: true });

        // Touch end
        this.container.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.touchEndY = e.changedTouches[0].screenY;
            this.handleSwipe();
        }, { passive: true });
    }

    handleSwipe() {
        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;
        
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
        this.canvas.style.cssText = 'width: 100%; height: auto; display: block;';
        
        const viewerContainer = document.createElement('div');
        viewerContainer.className = 'pdf-viewer-container';
        viewerContainer.style.cssText = `
            height: 600px;
            overflow: auto;
            background: #525659;
            display: flex;
            justify-content: center;
            padding: 20px;
        `;
        
        const pageWrapper = document.createElement('div');
        pageWrapper.style.cssText = 'box-shadow: 0 2px 8px rgba(0,0,0,0.3);';
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
    }

    async zoomOut() {
        this.scale = Math.max(this.scale - 0.25, 0.5);
        await this.renderPage(this.currentPage);
        this.updateZoomIndicator();
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
        viewerContainer.style.cssText = `
            height: 600px;
            overflow: auto;
            background: white;
            padding: 40px;
            border-radius: 0 0 12px 12px;
        `;
        
        viewerContainer.innerHTML = `
            <div style="max-width: 800px; margin: 0 auto; font-family: 'Times New Roman', serif; line-height: 1.6;">
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
        return false;
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

    zoomIn() {}
    zoomOut() {}

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
            overflow: auto;
            background: white;
            padding: 40px;
            border-radius: 0 0 12px 12px;
        `;
        
        viewerContainer.innerHTML = `
            <div style="max-width: 800px; margin: 0 auto; font-family: 'Courier New', monospace; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;">
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
        return false;
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

    zoomIn() {}
    zoomOut() {}
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
            overflow: auto;
            background: #f5f5f5;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            border-radius: 0 0 12px 12px;
        `;
        
        const img = document.createElement('img');
        img.src = this.fileUrl;
        img.style.cssText = 'max-width: 100%; max-height: 100%; object-fit: contain;';
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
