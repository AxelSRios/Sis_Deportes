"""
Vistas de la aplicación core.

Traduce el front-end estático original (HTML/CSS/JS) en páginas servidas
por Django, integrando autenticación real sobre django.contrib.auth.
"""
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.text import slugify
from django.utils.timezone import make_aware, is_naive

from .cache_utils import version_cache
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

ROLES_LABELS = {
    'ADMIN': 'Administrador General de la A.F.O.',
    'DIRIGENTE': 'Dirigente de Club Afiliado',
    'ARBITRO': 'Comisión Técnica / Árbitros',
    'TESORERO': 'Tesorero / Finanzas Institucionales',
    'USUARIO': 'Usuario institucional',
}
# Nombres de grupo aceptados para cada rol. El rol se deduce del usuario,
# nunca se elige en el formulario de acceso.
ROLE_GROUP_ALIASES = {
    'ADMIN': {'ADMIN', 'Administrador General'},
    'DIRIGENTE': {'DIRIGENTE', 'Dirigente de Club Afiliado'},
    'ARBITRO': {'ARBITRO', 'Comisión Técnica / Árbitros'},
    'TESORERO': {'TESORERO', 'Tesorero / Finanzas Institucionales'},
}

LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


def _resolve_role(user):
    """Deduce el rol institucional a partir de los grupos del usuario."""
    if user.is_superuser:
        return 'ADMIN'
    group_names = set(user.groups.values_list('name', flat=True))
    for role, aliases in ROLE_GROUP_ALIASES.items():
        if group_names & aliases:
            return role
    return 'USUARIO'


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or 'desconocida'


def _throttle_key(request, username):
    return f'afo:login-fail:{_client_ip(request)}:{username.lower()}'


def _remaining_attempts(request, username):
    return max(0, LOGIN_MAX_ATTEMPTS - cache.get(_throttle_key(request, username), 0))


def _register_login_failure(request, username):
    key = _throttle_key(request, username)
    attempts = cache.get(key, 0) + 1
    cache.set(key, attempts, LOGIN_LOCKOUT_SECONDS)


def _clear_login_failures(request, username):
    cache.delete(_throttle_key(request, username))


def _safe_next(request, candidate):
    """Devuelve `next` solo si es una URL local y segura."""
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return ''


def _register_login_audit(user, role, request):
    """Registra el acceso sin bloquear el inicio de sesión si falla."""
    try:
        HistorialOperacion.objects.create(
            usuario=user,
            operacion=f"Inicio de sesión · rol {role} · IP {_client_ip(request)}",
            fecha=timezone.now(),
        )
    except Exception:
        pass


def index(request):
    """Portada pública con la actualidad deportiva de la AFO."""
    ahora = timezone.now()

    proximos_partidos = list(
        Partido.objects.filter(fecha__gte=ahora)
        .select_related('campeonato', 'equipo_local__club', 'equipo_visitante__club')
        .order_by('fecha')[:4]
    )
    proximo_partido = proximos_partidos[0] if proximos_partidos else None

    campeonatos = (
        Campeonato.objects.select_related('categoria')
        .annotate(total_partidos=Count('partido'))
        .order_by('-fecha_inicio', '-id')[:4]
    )

    clubes_destacados = (
        Club.objects.annotate(
            total_equipos=Count('equipo', distinct=True),
            total_deportistas=Count('deportista', distinct=True),
        )
        .order_by('-total_equipos', 'nombre')[:8]
    )

    resultados_recientes = (
        Partido.objects.exclude(Q(resultado__isnull=True) | Q(resultado=''))
        .select_related('campeonato', 'equipo_local', 'equipo_visitante')
        .order_by('-fecha')[:4]
    )

    contexto = {
        'proximos_partidos': proximos_partidos,
        'proximo_partido': proximo_partido,
        'campeonatos': campeonatos,
        'clubes_destacados': clubes_destacados,
        'resultados_recientes': resultados_recientes,
        'total_clubes': Club.objects.count(),
        'total_equipos': Equipo.objects.count(),
        'total_deportistas': Deportista.objects.count(),
        'total_campeonatos': Campeonato.objects.count(),
        'total_arbitros': Arbitro.objects.count(),
        'total_partidos_programados': Partido.objects.filter(fecha__gte=ahora).count(),
        'temporada_actual': timezone.localdate().year,
    }

    return render(request, 'index.html', contexto)


