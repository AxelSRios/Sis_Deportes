"""Crea el Campeonato de Primera A 2026 y su rol de partidos.

Formato: liga, todos contra todos, una rueda. Cada fecha se juega los domingos
en el Estadio Jesús Bermúdez. Es idempotente: si el campeonato ya tiene
partidos, no genera duplicados.
"""
from datetime import date, datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.cache_utils import invalidar_cache
from core.models import Campeonato, Cancha, Categoria, Equipo, Partido

NOMBRE = 'Campeonato de Primera A 2026'
TEMPORADA = 2026
INICIO = date(2026, 11, 29)
HORARIOS = [time(11, 0), time(13, 0), time(15, 0), time(17, 0)]


def _round_robin(equipos):
    """Calendario todos contra todos (una rueda) con el método del círculo."""
    lista = list(equipos)
    if len(lista) % 2 == 1:
        lista.append(None)
    n = len(lista)
    rondas = []
    for ronda in range(n - 1):
        pares = []
        for i in range(n // 2):
            local = lista[i]
            visitante = lista[n - 1 - i]
            if local is None or visitante is None:
                continue
            pares.append((local, visitante) if ronda % 2 == 0 else (visitante, local))
        rondas.append(pares)
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]
    return rondas


class Command(BaseCommand):
    help = 'Crea el Campeonato de Primera A 2026 y su fixture (una rueda).'

    def handle(self, *args, **options):
        categoria, _ = Categoria.objects.get_or_create(nombre='Primera A')

        equipos = list(
            Equipo.objects.filter(
                division='Primera A',
                categoria__nombre='Primera A',
                estado='ACTIVO',
            ).order_by('nombre')
        )
        if len(equipos) < 2:
            raise SystemExit('Se necesitan al menos dos equipos de Primera A.')

        escenario = (
            Cancha.objects.filter(nombre__iexact='Estadio Jesús Bermúdez')
            .values_list('nombre', flat=True)
            .first()
            or ''
        )

        campeonato, creado = Campeonato.objects.get_or_create(
            nombre=NOMBRE,
            temporada=TEMPORADA,
            defaults={
                'categoria': categoria,
                'disciplina': 'Fútbol',
                'modalidad': 'LIGA',
                'reglamento': 'Todos contra todos, una rueda.',
                'fecha_inicio': INICIO,
                'fecha_conclusion': INICIO + timedelta(weeks=12),
                'estado': 'ACTIVO',
            },
        )

        if Partido.objects.filter(campeonato=campeonato).exists():
            self.stdout.write(self.style.WARNING(
                f'El campeonato ya tiene '
                f'{Partido.objects.filter(campeonato=campeonato).count()} partidos. '
                'No se generaron duplicados.'
            ))
            invalidar_cache()
            return

        rondas = _round_robin(equipos)
        creados = 0
        tz = timezone.get_current_timezone()

        with transaction.atomic():
            for indice_ronda, pares in enumerate(rondas):
                dia = INICIO + timedelta(weeks=indice_ronda)
                for indice, (local, visitante) in enumerate(pares):
                    inicio = datetime.combine(dia, HORARIOS[indice % len(HORARIOS)])
                    partido = Partido(
                        campeonato=campeonato,
                        equipo_local=local,
                        equipo_visitante=visitante,
                        fecha=timezone.make_aware(inicio, tz),
                        escenario=escenario,
                        estado='Programado',
                    )
                    partido.full_clean()
                    partido.save()
                    creados += 1

        invalidar_cache()

        self.stdout.write(self.style.SUCCESS(
            f'Campeonato: {campeonato.nombre} ({"creado" if creado else "existente"})'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Equipos: {len(equipos)} | Fechas: {len(rondas)} | Partidos creados: {creados}'
        ))
