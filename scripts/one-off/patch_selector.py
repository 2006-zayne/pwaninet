import re

with open("static/js/post-content.js", "r") as f:
    text = f.read()

new_logic = """
    function processLinks(root) {
        // Target all links inside posts, comments, and shared messages
        // User-generated links from Django's urlize don't have CSS classes.
        const links = root.querySelectorAll('a:not([class])');
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
    }
"""

text = re.sub(r'    function processLinks\(root\) \{.*?(?=    \n    processLinks\(document\);)', new_logic, text, flags=re.DOTALL)

with open("static/js/post-content.js", "w") as f:
    f.write(text)
