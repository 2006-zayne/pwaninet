from django.apps import AppConfig


class GroupsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'groups'

    def ready(self):
        """Import tasks and signals when app is ready"""
        try:
            import groups.tasks
        except ImportError:
            pass
        import groups.signals
