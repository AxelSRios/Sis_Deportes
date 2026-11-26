from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Campeonato, Categoria, Club, Equipo, Partido


class Campeonato2026Tests(TestCase):
    def _preparar(self):
        categoria = Categoria.objects.create(nombre='Primera A')
        for indice in range(4):
            club = Club.objects.create(nombre=f'Club Prueba {indice}')
            Equipo.objects.create(
                nombre=f'Club Prueba {indice} Primera A',
                club=club,
                categoria=categoria,
                division='Primera A',
                temporada=2026,
            )

    def _cargar(self):
        call_command('cargar_campeonato_2026', stdout=StringIO())

    def test_crea_campeonato_y_fixture(self):
        self._preparar()
        self._cargar()

        self.assertEqual(Campeonato.objects.count(), 1)
        self.assertEqual(Partido.objects.count(), 6)

        for equipo in Equipo.objects.all():
            jugados = (
                Partido.objects.filter(equipo_local=equipo).count()
                + Partido.objects.filter(equipo_visitante=equipo).count()
            )
            self.assertEqual(jugados, 3, equipo.nombre)

        parejas = {
            tuple(sorted((p.equipo_local_id, p.equipo_visitante_id)))
            for p in Partido.objects.all()
        }
        self.assertEqual(len(parejas), 6)
        self.assertTrue(all(p.estado == 'Programado' for p in Partido.objects.all()))

    def test_no_duplica_partidos(self):
        self._preparar()
        self._cargar()
        self._cargar()

        self.assertEqual(Partido.objects.count(), 6)
