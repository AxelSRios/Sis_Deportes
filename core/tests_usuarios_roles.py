import tempfile
from io import StringIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from core.roles import resolver_rol


class CrearUsuariosRolesTests(TestCase):
    def _crear(self, **extra):
        archivo = Path(tempfile.gettempdir()) / 'afo-credenciales-test.txt'
        extra.setdefault('archivo', str(archivo))
        call_command('crear_usuarios_roles', stdout=StringIO(), **extra)
        return archivo

    def test_crea_una_cuenta_por_rol(self):
        archivo = self._crear()

        self.assertEqual(User.objects.count(), 4)
        esperados = {
            'administrador': 'ADMIN',
            'dirigente': 'DIRIGENTE',
            'arbitro': 'ARBITRO',
            'tesorero': 'TESORERO',
        }
        for username, rol in esperados.items():
            usuario = User.objects.get(username=username)
            self.assertTrue(usuario.is_active)
            self.assertEqual(resolver_rol(usuario), rol)

        admin = User.objects.get(username='administrador')
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(archivo.exists())
        self.assertIn('administrador', archivo.read_text(encoding='utf-8'))

    def test_no_duplica_al_ejecutar_dos_veces(self):
        self._crear()
        self._crear()

        self.assertEqual(User.objects.count(), 4)

    def test_elimina_la_cuenta_legacy(self):
        User.objects.create_user(username='admin', password='admin123')

        self._crear(eliminar_legacy=True)

        self.assertFalse(User.objects.filter(username='admin').exists())
        self.assertTrue(User.objects.filter(username='administrador').exists())
