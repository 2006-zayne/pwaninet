from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'documents'
    verbose_name = 'Document Repository'
    
    def ready(self):
        """Import signal handlers when app is ready."""
        import documents.signals.handlers
