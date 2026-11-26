"""Carga un conjunto de demostración con 50 deportistas bolivianos ficticios.

No utiliza información de personas reales: nombres, cédulas, teléfonos,
direcciones y correos son inventados y llevan la marca "demostración".
Crea también clubes, categorías y equipos de soporte para que los registros
tengan relaciones válidas.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from core.cache_utils import invalidar_cache
from core.models import Categoria, Club, Deportista, Equipo

CATEGORIAS = [
    ('Sub-14', 12, 14, 'Categoría juvenil Sub-14.'),
    ('Sub-16', 15, 16, 'Categoría juvenil Sub-16.'),
    ('Sub-18', 17, 18, 'Categoría juvenil Sub-18.'),
    ('Primera', 19, 40, 'Categoría principal de la A.F.O.'),
]

CLUBES = [
    ('Club Deportivo San Felipe', 'Oruro', '1998-03-14', 'Javier Mamani'),
    ('Club Atlético Socavón', 'Oruro', '2001-07-21', 'Ruth Quispe'),
    ('Club Sportivo Norte', 'Oruro', '1995-11-02', 'Marcelo Condori'),
    ('Club Deportivo Challapata', 'Challapata', '2004-01-18', 'Nadia Flores'),
    ('Club Atlético Huanuni', 'Huanuni', '1992-09-09', 'Osvaldo Choque'),
    ('Club Deportivo Caracollo', 'Caracollo', '2008-05-26', 'Elena Apaza'),
    ('Club Sport Oruro', 'Oruro', '1989-12-12', 'Ramiro Céspedes'),
    ('Club Deportivo Machacamarca', 'Machacamarca', '2010-08-30', 'Lourdes Ticona'),
]

# club, categoría, entrenador
EQUIPOS = [
    ('Club Deportivo San Felipe Sub-14', 'Club Deportivo San Felipe', 'Sub-14', 'Álvaro Nina'),
    ('Club Atlético Socavón Sub-16', 'Club Atlético Socavón', 'Sub-16', 'Carla Villarroel'),
    ('Club Sportivo Norte Sub-18', 'Club Sportivo Norte', 'Sub-18', 'Pedro Salazar'),
    ('Club Deportivo Challapata Primera', 'Club Deportivo Challapata', 'Primera', 'Mónica Arce'),
    ('Club Atlético Huanuni Sub-16', 'Club Atlético Huanuni', 'Sub-16', 'Wilson Loayza'),
    ('Club Deportivo Caracollo Sub-14', 'Club Deportivo Caracollo', 'Sub-14', 'Sandra Véliz'),
    ('Club Sport Oruro Primera', 'Club Sport Oruro', 'Primera', 'Hugo Sánchez'),
    ('Club Deportivo Machacamarca Sub-18', 'Club Deportivo Machacamarca', 'Sub-18', 'Patricia Ríos'),
]

# 50 nombres ficticios, con paridad de género.
NOMBRES = [
    ('José', 'Mamani', 'M'), ('María', 'Quispe', 'F'),
    ('Luis', 'Condori', 'M'), ('Ana', 'Choque', 'F'),
    ('Carlos', 'Flores', 'M'), ('Silvia', 'Vargas', 'F'),
    ('Juan', 'Rojas', 'M'), ('Rocío', 'Céspedes', 'F'),
    ('Miguel', 'Aguilar', 'M'), ('Fernanda', 'Colque', 'F'),
    ('Pedro', 'Ticona', 'M'), ('Carla', 'Apaza', 'F'),
    ('Jorge', 'Calla', 'M'), ('Lucía', 'Huanca', 'F'),
    ('Roberto', 'López', 'M'), ('Daniela', 'Gutiérrez', 'F'),
    ('Fernando', 'Paredes', 'M'), ('Gabriela', 'Torrez', 'F'),
    ('Ricardo', 'Nina', 'M'), ('Paola', 'Limachi', 'F'),
    ('Álvaro', 'Cáceres', 'M'), ('Andrea', 'Villarroel', 'F'),
    ('Sergio', 'Escobar', 'M'), ('Valeria', 'Arce', 'F'),
    ('Marco Antonio', 'Zenteno', 'M'), ('Camila', 'Céspedes', 'F'),
    ('Diego', 'Salazar', 'M'), ('Natalia', 'Ibáñez', 'F'),
    ('Óscar', 'Méndez', 'M'), ('Verónica', 'Loayza', 'F'),
    ('Hugo', 'Sánchez', 'M'), ('Mónica', 'Riveros', 'F'),
    ('Ramiro', 'Céspedes', 'M'), ('Patricia', 'Orellana', 'F'),
    ('Iván', 'Bustamante', 'M'), ('Claudia', 'Ríos', 'F'),
    ('Raúl', 'Villca', 'M'), ('Eliana', 'Cáceres', 'F'),
    ('Gonzalo', 'Véliz', 'M'), ('Maribel', 'Fernández', 'F'),
    ('Wilson', 'Choque', 'M'), ('Karen', 'Mamani', 'F'),
    ('Edwin', 'Quispe', 'M'), ('Sandra', 'Condori', 'F'),
    ('Freddy', 'Huanca', 'M'), ('Rina', 'Colque', 'F'),
    ('Ronald', 'Apaza', 'M'), ('Gladys', 'Ticona', 'F'),
    ('Jhonny', 'Callisaya', 'M'), ('Lizeth', 'Choqueticlla', 'F'),
]

EDADES = {
    'Sub-14': [13, 14],
    'Sub-16': [15, 16],
    'Sub-18': [17, 18],
    'Primera': [20, 21, 22, 23, 24, 25],
}


class Command(BaseCommand):
    help = 'Carga 50 deportistas bolivianos ficticios con clubes y equipos de soporte.'

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=50)
        parser.add_argument(
            '--limpiar', action='store_true',
            help='Elimina solo los registros de demostración creados por este comando.',
        )

    def handle(self, *args, **options):
        if options['limpiar']:
            self._limpiar()
            return

        cantidad = max(0, min(int(options['cantidad']), len(NOMBRES)))
        creados = {'categorias': 0, 'clubes': 0, 'equipos': 0, 'deportistas': 0}
        existentes = 0

        with transaction.atomic():
            categorias = {}
            for nombre, edad_min, edad_max, descripcion in CATEGORIAS:
                categoria = Categoria.objects.filter(nombre__iexact=nombre).first()
                if categoria is None:
                    categoria = Categoria(
                        nombre=nombre,
                        edad_min=edad_min,
                        edad_max=edad_max,
                        descripcion=descripcion,
                    )
                    categoria.full_clean()
                    categoria.save()
                    creados['categorias'] += 1
                categorias[nombre] = categoria

            clubes = {}
            for indice, (nombre, ciudad, fundacion, presidente) in enumerate(CLUBES, start=1):
                club = Club.objects.filter(nombre__iexact=nombre).first()
                if club is None:
                    club = Club(
                        nombre=nombre,
                        direccion=f'{ciudad}, Bolivia · registro ficticio de demostración',
                        telefono=f'+5912{indice:07d}'[:12],
                        email=f'club{indice:02d}@example.bo',
                        fundacion=date.fromisoformat(fundacion),
                        presidente=presidente,
                        nit_personeria=f'NIT-DEMO-{indice:03d}',
                        estado_juridico='Personería jurídica vigente',
                        estado='ACTIVO',
                        observaciones='Datos ficticios de demostración AFO 2026.',
                    )
                    club.full_clean()
                    club.save()
                    creados['clubes'] += 1
                clubes[nombre] = club

            equipos = []
            for nombre, club_nombre, categoria_nombre, entrenador in EQUIPOS:
                equipo = Equipo.objects.filter(nombre__iexact=nombre).first()
                if equipo is None:
                    equipo = Equipo(
                        nombre=nombre,
                        club=clubes[club_nombre],
                        categoria=categorias[categoria_nombre],
                        division=categoria_nombre,
                        temporada=2026,
                        entrenador=entrenador,
                        estado='ACTIVO',
                    )
                    equipo.full_clean()
                    equipo.save()
                    creados['equipos'] += 1
                equipos.append(equipo)

            for indice in range(cantidad):
                nombre, apellido, genero = NOMBRES[indice]
                equipo = equipos[indice % len(equipos)]
                categoria = equipo.categoria
                ci = f'90{indice + 1:05d}-OR'
                if Deportista.objects.filter(ci=ci).exists():
                    existentes += 1
                    continue

                edades = EDADES[categoria.nombre]
                edad = edades[indice % len(edades)]
                nacimiento = date(
                    2026 - edad,
                    (indice % 12) + 1,
                    (indice % 27) + 1,
                )
                telefono = f'+5917{indice:07d}'
                jugador = Deportista(
                    nombre=nombre,
                    apellido=apellido,
                    ci=ci,
                    fecha_nacimiento=nacimiento,
                    genero=genero,
                    telefono=telefono,
                    direccion=f'{equipo.club.direccion.split(",")[0]} · registro ficticio de demostración',
                    club=equipo.club,
                    equipo=equipo,
                    categoria=categoria,
                    estado='ACTIVO',
                )
                jugador.full_clean()
                jugador.save()
                creados['deportistas'] += 1

        invalidar_cache()
        self.stdout.write(self.style.SUCCESS(
            f"Creados: {creados['categorias']} categorías, {creados['clubes']} clubes, "
            f"{creados['equipos']} equipos y {creados['deportistas']} deportistas."
        ))
        if existentes:
            self.stdout.write(f'Ya existían {existentes} deportistas con las CI de demostración.')

    def _limpiar(self):
        with transaction.atomic():
            borrados = Deportista.objects.filter(
                ci__startswith='90',
                direccion__icontains='demostración',
            ).delete()[0]
            equipos = Equipo.objects.filter(
                nombre__in=[e[0] for e in EQUIPOS],
            ).delete()[0]
            clubes = Club.objects.filter(
                nombre__in=[c[0] for c in CLUBES],
            ).delete()[0]
            categorias = Categoria.objects.filter(
                nombre__in=[c[0] for c in CATEGORIAS],
            ).delete()[0]
        invalidar_cache()
        self.stdout.write(self.style.SUCCESS(
            f'Eliminados: {borrados} deportistas, {equipos} equipos, '
            f'{clubes} clubes y {categorias} categorías de demostración.'
        ))
