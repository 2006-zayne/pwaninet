with open("pwaninet/urls.py", "r") as f:
    text = f.read()

import re

new_apk = """
from django.core.signing import TimestampSigner, BadSignature
from django.http import FileResponse, HttpResponseForbidden, HttpResponseRedirect
import logging

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "HEAD"])
def download_android_apk(request):
    \"\"\"
    Version-agnostic mobile download controller.
    Abstracts storage paths, records request telemetry, resolves the latest production release,
    and gates access via signed tokens if marked private or beta.
    \"\"\"
    # Telemetry logging
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    logger.info(f"Mobile app download requested by IP: {ip_address}, User-Agent: {user_agent}")
    
    is_beta_or_private = getattr(settings, 'APK_IS_BETA', False)
    
    if is_beta_or_private:
        token = request.GET.get('token')
        if not token:
            return HttpResponseForbidden("This is a private/beta release. Download token required.")
        signer = TimestampSigner()
        try:
            # Token expires in 1 hour
            data = signer.unsign_object(token, max_age=3600)
        except BadSignature:
            return HttpResponseForbidden("Invalid or expired download token.")
    
    github_url = getattr(settings, 'APK_DOWNLOAD_URL', 'https://github.com/2006-zayne/pwaninet/releases/latest/download/pwaninet.apk')
    
    if getattr(settings, 'REDIRECT_APK_TO_GITHUB', True) and not getattr(settings, 'DEBUG', False):
        return HttpResponseRedirect(github_url)
    
    import os
    local_candidates = [
        os.path.join(settings.BASE_DIR, 'media', 'downloads', 'pwaninet.apk'),
        os.path.join(settings.BASE_DIR, 'android', 'app', 'build', 'outputs', 'apk', 'release', 'app-release.apk'),
    ]
    for apk_path in local_candidates:
        if os.path.exists(apk_path) and os.path.getsize(apk_path) > 0:
            return FileResponse(
                open(apk_path, 'rb'),
                as_attachment=True,
                filename='pwaninet.apk',
                content_type='application/vnd.android.package-archive'
            )
            
    return HttpResponseRedirect(github_url)
"""

pattern = r"@require_http_methods\(\[\"GET\", \"HEAD\"\]\)\ndef download_android_apk\(request\):.*?return HttpResponseRedirect\(github_url\)"
text = re.sub(pattern, new_apk.strip(), text, flags=re.DOTALL)

text = text.replace("path('download/android/', download_android_apk, name='download_android_apk')", "path('download/app/latest/', download_android_apk, name='download_android_apk')")

with open("pwaninet/urls.py", "w") as f:
    f.write(text)
