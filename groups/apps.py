from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'groups'

    def ready(self):
        """Import tasks when app is ready to register with Celery"""
        try:
            import groups.tasks
        except ImportError:
            pass
