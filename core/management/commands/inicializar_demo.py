"""
Inicializa las cuentas institucionales del sistema A.F.O.

Las contraseñas se generan al azar y se guardan en un archivo local fuera del
repositorio (ver el comando crear_usuarios_roles). No se usan claves débiles
por defecto.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea los grupos y las cuentas por rol con contraseñas seguras.'

    def handle(self, *args, **options):
        call_command('crear_usuarios_roles', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            'Cuentas institucionales inicializadas correctamente.'
        ))
