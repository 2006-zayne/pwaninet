/**
 * Upload API
 * 
 * Responsible only for communication with Django backend.
 * Encapsulates FormData creation, CSRF, HTMX integration, fetch/XHR, and response parsing.
 * No UI code inside UploadAPI.
 */

class UploadAPI {
    constructor() {
        this.baseUrl = this.resolveBaseUrl();
        this.csrfToken = this.getCSRFToken();
    }

    resolveBaseUrl() {
        // Primary endpoint for post creation in Django URLs.
        const defaultCreatePath = '/api/posts/';
        if (typeof window === 'undefined' || !window.location) {
            return defaultCreatePath;
        }

        const path = window.location.pathname || '';
        // If we are already on an API path or similar, you might want to use it
        // but typically all uploads should go to /api/posts/
        return defaultCreatePath;
    }

    /**
     * Get CSRF token from meta tag or cookie
     * @returns {string}
     */
    getCSRFToken() {
        // Try meta tag first
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (metaTag) {
            return metaTag.getAttribute('content');
        }

        // Try cookie
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return decodeURIComponent(value);
            }
        }

        return '';
    }

    /**
     * Create FormData for post creation
     * @param {object} data - Upload data
     * @param {string} data.content - Post content
     * @param {File[]} data.images - Image files
     * @param {File} data.video - Video file
     * @param {File} data.docs - Document file
     * @param {File} data.audio - Audio file
     * @param {string} data.unit - Unit ID
     * @param {string} data.group - Group ID
     * @param {string} data.gradient_class - Gradient class
     * @returns {FormData}
     */
    createFormData(data) {
        console.log('[UploadAPI] Creating FormData with data:', data);
        const formData = new FormData();

        // Add text fields
        if (data.content) {
            formData.append('content', data.content);
            console.log('[UploadAPI] Adding content:', data.content);
        }
        if (data.unit) {
            formData.append('unit', data.unit);
            console.log('[UploadAPI] Adding unit:', data.unit);
        }
        if (data.group) {
            formData.append('group', data.group);
            console.log('[UploadAPI] Adding group:', data.group);
        }
        if (data.visibility) {
            formData.append('visibility', data.visibility);
            console.log('[UploadAPI] Adding visibility:', data.visibility);
        }
        if (data.gradient_class) {
            formData.append('gradient_class', data.gradient_class);
            console.log('[UploadAPI] Adding gradient_class:', data.gradient_class);
        }
        if (data.custom_gradient_text && data.custom_gradient_text.trim() !== '') {
            formData.append('custom_gradient_text', data.custom_gradient_text);
            console.log('[UploadAPI] Adding custom_gradient_text:', data.custom_gradient_text);
        }
        if (data.custom_gradient_color1 && data.custom_gradient_color1.trim() !== '') {
            formData.append('custom_gradient_color1', data.custom_gradient_color1);
            console.log('[UploadAPI] Adding custom_gradient_color1:', data.custom_gradient_color1);
        }
        if (data.custom_gradient_color2 && data.custom_gradient_color2.trim() !== '') {
            formData.append('custom_gradient_color2', data.custom_gradient_color2);
            console.log('[UploadAPI] Adding custom_gradient_color2:', data.custom_gradient_color2);
        }
        if (data.custom_gradient_text_color && data.custom_gradient_text_color.trim() !== '') {
            formData.append('custom_gradient_text_color', data.custom_gradient_text_color);
            console.log('[UploadAPI] Adding custom_gradient_text_color:', data.custom_gradient_text_color);
        }

        // Add media files
        if (data.images && data.images.length > 0) {
            data.images.forEach((image, index) => {
                formData.append('images', image);
            });
            console.log('[UploadAPI] Adding', data.images.length, 'images');
        }
        if (data.video) {
            formData.append('video', data.video);
            console.log('[UploadAPI] Adding video');
        }
        if (data.docs) {
            formData.append('docs', data.docs);
            console.log('[UploadAPI] Adding docs');
        }
        if (data.audio) {
            formData.append('audio', data.audio);
            console.log('[UploadAPI] Adding audio');
        }

        console.log('[UploadAPI] FormData created successfully');
        return formData;
    }

    createFormDataFromSession(session) {
        return this.createFormData({
            content: session.caption,
            images: session.files.filter((file) => file.type.startsWith('image/')),
            video: session.files.find((file) => file.type.startsWith('video/')) || null,
            docs: session.files.find((file) => file.type === 'application/pdf') || null,
            audio: session.files.find((file) => file.type.startsWith('audio/')) || null,
            unit: session.metadata?.unit || null,
            group: session.metadata?.group || null,
            visibility: session.visibility || null,
            gradient_class: session.metadata?.gradient_class || 'none',
            custom_gradient_text: session.metadata?.custom_gradient_text || null,
            custom_gradient_color1: session.metadata?.custom_gradient_color1 || null,
            custom_gradient_color2: session.metadata?.custom_gradient_color2 || null,
        });
    }

    resolveFormData(input) {
        if (input && typeof input === 'object' && Array.isArray(input.files) && 'caption' in input) {
            return this.createFormDataFromSession(input);
        }
        return this.createFormData(input);
    }

    /**
     * Get default headers for requests
     * @returns {object}
     */
    getHeaders() {
        const headers = {
            'X-Requested-With': 'XMLHttpRequest',
        };

        if (this.csrfToken) {
            headers['X-CSRFToken'] = this.csrfToken;
        }

        return headers;
    }

    /**
     * Upload post data to Django backend
     * @param {object} data - Upload data
     * @param {Function} onProgress - Progress callback
     * @returns {Promise<object>}
     */
    async upload(data, onProgress = null) {
        const formData = this.resolveFormData(data);
        const headers = this.getHeaders();

        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();

            // Track upload progress
            if (onProgress) {
                xhr.upload.addEventListener('progress', (event) => {
                    if (event.lengthComputable) {
                        const percentComplete = (event.loaded / event.total) * 100;
                        onProgress({
                            loaded: event.loaded,
                            total: event.total,
                            percent: percentComplete,
                        });
                    }
                });
            }

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = this.parseResponse(xhr);
                        resolve(response);
                    } catch (error) {
                        reject(new Error('Failed to parse response'));
                    }
                } else {
                    const error = this.parseError(xhr);
                    reject(error);
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Network error during upload'));
            });

            xhr.addEventListener('abort', () => {
                reject(new Error('Upload was cancelled'));
            });

            xhr.open('POST', this.baseUrl);
            
            // Set headers
            Object.entries(headers).forEach(([key, value]) => {
                xhr.setRequestHeader(key, value);
            });

            xhr.send(formData);
        });
    }

    /**
     * Upload using fetch API (alternative to XHR)
     * @param {object} data - Upload data
     * @param {AbortSignal} [signal] - AbortSignal for cancellation
     * @returns {Promise<object>}
     */
    async uploadWithFetch(data, signal = null) {
        const formData = this.resolveFormData(data);
        const headers = this.getHeaders();

        const response = await fetch(this.baseUrl, {
            method: 'POST',
            headers,
            body: formData,
            signal,
        });

        if (!response.ok) {
            throw await this.parseFetchError(response);
        }

        return await this.parseFetchResponse(response);
    }

    /**
     * Parse XHR response
     * @param {XMLHttpRequest} xhr - XHR object
     * @returns {object}
     */
    parseResponse(xhr) {
        const contentType = xhr.getResponseHeader('Content-Type');
        
        if (contentType && contentType.includes('application/json')) {
            try {
                return JSON.parse(xhr.responseText);
            } catch (error) {
                return { success: true, data: xhr.responseText };
            }
        }

        // For form submissions, Django typically redirects on success
        // Check if response is a redirect
        if (xhr.status === 302 || xhr.status === 301) {
            const redirectUrl = xhr.getResponseHeader('Location');
            return { success: true, redirect: redirectUrl };
        }

        // Default response
        return { success: true, data: xhr.responseText };
    }

    /**
     * Parse XHR error
     * @param {XMLHttpRequest} xhr - XHR object
     * @returns {Error}
     */
    parseError(xhr) {
        const contentType = xhr.getResponseHeader('Content-Type');
        let message = `Upload failed with status ${xhr.status}`;
        let errors = null;

        if (contentType && contentType.includes('application/json')) {
            try {
                const data = JSON.parse(xhr.responseText);
                message = data.message || data.error || message;
                errors = data.errors || null;
            } catch (error) {
                // Ignore parse error
            }
        } else {
            // Try to extract error from HTML response
            const parser = new DOMParser();
            const doc = parser.parseFromString(xhr.responseText, 'text/html');
            const errorElement = doc.querySelector('.errorlist, .alert-danger, [role="alert"]');
            if (errorElement) {
                message = errorElement.textContent.trim();
            }
        }

        const error = new Error(message);
        error.status = xhr.status;
        error.errors = errors;
        return error;
    }

    /**
     * Parse fetch response
     * @param {Response} response - Fetch response
     * @returns {object}
     */
    async parseFetchResponse(response) {
        const contentType = response.headers.get('Content-Type');
        
        if (contentType && contentType.includes('application/json')) {
            return await response.json();
        }

        const text = await response.text();
        return { success: true, data: text };
    }

    /**
     * Parse fetch error
     * @param {Response} response - Fetch response
     * @returns {Error}
     */
    async parseFetchError(response) {
        const contentType = response.headers.get('Content-Type');
        let message = `Upload failed with status ${response.status}`;
        let errors = null;

        if (contentType && contentType.includes('application/json')) {
            try {
                const data = await response.json();
                message = data.message || data.error || message;
                errors = data.errors || null;
            } catch (error) {
                // Ignore parse error
            }
        }

        const error = new Error(message);
        error.status = response.status;
        error.errors = errors;
        return error;
    }

    /**
     * Check if HTMX is available
     * @returns {boolean}
     */
    isHTMXAvailable() {
        return typeof htmx !== 'undefined' && htmx !== null;
    }

    /**
     * Trigger HTMX request for post creation
     * @param {HTMLElement} element - Element to trigger HTMX on
     * @param {object} data - Upload data
     * @returns {Promise<void>}
     */
    async uploadWithHTMX(element, data) {
        if (!this.isHTMXAvailable()) {
            throw new Error('HTMX is not available');
        }

        // Set form data
        const formData = this.resolveFormData(data);
        
        // Find or create form
        let form = element.closest('form');
        if (!form) {
            form = document.createElement('form');
            form.method = 'POST';
            form.action = this.baseUrl;
            element.parentNode.insertBefore(form, element);
            form.appendChild(element);
        }

        // Update form with data
        form.innerHTML = '';
        for (const [key, value] of formData.entries()) {
            if (value instanceof File) {
                const input = document.createElement('input');
                input.type = 'file';
                input.name = key;
                input.files = this.createFileList([value]);
                form.appendChild(input);
            } else {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = key;
                input.value = value;
                form.appendChild(input);
            }
        }

        // Add CSRF token
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = this.csrfToken;
        form.appendChild(csrfInput);

        // Trigger HTMX request
        return new Promise((resolve, reject) => {
            htmx.on('htmx:beforeRequest', (event) => {
                if (event.detail.target === form || event.detail.elt === form) {
                    // This is our request
                }
            });

            htmx.on('htmx:afterRequest', (event) => {
                if (event.detail.target === form || event.detail.elt === form) {
                    if (event.detail.successful) {
                        resolve({ success: true });
                    } else {
                        reject(new Error('HTMX request failed'));
                    }
                }
            });

            htmx.trigger(form, 'submit');
        });
    }

    /**
     * Create a FileList from an array of Files
     * @param {File[]} files - Array of files
     * @returns {FileList}
     */
    createFileList(files) {
        const dataTransfer = new DataTransfer();
        files.forEach(file => dataTransfer.items.add(file));
        return dataTransfer.files;
    }

    /**
     * Set base URL for uploads
     * @param {string} url - Base URL
     */
    setBaseUrl(url) {
        this.baseUrl = url;
    }

    /**
     * Update CSRF token
     * @param {string} token - CSRF token
     */
    setCSRFToken(token) {
        this.csrfToken = token;
    }
}

// Global upload API instance
export const uploadAPI = new UploadAPI();

export default UploadAPI;
