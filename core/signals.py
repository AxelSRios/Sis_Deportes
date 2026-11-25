"""Señales de autenticación conectadas al registro de accesos."""
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .accesslog import registrar_acceso
from .roles import resolver_rol


@receiver(user_logged_in, dispatch_uid='afo_acceso_login')
def registrar_login(sender, request, user, **kwargs):
    registrar_acceso(
        'LOGIN',
        request=request,
        usuario=user,
        username=user.get_username(),
        rol=resolver_rol(user),
        detalle='Autenticación correcta',
    )


@receiver(user_logged_out, dispatch_uid='afo_acceso_logout')
def registrar_logout(sender, request, user, **kwargs):
    if user is None:
        return
    registrar_acceso(
        'LOGOUT',
        request=request,
        usuario=user,
        username=user.get_username(),
        rol=resolver_rol(user),
        detalle='Cierre de sesión',
    )


@receiver(user_login_failed, dispatch_uid='afo_acceso_fallido')
def registrar_login_fallido(sender, credentials, request=None, **kwargs):
    # Nunca se lee ni se guarda la contraseña.
    username = ''
    if isinstance(credentials, dict):
        username = credentials.get('username') or credentials.get('email') or ''
    registrar_acceso(
        'LOGIN_FALLIDO',
        request=request,
        username=username,
        detalle='Credenciales inválidas',
    )
