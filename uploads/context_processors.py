from django.conf import settings


def upload_flags(request):
    return {
        "USE_RESUMABLE_UPLOADS": True,  # Always enabled by default
    }
