"""Verifica un respaldo y, opcionalmente, lo restaura en SQLite temporal.

La restauración de prueba nunca se ejecuta sobre la base de producción: crea
un archivo SQLite aislado, aplica las migraciones y carga el contenido para
comprobar que los datos y las relaciones son utilizables.
"""
import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

ALIAS = 'afo_restauracion_temporal'
ORDEN_CARGA = {
    'contenttypes.contenttype': 0,
    'auth.permission': 1,
    'auth.group': 2,
    'auth.user': 3,
    'core.club': 10,
    'core.categoria': 11,
    'core.campeonato': 12,
    'core.equipo': 13,
    'core.deportista': 14,
    'core.arbitro': 15,
    'core.partido': 16,
    'core.asignacionarbitro': 17,
    'core.inscripcion': 18,
    'core.sancion': 19,
    'core.pago': 20,
    'core.cancha': 21,
    'core.historialoperacion': 30,
    'admin.logentry': 40,
}


class Command(BaseCommand):
    help = 'Comprueba integridad y restauración de un respaldo en SQLite temporal.'

    def add_arguments(self, parser):
        parser.add_argument('--ruta', help='Archivo .json, .json.gz, .dump, .backup o .sql.')
        parser.add_argument('--restaurar', action='store_true', help='Carga el respaldo en un SQLite temporal.')
        parser.add_argument('--conservar', action='store_true', help='Conserva la base temporal para inspección.')

    def handle(self, *args, **options):
        ruta = Path(options.get('ruta') or self._ultimo()).expanduser().resolve()
        if not ruta.exists():
            raise CommandError(f'No existe el respaldo: {ruta}')

        if ruta.suffix in {'.dump', '.backup'} or ruta.name.endswith('.sql'):
            self._verificar_nativo(ruta)
            return

        texto, codificacion = self._leer_json(ruta)
        datos = json.loads(texto)
        if not isinstance(datos, list) or not datos:
            raise CommandError('El respaldo JSON está vacío o no es una lista de objetos.')

        conteo = Counter()
        for objeto in datos:
            if not isinstance(objeto, dict) or not objeto.get('model'):
                raise CommandError('El respaldo contiene un objeto sin modelo.')
            conteo[objeto['model']] += 1

        # Valida que Django pueda deserializar todos los objetos.
        objetos = list(serializers.deserialize('json', io.StringIO(texto)))
        if len(objetos) != len(datos):
            raise CommandError('La deserialización no coincide con el número de objetos.')

        self.stdout.write(self.style.SUCCESS(
            f'Respaldo válido: {ruta.name} · {len(datos)} objetos · '
            f'{len(conteo)} modelos · codificación {codificacion}.'
        ))
        for modelo, cantidad in sorted(conteo.items()):
            self.stdout.write(f'  {modelo}: {cantidad}')

        manifiesto = ruta.parent / 'ultimo_respaldo.json'
        if manifiesto.exists():
            try:
                info = json.loads(manifiesto.read_text(encoding='utf-8'))
                if info.get('archivo') == ruta.name and info.get('sha256'):
                    sha = self._sha256(ruta)
                    if sha == info['sha256']:
                        self.stdout.write(self.style.SUCCESS('SHA-256 coincide con el manifiesto.'))
                    else:
                        self.stdout.write(self.style.WARNING('El SHA-256 no coincide con el manifiesto.'))
            except (OSError, ValueError):
                self.stdout.write(self.style.WARNING('No se pudo leer el manifiesto de respaldo.'))

        if not options.get('restaurar'):
            self.stdout.write('Integridad verificada. Use --restaurar para probar la restauración aislada.')
            return

        self._restaurar(texto, conteo, options.get('conservar'))

    # ------------------------------------------------------------------
    def _ultimo(self):
        carpeta = Path(settings.AFO_BACKUP_DIR)
        candidatos = sorted(
            carpeta.glob('afo_backup_*'),
            key=lambda ruta: ruta.stat().st_mtime,
            reverse=True,
        )
        if not candidatos:
            raise CommandError('No hay respaldos en la carpeta configurada.')
        return candidatos[0]

    def _sha256(self, ruta):
        digest = hashlib.sha256()
        with open(ruta, 'rb') as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
                digest.update(bloque)
        return digest.hexdigest()

    def _leer_json(self, ruta):
        raw = ruta.read_bytes()
        if ruta.suffix == '.gz' or ruta.name.endswith('.json.gz'):
            raw = gzip.decompress(raw)
        for codificacion in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
            try:
                return raw.decode(codificacion), codificacion
            except UnicodeDecodeError:
                continue
        raise CommandError('No se pudo determinar la codificación del respaldo.')

    def _verificar_nativo(self, ruta):
        if ruta.stat().st_size == 0:
            raise CommandError('El archivo nativo está vacío.')
        pg_restore = shutil.which('pg_restore')
        if pg_restore and ruta.suffix in {'.dump', '.backup'}:
            resultado = subprocess.run(
                [pg_restore, '--list', str(ruta)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            if resultado.returncode != 0:
                raise CommandError(
                    'pg_restore no pudo leer el archivo; puede requerir una '
                    'versión de cliente compatible con el servidor.'
                )
            entradas = len([linea for linea in resultado.stdout.splitlines() if linea and not linea.startswith(';')])
            self.stdout.write(self.style.SUCCESS(
                f'Archivo nativo legible: {ruta.name} · {entradas} entradas · '
                f'{ruta.stat().st_size} bytes.'
            ))
            return
        self.stdout.write(self.style.WARNING(
            f'Archivo nativo presente ({ruta.stat().st_size} bytes). '
            'No hay pg_restore disponible para validarlo estructuralmente.'
        ))

    # ------------------------------------------------------------------
    def _restaurar(self, texto, conteo, conservar):
        temporal = tempfile.NamedTemporaryFile(suffix='.sqlite3', delete=False)
        temporal.close()
        nombre = temporal.name
        conexion = None
        try:
            connections.databases[ALIAS] = {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': nombre,
                'ATOMIC_REQUESTS': False,
                'AUTOCOMMIT': True,
                'CONN_MAX_AGE': 0,
                'CONN_HEALTH_CHECKS': False,
                'OPTIONS': {},
                'TIME_ZONE': None,
                'TEST': {'NAME': None, 'MIRROR': None, 'CHARSET': None, 'COLLATION': None},
            }
            call_command('migrate', database=ALIAS, verbosity=0, interactive=False)
            conexion = connections[ALIAS]

            # Las migraciones crean permisos y tipos de contenido. El fixture
            # también los incluye, así que se vacían antes de cargar.
            with conexion.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = OFF')
                for tabla in (
                    'auth_user_groups', 'auth_user_user_permissions',
                    'auth_group_permissions', 'auth_permission',
                    'django_content_type', 'django_admin_log',
                ):
                    try:
                        cursor.execute(f'DELETE FROM {tabla}')
                    except Exception:
                        pass

            objetos = list(serializers.deserialize('json', io.StringIO(texto), using=ALIAS))
            objetos.sort(key=lambda obj: ORDEN_CARGA.get(obj.object._meta.label_lower, 50))
            for obj in objetos:
                obj.save(using=ALIAS)

            fallos = []
            for modelo, esperado in conteo.items():
                try:
                    clase = apps.get_model(modelo)
                    obtenido = clase._default_manager.using(ALIAS).count()
                except LookupError:
                    fallos.append(f'{modelo}: modelo no existe')
                    continue
                if obtenido != esperado:
                    fallos.append(f'{modelo}: esperado {esperado}, restaurado {obtenido}')

            with conexion.cursor() as cursor:
                cursor.execute('PRAGMA foreign_key_check')
                violaciones = cursor.fetchall()

            if fallos or violaciones:
                detalle = '; '.join(fallos) if fallos else ''
                if violaciones:
                    detalle += f'; {len(violaciones)} violaciones de clave foránea'
                raise CommandError(f'La restauración de prueba falló: {detalle}')

            self.stdout.write(self.style.SUCCESS(
                f'Restauración verificada en SQLite temporal: {len(objetos)} objetos, '
                f'{len(conteo)} modelos, sin violaciones de integridad.'
            ))
        finally:
            try:
                if conexion is not None:
                    conexion.close()
            except Exception:
                pass
            try:
                del connections.databases[ALIAS]
            except Exception:
                pass
            if not conservar:
                try:
                    os.unlink(nombre)
                except OSError:
                    pass
            else:
                self.stdout.write(f'Base temporal conservada en: {nombre}')
