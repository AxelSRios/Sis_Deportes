"""Filtros de plantilla reutilizables para la interfaz pública de la AFO."""
import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

# Palabras que no aportan a las siglas de un club.
_STOPWORDS = {
    'club', 'c.d.', 'cd', 'c', 'd', 'deportivo', 'deportiva', 'empresa',
    'minera', 'asociacion', 'asociación', 'de', 'del', 'la', 'las', 'los',
    'el', 'y', 'e', 'the', 'f.c.', 'fc', 's.a.', 'sa',
}


@register.filter
def initials(value, max_letters=3):
    """Devuelve las iniciales visibles de un nombre.

    Ejemplos: "Club Deportivo Sur-Car" -> "SC"; "Oruro Royal Club" -> "ORC".
    Si no quedan palabras significativas, usa las primeras letras del texto.
    """
    if not value:
        return 'AFO'

    try:
        max_letters = int(max_letters)
    except (TypeError, ValueError):
        max_letters = 3

    clean = str(value).replace('.', ' ').replace('-', ' ').replace('/', ' ')
    words = [w for w in clean.split() if w]

    meaningful = [w for w in words if w.lower() not in _STOPWORDS]
    if not meaningful:
        meaningful = words

    if len(meaningful) == 1:
        return meaningful[0][:2].upper() or 'AFO'

    letters = ''.join(w[0] for w in meaningful[:max_letters])
    return letters.upper() or 'AFO'


@register.filter
def display_category(value):
    """Presenta una categoría libre de forma legible: 'primera-a' -> 'Primera A'."""
    if not value:
        return 'Club afiliado'
    text = str(value).replace('-', ' ').replace('_', ' ').strip()
    return text.title()


@register.filter
def short_name(value, max_length=28):
    """Recorta nombres largos sin cortar palabras a la mitad."""
    if not value:
        return ''
    try:
        max_length = int(max_length)
    except (TypeError, ValueError):
        max_length = 28

    text = str(value).strip()
    if len(text) <= max_length:
        return text

    cut = text[:max_length].rsplit(' ', 1)[0]
    return f'{cut}…'


@register.filter
def estado_clase(value):
    """Clases del chip de estado dentro de la paleta tricolor A.F.O."""
    estado = str(value or '').strip().upper()
    if estado in {
        'ACTIVO', 'APROBADA', 'PAGADO', 'FINALIZADO', 'CUMPLIDA',
        'VIGENTE', 'DISPONIBLE',
    }:
        return 'bg-secondary-fixed text-on-secondary-fixed'
    if estado in {'PENDIENTE', 'PLANIFICADO', 'PROGRAMADO', 'EN_JUEGO'}:
        return 'bg-primary/10 text-primary'
    if estado in {
        'SUSPENDIDO', 'SUSPENDIDA', 'RECHAZADA', 'ANULADA', 'ANULADO',
        'CANCELADO', 'BAJA', 'INACTIVO', 'NO_DISPONIBLE',
    }:
        return 'bg-primary text-on-primary'
    return 'bg-surface-container text-on-surface-variant'


@register.filter
def estado_label(value):
    """Presenta estados técnicos como texto legible."""
    if value is None or value == '':
        return 'Sin estado'
    return str(value).replace('_', ' ').strip().capitalize()


@register.filter
def si_no(value):
    return 'Sí' if value else 'No'


@register.filter
def rol_label(value):
    """Etiqueta legible del rol institucional guardado en el registro."""
    from core.roles import ROLES_LABELS
    if not value:
        return '—'
    return ROLES_LABELS.get(str(value), str(value))


@register.filter
def rango_paginas(pagina, vecinos=2):
    """Números de página visibles con elipsis, para paginaciones largas.

    Devuelve, por ejemplo, [1, '…', 4, 5, 6, '…', 20]. Es solo una ayuda
    de presentación: no altera la consulta ni el número de página actual.
    """
    try:
        actual = int(pagina.number)
        total = int(pagina.paginator.num_pages)
        vecinos = int(vecinos)
    except (AttributeError, TypeError, ValueError):
        return []

    if total <= 1:
        return []

    visibles = {1, total}
    for numero in range(actual - vecinos, actual + vecinos + 1):
        if 1 <= numero <= total:
            visibles.add(numero)

    resultado = []
    anterior = 0
    for numero in sorted(visibles):
        if anterior and numero - anterior > 1:
            resultado.append('…')
        resultado.append(numero)
        anterior = numero
    return resultado


