import re

with open("static/js/post-content.js", "r") as f:
    text = f.read()

new_logic = """// Ensure all auto-linked URLs in posts are handled correctly for PWA/Capacitor
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
        const modalEl = document.getElementById('externalLinkModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        
        // Native handling via Capacitor if available (launches Safari/Chrome instead of in-app WebView)
        if (window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Browser) {
            window.Capacitor.Plugins.Browser.open({ url: pendingExternalUrl });
        } else {
            // Standard PWA / Web fallback
            window.open(pendingExternalUrl, '_blank', 'noopener,noreferrer');
        }
    };

    function processLinks(root) {
        const containers = root.querySelectorAll('.post-content-full, .post-content-truncated, .fst-italic');
        containers.forEach(container => {
            const links = container.querySelectorAll('a');
            links.forEach(link => {
                if (link.hostname === window.location.hostname) {
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
                            pendingExternalUrl = link.href;
                            document.getElementById('externalLinkUrl').innerText = pendingExternalUrl;
                            const modal = new bootstrap.Modal(document.getElementById('externalLinkModal'));
                            modal.show();
                        });
                    }
                }
            });
        });
    }
    
    processLinks(document);
    
    document.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target) {
            processLinks(event.detail.target);
        }
    });
});
"""

text = re.sub(r'// Ensure all auto-linked URLs in posts open in a new tab securely.*', new_logic, text, flags=re.DOTALL)

with open("static/js/post-content.js", "w") as f:
    f.write(text)
