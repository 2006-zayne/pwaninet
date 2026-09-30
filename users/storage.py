"""Profile-picture storage with the bundled avatar served as a static asset."""

from django.core.files.storage import Storage, default_storage
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.deconstruct import deconstructible


DEFAULT_AVATAR_NAME = 'profile_pic/default_pic1.jpg'
DEFAULT_AVATAR_STATIC_NAME = 'images/default_pic1.jpg'


@deconstructible
class ProfilePictureStorage(Storage):
    """Delegate uploads to the configured media backend; keep the default in Git static assets."""

    def _is_default_avatar(self, name):
        return name == DEFAULT_AVATAR_NAME

    def _open(self, name, mode='rb'):
        if self._is_default_avatar(name):
            return staticfiles_storage.open(DEFAULT_AVATAR_STATIC_NAME, mode)
        return default_storage.open(name, mode)

    def _save(self, name, content):
        return default_storage.save(name, content)

    def _delete(self, name):
        if not self._is_default_avatar(name):
            default_storage.delete(name)

    def exists(self, name):
        if self._is_default_avatar(name):
            return True
        return default_storage.exists(name)

    def listdir(self, path):
        return default_storage.listdir(path)

    def size(self, name):
        if self._is_default_avatar(name):
            return staticfiles_storage.size(DEFAULT_AVATAR_STATIC_NAME)
        return default_storage.size(name)

    def url(self, name):
        if self._is_default_avatar(name):
            return staticfiles_storage.url(DEFAULT_AVATAR_STATIC_NAME)
        return default_storage.url(name)

    def path(self, name):
        if self._is_default_avatar(name):
            return staticfiles_storage.path(DEFAULT_AVATAR_STATIC_NAME)
        return default_storage.path(name)

    def __getattr__(self, name):
        return getattr(default_storage, name)
