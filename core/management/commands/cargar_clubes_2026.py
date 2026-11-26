"""Registra los clubes afiliados de la gestión 2026 en las categorías Primera A y Primera B.

Es idempotente: si un club ya existe (comparación sin distinguir mayúsculas ni
tildes), actualiza su categoría y estado en lugar de crear un duplicado.

No completa datos que no fueron proporcionados (NIT, presidente, dirección,
fundación, teléfono, correo ni documentación legal).
"""
import unicodedata

from django.core.management.base import BaseCommand
from django.db import transaction

from core.cache_utils import invalidar_cache
from core.models import Club

GESTION = 2026

CLUBES = {
    'Primera A': [
        'Empresa Minera Huanuni',
        'Club Ingenieros',
        'Deportivo Shalon',
        'Club AFIZ',
        'Oruro Royal Club',
        'Deportivo Escara',
        'Rosario Central',
        'Club Universidad',
        'Sportivo Euqueño',
        'Corque Fútbol Club',
        'FC VHSR',
        'Terrazas Fútbol Club',
        'Sajama Fútbol Club',
        'Deportivo Pomata',
    ],
    'Primera B': [
        'Club San José',
        'Club Aurora',
        'JCDT Bolivia',
        'Saavedra FC',
        'Atlético Quiroziñhos',
        'Atlético FELAP',
    ],
}

OBSERVACIONES = f'Club afiliado a la A.F.O. - Gestión {GESTION}.'


def _normalizar(texto):
    """Minúsculas, sin tildes y con espacios simples, para comparar nombres."""
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return ' '.join(texto.casefold().split())


class Command(BaseCommand):
    help = 'Carga los 20 clubes afiliados de la gestión 2026 (Primera A y Primera B).'

    def handle(self, *args, **options):
        esperados = {
            _normalizar(nombre)
            for nombres in CLUBES.values()
            for nombre in nombres
        }
        if len(esperados) != sum(len(n) for n in CLUBES.values()):
            raise SystemExit('La lista contiene nombres repetidos; se cancela la carga.')

        creados = []
        actualizados = []
        sin_cambios = []
        duplicados = []

        with transaction.atomic():
            existentes = {}
            for club in Club.objects.select_for_update().all():
                existentes.setdefault(_normalizar(club.nombre), []).append(club)

            for nombre_normalizado, clubes in existentes.items():
                if len(clubes) > 1:
                    duplicados.append([c.nombre for c in clubes])

            for categoria, nombres in CLUBES.items():
                for nombre in nombres:
                    clave = _normalizar(nombre)
                    club = (existentes.get(clave) or [None])[0]

                    if club is None:
                        club = Club(
                            nombre=nombre,
                            categoria_ingreso=categoria,
                            estado='ACTIVO',
                            observaciones=OBSERVACIONES,
                        )
                        club.full_clean()
                        club.save()
                        creados.append(nombre)
                        continue

                    cambios = []
                    if (club.categoria_ingreso or '').strip() != categoria:
                        club.categoria_ingreso = categoria
                        cambios.append('categoría')
                    if club.estado != 'ACTIVO':
                        club.estado = 'ACTIVO'
                        cambios.append('estado')
                    if not club.observaciones:
                        club.observaciones = OBSERVACIONES
                        cambios.append('observaciones')

                    if cambios:
                        club.full_clean()
                        club.save()
                        actualizados.append(f'{club.nombre} ({", ".join(cambios)})')
                    else:
                        sin_cambios.append(club.nombre)

        invalidar_cache()

        self.stdout.write(self.style.SUCCESS(
            f'Creados: {len(creados)} | Actualizados: {len(actualizados)} | '
            f'Sin cambios: {len(sin_cambios)}'
        ))
        if actualizados:
            self.stdout.write('Actualizados: ' + '; '.join(actualizados))
        if duplicados:
            self.stdout.write(self.style.WARNING(
                'Duplicados preexistentes detectados: ' + str(duplicados)
            ))
        else:
            self.stdout.write('Sin duplicados preexistentes.')
