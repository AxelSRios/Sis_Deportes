"""Programa el respaldo automático con el Programador de tareas de Windows.

La tarea ejecuta scripts/backup_afo.bat con el usuario actual. Para que se
ejecute con la sesión cerrada se debe crear con una cuenta de servicio; el
comando evita solicitar o almacenar contraseñas.
"""
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Crea, consulta o elimina la tarea programada de respaldo AFO.'

    def add_arguments(self, parser):
        parser.add_argument('--nombre', default='AFO Backup BD')
        parser.add_argument('--hora', default='02:00', help='Hora diaria HH:MM (por defecto 02:00).')
        parser.add_argument('--cada-horas', type=int, default=0, help='Si es mayor que 0, programa cada N horas.')
        parser.add_argument('--estado', action='store_true', help='Consulta la tarea existente.')
        parser.add_argument('--ejecutar', action='store_true', help='Ejecuta la tarea ahora.')
        parser.add_argument('--eliminar', action='store_true', help='Elimina la tarea.')

    def handle(self, *args, **options):
        nombre = options['nombre']
        if options['estado']:
            self._consultar(nombre)
            return
        if options['eliminar']:
            self._schtasks(['/Delete', '/TN', nombre, '/F'], 'No se pudo eliminar la tarea.')
            self.stdout.write(self.style.SUCCESS(f'Tarea eliminada: {nombre}'))
            return
        if options['ejecutar']:
            self._schtasks(['/Run', '/TN', nombre], 'No se pudo ejecutar la tarea.')
            self.stdout.write(self.style.SUCCESS(f'Tarea iniciada: {nombre}'))
            return

        script = Path(settings.BASE_DIR) / 'scripts' / 'backup_afo.bat'
        if not script.exists():
            raise CommandError(f'No existe el script de respaldo: {script}')

        comando = [
            '/Create', '/TN', nombre, '/TR', str(script),
            '/F', '/RL', 'LIMITED',
        ]
        if options['cada_horas'] and options['cada_horas'] > 0:
            comando += ['/SC', 'HOURLY', '/MO', str(options['cada_horas'])]
            if options.get('hora'):
                comando += ['/ST', options['hora']]
            frecuencia = f'cada {options["cada_horas"]} hora(s)'
        else:
            comando += ['/SC', 'DAILY', '/ST', options['hora']]
            frecuencia = f'diariamente a las {options["hora"]}'

        self._schtasks(comando, 'No se pudo crear la tarea programada.')
        self._configurar_energia(nombre)
        self.stdout.write(self.style.SUCCESS(
            f'Tarea creada: {nombre} · {frecuencia} · script {script.name}'
        ))
        self.stdout.write(
            'La tarea se ejecuta con el usuario actual. Si el equipo está apagado '
            'o la sesión cerrada, Windows no la ejecutará; para un servidor use una '
            'cuenta de servicio con permisos sobre la carpeta de respaldos.'
        )
        self._consultar(nombre)

    def _configurar_energia(self, nombre):
        """Permite que la tarea continúe en portátiles con batería."""
        nombre_seguro = nombre.replace("'", "''")
        script = (
            "$ErrorActionPreference='Stop';"
            "$s=New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries "
            "-DontStopIfGoingOnBatteries -StartWhenAvailable "
            "-ExecutionTimeLimit (New-TimeSpan -Hours 2);"
            f"Set-ScheduledTask -TaskName '{nombre_seguro}' -Settings $s | Out-Null"
        )
        try:
            resultado = subprocess.run(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script],
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            self.stdout.write(self.style.WARNING(
                'No se pudieron ajustar las opciones de energía de la tarea.'
            ))
            return
        if resultado.returncode != 0:
            self.stdout.write(self.style.WARNING(
                'La tarea se creó, pero Windows no permitió ajustar las opciones de batería.'
            ))

    def _schtasks(self, argumentos, mensaje):
        try:
            resultado = subprocess.run(
                ['schtasks'] + argumentos,
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise CommandError(f'{mensaje} {exc}') from exc
        if resultado.returncode != 0:
            detalle = (resultado.stderr or resultado.stdout or '').strip()
            raise CommandError(f'{mensaje} {detalle[:500]}')
        return resultado

    def _consultar(self, nombre):
        resultado = subprocess.run(
            ['schtasks', '/Query', '/TN', nombre, '/V', '/FO', 'LIST'],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if resultado.returncode != 0:
            self.stdout.write(self.style.WARNING(f'La tarea «{nombre}» no existe o no se puede consultar.'))
            return
        for linea in resultado.stdout.splitlines():
            texto = linea.strip()
            if not texto:
                continue
            if any(clave in texto for clave in (
                'Nombre de tarea', 'TaskName', 'Estado', 'Status',
                'Última ejecución', 'Last Run Time', 'Último resultado',
                'Last Result', 'Próxima ejecución', 'Next Run Time',
            )):
                self.stdout.write(texto)
