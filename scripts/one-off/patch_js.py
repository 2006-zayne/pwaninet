import re

with open("documents/templates/documents/partials/document_detail_content.html", "r") as f:
    content = f.read()

# We need to remove the fetch to /download/ since serve_download handles tracking natively when the file is downloaded!
# Just let the browser do standard download via the a tag href!
# Let's remove the script that overrides download clicks.

pattern = r"// Track the download via HTMX endpoint.*?// Let the default link behavior proceed \(download the file\)"
content = re.sub(pattern, "// Tracking is now handled by the secure backend download view.", content, flags=re.DOTALL)

with open("documents/templates/documents/partials/document_detail_content.html", "w") as f:
    f.write(content)

