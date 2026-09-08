import re

with open("documents/templates/documents/partials/document_detail_content.html", "r") as f:
    text = f.read()

# Fix inline onclick handlers
text = text.replace("onclick=\"copyLink({{ document.share_id }})\"", "onclick=\"copyLink('{{ document.share_id }}')\"")
text = text.replace("onclick=\"shareToProfile({{ document.share_id }})\"", "onclick=\"shareToProfile('{{ document.share_id }}')\"")
text = text.replace("onclick=\"shareToGroup({{ document.share_id }})\"", "onclick=\"shareToGroup('{{ document.share_id }}')\"")

# Fix executeGroupShare in JS
text = text.replace("onclick=\"executeGroupShare(${documentId}, ${group.id}, this)\"", "onclick=\"executeGroupShare('${documentId}', ${group.id}, this)\"")

# Also check trackAndDownload
text = text.replace("onclick=\"trackAndDownload(event, {{ document.share_id }},", "onclick=\"trackAndDownload(event, '{{ document.share_id }}',")

with open("documents/templates/documents/partials/document_detail_content.html", "w") as f:
    f.write(text)
