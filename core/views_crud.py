"""CRUD de los módulos deportivos del sistema A.F.O. · Oruro."""
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import forms
from .estadisticas import tabla_posiciones as _tabla_posiciones
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
    Partido,
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

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------


def _orden(request, queryset, opciones, por_defecto):
    """Aplica el orden elegido en el filtro si está permitido."""
    actual = (request.GET.get('orden') or '').strip()
    if actual in opciones:
        return queryset.order_by(actual), actual
    return queryset.order_by(por_defecto), ''


def _opciones_orden(opciones):
    return [{'valor': valor, 'etiqueta': etiqueta} for valor, etiqueta in opciones.items()]


def _formulario(
    request,
    formulario,
    titulo,
    subtitulo,
    cancelar,
    icono='edit_note',
    guardar_texto='Guardar cambios',
):
    return render(
        request,
        'admin/form.html',
        contexto(
            request,
            form=formulario,
            titulo=titulo,
            subtitulo=subtitulo,
            cancelar_url=cancelar,
            icono=icono,
            guardar_texto=guardar_texto,
        ),
    )


def _confirmar(request, objeto, titulo, descripcion, cancelar, bloqueo=''):
    return render(
        request,
        'admin/confirmar_eliminar.html',
        contexto(
            request,
            objeto=objeto,
            titulo=titulo,
            descripcion=descripcion,
            cancelar_url=cancelar,
            bloqueo=bloqueo,
        ),
    )


# ---------------------------------------------------------------------------
# Clubes
# ---------------------------------------------------------------------------


@modulo_requerido('clubes')
def clubes(request):
    busqueda = normalizar_busqueda(request)
    estado = (request.GET.get('estado') or '').strip()
    consulta = Club.objects.annotate(
        total_equipos=Count('equipo', distinct=True),
        total_deportistas=Count('deportista', distinct=True),
    )
    consulta = buscar(consulta, busqueda, ['nombre', 'presidente', 'nit_personeria'])
    if estado:
        consulta = consulta.filter(estado=estado)
    consulta, orden_actual = _orden(
        request,
        consulta,
        {
            'nombre': 'Nombre (A-Z)',
            '-nombre': 'Nombre (Z-A)',
            '-total_equipos': 'Más equipos',
            '-total_deportistas': 'Más deportistas',
        },
        'nombre',
    )
    pagina = paginar(request, consulta)
    return render(
        request,
        'admin/clubes.html',
        contexto(
            request,
            pagina=pagina,
            total=consulta.count(),
            busqueda=busqueda,
            estado_actual=estado,
            estados=Club.ESTADOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(
                {
                    'nombre': 'Nombre (A-Z)',
                    '-nombre': 'Nombre (Z-A)',
                    '-total_equipos': 'Más equipos',
                    '-total_deportistas': 'Más deportistas',
                }
            ),
            puede_editar=puede_escribir(_rol(request), 'clubes'),
        ),
    )


def _rol(request):
    from .views import _user_role

    return _user_role(request)


@modulo_requerido('clubes', escritura=True)
def club_crear(request):
    form = forms.ClubForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        club = form.save()
        registrar(request, 'clubes', 'CREAR', f'Club creado · {club.nombre}')
        messages.success(request, f'Club «{club.nombre}» registrado correctamente.')
        return redirect('clubes')
    return _formulario(
        request,
        form,
        'Nuevo club afiliado',
        'Registre los datos institucionales del club.',
        reverse('clubes'),
        icono='shield',
        guardar_texto='Registrar club',
    )


@modulo_requerido('clubes', escritura=True)
def club_editar(request, pk):
    club = get_object_or_404(Club, pk=pk)
    form = forms.ClubForm(request.POST or None, instance=club)
    if request.method == 'POST' and form.is_valid():
        club = form.save()
        registrar(request, 'clubes', 'EDITAR', f'Club actualizado · {club.nombre}')
        messages.success(request, 'Datos del club actualizados.')
        return redirect('club_detalle', pk=club.pk)
    return _formulario(
        request,
        form,
        f'Editar · {club.nombre}',
        'Actualice la información institucional o el estado de afiliación.',
        reverse('club_detalle', args=[club.pk]),
        icono='shield',
    )


@modulo_requerido('clubes')
def club_detalle(request, pk):
    club = get_object_or_404(Club, pk=pk)
    equipos = club.equipo_set.select_related('categoria').annotate(
        total_deportistas=Count('deportista', distinct=True)
    )
    deportistas = club.deportista_set.select_related('equipo', 'categoria')[:50]
    return render(
        request,
        'admin/club_detalle.html',
        contexto(
            request,
            club=club,
            equipos=equipos,
            deportistas=deportistas,
            puede_editar=puede_escribir(_rol(request), 'clubes'),
            puede_editar_equipos=puede_escribir(_rol(request), 'equipos'),
            puede_editar_deportistas=puede_escribir(_rol(request), 'deportistas'),
        ),
    )


