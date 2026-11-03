"""
Vistas de la aplicación core.

Traduce el front-end estático original (HTML/CSS/JS) en páginas servidas
por Django, integrando autenticación real sobre django.contrib.auth.
"""
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import make_aware, is_naive
from .models import Categoria, Club, Deportista
from django.db import transaction

from .models import (
    Club,
    Equipo,
    Deportista,
    Campeonato,
    Partido,
    Pago,
    Sancion,
    Arbitro,
    Inscripcion,
)

ROLES_LABELS = {
    'ADMIN': 'Administrador General de la A.F.O.',
    'DIRIGENTE': 'Dirigente de Club Afiliado',
    'ARBITRO': 'Comisión Técnica / Árbitros',
    'TESORERO': 'Tesorero / Finanzas Institucionales',
}
ROLES_GROUPS = {
    'ADMIN': 'Administrador General',
    'DIRIGENTE': 'Dirigente de Club Afiliado',
    'ARBITRO': 'Comisión Técnica / Árbitros',
    'TESORERO': 'Tesorero / Finanzas Institucionales',
}

def index(request):
    """Portada pública con el grid de módulos."""
    return render(request, 'index.html')


def login_view(request):
    """Autenticación institucional (formulario del front original, ahora real)."""
    if request.user.is_authenticated:
        return redirect('panel')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '').strip().upper()
        next_url = request.POST.get('next') or request.GET.get('next') or 'panel'

        user = authenticate(request, username=username, password=password)

        if user is None:
            error = 'Credenciales inválidas. Verifique el usuario o código institucional y la contraseña.'
        elif not user.is_active:
            error = 'La cuenta federativa está inhabilitada. Contacte a Secretaría General.'
        elif role and role not in ROLES_GROUPS:
            error = 'El rol seleccionado no es válido.'
        elif role and not user.is_superuser and not user.groups.filter(name=ROLES_GROUPS[role]).exists():
            error = 'El rol seleccionado no corresponde a los permisos de la cuenta.'
        else:
            auth_login(request, user)
            request.session['rol'] = role if role in ROLES_LABELS else (
                user.groups.values_list('name', flat=True).first() if user.groups.exists() else 'USUARIO'
            )
            return redirect(next_url)

    return render(request, 'login.html', {
        'error': error,
        'roles': ROLES_LABELS,
        'next': request.GET.get('next', ''),
    })

def logout_view(request):
    """Cierre de sesión institucional."""
    auth_logout(request)
    return redirect('index')


def _shell(request, template, contexto=None):
    contexto = contexto or {}
    contexto['rol_label'] = ROLES_LABELS.get(
        request.session.get('rol'), ''
    )
    return render(request, template, contexto)

@login_required
def panel(request):
    ahora = timezone.now()

    # Estadísticas generales
    total_clubes = Club.objects.count()
    total_equipos = Equipo.objects.count()
    total_deportistas = Deportista.objects.count()
    total_campeonatos = Campeonato.objects.count()
    total_arbitros = Arbitro.objects.count()

    # Planillas pendientes
    # Pendiente de implementar el modelo Planilla
    planillas_pendientes = 0

    # Partidos próximos
    proximos_partidos = Partido.objects.filter(
        fecha__gte=ahora
    ).select_related(
        'campeonato',
        'equipo_local',
        'equipo_visitante'
    ).order_by('fecha')[:5]

    total_partidos_proximos = Partido.objects.filter(
        fecha__gte=ahora
    ).count()

    # Recaudación del mes actual
    recaudacion_mes = Pago.objects.filter(
        fecha__year=ahora.year,
        fecha__month=ahora.month
    ).aggregate(
        total=Sum('monto')
    )['total'] or 0

    # Otros registros
    total_inscripciones = Inscripcion.objects.count()
    total_sanciones = Sancion.objects.count()

    contexto = {
        'rol_label': ROLES_LABELS.get(
            request.session.get('rol'), ''
        ),
        'total_clubes': total_clubes,
        'total_equipos': total_equipos,
        'total_deportistas': total_deportistas,
        'planillas_pendientes': planillas_pendientes,
        'total_campeonatos': total_campeonatos,
        'total_arbitros': total_arbitros,
        'proximos_partidos': proximos_partidos,
        'total_partidos_proximos': total_partidos_proximos,
        'recaudacion_mes': recaudacion_mes,
        'total_inscripciones': total_inscripciones,
        'total_sanciones': total_sanciones,
    }

    return render(request, 'panel_general.html', contexto)
