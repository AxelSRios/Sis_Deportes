"""Crea equipos y nóminas para los clubes de la gestión 2026.

Por cada club:
  - Un equipo principal en la división del club (Primera A o Primera B).
  - Un equipo juvenil con categoría elegida al azar entre Sub 15 y Sub 19.
  - Cada equipo recibe entre 15 y 22 jugadores ficticios.

Los datos personales son inventados (nombres, CI y teléfonos de demostración).
"""
import random
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.cache_utils import invalidar_cache
from core.models import Categoria, Club, Deportista, Equipo

TEMPORADA = 2026
SEMILLA = 2026

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

CATEGORIAS_JUVENILES = ['Sub 15', 'Sub 19']

NOMBRES_M = [
    'José', 'Luis', 'Carlos', 'Juan', 'Miguel', 'Pedro', 'Jorge', 'Roberto',
    'Fernando', 'Ricardo', 'Álvaro', 'Sergio', 'Marco Antonio', 'Diego',
    'Óscar', 'Hugo', 'Ramiro', 'Iván', 'Raúl', 'Gonzalo', 'Wilson', 'Edwin',
    'Freddy', 'Ronald', 'Jhonny',
]

NOMBRES_F = [
    'María', 'Ana', 'Silvia', 'Rocío', 'Fernanda', 'Carla', 'Lucía', 'Daniela',
    'Gabriela', 'Paola', 'Andrea', 'Valeria', 'Camila', 'Natalia', 'Verónica',
    'Mónica', 'Patricia', 'Claudia', 'Eliana', 'Maribel', 'Karen', 'Sandra',
    'Rina', 'Gladys', 'Lizeth',
]

APELLIDOS = [
    'Mamani', 'Quispe', 'Condori', 'Choque', 'Flores', 'Vargas', 'Rojas',
    'Céspedes', 'Aguilar', 'Colque', 'Ticona', 'Apaza', 'Calla', 'Huanca',
    'López', 'Gutiérrez', 'Paredes', 'Torrez', 'Nina', 'Limachi', 'Cáceres',
    'Villarroel', 'Escobar', 'Arce', 'Zenteno', 'Salazar', 'Ibáñez', 'Méndez',
    'Loayza', 'Sánchez', 'Riveros', 'Orellana', 'Bustamante', 'Ríos',
    'Villca', 'Véliz', 'Fernández', 'Callisaya', 'Choqueticlla',
]

EDADES = {
    'Sub 15': (13, 15),
    'Sub 19': (16, 19),
    'Primera A': (20, 30),
    'Primera B': (20, 30),
}


class Command(BaseCommand):
    help = 'Crea equipos por club y nóminas de 15 a 22 jugadores (gestión 2026).'

    def handle(self, *args, **options):
        random.seed(SEMILLA)
        rng = random.Random(SEMILLA)

        categorias = {}
        for nombre in list(CLUBES) + CATEGORIAS_JUVENILES:
            categoria, _ = Categoria.objects.get_or_create(nombre=nombre)
            categorias[nombre] = categoria

        faltantes = []
        equipos_creados = 0
        equipos_existentes = 0
        jugadores_creados = 0
        secuencia_ci = 80000000
        secuencia_tel = 70000000

        with transaction.atomic():
            for division, nombres in CLUBES.items():
                for nombre_club in nombres:
                    club = Club.objects.filter(nombre__iexact=nombre_club).first()
                    if club is None:
                        faltantes.append(nombre_club)
                        continue

                    # Equipo principal en la división del club.
                    principal, creado = Equipo.objects.get_or_create(
                        club=club,
                        nombre=f'{club.nombre} {division}',
                        defaults={
                            'categoria': categorias[division],
                            'division': division,
                            'temporada': TEMPORADA,
                            'entrenador': '',
                            'estado': 'ACTIVO',
                        },
                    )
                    if creado:
                        equipos_creados += 1
                    else:
                        equipos_existentes += 1

                    # Equipo juvenil: categoría al azar (solo uno por club).
                    juveniles = Equipo.objects.filter(
                        club=club,
                        nombre__in=[
                            f'{club.nombre} {categoria}'
                            for categoria in CATEGORIAS_JUVENILES
                        ],
                    )
                    juvenil = juveniles.first()
                    if juvenil is None:
                        categoria_j = rng.choice(CATEGORIAS_JUVENILES)
                        juvenil, creado_j = Equipo.objects.get_or_create(
                            club=club,
                            nombre=f'{club.nombre} {categoria_j}',
                            defaults={
                                'categoria': categorias[categoria_j],
                                'division': division,
                                'temporada': TEMPORADA,
                                'entrenador': '',
                                'estado': 'ACTIVO',
                            },
                        )
                        if creado_j:
                            equipos_creados += 1
                    else:
                        equipos_existentes += 1

                    for equipo in (principal, juvenil):
                        existentes = equipo.deportista_set.count()
                        if existentes >= 15:
                            continue
                        objetivo = rng.randint(15, 22)

                        for _ in range(objetivo - existentes):
                            secuencia_ci += 1
                            ci = f'{secuencia_ci}-OR'
                            while Deportista.objects.filter(ci=ci).exists():
                                secuencia_ci += 1
                                ci = f'{secuencia_ci}-OR'

                            secuencia_tel += 1
                            genero = rng.choice(['M', 'F'])
                            nombre_pila = rng.choice(
                                NOMBRES_M if genero == 'M' else NOMBRES_F
                            )
                            apellido = rng.choice(APELLIDOS)
                            edad_min, edad_max = EDADES[equipo.categoria.nombre]
                            edad = rng.randint(edad_min, edad_max)
                            nacimiento = date(
                                2026 - edad,
                                rng.randint(1, 12),
                                rng.randint(1, 28),
                            )

                            jugador = Deportista(
                                nombre=nombre_pila,
                                apellido=apellido,
                                ci=ci,
                                fecha_nacimiento=nacimiento,
                                genero=genero,
                                telefono=f'+591{secuencia_tel:08d}',
                                direccion='Oruro, Bolivia',
                                club=club,
                                equipo=equipo,
                                categoria=equipo.categoria,
                                estado='ACTIVO',
                            )
                            jugador.full_clean()
                            jugador.save()
                            jugadores_creados += 1

        invalidar_cache()

        self.stdout.write(self.style.SUCCESS(
            f'Equipos creados: {equipos_creados} | ya existentes: {equipos_existentes}'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'Jugadores creados: {jugadores_creados}'
        ))
        if faltantes:
            self.stdout.write(self.style.WARNING(
                'Clubes no encontrados (omitidos): ' + ', '.join(faltantes)
            ))
