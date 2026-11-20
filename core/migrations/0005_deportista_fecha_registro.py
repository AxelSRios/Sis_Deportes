"""Agrega la fecha de alta federativa del deportista.

Se usa en el Panel General para la serie mensual de registros. La columna se
crea como nullable para no inventar fechas en los registros históricos: al
añadir la columna, Django aplica la fecha de la migración a todas las filas
existentes, por eso se limpian inmediatamente después. Esas filas quedan en
NULL y el panel las informa aparte ("registros históricos sin fecha de alta").
"""
from django.db import migrations, models


def limpiar_fechas_historicas(apps, schema_editor):
    """Deja sin fecha los registros que existían antes de esta migración."""
    Deportista = apps.get_model('core', 'Deportista')
    Deportista.objects.update(fecha_registro=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_arbitro_categoria_arbitro_ci_arbitro_codigo_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='deportista',
            name='fecha_registro',
            field=models.DateField(auto_now_add=True, null=True, blank=True),
        ),
        migrations.RunPython(
            limpiar_fechas_historicas,
            migrations.RunPython.noop,
        ),
    ]
