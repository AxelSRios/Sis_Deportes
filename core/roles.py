"""Roles institucionales y su resolución a partir de los grupos de Django."""

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


def resolver_rol(user):
    """Deduce el rol institucional sin depender de la sesión."""
    if not user or not getattr(user, 'is_authenticated', False):
        return ''
    if getattr(user, 'is_superuser', False):
        return 'ADMIN'
    try:
        group_names = set(user.groups.values_list('name', flat=True))
    except Exception:
        return 'USUARIO'
    for role, aliases in ROLE_GROUP_ALIASES.items():
        if group_names & aliases:
            return role
    return 'USUARIO'
