with open("documents/selectors/document_selectors.py", "r") as f:
    text = f.read()

# Replace get_document_with_relations signature and filter
text = text.replace("def get_document_with_relations(document_id: int)", "def get_document_with_relations(share_id)")
text = text.replace(".filter(id=document_id).first()", ".filter(share_id=share_id).first()")
text = text.replace("def get_document_statistics(document_id: int)", "def get_document_statistics(share_id)")
text = text.replace("Document.objects.filter(id=document_id).first()", "Document.objects.filter(share_id=share_id).first()")

with open("documents/selectors/document_selectors.py", "w") as f:
    f.write(text)
