"""Tesorería, usuarios, reportes y auditoría del sistema A.F.O. · Oruro."""
import csv
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import Group, User
from django.contrib.auth.views import PasswordChangeView
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views import View

from . import forms
from .cache_utils import version_cache
from .exportadores import generar_pdf, generar_xlsx
from .models import (
    Arbitro,
    Campeonato,
    Categoria,
    Club,
    Deportista,
    Equipo,
    HistorialOperacion,
    Inscripcion,
    Pago,
    Partido,
    RegistroAcceso,
    Sancion,
)
from .permisos import (
    buscar,
    contexto,
    modulo_requerido,
    normalizar_busqueda,
    paginar,
    puede_escribir,
    registrar,
)
from .views import ROLES_LABELS, _user_role

# ---------------------------------------------------------------------------
# Tesorería / pagos
# ---------------------------------------------------------------------------


def _pagos_filtrados(request):
    consulta = Pago.objects.select_related('club', 'deportista')
    busqueda = normalizar_busqueda(request)
    consulta = buscar(
        consulta, busqueda,
        ['tipo', 'comprobante', 'club__nombre',
         'deportista__nombre', 'deportista__apellido'],
    )
    estado = (request.GET.get('estado') or '').strip()
    club_id = (request.GET.get('club') or '').strip()
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()
    if estado:
        consulta = consulta.filter(estado=estado)
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)
    if desde:
        consulta = consulta.filter(fecha__date__gte=desde)
    if hasta:
        consulta = consulta.filter(fecha__date__lte=hasta)
    return consulta, {
        'busqueda': busqueda,
        'estado_actual': estado,
        'club_actual': club_id,
        'desde': desde,
        'hasta': hasta,
    }


@modulo_requerido('pagos')
def tesoreria(request):
    consulta, filtros = _pagos_filtrados(request)
    total_cobrado = (
        consulta.filter(estado='PAGADO').aggregate(total=Sum('monto'))['total'] or 0
    )
    total_pendiente = (
        consulta.filter(estado='PENDIENTE').aggregate(total=Sum('monto'))['total'] or 0
    )
    return render(
        request,
        'admin/pagos.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            total_cobrado=total_cobrado,
            total_pendiente=total_pendiente,
            clubes=Club.objects.all(),
            estados=Pago.ESTADOS,
            puede_editar=puede_escribir(_user_role(request), 'pagos'),
            **filtros,
        ),
    )


@modulo_requerido('pagos', escritura=True)
def pago_crear(request):
    form = forms.PagoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pago = form.save()
        registrar(
            request, 'pagos', 'CREAR',
            f'Pago registrado · Bs {pago.monto} · {pago.tipo}',
        )
        messages.success(
            request,
            f'Pago de Bs {pago.monto} registrado con comprobante '
            f'{pago.comprobante or "sin número"}.',
        )
        return redirect('tesoreria')
    return render(
        request,
        'admin/form.html',
        contexto(
            request,
            form=form,
            titulo='Registrar pago',
            subtitulo='El comprobante se guarda en la caja institucional.',
            cancelar_url=reverse('tesoreria'),
            icono='payments',
            guardar_texto='Registrar pago',
        ),
    )


@modulo_requerido('pagos', escritura=True)
def pago_editar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    form = forms.PagoForm(request.POST or None, instance=pago)
    if request.method == 'POST' and form.is_valid():
        pago = form.save()
        registrar(
            request, 'pagos', 'EDITAR',
            f'Pago actualizado · Bs {pago.monto} · {pago.estado}',
        )
        messages.success(request, 'Pago actualizado.')
        return redirect('tesoreria')
    return render(
        request,
        'admin/form.html',
        contexto(
            request,
            form=form,
            titulo=f'Editar pago · Bs {pago.monto}',
            subtitulo='Modifique el monto, el estado o el comprobante.',
            cancelar_url=reverse('tesoreria'),
            icono='payments',
        ),
    )


