from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from core.models import Club


class CargaClubes2026Tests(TestCase):
    def _cargar(self):
        call_command('cargar_clubes_2026', stdout=StringIO())

    def test_carga_las_dos_categorias(self):
        self._cargar()

        self.assertEqual(Club.objects.count(), 20)
        self.assertEqual(
            Club.objects.filter(categoria_ingreso='Primera A').count(), 14
        )
        self.assertEqual(
            Club.objects.filter(categoria_ingreso='Primera B').count(), 6
        )
        self.assertEqual(Club.objects.filter(estado='ACTIVO').count(), 20)
        self.assertEqual(
            Club.objects.filter(observaciones__icontains='2026').count(), 20
        )

    def test_no_duplica_al_ejecutar_dos_veces(self):
        self._cargar()
        self._cargar()

        self.assertEqual(Club.objects.count(), 20)
        self.assertEqual(
            Club.objects.filter(nombre__iexact='Club Aurora').count(), 1
        )

    def test_no_inventa_datos_legales(self):
        self._cargar()

        for campo in ('nit_personeria', 'presidente', 'estado_juridico'):
            self.assertFalse(
                Club.objects.exclude(**{f'{campo}__isnull': True})
                .exclude(**{campo: ''})
                .exists(),
                f'{campo} no debe completarse sin información oficial',
            )
        self.assertFalse(Club.objects.exclude(fundacion__isnull=True).exists())
