from datetime import date
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .validadores import (
    validar_ci_boliviana,
    validar_correo,
    validar_direccion,
    validar_fecha_nacimiento,
    validar_fecha_pasada,
    validar_nombre_organizacion,
    validar_nombre_persona,
    validar_telefono_boliviano,
    validar_texto_libre,
)


def _validar_campo(errores, campo, funcion, valor, *args, **kwargs):
    """Aplica un validador y acumula el mensaje sin cortar el resto."""
    if not valor:
        return valor
    try:
        return funcion(valor, *args, **kwargs)
    except ValidationError as error:
        errores[campo] = error.messages
        return valor


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

    def clean(self):
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_organizacion, self.nombre,
            'nombre del club', 2, 150,
        )
        self.presidente = _validar_campo(
            errores, 'presidente', validar_nombre_persona, self.presidente,
            'nombre del presidente',
        )
        self.telefono = _validar_campo(
            errores, 'telefono', validar_telefono_boliviano, self.telefono
        )
        self.email = _validar_campo(
            errores, 'email', validar_correo, self.email
        )
        self.direccion = _validar_campo(
            errores, 'direccion', validar_direccion, self.direccion
        )
        self.nit_personeria = _validar_campo(
            errores, 'nit_personeria', validar_texto_libre,
            self.nit_personeria, 'NIT o personería jurídica', 100,
        )
        self.estado_juridico = _validar_campo(
            errores, 'estado_juridico', validar_texto_libre,
            self.estado_juridico, 'estado jurídico', 100,
        )
        self.observaciones = _validar_campo(
            errores, 'observaciones', validar_texto_libre,
            self.observaciones, 'observaciones', 2000,
        )
        if self.fundacion:
            self.fundacion = _validar_campo(
                errores, 'fundacion', validar_fecha_pasada,
                self.fundacion, 'fecha de fundación',
            )
        if errores:
            raise ValidationError(errores)


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
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_organizacion, self.nombre,
            'nombre de la categoría', 2, 100,
        )
        self.descripcion = _validar_campo(
            errores, 'descripcion', validar_texto_libre,
            self.descripcion, 'descripción de la categoría', 1000,
        )
        if (
            isinstance(self.edad_min, int)
            and isinstance(self.edad_max, int)
            and self.edad_min > self.edad_max
        ):
            errores['edad_max'] = [
                'La edad máxima no puede ser menor que la mínima.'
            ]
        for campo in ('edad_min', 'edad_max'):
            valor = getattr(self, campo)
            if isinstance(valor, int) and valor > 100:
                errores[campo] = ['La edad no puede superar los 100 años.']
        if errores:
            raise ValidationError(errores)


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
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_organizacion, self.nombre,
            'nombre del campeonato', 2, 150,
        )
        self.disciplina = _validar_campo(
            errores, 'disciplina', validar_nombre_organizacion,
            self.disciplina, 'disciplina', 2, 100,
        )
        self.reglamento = _validar_campo(
            errores, 'reglamento', validar_texto_libre, self.reglamento,
            'reglamento', 5000,
        )
        if self.temporada is not None and not (
            isinstance(self.temporada, int)
            and 1900 <= self.temporada <= 2100
        ):
            errores['temporada'] = [
                'La temporada debe estar entre 1900 y 2100.'
            ]
        if (
            isinstance(self.fecha_inicio, date)
            and isinstance(self.fecha_conclusion, date)
            and self.fecha_conclusion < self.fecha_inicio
        ):
            errores['fecha_conclusion'] = [
                'La conclusión no puede ser anterior al inicio.'
            ]
        if errores:
            raise ValidationError(errores)


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

    def clean(self):
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_organizacion, self.nombre,
            'nombre del equipo', 2, 150,
        )
        self.entrenador = _validar_campo(
            errores, 'entrenador', validar_nombre_persona, self.entrenador,
            'nombre del entrenador',
        )
        self.division = _validar_campo(
            errores, 'division', validar_nombre_organizacion, self.division,
            'división', 2, 50,
        )
        if self.temporada is not None and not (
            isinstance(self.temporada, int)
            and 1900 <= self.temporada <= 2100
        ):
            errores['temporada'] = [
                'La temporada debe estar entre 1900 y 2100.'
            ]
        if errores:
            raise ValidationError(errores)


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

    def clean(self):
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_persona, self.nombre, 'nombre'
        )
        self.apellido = _validar_campo(
            errores, 'apellido', validar_nombre_persona, self.apellido,
            'apellido',
        )
        self.ci = _validar_campo(
            errores, 'ci', validar_ci_boliviana, self.ci
        )
        self.telefono = _validar_campo(
            errores, 'telefono', validar_telefono_boliviano, self.telefono
        )
        self.direccion = _validar_campo(
            errores, 'direccion', validar_direccion, self.direccion, 200
        )
        if self.fecha_nacimiento:
            self.fecha_nacimiento = _validar_campo(
                errores, 'fecha_nacimiento', validar_fecha_nacimiento,
                self.fecha_nacimiento,
            )
        if errores:
            raise ValidationError(errores)


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

    def clean(self):
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_persona, self.nombre, 'nombre'
        )
        self.apellido = _validar_campo(
            errores, 'apellido', validar_nombre_persona, self.apellido,
            'apellido',
        )
        self.ci = _validar_campo(
            errores, 'ci', validar_ci_boliviana, self.ci
        )
        self.telefono = _validar_campo(
            errores, 'telefono', validar_telefono_boliviano, self.telefono
        )
        self.correo = _validar_campo(
            errores, 'correo', validar_correo, self.correo
        )
        self.licencia = _validar_campo(
            errores, 'licencia', validar_texto_libre, self.licencia,
            'licencia', 50,
        )
        if self.fecha_nacimiento:
            self.fecha_nacimiento = _validar_campo(
                errores, 'fecha_nacimiento', validar_fecha_nacimiento,
                self.fecha_nacimiento,
            )
        if errores:
            raise ValidationError(errores)

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
        errores = {}
        self.descripcion = _validar_campo(
            errores, 'descripcion', validar_texto_libre, self.descripcion,
            'descripción de la sanción', 2000,
        )
        self.observaciones = _validar_campo(
            errores, 'observaciones', validar_texto_libre, self.observaciones,
            'observaciones', 2000,
        )
        if (
            isinstance(self.fecha_inicio, date)
            and isinstance(self.fecha_fin, date)
            and self.fecha_fin < self.fecha_inicio
        ):
            errores['fecha_fin'] = [
                'La fecha final no puede ser anterior al inicio.'
            ]
        if errores:
            raise ValidationError(errores)


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

    def clean(self):
        errores = {}
        self.tipo = _validar_campo(
            errores, 'tipo', validar_texto_libre, self.tipo,
            'tipo de pago', 100,
        )
        self.comprobante = _validar_campo(
            errores, 'comprobante', validar_texto_libre, self.comprobante,
            'comprobante', 50,
        )
        if self.monto is not None:
            try:
                monto = float(self.monto)
            except (TypeError, ValueError):
                monto = None
            if monto is not None and monto <= 0:
                errores['monto'] = ['El monto debe ser mayor que cero.']
        if errores:
            raise ValidationError(errores)