@modulo_requerido('pagos', escritura=True)
def pago_eliminar(request, pk):
    pago = get_object_or_404(Pago, pk=pk)
    if request.method == 'POST':
        detalle = str(pago)
        pago.delete()
        registrar(request, 'pagos', 'ELIMINAR', f'Pago eliminado · {detalle}')
        messages.success(request, 'Pago eliminado de la caja.')
        return redirect('tesoreria')
    return render(
        request,
        'admin/confirmar_eliminar.html',
        contexto(
            request,
            objeto=pago,
            titulo='Eliminar pago',
            descripcion='El movimiento se borrará de la caja institucional.',
            cancelar_url=reverse('tesoreria'),
        ),
    )


@modulo_requerido('pagos')
def pago_comprobante(request, pk):
    pago = get_object_or_404(Pago.objects.select_related('club', 'deportista'), pk=pk)
    return render(
        request,
        'admin/comprobante.html',
        contexto(request, pago=pago, emitido=timezone.localtime()),
    )


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------


@modulo_requerido('usuarios')
def usuarios(request):
    busqueda = normalizar_busqueda(request)
    rol = (request.GET.get('rol') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    consulta = User.objects.prefetch_related('groups').order_by('username')
    consulta = buscar(
        consulta, busqueda,
        ['username', 'first_name', 'last_name', 'email'],
    )
    if rol:
        consulta = consulta.filter(groups__name=rol)
    if estado == 'ACTIVO':
        consulta = consulta.filter(is_active=True)
    elif estado == 'INACTIVO':
        consulta = consulta.filter(is_active=False)

    return render(
        request,
        'admin/usuarios.html',
        contexto(
            request,
            pagina=paginar(request, consulta.distinct()),
            total=consulta.distinct().count(),
            busqueda=busqueda,
            roles=forms.GRUPOS_ROL,
            rol_actual=rol,
            estado_actual=estado,
        ),
    )


@modulo_requerido('usuarios', escritura=True)
def usuario_crear(request):
    form = forms.UsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        registrar(
            request, 'usuarios', 'CREAR',
            f'Usuario creado · {usuario.username} · '
            f'{usuario.groups.first().name if usuario.groups.exists() else "sin rol"}',
        )
        messages.success(
            request, f'Usuario «{usuario.username}» creado con su rol.'
        )
        return redirect('usuarios')
    return render(
        request,
        'admin/form.html',
        contexto(
            request,
            form=form,
            titulo='Nuevo usuario',
            subtitulo='La contraseña se guarda cifrada; el rol se asigna por grupo.',
            cancelar_url=reverse('usuarios'),
            icono='manage_accounts',
            guardar_texto='Crear usuario',
        ),
    )


@modulo_requerido('usuarios', escritura=True)
def usuario_editar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    form = forms.UsuarioEditarForm(request.POST or None, instance=usuario)
    if request.method == 'POST' and form.is_valid():
        if usuario == request.user and not form.cleaned_data['is_active']:
            messages.error(request, 'No puede desactivar su propia cuenta.')
        elif usuario == request.user and form.cleaned_data['grupo'].name != (
            'Administrador General'
        ):
            messages.error(
                request,
                'No puede quitarse a sí mismo el rol de Administrador General.',
            )
        else:
            usuario = form.save()
            registrar(
                request, 'usuarios', 'EDITAR',
                f'Usuario actualizado · {usuario.username}',
            )
            messages.success(request, 'Usuario actualizado.')
            return redirect('usuarios')
    return render(
        request,
        'admin/form.html',
        contexto(
            request,
            form=form,
            titulo=f'Editar usuario · {usuario.username}',
            subtitulo='Cambie los datos, el rol o el estado de la cuenta.',
            cancelar_url=reverse('usuarios'),
            icono='manage_accounts',
        ),
    )


@modulo_requerido('usuarios', escritura=True)
def usuario_password(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = PasswordChangeForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            if usuario == request.user:
                update_session_auth_hash(request, usuario)
            registrar(
                request, 'usuarios', 'PASSWORD',
                f'Contraseña restablecida · {usuario.username}',
            )
            messages.success(request, 'Contraseña actualizada correctamente.')
            return redirect('usuarios')
    else:
        form = PasswordChangeForm(usuario)
    for campo in form.fields.values():
        campo.widget.attrs.setdefault(
            'class',
            'h-10 w-full rounded-lg border border-surface-container '
            'bg-surface-container-lowest px-3 text-sm outline-none '
            'focus:border-primary/50',
        )
    return render(
        request,
        'admin/password.html',
        contexto(
            request,
            form=form,
            usuario=usuario,
            titulo=f'Restablecer contraseña · {usuario.username}',
            cancelar_url=reverse('usuarios'),
        ),
    )


@modulo_requerido('usuarios', escritura=True)
def usuario_eliminar(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    bloqueo = ''
    if usuario == request.user:
        bloqueo = 'No puede eliminar su propia cuenta.'
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('usuarios')
        nombre = usuario.username
        usuario.delete()
        registrar(request, 'usuarios', 'ELIMINAR', f'Usuario eliminado · {nombre}')
        messages.success(request, f'Usuario «{nombre}» eliminado.')
        return redirect('usuarios')
    return render(
        request,
        'admin/confirmar_eliminar.html',
        contexto(
            request,
            objeto=usuario,
            titulo='Eliminar usuario',
            descripcion='La cuenta perderá el acceso al sistema. Su historial de '
                        'operaciones se conserva sin usuario asociado.',
            cancelar_url=reverse('usuarios'),
            bloqueo=bloqueo,
        ),
    )


# ---------------------------------------------------------------------------
# Perfil y contraseña propia
# ---------------------------------------------------------------------------


@modulo_requerido('perfil')
def perfil(request):
    form = forms.PerfilForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Datos de perfil actualizados.')
        return redirect('perfil')
    return render(
        request,
        'admin/perfil.html',
        contexto(
            request,
            form=form,
            grupos=list(request.user.groups.values_list('name', flat=True)),
        ),
    )


class CambiarPasswordView(PasswordChangeView):
    template_name = 'auth/password_change.html'
    success_url = reverse_lazy('perfil')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, 'Su contraseña fue actualizada.')
        registrar(self.request, 'usuarios', 'PASSWORD', 'Cambio de contraseña propio')
        return respuesta

    def get_context_data(self, **kwargs):
        datos = super().get_context_data(**kwargs)
        datos.update(contexto(self.request))
        for campo in datos['form'].fields.values():
            campo.widget.attrs.setdefault(
                'class',
                'h-10 w-full rounded-lg border border-surface-container '
                'bg-surface-container-lowest px-3 text-sm outline-none '
                'focus:border-primary/50',
            )
        return datos


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------


def _fechas(request, consulta, campo):
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()
    if desde:
        consulta = consulta.filter(**{f'{campo}__date__gte': desde})
    if hasta:
        consulta = consulta.filter(**{f'{campo}__date__lte': hasta})
    return consulta, desde, hasta


def _texto(valor):
    if valor is None or valor == '':
        return '—'
    if hasattr(valor, 'strftime'):
        if hasattr(valor, 'hour'):
            return timezone.localtime(valor).strftime('%d/%m/%Y %H:%M')
        return valor.strftime('%d/%m/%Y')
    return str(valor)


def _reporte_clubes(request):
    consulta = Club.objects.annotate(
        n_equipos=Count('equipo', distinct=True),
        n_deportistas=Count('deportista', distinct=True),
    ).order_by('nombre')
    estado = (request.GET.get('estado') or '').strip()
    if estado:
        consulta = consulta.filter(estado=estado)
    consulta, desde, hasta = _fechas(request, consulta, 'fundacion')
    filas = [
        [
            club.nombre, club.get_estado_display(), club.presidente or '—',
            club.telefono or '—', club.email or '—', _texto(club.fundacion),
            club.n_equipos, club.n_deportistas,
        ]
        for club in consulta
    ]
    return {
        'titulo': 'Reporte de clubes',
        'encabezados': [
            'Club', 'Estado', 'Presidente', 'Teléfono', 'Correo',
            'Fundación', 'Equipos', 'Deportistas',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre la fecha de fundación.',
        'filtros': True,
    }


def _reporte_equipos(request):
    consulta = Equipo.objects.select_related('club', 'categoria').annotate(
        n_deportistas=Count('deportista', distinct=True)
    ).order_by('club__nombre', 'nombre')
    club_id = (request.GET.get('club') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)
    filas = [
        [
            equipo.nombre, equipo.club.nombre if equipo.club else '—',
            equipo.categoria.nombre if equipo.categoria else '—',
            equipo.division or '—', equipo.temporada or '—',
            equipo.entrenador or '—', equipo.get_estado_display(),
            equipo.n_deportistas,
        ]
        for equipo in consulta
    ]
    return {
        'titulo': 'Reporte de equipos',
        'encabezados': [
            'Equipo', 'Club', 'Categoría', 'División', 'Temporada',
            'Entrenador', 'Estado', 'Deportistas',
        ],
        'filas': filas,
        'desde': '',
        'hasta': '',
        'nota': '',
        'filtros': True,
    }


def _reporte_deportistas(request):
    consulta = Deportista.objects.select_related(
        'club', 'equipo', 'categoria'
    ).order_by('apellido', 'nombre')
    club_id = (request.GET.get('club') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)
    if estado:
        consulta = consulta.filter(estado=estado)
    consulta, desde, hasta = _fechas(request, consulta, 'fecha_registro')
    filas = [
        [
            deportista.apellido, deportista.nombre, deportista.ci or '—',
            _texto(deportista.fecha_nacimiento),
            deportista.club.nombre if deportista.club else '—',
            deportista.equipo.nombre if deportista.equipo else '—',
            deportista.categoria.nombre if deportista.categoria else '—',
            deportista.get_estado_display(), _texto(deportista.fecha_registro),
        ]
        for deportista in consulta
    ]
    return {
        'titulo': 'Reporte de deportistas',
        'encabezados': [
            'Apellido', 'Nombre', 'CI', 'Nacimiento', 'Club', 'Equipo',
            'Categoría', 'Estado', 'Alta federativa',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre la fecha de alta federativa.',
        'filtros': True,
    }


def _reporte_campeonatos(request):
    consulta = Campeonato.objects.select_related('categoria').annotate(
        n_equipos=Count('inscripcion__equipo', distinct=True),
        n_partidos=Count('partido', distinct=True),
    ).order_by('-fecha_inicio', '-id')
    estado = (request.GET.get('estado') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()
    if estado:
        consulta = consulta.filter(estado=estado)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)
    consulta, desde, hasta = _fechas(request, consulta, 'fecha_inicio')
    filas = [
        [
            campeonato.nombre,
            campeonato.categoria.nombre if campeonato.categoria else '—',
            campeonato.temporada or '—', campeonato.get_modalidad_display(),
            _texto(campeonato.fecha_inicio), _texto(campeonato.fecha_conclusion),
            campeonato.get_estado_display() if campeonato.estado else 'Sin estado',
            campeonato.n_equipos, campeonato.n_partidos,
        ]
        for campeonato in consulta
    ]
    return {
        'titulo': 'Reporte de campeonatos',
        'encabezados': [
            'Campeonato', 'Categoría', 'Temporada', 'Modalidad', 'Inicio',
            'Conclusión', 'Estado', 'Equipos', 'Partidos',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre el inicio del campeonato.',
        'filtros': True,
    }


def _reporte_inscripciones(request):
    consulta = Inscripcion.objects.select_related(
        'campeonato', 'equipo__club', 'deportista'
    ).order_by('-fecha_registro')
    campeonato_id = (request.GET.get('campeonato') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    if campeonato_id.isdigit():
        consulta = consulta.filter(campeonato_id=campeonato_id)
    if estado:
        consulta = consulta.filter(estado=estado)
    consulta, desde, hasta = _fechas(request, consulta, 'fecha_registro')
    filas = [
        [
            inscripcion.campeonato.nombre if inscripcion.campeonato else '—',
            inscripcion.equipo.nombre if inscripcion.equipo else '—',
            str(inscripcion.deportista) if inscripcion.deportista else '—',
            inscripcion.get_estado_display(),
            _texto(inscripcion.fecha_registro),
            inscripcion.observaciones or '—',
        ]
        for inscripcion in consulta
    ]
    return {
        'titulo': 'Reporte de inscripciones',
        'encabezados': [
            'Campeonato', 'Equipo', 'Deportista', 'Estado', 'Registro',
            'Observaciones',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre la fecha de registro.',
        'filtros': True,
    }


def _reporte_partidos(request):
    consulta = Partido.objects.select_related(
        'campeonato', 'equipo_local', 'equipo_visitante'
    ).order_by('-fecha')
    campeonato_id = (request.GET.get('campeonato') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    if campeonato_id.isdigit():
        consulta = consulta.filter(campeonato_id=campeonato_id)
    if estado:
        consulta = consulta.filter(estado=estado)
    consulta, desde, hasta = _fechas(request, consulta, 'fecha')
    filas = [
        [
            _texto(partido.fecha),
            partido.campeonato.nombre if partido.campeonato else '—',
            partido.equipo_local.nombre if partido.equipo_local else '—',
            partido.equipo_visitante.nombre if partido.equipo_visitante else '—',
            partido.marcador or '—',
            partido.get_estado_display() if partido.get_estado_display() else partido.estado,
            partido.escenario or '—',
        ]
        for partido in consulta
    ]
    return {
        'titulo': 'Reporte de partidos',
        'encabezados': [
            'Fecha', 'Campeonato', 'Local', 'Visitante', 'Marcador',
            'Estado', 'Escenario',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre la programación del partido.',
        'filtros': True,
    }


def _reporte_arbitros(request):
    consulta = Arbitro.objects.annotate(
        n_partidos=Count('asignacionarbitro', distinct=True)
    ).order_by('apellido', 'nombre')
    categoria = (request.GET.get('categoria') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    if categoria:
        consulta = consulta.filter(categoria=categoria)
    if estado:
        consulta = consulta.filter(estado=estado)
    filas = [
        [
            arbitro.codigo or '—', arbitro.apellido, arbitro.nombre,
            arbitro.ci or '—', arbitro.get_categoria_display(),
            arbitro.get_especialidad_display(), arbitro.licencia or '—',
            'Sí' if arbitro.disponible else 'No',
            arbitro.get_estado_display(), arbitro.n_partidos,
        ]
        for arbitro in consulta
    ]
    return {
        'titulo': 'Reporte de árbitros',
        'encabezados': [
            'Código', 'Apellido', 'Nombre', 'CI', 'Categoría',
            'Especialidad', 'Licencia', 'Disponible', 'Estado', 'Partidos',
        ],
        'filas': filas,
        'desde': '',
        'hasta': '',
        'nota': '',
        'filtros': True,
    }


def _reporte_sanciones(request):
    consulta = Sancion.objects.select_related(
        'deportista', 'club', 'campeonato', 'partido'
    ).order_by('-fecha')
    estado = (request.GET.get('estado') or '').strip()
    tipo = (request.GET.get('tipo') or '').strip()
    if estado:
        consulta = consulta.filter(estado=estado)
    if tipo:
        consulta = consulta.filter(tipo=tipo)
    consulta, desde, hasta = _fechas(request, consulta, 'fecha')
    filas = [
        [
            _texto(sancion.fecha), sancion.get_tipo_display(),
            str(sancion.deportista) if sancion.deportista else '—',
            sancion.club.nombre if sancion.club else '—',
            sancion.campeonato.nombre if sancion.campeonato else '—',
            str(sancion.partido) if sancion.partido else '—',
            _texto(sancion.fecha_inicio), _texto(sancion.fecha_fin),
            sancion.get_estado_display(), sancion.descripcion or '—',
        ]
        for sancion in consulta
    ]
    return {
        'titulo': 'Reporte de sanciones',
        'encabezados': [
            'Fecha', 'Tipo', 'Deportista', 'Club', 'Campeonato', 'Partido',
            'Inicio', 'Fin', 'Estado', 'Descripción',
        ],
        'filas': filas,
        'desde': desde,
        'hasta': hasta,
        'nota': 'Filtro de fechas aplicado sobre la fecha de la sanción.',
        'filtros': True,
    }


def _reporte_pagos(request):
    consulta, filtros = _pagos_filtrados(request)
    filas = [
        [
            _texto(pago.fecha), pago.tipo or '—',
            pago.club.nombre if pago.club else '—',
            str(pago.deportista) if pago.deportista else '—',
            f'{pago.monto:.2f}' if pago.monto is not None else '—',
            pago.comprobante or '—', pago.get_estado_display(),
        ]
        for pago in consulta
    ]
    return {
        'titulo': 'Reporte de pagos',
        'encabezados': [
            'Fecha', 'Concepto', 'Club', 'Deportista', 'Monto (Bs)',
            'Comprobante', 'Estado',
        ],
        'filas': filas,
        'desde': filtros['desde'],
        'hasta': filtros['hasta'],
        'nota': 'Filtro de fechas aplicado sobre la fecha del pago.',
        'filtros': True,
    }


REPORTES = {
    'clubes': _reporte_clubes,
    'equipos': _reporte_equipos,
    'deportistas': _reporte_deportistas,
    'campeonatos': _reporte_campeonatos,
    'inscripciones': _reporte_inscripciones,
    'partidos': _reporte_partidos,
    'arbitros': _reporte_arbitros,
    'sanciones': _reporte_sanciones,
    'pagos': _reporte_pagos,
}

REPORTES_FINANCIEROS = {'pagos'}

# Catálogo de estados que corresponde a cada reporte (para el filtro).
ESTADOS_REPORTE = {
    'clubes': Club.ESTADOS,
    'equipos': Equipo.ESTADOS,
    'deportistas': Deportista.ESTADOS,
    'campeonatos': Campeonato.ESTADOS,
    'inscripciones': Inscripcion.ESTADOS,
    'partidos': Partido.ESTADOS,
    'arbitros': Arbitro.ESTADOS,
    'sanciones': Sancion.ESTADOS,
    'pagos': Pago.ESTADOS,
}


@modulo_requerido('reportes')
def reportes(request):
    rol = _user_role(request)
    clave_cache = (
        f'afo:reportes-catalogo:{version_cache()}:{rol}:'
        f'{request.GET.urlencode()}'
    )
    disponibles = cache.get(clave_cache)
    if disponibles is None:
        disponibles = [
            (clave, funcion(request))
            for clave, funcion in REPORTES.items()
            if clave not in REPORTES_FINANCIEROS or rol in {'ADMIN', 'TESORERO'}
        ]
        cache.set(clave_cache, disponibles, 180)
    return render(
        request,
        'admin/reportes.html',
        contexto(
            request,
            reportes=disponibles,
        ),
    )


def _reporte_permitido(request, clave):
    rol = _user_role(request)
    if clave not in REPORTES:
        return False
    if clave in REPORTES_FINANCIEROS and rol not in {'ADMIN', 'TESORERO'}:
        return False
    return True


@modulo_requerido('reportes')
def reporte_detalle(request, clave):
    if not _reporte_permitido(request, clave):
        from .views import _forbidden

        return _forbidden(request, 'El reporte solicitado no está disponible.')
    datos = REPORTES[clave](request)
    datos['clave'] = clave
    return render(
        request,
        'admin/reporte.html',
        contexto(
            request,
            **datos,
            clubes=Club.objects.all(),
            categorias=Categoria.objects.all(),
            campeonatos=Campeonato.objects.all(),
            tipos_sancion=Sancion.TIPOS,
            estados=ESTADOS_REPORTE.get(clave, ()),
        ),
    )


@modulo_requerido('reportes')
def reporte_csv(request, clave):
    if not _reporte_permitido(request, clave):
        from .views import _forbidden

        return _forbidden(request, 'El reporte solicitado no está disponible.')
    datos = REPORTES[clave](request)
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    marca = datetime.now().strftime('%Y%m%d-%H%M')
    respuesta['Content-Disposition'] = (
        f'attachment; filename="afo-{clave}-{marca}.csv"'
    )
    respuesta.write('\ufeff')
    escritor = csv.writer(respuesta, delimiter=';')
    escritor.writerow(datos['encabezados'])
    for fila in datos['filas']:
        escritor.writerow(fila)
    registrar(
        request, 'reportes', 'EXPORTAR',
        f'Reporte exportado a CSV · {datos["titulo"]} · {len(datos["filas"])} fila(s)',
    )
    return respuesta


def _nombre_exportacion(clave, extension):
    marca = datetime.now().strftime('%Y%m%d-%H%M')
    return f'afo-{clave}-{marca}.{extension}'


@modulo_requerido('reportes')
def reporte_pdf(request, clave):
    """Reporte en PDF listo para archivo o impresión institucional."""
    if not _reporte_permitido(request, clave):
        from .views import _forbidden

        return _forbidden(request, 'El reporte solicitado no está disponible.')
    datos = REPORTES[clave](request)
    contenido = generar_pdf(datos, timezone.localtime())
    respuesta = HttpResponse(contenido, content_type='application/pdf')
    nombre = _nombre_exportacion(clave, 'pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    registrar(
        request, 'reportes', 'EXPORTAR',
        f'Reporte exportado a PDF · {datos["titulo"]} · {len(datos["filas"])} fila(s)',
    )
    return respuesta


@modulo_requerido('reportes')
def reporte_xlsx(request, clave):
    """Reporte en Excel (.xlsx) con formato y filtros institucionales."""
    if not _reporte_permitido(request, clave):
        from .views import _forbidden

        return _forbidden(request, 'El reporte solicitado no está disponible.')
    datos = REPORTES[clave](request)
    contenido = generar_xlsx(datos, timezone.localtime())
    respuesta = HttpResponse(
        contenido,
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        ),
    )
    nombre = _nombre_exportacion(clave, 'xlsx')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    registrar(
        request, 'reportes', 'EXPORTAR',
        f'Reporte exportado a Excel · {datos["titulo"]} · {len(datos["filas"])} fila(s)',
    )
    return respuesta


# ---------------------------------------------------------------------------
# Auditoría
# ---------------------------------------------------------------------------


@modulo_requerido('auditoria')
def auditoria(request):
    busqueda = normalizar_busqueda(request)
    modulo = (request.GET.get('modulo') or '').strip()
    usuario_id = (request.GET.get('usuario') or '').strip()
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()

    consulta = HistorialOperacion.objects.select_related('usuario')
    consulta = buscar(consulta, busqueda, ['operacion', 'accion', 'modulo'])
    if modulo:
        consulta = consulta.filter(modulo=modulo)
    if usuario_id.isdigit():
        consulta = consulta.filter(usuario_id=usuario_id)
    if desde:
        consulta = consulta.filter(fecha__date__gte=desde)
    if hasta:
        consulta = consulta.filter(fecha__date__lte=hasta)

    modulos = (
        HistorialOperacion.objects.exclude(modulo='')
        .values_list('modulo', flat=True).distinct().order_by('modulo')
    )
    return render(
        request,
        'admin/auditoria.html',
        contexto(
            request,
            pagina=paginar(request, consulta, 25),
            total=consulta.count(),
            busqueda=busqueda,
            usuarios=User.objects.order_by('username'),
            usuario_actual=usuario_id,
            modulos=modulos,
            modulo_actual=modulo,
            desde=desde,
            hasta=hasta,
        ),
    )


# ---------------------------------------------------------------------------
# Accesos y sesiones
# ---------------------------------------------------------------------------


@modulo_requerido('auditoria')
def accesos(request):
    """Historial estructurado de inicios, cierres e intentos fallidos."""
    busqueda = normalizar_busqueda(request)
    evento = (request.GET.get('evento') or '').strip().upper()
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()
    eventos_validos = {clave for clave, _ in RegistroAcceso.EVENTOS}

    consulta = RegistroAcceso.objects.select_related('usuario')
    consulta = buscar(
        consulta,
        busqueda,
        ['username', 'ip', 'ip_proxy', 'detalle', 'usuario__username',
         'usuario__first_name', 'usuario__last_name'],
    )
    if evento in eventos_validos:
        consulta = consulta.filter(evento=evento)
    else:
        evento = ''
    if desde:
        fecha = parse_date(desde)
        if fecha:
            consulta = consulta.filter(fecha__date__gte=fecha)
    if hasta:
        fecha = parse_date(hasta)
        if fecha:
            consulta = consulta.filter(fecha__date__lte=fecha)

    base = RegistroAcceso.objects.all()
    resumen = {
        'total': base.count(),
        'exitosos': base.filter(evento='LOGIN').count(),
        'fallidos': base.filter(evento__in=['LOGIN_FALLIDO', 'BLOQUEO']).count(),
        'bloqueos': base.filter(evento='BLOQUEO').count(),
        'usuarios': base.filter(evento='LOGIN', usuario__isnull=False)
        .values('usuario_id').distinct().count(),
        'ultimo': base.filter(evento='LOGIN').order_by('-fecha').first(),
    }

    return render(
        request,
        'admin/accesos.html',
        contexto(
            request,
            pagina=paginar(request, consulta, 25),
            total=consulta.count(),
            busqueda=busqueda,
            evento_actual=evento,
            eventos=RegistroAcceso.EVENTOS,
            eventos_resumen=resumen,
            desde=desde,
            hasta=hasta,
        ),
    )
