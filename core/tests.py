"""Pruebas automatizadas del Sistema de Gestión Deportiva A.F.O. · Oruro.

Cubren los flujos reales de la consola: CRUD de cada módulo, permisos por
rol en el backend, validaciones de formularios, reportes CSV, comprobantes,
auditoría y panel. Se ejecutan sobre SQLite en memoria (ver settings.py),
de modo que nunca tocan la base institucional de Supabase.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Arbitro,
    AsignacionArbitro,
    Campeonato,
    Categoria,
    Club,
    Deportista,
    Equipo,
    HistorialOperacion,
    Inscripcion,
    Pago,
    Partido,
    Sancion,
)

CLAVE = 'Afo#Segura2026'


class BaseAfoTestCase(TestCase):
    """Datos mínimos compartidos: roles, usuarios y un padrón de prueba."""

    @classmethod
    def setUpTestData(cls):
        cls.grupo_admin = Group.objects.create(name='Administrador General')
        cls.grupo_dirigente = Group.objects.create(name='Dirigente de Club Afiliado')
        cls.grupo_arbitro = Group.objects.create(name='Comisión Técnica / Árbitros')
        cls.grupo_tesorero = Group.objects.create(
            name='Tesorero / Finanzas Institucionales'
        )

        cls.admin = User.objects.create_superuser(
            username='admin_test', email='admin@afo.bo', password=CLAVE
        )
        cls.dirigente = User.objects.create_user(
            username='dirigente_test', password=CLAVE
        )
        cls.dirigente.groups.add(cls.grupo_dirigente)
        cls.arbitro_user = User.objects.create_user(
            username='arbitro_test', password=CLAVE
        )
        cls.arbitro_user.groups.add(cls.grupo_arbitro)
        cls.tesorero = User.objects.create_user(
            username='tesorero_test', password=CLAVE
        )
        cls.tesorero.groups.add(cls.grupo_tesorero)

        cls.club = Club.objects.create(
            nombre='Club Deportivo Prueba',
            presidente='Ana Pérez',
            telefono='70000000',
            estado='ACTIVO',
        )
        cls.categoria = Categoria.objects.create(
            nombre='Sub 17', edad_min=15, edad_max=17
        )
        cls.equipo = Equipo.objects.create(
            nombre='Prueba FC', club=cls.club, categoria=cls.categoria
        )
        cls.equipo2 = Equipo.objects.create(
            nombre='Rival FC', club=cls.club, categoria=cls.categoria
        )
        cls.campeonato = Campeonato.objects.create(
            nombre='Torneo de Prueba',
            categoria=cls.categoria,
            disciplina='Fútbol',
            temporada=2026,
            modalidad='LIGA',
            estado='ACTIVO',
        )
        cls.fecha_partido = timezone.now() + timedelta(days=3)
        cls.partido = Partido.objects.create(
            campeonato=cls.campeonato,
            equipo_local=cls.equipo,
            equipo_visitante=cls.equipo2,
            fecha=cls.fecha_partido,
            escenario='Estadio Municipal',
        )
        cls.arbitro = Arbitro.objects.create(
            nombre='Ana', apellido='Quispe', ci='1000001'
        )
        cls.deportista = Deportista.objects.create(
            nombre='Luis',
            apellido='Mamani',
            ci='1000002',
            fecha_nacimiento=date(2006, 5, 4),
            genero='M',
            club=cls.club,
            equipo=cls.equipo,
            categoria=cls.categoria,
        )
        cls.pago = Pago.objects.create(
            tipo='Inscripción',
            monto=Decimal('150.00'),
            fecha=timezone.now(),
            club=cls.club,
            comprobante='C-001',
            estado='PAGADO',
        )

    def setUp(self):
        # La caché local persiste entre pruebas: se limpia para que cada una
        # vea exactamente los datos que creó.
        cache.clear()
        super().setUp()

    def ingresar(self, usuario):
        self.client.force_login(usuario)


# ---------------------------------------------------------------------------
# Permisos por rol (validados en el servidor, no solo en la interfaz)
# ---------------------------------------------------------------------------


class PermisosTests(BaseAfoTestCase):
    def test_anonimo_es_redirigido_al_login(self):
        respuesta = self.client.get(reverse('clubes'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('login'), respuesta['Location'])

    def test_admin_accede_a_todos_los_modulos(self):
        self.ingresar(self.admin)
        rutas = [
            'panel', 'clubes', 'equipos', 'deportistas', 'categorias',
            'campeonatos', 'inscripciones', 'partidos', 'arbitros',
            'asignaciones', 'sanciones', 'tesoreria', 'reportes',
            'usuarios', 'auditoria', 'perfil',
        ]
        for nombre in rutas:
            with self.subTest(ruta=nombre):
                self.assertEqual(
                    self.client.get(reverse(nombre)).status_code, 200
                )

    def test_dirigente_consulta_pero_no_crea_clubes(self):
        self.ingresar(self.dirigente)
        self.assertEqual(self.client.get(reverse('clubes')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('club_crear')).status_code, 403
        )
        self.assertEqual(
            self.client.get(reverse('club_eliminar', args=[self.club.pk])).status_code,
            403,
        )

    def test_dirigente_si_gestiona_equipos_y_deportistas(self):
        self.ingresar(self.dirigente)
        self.assertEqual(self.client.get(reverse('equipo_crear')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('deportista_crear')).status_code, 200
        )

    def test_arbitro_no_accede_a_finanzas_ni_usuarios(self):
        self.ingresar(self.arbitro_user)
        self.assertEqual(self.client.get(reverse('tesoreria')).status_code, 403)
        self.assertEqual(self.client.get(reverse('usuarios')).status_code, 403)
        self.assertEqual(self.client.get(reverse('auditoria')).status_code, 403)

    def test_arbitro_si_gestiona_partidos_y_asignaciones(self):
        self.ingresar(self.arbitro_user)
        self.assertEqual(self.client.get(reverse('partido_crear')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('asignacion_crear')).status_code, 200
        )

    def test_tesorero_si_gestiona_pagos(self):
        self.ingresar(self.tesorero)
        self.assertEqual(self.client.get(reverse('tesoreria')).status_code, 200)
        self.assertEqual(self.client.get(reverse('pago_crear')).status_code, 200)
        self.assertEqual(self.client.get(reverse('usuarios')).status_code, 403)

    def test_documento_403_usa_plantilla_institucional(self):
        self.ingresar(self.dirigente)
        respuesta = self.client.get(reverse('usuarios'))
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, 'Acceso restringido', status_code=403)


# ---------------------------------------------------------------------------
# CRUD de clubes, categorías, equipos y deportistas
# ---------------------------------------------------------------------------


class ClubesTests(BaseAfoTestCase):
    def test_crear_club_registra_auditoria(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('club_crear'),
            {'nombre': 'Club Nuevo', 'estado': 'ACTIVO', 'presidente': 'Juan'},
        )
        self.assertEqual(respuesta.status_code, 302)
        club = Club.objects.get(nombre='Club Nuevo')
        self.assertTrue(
            HistorialOperacion.objects.filter(
                modulo='clubes', accion='CREAR', operacion__contains='Club Nuevo'
            ).exists()
        )
        self.assertRedirects(respuesta, reverse('clubes'))
        self.assertTrue(club.pk)

    def test_no_permite_nombres_duplicados(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('club_crear'),
            {'nombre': 'club deportivo prueba', 'estado': 'ACTIVO'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Ya existe un club con ese nombre.')
        self.assertEqual(
            Club.objects.filter(nombre__iexact='Club Deportivo Prueba').count(),
            1,
        )

    def test_editar_club(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('club_editar', args=[self.club.pk]),
            {
                'nombre': 'Club Deportivo Prueba',
                'estado': 'SUSPENDIDO',
                'presidente': 'Nuevo Presidente',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.club.refresh_from_db()
        self.assertEqual(self.club.estado, 'SUSPENDIDO')
        self.assertEqual(self.club.presidente, 'Nuevo Presidente')

    def test_busqueda_y_filtro_por_estado(self):
        Club.objects.create(nombre='Otro Club', estado='BAJA')
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('clubes'), {'buscar': 'Otro'})
        nombres = [c.nombre for c in respuesta.context['pagina'].object_list]
        self.assertEqual(nombres, ['Otro Club'])

        respuesta = self.client.get(reverse('clubes'), {'estado': 'ACTIVO'})
        nombres = [c.nombre for c in respuesta.context['pagina'].object_list]
        self.assertIn('Club Deportivo Prueba', nombres)
        self.assertNotIn('Otro Club', nombres)

    def test_detalle_de_club(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('club_detalle', args=[self.club.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Club Deportivo Prueba')
        self.assertContains(respuesta, 'Prueba FC')

    def test_eliminar_club_sin_relaciones(self):
        club = Club.objects.create(nombre='Club Efímero')
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('club_eliminar', args=[club.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Club.objects.filter(pk=club.pk).exists())

    def test_eliminar_club_con_equipos_queda_bloqueado(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('club_eliminar', args=[self.club.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Club.objects.filter(pk=self.club.pk).exists())
        aviso = self.client.get(reverse('club_eliminar', args=[self.club.pk]))
        self.assertContains(aviso, 'Eliminación bloqueada')


class CategoriasEquiposTests(BaseAfoTestCase):
    def test_crear_categoria(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('categoria_crear'),
            {'nombre': 'Sub 20', 'edad_min': 18, 'edad_max': 20, 'descripcion': ''},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Categoria.objects.filter(nombre='Sub 20').exists())

    def test_categoria_rechaza_rango_invertido(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('categoria_crear'),
            {'nombre': 'Rara', 'edad_min': 20, 'edad_max': 10, 'descripcion': ''},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Categoria.objects.filter(nombre='Rara').exists())

    def test_eliminar_categoria_en_uso_bloqueado(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('categoria_eliminar', args=[self.categoria.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_crear_equipo(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('equipo_crear'),
            {
                'nombre': 'Nuevo Equipo',
                'club': self.club.pk,
                'categoria': self.categoria.pk,
                'division': 'Primera',
                'temporada': 2026,
                'entrenador': 'DT Prueba',
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Equipo.objects.filter(nombre='Nuevo Equipo').exists())

    def test_equipo_duplicado_en_el_mismo_club(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('equipo_crear'),
            {
                'nombre': 'prueba fc',
                'club': self.club.pk,
                'categoria': self.categoria.pk,
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta, 'Ese club ya tiene un equipo con el mismo nombre.'
        )

    def test_crear_deportista(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('deportista_crear'),
            {
                'nombre': 'Carla',
                'apellido': 'Rojas',
                'ci': '1000003',
                'fecha_nacimiento': '2007-03-09',
                'genero': 'F',
                'telefono': '71111111',
                'club': self.club.pk,
                'equipo': self.equipo.pk,
                'categoria': self.categoria.pk,
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            Deportista.objects.filter(nombre='Carla', apellido='Rojas').exists()
        )

    def test_deportista_con_equipo_de_otro_club(self):
        otro_club = Club.objects.create(nombre='Club Ajeno')
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('deportista_crear'),
            {
                'nombre': 'Pedro',
                'apellido': 'Soto',
                'fecha_nacimiento': '2004-01-01',
                'club': otro_club.pk,
                'equipo': self.equipo.pk,
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'pertenece a otro club')
        self.assertFalse(Deportista.objects.filter(nombre='Pedro').exists())

    def test_deportista_duplicado(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('deportista_crear'),
            {
                'nombre': 'Luis',
                'apellido': 'Mamani',
                'fecha_nacimiento': '2006-05-04',
                'club': self.club.pk,
                'equipo': self.equipo.pk,
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Ya existe un deportista')


# ---------------------------------------------------------------------------
# Campeonatos, partidos, árbitros, asignaciones y sanciones
# ---------------------------------------------------------------------------


class CampeonatosPartidosTests(BaseAfoTestCase):
    def test_crear_campeonato(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('campeonato_crear'),
            {
                'nombre': 'Copa Invierno',
                'categoria': self.categoria.pk,
                'disciplina': 'Fútbol',
                'temporada': 2026,
                'modalidad': 'ELIMINACION',
                'fecha_inicio': '2026-06-01',
                'fecha_conclusion': '2026-07-01',
                'estado': 'PLANIFICADO',
                'reglamento': '',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Campeonato.objects.filter(nombre='Copa Invierno').exists())

    def test_campeonato_con_fechas_invertidas(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('campeonato_crear'),
            {
                'nombre': 'Copa Imposible',
                'categoria': self.categoria.pk,
                'disciplina': 'Fútbol',
                'temporada': 2026,
                'modalidad': 'LIGA',
                'fecha_inicio': '2026-07-01',
                'fecha_conclusion': '2026-06-01',
                'estado': 'PLANIFICADO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Campeonato.objects.filter(nombre='Copa Imposible').exists())

    def test_detalle_campeonato_muestra_tabla(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(
            reverse('campeonato_detalle', args=[self.campeonato.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Tabla de posiciones')

    def test_crear_partido(self):
        self.ingresar(self.admin)
        fecha = (timezone.now() + timedelta(days=8)).strftime('%Y-%m-%dT%H:%M')
        respuesta = self.client.post(
            reverse('partido_crear'),
            {
                'campeonato': self.campeonato.pk,
                'equipo_local': self.equipo2.pk,
                'equipo_visitante': self.equipo.pk,
                'fecha': fecha,
                'escenario': 'Cancha 2',
                'estado': 'Programado',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            Partido.objects.filter(escenario='Cancha 2').count(), 1
        )

    def test_partido_rechaza_mismo_equipo(self):
        self.ingresar(self.admin)
        fecha = (timezone.now() + timedelta(days=9)).strftime('%Y-%m-%dT%H:%M')
        respuesta = self.client.post(
            reverse('partido_crear'),
            {
                'campeonato': self.campeonato.pk,
                'equipo_local': self.equipo.pk,
                'equipo_visitante': self.equipo.pk,
                'fecha': fecha,
                'escenario': 'Cancha 3',
                'estado': 'Programado',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'debe ser distinto del local')

    def test_partido_rechaza_goles_incompletos(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('partido_editar', args=[self.partido.pk]),
            {
                'campeonato': self.campeonato.pk,
                'equipo_local': self.equipo.pk,
                'equipo_visitante': self.equipo2.pk,
                'fecha': self.fecha_partido.strftime('%Y-%m-%dT%H:%M'),
                'escenario': 'Estadio Municipal',
                'estado': 'Programado',
                'goles_local': 2,
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'goles de ambos equipos')

    def test_registrar_resultado_sincroniza_marcador(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('partido_editar', args=[self.partido.pk]),
            {
                'campeonato': self.campeonato.pk,
                'equipo_local': self.equipo.pk,
                'equipo_visitante': self.equipo2.pk,
                'fecha': self.fecha_partido.strftime('%Y-%m-%dT%H:%M'),
                'escenario': 'Estadio Municipal',
                'estado': 'Finalizado',
                'goles_local': 3,
                'goles_visitante': 1,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.partido.refresh_from_db()
        self.assertEqual(self.partido.resultado, '3 - 1')
        self.assertEqual(self.partido.marcador, '3 - 1')

    def test_ficha_de_partido_accesible(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('partido_detalle', args=[self.partido.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Estadio Municipal')

    def test_eliminar_partido(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('partido_eliminar', args=[self.partido.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Partido.objects.filter(pk=self.partido.pk).exists())


class ArbitrajeTests(BaseAfoTestCase):
    def test_codigo_de_arbitro_es_automatico(self):
        self.assertTrue(self.arbitro.codigo.startswith('ARB-'))

    def test_crear_arbitro(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('arbitro_crear'),
            {
                'nombre': 'Marco',
                'apellido': 'Vargas',
                'ci': '1000004',
                'telefono': '72222222',
                'categoria': 'NACIONAL',
                'especialidad': 'CENTRAL',
                'disponible': 'on',
                'estado': 'ACTIVO',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Arbitro.objects.filter(apellido='Vargas').exists())

    def test_designar_arbitro(self):
        self.ingresar(self.arbitro_user)
        respuesta = self.client.post(
            reverse('asignacion_crear'),
            {
                'partido': self.partido.pk,
                'arbitro': self.arbitro.pk,
                'rol': 'CENTRAL',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            AsignacionArbitro.objects.filter(
                partido=self.partido, arbitro=self.arbitro
            ).exists()
        )

    def test_no_permite_repetir_rol_en_el_partido(self):
        AsignacionArbitro.objects.create(
            partido=self.partido, arbitro=self.arbitro, rol='CENTRAL'
        )
        otro = Arbitro.objects.create(nombre='Raúl', apellido='Luna', ci='1000005')
        self.ingresar(self.arbitro_user)
        respuesta = self.client.post(
            reverse('asignacion_crear'),
            {'partido': self.partido.pk, 'arbitro': otro.pk, 'rol': 'CENTRAL'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'ya está cubierto')
        self.assertEqual(AsignacionArbitro.objects.count(), 1)

    def test_arbitro_no_disponible_no_se_designa(self):
        self.arbitro.disponible = False
        self.arbitro.save(update_fields=['disponible'])
        self.ingresar(self.arbitro_user)
        respuesta = self.client.post(
            reverse('asignacion_crear'),
            {
                'partido': self.partido.pk,
                'arbitro': self.arbitro.pk,
                'rol': 'ASISTENTE1',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'no disponible')
        self.assertEqual(AsignacionArbitro.objects.count(), 0)

    def test_crear_sancion(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('sancion_crear'),
            {
                'tipo': 'SUSPENSION',
                'deportista': self.deportista.pk,
                'descripcion': 'Acumulación de tarjetas',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'fecha_inicio': '2026-01-10',
                'fecha_fin': '2026-01-20',
                'estado': 'VIGENTE',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            Sancion.objects.filter(descripcion='Acumulación de tarjetas').exists()
        )

    def test_sancion_sin_sujeto_es_rechazada(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('sancion_crear'),
            {
                'tipo': 'MULTA',
                'descripcion': 'Sin responsable',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'estado': 'VIGENTE',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Indique el deportista o el club sancionado')


# ---------------------------------------------------------------------------
# Inscripciones, tesorería y comprobantes
# ---------------------------------------------------------------------------


class InscripcionesPagosTests(BaseAfoTestCase):
    def test_crear_inscripcion_por_equipo(self):
        self.ingresar(self.dirigente)
        respuesta = self.client.post(
            reverse('inscripcion_crear'),
            {
                'campeonato': self.campeonato.pk,
                'equipo': self.equipo.pk,
                'estado': 'PENDIENTE',
                'observaciones': '',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(
            Inscripcion.objects.filter(
                campeonato=self.campeonato, equipo=self.equipo
            ).exists()
        )

    def test_no_duplica_inscripcion_de_equipo(self):
        Inscripcion.objects.create(
            campeonato=self.campeonato, equipo=self.equipo
        )
        self.ingresar(self.dirigente)
        respuesta = self.client.post(
            reverse('inscripcion_crear'),
            {
                'campeonato': self.campeonato.pk,
                'equipo': self.equipo.pk,
                'estado': 'PENDIENTE',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'ya está inscrito')
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_aprobar_inscripcion(self):
        inscripcion = Inscripcion.objects.create(
            campeonato=self.campeonato, equipo=self.equipo
        )
        self.ingresar(self.dirigente)
        respuesta = self.client.post(
            reverse('inscripcion_estado', args=[inscripcion.pk, 'APROBADA'])
        )
        self.assertEqual(respuesta.status_code, 302)
        inscripcion.refresh_from_db()
        self.assertEqual(inscripcion.estado, 'APROBADA')

    def test_crear_pago(self):
        self.ingresar(self.tesorero)
        respuesta = self.client.post(
            reverse('pago_crear'),
            {
                'tipo': 'Cuota mensual',
                'monto': '200.50',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'club': self.club.pk,
                'comprobante': 'C-100',
                'estado': 'PAGADO',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Pago.objects.filter(comprobante='C-100').exists())

    def test_pago_rechaza_monto_cero(self):
        self.ingresar(self.tesorero)
        respuesta = self.client.post(
            reverse('pago_crear'),
            {
                'tipo': 'Cuota',
                'monto': '0',
                'fecha': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
                'club': self.club.pk,
                'estado': 'PAGADO',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'mayor que cero')

    def test_comprobante_imprimible(self):
        self.ingresar(self.tesorero)
        respuesta = self.client.get(
            reverse('pago_comprobante', args=[self.pago.pk])
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Comprobante de pago')
        self.assertContains(respuesta, 'C-001')

    def test_totales_de_tesoreria(self):
        Pago.objects.create(
            tipo='Pendiente', monto=Decimal('50.00'),
            fecha=timezone.now(), estado='PENDIENTE',
        )
        self.ingresar(self.tesorero)
        respuesta = self.client.get(reverse('tesoreria'))
        self.assertEqual(respuesta.context['total_cobrado'], Decimal('150.00'))
        self.assertEqual(respuesta.context['total_pendiente'], Decimal('50.00'))


# ---------------------------------------------------------------------------
# Reportes y exportación CSV
# ---------------------------------------------------------------------------


class ReportesTests(BaseAfoTestCase):
    def test_catalogo_de_reportes(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reportes'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Reporte de clubes')

    def test_reporte_de_clubes_con_datos(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_detalle', args=['clubes']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Club Deportivo Prueba')

    def test_exportacion_csv_con_bom_y_punto_y_coma(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_csv', args=['clubes']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('text/csv', respuesta['Content-Type'])
        self.assertIn('attachment', respuesta['Content-Disposition'])
        contenido = respuesta.content.decode('utf-8')
        self.assertTrue(contenido.startswith('\ufeff'))
        self.assertIn('Club;Estado;Presidente', contenido)
        self.assertIn('Club Deportivo Prueba', contenido)

    def test_reporte_financiero_restringido_para_arbitro(self):
        self.ingresar(self.arbitro_user)
        self.assertEqual(
            self.client.get(reverse('reporte_detalle', args=['pagos'])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('reporte_csv', args=['pagos'])).status_code,
            403,
        )

    def test_tesorero_accede_al_reporte_de_pagos(self):
        self.ingresar(self.tesorero)
        respuesta = self.client.get(reverse('reporte_detalle', args=['pagos']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'C-001')

    def test_reporte_inexistente_devuelve_403(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_detalle', args=['inventado']))
        self.assertEqual(respuesta.status_code, 403)

    def test_exportacion_pdf_institucional(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_pdf', args=['clubes']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta['Content-Type'], 'application/pdf'
        )
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertIn('afo-clubes-', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'%PDF'))
        self.assertGreater(len(respuesta.content), 1000)

    def test_exportacion_excel_xlsx(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_xlsx', args=['clubes']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(
            'spreadsheetml.sheet', respuesta['Content-Type']
        )
        self.assertIn('afo-clubes-', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'PK'))

    def test_exportaciones_financieras_restringidas_para_arbitro(self):
        self.ingresar(self.arbitro_user)
        self.assertEqual(
            self.client.get(reverse('reporte_pdf', args=['pagos'])).status_code,
            403,
        )
        self.assertEqual(
            self.client.get(reverse('reporte_xlsx', args=['pagos'])).status_code,
            403,
        )

    def test_exportacion_pdf_registra_auditoria(self):
        self.ingresar(self.admin)
        self.client.get(reverse('reporte_pdf', args=['clubes']))
        self.assertTrue(
            HistorialOperacion.objects.filter(
                modulo='reportes',
                accion='EXPORTAR',
                operacion__contains='PDF',
            ).exists()
        )

    def test_pdf_de_reporte_vacio_sigue_siendo_valido(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('reporte_pdf', args=['sanciones']))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.content.startswith(b'%PDF'))


# ---------------------------------------------------------------------------
# Usuarios, perfil y contraseñas
# ---------------------------------------------------------------------------


class UsuariosTests(BaseAfoTestCase):
    def test_crear_usuario_con_rol(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('usuario_crear'),
            {
                'username': 'nuevo_dirigente',
                'first_name': 'Nuevo',
                'last_name': 'Dirigente',
                'email': 'nuevo@afo.bo',
                'is_active': 'on',
                'grupo': self.grupo_dirigente.pk,
                'password1': CLAVE,
                'password2': CLAVE,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        usuario = User.objects.get(username='nuevo_dirigente')
        self.assertTrue(usuario.check_password(CLAVE))
        self.assertEqual(usuario.groups.first(), self.grupo_dirigente)

    def test_password_debil_es_rechazada(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('usuario_crear'),
            {
                'username': 'debil',
                'first_name': 'Débil',
                'last_name': 'Prueba',
                'is_active': 'on',
                'grupo': self.grupo_dirigente.pk,
                'password1': '12345678',
                'password2': '12345678',
            },
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username='debil').exists())

    def test_no_puede_eliminar_su_propia_cuenta(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(
            reverse('usuario_eliminar', args=[self.admin.pk])
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_restablecer_contrasena_de_otro_usuario(self):
        self.ingresar(self.admin)
        nueva = 'Afo#NuevaClave26'
        respuesta = self.client.post(
            reverse('usuario_password', args=[self.dirigente.pk]),
            {
                'old_password': CLAVE,
                'new_password1': nueva,
                'new_password2': nueva,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.dirigente.refresh_from_db()
        self.assertTrue(self.dirigente.check_password(nueva))

    def test_cambiar_contrasena_propia(self):
        self.ingresar(self.arbitro_user)
        nueva = 'Afo#MiClaveNueva26'
        respuesta = self.client.post(
            reverse('password_change'),
            {
                'old_password': CLAVE,
                'new_password1': nueva,
                'new_password2': nueva,
            },
        )
        self.assertRedirects(respuesta, reverse('perfil'))
        self.arbitro_user.refresh_from_db()
        self.assertTrue(self.arbitro_user.check_password(nueva))

    def test_actualizar_perfil(self):
        self.ingresar(self.dirigente)
        respuesta = self.client.post(
            reverse('perfil'),
            {
                'first_name': 'Dirigente',
                'last_name': 'Actualizado',
                'email': 'dirigente@afo.bo',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.dirigente.refresh_from_db()
        self.assertEqual(self.dirigente.last_name, 'Actualizado')

    def test_dirigente_no_lista_usuarios(self):
        self.ingresar(self.dirigente)
        self.assertEqual(self.client.get(reverse('usuarios')).status_code, 403)


# ---------------------------------------------------------------------------
# Panel, login y auditoría
# ---------------------------------------------------------------------------


class PanelLoginTests(BaseAfoTestCase):
    def test_panel_admin_muestra_bloques_financieros(self):
        self.ingresar(self.admin)
        respuesta = self.client.get(reverse('panel'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Hola,')
        self.assertContains(respuesta, 'Resumen económico')

    def test_panel_dirigente_oculta_finanzas(self):
        self.ingresar(self.dirigente)
        respuesta = self.client.get(reverse('panel'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, 'Resumen económico')

    def test_panel_refresca_tras_una_operacion(self):
        self.ingresar(self.admin)
        inicial = self.client.get(reverse('panel')).context['total_clubes']
        self.client.post(
            reverse('club_crear'),
            {'nombre': 'Club Cache', 'estado': 'ACTIVO'},
        )
        actualizado = self.client.get(reverse('panel')).context['total_clubes']
        self.assertEqual(actualizado, inicial + 1)

    def test_estadisticas_json_respetan_rol(self):
        self.ingresar(self.arbitro_user)
        respuesta = self.client.get(reverse('panel_estadisticas'))
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertFalse(datos['permite_finanzas'])
        self.assertIsNone(datos['ingresos_mes'])

    def test_login_valido_redirige_al_panel(self):
        respuesta = self.client.post(
            reverse('login'),
            {'username': 'tesorero_test', 'password': CLAVE},
        )
        self.assertRedirects(respuesta, reverse('panel'))

    def test_login_invalido_muestra_error(self):
        respuesta = self.client.post(
            reverse('login'),
            {'username': 'tesorero_test', 'password': 'incorrecta'},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Credenciales inválidas')

    def test_auditoria_registra_operaciones(self):
        self.ingresar(self.admin)
        self.client.post(
            reverse('club_crear'),
            {'nombre': 'Club Auditado', 'estado': 'ACTIVO'},
        )
        self.assertTrue(
            HistorialOperacion.objects.filter(
                modulo='clubes', accion='CREAR'
            ).exists()
        )
        respuesta = self.client.get(reverse('auditoria'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Club Auditado')

    def test_logout_cierra_sesion(self):
        self.ingresar(self.admin)
        respuesta = self.client.post(reverse('logout'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            self.client.get(reverse('panel')).status_code, 302
        )


# ---------------------------------------------------------------------------
# Reglas de negocio a nivel de modelo y portada pública
# ---------------------------------------------------------------------------


class ModelosTests(BaseAfoTestCase):
    def test_marcador_se_deriva_de_los_goles(self):
        partido = Partido.objects.create(
            campeonato=self.campeonato,
            equipo_local=self.equipo,
            equipo_visitante=self.equipo2,
            fecha=timezone.now() + timedelta(days=20),
            goles_local=2,
            goles_visitante=2,
        )
        self.assertEqual(partido.resultado, '2 - 2')
        self.assertEqual(partido.marcador, '2 - 2')

    def test_categoria_valida_rango_de_edad(self):
        categoria = Categoria(nombre='Inválida', edad_min=18, edad_max=12)
        with self.assertRaises(ValidationError):
            categoria.full_clean()

    def test_campeonato_valida_fechas(self):
        campeonato = Campeonato(
            nombre='Fechas invertidas',
            fecha_inicio=date(2026, 8, 1),
            fecha_conclusion=date(2026, 7, 1),
        )
        with self.assertRaises(ValidationError):
            campeonato.full_clean()

    def test_inscripcion_exige_sujeto(self):
        inscripcion = Inscripcion(campeonato=self.campeonato)
        with self.assertRaises(ValidationError):
            inscripcion.full_clean()

    def test_partido_no_admite_equipos_iguales(self):
        partido = Partido(
            equipo_local=self.equipo, equipo_visitante=self.equipo
        )
        with self.assertRaises(ValidationError):
            partido.full_clean()

    def test_portada_publica_responde(self):
        respuesta = self.client.get(reverse('index'))
        self.assertEqual(respuesta.status_code, 200)

    def test_directorio_publico_de_clubes(self):
        respuesta = self.client.get(reverse('clubes_publicos'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Club Deportivo Prueba')
