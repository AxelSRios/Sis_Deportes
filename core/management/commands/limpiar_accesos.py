"""Limpieza controlada del historial de accesos por antigüedad."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import RegistroAcceso


class Command(BaseCommand):
    help = 'Elimina registros de acceso anteriores al período de retención.'

    def add_arguments(self, parser):
        parser.add_argument('--dias', type=int, default=settings.AFO_ACCESS_LOG_RETENTION_DAYS)
        parser.add_argument('--simular', action='store_true', help='Solo cuenta, no elimina.')

    def handle(self, *args, **options):
        dias = max(1, int(options['dias']))
        corte = timezone.now() - timedelta(days=dias)
        consulta = RegistroAcceso.objects.filter(fecha__lt=corte)
        cantidad = consulta.count()
        if options['simular']:
            self.stdout.write(f'Se eliminarían {cantidad} registro(s) anteriores a {corte.isoformat()}.')
            return
        eliminados, _ = consulta.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Limpieza completada: {eliminados} registro(s) anteriores a {corte.date().isoformat()}.'
        ))
