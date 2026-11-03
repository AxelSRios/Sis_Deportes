
from django.db import models
from django.conf import settings


class Club(models.Model):
    nombre = models.CharField(max_length=150)
    direccion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    fundacion = models.DateField(null=True, blank=True)
    presidente = models.CharField(max_length=150, null=True, blank=True)
    categoria_ingreso = models.CharField(max_length=100, null=True, blank=True)
    nit_personeria = models.CharField(max_length=100, null=True, blank=True)
    estado_juridico = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'clubes'

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    class Meta:
        db_table = 'categorias'

    def __str__(self):
        return self.nombre


class Campeonato(models.Model):
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    disciplina = models.CharField(max_length=100, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_conclusion = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'campeonatos'

    def __str__(self):
        return self.nombre

class Equipo(models.Model):
    nombre = models.CharField(max_length=150)
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'equipos'

    def __str__(self):
        return self.nombre


class Deportista(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=30, null=True, blank=True)
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'deportistas'

    def __str__(self):
        return self.nombre + ' ' + self.apellido


class Arbitro(models.Model):

    CATEGORIAS = [
        ('FIFA', 'FIFA'),
        ('NACIONAL', 'Nacional'),
        ('DEPARTAMENTAL', 'Departamental'),
    ]

    ESPECIALIDADES = [
        ('CENTRAL', 'Árbitro central'),
        ('ASISTENTE', 'Árbitro asistente'),
        ('CUARTO', 'Cuarto árbitro'),
        ('OTRO', 'Otro'),
    ]

    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]

    codigo = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    ci = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True
    )

    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(max_length=150, blank=True)

    categoria = models.CharField(
        max_length=20,
        choices=CATEGORIAS,
        default='DEPARTAMENTAL'
    )

    especialidad = models.CharField(
        max_length=20,
        choices=ESPECIALIDADES,
        default='CENTRAL'
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default='ACTIVO'
    )

    fecha_registro = models.DateField(
    auto_now_add=True,
    null=True,
    blank=True
)

    class Meta:
        db_table = 'arbitros'

    def __str__(self):
        return self.nombre + ' ' + self.apellido

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.codigo:
            self.codigo = f'ARB-{self.pk:05d}'
            super().save(update_fields=['codigo'])


class Partido(models.Model):
    campeonato = models.ForeignKey(
        Campeonato,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    equipo_local = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partidos_locales'
    )
    equipo_visitante = models.ForeignKey(
        Equipo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partidos_visitantes'
    )
    fecha = models.DateTimeField(null=True, blank=True)
    resultado = models.TextField(null=True, blank=True)
    escenario = models.CharField(max_length=150, blank=True)
    terna_arbitral = models.TextField(blank=True)
    estado = models.CharField(max_length=50, default='Programado')

    class Meta:
        db_table = 'partidos'

    def __str__(self):
        return f'{self.equipo_local} vs {self.equipo_visitante}'



class AsignacionArbitro(models.Model):
    partido = models.ForeignKey(
        Partido, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    arbitro = models.ForeignKey(
        Arbitro, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'asignaciones_arbitros'


class Inscripcion(models.Model):
    deportista = models.ForeignKey(
        Deportista, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    equipo = models.ForeignKey(
        Equipo, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    campeonato = models.ForeignKey(
        Campeonato, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        db_table = 'inscripciones'


class Sancion(models.Model):
    deportista = models.ForeignKey(
        Deportista, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    descripcion = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'sanciones'


class Pago(models.Model):
    deportista = models.ForeignKey(
        Deportista, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    fecha = models.DateTimeField(null=True, blank=True)
    tipo = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'pagos'


class HistorialOperacion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    operacion = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'historial_operaciones'
