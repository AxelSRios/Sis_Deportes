"""Registro estructurado de accesos y sesiones institucionales.

La escritura nunca debe interrumpir el inicio o cierre de sesión. Tampoco
se guardan contraseñas, tokens ni el cuerpo de la petición.
"""
import logging
import re

from .models import RegistroAcceso
from .roles import resolver_rol

logger = logging.getLogger('afo.accesos')

_CONTROL = re.compile(r'[\x00-\x1f\x7f]+')


def _limpiar(valor, maximo):
    texto = _CONTROL.sub(' ', str(valor or '')).strip()
    return texto[:maximo]


def _ip(request):
    if request is None:
        return '', ''
    directa = _limpiar(request.META.get('REMOTE_ADDR', ''), 64)
    proxy = _limpiar(request.META.get('HTTP_X_FORWARDED_FOR', ''), 255)
    return directa, proxy


def registrar_acceso(evento, request=None, usuario=None, username='', rol='', detalle=''):
    """Guarda un evento de acceso sin exponer credenciales.

    `evento` debe ser uno de RegistroAcceso.EVENTOS. Si algo falla, se
    registra en el logger del proyecto y la autenticación continúa.
    """
    try:
        ip, ip_proxy = _ip(request)
        user_agent = _limpiar(
            request.META.get('HTTP_USER_AGENT', '') if request is not None else '',
            300,
        )
        rol_final = _limpiar(rol, 24)
        if not rol_final and usuario is not None:
            rol_final = resolver_rol(usuario)
        if not rol_final and request is not None:
            try:
                rol_final = _limpiar(request.session.get('rol', ''), 24)
            except Exception:
                rol_final = ''

        nombre = _limpiar(username, 150)
        if not nombre and usuario is not None:
            nombre = _limpiar(usuario.get_username(), 150)

        RegistroAcceso.objects.create(
            evento=evento,
            usuario=usuario if getattr(usuario, 'pk', None) else None,
            username=nombre,
            rol=rol_final,
            ip=ip,
            ip_proxy=ip_proxy,
            user_agent=user_agent,
            detalle=_limpiar(detalle, 255),
        )
    except Exception:
        # Un fallo de auditoría no debe impedir el acceso al sistema.
        logger.warning('No se pudo registrar el evento de acceso %s', evento)
