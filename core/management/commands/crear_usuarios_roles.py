"""Crea una cuenta por rol institucional y guarda las claves en un archivo local.

- administrador  -> Administrador General (superusuario)
- dirigente      -> Dirigente de Club Afiliado
- arbitro        -> Comisión Técnica / Árbitros
- tesorero       -> Tesorero / Finanzas Institucionales

Por seguridad, las contraseñas no se imprimen en la consola: se escriben en un
archivo fuera del repositorio (por defecto en Documentos). Los usuarios que ya
existen no cambian su contraseña salvo que se use --restablecer.
"""
from datetime import datetime
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from core.cache_utils import invalidar_cache
from core.roles import resolver_rol

CARACTERES = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%&*?'
LARGO_CLAVE = 16

USUARIOS = [
    {
        'username': 'administrador',
        'first_name': 'Administración',
        'last_name': 'General',
        'grupo': 'Administrador General',
        'superuser': True,
        'etiqueta': 'Administrador General de la A.F.O.',
    },
    {
        'username': 'dirigente',
        'first_name': 'Dirigente',
        'last_name': 'de Club Afiliado',
        'grupo': 'Dirigente de Club Afiliado',
        'superuser': False,
        'etiqueta': 'Dirigente de Club Afiliado',
    },
    {
        'username': 'arbitro',
        'first_name': 'Comisión',
        'last_name': 'Técnica / Árbitros',
        'grupo': 'Comisión Técnica / Árbitros',
        'superuser': False,
        'etiqueta': 'Comisión Técnica / Árbitros',
    },
    {
        'username': 'tesorero',
        'first_name': 'Tesorero',
        'last_name': 'Finanzas Institucionales',
        'grupo': 'Tesorero / Finanzas Institucionales',
        'superuser': False,
        'etiqueta': 'Tesorero / Finanzas Institucionales',
    },
]


def _ruta_por_defecto():
    documentos = Path.home() / 'Documents'
    base = documentos if documentos.exists() else Path.home()
    return base / 'AFO-credenciales.txt'


class Command(BaseCommand):
    help = 'Crea las cuentas de cada rol y guarda las contraseñas en un archivo local.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo',
            type=str,
            default=str(_ruta_por_defecto()),
            help='Ruta del archivo donde se guardan las credenciales.',
        )
        parser.add_argument(
            '--restablecer',
            action='store_true',
            help='Genera una contraseña nueva incluso para usuarios existentes.',
        )
        parser.add_argument(
            '--eliminar-legacy',
            action='store_true',
            help='Elimina la cuenta antigua "admin" si existe.',
        )

    def handle(self, *args, **options):
        ruta = Path(options['archivo']).expanduser()
        restablecer = options['restablecer']
        creados = []
        actualizados = []
        claves = {}

        for datos in USUARIOS:
            grupo, _ = Group.objects.get_or_create(name=datos['grupo'])
            usuario, creado = User.objects.get_or_create(
                username=datos['username'],
                defaults={
                    'first_name': datos['first_name'],
                    'last_name': datos['last_name'],
                    'is_active': True,
                },
            )

            usuario.first_name = datos['first_name']
            usuario.last_name = datos['last_name']
            usuario.is_active = True
            usuario.is_staff = datos['superuser']
            usuario.is_superuser = datos['superuser']
            usuario.save()

            usuario.groups.add(grupo)

            if creado or restablecer:
                clave = get_random_string(LARGO_CLAVE, CARACTERES)
                usuario.set_password(clave)
                usuario.save(update_fields=['password'])
                claves[datos['username']] = clave
                if creado:
                    creados.append(datos['username'])
                else:
                    actualizados.append(datos['username'])
            else:
                claves[datos['username']] = None

        ruta.parent.mkdir(parents=True, exist_ok=True)
        lineas = [
            'A.F.O. Oruro — Credenciales de acceso',
            f'Generado: {datetime.now():%d/%m/%Y %H:%M}',
            '',
            'Cambie cada contraseña después del primer ingreso y elimine este archivo.',
            '',
        ]
        for datos in USUARIOS:
            usuario = User.objects.get(username=datos['username'])
            clave = claves.get(datos['username'])
            lineas.extend([
                datos['etiqueta'],
                f"  Usuario: {datos['username']}",
                f"  Contraseña: {clave if clave else '(sin cambios)'}",
                f"  Rol del sistema: {resolver_rol(usuario)}",
                '',
            ])
        ruta.write_text('\n'.join(lineas), encoding='utf-8')

        eliminados = []
        if options['eliminar_legacy']:
            nuevo_admin = User.objects.filter(
                username='administrador', is_superuser=True
            ).exists()
            if not nuevo_admin:
                self.stdout.write(self.style.ERROR(
                    'No se eliminó "admin": la cuenta administrador no está lista.'
                ))
            else:
                eliminados = list(
                    User.objects.filter(username='admin')
                    .values_list('username', flat=True)
                )
                User.objects.filter(username='admin').delete()

        invalidar_cache()

        nuevas = sum(1 for valor in claves.values() if valor)
        self.stdout.write(self.style.SUCCESS(
            f'Creados: {len(creados)} | Contraseñas nuevas: {nuevas}'
        ))
        self.stdout.write('Usuarios: ' + ', '.join(d['username'] for d in USUARIOS))
        if actualizados:
            self.stdout.write('Contraseñas restablecidas: ' + ', '.join(actualizados))
        self.stdout.write(f'Credenciales guardadas en: {ruta}')
        if eliminados:
            self.stdout.write(self.style.WARNING(
                'Cuenta antigua eliminada: ' + ', '.join(eliminados)
            ))
