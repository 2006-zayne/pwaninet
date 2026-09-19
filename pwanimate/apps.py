from django.apps import AppConfig
from pwanimate.version import __version__


class PwanimateConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pwanimate'
    verbose_name = 'Pwanimate AI & Context'
    version = __version__
