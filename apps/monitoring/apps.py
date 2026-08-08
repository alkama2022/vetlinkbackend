from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monitoring'
    verbose_name = 'Monitoring'

    def ready(self):
        from apps.monitoring import signals  # noqa: F401
        signals.register_monitoring_signals()
