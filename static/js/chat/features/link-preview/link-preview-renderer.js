/**
 * Link Preview Renderer
 * 
 * Renders Telegram/Discord-style link preview cards with:
 * - Lazy loading for images
 * - Fallback system (favicon, domain initials)
 * - Modern card design with hover effects
 */

export class LinkPreviewRenderer {
    constructor() {
        this.observer = null;
        this.initLazyLoading();
    }

    /**
     * Initialize lazy loading with Intersection Observer
     */
    initLazyLoading() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        if (img.dataset.src) {
                            img.src = img.dataset.src;
                            img.classList.add('loaded');
                            this.observer.unobserve(img);
                        }
                    }
                });
            }, {
                rootMargin: '50px',
                threshold: 0.1
            });
        }
    }

    /**
     * Render link preview card
     * @param {Object} previewData - Link preview data from backend
     * @returns {HTMLElement} - Link preview card element
     */
    render(previewData) {
        console.log("[LINK_PREVIEW] Rendering preview:", previewData);

        if (!previewData || !previewData.url) {
            return null;
        }

        const card = document.createElement('a');
        card.className = 'link-preview-card';
        card.href = previewData.url;
        card.target = '_blank';
        card.rel = 'noopener noreferrer';

        // Build card content
        const content = this.buildCardContent(previewData);
        card.appendChild(content);

        return card;
    }

    /**
     * Build card content based on available data
     * @param {Object} previewData - Link preview data
     * @returns {DocumentFragment} - Card content fragment
     */
    buildCardContent(previewData) {
        const fragment = document.createDocumentFragment();

        // Add thumbnail if available
        if (previewData.has_thumbnail && previewData.image_url) {
            const thumbnail = this.renderThumbnail(previewData.image_url);
            fragment.appendChild(thumbnail);
        } else {
            // Fallback: no thumbnail
            const fallback = this.renderNoThumbnailFallback(previewData);
            fragment.appendChild(fallback);
        }

        // Add content section
        const content = this.renderContentSection(previewData);
        fragment.appendChild(content);

        return fragment;
    }

    /**
     * Render thumbnail image with lazy loading
     * @param {string} imageUrl - Image URL
     * @returns {HTMLElement} - Image element
     */
    renderThumbnail(imageUrl) {
        const img = document.createElement('img');
        img.className = 'link-preview-image';
        img.alt = 'Link preview thumbnail';
        
        // Lazy loading
        if (this.observer) {
            img.dataset.src = imageUrl;
            img.loading = 'lazy';
            this.observer.observe(img);
        } else {
            // Fallback for browsers without IntersectionObserver
            img.src = imageUrl;
            img.loading = 'lazy';
        }

        // Handle load event
        img.onload = () => {
            img.classList.add('loaded');
        };

        // Handle error event
        img.onerror = () => {
            console.warn("[LINK_PREVIEW] Failed to load thumbnail:", imageUrl);
            img.style.display = 'none';
        };

        return img;
    }

    /**
     * Render fallback when no thumbnail is available
     * @param {Object} previewData - Link preview data
     * @returns {HTMLElement} - Fallback element
     */
    renderNoThumbnailFallback(previewData) {
        const fallback = document.createElement('div');
        fallback.className = 'link-preview-no-thumbnail';

        if (previewData.has_favicon && previewData.favicon_url) {
            const favicon = document.createElement('img');
            favicon.className = 'link-preview-favicon-large';
            favicon.src = previewData.favicon_url;
            favicon.alt = 'Favicon';
            fallback.appendChild(favicon);
        } else {
            // Domain initials fallback
            const initials = this.getDomainInitials(previewData.domain || previewData.url);
            const initialsEl = document.createElement('div');
            initialsEl.className = 'link-preview-domain-initials-large';
            initialsEl.textContent = initials;
            fallback.appendChild(initialsEl);
        }

        return fallback;
    }

    /**
     * Render content section (title, description, domain)
     * @param {Object} previewData - Link preview data
     * @returns {HTMLElement} - Content section element
     */
    renderContentSection(previewData) {
        const content = document.createElement('div');
        content.className = 'link-preview-content';

        // Title
        if (previewData.title) {
            const title = document.createElement('div');
            title.className = 'link-preview-title';
            title.textContent = this.sanitize(previewData.title);
            content.appendChild(title);
        }

        // Description
        if (previewData.description) {
            const description = document.createElement('div');
            description.className = 'link-preview-description';
            description.textContent = this.sanitize(previewData.description);
            content.appendChild(description);
        }

        // Domain with favicon
        const domain = this.renderDomain(previewData);
        content.appendChild(domain);

        return content;
    }

    /**
     * Render domain with favicon or initials
     * @param {Object} previewData - Link preview data
     * @returns {HTMLElement} - Domain element
     */
    renderDomain(previewData) {
        const domain = document.createElement('div');
        domain.className = 'link-preview-domain';

        // Add favicon if available
        if (previewData.has_favicon && previewData.favicon_url) {
            const favicon = document.createElement('img');
            favicon.className = 'link-preview-favicon';
            favicon.src = previewData.favicon_url;
            favicon.alt = 'Favicon';
            domain.appendChild(favicon);
        } else {
            // Domain initials fallback
            const initials = this.getDomainInitials(previewData.domain || previewData.url);
            const initialsEl = document.createElement('div');
            initialsEl.className = 'link-preview-domain-initials';
            initialsEl.textContent = initials;
            domain.appendChild(initialsEl);
        }

        // Domain text
        const domainText = document.createElement('span');
        domainText.textContent = previewData.domain || this.extractDomain(previewData.url);
        domain.appendChild(domainText);

        return domain;
    }

    /**
     * Get domain initials for fallback
     * @param {string} domain - Domain name
     * @returns {string} - Initials (max 2 characters)
     */
    getDomainInitials(domain) {
        if (!domain) return '?';
        
        // Extract domain name without TLD
        const parts = domain.replace('www.', '').split('.');
        const name = parts[0] || domain;
        
        // Get first 1-2 characters
        return name.substring(0, 2).toUpperCase();
    }

    /**
     * Extract domain from URL
     * @param {string} url - URL
     * @returns {string} - Domain
     */
    extractDomain(url) {
        try {
            const urlObj = new URL(url);
            return urlObj.hostname;
        } catch (e) {
            return url;
        }
    }

    /**
     * Sanitize text to prevent XSS
     * @param {string} text - Text to sanitize
     * @returns {string} - Sanitized text
     */
    sanitize(text) {
        if (!text) return '';
        
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Cleanup observer
     */
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
    }
}

// Export singleton instance
export const linkPreviewRenderer = new LinkPreviewRenderer();
