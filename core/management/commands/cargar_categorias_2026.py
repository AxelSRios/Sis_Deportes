"""Crea las categorías base de la gestión 2026.

La categoría es un dato propio del equipo (un club puede tener equipos en
distintas categorías). Es idempotente: no duplica las existentes.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.cache_utils import invalidar_cache
from core.models import Categoria

CATEGORIAS = ['Primera A', 'Primera B']


class Command(BaseCommand):
    help = 'Crea las categorías Primera A y Primera B si no existen.'

    def handle(self, *args, **options):
        creadas = []
        existentes = []
        with transaction.atomic():
            for nombre in CATEGORIAS:
                categoria = Categoria.objects.filter(nombre__iexact=nombre).first()
                if categoria is not None:
                    existentes.append(categoria.nombre)
                    continue
                categoria = Categoria(nombre=nombre)
                categoria.full_clean()
                categoria.save()
                creadas.append(categoria.nombre)

        invalidar_cache()
        self.stdout.write(self.style.SUCCESS(
            f'Creadas: {len(creadas)} | Ya existían: {len(existentes)}'
        ))
        if creadas:
            self.stdout.write('Nuevas: ' + ', '.join(creadas))
        if existentes:
            self.stdout.write('Existentes: ' + ', '.join(existentes))