# Secciones del sistema: clave de navegación, miga, título y descripción.
_SECCIONES = {
    'panel': ('panel', 'Panel General', 'Panel General',
              'Centro de control institucional de la A.F.O.'),
    'gestion_deportiva': ('gestion', 'Gestión Deportiva', 'Gestión Deportiva',
                          'Clubes, planteles, fichajes y cuerpo arbitral.'),
    'competencia': ('competencia', 'Competencia', 'Centro de Competencia',
                    'Torneos, calendario, posiciones y resultados oficiales.'),
    'administracion': ('administracion', 'Administración', 'Centro de Administración',
                       'Caja, usuarios, reportes y auditoría institucional.'),
    'clubes': ('clubes', 'Clubes', 'Clubes afiliados',
               'Padrón institucional de la A.F.O.'),
    'canchas': ('canchas', 'Canchas', 'Canchas y escenarios',
                'Estadios, complejos y canchas oficiales de la A.F.O.'),
    'equipos': ('equipos', 'Equipos', 'Equipos',
                'Planteles por club, categoría y temporada.'),
    'deportistas': ('deportistas', 'Deportistas', 'Deportistas',
                    'Fichas, habilitaciones y sanciones del padrón.'),
    'categorias': ('categorias', 'Categorías', 'Categorías',
                   'Divisiones y límites de edad del fútbol orureño.'),
    'campeonatos': ('campeonatos', 'Campeonatos', 'Campeonatos',
                    'Torneos oficiales, calendario y tablas de posiciones.'),
    'inscripciones': ('inscripciones', 'Inscripciones', 'Inscripciones',
                      'Altas de equipos y deportistas en cada torneo.'),
    'partidos': ('partidos', 'Partidos', 'Partidos',
                 'Fixture, programación y resultados homologados.'),
    'arbitros': ('arbitros', 'Árbitros', 'Árbitros',
                 'Cuerpo arbitral y disponibilidad para designaciones.'),
    'asignaciones': ('asignaciones', 'Designaciones', 'Designaciones arbitrales',
                     'Ternas asignadas a cada encuentro oficial.'),
    'sanciones': ('sanciones', 'Sanciones', 'Sanciones',
                  'Resoluciones del Tribunal de Penas.'),
    'tesoreria': ('tesoreria', 'Tesorería', 'Tesorería',
                  'Caja institucional, comprobantes y pagos.'),
    'usuarios': ('usuarios', 'Usuarios', 'Usuarios',
                 'Cuentas, roles y permisos del sistema.'),
    'perfil': ('perfil', 'Mi perfil', 'Mi perfil',
               'Datos de la cuenta y seguridad de acceso.'),
    'reportes': ('reportes', 'Reportes', 'Reportes',
                 'Exportaciones oficiales en PDF, Excel y CSV.'),
    'auditoria': ('auditoria', 'Auditoría', 'Auditoría',
                  'Historial de operaciones y trazabilidad del sistema.'),
    'accesos': ('accesos', 'Accesos', 'Accesos y sesiones',
                'Inicios, cierres e intentos fallidos registrados.'),
    'accesos_sesiones': ('accesos', 'Accesos', 'Accesos y sesiones',
                         'Inicios, cierres e intentos fallidos registrados.'),
}

_PREFIJOS_SECCION = (
    ('club', 'clubes'), ('cancha', 'canchas'), ('equipo', 'equipos'),
    ('deportista', 'deportistas'),
    ('categoria', 'categorias'), ('campeonato', 'campeonatos'),
    ('inscripcion', 'inscripciones'), ('partido', 'partidos'),
    ('arbitro', 'arbitros'), ('arbitraje', 'arbitros'),
    ('asignacion', 'asignaciones'), ('sancion', 'sanciones'),
    ('pago', 'tesoreria'), ('tesoreria', 'tesoreria'),
    ('usuario', 'usuarios'), ('perfil', 'perfil'), ('password', 'perfil'),
    ('reporte', 'reportes'), ('auditoria', 'auditoria'),
)


@register.simple_tag(takes_context=True)
def seccion_actual(context):
    """Sección de navegación y textos de cabecera según la URL resuelta."""
    request = context.get('request')
    nombre = getattr(getattr(request, 'resolver_match', None), 'url_name', '') or ''
    entrada = _SECCIONES.get(nombre)
    if entrada is None:
        for prefijo, candidata in _PREFIJOS_SECCION:
            if nombre.startswith(prefijo):
                entrada = next(
                    (item for item in _SECCIONES.values() if item[0] == candidata),
                    None,
                )
                break
    if entrada is None:
        entrada = _SECCIONES['panel']
    clave, miga, titulo, descripcion = entrada
    return {
        'clave': clave,
        'miga': miga,
        'titulo': titulo,
        'descripcion': descripcion,
    }


@register.simple_tag
def static_v(path):
    """URL del estático con su fecha de modificación como versión.

    El navegador guarda los JS/CSS por heurística; al cambiar el archivo
    cambia también la URL y nadie queda con una copia vieja.
    """
    url = static(path)
    try:
        ruta = finders.find(path)
        version = int(os.path.getmtime(ruta)) if ruta else 0
    except (OSError, TypeError):
        version = 0
    return f'{url}?v={version}'
