"""
Inicializa el sistema con datos de demostración:
  - Grupos institucionales (ADMIN, DIRIGENTE, ARBITRO, TESORERO)
  - Superusuario:  admin  /  Admin12345
  - Usuarios por rol: dirigente, arbitro, tesorero (clave: Demo12345)
"""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

ROLES = ['ADMIN', 'DIRIGENTE', 'ARBITRO', 'TESORERO']

USUARIOS = [
    ('admin', 'Administración General', 'Admin12345', ['ADMIN']),
    ('dirigente', 'Dirigente de Club', 'Demo12345', ['DIRIGENTE']),
    ('arbitro', 'Comisión de Árbitros', 'Demo12345', ['ARBITRO']),
    ('tesorero', 'Tesorería AFO', 'Demo12345', ['TESORERO']),
]


class Command(BaseCommand):
    help = 'Crea grupos, superusuario y usuarios de demostración del sistema AFO.'

    def handle(self, *args, **options):
        for name in ROLES:
            Group.objects.get_or_create(name=name)

        for username, full_name, password, groups in USUARIOS:
            user, created = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.first_name = full_name
            user.is_staff = username == 'admin'
            user.is_active = True
            user.save()
            user.groups.set(Group.objects.filter(name__in=groups))
            verb = 'creado' if created else 'actualizado'
            self.stdout.write(self.style.SUCCESS(f'Usuario {username} {verb} (clave: {password})'))

        self.stdout.write(self.style.SUCCESS('Sistema de demostración inicializado correctamente.'))