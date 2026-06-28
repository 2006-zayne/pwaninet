/**
 * Post Content Manager
 * Handles text truncation and see more/see less functionality
 * 
 * Architecture:
 * - Truncates long post content
 * - Shows "See more" button for truncated content
 * - Expands inline on click
 * - Shows "See less" button when expanded
 * - Works across all post card implementations
 */

(function() {
    'use strict';

    const MAX_CHARS = 300; // Maximum characters before truncation
    const TRUNCATION_SUFFIX = '...';

    function initPostContent() {
        const contentWrappers = document.querySelectorAll('.post-content-wrapper');
        
        contentWrappers.forEach(wrapper => {
            const fullTextSpan = wrapper.querySelector('.post-content-full');
            const truncatedSpan = wrapper.querySelector('.post-content-truncated');
            const seeMoreBtn = wrapper.querySelector('.see-more-btn');
            
            if (!fullTextSpan || !truncatedSpan || !seeMoreBtn) return;
            
            const fullText = fullTextSpan.textContent.trim();
            
            // Only truncate if content is long enough
            if (fullText.length <= MAX_CHARS) {
                return; // No truncation needed
            }
            
            // Create truncated version
            const truncatedText = fullText.substring(0, MAX_CHARS - TRUNCATION_SUFFIX.length) + TRUNCATION_SUFFIX;
            truncatedSpan.textContent = truncatedText;
            
            // Show truncated version initially
            fullTextSpan.style.display = 'none';
            truncatedSpan.style.display = 'inline';
            seeMoreBtn.style.display = 'inline';
            
            // Handle see more/see less toggle
            seeMoreBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const isExpanded = fullTextSpan.style.display !== 'none';
                
                if (isExpanded) {
                    // Collapse
                    fullTextSpan.style.display = 'none';
                    truncatedSpan.style.display = 'inline';
                    seeMoreBtn.textContent = 'See more';
                } else {
                    // Expand
                    fullTextSpan.style.display = 'inline';
                    truncatedSpan.style.display = 'none';
                    seeMoreBtn.textContent = 'See less';
                }
            });
        });
        
        console.log('[PostContent] Initialized', contentWrappers.length, 'post content wrappers');
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPostContent);
    } else {
        initPostContent();
    }

    // Re-initialize when new posts are loaded (HTMX)
    document.addEventListener('htmx:afterSwap', function(event) {
        const target = event.detail.target;
        
        // Check if swap contains post content
        if (target.querySelector('.post-content-wrapper') || target.classList.contains('post-content-wrapper')) {
            setTimeout(() => {
                initPostContent();
            }, 100);
        }
    });

    // Public API
    window.PwaniNetPostContent = {
        init: initPostContent
    };

})();
