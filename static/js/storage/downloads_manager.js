/**
 * Downloads Manager for PwaniNet
 * Handles file downloads using OPFS (Origin Private File System) with IndexedDB fallback
 */

class DownloadsManager {
    constructor() {
        this.opfsAvailable = 'showOpenFilePicker' in window || 'getDirectory' in navigator;
        this.useOPFS = this.opfsAvailable;
        this.opfsRoot = null;
        this.indexedDBManager = null;
        this.initialized = false;
    }

    /**
     * Initialize the downloads manager
     */
    async init() {
        if (this.initialized) return;

        // Initialize IndexedDB manager
        const { indexedDBManager } = await import('./indexeddb.js');
        this.indexedDBManager = indexedDBManager;
        await this.indexedDBManager.init();

        // Initialize OPFS if available
        if (this.useOPFS) {
            try {
                this.opfsRoot = await navigator.storage.getDirectory();
                console.log('OPFS initialized successfully');
            } catch (error) {
                console.warn('OPFS initialization failed, falling back to IndexedDB:', error);
                this.useOPFS = false;
            }
        }

        this.initialized = true;
    }

    /**
     * Download a media file
     */
    async download(media) {
        await this.init();

        const { url, filename, postId, mediaId, mimeType, category } = media;

        // Check if already downloaded
        const exists = await this.exists(url);
        if (exists) {
            this.showToast('Already downloaded', 'info');
            return null;
        }

        try {
            // Fetch the file
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch: ${response.statusText}`);
            }

            const blob = await response.blob();
            const size = blob.size;
            const extension = this.getExtension(filename, mimeType);
            const downloadDate = new Date().toISOString();
            const id = this.generateId();

            // Store file
            let fileHandle;
            if (this.useOPFS) {
                fileHandle = await this.storeInOPFS(id, blob, filename);
            } else {
                fileHandle = await this.storeInIndexedDB(id, blob);
            }

            // Generate thumbnail for images
            let thumbnail = null;
            if (category === 'image') {
                thumbnail = await this.generateThumbnail(blob);
            }

            // Create metadata
            const metadata = {
                id,
                postId,
                mediaId,
                filename,
                mimeType,
                extension,
                category,
                size,
                downloadDate,
                thumbnail,
                sourceURL: url,
                opfsPath: this.useOPFS ? `/downloads/${id}/${filename}` : null
            };

            // Save metadata
            await this.indexedDBManager.addDownload(metadata);

            this.showToast('Download complete', 'success');
            return metadata;
        } catch (error) {
            console.error('Download failed:', error);
            this.showToast('Download failed: ' + error.message, 'error');
            throw error;
        }
    }

    /**
     * Store file in OPFS
     */
    async storeInOPFS(id, blob, filename) {
        const downloadsDir = await this.opfsRoot.getDirectoryHandle('downloads', { create: true });
        const fileDir = await downloadsDir.getDirectoryHandle(id, { create: true });
        const fileHandle = await fileDir.getFileHandle(filename, { create: true });
        const writable = await fileHandle.createWritable();
        await writable.write(blob);
        await writable.close();
        return fileHandle;
    }

    /**
     * Store file in IndexedDB (fallback)
     */
    async storeInIndexedDB(id, blob) {
        // Store in a separate IndexedDB store for blobs
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('PwaniNetFiles', 1);

            request.onerror = () => reject(request.error);

            request.onsuccess = () => {
                const db = request.result;
                const transaction = db.transaction(['files'], 'readwrite');
                const store = transaction.objectStore('files');
                const putRequest = store.put({ id, blob });

                putRequest.onsuccess = () => resolve(putRequest.result);
                putRequest.onerror = () => reject(putRequest.error);
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains('files')) {
                    db.createObjectStore('files', { keyPath: 'id' });
                }
            };
        });
    }

    /**
     * Check if a file exists
     */
    async exists(sourceURL) {
        await this.init();
        return await this.indexedDBManager.downloadExists(sourceURL);
    }

    /**
     * Get all downloads
     */
    async getAll() {
        await this.init();
        return await this.indexedDBManager.getAllDownloads();
    }

    /**
     * Get downloads by category
     */
    async getByCategory(category) {
        await this.init();
        return await this.indexedDBManager.getDownloadsByCategory(category);
    }

    /**
     * Get images
     */
    async getImages() {
        return await this.getByCategory('image');
    }

    /**
     * Get videos
     */
    async getVideos() {
        return await this.getByCategory('video');
    }

    /**
     * Get documents
     */
    async getDocuments() {
        return await this.getByCategory('document');
    }

    /**
     * Open a downloaded file
     */
    async open(id) {
        await this.init();

        const metadata = await this.indexedDBManager.getDownload(id);
        if (!metadata) {
            throw new Error('Download not found');
        }

        let blob;
        if (this.useOPFS && metadata.opfsPath) {
            blob = await this.getFromOPFS(metadata);
        } else {
            blob = await this.getFromIndexedDB(id);
        }

        if (!blob) {
            throw new Error('File not found in storage');
        }

        // Create object URL and open
        const objectUrl = URL.createObjectURL(blob);
        
        if (metadata.category === 'image') {
            // Open in fullscreen viewer
            this.openImageViewer(objectUrl, metadata);
        } else if (metadata.category === 'video') {
            // Play in existing video player
            this.openVideoPlayer(objectUrl, metadata);
        } else {
            // Open in browser
            window.open(objectUrl, '_blank');
        }

        // Cleanup object URL after some time
        setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    }

    /**
     * Get file from OPFS
     */
    async getFromOPFS(metadata) {
        const downloadsDir = await this.opfsRoot.getDirectoryHandle('downloads');
        const fileDir = await downloadsDir.getDirectoryHandle(metadata.id);
        const fileHandle = await fileDir.getFileHandle(metadata.filename);
        const file = await fileHandle.getFile();
        return file;
    }

    /**
     * Get file from IndexedDB
     */
    async getFromIndexedDB(id) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('PwaniNetFiles', 1);

            request.onerror = () => reject(request.error);

            request.onsuccess = () => {
                const db = request.result;
                const transaction = db.transaction(['files'], 'readonly');
                const store = transaction.objectStore('files');
                const getRequest = store.get(id);

                getRequest.onsuccess = () => {
                    if (getRequest.result) {
                        resolve(getRequest.result.blob);
                    } else {
                        resolve(null);
                    }
                };
                getRequest.onerror = () => reject(getRequest.error);
            };
        });
    }

    /**
     * Open image in fullscreen viewer
     */
    openImageViewer(objectUrl, metadata) {
        // Reuse existing fullscreen viewer if available
        const existingViewer = document.querySelector('.fullscreen-container');
        if (existingViewer) {
            const img = existingViewer.querySelector('.fullscreen-image');
            if (img) {
                img.src = objectUrl;
                return;
            }
        }

        // Create new fullscreen viewer
        const viewer = document.createElement('div');
        viewer.className = 'fullscreen-container';
        viewer.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #000;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        `;

        const img = document.createElement('img');
        img.src = objectUrl;
        img.className = 'fullscreen-image';
        img.style.cssText = `
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        `;

        const closeBtn = document.createElement('button');
        closeBtn.innerHTML = '<i class="bi bi-x-lg"></i>';
        closeBtn.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.9);
            border: none;
            font-size: 24px;
            cursor: pointer;
            z-index: 10000;
        `;
        closeBtn.onclick = () => viewer.remove();

        viewer.appendChild(closeBtn);
        viewer.appendChild(img);
        document.body.appendChild(viewer);
    }

    /**
     * Open video in existing video player
     */
    openVideoPlayer(objectUrl, metadata) {
        // Create a modal with video player
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.style.cssText = 'display: block; background: rgba(0,0,0,0.8);';
        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content bg-dark">
                    <div class="modal-header border-0">
                        <h5 class="modal-title text-white">${metadata.filename}</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <video controls class="w-100" style="max-height: 70vh;">
                            <source src="${objectUrl}" type="${metadata.mimeType}">
                        </video>
                    </div>
                </div>
            </div>
        `;

        const closeBtn = modal.querySelector('.btn-close');
        closeBtn.onclick = () => modal.remove();
        modal.onclick = (e) => {
            if (e.target === modal) modal.remove();
        };

        document.body.appendChild(modal);
    }