@login_required
def clubes_publicos(request):

    clubes_registrados = Club.objects.all().order_by('nombre').prefetch_related(
        'equipo_set',
        'deportista_set'
    )

    contexto = {
        'clubes_registrados': clubes_registrados,
        'total_clubes': Club.objects.count(),
        'total_equipos': Equipo.objects.count(),
        'total_deportistas': Deportista.objects.count(),
    }

    return render(request, 'clubes_publicos.html', contexto)
def clubes(request):

    if request.method == 'POST':

        accion = request.POST.get('accion')

        # REGISTRAR CLUB Y EQUIPOS
        if accion == 'registrar_club':

            nombre = request.POST.get('nombre', '').strip()

            if nombre:

                equipos_seleccionados = request.POST.getlist('equipos')

                with transaction.atomic():

                    nuevo_club = Club.objects.create(
                        nombre=nombre,
                        fundacion=request.POST.get('fundacion') or None,
                        presidente=request.POST.get('presidente', '').strip(),
                        direccion=request.POST.get('direccion', '').strip(),
                        telefono=request.POST.get('telefono', '').strip(),
                        categoria_ingreso=request.POST.get('categoria_ingreso', ''),
                        nit_personeria=request.POST.get('nit_personeria', '').strip(),
                        estado_juridico=request.POST.get('estado_juridico', '').strip()
                    )

                    for nombre_equipo in equipos_seleccionados:
                        Equipo.objects.create(
                            nombre=nombre_equipo,
                            club=nuevo_club
                        )

                return redirect('clubes')

        # ELIMINAR CLUB
        elif accion == 'eliminar_club':

            club_id = request.POST.get('club_id')

            club = Club.objects.filter(id=club_id).first()

            if club:
                club.delete()

            return redirect('clubes')

    clubes_registrados = Club.objects.all().order_by('nombre').prefetch_related(
        'equipo_set',            
        'deportista_set'
    )
    contexto = {
        'clubes_registrados': clubes_registrados,
    }

    return _shell(request, 'clubes_equipos.html', contexto)
@login_required
def clubes(request):

    if request.method == 'POST':

        accion = request.POST.get('accion')

        # REGISTRAR CLUB Y EQUIPOS
        if accion == 'registrar_club':

            nombre = request.POST.get('nombre', '').strip()

            if nombre:

                equipos_seleccionados = request.POST.getlist('equipos')

                with transaction.atomic():

                    nuevo_club = Club.objects.create(
                        nombre=nombre,
                        fundacion=request.POST.get('fundacion') or None,
                        presidente=request.POST.get('presidente', '').strip(),
                        direccion=request.POST.get('direccion', '').strip(),
                        telefono=request.POST.get('telefono', '').strip(),
                        categoria_ingreso=request.POST.get('categoria_ingreso', ''),
                        nit_personeria=request.POST.get('nit_personeria', '').strip(),
                        estado_juridico=request.POST.get('estado_juridico', '').strip()
                    )

                    for nombre_equipo in equipos_seleccionados:
                        Equipo.objects.create(
                            nombre=nombre_equipo,
                            club=nuevo_club
                        )

                return redirect('clubes')

        # ELIMINAR CLUB
        elif accion == 'eliminar_club':

            club_id = request.POST.get('club_id')

            club = Club.objects.filter(id=club_id).first()

            if club:
                club.delete()

            return redirect('clubes')

    clubes_registrados = Club.objects.all().order_by('nombre').prefetch_related(
        'equipo_set',
        'deportista_set'
    )
    contexto = {
        'clubes_registrados': clubes_registrados,
    }

    return _shell(request, 'clubes_equipos.html', contexto)


