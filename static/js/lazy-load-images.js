/**
 * PwaniNet Lazy Image Loader
 * Implements lazy loading for images and media posts
 * Uses Intersection Observer API for performance
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        // Root margin for triggering load (in pixels)
        ROOT_MARGIN: '50px',
        // Threshold for triggering load (0-1)
        THRESHOLD: 0.01,
        // Data attribute for lazy loading
        DATA_ATTR: 'data-src',
        // Class for lazy loaded images
        LOADED_CLASS: 'lazy-loaded',
        // Class for loading state
        LOADING_CLASS: 'lazy-loading'
    };

    let observer = null;

    /**
     * Load image from data-src
     */
    function loadImage(img) {
        const src = img.getAttribute(CONFIG.DATA_ATTR);
        if (!src) return;

        img.classList.add(CONFIG.LOADING_CLASS);

        // Create new image to preload
        const tempImg = new Image();
        
        tempImg.onload = function() {
            img.src = src;
            img.classList.remove(CONFIG.LOADING_CLASS);
            img.classList.add(CONFIG.LOADED_CLASS);
            img.removeAttribute(CONFIG.DATA_ATTR);
        };

        tempImg.onerror = function() {
            img.classList.remove(CONFIG.LOADING_CLASS);
            // Show fallback or error state
            img.style.opacity = '0.5';
        };

        tempImg.src = src;
    }

    /**
     * Load video from data-src
     */
    function loadVideo(video) {
        const src = video.getAttribute(CONFIG.DATA_ATTR);
        if (!src) return;

        video.classList.add(CONFIG.LOADING_CLASS);
        video.src = src;
        video.classList.remove(CONFIG.LOADING_CLASS);
        video.classList.add(CONFIG.LOADED_CLASS);
        video.removeAttribute(CONFIG.DATA_ATTR);
    }

    /**
     * Load background image from data-src
     */
    function loadBackground(element) {
        const src = element.getAttribute(CONFIG.DATA_ATTR);
        if (!src) return;

        element.classList.add(CONFIG.LOADING_CLASS);

        const tempImg = new Image();
        tempImg.onload = function() {
            element.style.backgroundImage = `url('${src}')`;
            element.classList.remove(CONFIG.LOADING_CLASS);
            element.classList.add(CONFIG.LOADED_CLASS);
            element.removeAttribute(CONFIG.DATA_ATTR);
        };

        tempImg.src = src;
    }

    /**
     * Handle intersection observer callback
     */
    function handleIntersection(entries, observer) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                
                if (element.tagName === 'IMG') {
                    loadImage(element);
                } else if (element.tagName === 'VIDEO') {
                    loadVideo(element);
                } else {
                    loadBackground(element);
                }
                
                observer.unobserve(element);
            }
        });
    }

    /**
     * Initialize lazy loading
     */
    function initLazyLoading() {
        // Check if Intersection Observer is supported
        if (!('IntersectionObserver' in window)) {
            console.warn('[LazyLoad] Intersection Observer not supported, loading all images immediately');
            loadAllImages();
            return;
        }

        // Create observer
        observer = new IntersectionObserver(handleIntersection, {
            rootMargin: CONFIG.ROOT_MARGIN,
            threshold: CONFIG.THRESHOLD
        });

        // Find all lazy elements
        const lazyImages = document.querySelectorAll(`img[${CONFIG.DATA_ATTR}]`);
        const lazyVideos = document.querySelectorAll(`video[${CONFIG.DATA_ATTR}]`);
        const lazyBackgrounds = document.querySelectorAll(`[${CONFIG.DATA_ATTR}]:not(img):not(video)`);

        // Observe all lazy elements
        lazyImages.forEach(img => observer.observe(img));
        lazyVideos.forEach(video => observer.observe(video));
        lazyBackgrounds.forEach(bg => observer.observe(bg));

        console.log(`[LazyLoad] Initialized with ${lazyImages.length} images, ${lazyVideos.length} videos, ${lazyBackgrounds.length} backgrounds`);
    }

    /**
     * Fallback: load all images immediately
     */
    function loadAllImages() {
        const lazyImages = document.querySelectorAll(`img[${CONFIG.DATA_ATTR}]`);
        const lazyVideos = document.querySelectorAll(`video[${CONFIG.DATA_ATTR}]`);
        const lazyBackgrounds = document.querySelectorAll(`[${CONFIG.DATA_ATTR}]:not(img):not(video)`);

        lazyImages.forEach(img => loadImage(img));
        lazyVideos.forEach(video => loadVideo(video));
        lazyBackgrounds.forEach(bg => loadBackground(bg));
    }

    /**
     * Add lazy loading to dynamically added elements
     */
    function observeNewElements() {
        if (!observer) return;

        const lazyImages = document.querySelectorAll(`img[${CONFIG.DATA_ATTR}]`);
        const lazyVideos = document.querySelectorAll(`video[${CONFIG.DATA_ATTR}]`);
        const lazyBackgrounds = document.querySelectorAll(`[${CONFIG.DATA_ATTR}]:not(img):not(video)`);

        lazyImages.forEach(img => {
            if (!img.classList.contains(CONFIG.LOADED_CLASS)) {
                observer.observe(img);
            }
        });
        lazyVideos.forEach(video => {
            if (!video.classList.contains(CONFIG.LOADED_CLASS)) {
                observer.observe(video);
            }
        });
        lazyBackgrounds.forEach(bg => {
            if (!bg.classList.contains(CONFIG.LOADED_CLASS)) {
                observer.observe(bg);
            }
        });
    }

    /**
     * Initialize when DOM is ready
     */
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initLazyLoading);
        } else {
            initLazyLoading();
        }

        // Observe new elements after HTMX swaps
        document.addEventListener('htmx:afterSwap', function() {
            observeNewElements();
        });
    }

    // Initialize
    init();

    // Expose public API
    window.PwaniNetLazyLoad = {
        init: initLazyLoading,
        observeNewElements,
        loadAllImages,
        CONFIG
    };

})();
