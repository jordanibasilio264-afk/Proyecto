from django.apps import AppConfig


class AuditoriaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.Auditoria"

    def ready(self):
        print(">>> signals de Auditoria cargadas")
        from . import signals  # noqa: F401