from django.apps import AppConfig


class CommunityConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.community'

    def ready(self):
        # future signal registration or startup logic
        pass
