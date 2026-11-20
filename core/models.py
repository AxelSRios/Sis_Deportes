from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Club(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('SUSPENDIDO', 'Suspendido'),
        ('BAJA', 'Dado de baja'),
    ]

    nombre = models.CharField(max_length=150)
    logo_url = models.URLField(max_length=300, blank=True)
    direccion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=30, null=True, blank=True)
    email = models.EmailField(max_length=150, blank=True)
    fundacion = models.DateField(null=True, blank=True)
    presidente = models.CharField(max_length=150, null=True, blank=True)
    categoria_ingreso = models.CharField(max_length=100, null=True, blank=True)
    nit_personeria = models.CharField(max_length=100, null=True, blank=True)
    estado_juridico = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO')
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'clubes'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    edad_min = models.PositiveSmallIntegerField(null=True, blank=True)
    edad_max = models.PositiveSmallIntegerField(null=True, blank=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'categorias'
        ordering = ['nombre']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.nombre

    def clean(self):
        if (
            self.edad_min is not None
            and self.edad_max is not None
            and self.edad_min > self.edad_max
        ):
            raise ValidationError(
                {'edad_max': 'La edad máxima no puede ser menor que la mínima.'}
            )


class Campeonato(models.Model):
    MODALIDADES = [
        ('LIGA', 'Liga (todos contra todos)'),
        ('ELIMINACION', 'Eliminación directa'),
        ('MIXTO', 'Fase de grupos y eliminación'),
    ]
    ESTADOS = [
        ('PLANIFICADO', 'Planificado'),
        ('ACTIVO', 'En curso'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
    ]

    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    disciplina = models.CharField(max_length=100, blank=True)
    temporada = models.PositiveSmallIntegerField(null=True, blank=True)
    modalidad = models.CharField(
        max_length=20, choices=MODALIDADES, default='LIGA'
    )
    reglamento = models.TextField(blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_conclusion = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADOS, null=True, blank=True
    )

    class Meta:
        db_table = 'campeonatos'
        ordering = ['-fecha_inicio', '-id']

    def __str__(self):
        return self.nombre

    @property
    def progreso(self):
        """Avance del calendario oficial entre el inicio y la conclusión (0–100).

        Solo se calcula cuando existen ambas fechas; sin ellas no se inventa
        ningún porcentaje y la interfaz muestra el estado sin barra de avance.
        """
        if not self.fecha_inicio or not self.fecha_conclusion:
            return None
        total = (self.fecha_conclusion - self.fecha_inicio).days
        if total <= 0:
            return 100
        transcurridos = (date.today() - self.fecha_inicio).days
        return max(0, min(100, round(transcurridos * 100 / total)))

    @property
    def dias_restantes(self):
        """Días que faltan para la conclusión (negativo si ya concluyó)."""
        if not self.fecha_conclusion:
            return None
        return (self.fecha_conclusion - date.today()).days

    def clean(self):
        if (
            self.fecha_inicio
            and self.fecha_conclusion
            and self.fecha_conclusion < self.fecha_inicio
        ):
            raise ValidationError(
                {'fecha_conclusion': 'La conclusión no puede ser anterior al inicio.'}
            )


class Equipo(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    ]

    nombre = models.CharField(max_length=150)
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    division = models.CharField(max_length=50, blank=True)
    temporada = models.PositiveSmallIntegerField(null=True, blank=True)
    entrenador = models.CharField(max_length=150, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='ACTIVO')

    class Meta:
        db_table = 'equipos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Deportista(models.Model):
    ESTADOS = [
        ('ACTIVO', 'Activo'),
        ('SUSPENDIDO', 'Suspendido'),
        ('INACTIVO', 'Inactivo'),
    ]
    GENEROS = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('OTRO', 'Otro'),
    ]

    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    ci = models.CharField(
        max_length=30, unique=True, null=True, blank=True
    )
    fecha_nacimiento = models.DateField(null=True, blank=True)
    genero = models.CharField(
        max_length=30, choices=GENEROS, null=True, blank=True
    )
    foto_url = models.URLField(max_length=300, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    equipo = models.ForeignKey(
        Equipo, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='ACTIVO'
    )
    # Fecha de alta federativa. Necesaria para las series mensuales del panel.
    # Las filas históricas quedan en NULL (no se inventan fechas).
    fecha_registro = models.DateField(
        auto_now_add=True,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'deportistas'
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.apellido}, {self.nombre}'


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
    licencia = models.CharField(max_length=50, blank=True)
    disponible = models.BooleanField(default=True)

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
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f'{self.apellido}, {self.nombre}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.codigo:
            self.codigo = f'ARB-{self.pk:05d}'
            super().save(update_fields=['codigo'])


class Partido(models.Model):
    ESTADOS = [
        ('Programado', 'Programado'),
        ('En juego', 'En juego'),
        ('Finalizado', 'Finalizado'),
        ('Suspendido', 'Suspendido'),
        ('Cancelado', 'Cancelado'),
    ]

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
    goles_local = models.PositiveSmallIntegerField(null=True, blank=True)
    goles_visitante = models.PositiveSmallIntegerField(null=True, blank=True)
    resultado = models.TextField(null=True, blank=True)
    escenario = models.CharField(max_length=150, blank=True)
    terna_arbitral = models.TextField(blank=True)
    estado = models.CharField(
        max_length=50, choices=ESTADOS, default='Programado'
    )

    class Meta:
        db_table = 'partidos'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.equipo_local} vs {self.equipo_visitante}'

    @property
    def marcador(self):
        if self.goles_local is None or self.goles_visitante is None:
            return None
        return f'{self.goles_local} - {self.goles_visitante}'

    def clean(self):
        if (
            self.equipo_local_id
            and self.equipo_visitante_id
            and self.equipo_local_id == self.equipo_visitante_id
        ):
            raise ValidationError(
                {'equipo_visitante': 'El equipo visitante debe ser distinto del local.'}
            )

    def save(self, *args, **kwargs):
        # Mantiene el campo libre `resultado` alineado con los goles para que
        # el panel y las fichas muestren siempre el mismo marcador.
        if self.goles_local is not None and self.goles_visitante is not None:
            self.resultado = f'{self.goles_local} - {self.goles_visitante}'
        super().save(*args, **kwargs)


class AsignacionArbitro(models.Model):
    ROLES = [
        ('CENTRAL', 'Árbitro central'),
        ('ASISTENTE1', 'Asistente 1'),
        ('ASISTENTE2', 'Asistente 2'),
        ('CUARTO', 'Cuarto árbitro'),
    ]

    partido = models.ForeignKey(
        Partido, on_delete=models.CASCADE,
        null=True, blank=True
    )
    arbitro = models.ForeignKey(
        Arbitro, on_delete=models.CASCADE,
        null=True, blank=True
    )
    rol = models.CharField(max_length=20, choices=ROLES, default='CENTRAL')

    class Meta:
        db_table = 'asignaciones_arbitros'
        ordering = ['partido', 'rol']
        unique_together = [('partido', 'arbitro')]

    def __str__(self):
        return f'{self.partido} · {self.arbitro} ({self.get_rol_display()})'


class Inscripcion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('ANULADA', 'Anulada'),
    ]

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
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='PENDIENTE'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'inscripciones'
        ordering = ['-fecha_registro', '-id']

    def __str__(self):
        return f'{self.deportista or self.equipo} · {self.campeonato}'

    def clean(self):
        if not self.deportista_id and not self.equipo_id:
            raise ValidationError(
                'La inscripción debe indicar un deportista o un equipo.'
            )
        if self.deportista_id and not self.equipo_id:
            if self.deportista_id and self.deportista.equipo_id:
                self.equipo_id = self.deportista.equipo_id


