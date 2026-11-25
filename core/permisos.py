"""Permisos por rol y utilidades comunes de los módulos administrativos."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect
from django.utils import timezone

from .cache_utils import invalidar_cache
from .models import HistorialOperacion
from .views import (
    ROLES_AUDITORIA,
    ROLES_FINANZAS,
    ROLES_LABELS,
    _forbidden,
    _user_role,
)

TODOS = {'ADMIN', 'DIRIGENTE', 'ARBITRO', 'TESORERO'}

# Quién puede crear, editar y eliminar en cada módulo.
ESCRITURA = {
    'clubes': {'ADMIN'},
    'canchas': {'ADMIN'},
    'equipos': {'ADMIN', 'DIRIGENTE'},
    'deportistas': {'ADMIN', 'DIRIGENTE'},
    'categorias': {'ADMIN'},
    'campeonatos': {'ADMIN'},
    'inscripciones': {'ADMIN', 'DIRIGENTE'},
    'partidos': {'ADMIN', 'ARBITRO'},
    'arbitros': {'ADMIN'},
    'asignaciones': {'ADMIN', 'ARBITRO'},
    'sanciones': {'ADMIN'},
    'pagos': {'ADMIN', 'TESORERO'},
    'usuarios': {'ADMIN'},
}

# Módulos cuyo acceso de lectura está restringido.
LECTURA_RESTRINGIDA = {
    'pagos': ROLES_FINANZAS,
    'usuarios': {'ADMIN'},
    'auditoria': ROLES_AUDITORIA,
}

ETIQUETAS_MODULO = {
    'clubes': 'Clubes',
    'canchas': 'Canchas',
    'equipos': 'Equipos',
    'deportistas': 'Deportistas',
    'categorias': 'Categorías',
    'campeonatos': 'Campeonatos',
    'inscripciones': 'Inscripciones',
    'partidos': 'Partidos',
    'arbitros': 'Árbitros',
    'asignaciones': 'Asignaciones arbitrales',
    'sanciones': 'Sanciones',
    'pagos': 'Tesorería',
    'usuarios': 'Usuarios',
    'auditoria': 'Auditoría',
}


def puede_leer(rol, modulo):
    permitidos = LECTURA_RESTRINGIDA.get(modulo, TODOS)
    return rol in permitidos


def puede_escribir(rol, modulo):
    return rol in ESCRITURA.get(modulo, set())


def modulo_requerido(modulo, escritura=False):
    """Protege una vista por rol; devuelve 403 con el diseño institucional."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            rol = _user_role(request)
            if not puede_leer(rol, modulo):
                return _forbidden(
                    request,
                    'Su rol no tiene acceso a este módulo.',
                )
            if escritura and not puede_escribir(rol, modulo):
                return _forbidden(
                    request,
                    'Su rol puede consultar este módulo, pero no modificarlo.',
                )
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador


def contexto(request, **extra):
    """Contexto común de todas las páginas administrativas."""
    rol = _user_role(request)
    datos = {
        'rol': rol,
        'rol_label': ROLES_LABELS.get(rol, ''),
        'usuario_nombre': request.user.get_full_name() or request.user.username,
        'temporada_actual': timezone.localdate().year,
        'puede_ver_finanzas': puede_leer(rol, 'pagos'),
        'puede_ver_usuarios': puede_leer(rol, 'usuarios'),
        'puede_ver_auditoria': puede_leer(rol, 'auditoria'),
        'puede_escribir_pagos': puede_escribir(rol, 'pagos'),
    }
    datos.update(extra)
    return datos


def paginar(request, queryset, por_pagina=15):
    paginador = Paginator(queryset, por_pagina)
    return paginador.get_page(request.GET.get('page'))


def normalizar_busqueda(request, parametro='buscar'):
    return (request.GET.get(parametro) or '').strip()


def registrar(request, modulo, accion, detalle):
    """Huella de auditoría. Nunca interrumpe la operación principal."""
    try:
        HistorialOperacion.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            modulo=modulo,
            accion=accion,
            operacion=detalle,
            fecha=timezone.now(),
        )
    except Exception:
        pass
    # Cualquier operación de escritura invalida los datos cacheados.
    invalidar_cache()


def buscar(queryset, termino, campos):
    """Filtro OR insensible a mayúsculas sobre los campos indicados."""
    if not termino:
        return queryset
    consulta = Q()
    for campo in campos:
        consulta |= Q(**{f'{campo}__icontains': termino})
    return queryset.filter(consulta)


def volver(request, por_defecto):
    """Respeta `next` solo si es local."""
    destino = request.POST.get('next') or request.GET.get('next')
    if destino and destino.startswith('/') and not destino.startswith('//'):
        return redirect(destino)
    return redirect(por_defecto)
