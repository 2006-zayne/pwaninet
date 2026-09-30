import re

with open("documents/views.py", "r") as f:
    content = f.read()

# Add download token logic
patch = """
    # Generate download token
    from django.core.signing import TimestampSigner
    signer = TimestampSigner()
    download_token = signer.sign_object(str(document.share_id))
    
    context = {
        'page_title': document.title,
        'download_token': download_token,
"""

content = re.sub(r'context = \{\n\s+\'page_title\': document.title,', patch, content)

with open("documents/views.py", "w") as f:
    f.write(content)
