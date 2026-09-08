from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        import logging
        from importlib import import_module
        logger = logging.getLogger(__name__)
        try:
            import_module('notifications.signals')
            import_module('notifications.event_processor')
        except Exception as exc:
            logger.error(f"Failed to import notification modules in ready(): {exc}")