@login_required
def campeonatos(request):
    error = None

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # REGISTRAR NUEVO CAMPEONATO
        if accion == 'crear_campeonato':
            nombre = request.POST.get('nombre', '').strip()
            disciplina = request.POST.get('disciplina', '').strip()
            categoria_nombre = request.POST.get('categoria', '').strip()
            fecha_inicio = parse_date(request.POST.get('fecha_inicio', ''))
            fecha_conclusion = parse_date(request.POST.get('fecha_conclusion', ''))

            if not nombre or not disciplina or not categoria_nombre:
                error = 'Completa el nombre, disciplina y categoría.'

            elif fecha_inicio and fecha_conclusion and fecha_conclusion < fecha_inicio:
                error = 'La fecha de conclusión no puede ser anterior al inicio.'

            else:
                categoria, creada = Categoria.objects.get_or_create(
                    nombre=categoria_nombre
                )

                Campeonato.objects.create(
                    nombre=nombre,
                    disciplina=disciplina,
                    categoria=categoria,
                    fecha_inicio=fecha_inicio,
                    fecha_conclusion=fecha_conclusion
                )

                return redirect('campeonatos')

        # PROGRAMAR NUEVO PARTIDO
        elif accion == 'programar_partido':
            campeonato_id = request.POST.get('campeonato')
            local_id = request.POST.get('equipo_local')
            visitante_id = request.POST.get('equipo_visitante')
            fecha = parse_datetime(request.POST.get('fecha', ''))
            escenario = request.POST.get('escenario', '').strip()
            terna = request.POST.get('terna_arbitral', '').strip()

            if not all([campeonato_id, local_id, visitante_id, fecha, escenario]):
                error = 'Completa todos los campos obligatorios del partido.'

            elif local_id == visitante_id:
                error = 'El equipo local y visitante no pueden ser el mismo.'

            else:
                campeonato = Campeonato.objects.filter(id=campeonato_id).first()
                equipo_local = Equipo.objects.filter(id=local_id).first()
                equipo_visitante = Equipo.objects.filter(id=visitante_id).first()

                if not campeonato or not equipo_local or not equipo_visitante:
                    error = 'El campeonato o alguno de los equipos seleccionados no existe.'

                else:
                    if is_naive(fecha):
                        fecha = make_aware(fecha)

                    Partido.objects.create(
                        campeonato=campeonato,
                        equipo_local=equipo_local,
                        equipo_visitante=equipo_visitante,
                        fecha=fecha,
                        escenario=escenario,
                        terna_arbitral=terna,
                        estado='Programado'
                    )

                    return redirect('campeonatos')

    # FILTRAR PARTIDOS POR CAMPEONATO
    campeonato_id = request.GET.get('campeonato')

    campeonato_actual = None

    partidos = Partido.objects.select_related(
        'campeonato',
        'equipo_local',
        'equipo_visitante'
    )

    if campeonato_id:
        campeonato_actual = Campeonato.objects.filter(
            id=campeonato_id
        ).first()

        if campeonato_actual:
            partidos = partidos.filter(
                campeonato=campeonato_actual
            )

    # DATOS QUE SE ENVÍAN AL HTML
    contexto = {
        'campeonatos_registrados': Campeonato.objects.select_related(
            'categoria'
        ).order_by('-id'),

        'partidos_registrados': partidos.order_by('fecha'),

        'campeonato_actual': campeonato_actual,

        'categorias': Categoria.objects.all().order_by('nombre'),

        'equipos': Equipo.objects.select_related('club').order_by('nombre'),

        'error': error,
    }

    return _shell(request, 'campeonatos_fixture.html', contexto)



