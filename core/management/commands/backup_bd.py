"""Respaldo de la base de datos AFO con retención y bitácora.

Formatos:
  * pg_dump nativo para PostgreSQL cuando el cliente es compatible.
  * JSON comprimido (dumpdata) como respaldo lógico universal y restaurable.

Nunca se imprimen ni se escriben credenciales. El comando devuelve código de
salida distinto de cero si el respaldo no se pudo completar.
"""
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

PREFIJO = 'afo_backup_'
MANIFIESTO = 'ultimo_respaldo.json'
BITACORA = 'backup.log'


class Command(BaseCommand):
    help = 'Genera un respaldo de la base de datos con retención y bitácora.'

    def add_arguments(self, parser):
        parser.add_argument('--salida', help='Carpeta destino (por defecto AFO_BACKUP_DIR).')
        parser.add_argument('--retencion', type=int, help='Copias a conservar (por defecto AFO_BACKUP_RETENTION).')
        parser.add_argument('--formato', choices=['auto', 'json', 'pg_dump'], default='auto')
        parser.add_argument('--etiqueta', default='manual', help='Sufijo descriptivo del archivo.')
        parser.add_argument('--timeout', type=int, help='Segundos máximos para pg_dump.')
        parser.add_argument('--sin-retencion', action='store_true', help='No elimina copias antiguas.')

    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.inicio = time.monotonic()
        self.destino = Path(options.get('salida') or settings.AFO_BACKUP_DIR).expanduser().resolve()
        self.destino.mkdir(parents=True, exist_ok=True)
        self.bitacora = self.destino / BITACORA
        self.retencion = options.get('retencion') or settings.AFO_BACKUP_RETENTION
        self.timeout = options.get('timeout') or settings.AFO_BACKUP_TIMEOUT
        self.password = str(connection.settings_dict.get('PASSWORD') or '')
        self.advertencias = []
        self._limpiar_temporales()
        self._advertir_sistema_archivos()

        etiqueta = re.sub(r'[^A-Za-z0-9_-]+', '-', options.get('etiqueta') or 'manual')[:40]
        marca = timezone.localtime().strftime('%Y%m%d_%H%M%S')
        base = f'{PREFIJO}{marca}_{etiqueta}'

        formato = options.get('formato') or 'auto'
        archivo = None
        try:
            if connection.vendor == 'postgresql' and formato in {'auto', 'pg_dump'}:
                archivo = self._intentar_pg_dump(base)
            elif formato == 'pg_dump':
                raise CommandError('pg_dump solo aplica a PostgreSQL.')

            if archivo is None:
                if formato == 'pg_dump':
                    raise CommandError('No fue posible usar pg_dump y el formato fue solicitado explícitamente.')
                archivo = self._respaldo_json(base)

            datos = self._describir(archivo)
            if not options.get('sin_retencion'):
                self._aplicar_retencion(archivo)

            manifiesto = {
                'generado_en': timezone.now().isoformat(),
                'archivo': archivo.name,
                'formato': datos['formato'],
                'motor': connection.vendor,
                'bytes': datos['bytes'],
                'sha256': datos['sha256'],
                'objetos': datos.get('objetos'),
                'modelos': datos.get('modelos'),
                'advertencias': self.advertencias,
                'estado': 'OK' if not self.advertencias else 'OK_CON_ADVERTENCIA',
            }
            (self.destino / MANIFIESTO).write_text(
                json.dumps(manifiesto, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
            self._log('OK', f"{archivo.name} · {datos['bytes']} bytes · sha256 {datos['sha256'][:16]}…")
            if self.advertencias:
                self.stdout.write(self.style.WARNING('Respaldo generado con advertencias:'))
                for aviso in self.advertencias:
                    self.stdout.write(f'  · {aviso}')
            self.stdout.write(self.style.SUCCESS(
                f"Respaldo creado: {archivo} ({datos['bytes']} bytes, {datos['formato']})."
            ))
        except CommandError:
            raise
        except Exception as exc:
            self._log('ERROR', f'{type(exc).__name__}: {self._limpiar(str(exc))}')
            raise CommandError(f'No se pudo generar el respaldo: {self._limpiar(str(exc))}') from exc

    # ------------------------------------------------------------------
    def _advertir_sistema_archivos(self):
        """Avisa si el respaldo queda en un volumen sin permisos NTFS."""
        if os.name != 'nt':
            return
        try:
            import ctypes
            raiz = (self.destino.drive or '') + '\\'
            nombre = ctypes.create_unicode_buffer(261)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                raiz, None, 0, None, None, None, nombre, len(nombre),
            )
            sistema = nombre.value.upper() if ok else ''
        except Exception:
            sistema = ''
        if sistema and sistema not in {'NTFS', 'REFS'}:
            aviso = (
                f'La carpeta de respaldos está en un volumen {sistema} sin '
                'permisos NTFS; proteja el medio o mueva los respaldos a NTFS.'
            )
            self.advertencias.append(aviso)
            self._log('AVISO', aviso)

    def _limpiar_temporales(self):
        """Elimina archivos .tmp de ejecuciones interrumpidas."""
        for ruta in self.destino.glob(f'{PREFIJO}*.tmp'):
            try:
                if time.time() - ruta.stat().st_mtime > 3600:
                    ruta.unlink()
                    self._log('LIMPIEZA', f'Temporal huérfano eliminado: {ruta.name}')
            except OSError:
                pass

    def _limpiar(self, texto):
        """Evita que un mensaje de error revele la contraseña de la BD."""
        texto = str(texto or '')
        if self.password:
            texto = texto.replace(self.password, '***')
        return texto[:800]

    def _log(self, nivel, mensaje):
        linea = f'{timezone.now().isoformat()} | {nivel} | {mensaje}\n'
        try:
            with open(self.bitacora, 'a', encoding='utf-8') as archivo:
                archivo.write(linea)
        except OSError:
            pass

    def _sha256(self, ruta):
        digest = hashlib.sha256()
        with open(ruta, 'rb') as archivo:
            for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
                digest.update(bloque)
        return digest.hexdigest()

    # ------------------------------------------------------------------
    def _version_pg_dump(self, ejecutable):
        try:
            salida = subprocess.run(
                [ejecutable, '--version'],
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        coincidencia = re.search(r'(\d+)\.(\d+)', salida.stdout or '')
        if not coincidencia:
            return None
        return int(coincidencia.group(1)), int(coincidencia.group(2))

    def _version_servidor(self):
        try:
            version = int(connection.pg_version)
        except Exception:
            return None
        if version >= 100000:
            return version // 10000, version % 10000
        return version // 10000, (version % 10000) // 100

    def _intentar_pg_dump(self, base):
        ejecutable = shutil.which(settings.AFO_BACKUP_PG_DUMP) or settings.AFO_BACKUP_PG_DUMP
        if not ejecutable or not Path(ejecutable).exists():
            self.advertencias.append('pg_dump no está disponible; se usará respaldo lógico JSON.')
            return None

        cliente = self._version_pg_dump(ejecutable)
        servidor = self._version_servidor()
        if cliente and servidor and cliente < servidor:
            self.advertencias.append(
                f'pg_dump {cliente[0]}.{cliente[1]} es anterior al servidor '
                f'{servidor[0]}.{servidor[1]}; se usará respaldo lógico JSON.'
            )
            self._log('AVISO', self.advertencias[-1])
            return None

        db = connection.settings_dict
        host = db.get('HOST') or '127.0.0.1'
        puerto = str(db.get('PORT') or '5432')
        usuario = db.get('USER') or ''
        nombre = db.get('NAME') or ''
        sslmode = (db.get('OPTIONS') or {}).get('sslmode') or 'require'
        archivo = self.destino / f'{base}.dump'

        entorno = os.environ.copy()
        if self.password:
            entorno['PGPASSWORD'] = self.password
        entorno['PGSSLMODE'] = sslmode

        comando = [
            ejecutable, '--format=custom', '--compress=9',
            '--no-owner', '--no-privileges',
            '--host', host, '--port', puerto,
            '--username', usuario, '--dbname', nombre,
            '--file', str(archivo),
        ]
        self._log('INFO', f'Iniciando pg_dump hacia {archivo.name}')
        try:
            resultado = subprocess.run(
                comando, env=entorno, capture_output=True, text=True,
                timeout=self.timeout, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            archivo.unlink(missing_ok=True)
            self._log('ERROR', f'pg_dump excedió {self.timeout}s')
            self.advertencias.append('pg_dump excedió el tiempo límite; se usará JSON.')
            return None
        except OSError as exc:
            self._log('ERROR', self._limpiar(str(exc)))
            self.advertencias.append('pg_dump no pudo ejecutarse; se usará JSON.')
            return None

        if resultado.returncode != 0:
            archivo.unlink(missing_ok=True)
            lineas = (resultado.stderr or '').strip().splitlines()
            detalle = self._limpiar(lineas[-1] if lineas else 'error desconocido')
            self._log('ERROR', f'pg_dump falló: {detalle}')
            self.advertencias.append('pg_dump falló; se usará respaldo lógico JSON.')
            return None

        # Verificación estructural del archivo nativo (sin restaurar).
        pg_restore = shutil.which('pg_restore')
        if pg_restore:
            listado = subprocess.run(
                [pg_restore, '--list', str(archivo)],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if listado.returncode != 0:
                self.advertencias.append('El archivo pg_dump no pudo verificarse con pg_restore --list.')

        self._log('OK', f'pg_dump completado: {archivo.name}')
        return archivo

    # ------------------------------------------------------------------
    def _respaldo_json(self, base):
        archivo = self.destino / f'{base}.json.gz'
        temporal = archivo.with_suffix(archivo.suffix + '.tmp')
        try:
            with gzip.open(temporal, 'wt', encoding='utf-8', compresslevel=9) as salida:
                call_command('dumpdata', exclude=['sessions'], indent=1, stdout=salida)
            os.replace(temporal, archivo)
        except Exception:
            temporal.unlink(missing_ok=True)
            archivo.unlink(missing_ok=True)
            raise
        self._log('OK', f'Respaldo lógico completado: {archivo.name}')
        return archivo

    def _describir(self, archivo):
        datos = {
            'formato': 'pg_dump' if archivo.suffix == '.dump' else 'json',
            'bytes': archivo.stat().st_size,
            'sha256': self._sha256(archivo),
        }
        if datos['formato'] == 'json':
            with gzip.open(archivo, 'rt', encoding='utf-8') as entrada:
                contenido = json.load(entrada)
            if not isinstance(contenido, list) or not contenido:
                raise CommandError('El respaldo JSON quedó vacío o inválido.')
            modelos = {}
            for objeto in contenido:
                modelo = objeto.get('model') if isinstance(objeto, dict) else None
                if modelo:
                    modelos[modelo] = modelos.get(modelo, 0) + 1
            datos['objetos'] = len(contenido)
            datos['modelos'] = dict(sorted(modelos.items()))
        return datos

    # ------------------------------------------------------------------
    def _aplicar_retencion(self, actual):
        try:
            limite = max(1, int(self.retencion))
        except (TypeError, ValueError):
            limite = 14
        archivos = sorted(
            (ruta for ruta in self.destino.glob(f'{PREFIJO}*') if ruta.is_file()),
            key=lambda ruta: ruta.stat().st_mtime,
            reverse=True,
        )
        conservar = set(archivos[:limite])
        conservar.add(actual)
        for ruta in archivos:
            if ruta in conservar:
                continue
            try:
                ruta.unlink()
                self._log('RETENCION', f'Eliminado {ruta.name}')
            except OSError as exc:
                self._log('AVISO', f'No se pudo eliminar {ruta.name}: {self._limpiar(str(exc))}')
