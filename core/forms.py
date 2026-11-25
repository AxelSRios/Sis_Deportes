"""Formularios del sistema A.F.O. · Oruro.

Todos los formularios validan contra la base y comparten el mismo estilo
visual. Las reglas de negocio (duplicados, coherencia entre club/equipo,
marcadores, inscripciones) viven aquí para que las vistas queden delgadas.
"""
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    Arbitro,
    AsignacionArbitro,
    Campeonato,
    Cancha,
    Categoria,
    Club,
    Deportista,
    Equipo,
    Inscripcion,
    Pago,
    Partido,
    Sancion,
)
from .validadores import (
    validar_ci_unica,
    validar_correo_unico,
    validar_direccion,
    validar_fecha_nacimiento,
    validar_fecha_pasada,
    validar_nombre_organizacion,
    validar_nombre_persona,
    validar_telefono_boliviano,
    validar_texto_libre,
    validar_usuario,
)

# Grupos institucionales que otorgan rol. Deben coincidir con ROLE_GROUP_ALIASES
# de core/views.py para que el login resuelva el rol correctamente.
GRUPOS_ROL = [
    'Administrador General',
    'Dirigente de Club Afiliado',
    'Comisión Técnica / Árbitros',
    'Tesorero / Finanzas Institucionales',
]


class EstiloFormMixin:
    """Aplica las clases del sistema de diseño a todos los widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault(
                    'class',
                    'h-4 w-4 rounded border-outline-variant text-primary '
                    'focus:ring-secondary/40',
                )
                continue
            base = (
                'w-full rounded-xl border border-outline-variant '
                'bg-surface-container-lowest px-3.5 text-sm text-on-surface '
                'outline-none transition focus:border-secondary/70 '
                'focus:ring-2 focus:ring-secondary/20'
            )
            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', base + ' py-2.5 min-h-[96px]')
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs.setdefault('class', base + ' h-11')
            if isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', base + ' h-11 pr-8')


class FechaFormMixin:
    """Inputs nativos de fecha y hora (compatibles con móviles)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.DateTimeInput):
                widget.input_type = 'datetime-local'
                widget.format = '%Y-%m-%dT%H:%M'
            elif isinstance(widget, forms.DateInput):
                widget.input_type = 'date'
                widget.format = '%Y-%m-%d'

    def clean_fecha(self):
        return self.cleaned_data.get('fecha')


class ClubForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Club
        fields = [
            'nombre', 'logo_url', 'fundacion', 'presidente', 'telefono',
            'email', 'direccion', 'categoria_ingreso', 'nit_personeria',
            'estado_juridico', 'estado', 'observaciones',
        ]
        widgets = {
            'fundacion': forms.DateInput(format='%Y-%m-%d'),
            'direccion': forms.Textarea(attrs={'rows': 2}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def clean_nombre(self):
        nombre = validar_nombre_organizacion(
            self.cleaned_data.get('nombre'), 'nombre del club', maximo=150
        )
        repetido = Club.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError('Ya existe un club con ese nombre.')
        return nombre

    def clean_presidente(self):
        valor = self.cleaned_data.get('presidente')
        if not valor:
            return valor
        return validar_nombre_persona(valor, 'nombre del presidente')

    def clean_telefono(self):
        return validar_telefono_boliviano(self.cleaned_data.get('telefono'))

    def clean_email(self):
        return validar_correo_unico(
            self.cleaned_data.get('email'), Club, self.instance.pk
        )

    def clean_direccion(self):
        return validar_direccion(self.cleaned_data.get('direccion'))

    def clean_nit_personeria(self):
        return validar_texto_libre(
            self.cleaned_data.get('nit_personeria'),
            'NIT o personería jurídica',
            maximo=100,
        )

    def clean_estado_juridico(self):
        return validar_texto_libre(
            self.cleaned_data.get('estado_juridico'),
            'estado jurídico',
            maximo=100,
        )

    def clean_fundacion(self):
        valor = self.cleaned_data.get('fundacion')
        if not valor:
            return valor
        return validar_fecha_pasada(valor, 'fecha de fundación')

    def clean_observaciones(self):
        return validar_texto_libre(
            self.cleaned_data.get('observaciones'),
            'observaciones',
            maximo=2000,
        )


class CanchaForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Cancha
        fields = [
            'nombre', 'tipo', 'descripcion', 'direccion', 'ciudad',
            'latitud', 'longitud', 'imagen', 'imagen_url', 'activa', 'orden',
        ]
        widgets = {
            'descripcion': forms.TextInput(
                attrs={'placeholder': 'Ej. Capacidad 33.000 · Césped natural'}
            ),
            'direccion': forms.TextInput(
                attrs={'placeholder': 'Ej. Av. Del Ejército, zona norte'}
            ),
            'ciudad': forms.TextInput(attrs={'placeholder': 'Oruro'}),
            'latitud': forms.NumberInput(
                attrs={'step': '0.000001', 'placeholder': '-17.964000'}
            ),
            'longitud': forms.NumberInput(
                attrs={'step': '0.000001', 'placeholder': '-67.106000'}
            ),
            'imagen_url': forms.URLInput(
                attrs={'placeholder': 'https://…/imagen.jpg'}
            ),
            'orden': forms.NumberInput(attrs={'min': 0, 'step': 1}),
        }

    def clean_nombre(self):
        nombre = validar_nombre_organizacion(
            self.cleaned_data.get('nombre'), 'nombre del escenario', maximo=150
        )
        repetido = Cancha.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError('Ya existe un escenario con ese nombre.')
        return nombre

    def clean_direccion(self):
        return validar_direccion(self.cleaned_data.get('direccion'))

    def clean_ciudad(self):
        valor = self.cleaned_data.get('ciudad')
        if not valor:
            return valor
        return validar_nombre_organizacion(valor, 'ciudad', maximo=100)

    def clean_descripcion(self):
        return validar_texto_libre(
            self.cleaned_data.get('descripcion'),
            'descripción del escenario',
            maximo=200,
        )

    def clean(self):
        datos = super().clean()
        latitud = datos.get('latitud')
        longitud = datos.get('longitud')
        if (latitud is None) != (longitud is None):
            raise ValidationError(
                'Registre la latitud y la longitud juntas, o deje ambas vacías.'
            )
        if latitud is not None and not (-90 <= float(latitud) <= 90):
            self.add_error('latitud', 'La latitud debe estar entre -90 y 90.')
        if longitud is not None and not (-180 <= float(longitud) <= 180):
            self.add_error('longitud', 'La longitud debe estar entre -180 y 180.')
        return datos


class CategoriaForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'edad_min', 'edad_max', 'descripcion']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 2})}

    def clean_nombre(self):
        nombre = validar_nombre_organizacion(
            self.cleaned_data.get('nombre'), 'nombre de la categoría', maximo=100
        )
        repetido = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError('Ya existe una categoría con ese nombre.')
        return nombre

    def clean_descripcion(self):
        return validar_texto_libre(
            self.cleaned_data.get('descripcion'),
            'descripción de la categoría',
            maximo=1000,
        )

    def clean(self):
        datos = super().clean()
        edad_min = datos.get('edad_min')
        edad_max = datos.get('edad_max')
        if edad_min is not None and edad_max is not None and edad_min > edad_max:
            self.add_error(
                'edad_max',
                'La edad máxima no puede ser menor que la mínima.',
            )
        for campo in ('edad_min', 'edad_max'):
            valor = datos.get(campo)
            if valor is not None and valor > 100:
                self.add_error(campo, 'La edad no puede superar los 100 años.')
        return datos


class EquipoForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Equipo
        fields = [
            'nombre', 'club', 'categoria', 'division', 'temporada',
            'entrenador', 'estado',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['club'].required = True
        self.fields['categoria'].required = True
        self.fields['nombre'].required = True
        self.fields['temporada'].help_text = 'Año de la temporada (ej. 2026).'

    def clean_nombre(self):
        return validar_nombre_organizacion(
            self.cleaned_data.get('nombre'), 'nombre del equipo', maximo=150
        )

    def clean_entrenador(self):
        valor = self.cleaned_data.get('entrenador')
        if not valor:
            return valor
        return validar_nombre_persona(valor, 'nombre del entrenador')

    def clean_division(self):
        valor = self.cleaned_data.get('division')
        if not valor:
            return valor
        return validar_nombre_organizacion(valor, 'división', maximo=50)

    def clean_temporada(self):
        valor = self.cleaned_data.get('temporada')
        if valor is not None and not (1900 <= valor <= 2100):
            raise ValidationError(
                'La temporada debe estar entre 1900 y 2100.'
            )
        return valor

    def clean(self):
        datos = super().clean()
        club = datos.get('club')
        nombre = (datos.get('nombre') or '').strip()
        if club and nombre:
            repetido = Equipo.objects.filter(
                club=club, nombre__iexact=nombre
            )
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise ValidationError(
                    'Ese club ya tiene un equipo con el mismo nombre.'
                )
        return datos


class DeportistaForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Deportista
        fields = [
            'nombre', 'apellido', 'ci', 'fecha_nacimiento', 'genero',
            'foto_url', 'telefono', 'direccion', 'club', 'equipo',
            'categoria', 'estado',
        ]
        widgets = {'fecha_nacimiento': forms.DateInput(format='%Y-%m-%d')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_nacimiento'].required = True

    def clean_nombre(self):
        return validar_nombre_persona(
            self.cleaned_data.get('nombre'), 'nombre'
        )

    def clean_apellido(self):
        return validar_nombre_persona(
            self.cleaned_data.get('apellido'), 'apellido'
        )

    def clean_ci(self):
        valor = self.cleaned_data.get('ci')
        if not valor:
            return valor
        return validar_ci_unica(valor, Deportista, self.instance.pk)

    def clean_telefono(self):
        return validar_telefono_boliviano(self.cleaned_data.get('telefono'))

    def clean_direccion(self):
        return validar_direccion(
            self.cleaned_data.get('direccion'), maximo=200
        )

    def clean_fecha_nacimiento(self):
        valor = self.cleaned_data.get('fecha_nacimiento')
        if not valor:
            raise ValidationError('La fecha de nacimiento es obligatoria.')
        return validar_fecha_nacimiento(valor)

    def clean(self):
        datos = super().clean()
        nombre = (datos.get('nombre') or '').strip()
        apellido = (datos.get('apellido') or '').strip()
        nacimiento = datos.get('fecha_nacimiento')
        club = datos.get('club')
        equipo = datos.get('equipo')

        if equipo and club and equipo.club_id and equipo.club_id != club.pk:
            self.add_error(
                'equipo',
                'El equipo seleccionado pertenece a otro club.',
            )
        if equipo and not club:
            datos['club'] = equipo.club

        if nombre and apellido and nacimiento:
            repetido = Deportista.objects.filter(
                nombre__iexact=nombre,
                apellido__iexact=apellido,
                fecha_nacimiento=nacimiento,
            )
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise ValidationError(
                    'Ya existe un deportista con el mismo nombre y fecha de '
                    'nacimiento. Revise el padrón antes de duplicarlo.'
                )
        return datos


class CampeonatoForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Campeonato
        fields = [
            'nombre', 'categoria', 'disciplina', 'temporada', 'modalidad',
            'fecha_inicio', 'fecha_conclusion', 'estado', 'reglamento',
        ]
        widgets = {
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d'),
            'fecha_conclusion': forms.DateInput(format='%Y-%m-%d'),
            'reglamento': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].required = True
        self.fields['categoria'].required = True
        self.fields['disciplina'].required = True
        if not self.instance.pk and not self.initial.get('temporada'):
            self.initial['temporada'] = timezone.localdate().year

    def clean_nombre(self):
        return validar_nombre_organizacion(
            self.cleaned_data.get('nombre'), 'nombre del campeonato', maximo=150
        )

    def clean_disciplina(self):
        return validar_nombre_organizacion(
            self.cleaned_data.get('disciplina'), 'disciplina', maximo=100
        )

    def clean_temporada(self):
        valor = self.cleaned_data.get('temporada')
        if valor is not None and not (1900 <= valor <= 2100):
            raise ValidationError(
                'La temporada debe estar entre 1900 y 2100.'
            )
        return valor

    def clean_reglamento(self):
        return validar_texto_libre(
            self.cleaned_data.get('reglamento'), 'reglamento', maximo=5000
        )


class PartidoForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Partido
        fields = [
            'campeonato', 'equipo_local', 'equipo_visitante', 'fecha',
            'escenario', 'estado', 'goles_local', 'goles_visitante',
        ]
        widgets = {
            'fecha': forms.DateTimeInput(format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campeonato'].required = True
        self.fields['equipo_local'].required = True
        self.fields['equipo_visitante'].required = True
        self.fields['fecha'].required = True
        self.fields['escenario'].required = True

    def clean_escenario(self):
        return validar_nombre_organizacion(
            self.cleaned_data.get('escenario'), 'escenario', maximo=150
        )

    def clean_goles_local(self):
        valor = self.cleaned_data.get('goles_local')
        if valor is not None and valor > 99:
            raise ValidationError('Los goles no pueden superar 99.')
        return valor

    def clean_goles_visitante(self):
        valor = self.cleaned_data.get('goles_visitante')
        if valor is not None and valor > 99:
            raise ValidationError('Los goles no pueden superar 99.')
        return valor

    def clean(self):
        datos = super().clean()
        local = datos.get('equipo_local')
        visitante = datos.get('equipo_visitante')
        gl = datos.get('goles_local')
        gv = datos.get('goles_visitante')
        campeonato = datos.get('campeonato')
        fecha = datos.get('fecha')

        if local and visitante and local.pk == visitante.pk:
            self.add_error(
                'equipo_visitante',
                'El equipo visitante debe ser distinto del local.',
            )

        if (gl is None) != (gv is None):
            raise ValidationError(
                'Registre los goles de ambos equipos o deje los dos vacíos.'
            )

        if local and visitante and campeonato and fecha:
            choque = Partido.objects.filter(
                campeonato=campeonato,
                fecha=fecha,
            ).filter(
                models_q_equipos(local.pk, visitante.pk)
            )
            if self.instance.pk:
                choque = choque.exclude(pk=self.instance.pk)
            if choque.exists():
                raise ValidationError(
                    'Ya existe un partido de estos equipos en ese campeonato '
                    'y a esa misma hora.'
                )
        return datos


def models_q_equipos(local_id, visitante_id):
    """Q de choque entre los mismos equipos (en cualquier condición)."""
    from django.db.models import Q

    return (
        (Q(equipo_local_id=local_id) & Q(equipo_visitante_id=visitante_id))
        | (Q(equipo_local_id=visitante_id) & Q(equipo_visitante_id=local_id))
    )


class InscripcionForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = [
            'campeonato', 'equipo', 'deportista', 'estado', 'observaciones',
        ]
        widgets = {'observaciones': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campeonato'].required = True

    def clean_observaciones(self):
        return validar_texto_libre(
            self.cleaned_data.get('observaciones'),
            'observaciones',
            maximo=2000,
        )

    def clean(self):
        datos = super().clean()
        campeonato = datos.get('campeonato')
        equipo = datos.get('equipo')
        deportista = datos.get('deportista')

        if not equipo and not deportista:
            raise ValidationError(
                'Seleccione un equipo o un deportista para inscribir.'
            )
        if deportista and not equipo and deportista.equipo_id:
            datos['equipo'] = deportista.equipo

        if campeonato:
            repetida = Inscripcion.objects.filter(campeonato=campeonato)
            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)
            if deportista and repetida.filter(deportista=deportista).exists():
                self.add_error(
                    'deportista',
                    'Ese deportista ya está inscrito en este campeonato.',
                )
            if equipo and not deportista and repetida.filter(
                equipo=equipo, deportista__isnull=True
            ).exists():
                self.add_error(
                    'equipo',
                    'Ese equipo ya está inscrito en este campeonato.',
                )
        return datos


class ArbitroForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Arbitro
        fields = [
            'nombre', 'apellido', 'ci', 'fecha_nacimiento', 'telefono',
            'correo', 'licencia', 'categoria', 'especialidad',
            'disponible', 'estado',
        ]
        widgets = {'fecha_nacimiento': forms.DateInput(format='%Y-%m-%d')}

    def clean_nombre(self):
        return validar_nombre_persona(
            self.cleaned_data.get('nombre'), 'nombre'
        )

    def clean_apellido(self):
        return validar_nombre_persona(
            self.cleaned_data.get('apellido'), 'apellido'
        )

    def clean_ci(self):
        valor = self.cleaned_data.get('ci')
        if not valor:
            return valor
        return validar_ci_unica(valor, Arbitro, self.instance.pk)

    def clean_telefono(self):
        return validar_telefono_boliviano(self.cleaned_data.get('telefono'))

    def clean_correo(self):
        return validar_correo_unico(
            self.cleaned_data.get('correo'),
            Arbitro,
            self.instance.pk,
            campo='correo',
        )

    def clean_fecha_nacimiento(self):
        valor = self.cleaned_data.get('fecha_nacimiento')
        if not valor:
            return valor
        return validar_fecha_nacimiento(valor)

    def clean_licencia(self):
        return validar_texto_libre(
            self.cleaned_data.get('licencia'), 'licencia', maximo=50
        )

    def clean(self):
        datos = super().clean()
        nombre = (datos.get('nombre') or '').strip()
        apellido = (datos.get('apellido') or '').strip()
        nacimiento = datos.get('fecha_nacimiento')
        if nombre and apellido and nacimiento:
            repetido = Arbitro.objects.filter(
                nombre__iexact=nombre,
                apellido__iexact=apellido,
                fecha_nacimiento=nacimiento,
            )
            if self.instance.pk:
                repetido = repetido.exclude(pk=self.instance.pk)
            if repetido.exists():
                raise ValidationError(
                    'Ya existe un árbitro con el mismo nombre y fecha de '
                    'nacimiento.'
                )
        return datos


class AsignacionForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = AsignacionArbitro
        fields = ['partido', 'arbitro', 'rol']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['partido'].required = True
        self.fields['arbitro'].required = True
        self.fields['partido'].queryset = Partido.objects.select_related(
            'equipo_local', 'equipo_visitante'
        ).order_by('-fecha', '-id')
        self.fields['arbitro'].queryset = Arbitro.objects.filter(
            estado='ACTIVO'
        ).order_by('apellido', 'nombre')

    def clean(self):
        datos = super().clean()
        partido = datos.get('partido')
        arbitro = datos.get('arbitro')
        rol = datos.get('rol')

        if arbitro and not arbitro.disponible:
            self.add_error(
                'arbitro', 'El árbitro está marcado como no disponible.'
            )

        if partido and arbitro:
            repetida = AsignacionArbitro.objects.filter(
                partido=partido, arbitro=arbitro
            )
            if self.instance.pk:
                repetida = repetida.exclude(pk=self.instance.pk)
            if repetida.exists():
                self.add_error(
                    'arbitro', 'Ese árbitro ya está asignado a este partido.'
                )

        if partido and rol:
            ocupado = AsignacionArbitro.objects.filter(partido=partido, rol=rol)
            if self.instance.pk:
                ocupado = ocupado.exclude(pk=self.instance.pk)
            if ocupado.exists():
                self.add_error(
                    'rol', 'Ese rol arbitral ya está cubierto en este partido.'
                )
        return datos


class SancionForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Sancion
        fields = [
            'tipo', 'deportista', 'club', 'campeonato', 'partido',
            'fecha', 'fecha_inicio', 'fecha_fin', 'descripcion',
            'estado', 'observaciones',
        ]
        widgets = {
            'fecha': forms.DateTimeInput(format='%Y-%m-%dT%H:%M'),
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 2}),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descripcion'].required = True
        if not self.instance.pk and not self.initial.get('fecha'):
            self.initial['fecha'] = timezone.localtime().strftime(
                '%Y-%m-%dT%H:%M'
            )

    def clean_descripcion(self):
        return validar_texto_libre(
            self.cleaned_data.get('descripcion'),
            'descripción de la sanción',
            maximo=2000,
            obligatorio=True,
        )

    def clean_observaciones(self):
        return validar_texto_libre(
            self.cleaned_data.get('observaciones'),
            'observaciones',
            maximo=2000,
        )

    def clean(self):
        datos = super().clean()
        if not datos.get('deportista') and not datos.get('club'):
            raise ValidationError(
                'Indique el deportista o el club sancionado.'
            )
        return datos


class PagoForm(EstiloFormMixin, FechaFormMixin, forms.ModelForm):
    class Meta:
        model = Pago
        fields = [
            'tipo', 'monto', 'fecha', 'club', 'deportista',
            'comprobante', 'estado',
        ]
        widgets = {'fecha': forms.DateTimeInput(format='%Y-%m-%dT%H:%M')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo'].required = True
        self.fields['monto'].required = True
        if not self.instance.pk and not self.initial.get('fecha'):
            self.initial['fecha'] = timezone.localtime().strftime(
                '%Y-%m-%dT%H:%M'
            )

    def clean_tipo(self):
        return validar_texto_libre(
            self.cleaned_data.get('tipo'),
            'tipo de pago',
            maximo=100,
            obligatorio=True,
        )

    def clean_comprobante(self):
        return validar_texto_libre(
            self.cleaned_data.get('comprobante'),
            'comprobante',
            maximo=50,
        )

    def clean(self):
        datos = super().clean()
        monto = datos.get('monto')
        if monto is not None and monto <= 0:
            self.add_error('monto', 'El monto debe ser mayor que cero.')
        return datos


class UsuarioForm(EstiloFormMixin, forms.ModelForm):
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=GRUPOS_ROL).order_by('name'),
        label='Rol institucional',
        empty_label='Seleccione un rol',
    )
    password1 = forms.CharField(
        label='Contraseña', widget=forms.PasswordInput, min_length=8,
        help_text='Mínimo 8 caracteres. No use datos personales evidentes.',
    )
    password2 = forms.CharField(
        label='Repetir contraseña', widget=forms.PasswordInput,
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'is_active',
        ]
        labels = {
            'username': 'Usuario de acceso',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo institucional',
            'is_active': 'Cuenta habilitada',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_username(self):
        username = validar_usuario(self.cleaned_data.get('username'))
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Ese usuario ya existe.')
        return username

    def clean_first_name(self):
        return validar_nombre_persona(
            self.cleaned_data.get('first_name'), 'nombre'
        )

    def clean_last_name(self):
        return validar_nombre_persona(
            self.cleaned_data.get('last_name'), 'apellido'
        )

    def clean_email(self):
        return validar_correo_unico(self.cleaned_data.get('email'), User)

    def clean(self):
        datos = super().clean()
        p1 = datos.get('password1')
        p2 = datos.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        if p1:
            candidato = User(
                username=datos.get('username', ''),
                first_name=datos.get('first_name', ''),
                last_name=datos.get('last_name', ''),
                email=datos.get('email', ''),
            )
            try:
                password_validation.validate_password(p1, candidato)
            except ValidationError as error:
                self.add_error('password1', error)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data['password1'])
        if commit:
            usuario.save()
            usuario.groups.set([self.cleaned_data['grupo']])
        return usuario


class UsuarioEditarForm(EstiloFormMixin, forms.ModelForm):
    grupo = forms.ModelChoiceField(
        queryset=Group.objects.filter(name__in=GRUPOS_ROL).order_by('name'),
        label='Rol institucional',
        empty_label='Seleccione un rol',
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'is_active',
        ]
        labels = {
            'username': 'Usuario de acceso',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo institucional',
            'is_active': 'Cuenta habilitada',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = False
        if self.instance.pk:
            grupo = self.instance.groups.first()
            if grupo:
                self.fields['grupo'].initial = grupo

    def clean_username(self):
        username = validar_usuario(self.cleaned_data.get('username'))
        repetido = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            repetido = repetido.exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError('Ese usuario ya existe.')
        return username

    def clean_first_name(self):
        return validar_nombre_persona(
            self.cleaned_data.get('first_name'), 'nombre'
        )

    def clean_last_name(self):
        return validar_nombre_persona(
            self.cleaned_data.get('last_name'), 'apellido'
        )

    def clean_email(self):
        return validar_correo_unico(
            self.cleaned_data.get('email'), User, self.instance.pk
        )

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set([self.cleaned_data['grupo']])
        return usuario


class PerfilForm(EstiloFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo institucional',
        }

    def clean_first_name(self):
        valor = self.cleaned_data.get('first_name')
        if not valor:
            return valor
        return validar_nombre_persona(valor, 'nombre')

    def clean_last_name(self):
        valor = self.cleaned_data.get('last_name')
        if not valor:
            return valor
        return validar_nombre_persona(valor, 'apellido')

    def clean_email(self):
        return validar_correo_unico(
            self.cleaned_data.get('email'), User, self.instance.pk
        )