@login_required
def arbitraje(request):
    error = None
    exito = None

    if request.method == 'POST':
        print("=== FORMULARIO DE ARBITRAJE RECIBIDO ===")
        print("DATOS RECIBIDOS:", request.POST)

        accion = request.POST.get('accion')
        print("ACCION:", accion)

        if accion == 'registrar_arbitro':
            nombre = request.POST.get('nombre', '').strip()
            apellido = request.POST.get('apellido', '').strip()
            ci = request.POST.get('ci', '').strip()

            if not nombre or not apellido or not ci:
                error = 'Completa los nombres, apellidos y carnet de identidad.'

            elif Arbitro.objects.filter(ci=ci).exists():
                error = 'Ya existe un árbitro registrado con ese carnet.'

            else:
                Arbitro.objects.create(
                    nombre=nombre,
                    apellido=apellido,
                    ci=ci,
                    fecha_nacimiento=parse_date(
                        request.POST.get('fecha_nacimiento', '')
                    ),
                    telefono=request.POST.get('telefono', '').strip(),
                    correo=request.POST.get('correo', '').strip(),
                    categoria=request.POST.get('categoria', 'DEPARTAMENTAL'),
                    especialidad=request.POST.get('especialidad', 'CENTRAL'),
                    estado='ACTIVO'
                )

                return redirect('arbitraje')

    busqueda = request.GET.get('buscar', '').strip()
    categoria = request.GET.get('categoria', '').strip()
    estado = request.GET.get('estado', '').strip()

    arbitros = Arbitro.objects.all().order_by('apellido', 'nombre')

    if busqueda:
        arbitros = arbitros.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(ci__icontains=busqueda) |
            Q(codigo__icontains=busqueda)
        )

    if categoria:
        arbitros = arbitros.filter(categoria=categoria)

    if estado:
        arbitros = arbitros.filter(estado=estado)

    contexto = {
        'arbitros': arbitros,
        'total_arbitros': Arbitro.objects.count(),
        'total_fifa': Arbitro.objects.filter(categoria='FIFA').count(),
        'total_nacionales': Arbitro.objects.filter(categoria='NACIONAL').count(),
        'total_departamentales': Arbitro.objects.filter(categoria='DEPARTAMENTAL').count(),
        'total_activos': Arbitro.objects.filter(estado='ACTIVO').count(),
        'busqueda': busqueda,
        'categoria_actual': categoria,
        'estado_actual': estado,
        'error': error,
        'exito': exito,
    }

    return _shell(request, 'arbitraje_designaciones.html', contexto)



@login_required
def deportistas(request):
    error = None

    # REGISTRAR NUEVO DEPORTISTA
    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'registrar_deportista':
            nombre = request.POST.get('nombre', '').strip()
            apellido = request.POST.get('apellido', '').strip()
            fecha_nacimiento = request.POST.get('fecha_nacimiento', '').strip()
            genero = request.POST.get('genero', '').strip()
            club_id = request.POST.get('club', '').strip()

            if not nombre or not apellido:
                error = 'El nombre y apellido son obligatorios.'

            elif not fecha_nacimiento:
                error = 'La fecha de nacimiento es obligatoria.'

            else:
                club = None

                if club_id:
                    club = Club.objects.filter(pk=club_id).first()

                    if club is None:
                        error = 'El club seleccionado no existe.'

                if error is None:
                    Deportista.objects.create(
                        nombre=nombre,
                        apellido=apellido,
                        fecha_nacimiento=parse_date(fecha_nacimiento),
                        genero=genero or None,
                        club=club
                    )

                    return redirect('deportistas')

    # CONSULTAR DATOS DE POSTGRESQL
    deportistas_registrados = Deportista.objects.select_related(
        'club'
    ).order_by('apellido', 'nombre')

    contexto = {
        'clubes': Club.objects.all().order_by('nombre'),
        'deportistas': deportistas_registrados,
        'total_deportistas': Deportista.objects.count(),
        'error': error,
    }

    return _shell(request, 'deportistas_fichajes.html', contexto)



@login_required
def tesoreria(request):
    return _shell(request, 'tesoreria_pagos.html')


@login_required
def auditoria(request):
    return _shell(request, 'auditoria_usuarios.html')