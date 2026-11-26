"""
Rutas de la aplicación core (Sistema de Gestión Deportiva AFO · Oruro).

Las rutas antiguas se conservan como alias para no romper enlaces ni
marcadores, pero apuntan a los módulos CRUD definitivos.
"""
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from . import views_admin as admin
from . import views_crud as crud

urlpatterns = [
    # ---------------------------------------------------------------- Público
    path('', views.index, name='index'),
    path('health/', views.health, name='health'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('clubes-publicos/', views.clubes_publicos, name='clubes_publicos'),

    # ------------------------------------------------------------------ Panel
    path('panel-general/', views.panel, name='panel'),
    path('panel-general/estadisticas/', views.panel_estadisticas, name='panel_estadisticas'),

    # ------------------------------------------------- Centros de sección
    path('gestion-deportiva/', views.gestion_deportiva, name='gestion_deportiva'),
    path('competencia/', views.competencia, name='competencia'),
    path('administracion/', views.administracion, name='administracion'),

    # ----------------------------------------------------------------- Clubes
    path('clubes/', crud.clubes, name='clubes'),
    path('clubes/nuevo/', crud.club_crear, name='club_crear'),
    path('clubes/<int:pk>/', crud.club_detalle, name='club_detalle'),
    path('clubes/<int:pk>/editar/', crud.club_editar, name='club_editar'),
    path('clubes/<int:pk>/eliminar/', crud.club_eliminar, name='club_eliminar'),
    path('clubes-equipos/', crud.clubes),

    # ------------------------------------------------- Canchas y escenarios
    path('canchas/', crud.canchas, name='canchas'),
    path('canchas/nueva/', crud.cancha_crear, name='cancha_crear'),
    path('canchas/<int:pk>/editar/', crud.cancha_editar, name='cancha_editar'),
    path('canchas/<int:pk>/eliminar/', crud.cancha_eliminar, name='cancha_eliminar'),

    # ---------------------------------------------------------------- Equipos
    path('equipos/', crud.equipos, name='equipos'),
    path('equipos/nuevo/', crud.equipo_crear, name='equipo_crear'),
    path('equipos/<int:pk>/editar/', crud.equipo_editar, name='equipo_editar'),
    path('equipos/<int:pk>/eliminar/', crud.equipo_eliminar, name='equipo_eliminar'),

    # ------------------------------------------------------------ Deportistas
    path('deportistas/', crud.deportistas, name='deportistas'),
    path('deportistas/nuevo/', crud.deportista_crear, name='deportista_crear'),
    path('deportistas/<int:pk>/', crud.deportista_detalle, name='deportista_detalle'),
    path('deportistas/<int:pk>/editar/', crud.deportista_editar, name='deportista_editar'),
    path('deportistas/<int:pk>/eliminar/', crud.deportista_eliminar, name='deportista_eliminar'),
    path('deportistas-fichajes/', crud.deportistas),

    # ------------------------------------------------------------- Categorías
    path('categorias/', crud.categorias, name='categorias'),
    path('categorias/nueva/', crud.categoria_crear, name='categoria_crear'),
    path('categorias/<int:pk>/editar/', crud.categoria_editar, name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/', crud.categoria_eliminar, name='categoria_eliminar'),

    # ------------------------------------------------------------ Campeonatos
    path('campeonatos/', crud.campeonatos, name='campeonatos'),
    path('campeonatos/nuevo/', crud.campeonato_crear, name='campeonato_crear'),
    path('campeonatos/<int:pk>/', crud.campeonato_detalle, name='campeonato_detalle'),
    path('campeonatos/<int:pk>/editar/', crud.campeonato_editar, name='campeonato_editar'),
    path('campeonatos/<int:pk>/eliminar/', crud.campeonato_eliminar, name='campeonato_eliminar'),
    path('campeonatos-fixture/', crud.campeonatos),

    # ----------------------------------------------------------- Inscripciones
    path('inscripciones/', crud.inscripciones, name='inscripciones'),
    path('inscripciones/nueva/', crud.inscripcion_crear, name='inscripcion_crear'),
    path('inscripciones/<int:pk>/editar/', crud.inscripcion_editar, name='inscripcion_editar'),
    path(
        'inscripciones/<int:pk>/estado/<str:estado>/',
        crud.inscripcion_estado,
        name='inscripcion_estado',
    ),
    path('inscripciones/<int:pk>/eliminar/', crud.inscripcion_eliminar, name='inscripcion_eliminar'),

    # ---------------------------------------------------------------- Partidos
    path('partidos/', crud.partidos, name='partidos'),
    path('partidos/nuevo/', crud.partido_crear, name='partido_crear'),
    path('partidos/<int:pk>/', views.partido_detalle, name='partido_detalle'),
    path('partidos/<int:pk>/editar/', crud.partido_editar, name='partido_editar'),
    path('partidos/<int:pk>/eliminar/', crud.partido_eliminar, name='partido_eliminar'),

    # ---------------------------------------------------------------- Árbitros
    path('arbitros/', crud.arbitros, name='arbitros'),
    path('arbitros/nuevo/', crud.arbitro_crear, name='arbitro_crear'),
    path('arbitros/<int:pk>/', crud.arbitro_detalle, name='arbitro_detalle'),
    path('arbitros/<int:pk>/editar/', crud.arbitro_editar, name='arbitro_editar'),
    path('arbitros/<int:pk>/eliminar/', crud.arbitro_eliminar, name='arbitro_eliminar'),
    path('arbitraje-designaciones/', crud.arbitros, name='arbitraje'),

    # ------------------------------------------------------------ Asignaciones
    path('asignaciones/', crud.asignaciones, name='asignaciones'),
    path('asignaciones/nueva/', crud.asignacion_crear, name='asignacion_crear'),
    path('asignaciones/<int:pk>/editar/', crud.asignacion_editar, name='asignacion_editar'),
    path('asignaciones/<int:pk>/eliminar/', crud.asignacion_eliminar, name='asignacion_eliminar'),

    # --------------------------------------------------------------- Sanciones
    path('sanciones/', crud.sanciones, name='sanciones'),
    path('sanciones/nueva/', crud.sancion_crear, name='sancion_crear'),
    path('sanciones/<int:pk>/editar/', crud.sancion_editar, name='sancion_editar'),
    path('sanciones/<int:pk>/eliminar/', crud.sancion_eliminar, name='sancion_eliminar'),

    # --------------------------------------------------------------- Tesorería
    path('tesoreria/', admin.tesoreria, name='tesoreria'),
    path('tesoreria/nuevo/', admin.pago_crear, name='pago_crear'),
    path('tesoreria/<int:pk>/editar/', admin.pago_editar, name='pago_editar'),
    path('tesoreria/<int:pk>/eliminar/', admin.pago_eliminar, name='pago_eliminar'),
    path('tesoreria/<int:pk>/comprobante/', admin.pago_comprobante, name='pago_comprobante'),
    path('tesoreria-pagos/', admin.tesoreria),

    # ---------------------------------------------------------------- Usuarios
    path('usuarios/', admin.usuarios, name='usuarios'),
    path('usuarios/nuevo/', admin.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:pk>/editar/', admin.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:pk>/password/', admin.usuario_password, name='usuario_password'),
    path('usuarios/<int:pk>/eliminar/', admin.usuario_eliminar, name='usuario_eliminar'),

    # --------------------------------------------------------- Perfil y clave
    path('perfil/', admin.perfil, name='perfil'),
    path(
        'perfil/password/',
        admin.CambiarPasswordView.as_view(),
        name='password_change',
    ),

    # ---------------------------------------------------------------- Reportes
    path('reportes/', admin.reportes, name='reportes'),
    path('reportes/<slug:clave>/', admin.reporte_detalle, name='reporte_detalle'),
    path('reportes/<slug:clave>/csv/', admin.reporte_csv, name='reporte_csv'),
    path('reportes/<slug:clave>/pdf/', admin.reporte_pdf, name='reporte_pdf'),
    path('reportes/<slug:clave>/xlsx/', admin.reporte_xlsx, name='reporte_xlsx'),

    # --------------------------------------------------------------- Auditoría
    path('auditoria/', admin.auditoria, name='auditoria'),
    path('auditoria-usuarios/', admin.auditoria),
    path('accesos/', admin.accesos, name='accesos'),
    path('accesos-sesiones/', admin.accesos, name='accesos_sesiones'),

    # Recuperación de contraseña
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='auth/password_reset_form.html',
            email_template_name='auth/password_reset_email.html',
            subject_template_name='auth/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='auth/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='auth/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='auth/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
]
