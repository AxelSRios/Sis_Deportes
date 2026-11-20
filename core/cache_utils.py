"""Versión de caché compartida por las vistas de lectura intensiva.

Cada operación registrada en auditoría incrementa la versión, de modo que
los datos cacheados (panel, catálogo de reportes) se descartan en cuanto
alguien crea, edita o elimina algo. Así la navegación repetida es rápida
sin mostrar información vieja después de una operación.

La caché por defecto de Django es local al proceso. En un despliegue con
varios workers conviene configurar Redis o Memcached en ``CACHES`` para
que la invalidación sea común a todos.
"""
from django.core.cache import cache

VERSION_KEY = 'afo:cache-version'


def version_cache() -> int:
    """Versión actual; se inicializa sola la primera vez."""
    version = cache.get(VERSION_KEY)
    if version is None:
        version = 1
        cache.set(VERSION_KEY, version, None)
    return int(version)


def invalidar_cache() -> None:
    """Fuerza el recálculo de todo lo cacheado con la versión anterior."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 1, None)
