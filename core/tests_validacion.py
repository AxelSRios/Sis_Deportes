"""Auditoría de validación de datos del sistema A.F.O. · Oruro.

Cubre los formatos bolivianos exigidos (nombres, CI, teléfonos, fechas,
correos y direcciones), los límites de longitud, los duplicados, los datos
vacíos, los intentos de XSS y SQL Injection, los permisos por rol y las
restricciones reales de la base de datos.

Todas las pruebas se ejecutan sobre la base SQLite de pruebas; nunca tocan
la base institucional de Supabase.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .forms import (
    ArbitroForm,
    AsignacionForm,
    CampeonatoForm,
    CanchaForm,
    CategoriaForm,
    ClubForm,
    DeportistaForm,
    EquipoForm,
    InscripcionForm,
    PagoForm,
    PartidoForm,
    PerfilForm,
    SancionForm,
    UsuarioEditarForm,
    UsuarioForm,
)
from .models import (
    Arbitro,
    AsignacionArbitro,
    Campeonato,
    Cancha,
    Categoria,
    Club,
    Deportista,
    Equipo,
    Inscripcion,
    Pago,
    Partido,
    Sancion,
)
from .tests import CLAVE, BaseAfoTestCase
from .validadores import (
    ci_clave,
    validar_ci_boliviana,
    validar_correo,
    validar_direccion,
    validar_fecha_nacimiento,
    validar_fecha_pasada,
    validar_nombre_organizacion,
    validar_nombre_persona,
    validar_telefono_boliviano,
    validar_texto_libre,
    validar_usuario,
)


def hace(anios):
    """Fecha de hace N años sin fallar en los 29 de febrero."""
    hoy = timezone.localdate()
    try:
        return hoy.replace(year=hoy.year - anios)
    except ValueError:
        return hoy.replace(year=hoy.year - anios, day=28)


# ---------------------------------------------------------------------------
# Validadores unitarios (sin base de datos)
# ---------------------------------------------------------------------------


class ValidadoresNombreTests(SimpleTestCase):
    def test_nombres_validos_con_tildes_ñ_espacios_y_separadores(self):
        casos = {
            'María José': 'María José',
            'Ñusta': 'Ñusta',
            "O'Connor": "O'Connor",
            'Jean-Pierre': 'Jean-Pierre',
            '  Ana   Pérez  ': 'Ana Pérez',
            'Ángel': 'Ángel',
            'Muñoz': 'Muñoz',
        }
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(validar_nombre_persona(valor), esperado)

    def test_nombres_invalidos(self):
        invalidos = [
            'Juan123', '123', 'A', '', '   ', 'Juan 3',
            '<script>alert(1)</script>', 'Juan;DROP TABLE clubes',
            'Juan@Pérez', 'Juan_Pérez', 'x' * 61,
        ]
        for valor in invalidos:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_nombre_persona(valor)

    def test_nombres_de_organizacion_validos(self):
        for valor in [
            'Club Deportivo Prueba', 'Sub 17', 'Estadio Jesús Bermúdez',
            'Copa 2026', 'Oruro', "Club O'Higgins", 'Cancha N.º 2',
        ]:
            with self.subTest(valor=valor):
                self.assertTrue(validar_nombre_organizacion(valor))

    def test_nombres_de_organizacion_invalidos(self):
        for valor in [
            '', '   ', 'A', 'x' * 151, '<script>alert(1)</script>',
            'Club;DROP TABLE clubes', 'Club{prueba}', 'Club|prueba',
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_nombre_organizacion(valor)


class ValidadoresCedulaTests(SimpleTestCase):
    def test_cedulas_validas_y_normalizacion(self):
        casos = {
            '1000001': '1000001',
            '1000001-LP': '1000001-LP',
            '1000001 lp': '1000001-LP',
            '1000001 OR': '1000001-OR',
            '7654321-1K': '7654321-1K',
            '7654321-1K CB': '7654321-1K-CB',
            '123456': '123456',
            '12345678': '12345678',
            '1000001OR': '1000001-OR',
        }
        for valor, esperado in casos.items():
            with self.subTest(valor=valor):
                self.assertEqual(validar_ci_boliviana(valor), esperado)

    def test_extension_departamental_no_cambia_la_clave_de_duplicado(self):
        self.assertEqual(ci_clave('1000001'), '1000001')
        self.assertEqual(ci_clave('1000001-LP'), '1000001')
        self.assertEqual(ci_clave('1000001 OR'), '1000001')
        self.assertEqual(ci_clave('1000001-1K OR'), '10000011K')

    def test_cedulas_invalidas(self):
        invalidos = [
            '12345', '123456789', '1000001-XX', 'ABC123', '1000001-',
            '0', '000000', '<script>alert(1)</script>', '',
            '1000001-1K-XX',
        ]
        for valor in invalidos:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_ci_boliviana(valor)

    def test_longitudes_limite_de_cedula(self):
        self.assertEqual(validar_ci_boliviana('123456'), '123456')
        self.assertEqual(validar_ci_boliviana('12345678'), '12345678')
        with self.assertRaises(ValidationError):
            validar_ci_boliviana('12345')
        with self.assertRaises(ValidationError):
            validar_ci_boliviana('123456789')


class ValidadoresTelefonoTests(SimpleTestCase):
    def test_telefonos_validos(self):
        esperado = '+59171234567'
        for valor in [
            '71234567', '+591 71234567', '59171234567',
            '7 123 4567', '+591-7-123-4567',
        ]:
            with self.subTest(valor=valor):
                self.assertEqual(validar_telefono_boliviano(valor), esperado)
        self.assertEqual(
            validar_telefono_boliviano('2-123-4567'), '+59121234567'
        )
        self.assertEqual(
            validar_telefono_boliviano('4 123 4567'), '+59141234567'
        )
        self.assertEqual(validar_telefono_boliviano(''), '')

    def test_telefonos_invalidos(self):
        for valor in [
            '1234567', '123456789', '51234567', '81234567',
            '7123456a', '<script>', '+591 7123456', '00591 71234567',
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_telefono_boliviano(valor)


class ValidadoresFechaTests(SimpleTestCase):
    def test_fechas_de_nacimiento_validas(self):
        self.assertEqual(
            validar_fecha_nacimiento(date(2000, 2, 29)), date(2000, 2, 29)
        )
        self.assertEqual(validar_fecha_nacimiento(hace(20)), hace(20))
        self.assertEqual(validar_fecha_nacimiento(hace(4)), hace(4))
        self.assertEqual(validar_fecha_nacimiento(hace(100)), hace(100))

    def test_fechas_de_nacimiento_invalidas(self):
        invalidas = [
            timezone.localdate() + timedelta(days=1),
            timezone.localdate(),
            hace(3),
            hace(101),
            date(1800, 1, 1),
        ]
        for valor in invalidas:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_fecha_nacimiento(valor)

    def test_fecha_pasada(self):
        self.assertEqual(
            validar_fecha_pasada(date(1980, 1, 1)), date(1980, 1, 1)
        )
        self.assertEqual(
            validar_fecha_pasada(timezone.localdate()), timezone.localdate()
        )
        for valor in [
            timezone.localdate() + timedelta(days=1), date(1899, 12, 31)
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_fecha_pasada(valor)


class ValidadoresCorreoTextoTests(SimpleTestCase):
    def test_correos_validos(self):
        self.assertEqual(
            validar_correo('ana.perez@dominio.com.bo'),
            'ana.perez@dominio.com.bo',
        )
        self.assertEqual(validar_correo('X@Y.BO'), 'X@y.bo')
        self.assertEqual(validar_correo(''), '')

    def test_correos_invalidos(self):
        for valor in [
            'sin-arroba', 'a@b', 'a@dominio', '@dominio.bo',
            'a b@dominio.bo', '<script>@x.com', 'x' * 140 + '@x.com',
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_correo(valor)

    def test_direcciones_validas_e_invalidas(self):
        self.assertEqual(
            validar_direccion('Av. Del Ejército #123, zona norte'),
            'Av. Del Ejército #123, zona norte',
        )
        self.assertEqual(validar_direccion(''), '')
        for valor in [
            'a', 'x' * 221, '<script>alert(1)</script>',
            'javascript:alert(1)',
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_direccion(valor)

    def test_texto_libre(self):
        self.assertEqual(
            validar_texto_libre('Observación normal, con comas y puntos.'),
            'Observación normal, con comas y puntos.',
        )
        self.assertEqual(validar_texto_libre(''), '')
        for valor in [
            '<script>alert(1)</script>', 'javascript:alert(1)',
            'x' * 1001, '<iframe src="x">',
        ]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_texto_libre(valor)

    def test_usuario_de_acceso(self):
        for valor in ['admin', 'nuevo.usuario', 'dirigente_2', 'a-b-c']:
            with self.subTest(valor=valor):
                self.assertEqual(validar_usuario(valor), valor)
        for valor in ['', 'ab', 'usuario con espacio', 'acentué', 'x' * 31]:
            with self.subTest(valor=valor):
                with self.assertRaises(ValidationError):
                    validar_usuario(valor)


# ---------------------------------------------------------------------------
# Formularios: datos válidos, inválidos, duplicados y límites
# ---------------------------------------------------------------------------


class FormulariosBaseTests(BaseAfoTestCase):
    def datos_deportista(self, **cambios):
        datos = {
            'nombre': 'María José',
            'apellido': 'Ñusta Pérez',
            'ci': '1000009-1K OR',
            'fecha_nacimiento': '2000-02-29',
            'genero': 'M',
            'foto_url': '',
            'telefono': '+591 71234567',
            'direccion': 'Av. Del Ejército #123, zona norte',
            'club': self.club.pk,
            'equipo': self.equipo.pk,
            'categoria': self.categoria.pk,
            'estado': 'ACTIVO',
        }
        datos.update(cambios)
        return datos

    def datos_club(self, **cambios):
        datos = {
            'nombre': 'Club Validación',
            'logo_url': '',
            'fundacion': '1980-01-01',
            'presidente': 'Ana Pérez',
            'telefono': '+591 2 123 4567',
            'email': 'club.validacion@afo.bo',
            'direccion': 'Av. Del Ejército #123',
            'categoria_ingreso': 'Primera',
            'nit_personeria': 'NIT-123456',
            'estado_juridico': 'Personería vigente',
            'estado': 'ACTIVO',
            'observaciones': 'Club de prueba',
        }
        datos.update(cambios)
        return datos


class DeportistaFormTests(FormulariosBaseTests):
    def test_acepta_datos_bolivianos_validos_y_normaliza(self):
        formulario = DeportistaForm(data=self.datos_deportista())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        deportista = formulario.save()
        self.assertEqual(deportista.ci, '1000009-1K-OR')
        self.assertEqual(deportista.telefono, '+59171234567')

    def test_rechaza_nombre_con_numeros(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(nombre='Juan123')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_rechaza_apellido_con_simbolos(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(apellido='Pérez<script>')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('apellido', formulario.errors)

    def test_rechaza_datos_vacios_obligatorios(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(
                nombre='', apellido='', fecha_nacimiento=''
            )
        )
        self.assertFalse(formulario.is_valid())
        for campo in ('nombre', 'apellido', 'fecha_nacimiento'):
            self.assertIn(campo, formulario.errors)

    def test_rechaza_ci_invalida(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(ci='12345')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('ci', formulario.errors)

    def test_rechaza_ci_duplicada_ignorando_extension(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(ci='1000002-LP')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('ci', formulario.errors)
        self.assertIn('cédula', formulario.errors['ci'][0].lower())

    def test_rechaza_telefono_invalido(self):
        for telefono in ('1234567', '123456789', '51234567', '7123456a'):
            with self.subTest(telefono=telefono):
                formulario = DeportistaForm(
                    data=self.datos_deportista(telefono=telefono)
                )
                self.assertFalse(formulario.is_valid())
                self.assertIn('telefono', formulario.errors)

    def test_rechaza_fecha_futura(self):
        manana = (timezone.localdate() + timedelta(days=1)).isoformat()
        formulario = DeportistaForm(
            data=self.datos_deportista(fecha_nacimiento=manana)
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fecha_nacimiento', formulario.errors)

    def test_rechaza_menor_de_cuatro_anios(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(
                fecha_nacimiento=hace(3).isoformat()
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fecha_nacimiento', formulario.errors)

    def test_rechaza_direccion_con_xss(self):
        formulario = DeportistaForm(
            data=self.datos_deportista(
                direccion='<script>alert(1)</script>'
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('direccion', formulario.errors)

    def test_limites_de_longitud(self):
        self.assertTrue(
            DeportistaForm(
                data=self.datos_deportista(nombre='A' * 60)
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(nombre='A' * 61)
            ).is_valid()
        )
        self.assertTrue(
            DeportistaForm(
                data=self.datos_deportista(direccion='A' * 200)
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(direccion='A' * 201)
            ).is_valid()
        )

    def test_limites_de_ci_y_telefono(self):
        self.assertTrue(
            DeportistaForm(
                data=self.datos_deportista(ci='900001')
            ).is_valid()
        )
        self.assertTrue(
            DeportistaForm(
                data=self.datos_deportista(ci='90000001')
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(ci='90001')
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(ci='900000001')
            ).is_valid()
        )
        self.assertTrue(
            DeportistaForm(
                data=self.datos_deportista(telefono='71234567')
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(telefono='7123456')
            ).is_valid()
        )
        self.assertFalse(
            DeportistaForm(
                data=self.datos_deportista(telefono='712345678')
            ).is_valid()
        )

    def test_editar_conserva_su_propia_cedula(self):
        formulario = DeportistaForm(
            instance=self.deportista,
            data=self.datos_deportista(
                nombre=self.deportista.nombre,
                apellido=self.deportista.apellido,
                ci=self.deportista.ci,
                fecha_nacimiento=self.deportista.fecha_nacimiento.isoformat(),
                club=self.deportista.club_id,
                equipo=self.deportista.equipo_id,
                categoria=self.deportista.categoria_id,
            ),
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)


class ClubFormTests(FormulariosBaseTests):
    def test_acepta_datos_validos(self):
        formulario = ClubForm(data=self.datos_club())
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_rechaza_nombre_vacio(self):
        formulario = ClubForm(data=self.datos_club(nombre='   '))
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_rechaza_presidente_con_numeros(self):
        formulario = ClubForm(data=self.datos_club(presidente='Ana 123'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('presidente', formulario.errors)

    def test_rechaza_telefono_invalido(self):
        formulario = ClubForm(data=self.datos_club(telefono='12345'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('telefono', formulario.errors)

    def test_rechaza_correo_invalido(self):
        formulario = ClubForm(data=self.datos_club(email='club@'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_rechaza_correo_duplicado(self):
        Club.objects.create(nombre='Club Existente', email='repetido@afo.bo')
        formulario = ClubForm(
            data=self.datos_club(email='REPETIDO@afo.bo')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_rechaza_fundacion_futura(self):
        formulario = ClubForm(
            data=self.datos_club(fundacion='2999-01-01')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fundacion', formulario.errors)

    def test_rechaza_xss_en_observaciones(self):
        formulario = ClubForm(
            data=self.datos_club(
                observaciones='<script>alert(1)</script>'
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('observaciones', formulario.errors)

    def test_limites_de_longitud_del_nombre(self):
        self.assertTrue(
            ClubForm(data=self.datos_club(nombre='C' * 150)).is_valid()
        )
        self.assertFalse(
            ClubForm(data=self.datos_club(nombre='C' * 151)).is_valid()
        )


class CanchaFormTests(FormulariosBaseTests):
    def datos_cancha(self, **cambios):
        datos = {
            'nombre': 'Cancha Validación',
            'tipo': 'SINTETICA',
            'descripcion': 'Sintética de prueba',
            'direccion': 'Av. 6 de Octubre #123',
            'ciudad': 'Oruro',
            'latitud': '-17.964000',
            'longitud': '-67.106000',
            'imagen_url': '',
            'activa': 'on',
            'orden': '1',
        }
        datos.update(cambios)
        return datos

    def test_acepta_cancha_valida(self):
        formulario = CanchaForm(data=self.datos_cancha())
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_rechaza_nombre_con_xss(self):
        formulario = CanchaForm(
            data=self.datos_cancha(nombre='<script>alert(1)</script>')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_rechaza_coordenadas_incompletas(self):
        formulario = CanchaForm(data=self.datos_cancha(longitud=''))
        self.assertFalse(formulario.is_valid())
        self.assertIn('latitud', formulario.errors)

    def test_rechaza_latitud_fuera_de_rango(self):
        formulario = CanchaForm(data=self.datos_cancha(latitud='100'))
        self.assertFalse(formulario.is_valid())
        self.assertIn('latitud', formulario.errors)

    def test_rechaza_direccion_con_xss(self):
        formulario = CanchaForm(
            data=self.datos_cancha(
                direccion='<script>alert(1)</script>'
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('direccion', formulario.errors)


class CategoriaEquipoFormTests(FormulariosBaseTests):
    def test_categoria_valida(self):
        formulario = CategoriaForm(
            data={
                'nombre': 'Sub 13 Validación',
                'edad_min': 11,
                'edad_max': 13,
                'descripcion': 'Categoría de prueba',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_categoria_rechaza_rango_invertido(self):
        formulario = CategoriaForm(
            data={
                'nombre': 'Sub 13 Invertida',
                'edad_min': 13,
                'edad_max': 11,
                'descripcion': '',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('edad_max', formulario.errors)

    def test_categoria_rechaza_nombre_duplicado(self):
        formulario = CategoriaForm(
            data={
                'nombre': 'Sub 17',
                'edad_min': 15,
                'edad_max': 17,
                'descripcion': '',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_equipo_valido(self):
        formulario = EquipoForm(
            data={
                'nombre': 'Equipo Validación',
                'club': self.club.pk,
                'categoria': self.categoria.pk,
                'division': 'Primera',
                'temporada': 2026,
                'entrenador': 'Carlos Mamani',
                'estado': 'ACTIVO',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_equipo_rechaza_entrenador_con_numeros(self):
        formulario = EquipoForm(
            data={
                'nombre': 'Equipo Validación',
                'club': self.club.pk,
                'categoria': self.categoria.pk,
                'division': 'Primera',
                'temporada': 2026,
                'entrenador': 'Carlos 2',
                'estado': 'ACTIVO',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('entrenador', formulario.errors)

    def test_equipo_rechaza_temporada_fuera_de_rango(self):
        formulario = EquipoForm(
            data={
                'nombre': 'Equipo Validación',
                'club': self.club.pk,
                'categoria': self.categoria.pk,
                'division': 'Primera',
                'temporada': 1800,
                'entrenador': 'Carlos Mamani',
                'estado': 'ACTIVO',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('temporada', formulario.errors)


class CampeonatoPartidoFormTests(FormulariosBaseTests):
    def datos_campeonato(self, **cambios):
        datos = {
            'nombre': 'Copa Validación',
            'categoria': self.categoria.pk,
            'disciplina': 'Fútbol',
            'temporada': 2026,
            'modalidad': 'LIGA',
            'fecha_inicio': '2026-01-01',
            'fecha_conclusion': '2026-02-01',
            'estado': 'PLANIFICADO',
            'reglamento': 'Reglamento de prueba',
        }
        datos.update(cambios)
        return datos

    def datos_partido(self, **cambios):
        datos = {
            'campeonato': self.campeonato.pk,
            'equipo_local': self.equipo.pk,
            'equipo_visitante': self.equipo2.pk,
            'fecha': (
                timezone.now() + timedelta(days=15)
            ).strftime('%Y-%m-%dT%H:%M'),
            'escenario': 'Estadio Municipal',
            'estado': 'Programado',
            'goles_local': '',
            'goles_visitante': '',
        }
        datos.update(cambios)
        return datos

    def test_campeonato_valido(self):
        formulario = CampeonatoForm(data=self.datos_campeonato())
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_campeonato_rechaza_fechas_invertidas(self):
        formulario = CampeonatoForm(
            data=self.datos_campeonato(
                fecha_inicio='2026-02-01',
                fecha_conclusion='2026-01-01',
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fecha_conclusion', formulario.errors)

    def test_campeonato_rechaza_nombre_con_xss(self):
        formulario = CampeonatoForm(
            data=self.datos_campeonato(
                nombre='<script>alert(1)</script>'
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_partido_valido(self):
        formulario = PartidoForm(data=self.datos_partido())
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_partido_rechaza_equipos_iguales(self):
        formulario = PartidoForm(
            data=self.datos_partido(equipo_visitante=self.equipo.pk)
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('equipo_visitante', formulario.errors)

    def test_partido_rechaza_goles_incompletos(self):
        formulario = PartidoForm(
            data=self.datos_partido(goles_local=2)
        )
        self.assertFalse(formulario.is_valid())

    def test_partido_rechaza_goles_fuera_de_limite(self):
        formulario = PartidoForm(
            data=self.datos_partido(goles_local=100, goles_visitante=0)
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('goles_local', formulario.errors)


class InscripcionSancionPagoFormTests(FormulariosBaseTests):
    def test_inscripcion_valida(self):
        formulario = InscripcionForm(
            data={
                'campeonato': self.campeonato.pk,
                'equipo': self.equipo.pk,
                'deportista': '',
                'estado': 'PENDIENTE',
                'observaciones': 'Inscripción de prueba',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_inscripcion_rechaza_sin_sujeto(self):
        formulario = InscripcionForm(
            data={
                'campeonato': self.campeonato.pk,
                'equipo': '',
                'deportista': '',
                'estado': 'PENDIENTE',
                'observaciones': '',
            }
        )
        self.assertFalse(formulario.is_valid())

    def test_inscripcion_rechaza_duplicado(self):
        Inscripcion.objects.create(
            campeonato=self.campeonato, equipo=self.equipo
        )
        formulario = InscripcionForm(
            data={
                'campeonato': self.campeonato.pk,
                'equipo': self.equipo.pk,
                'deportista': '',
                'estado': 'PENDIENTE',
                'observaciones': '',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('equipo', formulario.errors)

    def test_inscripcion_rechaza_observaciones_con_xss(self):
        formulario = InscripcionForm(
            data={
                'campeonato': self.campeonato.pk,
                'equipo': self.equipo.pk,
                'deportista': '',
                'estado': 'PENDIENTE',
                'observaciones': '<script>alert(1)</script>',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('observaciones', formulario.errors)

    def test_sancion_valida(self):
        formulario = SancionForm(
            data={
                'tipo': 'AMONESTACION',
                'deportista': self.deportista.pk,
                'club': '',
                'campeonato': self.campeonato.pk,
                'partido': '',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'fecha_inicio': '',
                'fecha_fin': '',
                'descripcion': 'Tarjeta amarilla por reclamo',
                'estado': 'VIGENTE',
                'observaciones': '',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_sancion_rechaza_sin_sancionado(self):
        formulario = SancionForm(
            data={
                'tipo': 'AMONESTACION',
                'deportista': '',
                'club': '',
                'campeonato': '',
                'partido': '',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'fecha_inicio': '',
                'fecha_fin': '',
                'descripcion': 'Sin sujeto',
                'estado': 'VIGENTE',
                'observaciones': '',
            }
        )
        self.assertFalse(formulario.is_valid())

    def test_sancion_rechaza_descripcion_con_xss(self):
        formulario = SancionForm(
            data={
                'tipo': 'AMONESTACION',
                'deportista': self.deportista.pk,
                'club': '',
                'campeonato': '',
                'partido': '',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'fecha_inicio': '',
                'fecha_fin': '',
                'descripcion': '<script>alert(1)</script>',
                'estado': 'VIGENTE',
                'observaciones': '',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('descripcion', formulario.errors)

    def test_sancion_rechaza_fechas_invertidas(self):
        formulario = SancionForm(
            data={
                'tipo': 'SUSPENSION',
                'deportista': self.deportista.pk,
                'club': '',
                'campeonato': '',
                'partido': '',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'fecha_inicio': '2026-02-01',
                'fecha_fin': '2026-01-01',
                'descripcion': 'Suspensión de prueba',
                'estado': 'VIGENTE',
                'observaciones': '',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fecha_fin', formulario.errors)

    def test_pago_valido(self):
        formulario = PagoForm(
            data={
                'tipo': 'Inscripción',
                'monto': '150.00',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'club': self.club.pk,
                'deportista': '',
                'comprobante': 'C-100',
                'estado': 'PAGADO',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_pago_rechaza_monto_cero_o_negativo(self):
        for monto in ('0', '-5.00'):
            with self.subTest(monto=monto):
                formulario = PagoForm(
                    data={
                        'tipo': 'Inscripción',
                        'monto': monto,
                        'fecha': timezone.localtime().strftime(
                            '%Y-%m-%dT%H:%M'
                        ),
                        'club': self.club.pk,
                        'deportista': '',
                        'comprobante': 'C-100',
                        'estado': 'PAGADO',
                    }
                )
                self.assertFalse(formulario.is_valid())
                self.assertIn('monto', formulario.errors)

    def test_pago_rechaza_comprobante_con_xss(self):
        formulario = PagoForm(
            data={
                'tipo': 'Inscripción',
                'monto': '150.00',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'club': self.club.pk,
                'deportista': '',
                'comprobante': '<script>alert(1)</script>',
                'estado': 'PAGADO',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('comprobante', formulario.errors)


class ArbitroAsignacionFormTests(FormulariosBaseTests):
    def datos_arbitro(self, **cambios):
        datos = {
            'nombre': 'Raúl',
            'apellido': 'Luna Mamani',
            'ci': '2000001-1K LP',
            'fecha_nacimiento': '1985-05-10',
            'telefono': '71234567',
            'correo': 'raul.luna@afo.bo',
            'licencia': 'FIFA-2020',
            'categoria': 'NACIONAL',
            'especialidad': 'CENTRAL',
            'disponible': 'on',
            'estado': 'ACTIVO',
        }
        datos.update(cambios)
        return datos

    def test_arbitro_valido_y_normaliza(self):
        formulario = ArbitroForm(data=self.datos_arbitro())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        arbitro = formulario.save()
        self.assertEqual(arbitro.ci, '2000001-1K-LP')
        self.assertEqual(arbitro.telefono, '+59171234567')

    def test_arbitro_rechaza_ci_duplicada(self):
        formulario = ArbitroForm(
            data=self.datos_arbitro(ci='1000001-OR')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('ci', formulario.errors)

    def test_arbitro_rechaza_correo_duplicado(self):
        Arbitro.objects.create(
            nombre='Otro', apellido='Árbitro',
            ci='2000002', correo='repetido.arbitro@afo.bo',
        )
        formulario = ArbitroForm(
            data=self.datos_arbitro(correo='REPETIDO.ARBITRO@afo.bo')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('correo', formulario.errors)

    def test_arbitro_rechaza_nombre_con_numeros(self):
        formulario = ArbitroForm(
            data=self.datos_arbitro(nombre='Raúl 2')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('nombre', formulario.errors)

    def test_arbitro_rechaza_fecha_futura(self):
        formulario = ArbitroForm(
            data=self.datos_arbitro(
                fecha_nacimiento=(
                    timezone.localdate() + timedelta(days=1)
                ).isoformat()
            )
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('fecha_nacimiento', formulario.errors)

    def test_arbitro_rechaza_correo_invalido(self):
        formulario = ArbitroForm(
            data=self.datos_arbitro(correo='raul@')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('correo', formulario.errors)

    def test_asignacion_valida(self):
        formulario = AsignacionForm(
            data={
                'partido': self.partido.pk,
                'arbitro': self.arbitro.pk,
                'rol': 'CENTRAL',
            }
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_asignacion_rechaza_arbitro_repetido(self):
        AsignacionArbitro.objects.create(
            partido=self.partido, arbitro=self.arbitro, rol='CENTRAL'
        )
        formulario = AsignacionForm(
            data={
                'partido': self.partido.pk,
                'arbitro': self.arbitro.pk,
                'rol': 'ASISTENTE1',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('arbitro', formulario.errors)

    def test_asignacion_rechaza_rol_ocupado(self):
        otro = Arbitro.objects.create(
            nombre='Segundo', apellido='Árbitro', ci='2000003'
        )
        AsignacionArbitro.objects.create(
            partido=self.partido, arbitro=self.arbitro, rol='CENTRAL'
        )
        formulario = AsignacionForm(
            data={
                'partido': self.partido.pk,
                'arbitro': otro.pk,
                'rol': 'CENTRAL',
            }
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('rol', formulario.errors)


class UsuariosFormTests(FormulariosBaseTests):
    def datos_usuario(self, **cambios):
        datos = {
            'username': 'nuevo.usuario',
            'first_name': 'María',
            'last_name': 'Pérez',
            'email': 'nuevo.usuario@afo.bo',
            'is_active': 'on',
            'grupo': self.grupo_dirigente.pk,
            'password1': CLAVE,
            'password2': CLAVE,
        }
        datos.update(cambios)
        return datos

    def test_usuario_valido(self):
        formulario = UsuarioForm(data=self.datos_usuario())
        self.assertTrue(formulario.is_valid(), formulario.errors)
        usuario = formulario.save()
        self.assertTrue(usuario.check_password(CLAVE))
        self.assertEqual(usuario.groups.first(), self.grupo_dirigente)

    def test_usuario_rechaza_correo_duplicado(self):
        formulario = UsuarioForm(
            data=self.datos_usuario(email='ADMIN@afo.bo')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_usuario_rechaza_nombre_con_numeros(self):
        formulario = UsuarioForm(
            data=self.datos_usuario(first_name='María2')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('first_name', formulario.errors)

    def test_usuario_rechaza_username_invalido(self):
        for username in ('ab', 'usuario con espacio', 'acentué'):
            with self.subTest(username=username):
                formulario = UsuarioForm(
                    data=self.datos_usuario(username=username)
                )
                self.assertFalse(formulario.is_valid())
                self.assertIn('username', formulario.errors)

    def test_usuario_rechaza_correo_invalido(self):
        formulario = UsuarioForm(
            data=self.datos_usuario(email='nuevo@')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_usuario_rechaza_contrasenas_distintas(self):
        formulario = UsuarioForm(
            data=self.datos_usuario(password2='Otra#Clave2026')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('password2', formulario.errors)

    def test_editar_usuario_conserva_su_correo(self):
        formulario = UsuarioEditarForm(
            instance=self.admin,
            data={
                'username': self.admin.username,
                'first_name': 'Admin',
                'last_name': 'General',
                'email': self.admin.email,
                'is_active': 'on',
                'grupo': self.grupo_admin.pk,
            },
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_editar_usuario_rechaza_correo_de_otro(self):
        User.objects.create_user(
            username='otro', email='ocupado@afo.bo', password=CLAVE
        )
        formulario = UsuarioEditarForm(
            instance=self.admin,
            data={
                'username': self.admin.username,
                'first_name': 'Admin',
                'last_name': 'General',
                'email': 'ocupado@afo.bo',
                'is_active': 'on',
                'grupo': self.grupo_admin.pk,
            },
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_perfil_valido(self):
        formulario = PerfilForm(
            instance=self.dirigente,
            data={
                'first_name': 'Dirigente',
                'last_name': 'Actualizado',
                'email': 'dirigente@afo.bo',
            },
        )
        self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_perfil_rechaza_correo_duplicado(self):
        formulario = PerfilForm(
            instance=self.dirigente,
            data={
                'first_name': 'Dirigente',
                'last_name': 'Actualizado',
                'email': self.admin.email,
            },
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('email', formulario.errors)

    def test_perfil_rechaza_nombre_con_numeros(self):
        formulario = PerfilForm(
            instance=self.dirigente,
            data={
                'first_name': 'Dirigente2',
                'last_name': 'Actualizado',
                'email': '',
            },
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('first_name', formulario.errors)


# ---------------------------------------------------------------------------
# Modelos y base de datos
# ---------------------------------------------------------------------------


class ModelosValidacionTests(BaseAfoTestCase):
    def test_datos_base_pasan_full_clean(self):
        for objeto in (
            self.club, self.categoria, self.equipo, self.campeonato,
            self.partido, self.arbitro, self.deportista, self.pago,
        ):
            with self.subTest(modelo=objeto.__class__.__name__):
                objeto.full_clean()

    def test_modelo_rechaza_nombre_con_numeros(self):
        deportista = Deportista(
            nombre='Luis2', apellido='Mamani',
            fecha_nacimiento=date(2000, 1, 1),
        )
        with self.assertRaises(ValidationError) as contexto:
            deportista.full_clean()
        self.assertIn('nombre', contexto.exception.message_dict)

    def test_modelo_rechaza_ci_invalida(self):
        deportista = Deportista(
            nombre='Luis', apellido='Mamani', ci='ABC123',
            fecha_nacimiento=date(2000, 1, 1),
        )
        with self.assertRaises(ValidationError) as contexto:
            deportista.full_clean()
        self.assertIn('ci', contexto.exception.message_dict)

    def test_modelo_rechaza_fecha_futura(self):
        deportista = Deportista(
            nombre='Luis', apellido='Mamani',
            fecha_nacimiento=timezone.localdate() + timedelta(days=1),
        )
        with self.assertRaises(ValidationError) as contexto:
            deportista.full_clean()
        self.assertIn('fecha_nacimiento', contexto.exception.message_dict)

    def test_modelo_rechaza_telefono_invalido(self):
        deportista = Deportista(
            nombre='Luis', apellido='Mamani', telefono='12345',
            fecha_nacimiento=date(2000, 1, 1),
        )
        with self.assertRaises(ValidationError) as contexto:
            deportista.full_clean()
        self.assertIn('telefono', contexto.exception.message_dict)

    def test_modelo_rechaza_correo_invalido(self):
        club = Club(nombre='Club Correo', email='club@')
        with self.assertRaises(ValidationError) as contexto:
            club.full_clean()
        self.assertIn('email', contexto.exception.message_dict)

    def test_modelo_rechaza_direccion_con_xss(self):
        club = Club(
            nombre='Club Dirección',
            direccion='<script>alert(1)</script>',
        )
        with self.assertRaises(ValidationError) as contexto:
            club.full_clean()
        self.assertIn('direccion', contexto.exception.message_dict)

    def test_modelo_normaliza_ci_y_telefono(self):
        deportista = Deportista(
            nombre='Ana', apellido='Quispe', ci='3000001 lp',
            telefono='7 123 4567', fecha_nacimiento=date(1990, 1, 1),
        )
        deportista.full_clean()
        self.assertEqual(deportista.ci, '3000001-LP')
        self.assertEqual(deportista.telefono, '+59171234567')

    def test_modelo_cancha_exige_coordenadas_completas(self):
        cancha = Cancha(
            nombre='Cancha Incompleta', latitud=Decimal('-17.9')
        )
        with self.assertRaises(ValidationError) as contexto:
            cancha.full_clean()
        self.assertIn('latitud', contexto.exception.message_dict)

    def test_modelo_pago_rechaza_monto_cero(self):
        pago = Pago(tipo='Cuota', monto=Decimal('0'))
        with self.assertRaises(ValidationError) as contexto:
            pago.full_clean()
        self.assertIn('monto', contexto.exception.message_dict)

    def test_ci_duplicada_es_rechazada_por_la_base(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Deportista.objects.create(
                    nombre='Otro', apellido='Jugador',
                    ci=self.deportista.ci,
                    fecha_nacimiento=date(2001, 1, 1),
                )
        self.assertEqual(
            Deportista.objects.filter(ci=self.deportista.ci).count(), 1
        )


# ---------------------------------------------------------------------------
# Seguridad, permisos y ataques comunes
# ---------------------------------------------------------------------------


class SeguridadTests(BaseAfoTestCase):
    def test_anonimo_no_accede_a_formularios(self):
        for ruta in ('club_crear', 'deportista_crear', 'cancha_crear'):
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(reverse(ruta))
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn(reverse('login'), respuesta['Location'])

    def test_dirigente_no_puede_crear_clubes(self):
        self.ingresar(self.dirigente)
        self.assertEqual(
            self.client.get(reverse('club_crear')).status_code, 403
        )
        respuesta = self.client.post(
            reverse('club_crear'),
            {
                'nombre': 'Club No Autorizado',
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(
            Club.objects.filter(nombre='Club No Autorizado').exists()
        )

    def test_arbitro_no_accede_a_finanzas_ni_usuarios(self):
        self.ingresar(self.arbitro_user)
        for ruta in ('tesoreria', 'usuarios', 'auditoria'):
            with self.subTest(ruta=ruta):
                self.assertEqual(
                    self.client.get(reverse(ruta)).status_code, 403
                )

    def test_csrf_obligatorio_en_formularios(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.admin)
        respuesta = cliente.post(
            reverse('club_crear'),
            {
                'nombre': 'Club Sin Token',
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(
            Club.objects.filter(nombre='Club Sin Token').exists()
        )

    def test_sql_injection_en_nombre_se_rechaza_sin_danar_la_base(self):
        self.ingresar(self.admin)
        antes = Club.objects.count()
        respuesta = self.client.post(
            reverse('club_crear'),
            {
                'nombre': "Club'; DROP TABLE clubes; --",
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Club.objects.count(), antes)
        self.assertTrue(
            Club.objects.filter(nombre='Club Deportivo Prueba').exists()
        )

    def test_sql_injection_en_busqueda_no_provoca_error(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(
            reverse('clubes'), {'q': "' OR 1=1 --"}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            Club.objects.filter(nombre='Club Deportivo Prueba').exists()
        )

    def test_xss_almacenado_se_escapa_al_mostrar(self):
        club = Club.objects.create(
            nombre='Club XSS',
            observaciones="<script>alert('xss')</script>",
        )
        self.ingresar(self.admin)
        respuesta = self.client.get(
            reverse('club_detalle', args=[club.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        contenido = respuesta.content.decode()
        self.assertNotIn("<script>alert('xss')</script>", contenido)
        self.assertIn('&lt;script&gt;', contenido)

    def test_xss_en_busqueda_se_escapa(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(
            reverse('clubes'), {'q': '<script>alert(1)</script>'}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn(
            '<script>alert(1)</script>', respuesta.content.decode()
        )

    def test_permisos_de_escritura_por_rol(self):
        casos = [
            (self.dirigente, 'deportista_crear', 200),
            (self.dirigente, 'club_crear', 403),
            (self.arbitro_user, 'partido_crear', 200),
            (self.arbitro_user, 'pago_crear', 403),
            (self.tesorero, 'pago_crear', 200),
            (self.tesorero, 'deportista_crear', 403),
        ]
        for usuario, ruta, esperado in casos:
            with self.subTest(usuario=usuario.username, ruta=ruta):
                self.ingresar(usuario)
                self.assertEqual(
                    self.client.get(reverse(ruta)).status_code, esperado
                )