class Cancha(models.Model):
    """Escenario deportivo oficial: estadio, complejo o cancha auxiliar."""

    TIPOS = [
        ('ESTADIO', 'Estadio'),
        ('COMPLEJO', 'Complejo deportivo'),
        ('SINTETICA', 'Cancha sintética'),
        ('AUXILIAR', 'Cancha auxiliar'),
    ]

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=20, choices=TIPOS, default='ESTADIO')
    descripcion = models.CharField(
        max_length=200, blank=True,
        help_text='Capacidad, superficie o uso principal del escenario.',
    )
    direccion = models.CharField(max_length=220, blank=True)
    ciudad = models.CharField(max_length=100, blank=True, default='Oruro')
    latitud = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Latitud en grados decimales. Ej. -17.964000',
    )
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
        help_text='Longitud en grados decimales. Ej. -67.106000',
    )
    imagen = models.ImageField(
        upload_to='canchas/', null=True, blank=True,
        help_text='Imagen del escenario (JPG, PNG o WebP).',
    )
    imagen_url = models.URLField(
        max_length=400, blank=True,
        help_text='Alternativa: enlace público a la imagen.',
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(
        default=0, help_text='Orden de aparición en el portal público.',
    )
    creada = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = 'canchas'
        ordering = ['orden', 'nombre']
        verbose_name = 'cancha'
        verbose_name_plural = 'canchas'

    def __str__(self):
        return self.nombre

    @property
    def imagen_mostrar(self):
        """Imagen cargada o, en su defecto, el enlace externo."""
        if self.imagen:
            return self.imagen.url
        return self.imagen_url

    @property
    def mapa_url(self):
        """Enlace a Google Maps con coordenadas o, si faltan, la dirección."""
        if self.latitud is not None and self.longitud is not None:
            return (
                'https://www.google.com/maps/search/?api=1&query='
                f'{self.latitud},{self.longitud}'
            )
        destino = ', '.join(
            parte for parte in [self.nombre, self.direccion, self.ciudad] if parte
        )
        if not destino:
            return ''
        return (
            'https://www.google.com/maps/search/?api=1&query='
            + quote(destino)
        )

    def clean(self):
        errores = {}
        self.nombre = _validar_campo(
            errores, 'nombre', validar_nombre_organizacion, self.nombre,
            'nombre del escenario', 2, 150,
        )
        self.direccion = _validar_campo(
            errores, 'direccion', validar_direccion, self.direccion
        )
        self.ciudad = _validar_campo(
            errores, 'ciudad', validar_nombre_organizacion, self.ciudad,
            'ciudad', 2, 100,
        )
        self.descripcion = _validar_campo(
            errores, 'descripcion', validar_texto_libre, self.descripcion,
            'descripción del escenario', 200,
        )
        if (self.latitud is None) != (self.longitud is None):
            errores['latitud'] = [
                'Registre la latitud y la longitud juntas, o deje ambas vacías.'
            ]
        try:
            latitud = float(self.latitud)
        except (TypeError, ValueError):
            latitud = None
        try:
            longitud = float(self.longitud)
        except (TypeError, ValueError):
            longitud = None
        if latitud is not None and not (-90 <= latitud <= 90):
            errores['latitud'] = ['La latitud debe estar entre -90 y 90.']
        if longitud is not None and not (-180 <= longitud <= 180):
            errores['longitud'] = ['La longitud debe estar entre -180 y 180.']
        if errores:
            raise ValidationError(errores)


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


class RegistroAcceso(models.Model):
    """Trazabilidad de sesiones: ingreso, salida e intentos fallidos.

    No se almacenan contraseñas ni tokens. `username` conserva el nombre
    intentado aunque la cuenta no exista; `usuario` solo se enlaza cuando la
    autenticación fue válida (o al cerrar una sesión existente).
    """

    EVENTOS = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGIN_FALLIDO', 'Intento fallido'),
        ('LOGOUT', 'Cierre de sesión'),
        ('BLOQUEO', 'Bloqueo por intentos'),
    ]

    evento = models.CharField(max_length=20, choices=EVENTOS, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='accesos',
    )
    username = models.CharField(max_length=150, blank=True)
    rol = models.CharField(max_length=24, blank=True)
    ip = models.CharField(max_length=64, blank=True)
    ip_proxy = models.CharField(max_length=255, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    detalle = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'registros_acceso'
        ordering = ['-fecha', '-id']
        verbose_name = 'registro de acceso'
        verbose_name_plural = 'registros de acceso'
        indexes = [
            models.Index(fields=['evento', 'fecha'], name='acceso_evento_fecha_idx'),
            models.Index(fields=['username', 'fecha'], name='acceso_usuario_fecha_idx'),
        ]

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.get_evento_display()} · {self.username or "—"}'

    @property
    def es_fallido(self):
        return self.evento in {'LOGIN_FALLIDO', 'BLOQUEO'}