@modulo_requerido('clubes', escritura=True)
def club_eliminar(request, pk):
    club = get_object_or_404(Club, pk=pk)
    equipos = club.equipo_set.count()
    deportistas = club.deportista_set.count()
    bloqueo = ''
    if equipos or deportistas:
        bloqueo = (
            f'El club tiene {equipos} equipo(s) y {deportistas} deportista(s). '
            'Reasígnelos o registre el club como «Dado de baja» para conservar '
            'el historial.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('club_detalle', pk=club.pk)
        nombre = club.nombre
        club.delete()
        registrar(request, 'clubes', 'ELIMINAR', f'Club eliminado · {nombre}')
        messages.success(request, f'Club «{nombre}» eliminado.')
        return redirect('clubes')
    return _confirmar(
        request,
        club,
        'Eliminar club',
        'Esta acción borra el club de la base institucional. No se puede deshacer.',
        reverse('club_detalle', args=[club.pk]),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Canchas y escenarios
# ---------------------------------------------------------------------------


@modulo_requerido('canchas')
def canchas(request):
    busqueda = normalizar_busqueda(request)
    tipo = (request.GET.get('tipo') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    consulta = Cancha.objects.all()
    consulta = buscar(consulta, busqueda, ['nombre', 'direccion', 'ciudad', 'descripcion'])
    if tipo:
        consulta = consulta.filter(tipo=tipo)
    if estado == 'activas':
        consulta = consulta.filter(activa=True)
    elif estado == 'inactivas':
        consulta = consulta.filter(activa=False)

    consulta, orden_actual = _orden(
        request,
        consulta,
        {
            'nombre': 'Nombre (A-Z)',
            '-nombre': 'Nombre (Z-A)',
            'orden': 'Orden del portal',
            '-orden': 'Orden inverso',
        },
        'orden',
    )
    pagina = paginar(request, consulta, por_pagina=12)
    return render(
        request,
        'admin/canchas.html',
        contexto(
            request,
            pagina=pagina,
            total=consulta.count(),
            busqueda=busqueda,
            tipo_actual=tipo,
            estado_actual=estado,
            tipos=Cancha.TIPOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(
                {
                    'nombre': 'Nombre (A-Z)',
                    '-nombre': 'Nombre (Z-A)',
                    'orden': 'Orden del portal',
                    '-orden': 'Orden inverso',
                }
            ),
            puede_editar=puede_escribir(_rol(request), 'canchas'),
        ),
    )


@modulo_requerido('canchas', escritura=True)
def cancha_crear(request):
    form = forms.CanchaForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        cancha = form.save()
        registrar(request, 'canchas', 'CREAR', f'Escenario creado · {cancha.nombre}')
        messages.success(request, f'Escenario «{cancha.nombre}» registrado correctamente.')
        return redirect('canchas')
    return _formulario(
        request,
        form,
        'Nuevo escenario deportivo',
        'Registre la cancha, su ubicación y una imagen para el portal público.',
        reverse('canchas'),
        icono='stadium',
        guardar_texto='Registrar escenario',
    )


@modulo_requerido('canchas', escritura=True)
def cancha_editar(request, pk):
    cancha = get_object_or_404(Cancha, pk=pk)
    form = forms.CanchaForm(
        request.POST or None, request.FILES or None, instance=cancha
    )
    if request.method == 'POST' and form.is_valid():
        cancha = form.save()
        registrar(request, 'canchas', 'EDITAR', f'Escenario actualizado · {cancha.nombre}')
        messages.success(request, 'Datos del escenario actualizados.')
        return redirect('canchas')
    return _formulario(
        request,
        form,
        f'Editar · {cancha.nombre}',
        'Actualice la imagen, la ubicación o el estado del escenario.',
        reverse('canchas'),
        icono='stadium',
    )


@modulo_requerido('canchas', escritura=True)
def cancha_eliminar(request, pk):
    cancha = get_object_or_404(Cancha, pk=pk)
    if request.method == 'POST':
        nombre = cancha.nombre
        cancha.delete()
        registrar(request, 'canchas', 'ELIMINAR', f'Escenario eliminado · {nombre}')
        messages.success(request, f'Escenario «{nombre}» eliminado.')
        return redirect('canchas')
    return _confirmar(
        request,
        cancha,
        'Eliminar escenario',
        'Esta acción quita el escenario del portal público. No se puede deshacer.',
        reverse('canchas'),
    )


# ---------------------------------------------------------------------------
# Equipos
# ---------------------------------------------------------------------------


@modulo_requerido('equipos')
def equipos(request):
    busqueda = normalizar_busqueda(request)
    club_id = (request.GET.get('club') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    consulta = Equipo.objects.select_related('club', 'categoria').annotate(
        total_deportistas=Count('deportista', distinct=True)
    )
    consulta = buscar(consulta, busqueda, ['nombre', 'entrenador', 'club__nombre'])
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)
    if estado:
        consulta = consulta.filter(estado=estado)

    opciones = {
        'nombre': 'Nombre (A-Z)',
        '-nombre': 'Nombre (Z-A)',
        '-total_deportistas': 'Más deportistas',
    }
    consulta, orden_actual = _orden(request, consulta, opciones, 'nombre')
    return render(
        request,
        'admin/equipos.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            clubes=Club.objects.all(),
            categorias=Categoria.objects.all(),
            club_actual=club_id,
            categoria_actual=categoria_id,
            estado_actual=estado,
            estados=Equipo.ESTADOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(opciones),
            puede_editar=puede_escribir(_rol(request), 'equipos'),
        ),
    )


@modulo_requerido('equipos', escritura=True)
def equipo_crear(request):
    form = forms.EquipoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        equipo = form.save()
        registrar(request, 'equipos', 'CREAR', f'Equipo creado · {equipo.nombre}')
        messages.success(request, f'Equipo «{equipo.nombre}» registrado.')
        return redirect('equipos')
    return _formulario(
        request,
        form,
        'Nuevo equipo',
        'Asocie el equipo a su club y categoría.',
        reverse('equipos'),
        icono='groups',
        guardar_texto='Registrar equipo',
    )


@modulo_requerido('equipos', escritura=True)
def equipo_editar(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    form = forms.EquipoForm(request.POST or None, instance=equipo)
    if request.method == 'POST' and form.is_valid():
        equipo = form.save()
        registrar(request, 'equipos', 'EDITAR', f'Equipo actualizado · {equipo.nombre}')
        messages.success(request, 'Equipo actualizado.')
        return redirect('equipos')
    return _formulario(
        request,
        form,
        f'Editar · {equipo.nombre}',
        'Datos deportivos del equipo.',
        reverse('equipos'),
        icono='groups',
    )


@modulo_requerido('equipos', escritura=True)
def equipo_eliminar(request, pk):
    equipo = get_object_or_404(Equipo, pk=pk)
    partidos = equipo.partidos_locales.count() + equipo.partidos_visitantes.count()
    inscripciones = equipo.inscripcion_set.count()
    bloqueo = ''
    if partidos or inscripciones:
        bloqueo = (
            f'El equipo participa en {partidos} partido(s) y {inscripciones} '
            'inscripción(es). Para no romper el fixture, cambie su estado a '
            '«Inactivo» en lugar de eliminarlo.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('equipos')
        nombre = equipo.nombre
        equipo.delete()
        registrar(request, 'equipos', 'ELIMINAR', f'Equipo eliminado · {nombre}')
        messages.success(request, f'Equipo «{nombre}» eliminado.')
        return redirect('equipos')
    return _confirmar(
        request,
        equipo,
        'Eliminar equipo',
        'El equipo se borrará del padrón deportivo.',
        reverse('equipos'),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Deportistas
# ---------------------------------------------------------------------------


@modulo_requerido('deportistas')
def deportistas(request):
    busqueda = normalizar_busqueda(request)
    club_id = (request.GET.get('club') or '').strip()
    equipo_id = (request.GET.get('equipo') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    consulta = Deportista.objects.select_related('club', 'equipo', 'categoria')
    consulta = buscar(
        consulta, busqueda, ['nombre', 'apellido', 'ci', 'club__nombre']
    )
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)
    if equipo_id.isdigit():
        consulta = consulta.filter(equipo_id=equipo_id)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)
    if estado:
        consulta = consulta.filter(estado=estado)

    opciones = {
        'apellido': 'Apellido (A-Z)',
        '-apellido': 'Apellido (Z-A)',
        '-fecha_registro': 'Altas más recientes',
        '-fecha_nacimiento': 'Mayores primero',
    }
    consulta, orden_actual = _orden(request, consulta, opciones, 'apellido')

    return render(
        request,
        'admin/deportistas.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            clubes=Club.objects.all(),
            equipos=Equipo.objects.select_related('club'),
            categorias=Categoria.objects.all(),
            club_actual=club_id,
            equipo_actual=equipo_id,
            categoria_actual=categoria_id,
            estado_actual=estado,
            estados=Deportista.ESTADOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(opciones),
            puede_editar=puede_escribir(_rol(request), 'deportistas'),
        ),
    )


@modulo_requerido('deportistas', escritura=True)
def deportista_crear(request):
    form = forms.DeportistaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        deportista = form.save()
        registrar(
            request, 'deportistas', 'CREAR',
            f'Deportista registrado · {deportista.apellido}, {deportista.nombre}',
        )
        messages.success(
            request,
            f'Deportista {deportista.apellido}, {deportista.nombre} registrado.',
        )
        return redirect('deportistas')
    return _formulario(
        request,
        form,
        'Nuevo fichaje',
        'Registre los datos personales y deportivos del deportista.',
        reverse('deportistas'),
        icono='person_add',
        guardar_texto='Registrar deportista',
    )


@modulo_requerido('deportistas', escritura=True)
def deportista_editar(request, pk):
    deportista = get_object_or_404(Deportista, pk=pk)
    form = forms.DeportistaForm(request.POST or None, instance=deportista)
    if request.method == 'POST' and form.is_valid():
        deportista = form.save()
        registrar(
            request, 'deportistas', 'EDITAR',
            f'Deportista actualizado · {deportista.apellido}, {deportista.nombre}',
        )
        messages.success(request, 'Ficha del deportista actualizada.')
        return redirect('deportista_detalle', pk=deportista.pk)
    return _formulario(
        request,
        form,
        f'Editar · {deportista.apellido}, {deportista.nombre}',
        'Actualice datos personales, club o situación federativa.',
        reverse('deportista_detalle', args=[deportista.pk]),
        icono='badge',
    )


@modulo_requerido('deportistas')
def deportista_detalle(request, pk):
    deportista = get_object_or_404(
        Deportista.objects.select_related('club', 'equipo', 'categoria'), pk=pk
    )
    inscripciones = deportista.inscripcion_set.select_related(
        'campeonato', 'equipo'
    ).order_by('-fecha_registro')[:20]
    sanciones = deportista.sancion_set.select_related(
        'campeonato', 'partido'
    ).order_by('-fecha')[:20]
    pagos = None
    if contexto(request)['puede_ver_finanzas']:
        pagos = deportista.pago_set.order_by('-fecha')[:20]
    return render(
        request,
        'admin/deportista_detalle.html',
        contexto(
            request,
            deportista=deportista,
            inscripciones=inscripciones,
            sanciones=sanciones,
            pagos=pagos,
            puede_editar=puede_escribir(_rol(request), 'deportistas'),
        ),
    )


@modulo_requerido('deportistas', escritura=True)
def deportista_eliminar(request, pk):
    deportista = get_object_or_404(Deportista, pk=pk)
    relacionados = (
        deportista.inscripcion_set.count()
        + deportista.sancion_set.count()
        + deportista.pago_set.count()
    )
    bloqueo = ''
    if relacionados:
        bloqueo = (
            'El deportista tiene inscripciones, sanciones o pagos asociados. '
            'Cambie su estado a «Inactivo» para conservar el historial.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('deportista_detalle', pk=deportista.pk)
        nombre = str(deportista)
        deportista.delete()
        registrar(request, 'deportistas', 'ELIMINAR', f'Deportista eliminado · {nombre}')
        messages.success(request, f'Deportista {nombre} eliminado.')
        return redirect('deportistas')
    return _confirmar(
        request,
        deportista,
        'Eliminar deportista',
        'Se borrará la ficha del deportista del padrón.',
        reverse('deportista_detalle', args=[deportista.pk]),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------


@modulo_requerido('categorias')
def categorias(request):
    busqueda = normalizar_busqueda(request)
    consulta = Categoria.objects.annotate(
        total_equipos=Count('equipo', distinct=True),
        total_deportistas=Count('deportista', distinct=True),
    ).order_by('nombre')
    consulta = buscar(consulta, busqueda, ['nombre', 'descripcion'])
    return render(
        request,
        'admin/categorias.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            puede_editar=puede_escribir(_rol(request), 'categorias'),
        ),
    )


@modulo_requerido('categorias', escritura=True)
def categoria_crear(request):
    form = forms.CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        categoria = form.save()
        registrar(request, 'categorias', 'CREAR', f'Categoría creada · {categoria.nombre}')
        messages.success(request, f'Categoría «{categoria.nombre}» creada.')
        return redirect('categorias')
    return _formulario(
        request,
        form,
        'Nueva categoría',
        'Defina el nombre y el rango de edad de la categoría.',
        reverse('categorias'),
        icono='category',
        guardar_texto='Crear categoría',
    )


@modulo_requerido('categorias', escritura=True)
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    form = forms.CategoriaForm(request.POST or None, instance=categoria)
    if request.method == 'POST' and form.is_valid():
        categoria = form.save()
        registrar(request, 'categorias', 'EDITAR', f'Categoría actualizada · {categoria.nombre}')
        messages.success(request, 'Categoría actualizada.')
        return redirect('categorias')
    return _formulario(
        request,
        form,
        f'Editar · {categoria.nombre}',
        'Datos de la categoría.',
        reverse('categorias'),
        icono='category',
    )


@modulo_requerido('categorias', escritura=True)
def categoria_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    usos = (
        categoria.equipo_set.count()
        + categoria.deportista_set.count()
        + categoria.campeonato_set.count()
    )
    bloqueo = ''
    if usos:
        bloqueo = (
            f'La categoría está asignada a {usos} registro(s). '
            'Reasígnelos antes de eliminarla.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('categorias')
        nombre = categoria.nombre
        categoria.delete()
        registrar(request, 'categorias', 'ELIMINAR', f'Categoría eliminada · {nombre}')
        messages.success(request, f'Categoría «{nombre}» eliminada.')
        return redirect('categorias')
    return _confirmar(
        request,
        categoria,
        'Eliminar categoría',
        'La categoría se borrará del sistema.',
        reverse('categorias'),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Campeonatos
# ---------------------------------------------------------------------------


@modulo_requerido('campeonatos')
def campeonatos(request):
    busqueda = normalizar_busqueda(request)
    estado = (request.GET.get('estado') or '').strip()
    categoria_id = (request.GET.get('categoria') or '').strip()

    consulta = Campeonato.objects.select_related('categoria').annotate(
        total_equipos=Count('inscripcion__equipo', distinct=True),
        total_partidos=Count('partido', distinct=True),
    )
    consulta = buscar(consulta, busqueda, ['nombre', 'disciplina'])
    if estado:
        consulta = consulta.filter(estado=estado)
    if categoria_id.isdigit():
        consulta = consulta.filter(categoria_id=categoria_id)

    opciones = {
        '-fecha_inicio': 'Inicio más reciente',
        'fecha_inicio': 'Inicio más antiguo',
        'nombre': 'Nombre (A-Z)',
    }
    consulta, orden_actual = _orden(request, consulta, opciones, '-fecha_inicio')
    return render(
        request,
        'admin/campeonatos.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            categorias=Categoria.objects.all(),
            categoria_actual=categoria_id,
            estado_actual=estado,
            estados=Campeonato.ESTADOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(opciones),
            puede_editar=puede_escribir(_rol(request), 'campeonatos'),
        ),
    )


@modulo_requerido('campeonatos', escritura=True)
def campeonato_crear(request):
    form = forms.CampeonatoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        campeonato = form.save()
        registrar(
            request, 'campeonatos', 'CREAR',
            f'Campeonato creado · {campeonato.nombre}',
        )
        messages.success(request, f'Campeonato «{campeonato.nombre}» creado.')
        return redirect('campeonato_detalle', pk=campeonato.pk)
    return _formulario(
        request,
        form,
        'Nuevo campeonato',
        'Configure el torneo, su categoría y su calendario.',
        reverse('campeonatos'),
        icono='emoji_events',
        guardar_texto='Crear campeonato',
    )


@modulo_requerido('campeonatos', escritura=True)
def campeonato_editar(request, pk):
    campeonato = get_object_or_404(Campeonato, pk=pk)
    form = forms.CampeonatoForm(request.POST or None, instance=campeonato)
    if request.method == 'POST' and form.is_valid():
        campeonato = form.save()
        registrar(
            request, 'campeonatos', 'EDITAR',
            f'Campeonato actualizado · {campeonato.nombre}',
        )
        messages.success(request, 'Campeonato actualizado.')
        return redirect('campeonato_detalle', pk=campeonato.pk)
    return _formulario(
        request,
        form,
        f'Editar · {campeonato.nombre}',
        'Datos y estado del campeonato.',
        reverse('campeonato_detalle', args=[campeonato.pk]),
        icono='emoji_events',
    )


@modulo_requerido('campeonatos')
def campeonato_detalle(request, pk):
    campeonato = get_object_or_404(
        Campeonato.objects.select_related('categoria'), pk=pk
    )
    inscripciones = campeonato.inscripcion_set.select_related(
        'equipo__club', 'deportista'
    ).order_by('equipo__nombre')
    partidos = campeonato.partido_set.select_related(
        'equipo_local', 'equipo_visitante'
    ).order_by('fecha')

    # Calendario agrupado por fecha local: una jornada por bloque visual.
    calendario = []
    for partido in partidos:
        fecha = timezone.localtime(partido.fecha).date() if partido.fecha else None
        if not calendario or calendario[-1]['fecha'] != fecha:
            calendario.append({'fecha': fecha, 'partidos': []})
        calendario[-1]['partidos'].append(partido)

    return render(
        request,
        'admin/campeonato_detalle.html',
        contexto(
            request,
            campeonato=campeonato,
            inscripciones=inscripciones,
            partidos=partidos,
            calendario=calendario,
            tabla=_tabla_posiciones(campeonato),
            jugados=partidos.filter(
                goles_local__isnull=False, goles_visitante__isnull=False
            ).count(),
            puede_editar=puede_escribir(_rol(request), 'campeonatos'),
            puede_editar_partidos=puede_escribir(_rol(request), 'partidos'),
            puede_editar_inscripciones=puede_escribir(_rol(request), 'inscripciones'),
        ),
    )


@modulo_requerido('campeonatos', escritura=True)
def campeonato_eliminar(request, pk):
    campeonato = get_object_or_404(Campeonato, pk=pk)
    partidos = campeonato.partido_set.count()
    inscripciones = campeonato.inscripcion_set.count()
    bloqueo = ''
    if partidos or inscripciones:
        bloqueo = (
            f'El campeonato tiene {partidos} partido(s) y {inscripciones} '
            'inscripción(es). Márquelo como «Cancelado» para conservar el historial.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('campeonato_detalle', pk=campeonato.pk)
        nombre = campeonato.nombre
        campeonato.delete()
        registrar(request, 'campeonatos', 'ELIMINAR', f'Campeonato eliminado · {nombre}')
        messages.success(request, f'Campeonato «{nombre}» eliminado.')
        return redirect('campeonatos')
    return _confirmar(
        request,
        campeonato,
        'Eliminar campeonato',
        'El campeonato se borrará del sistema.',
        reverse('campeonato_detalle', args=[campeonato.pk]),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Inscripciones
# ---------------------------------------------------------------------------


@modulo_requerido('inscripciones')
def inscripciones(request):
    busqueda = normalizar_busqueda(request)
    campeonato_id = (request.GET.get('campeonato') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    club_id = (request.GET.get('club') or '').strip()

    consulta = Inscripcion.objects.select_related(
        'campeonato', 'equipo__club', 'deportista'
    )
    consulta = buscar(
        consulta, busqueda,
        ['deportista__nombre', 'deportista__apellido', 'equipo__nombre'],
    )
    if campeonato_id.isdigit():
        consulta = consulta.filter(campeonato_id=campeonato_id)
    if estado:
        consulta = consulta.filter(estado=estado)
    if club_id.isdigit():
        consulta = consulta.filter(equipo__club_id=club_id)

    return render(
        request,
        'admin/inscripciones.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            campeonatos=Campeonato.objects.all(),
            clubes=Club.objects.all(),
            campeonato_actual=campeonato_id,
            club_actual=club_id,
            estado_actual=estado,
            estados=Inscripcion.ESTADOS,
            puede_editar=puede_escribir(_rol(request), 'inscripciones'),
        ),
    )


@modulo_requerido('inscripciones', escritura=True)
def inscripcion_crear(request):
    inicial = {}
    campeonato_id = request.GET.get('campeonato')
    if campeonato_id and campeonato_id.isdigit():
        inicial['campeonato'] = campeonato_id
    form = forms.InscripcionForm(request.POST or None, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        inscripcion = form.save()
        registrar(
            request, 'inscripciones', 'CREAR',
            f'Inscripción registrada · {inscripcion}',
        )
        messages.success(request, 'Inscripción registrada.')
        return redirect('inscripciones')
    return _formulario(
        request,
        form,
        'Nueva inscripción',
        'Inscriba un equipo o un deportista en un campeonato.',
        reverse('inscripciones'),
        icono='fact_check',
        guardar_texto='Registrar inscripción',
    )


@modulo_requerido('inscripciones', escritura=True)
def inscripcion_editar(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    form = forms.InscripcionForm(request.POST or None, instance=inscripcion)
    if request.method == 'POST' and form.is_valid():
        inscripcion = form.save()
        registrar(
            request, 'inscripciones', 'EDITAR',
            f'Inscripción actualizada · {inscripcion}',
        )
        messages.success(request, 'Inscripción actualizada.')
        return redirect('inscripciones')
    return _formulario(
        request,
        form,
        'Editar inscripción',
        'Actualice el estado o las observaciones.',
        reverse('inscripciones'),
        icono='fact_check',
    )


@modulo_requerido('inscripciones', escritura=True)
def inscripcion_estado(request, pk, estado):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    validos = dict(Inscripcion.ESTADOS)
    if estado not in validos or request.method != 'POST':
        messages.error(request, 'Cambio de estado no válido.')
        return redirect('inscripciones')
    inscripcion.estado = estado
    inscripcion.save(update_fields=['estado'])
    registrar(
        request, 'inscripciones', estado,
        f'Inscripción {validos[estado].lower()} · {inscripcion}',
    )
    messages.success(
        request, f'Inscripción marcada como «{validos[estado]}».'
    )
    return redirect('inscripciones')


@modulo_requerido('inscripciones', escritura=True)
def inscripcion_eliminar(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    if request.method == 'POST':
        detalle = str(inscripcion)
        inscripcion.delete()
        registrar(request, 'inscripciones', 'ELIMINAR', f'Inscripción eliminada · {detalle}')
        messages.success(request, 'Inscripción eliminada.')
        return redirect('inscripciones')
    return _confirmar(
        request,
        inscripcion,
        'Eliminar inscripción',
        'La inscripción se borrará del campeonato.',
        reverse('inscripciones'),
    )


# ---------------------------------------------------------------------------
# Partidos
# ---------------------------------------------------------------------------


@modulo_requerido('partidos')
def partidos(request):
    busqueda = normalizar_busqueda(request)
    campeonato_id = (request.GET.get('campeonato') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    desde = (request.GET.get('desde') or '').strip()
    hasta = (request.GET.get('hasta') or '').strip()

    consulta = Partido.objects.select_related(
        'campeonato', 'equipo_local__club', 'equipo_visitante__club'
    )
    consulta = buscar(
        consulta, busqueda,
        ['equipo_local__nombre', 'equipo_visitante__nombre', 'escenario'],
    )
    if campeonato_id.isdigit():
        consulta = consulta.filter(campeonato_id=campeonato_id)
    if estado:
        consulta = consulta.filter(estado=estado)
    if desde:
        consulta = consulta.filter(fecha__date__gte=desde)
    if hasta:
        consulta = consulta.filter(fecha__date__lte=hasta)

    opciones = {
        '-fecha': 'Fecha más reciente',
        'fecha': 'Fecha más antigua',
        'campeonato__nombre': 'Campeonato (A-Z)',
    }
    consulta, orden_actual = _orden(request, consulta, opciones, '-fecha')
    return render(
        request,
        'admin/partidos.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            campeonatos=Campeonato.objects.all(),
            campeonato_actual=campeonato_id,
            estado_actual=estado,
            estados=Partido.ESTADOS,
            desde=desde,
            hasta=hasta,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(opciones),
            puede_editar=puede_escribir(_rol(request), 'partidos'),
        ),
    )


@modulo_requerido('partidos', escritura=True)
def partido_crear(request):
    inicial = {}
    campeonato_id = request.GET.get('campeonato')
    if campeonato_id and campeonato_id.isdigit():
        inicial['campeonato'] = campeonato_id
    form = forms.PartidoForm(request.POST or None, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        partido = form.save()
        registrar(
            request, 'partidos', 'CREAR',
            f'Partido programado · {partido} · '
            f'{partido.fecha:%d/%m/%Y %H:%M}' if partido.fecha else
            f'Partido programado · {partido}',
        )
        messages.success(request, 'Partido programado en el fixture.')
        return redirect('partido_detalle', pk=partido.pk)
    return _formulario(
        request,
        form,
        'Programar partido',
        'Defina campeonato, equipos, fecha y escenario.',
        reverse('partidos'),
        icono='sports_soccer',
        guardar_texto='Programar partido',
    )


@modulo_requerido('partidos', escritura=True)
def partido_editar(request, pk):
    partido = get_object_or_404(Partido, pk=pk)
    form = forms.PartidoForm(request.POST or None, instance=partido)
    if request.method == 'POST' and form.is_valid():
        partido = form.save()
        registrar(
            request, 'partidos', 'EDITAR',
            f'Partido actualizado · {partido} · {partido.get_estado_display()}',
        )
        messages.success(request, 'Partido actualizado.')
        return redirect('partido_detalle', pk=partido.pk)
    return _formulario(
        request,
        form,
        f'Editar partido · {partido}',
        'Actualice la programación o registre el marcador final.',
        reverse('partido_detalle', args=[partido.pk]),
        icono='scoreboard',
    )


@modulo_requerido('partidos', escritura=True)
def partido_eliminar(request, pk):
    partido = get_object_or_404(Partido, pk=pk)
    if request.method == 'POST':
        detalle = str(partido)
        partido.delete()
        registrar(request, 'partidos', 'ELIMINAR', f'Partido eliminado · {detalle}')
        messages.success(request, 'Partido eliminado del fixture.')
        return redirect('partidos')
    return _confirmar(
        request,
        partido,
        'Eliminar partido',
        'Se borrarán también sus asignaciones arbitrales.',
        reverse('partido_detalle', args=[partido.pk]),
    )


# ---------------------------------------------------------------------------
# Árbitros
# ---------------------------------------------------------------------------


@modulo_requerido('arbitros')
def arbitros(request):
    busqueda = normalizar_busqueda(request)
    categoria = (request.GET.get('categoria') or '').strip()
    estado = (request.GET.get('estado') or '').strip()

    consulta = Arbitro.objects.annotate(
        total_partidos=Count('asignacionarbitro', distinct=True)
    )
    consulta = buscar(consulta, busqueda, ['nombre', 'apellido', 'ci', 'codigo'])
    if categoria:
        consulta = consulta.filter(categoria=categoria)
    if estado:
        consulta = consulta.filter(estado=estado)

    opciones = {
        'apellido': 'Apellido (A-Z)',
        '-total_partidos': 'Más partidos dirigidos',
    }
    consulta, orden_actual = _orden(request, consulta, opciones, 'apellido')
    return render(
        request,
        'admin/arbitros.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            categorias=Arbitro.CATEGORIAS,
            categoria_actual=categoria,
            estado_actual=estado,
            estados=Arbitro.ESTADOS,
            orden_actual=orden_actual,
            opciones_orden=_opciones_orden(opciones),
            puede_editar=puede_escribir(_rol(request), 'arbitros'),
        ),
    )


@modulo_requerido('arbitros', escritura=True)
def arbitro_crear(request):
    form = forms.ArbitroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        arbitro = form.save()
        registrar(
            request, 'arbitros', 'CREAR',
            f'Árbitro registrado · {arbitro.apellido}, {arbitro.nombre}',
        )
        messages.success(request, 'Árbitro registrado en el plantel.')
        return redirect('arbitros')
    return _formulario(
        request,
        form,
        'Nuevo árbitro',
        'Registre los datos y la licencia del árbitro.',
        reverse('arbitros'),
        icono='sports',
        guardar_texto='Registrar árbitro',
    )


@modulo_requerido('arbitros', escritura=True)
def arbitro_editar(request, pk):
    arbitro = get_object_or_404(Arbitro, pk=pk)
    form = forms.ArbitroForm(request.POST or None, instance=arbitro)
    if request.method == 'POST' and form.is_valid():
        arbitro = form.save()
        registrar(
            request, 'arbitros', 'EDITAR',
            f'Árbitro actualizado · {arbitro.apellido}, {arbitro.nombre}',
        )
        messages.success(request, 'Datos del árbitro actualizados.')
        return redirect('arbitro_detalle', pk=arbitro.pk)
    return _formulario(
        request,
        form,
        f'Editar · {arbitro.apellido}, {arbitro.nombre}',
        'Actualice licencia, disponibilidad o estado.',
        reverse('arbitro_detalle', args=[arbitro.pk]),
        icono='sports',
    )


@modulo_requerido('arbitros')
def arbitro_detalle(request, pk):
    arbitro = get_object_or_404(Arbitro, pk=pk)
    asignaciones = arbitro.asignacionarbitro_set.select_related(
        'partido__campeonato', 'partido__equipo_local', 'partido__equipo_visitante'
    ).order_by('-partido__fecha')
    return render(
        request,
        'admin/arbitro_detalle.html',
        contexto(
            request,
            arbitro=arbitro,
            asignaciones=asignaciones,
            puede_editar=puede_escribir(_rol(request), 'arbitros'),
        ),
    )


@modulo_requerido('arbitros', escritura=True)
def arbitro_eliminar(request, pk):
    arbitro = get_object_or_404(Arbitro, pk=pk)
    asignaciones = arbitro.asignacionarbitro_set.count()
    bloqueo = ''
    if asignaciones:
        bloqueo = (
            f'El árbitro tiene {asignaciones} designación(es) registradas. '
            'Cámbielo a «Inactivo» para conservar el historial.'
        )
    if request.method == 'POST':
        if bloqueo:
            messages.error(request, bloqueo)
            return redirect('arbitro_detalle', pk=arbitro.pk)
        nombre = str(arbitro)
        arbitro.delete()
        registrar(request, 'arbitros', 'ELIMINAR', f'Árbitro eliminado · {nombre}')
        messages.success(request, f'Árbitro {nombre} eliminado.')
        return redirect('arbitros')
    return _confirmar(
        request,
        arbitro,
        'Eliminar árbitro',
        'El árbitro se borrará del plantel.',
        reverse('arbitro_detalle', args=[arbitro.pk]),
        bloqueo,
    )


# ---------------------------------------------------------------------------
# Asignaciones arbitrales
# ---------------------------------------------------------------------------


@modulo_requerido('asignaciones')
def asignaciones(request):
    busqueda = normalizar_busqueda(request)
    campeonato_id = (request.GET.get('campeonato') or '').strip()
    arbitro_id = (request.GET.get('arbitro') or '').strip()

    consulta = AsignacionArbitro.objects.select_related(
        'partido__campeonato', 'partido__equipo_local',
        'partido__equipo_visitante', 'arbitro',
    )
    consulta = buscar(
        consulta, busqueda,
        ['arbitro__nombre', 'arbitro__apellido',
         'partido__equipo_local__nombre', 'partido__equipo_visitante__nombre'],
    )
    if campeonato_id.isdigit():
        consulta = consulta.filter(partido__campeonato_id=campeonato_id)
    if arbitro_id.isdigit():
        consulta = consulta.filter(arbitro_id=arbitro_id)

    return render(
        request,
        'admin/asignaciones.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            campeonatos=Campeonato.objects.all(),
            arbitros=Arbitro.objects.filter(estado='ACTIVO'),
            campeonato_actual=campeonato_id,
            arbitro_actual=arbitro_id,
            puede_editar=puede_escribir(_rol(request), 'asignaciones'),
        ),
    )


@modulo_requerido('asignaciones', escritura=True)
def asignacion_crear(request):
    inicial = {}
    partido_id = request.GET.get('partido')
    if partido_id and partido_id.isdigit():
        inicial['partido'] = partido_id
    form = forms.AsignacionForm(request.POST or None, initial=inicial)
    if request.method == 'POST' and form.is_valid():
        asignacion = form.save()
        registrar(
            request, 'asignaciones', 'CREAR',
            f'Designación arbitral · {asignacion}',
        )
        messages.success(request, 'Designación arbitral registrada.')
        return redirect('asignaciones')
    return _formulario(
        request,
        form,
        'Nueva designación arbitral',
        'Asigne un árbitro disponible a un partido y cubra cada rol.',
        reverse('asignaciones'),
        icono='sports',
        guardar_texto='Registrar designación',
    )


@modulo_requerido('asignaciones', escritura=True)
def asignacion_editar(request, pk):
    asignacion = get_object_or_404(AsignacionArbitro, pk=pk)
    form = forms.AsignacionForm(request.POST or None, instance=asignacion)
    if request.method == 'POST' and form.is_valid():
        asignacion = form.save()
        registrar(
            request, 'asignaciones', 'EDITAR',
            f'Designación actualizada · {asignacion}',
        )
        messages.success(request, 'Designación actualizada.')
        return redirect('asignaciones')
    return _formulario(
        request,
        form,
        'Editar designación',
        'Cambie el árbitro o el rol asignado.',
        reverse('asignaciones'),
        icono='sports',
    )


@modulo_requerido('asignaciones', escritura=True)
def asignacion_eliminar(request, pk):
    asignacion = get_object_or_404(AsignacionArbitro, pk=pk)
    if request.method == 'POST':
        detalle = str(asignacion)
        asignacion.delete()
        registrar(
            request, 'asignaciones', 'ELIMINAR',
            f'Designación eliminada · {detalle}',
        )
        messages.success(request, 'Designación eliminada.')
        return redirect('asignaciones')
    return _confirmar(
        request,
        asignacion,
        'Eliminar designación',
        'El árbitro dejará de estar asignado a este partido.',
        reverse('asignaciones'),
    )


# ---------------------------------------------------------------------------
# Sanciones
# ---------------------------------------------------------------------------


@modulo_requerido('sanciones')
def sanciones(request):
    busqueda = normalizar_busqueda(request)
    tipo = (request.GET.get('tipo') or '').strip()
    estado = (request.GET.get('estado') or '').strip()
    club_id = (request.GET.get('club') or '').strip()

    consulta = Sancion.objects.select_related(
        'deportista', 'club', 'campeonato', 'partido'
    )
    consulta = buscar(
        consulta, busqueda,
        ['descripcion', 'deportista__nombre', 'deportista__apellido',
         'club__nombre', 'observaciones'],
    )
    if tipo:
        consulta = consulta.filter(tipo=tipo)
    if estado:
        consulta = consulta.filter(estado=estado)
    if club_id.isdigit():
        consulta = consulta.filter(club_id=club_id)

    return render(
        request,
        'admin/sanciones.html',
        contexto(
            request,
            pagina=paginar(request, consulta),
            total=consulta.count(),
            busqueda=busqueda,
            clubes=Club.objects.all(),
            club_actual=club_id,
            tipo_actual=tipo,
            tipos=Sancion.TIPOS,
            estado_actual=estado,
            estados=Sancion.ESTADOS,
            puede_editar=puede_escribir(_rol(request), 'sanciones'),
        ),
    )


@modulo_requerido('sanciones', escritura=True)
def sancion_crear(request):
    form = forms.SancionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        sancion = form.save()
        registrar(
            request, 'sanciones', 'CREAR',
            f'Sanción registrada · {sancion.get_tipo_display()} · {sancion}',
        )
        messages.success(request, 'Sanción registrada en el tribunal.')
        return redirect('sanciones')
    return _formulario(
        request,
        form,
        'Nueva sanción',
        'Registre la resolución del Tribunal de Penas.',
        reverse('sanciones'),
        icono='gavel',
        guardar_texto='Registrar sanción',
    )


@modulo_requerido('sanciones', escritura=True)
def sancion_editar(request, pk):
    sancion = get_object_or_404(Sancion, pk=pk)
    form = forms.SancionForm(request.POST or None, instance=sancion)
    if request.method == 'POST' and form.is_valid():
        sancion = form.save()
        registrar(
            request, 'sanciones', 'EDITAR',
            f'Sanción actualizada · {sancion}',
        )
        messages.success(request, 'Sanción actualizada.')
        return redirect('sanciones')
    return _formulario(
        request,
        form,
        'Editar sanción',
        'Actualice el estado o el alcance de la sanción.',
        reverse('sanciones'),
        icono='gavel',
    )


@modulo_requerido('sanciones', escritura=True)
def sancion_eliminar(request, pk):
    sancion = get_object_or_404(Sancion, pk=pk)
    if request.method == 'POST':
        detalle = str(sancion)
        sancion.delete()
        registrar(request, 'sanciones', 'ELIMINAR', f'Sanción eliminada · {detalle}')
        messages.success(request, 'Sanción eliminada.')
        return redirect('sanciones')
    return _confirmar(
        request,
        sancion,
        'Eliminar sanción',
        'La sanción se borrará del historial disciplinario.',
        reverse('sanciones'),
    )