def login_view(request):
    """Autenticación institucional con rol derivado de los grupos del usuario."""
    if request.user.is_authenticated:
        return redirect('panel')

    error = None
    username = ''
    remember = False
    next_url = _safe_next(
        request,
        request.POST.get('next') or request.GET.get('next') or '',
    )

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember = request.POST.get('remember') == 'on'

        if _remaining_attempts(request, username) <= 0:
            error = (
                'Demasiados intentos fallidos. Espere 15 minutos o contacte '
                'a Secretaría General.'
            )
        else:
            user = authenticate(request, username=username, password=password)

            if user is None:
                _register_login_failure(request, username)
                restantes = _remaining_attempts(request, username)
                error = (
                    'Credenciales inválidas. Verifique el usuario o código '
                    'institucional y la contraseña.'
                )
                if restantes <= 2:
                    error += f' Le quedan {restantes} intento(s).'
            elif not user.is_active:
                error = (
                    'La cuenta federativa está inhabilitada. '
                    'Contacte a Secretaría General.'
                )
            else:
                _clear_login_failures(request, username)
                auth_login(request, user)
                role = _resolve_role(user)
                request.session['rol'] = role
                # Sesión de 14 días solo si marca "recordarme"; si no, al cerrar.
                request.session.set_expiry(60 * 60 * 24 * 14 if remember else 0)
                _register_login_audit(user, role, request)
                return redirect(next_url or 'panel')

    return render(request, 'login.html', {
        'error': error,
        'next': next_url,
        'username': username,
        'remember': remember,
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


# ===========================================================================
# Panel General · utilidades compartidas entre la vista y el endpoint JSON
# ===========================================================================

# Permisos por responsabilidad institucional.
ROLES_FINANZAS = {'ADMIN', 'TESORERO'}
ROLES_AUDITORIA = {'ADMIN'}

# Orden de los bloques del panel según la responsabilidad del rol. Se resuelve
# en Python para que la plantilla solo recorra una lista de parciales.
ORDEN_PANEL = {
    'ADMIN': (
        'kpis', 'modulos', 'pendientes', 'graficos', 'operativo',
        'campeonatos', 'resultados', 'economia',
    ),
    'TESORERO': (
        'economia', 'kpis', 'modulos', 'pendientes', 'graficos',
        'operativo', 'campeonatos', 'resultados',
    ),
    'ARBITRO': (
        'pendientes', 'operativo', 'resultados',
        'kpis', 'modulos', 'graficos', 'campeonatos',
    ),
    'DIRIGENTE': (
        'kpis', 'modulos', 'pendientes', 'operativo', 'graficos',
        'campeonatos', 'resultados',
    ),
}

MESES_ABREV = [
    'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
    'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic',
]

# Marcadores del tipo "2-1", "2 : 1", "2x1" o "2 – 1".
_RESULTADO_RE = re.compile(r'(\d{1,2})\s*[-–—:xX]\s*(\d{1,2})')


def _user_role(request):
    """Rol efectivo del usuario: sesión o, en su defecto, sus grupos."""
    rol = request.session.get('rol')
    if rol in ROLES_LABELS:
        return rol
    return _resolve_role(request.user)


def _forbidden(request, mensaje):
    """Respuesta 403 con el diseño institucional."""
    return render(
        request,
        '403.html',
        {
            'mensaje': mensaje,
            'rol_label': ROLES_LABELS.get(_user_role(request), ''),
        },
        status=403,
    )


def _log_operation(user, operacion):
    """Registra una operación en HistorialOperacion sin romper la vista."""
    try:
        HistorialOperacion.objects.create(
            usuario=user if getattr(user, 'is_authenticated', False) else None,
            operacion=operacion,
            fecha=timezone.now(),
        )
    except Exception:
        pass


def _parse_anio(request):
    """Año del filtro de gráficos, acotado a un rango razonable."""
    actual = timezone.localdate().year
    crudo = request.GET.get('anio')
    try:
        anio = int(crudo)
    except (TypeError, ValueError):
        return actual
    if anio < 1990 or anio > actual + 1:
        return actual
    return anio


def _anios_disponibles(incluir=None):
    """Años con información real en la base, más el año en curso y el filtrado."""
    anios = {timezone.localdate().year}
    if incluir:
        anios.add(incluir)
    fuentes = (
        (Partido, 'fecha'),
        (Pago, 'fecha'),
        (Deportista, 'fecha_registro'),
        (Campeonato, 'fecha_inicio'),
    )
    for modelo, campo in fuentes:
        try:
            valores = modelo.objects.filter(
                **{f'{campo}__isnull': False}
            ).dates(campo, 'year')
            for valor in valores:
                anios.add(valor.year)
        except Exception:
            continue
    return sorted(anios, reverse=True)


def _partidos_disputados(queryset=None):
    """Partidos con marcador registrado o marcados como finalizados."""
    queryset = queryset if queryset is not None else Partido.objects.all()
    return queryset.filter(
        Q(estado__iexact='finalizado')
        | (Q(resultado__isnull=False) & ~Q(resultado=''))
    )


def _marcador_partido(texto):
    """Interpreta el campo libre `resultado` como marcador local-visitante."""
    if not texto:
        return None
    coincidencia = _RESULTADO_RE.search(str(texto))
    if not coincidencia:
        return None
    return {
        'local': int(coincidencia.group(1)),
        'visitante': int(coincidencia.group(2)),
    }


def _estado_campeonato(campeonato, hoy):
    """Estado institucional; si no está definido, se deriva de las fechas."""
    if campeonato.estado:
        return campeonato.get_estado_display()
    if campeonato.fecha_conclusion and campeonato.fecha_conclusion < hoy:
        return 'Finalizado'
    if campeonato.fecha_inicio and campeonato.fecha_inicio <= hoy:
        return 'En curso'
    if campeonato.fecha_inicio:
        return 'Planificado'
    return 'Sin fechas'


def _serie_mensual(queryset, campo, funcion, anio):
    """Doce valores (Ene..Dic) para el año indicado, con ceros incluidos."""
    filas = (
        queryset.filter(**{f'{campo}__year': anio})
        .annotate(_mes=TruncMonth(campo))
        .values('_mes')
        .annotate(_total=funcion)
        .order_by('_mes')
    )
    valores = [0] * 12
    for fila in filas:
        mes = fila['_mes']
        if mes is None:
            continue
        total = fila['_total'] or 0
        valores[mes.month - 1] = float(total)
    return valores


def _panel_charts(request, anio):
    """Series reales del panel, cacheadas por rol, año y versión de datos."""
    rol = _user_role(request)
    clave = f'afo:panel-charts:{version_cache()}:{rol}:{anio}'
    datos = cache.get(clave)
    if datos is None:
        datos = _panel_charts_calculo(request, anio)
        cache.set(clave, datos, 300)
    return datos


def _panel_charts_calculo(request, anio):
    """Series reales para los cinco gráficos del panel."""
    rol = _user_role(request)

    # 1) Deportistas registrados por mes.
    deportistas_mes = _serie_mensual(
        Deportista.objects.all(), 'fecha_registro', Count('id'), anio
    )

    # 2) Partidos disputados por campeonato.
    filas_campeonato = (
        _partidos_disputados()
        .filter(fecha__year=anio)
        .values('campeonato__nombre')
        .annotate(total=Count('id'))
        .order_by('-total')[:8]
    )
    partidos_campeonato = {
        'labels': [
            (fila['campeonato__nombre'] or 'Sin campeonato')
            for fila in filas_campeonato
        ],
        'data': [fila['total'] for fila in filas_campeonato],
        'total': sum(fila['total'] for fila in filas_campeonato),
    }

    # 3) Resultados: victoria local, empate o victoria visitante.
    conteo = {'local': 0, 'empate': 0, 'visitante': 0, 'sin_marcador': 0}
    textos = (
        _partidos_disputados()
        .filter(fecha__year=anio)
        .values_list('resultado', flat=True)
    )
    for texto in textos.iterator():
        marcador = _marcador_partido(texto)
        if marcador is None:
            conteo['sin_marcador'] += 1
        elif marcador['local'] > marcador['visitante']:
            conteo['local'] += 1
        elif marcador['local'] == marcador['visitante']:
            conteo['empate'] += 1
        else:
            conteo['visitante'] += 1

    resultados = {
        'labels': [
            'Victoria local', 'Empate', 'Victoria visitante', 'Sin marcador legible',
        ],
        'data': [
            conteo['local'], conteo['empate'],
            conteo['visitante'], conteo['sin_marcador'],
        ],
        'total': sum(conteo.values()),
    }

    # 4) Ingresos económicos por mes (solo roles financieros).
    ingresos_mes = None
    if rol in ROLES_FINANZAS:
        valores = _serie_mensual(
            Pago.objects.all(), 'fecha', Sum('monto'), anio
        )
        ingresos_mes = {
            'labels': MESES_ABREV,
            'data': valores,
            'total': round(sum(valores), 2),
        }

    # 5) Clubes y equipos registrados (clubes con más estructura).
    clubes = (
        Club.objects.annotate(
            n_equipos=Count('equipo', distinct=True),
            n_deportistas=Count('deportista', distinct=True),
        )
        .order_by('-n_equipos', '-n_deportistas', 'nombre')[:8]
    )
    clubes_equipos = {
        'labels': [club.nombre for club in clubes],
        'equipos': [club.n_equipos for club in clubes],
        'deportistas': [club.n_deportistas for club in clubes],
        'total': sum(club.n_equipos + club.n_deportistas for club in clubes),
    }

    return {
        'meses': MESES_ABREV,
        'anio': anio,
        'deportistas_mes': {
            'labels': MESES_ABREV,
            'data': deportistas_mes,
            'total': sum(deportistas_mes),
        },
        'partidos_campeonato': partidos_campeonato,
        'resultados': resultados,
        'ingresos_mes': ingresos_mes,
        'clubes_equipos': clubes_equipos,
        'permite_finanzas': rol in ROLES_FINANZAS,
    }


def _registrar_pago(request):
    """Crea un Pago desde el panel. Devuelve un mensaje de error o None."""
    tipo = (request.POST.get('tipo') or '').strip()
    if not tipo:
        return 'Indique el concepto o tipo de pago.'

    monto_texto = (request.POST.get('monto') or '').strip().replace(',', '.')
    try:
        monto = Decimal(monto_texto)
    except (InvalidOperation, ValueError):
        return 'El monto ingresado no es válido.'

    if monto <= 0:
        return 'El monto debe ser mayor que cero.'

    fecha = parse_datetime(request.POST.get('fecha') or '')
    if fecha is None:
        fecha = timezone.now()
    elif is_naive(fecha):
        fecha = make_aware(fecha)

    deportista = None
    deportista_id = (request.POST.get('deportista') or '').strip()
    if deportista_id:
        deportista = Deportista.objects.filter(pk=deportista_id).first()
        if deportista is None:
            return 'El deportista seleccionado no existe.'

    pago = Pago.objects.create(
        deportista=deportista,
        monto=monto,
        fecha=fecha,
        tipo=tipo,
    )
    _log_operation(
        request.user,
        f'Registro de pago · Bs {pago.monto} · {tipo} · '
        f'{deportista or "Sin deportista asociado"}',
    )
    return None


@login_required
def panel(request):
    """Panel general: resumen operativo con datos reales del sistema."""
    ahora = timezone.now()
    hoy = timezone.localdate()
    rol = _user_role(request)
    anio = _parse_anio(request)

    # Registro de pago desde el propio panel (solo ADMIN / TESORERO).
    if request.method == 'POST' and request.POST.get('accion') == 'registrar_pago':
        if rol not in ROLES_FINANZAS:
            return _forbidden(
                request,
                'Su rol no tiene permisos para registrar pagos.',
            )
        error = _registrar_pago(request)
        if error:
            messages.error(request, error)
        else:
            messages.success(
                request,
                'Pago registrado en la caja institucional. '
                'El movimiento ya figura en la actividad reciente.',
            )
        return redirect('panel')

    # Contexto cacheado por rol, año, fecha y usuario (cuando la actividad
    # reciente es privada). Cualquier escritura incrementa la versión y lo
    # descarta, así que nunca se muestran datos viejos tras una operación.
    clave_panel = (
        f'afo:panel:{version_cache()}:{rol}:{anio}:{hoy.isoformat()}'
    )
    if rol not in ROLES_AUDITORIA:
        clave_panel += f':{request.user.pk}'
    cacheado = cache.get(clave_panel)
    if cacheado is not None:
        cacheado['usuario_nombre'] = (
            request.user.get_full_name() or request.user.username
        )
        return render(request, 'panel_general.html', cacheado)

    charts = _panel_charts(request, anio)
    puede_ver_finanzas = rol in ROLES_FINANZAS

    # --- Indicadores generales (una consulta agregada por modelo) -------------
    club_stats = Club.objects.aggregate(
        total=Count('pk'),
        activos=Count('pk', filter=Q(estado='ACTIVO')),
    )
    total_clubes = club_stats['total']
    clubes_activos = club_stats['activos']

    equipo_stats = Equipo.objects.aggregate(
        total=Count('pk'),
        con_club=Count('pk', filter=Q(club__isnull=False)),
    )
    total_equipos = equipo_stats['total']
    equipos_con_club = equipo_stats['con_club']

    deportista_stats = Deportista.objects.aggregate(
        total=Count('pk'),
        del_anio=Count('pk', filter=Q(fecha_registro__year=hoy.year)),
    )
    total_deportistas = deportista_stats['total']
    deportistas_anio = deportista_stats['del_anio']

    campeonato_stats = Campeonato.objects.aggregate(
        total=Count('pk'),
        activos=Count(
            'pk',
            filter=Q(estado='ACTIVO') | (
                Q(estado__isnull=True)
                & Q(fecha_inicio__lte=hoy)
                & (Q(fecha_conclusion__isnull=True) | Q(fecha_conclusion__gte=hoy))
            ),
        ),
    )
    total_campeonatos = campeonato_stats['total']
    campeonatos_activos = campeonato_stats['activos']

    partido_stats = Partido.objects.aggregate(
        total=Count('pk'),
        proximos=Count('pk', filter=Q(fecha__gte=ahora)),
    )
    total_partidos = partido_stats['total']
    total_partidos_proximos = partido_stats['proximos']

    total_arbitros = Arbitro.objects.count()
    total_categorias = Categoria.objects.count()
    total_inscripciones = Inscripcion.objects.count()
    total_sanciones = Sancion.objects.count()
    total_asignaciones = AsignacionArbitro.objects.count()
    partidos_jugados = _partidos_disputados().count()

    # --- Próximos encuentros ---------------------------------------------------
    proximos_partidos = list(
        Partido.objects.filter(fecha__gte=ahora)
        .select_related(
            'campeonato',
            'equipo_local__club',
            'equipo_visitante__club',
        )
        .order_by('fecha')[:5]
    )

    # --- Últimos marcadores ----------------------------------------------------
    resultados_recientes = list(
        _partidos_disputados()
        .select_related(
            'campeonato',
            'equipo_local__club',
            'equipo_visitante__club',
        )
        .order_by('-fecha', '-id')[:3]
    )

    # --- Pendientes del padrón -------------------------------------------------
    equipos_sin_club = Equipo.objects.filter(club__isnull=True).count()
    clubes_sin_equipos = (
        Club.objects.annotate(total=Count('equipo')).filter(total=0).count()
    )
    partidos_sin_terna = (
        Partido.objects.filter(fecha__gte=ahora)
        .filter(Q(terna_arbitral__isnull=True) | Q(terna_arbitral=''))
        .count()
    )
    pagos_sin_monto = (
        Pago.objects.filter(Q(monto__isnull=True) | Q(monto=0)).count()
        if puede_ver_finanzas else 0
    )

    # Solo se muestran los pendientes que existen: nada de filas decorativas
    # con la etiqueta «al día».
    pendientes = []
    if equipos_sin_club:
        pendientes.append({
            'cantidad': equipos_sin_club,
            'singular': 'equipo sin club',
            'plural': 'equipos sin club',
            'detalle': 'Asigna cada equipo a su institución.',
            'ruta': 'clubes',
            'icono': 'group_off',
            'tono': 'alerta',
        })
    if clubes_sin_equipos:
        pendientes.append({
            'cantidad': clubes_sin_equipos,
            'singular': 'club sin equipos',
            'plural': 'clubes sin equipos',
            'detalle': 'Completa la estructura de cada club.',
            'ruta': 'clubes',
            'icono': 'shield',
            'tono': 'info',
        })
    if partidos_sin_terna:
        pendientes.append({
            'cantidad': partidos_sin_terna,
            'singular': 'partido sin terna',
            'plural': 'partidos sin terna',
            'detalle': 'Designa el equipo arbitral.',
            'ruta': 'asignaciones',
            'icono': 'sports',
            'tono': 'alerta',
        })
    if total_sanciones:
        pendientes.append({
            'cantidad': total_sanciones,
            'singular': 'sanción vigente',
            'plural': 'sanciones vigentes',
            'detalle': 'Resoluciones del Tribunal de Penas.',
            'ruta': 'sanciones',
            'icono': 'gavel',
            'tono': 'info',
        })
    if pagos_sin_monto:
        pendientes.append({
            'cantidad': pagos_sin_monto,
            'singular': 'pago sin monto',
            'plural': 'pagos sin monto',
            'detalle': 'Completa el comprobante en Tesorería.',
            'ruta': 'tesoreria',
            'icono': 'payments',
            'tono': 'alerta',
        })

    # --- Campeonatos -----------------------------------------------------------
    campeonatos_info = []
    for campeonato in (
        Campeonato.objects.select_related('categoria')
        .annotate(
            total_equipos=Count('inscripcion__equipo', distinct=True),
            total_partidos=Count('partido', distinct=True),
        )
        .order_by('-fecha_inicio', '-id')[:6]
    ):
        campeonatos_info.append({
            'campeonato': campeonato,
            'estado': _estado_campeonato(campeonato, hoy),
            'progreso': campeonato.progreso,
        })

    # --- Resumen económico -----------------------------------------------------
    economia = None
    variacion_ingresos = None
    total_pagos = 0
    if puede_ver_finanzas:
        inicio_mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
        pago_stats = Pago.objects.aggregate(
            total=Sum('monto'),
            registros=Count('pk'),
            mes=Sum(
                'monto',
                filter=Q(fecha__year=hoy.year, fecha__month=hoy.month),
            ),
            mes_anterior=Sum(
                'monto',
                filter=Q(
                    fecha__year=inicio_mes_anterior.year,
                    fecha__month=inicio_mes_anterior.month,
                ),
            ),
        )
        total_ingresos = pago_stats['total'] or 0
        ingresos_mes = pago_stats['mes'] or 0
        ingresos_mes_anterior = pago_stats['mes_anterior'] or 0
        total_pagos = pago_stats['registros'] or 0

        if ingresos_mes_anterior:
            variacion_ingresos = round(
                (float(ingresos_mes) - float(ingresos_mes_anterior))
                / float(ingresos_mes_anterior) * 100,
                1,
            )

        economia = {
            'total_ingresos': total_ingresos,
            'ingresos_mes': ingresos_mes,
            'ingresos_mes_anterior': ingresos_mes_anterior,
            'variacion': variacion_ingresos,
            'pagos_registrados': total_pagos,
            'pagos_sin_monto': pagos_sin_monto,
            # Movimientos concretos: aportan información que el gráfico no da.
            'ultimos': list(
                Pago.objects.filter(monto__gt=0)
                .select_related('deportista')
                .order_by('-fecha', '-id')[:4]
            ),
        }

    # --- Actividad reciente ----------------------------------------------------
    actividad = HistorialOperacion.objects.select_related('usuario')
    if rol not in ROLES_AUDITORIA:
        # Cada rol consulta únicamente su propia huella operativa.
        actividad = actividad.filter(usuario=request.user)
    actividad_reciente = list(actividad.order_by('-fecha', '-id')[:6])

    # Orden de bloques resuelto por rol: la plantilla solo recorre la lista.
    bloques = ORDEN_PANEL.get(rol, ORDEN_PANEL['DIRIGENTE'])
    orden_panel = [
        f'panel/_{bloque}.html'
        for bloque in bloques
        if bloque != 'economia' or puede_ver_finanzas
    ]

    contexto = {
        'rol': rol,
        'rol_label': ROLES_LABELS.get(rol, ''),
        'usuario_nombre': request.user.get_full_name() or request.user.username,
        'temporada_actual': hoy.year,
        'hoy': hoy,
        'anio': anio,
        'anios_disponibles': _anios_disponibles(anio),
        'charts': charts,
        'orden_panel': orden_panel,
        'puede_ver_finanzas': puede_ver_finanzas,
        'puede_registrar_pago': puede_ver_finanzas,
        'puede_ver_auditoria': rol in ROLES_AUDITORIA,
        'total_clubes': total_clubes,
        'clubes_activos': clubes_activos,
        'total_equipos': total_equipos,
        'equipos_con_club': equipos_con_club,
        'total_deportistas': total_deportistas,
        'deportistas_anio': deportistas_anio,
        'total_campeonatos': total_campeonatos,
        'total_categorias': total_categorias,
        'total_inscripciones': total_inscripciones,
        'total_partidos': total_partidos,
        'partidos_jugados': partidos_jugados,
        'total_sanciones': total_sanciones,
        'total_asignaciones': total_asignaciones,
        'total_pagos': total_pagos,
        'variacion_ingresos': variacion_ingresos,
        'total_arbitros': total_arbitros,
        'proximos_partidos': proximos_partidos,
        'total_partidos_proximos': total_partidos_proximos,
        'resultados_recientes': resultados_recientes,
        'pendientes': pendientes,
        'hay_pendientes': bool(pendientes),
        'hay_graficos_secundarios': bool(
            charts['resultados']['total'] or charts['clubes_equipos']['total']
        ),
        'campeonatos_info': campeonatos_info,
        'campeonatos_activos': campeonatos_activos,
        'economia': economia,
        'actividad_reciente': actividad_reciente,
        'deportistas_sin_fecha': Deportista.objects.filter(
            fecha_registro__isnull=True
        ).count(),
        'deportistas_opciones': Deportista.objects.select_related('club').order_by(
            'apellido', 'nombre'
        )[:300],
        'total_deportistas_opciones': total_deportistas,
    }

    cache.set(clave_panel, contexto, 180)
    return render(request, 'panel_general.html', contexto)


@login_required
def panel_estadisticas(request):
    """Datos JSON de los gráficos del panel para el filtro por año."""
    anio = _parse_anio(request)
    datos = _panel_charts(request, anio)
    datos['anio'] = anio
    return JsonResponse(datos)


@login_required
def partido_detalle(request, pk):
    """Ficha completa de un partido del fixture oficial."""
    partido = get_object_or_404(
        Partido.objects.select_related(
            'campeonato__categoria',
            'equipo_local__club',
            'equipo_visitante__club',
        ),
        pk=pk,
    )
    asignaciones = (
        AsignacionArbitro.objects.filter(partido=partido)
        .select_related('arbitro')
        .order_by('arbitro__apellido', 'arbitro__nombre')
    )

    contexto = {
        'partido': partido,
        'asignaciones': asignaciones,
        'marcador': _marcador_partido(partido.resultado),
        'rol': _user_role(request),
        'rol_label': ROLES_LABELS.get(_user_role(request), ''),
        'usuario_nombre': request.user.get_full_name() or request.user.username,
        'temporada_actual': timezone.localdate().year,
        'puede_editar_partido': _user_role(request) in {'ADMIN', 'ARBITRO'},
        'puede_editar_asignaciones': _user_role(request) in {'ADMIN', 'ARBITRO'},
    }
    return render(request, 'partido_detalle.html', contexto)


def clubes_publicos(request):
    """Directorio público de clubes afiliados a la AFO."""
    clubes_registrados = (
        Club.objects.annotate(
            total_equipos=Count('equipo', distinct=True),
            total_deportistas=Count('deportista', distinct=True),
        )
        .prefetch_related('equipo_set')
        .order_by('nombre')
    )

    categorias = {}
    for valor in (
        Club.objects.exclude(categoria_ingreso__isnull=True)
        .exclude(categoria_ingreso='')
        .values_list('categoria_ingreso', flat=True)
    ):
        clave = slugify(valor)
        if not clave:
            continue
        etiqueta = str(valor).replace('-', ' ').replace('_', ' ').strip().title()
        categorias.setdefault(clave, etiqueta)

    categorias_clubes = [
        {'clave': clave, 'label': etiqueta}
        for clave, etiqueta in sorted(categorias.items(), key=lambda item: item[1].lower())
    ]

    contexto = {
        'clubes_registrados': clubes_registrados,
        'categorias_clubes': categorias_clubes,
        'total_clubes': Club.objects.count(),
        'total_equipos': Equipo.objects.count(),
        'total_deportistas': Deportista.objects.count(),
        'temporada_actual': timezone.localdate().year,
    }

    return render(request, 'clubes_publicos.html', contexto)


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

                _log_operation(
                    request.user,
                    f'Registro de club · {nuevo_club.nombre} · '
                    f'{len(equipos_seleccionados)} equipo(s)',
                )

                return redirect('clubes')

        # ELIMINAR CLUB
        elif accion == 'eliminar_club':

            club_id = request.POST.get('club_id')

            club = Club.objects.filter(id=club_id).first()

            if club:
                club.delete()
                _log_operation(
                    request.user,
                    f'Eliminación de club · {club.nombre}',
                )

            return redirect('clubes')

    clubes_registrados = Club.objects.all().order_by('nombre').prefetch_related(
        'equipo_set',
        'deportista_set'
    )
    contexto = {
        'clubes_registrados': clubes_registrados,
        'total_clubes': Club.objects.count(),
        'total_equipos': Equipo.objects.count(),
        'total_deportistas': Deportista.objects.count(),
        'planillas_pendientes': 0,
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

                _log_operation(
                    request.user,
                    f'Registro de campeonato · {nombre} · {disciplina} · '
                    f'categoría {categoria.nombre}',
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

                    _log_operation(
                        request.user,
                        f'Programación de partido · {equipo_local.nombre} vs '
                        f'{equipo_visitante.nombre} · {campeonato.nombre} · '
                        f'{fecha:%d/%m/%Y %H:%M}',
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
        accion = request.POST.get('accion')

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

                _log_operation(
                    request.user,
                    f'Registro de árbitro · {apellido}, {nombre} · CI {ci}',
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

                    _log_operation(
                        request.user,
                        f'Registro de deportista · {apellido}, {nombre} · '
                        f'{club.nombre if club else "Sin club"}',
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
    if _user_role(request) not in ROLES_FINANZAS:
        return _forbidden(
            request,
            'La caja institucional está reservada a Tesorería y a la '
            'Administración General.',
        )
    return _shell(request, 'tesoreria_pagos.html')


@login_required
def auditoria(request):
    if _user_role(request) not in ROLES_AUDITORIA:
        return _forbidden(
            request,
            'La auditoría completa del sistema está reservada a la '
            'Administración General.',
        )
    return _shell(request, 'auditoria_usuarios.html')