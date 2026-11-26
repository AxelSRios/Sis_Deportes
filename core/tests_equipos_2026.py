from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Club, Deportista, Equipo


class CargarEquipos2026Tests(TestCase):
    def _cargar(self):
        call_command('cargar_equipos_2026', stdout=StringIO())

    def test_crea_dos_equipos_por_club_con_nomina(self):
        Club.objects.create(nombre='Club AFIZ')
        Club.objects.create(nombre='Club Aurora')

        self._cargar()

        self.assertEqual(Equipo.objects.count(), 4)
        self.assertEqual(Equipo.objects.filter(division='Primera A').count(), 2)
        self.assertEqual(Equipo.objects.filter(division='Primera B').count(), 2)

        for equipo in Equipo.objects.all():
            total = equipo.deportista_set.count()
            self.assertGreaterEqual(total, 15, equipo.nombre)
            self.assertLessEqual(total, 22, equipo.nombre)

        self.assertEqual(
            Deportista.objects.filter(equipo__isnull=True).count(), 0
        )
        self.assertEqual(
            Deportista.objects.values('ci').distinct().count(),
            Deportista.objects.count(),
        )

    def test_no_duplica_al_ejecutar_dos_veces(self):
        Club.objects.create(nombre='Club AFIZ')

        self._cargar()
        equipos = Equipo.objects.count()
        jugadores = Deportista.objects.count()

        self._cargar()

        self.assertEqual(Equipo.objects.count(), equipos)
        self.assertEqual(Deportista.objects.count(), jugadores)
