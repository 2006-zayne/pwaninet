/**
 * Post Content Manager
 * Handles text truncation and see more/see less functionality
 * 
 * Architecture:
 * - Truncates long post content (> 200 characters)
 * - Shows "See more" button for truncated content
 * - Expands inline on click
 * - Shows "See less" button when expanded
 * - Uses delegated event handling to guarantee no duplicate listeners and full HTMX compatibility
 */

(function() {
    'use strict';

    const MAX_CHARS = 200; // Maximum characters before truncation
    const TRUNCATION_SUFFIX = '...';

    function truncateWrapper(wrapper) {
        const fullTextSpan = wrapper.querySelector('.post-content-full');
        const truncatedSpan = wrapper.querySelector('.post-content-truncated');
        const seeMoreBtn = wrapper.querySelector('.see-more-btn');
        
        if (!fullTextSpan || !truncatedSpan || !seeMoreBtn) return;
        
        // Cache original text so re-truncation doesn't lose content
        if (!wrapper._fullText) {
            wrapper._fullText = fullTextSpan.textContent.trim();
        }
        const fullText = wrapper._fullText;
        
        // Only truncate if content is long enough
        if (fullText.length <= MAX_CHARS) {
            fullTextSpan.style.display = 'inline';
            truncatedSpan.style.display = 'none';
            seeMoreBtn.style.display = 'none';
            return;
        }
        
        // Create truncated version if not already set
        if (!truncatedSpan.textContent) {
            const truncatedText = fullText.substring(0, MAX_CHARS) + TRUNCATION_SUFFIX;
            truncatedSpan.textContent = truncatedText;
        }
        
        // Respect existing expanded state (or check sessionStorage)
        const postId = wrapper.dataset.postId;
        const isSavedExpanded = postId && sessionStorage.getItem(`post-expanded-${postId}`) === 'true';
        const isCurrentlyExpanded = fullTextSpan.style.display === 'inline' || isSavedExpanded;
        
        if (isCurrentlyExpanded) {
            fullTextSpan.style.display = 'inline';
            truncatedSpan.style.display = 'none';
            seeMoreBtn.textContent = 'See less';
            seeMoreBtn.style.display = 'inline';
        } else {
            fullTextSpan.style.display = 'none';
            truncatedSpan.style.display = 'inline';
            seeMoreBtn.textContent = 'See more';
            seeMoreBtn.style.display = 'inline';
        }
    }

    function initPostContent(root) {
        const container = root instanceof Element || root instanceof Document ? root : document;
        const wrappers = container.querySelectorAll ? container.querySelectorAll('.post-content-wrapper') : [];
        wrappers.forEach(truncateWrapper);
        if (container.classList && container.classList.contains('post-content-wrapper')) {
            truncateWrapper(container);
        }
    }

    // Single delegated click listener on document handles all current and future see-more-btn clicks
    document.addEventListener('click', function(e) {
        const seeMoreBtn = e.target.closest('.see-more-btn');
        if (!seeMoreBtn) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const wrapper = seeMoreBtn.closest('.post-content-wrapper');
        if (!wrapper) return;
        
        const fullTextSpan = wrapper.querySelector('.post-content-full');
        const truncatedSpan = wrapper.querySelector('.post-content-truncated');
        if (!fullTextSpan || !truncatedSpan) return;
        
        const postId = wrapper.dataset.postId;
        const isCurrentlyExpanded = fullTextSpan.style.display !== 'none';
        
        if (isCurrentlyExpanded) {
            // Collapse
            fullTextSpan.style.display = 'none';
            truncatedSpan.style.display = 'inline';
            seeMoreBtn.textContent = 'See more';
            if (postId) sessionStorage.setItem(`post-expanded-${postId}`, 'false');
        } else {
            // Expand
            fullTextSpan.style.display = 'inline';
            truncatedSpan.style.display = 'none';
            seeMoreBtn.textContent = 'See less';
            if (postId) sessionStorage.setItem(`post-expanded-${postId}`, 'true');
        }
    });

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initPostContent(document);
        });
    } else {
        initPostContent(document);
    }

    // Re-initialize when new posts are loaded (HTMX)
    document.addEventListener('htmx:afterSwap', function(event) {
        const target = event.detail.target;
        if (target) {
            setTimeout(function() {
                initPostContent(target);
            }, 50);
        }
    });

    document.addEventListener('htmx:load', function(event) {
        const elt = event.detail.elt;
        if (elt) {
            initPostContent(elt);
        }
    });

    // Public API
    window.PwaniNetPostContent = {
        init: initPostContent
    };

})();
