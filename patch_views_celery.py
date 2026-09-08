import re
with open("documents/views.py", "r") as f:
    text = f.read()

text = text.replace("update_document_analytics.delay(share_id)", "update_document_analytics.delay(document.id)")

with open("documents/views.py", "w") as f:
    f.write(text)
