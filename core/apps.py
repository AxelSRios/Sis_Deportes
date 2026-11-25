from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'

    def ready(self):
        # Conecta las señales de autenticación al registro de accesos.
        from . import signals  # noqa: F401
