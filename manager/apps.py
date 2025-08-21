from django.apps import AppConfig

class ManagerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "manager"

    def ready(self):
        # import *after* Django has loaded models
        from . import signals   # noqa
