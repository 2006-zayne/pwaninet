import re

with open("documents/views.py", "r") as f:
    content = f.read()

# Replace track_download with serve_download logic
download_view = """
from django.core.signing import TimestampSigner, BadSignature
from django.http import FileResponse, HttpResponseForbidden, HttpResponseNotFound

def serve_download(request, share_id):
    \"\"\"
    Endpoint for secure, token-gated document downloads.
    \"\"\"
    token = request.GET.get('t')
    if not token:
        return HttpResponseForbidden("Missing download token.")
        
    signer = TimestampSigner()
    try:
        # Verify token, expires in 24 hours (86400 seconds)
        data = signer.unsign_object(token, max_age=86400)
    except BadSignature:
        return HttpResponseForbidden("Invalid or expired download token.")
        
    try:
        document = Document.objects.get(share_id=share_id)
        
        from .engagement.models import DocumentDownload
        from .models import DocumentFile
        
        file_id = request.GET.get('file_id')
        document_file = DocumentFile.objects.get(id=file_id) if file_id else document.latest_version.files.first()
        
        if not document_file:
            return HttpResponseNotFound("File not found.")
            
        # Create download record
        DocumentDownload.objects.create(
            document=document,
            document_file=document_file,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )
        
        # Invalidate cache
        from django.core.cache import cache
        cache.delete(f'doc_download_count_{share_id}')
        
        # Stream file securely
        import mimetypes
        content_type, _ = mimetypes.guess_type(document_file.file.name)
        response = FileResponse(document_file.file.open('rb'), content_type=content_type or 'application/octet-stream')
        filename = f"{document.title}.{document_file.extension}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Document.DoesNotExist:
        return HttpResponseNotFound("Document not found")
    except Exception as e:
        return HttpResponseForbidden(f"Download failed: {str(e)}")
"""

content = re.sub(r'def track_download\(request, share_id\):.*?(?=\n\n\n|\n@)', download_view.strip(), content, flags=re.DOTALL)

with open("documents/views.py", "w") as f:
    f.write(content)