    /**
     * Share a downloaded file
     */
    async share(id) {
        await this.init();

        const metadata = await this.indexedDBManager.getDownload(id);
        if (!metadata) {
            throw new Error('Download not found');
        }

        let blob;
        if (this.useOPFS && metadata.opfsPath) {
            blob = await this.getFromOPFS(metadata);
        } else {
            blob = await this.getFromIndexedDB(id);
        }

        if (!blob) {
            throw new Error('File not found in storage');
        }

        const file = new File([blob], metadata.filename, { type: metadata.mimeType });

        // Try Web Share API
        if (navigator.share && navigator.canShare({ files: [file] })) {
            try {
                await navigator.share({
                    files: [file],
                    title: metadata.filename,
                    text: `Shared from PwaniNet`
                });
                return;
            } catch (error) {
                if (error.name !== 'AbortError') {
                    console.warn('Share failed:', error);
                }
            }
        }

        // Fallback: copy download link or download again
        this.showToast('Share not supported. Downloading instead.', 'info');
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objectUrl;
        a.download = metadata.filename;
        a.click();
        URL.revokeObjectURL(objectUrl);
    }

    /**
     * Delete a downloaded file
     */
    async delete(id) {
        await this.init();

        const metadata = await this.indexedDBManager.getDownload(id);
        if (!metadata) {
            throw new Error('Download not found');
        }

        // Delete from storage
        if (this.useOPFS && metadata.opfsPath) {
            await this.deleteFromOPFS(metadata);
        } else {
            await this.deleteFromIndexedDB(id);
        }

        // Delete metadata
        await this.indexedDBManager.deleteDownload(id);

        this.showToast('Download deleted', 'success');
    }

