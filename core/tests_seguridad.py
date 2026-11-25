"""Pruebas de accesos y respaldos (se ejecutan sobre SQLite de prueba)."""
import gzip
import json
import os
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import RegistroAcceso

User = get_user_model()


class RegistroAccesoTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(
            username='admin_seguridad',
            email='admin@afo.test',
            password='ClaveSegura123!',
            first_name='Admin',
            last_name='Seguridad',
        )
        self.user = User.objects.create_user(
            username='usuario_seguridad',
            password='ClaveSegura123!',
        )

    def test_login_exitoso_registra_usuario_rol_ip_y_hora(self):
        respuesta = self.client.post(reverse('login'), {
            'username': self.admin.username,
            'password': 'ClaveSegura123!',
        })
        self.assertEqual(respuesta.status_code, 302)
        registro = RegistroAcceso.objects.get(evento='LOGIN')
        self.assertEqual(registro.usuario_id, self.admin.pk)
        self.assertEqual(registro.username, self.admin.username)
        self.assertEqual(registro.rol, 'ADMIN')
        self.assertTrue(registro.ip)
        self.assertIsNotNone(registro.fecha)

    def test_login_fallido_no_guarda_contrasena(self):
        clave = 'NoDebeAparecer-987!'
        respuesta = self.client.post(reverse('login'), {
            'username': 'intruso',
            'password': clave,
        })
        self.assertEqual(respuesta.status_code, 200)
        registro = RegistroAcceso.objects.get(evento='LOGIN_FALLIDO')
        self.assertEqual(registro.username, 'intruso')
        self.assertEqual(registro.usuario_id, None)
        representacion = json.dumps(registro.__dict__, default=str)
        self.assertNotIn(clave, representacion)
        self.assertNotIn('password', representacion.lower())

    def test_logout_registra_cierre(self):
        self.client.force_login(self.user)
        self.client.get(reverse('logout'))
        registro = RegistroAcceso.objects.get(evento='LOGOUT')
        self.assertEqual(registro.usuario_id, self.user.pk)
        self.assertEqual(registro.username, self.user.username)

    def test_bloqueo_tras_intentos_fallidos(self):
        for _ in range(5):
            self.client.post(reverse('login'), {
                'username': 'bloqueado',
                'password': 'incorrecta',
            })
        self.client.post(reverse('login'), {
            'username': 'bloqueado',
            'password': 'incorrecta',
        })
        self.assertTrue(RegistroAcceso.objects.filter(
            evento='LOGIN_FALLIDO', username='bloqueado').exists())
        self.assertTrue(RegistroAcceso.objects.filter(
            evento='BLOQUEO', username='bloqueado').exists())

    def test_no_confia_en_x_forwarded_for_por_defecto(self):
        self.client.post(
            reverse('login'),
            {'username': 'intruso', 'password': 'mala'},
            HTTP_X_FORWARDED_FOR='203.0.113.9',
        )
        registro = RegistroAcceso.objects.get(evento='LOGIN_FALLIDO')
        self.assertEqual(registro.ip, '127.0.0.1')
        self.assertEqual(registro.ip_proxy, '203.0.113.9')

    def test_vista_accesos_solo_para_administracion(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accesos')).status_code, 403)

        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse('accesos'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Registro de accesos')


class RespaldoTests(TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        User.objects.create_user(username='usuario_respaldo', password='ClaveSegura123!')

    def test_respaldo_json_y_verificacion(self):
        with override_settings(AFO_BACKUP_DIR=Path(self.temporal.name)):
            call_command('backup_bd', '--formato', 'json', '--etiqueta', 'prueba')
            archivos = list(Path(self.temporal.name).glob('afo_backup_*.json.gz'))
            self.assertEqual(len(archivos), 1)
            manifiesto = Path(self.temporal.name) / 'ultimo_respaldo.json'
            self.assertTrue(manifiesto.exists())
            info = json.loads(manifiesto.read_text(encoding='utf-8'))
            self.assertEqual(info['formato'], 'json')
            self.assertGreater(info['objetos'], 0)
            self.assertTrue(info['sha256'])

            call_command('verificar_respaldo', '--ruta', str(archivos[0]))
            with gzip.open(archivos[0], 'rt', encoding='utf-8') as entrada:
                datos = json.load(entrada)
            self.assertTrue(any(obj['model'] == 'auth.user' for obj in datos))

    def test_retencion_conserva_solo_las_copias_nuevas(self):
        carpeta = Path(self.temporal.name)
        for indice in range(4):
            ruta = carpeta / f'afo_backup_2020010{indice}_000000_viejo.json.gz'
            ruta.write_bytes(b'x')
            os.utime(ruta, (1000 + indice, 1000 + indice))
        with override_settings(AFO_BACKUP_DIR=carpeta):
            call_command(
                'backup_bd', '--formato', 'json', '--etiqueta', 'retencion',
                '--retencion', '2',
            )
        archivos = sorted(carpeta.glob('afo_backup_*'))
        self.assertEqual(len(archivos), 2)
