"""
Vistas de la aplicación core.

Traduce el front-end estático original (HTML/CSS/JS) en páginas servidas
por Django, integrando autenticación real sobre django.contrib.auth.
"""
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

ROLES_LABELS = {
    'ADMIN': 'Administrador General de la A.F.O.',
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
        elif role and not user.is_superuser and not (user.groups.filter(name=role).exists()):
            error = f'El rol seleccionado [{role}] no corresponde a los permisos federativos de la cuenta.'
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


def _shell(request, template):
    return render(request, template, {'rol_label': ROLES_LABELS.get(request.session.get('rol'), '')})


@login_required
def panel(request):
    return _shell(request, 'panel_general.html')


@login_required
def clubes(request):
    return _shell(request, 'clubes_equipos.html')


@login_required
def campeonatos(request):
    return _shell(request, 'campeonatos_fixture.html')


@login_required
def arbitraje(request):
    return _shell(request, 'arbitraje_designaciones.html')


@login_required
def deportistas(request):
    return _shell(request, 'deportistas_fichajes.html')


@login_required
def tesoreria(request):
    return _shell(request, 'tesoreria_pagos.html')


@login_required
def auditoria(request):
    return _shell(request, 'auditoria_usuarios.html')