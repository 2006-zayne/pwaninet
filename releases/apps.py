from django.apps import AppConfig


class ReleasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'releases'
    verbose_name = 'Release Management'

    def ready(self):
        """Import signals when the app is ready."""
        import releases.signals
