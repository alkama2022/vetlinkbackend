from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Import signal handlers to ensure audit logging is hooked.
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid crashing the app if signals can't be imported in tests or migrations
            pass
