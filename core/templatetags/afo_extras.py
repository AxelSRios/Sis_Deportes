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
    """Clases del chip de estado según la situación del registro."""
    estado = str(value or '').strip().upper()
    if estado in {
        'ACTIVO', 'APROBADA', 'PAGADO', 'FINALIZADO', 'CUMPLIDA',
        'VIGENTE', 'DISPONIBLE',
    }:
        return 'bg-secondary-fixed/60 text-on-secondary-fixed'
    if estado in {'PENDIENTE', 'PLANIFICADO', 'PROGRAMADO', 'EN_JUEGO'}:
        return 'bg-tertiary-fixed/60 text-tertiary'
    if estado in {
        'SUSPENDIDO', 'SUSPENDIDA', 'RECHAZADA', 'ANULADA', 'ANULADO',
        'CANCELADO', 'BAJA', 'INACTIVO', 'NO_DISPONIBLE',
    }:
        return 'bg-error/10 text-error'
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
