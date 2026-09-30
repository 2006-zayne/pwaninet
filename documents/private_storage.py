"""Private storage for student-generated documents and their previews."""

import os
import re

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage, Storage
from django.urls import reverse


class PrivateResourceStorage(Storage):
    """Storage backend that never returns a public object URL."""

    def __init__(self):
        bucket = getattr(settings, "PWANIMATE_PRIVATE_MEDIA_BUCKET", "")
        settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "").strip().lower()
        # PWANINET_ENV is the deployment intent. It can override a production
        # settings module when that module is used locally for device testing.
        environment = os.environ.get("PWANINET_ENV", "").strip().lower()
        if not environment:
            default_environment = (
                "production" if settings_module.endswith(".production")
                else getattr(settings, "APP_ENVIRONMENT", "")
            )
            environment = os.environ.get("DJANGO_ENV", default_environment).strip().lower()
        is_development = getattr(settings, "DEBUG", False) or environment in {
            "development", "dev", "local"
        }
        self.uses_s3 = bool(getattr(settings, "USE_S3", False) and bucket)
        if getattr(settings, "USE_S3", False) and not bucket and not is_development:
            raise ImproperlyConfigured(
                "Set PWANIMATE_PRIVATE_MEDIA_BUCKET to a private R2 bucket "
                "before generating Pwanimate resources in production."
            )

        if self.uses_s3:
            from storages.backends.s3boto3 import S3Boto3Storage

            self.backend = S3Boto3Storage(
                bucket_name=bucket,
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                region_name=settings.AWS_S3_REGION_NAME,
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.AWS_SECRET_ACCESS_KEY,
                location="private-resources",
                default_acl=None,
                file_overwrite=False,
                custom_domain=None,
                querystring_auth=True,
                signature_version="s3v4",
                addressing_style="path",
                client_config=settings.AWS_S3_CLIENT_CONFIG,
            )
        else:
            self.backend = FileSystemStorage(
                location=getattr(
                    settings,
                    "PWANIMATE_PRIVATE_MEDIA_ROOT",
                    os.path.join(settings.BASE_DIR, "private_media"),
                ),
                base_url=None,
            )

    def _open(self, name, mode="rb"):
        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend.save(name, content)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def size(self, name):
        return self.backend.size(name)

    def path(self, name):
        return self.backend.path(name)

    def url(self, name):
        match = re.search(r"private-documents/[^/]+/(\d+)/", name)
        if not match:
            raise ValueError("Private resource storage path has no document file ID")
        return reverse(
            "documents:private_resource_asset",
            kwargs={"file_id": int(match.group(1)), "asset": "original"},
        )


_private_storage = None


def get_private_resource_storage():
    global _private_storage
    if _private_storage is None:
        _private_storage = PrivateResourceStorage()
    return _private_storage
