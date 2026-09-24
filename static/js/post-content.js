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

    // Single delegated click listener on document handles all current and future see-more-btn clicks
    document.addEventListener('click', function(e) {
        const seeMoreBtn = e.target.closest('.see-more-btn');
        if (!seeMoreBtn) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const wrapper = seeMoreBtn.closest('.post-content-wrapper');
        if (!wrapper) return;
        
        const textBody = wrapper.querySelector('.post-text-body');
        if (!textBody) return;
        
        const isExpanded = textBody.classList.toggle('is-expanded');
        seeMoreBtn.textContent = isExpanded ? 'See less' : 'See more';
        seeMoreBtn.setAttribute('aria-expanded', isExpanded);
    });

    // Public API
    window.PwaniNetPostContent = {
        init: function() {}
    };

})();

// Ensure all auto-linked URLs in posts are handled correctly for PWA/Capacitor
document.addEventListener('DOMContentLoaded', function() {
    // 1. Inject the External Link Warning Modal if it doesn't exist
    if (!document.getElementById('externalLinkModal')) {
        const modalHtml = `
        <div class="modal fade" id="externalLinkModal" tabindex="-1" aria-labelledby="externalLinkModalLabel" aria-hidden="true" style="z-index: 1060;">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header border-0 pb-0">
                        <h5 class="modal-title fw-bold" id="externalLinkModalLabel">External Link</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body text-center py-4">
                        <i class="bi bi-box-arrow-up-right text-primary mb-3" style="font-size: 2.5rem;"></i>
                        <p class="mb-2">You are about to leave PwaniNet and visit an external website:</p>
                        <p class="mb-4"><strong id="externalLinkUrl" style="word-break: break-all; color: var(--bs-primary);"></strong></p>
                        <p class="text-muted small mb-0">Are you sure you want to proceed?</p>
                    </div>
                    <div class="modal-footer border-0 pt-0 d-flex justify-content-between">
                        <button type="button" class="btn btn-outline-secondary" onclick="copyExternalLink()">Copy Link</button>
                        <div>
                            <button type="button" class="btn btn-light" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary px-4" onclick="proceedToExternalLink()">Open</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    let pendingExternalUrl = '';

    window.copyExternalLink = function() {
        if (pendingExternalUrl) {
            if (window.copyLinkToClipboard) {
                window.copyLinkToClipboard(pendingExternalUrl);
            } else if (navigator.clipboard) {
                navigator.clipboard.writeText(pendingExternalUrl);
                alert("Link copied!");
            }
        }
    };

    window.proceedToExternalLink = function() {
        if (!pendingExternalUrl) return;
        const targetUrl = pendingExternalUrl;
        const modalEl = document.getElementById('externalLinkModal');
        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
        }
        
        // 1. In Capacitor Android native wrapper, launch via AndroidBridge / PwaninetBridge
        const bridge = window.AndroidBridge || window.PwaninetBridge;
        if (bridge && typeof bridge.openExternalUrl === 'function') {
            bridge.openExternalUrl(targetUrl);
            return;
        }

        // 2. If Capacitor Browser plugin is installed
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Browser) {
            window.Capacitor.Plugins.Browser.open({ url: targetUrl });
            return;
        }

        // 3. Web / PWA fallback: open in external browser tab
        window.open(targetUrl, '_blank', 'noopener,noreferrer');
    };

    function processLinks(root) {
        // Target all links inside posts, comments, and shared messages
        const links = root.querySelectorAll ? root.querySelectorAll('.post-content-wrapper a, .post-content-text a, a:not([class])') : [];
        links.forEach(link => {
            if (!link.href || link.href.startsWith('javascript:')) return;

            // Check if internal link
            const isInternal = link.hostname === window.location.hostname || 
                               link.hostname.endsWith('pwaninet.app') ||
                               link.hostname === 'localhost' ||
                               link.hostname === '127.0.0.1';

            if (isInternal) {
                // Internal links should route normally within the app
                link.removeAttribute('target');
            } else {
                // External links - intercept click
                link.removeAttribute('target'); // Remove generic targets
                // Prevent duplicate listeners
                if (!link.hasAttribute('data-external-handled')) {
                    link.setAttribute('data-external-handled', 'true');
                    link.addEventListener('click', function(e) {
                        e.preventDefault();
                        e.stopPropagation();
                        pendingExternalUrl = link.href;
                        const urlEl = document.getElementById('externalLinkUrl');
                        if (urlEl) urlEl.innerText = pendingExternalUrl;
                        const modalEl = document.getElementById('externalLinkModal');
                        if (modalEl && window.bootstrap && window.bootstrap.Modal) {
                            const modal = new bootstrap.Modal(modalEl);
                            modal.show();
                        } else {
                            window.proceedToExternalLink();
                        }
                    });
                }
            }
        });
    }
    
    processLinks(document);
    
    document.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target) {
            processLinks(event.detail.target);
        }
    });
});
