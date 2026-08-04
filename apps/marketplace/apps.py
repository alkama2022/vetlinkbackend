from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.marketplace'
    verbose_name = 'Marketplace'

    def ready(self):
        # register signals
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