class Sancion(models.Model):
    TIPOS = [
        ('AMONESTACION', 'Amonestación'),
        ('SUSPENSION', 'Suspensión'),
        ('MULTA', 'Multa'),
        ('EXPULSION', 'Expulsión'),
        ('OTRO', 'Otro'),
    ]
    ESTADOS = [
        ('VIGENTE', 'Vigente'),
        ('CUMPLIDA', 'Cumplida'),
        ('ANULADA', 'Anulada'),
    ]

    deportista = models.ForeignKey(
        Deportista, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    campeonato = models.ForeignKey(
        Campeonato, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    partido = models.ForeignKey(
        Partido, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    tipo = models.CharField(
        max_length=20, choices=TIPOS, default='AMONESTACION'
    )
    descripcion = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='VIGENTE'
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'sanciones'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.get_tipo_display()} · {self.deportista or self.club}'

    def clean(self):
        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_fin < self.fecha_inicio
        ):
            raise ValidationError(
                {'fecha_fin': 'La fecha final no puede ser anterior al inicio.'}
            )


class Pago(models.Model):
    ESTADOS = [
        ('PAGADO', 'Pagado'),
        ('PENDIENTE', 'Pendiente'),
        ('ANULADO', 'Anulado'),
    ]

    deportista = models.ForeignKey(
        Deportista, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    club = models.ForeignKey(
        Club, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    monto = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    fecha = models.DateTimeField(null=True, blank=True)
    tipo = models.CharField(max_length=100, null=True, blank=True)
    comprobante = models.CharField(max_length=50, blank=True)
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='PAGADO'
    )

    class Meta:
        db_table = 'pagos'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return f'{self.tipo or "Pago"} · Bs {self.monto or 0} · {self.fecha}'


class HistorialOperacion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    modulo = models.CharField(max_length=40, blank=True)
    accion = models.CharField(max_length=40, blank=True)
    operacion = models.TextField(null=True, blank=True)
    fecha = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'historial_operaciones'
        ordering = ['-fecha', '-id']
        verbose_name = 'historial de operación'
        verbose_name_plural = 'historial de operaciones'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.operacion}'
