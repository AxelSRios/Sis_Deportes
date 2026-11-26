from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Categoria


class CargaCategorias2026Tests(TestCase):
    def _cargar(self):
        call_command('cargar_categorias_2026', stdout=StringIO())

    def test_crea_las_categorias_base(self):
        self._cargar()

        self.assertEqual(Categoria.objects.count(), 2)
        self.assertTrue(Categoria.objects.filter(nombre='Primera A').exists())
        self.assertTrue(Categoria.objects.filter(nombre='Primera B').exists())

    def test_no_duplica_al_ejecutar_dos_veces(self):
        self._cargar()
        self._cargar()

        self.assertEqual(Categoria.objects.count(), 2)