    /**
     * Delete from OPFS
     */
    async deleteFromOPFS(metadata) {
        try {
            const downloadsDir = await this.opfsRoot.getDirectoryHandle('downloads');
            await downloadsDir.removeEntry(metadata.id, { recursive: true });
        } catch (error) {
            console.warn('Failed to delete from OPFS:', error);
        }
    }

    /**
     * Delete from IndexedDB
     */
    async deleteFromIndexedDB(id) {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('PwaniNetFiles', 1);

            request.onerror = () => reject(request.error);

            request.onsuccess = () => {
                const db = request.result;
                const transaction = db.transaction(['files'], 'readwrite');
                const store = transaction.objectStore('files');
                const deleteRequest = store.delete(id);

                deleteRequest.onsuccess = () => resolve();
                deleteRequest.onerror = () => reject(deleteRequest.error);
            };
        });
    }

    /**
     * Clear all downloads
     */
    async clear() {
        await this.init();

        const downloads = await this.getAll();

        // Delete all files
        for (const download of downloads) {
            if (this.useOPFS && download.opfsPath) {
                await this.deleteFromOPFS(download);
            } else {
                await this.deleteFromIndexedDB(download.id);
            }
        }

        // Clear metadata
        await this.indexedDBManager.clearDownloads();

        this.showToast('All downloads cleared', 'success');
    }

    /**
     * Generate thumbnail from image blob
     */
    async generateThumbnail(blob, maxSize = 200) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            const url = URL.createObjectURL(blob);

            img.onload = () => {
                URL.revokeObjectURL(url);

                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                let width = img.width;
                let height = img.height;

                if (width > height) {
                    if (width > maxSize) {
                        height *= maxSize / width;
                        width = maxSize;
                    }
                } else {
                    if (height > maxSize) {
                        width *= maxSize / height;
                        height = maxSize;
                    }
                }

                canvas.width = width;
                canvas.height = height;

                ctx.drawImage(img, 0, 0, width, height);

                canvas.toBlob((thumbnailBlob) => {
                    resolve(URL.createObjectURL(thumbnailBlob));
                }, 'image/jpeg', 0.8);
            };

            img.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('Failed to generate thumbnail'));
            };

            img.src = url;
        });
    }

    /**
     * Get file extension
     */
    getExtension(filename, mimeType) {
        const ext = filename.split('.').pop().toLowerCase();
        if (ext && ext !== filename) {
            return ext;
        }

        // Fallback to mime type
        const mimeToExt = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/webp': 'webp',
            'image/gif': 'gif',
            'video/mp4': 'mp4',
            'video/webm': 'webm',
            'video/quicktime': 'mov',
            'application/pdf': 'pdf',
            'text/plain': 'txt',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
        };

        return mimeToExt[mimeType] || 'unknown';
    }

    /**
     * Generate unique ID
     */
    generateId() {
        return 'download_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        // Try to use existing toast system
        const existingToast = document.querySelector('.toast-container');
        if (existingToast) {
            // Create toast element
            const toast = document.createElement('div');
            toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
            toast.setAttribute('role', 'alert');
            toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            `;
            existingToast.appendChild(toast);
            
            const bsToast = new bootstrap.Toast(toast);
            bsToast.show();
            
            toast.addEventListener('hidden.bs.toast', () => toast.remove());
        } else {
            // Fallback to console
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Sort downloads
     */
    sortDownloads(downloads, sortBy = 'newest') {
        const sorted = [...downloads];
        
        switch (sortBy) {
            case 'newest':
                sorted.sort((a, b) => new Date(b.downloadDate) - new Date(a.downloadDate));
                break;
            case 'oldest':
                sorted.sort((a, b) => new Date(a.downloadDate) - new Date(b.downloadDate));
                break;
            case 'largest':
                sorted.sort((a, b) => b.size - a.size);
                break;
            case 'smallest':
                sorted.sort((a, b) => a.size - b.size);
                break;
            case 'az':
                sorted.sort((a, b) => a.filename.localeCompare(b.filename));
                break;
        }

        return sorted;
    }

    /**
     * Search downloads
     */
    searchDownloads(downloads, query) {
        const lowerQuery = query.toLowerCase();
        return downloads.filter(d => 
            d.filename.toLowerCase().includes(lowerQuery) ||
            d.extension.toLowerCase().includes(lowerQuery) ||
            d.category.toLowerCase().includes(lowerQuery)
        );
    }
}

// Export singleton instance
const downloadsManager = new DownloadsManager();
