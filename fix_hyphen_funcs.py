import re

files = [
    "posts/templates/posts/partials/post_card.html",
    "posts/templates/posts/partials/post_detail_content.html",
    "posts/templates/posts/partials/shared_post_card.html"
]

for filepath in files:
    with open(filepath, "r") as f:
        text = f.read()

    # Fix onclick function calls
    text = re.sub(r'onclick="removeUser([{}a-zA-Z_.\s]*)', r'onclick="window[\'removeUser\1\']', text)
    text = re.sub(r'onclick="removeGroup([{}a-zA-Z_.\s]*)', r'onclick="window[\'removeGroup\1\']', text)
    text = re.sub(r'onclick="removeUserShared([{}a-zA-Z_.\s]*)', r'onclick="window[\'removeUserShared\1\']', text)
    text = re.sub(r'onclick="removeGroupShared([{}a-zA-Z_.\s]*)', r'onclick="window[\'removeGroupShared\1\']', text)

    # Fix window function definitions
    text = re.sub(r"window\['removeUser'\s*\+\s*({{\s*[^}]+\s*}})\s*\]", r"window['removeUser\1']", text)
    text = re.sub(r"window\['removeGroup'\s*\+\s*({{\s*[^}]+\s*}})\s*\]", r"window['removeGroup\1']", text)
    text = re.sub(r"window\['removeUserShared'\s*\+\s*({{\s*[^}]+\s*}})\s*\]", r"window['removeUserShared\1']", text)
    text = re.sub(r"window\['removeGroupShared'\s*\+\s*({{\s*[^}]+\s*}})\s*\]", r"window['removeGroupShared\1']", text)

    with open(filepath, "w") as f:
        f.write(text)

