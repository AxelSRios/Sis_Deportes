"""Validadores de datos para el sistema A.F.O. · Oruro.

Centraliza las reglas de formato usadas en Bolivia para que formularios y
modelos validen exactamente igual:

* Nombres y apellidos de personas (letras, tildes, ñ, espacios, apóstrofos
  y guiones; nunca dígitos).
* Cédula de identidad (6 a 8 dígitos, complemento opcional y extensión
  departamental LP, OR, CB, SC, PT, CH, TJ, BN o PD).
* Teléfonos bolivianos (8 dígitos nacionales y prefijo +591).
* Fechas de nacimiento (válidas, no futuras y con edad razonable).
* Correos electrónicos (formato y longitud).
* Direcciones y textos libres (sin controles ni intentos de inyección de
  marcado).

Importante: validar el *formato* de una cédula no demuestra que exista ni
que pertenezca a la persona. La autenticidad solo puede confirmarla el
registro oficial (SEGIP) o la propia institución con el documento físico.
"""
import re
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone

# Extensiones departamentales reconocidas en Bolivia.
DEPARTAMENTOS_CI = {
    'LP': 'La Paz',
    'OR': 'Oruro',
    'CB': 'Cochabamba',
    'SC': 'Santa Cruz',
    'PT': 'Potosí',
    'CH': 'Chuquisaca',
    'TJ': 'Tarija',
    'BN': 'Beni',
    'PD': 'Pando',
}

LETRAS = 'A-Za-zÁÉÍÓÚÜÑáéíóúüñ'

_RE_NOMBRE_PERSONA = re.compile(
    rf"^[{LETRAS}]+(?:[ '\-.][{LETRAS}]+)*$"
)
_RE_NOMBRE_ORGANIZACION = re.compile(
    rf"^[0-9{LETRAS}º°]+(?:[ .,'&()/°º#\-][0-9{LETRAS}º°]+)*$"
)
_RE_USUARIO = re.compile(r'^[A-Za-z0-9._-]{4,30}$')
_RE_CI_CON_SEPARADOR = re.compile(r'^(\d{6,8})(?:-([A-Z0-9]{1,2}))?$')
_RE_CI_SIN_SEPARADOR = re.compile(r'^(\d{6,8})([A-Z0-9]{1,2})$')
_RE_COMPLEMENTO = re.compile(r'^(?:[0-9][A-Z0-9]?|[A-Z])$')
_RE_EXTENSION = re.compile(
    r'[-\s](LP|OR|CB|SC|PT|CH|TJ|BN|PD)$', re.IGNORECASE
)
_RE_PELIGRO_TEXTO = re.compile(
    r'(<\s*/?\s*script|javascript\s*:|on(?:error|load|click|mouseover)\s*=|'
    r'<\s*iframe|<\s*object|<\s*embed)',
    re.IGNORECASE,
)
_CARACTERES_PELIGROSOS = set('<>{}[]\\|\x00')


def _texto(valor):
    return str(valor or '').strip()


def _compactar_espacios(valor):
    return re.sub(r'\s+', ' ', _texto(valor))


def _error(mensaje):
    raise ValidationError(mensaje)


# ---------------------------------------------------------------------------
# Nombres
# ---------------------------------------------------------------------------


def validar_nombre_persona(valor, campo='nombre', minimo=2, maximo=60):
    """Valida nombres y apellidos: letras, tildes, ñ, espacios y separadores.

    Rechaza dígitos, símbolos de marcado y cadenas formadas solo por signos.
    Devuelve el texto normalizado (sin espacios repetidos en los extremos).
    """
    texto = _compactar_espacios(valor)
    if not texto:
        _error(f'El {campo} es obligatorio.')
    if len(texto) < minimo:
        _error(f'El {campo} debe tener al menos {minimo} letras.')
    if len(texto) > maximo:
        _error(f'El {campo} no puede superar los {maximo} caracteres.')
    if any(caracter.isdigit() for caracter in texto):
        _error(f'El {campo} no puede contener números.')
    if any(caracter in _CARACTERES_PELIGROSOS for caracter in texto):
        _error(f'El {campo} contiene caracteres no permitidos.')
    if not _RE_NOMBRE_PERSONA.match(texto):
        _error(
            f'El {campo} solo admite letras, tildes, ñ, espacios, '
            'apóstrofos y guiones.'
        )
    if not re.search(rf'[{LETRAS}]', texto):
        _error(f'El {campo} debe contener letras.')
    return texto


def validar_nombre_organizacion(valor, campo='nombre', minimo=2, maximo=150):
    """Valida nombres de clubes, equipos, canchas, categorías y torneos."""
    texto = _compactar_espacios(valor)
    if not texto:
        _error(f'El {campo} es obligatorio.')
    if len(texto) < minimo:
        _error(f'El {campo} debe tener al menos {minimo} caracteres.')
    if len(texto) > maximo:
        _error(f'El {campo} no puede superar los {maximo} caracteres.')
    if any(caracter in _CARACTERES_PELIGROSOS for caracter in texto):
        _error(f'El {campo} contiene caracteres no permitidos.')
    if _RE_PELIGRO_TEXTO.search(texto):
        _error(f'El {campo} contiene contenido no permitido.')
    if not _RE_NOMBRE_ORGANIZACION.match(texto):
        _error(
            f'El {campo} solo admite letras, números, espacios y '
            'signos como . , - \' & ( ) / ° º #.'
        )
    if not re.search(rf'[{LETRAS}0-9]', texto):
        _error(f'El {campo} debe contener letras o números.')
    return texto


# ---------------------------------------------------------------------------
# Cédula de identidad boliviana
# ---------------------------------------------------------------------------


def _partes_ci(valor):
    texto = re.sub(r'\s+', ' ', _texto(valor)).upper()
    if not texto:
        _error('La cédula de identidad es obligatoria.')
    if any(caracter in _CARACTERES_PELIGROSOS for caracter in texto):
        _error('La cédula de identidad contiene caracteres no permitidos.')

    extension = ''
    coincidencia = _RE_EXTENSION.search(texto)
    if coincidencia:
        extension = coincidencia.group(1).upper()
        texto = texto[:coincidencia.start()].strip()
    else:
        # Acepta también el código pegado al número: 1000001OR.
        pegado = re.fullmatch(r'(\d{6,8})([A-Z]{2})', texto)
        if pegado and pegado.group(2) in DEPARTAMENTOS_CI:
            texto = pegado.group(1)
            extension = pegado.group(2)

    coincidencia = _RE_CI_CON_SEPARADOR.match(texto)
    if coincidencia:
        numero = coincidencia.group(1)
        complemento = (coincidencia.group(2) or '').upper()
    else:
        # Sin separador el complemento debe contener al menos una letra para
        # no confundir un noveno dígito con un complemento (123456789).
        coincidencia = _RE_CI_SIN_SEPARADOR.match(texto)
        if not coincidencia:
            _error(
                'Cédula de identidad inválida. Use de 6 a 8 dígitos y, si '
                'corresponde, complemento y extensión (ej. 1000001-1K LP).'
            )
        numero = coincidencia.group(1)
        complemento = coincidencia.group(2).upper()
        if not re.search(r'[A-Z]', complemento):
            _error(
                'Cédula de identidad inválida: el número tiene demasiados '
                'dígitos.'
            )

    if complemento and not _RE_COMPLEMENTO.match(complemento):
        _error(
            'El complemento de la cédula no es válido. Use una letra o un '
            'dígito seguido de letra (ej. 1K, A).'
        )
    if int(numero) == 0:
        _error('La cédula de identidad no puede ser cero.')
    return numero, complemento, extension


def validar_ci_boliviana(valor):
    """Valida una CI boliviana y devuelve su forma normalizada.

    Formatos aceptados: ``1000001``, ``1000001-LP``, ``1000001 LP``,
    ``1000001-1K``, ``1000001-1K OR``. La extensión debe ser una de las
    nueve reconocidas; no se aceptan letras sueltas como departamento.
    """
    numero, complemento, extension = _partes_ci(valor)
    normalizada = numero
    if complemento:
        normalizada += f'-{complemento}'
    if extension:
        normalizada += f'-{extension}'
    return normalizada


def ci_clave(valor):
    """Clave de comparación para detectar duplicados ignorando la extensión.

    ``1000001``, ``1000001-LP`` y ``1000001 OR`` corresponden a la misma
    cédula; la extensión solo indica el departamento de emisión.
    """
    try:
        numero, complemento, _extension = _partes_ci(valor)
    except ValidationError:
        return _compactar_espacios(valor).upper()
    return f'{numero}{complemento}'


def validar_ci_unica(valor, modelo, pk=None, campo='ci'):
    """Valida formato y unicidad de CI dentro de un modelo concreto."""
    normalizada = validar_ci_boliviana(valor)
    clave = ci_clave(normalizada)
    existentes = modelo.objects.exclude(**{f'{campo}__isnull': True})
    existentes = existentes.exclude(**{campo: ''})
    if pk:
        existentes = existentes.exclude(pk=pk)
    for registrada in existentes.values_list(campo, flat=True):
        if ci_clave(registrada) == clave:
            _error('Ya existe un registro con esa cédula de identidad.')
    return normalizada


# ---------------------------------------------------------------------------
# Teléfonos bolivianos
# ---------------------------------------------------------------------------


def validar_telefono_boliviano(valor):
    """Valida un teléfono boliviano y lo devuelve como ``+591XXXXXXXX``.

    Acepta el número con o sin prefijo y con espacios o guiones. Debe tener
    8 dígitos nacionales y comenzar con 2, 3, 4 (fijos), 6 o 7 (móviles).
    """
    texto = _texto(valor)
    if not texto:
        return ''
    if re.search(r'[A-Za-z<>;{}|\\]', texto):
        _error('El teléfono solo puede contener números, espacios, + y guiones.')
    digitos = re.sub(r'\D', '', texto)
    if len(digitos) == 11 and digitos.startswith('591'):
        nacional = digitos[3:]
    elif len(digitos) == 8:
        nacional = digitos
    else:
        _error(
            'El teléfono debe tener 8 dígitos (ej. 71234567) y puede '
            'llevar el prefijo +591.'
        )
    if len(nacional) != 8:
        _error('El teléfono debe tener exactamente 8 dígitos.')
    if nacional[0] not in '23467':
        _error(
            'El teléfono no es válido en Bolivia: debe comenzar con 2, 3, '
            '4, 6 o 7.'
        )
    return f'+591{nacional}'


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------


def calcular_edad(nacimiento, referencia=None):
    referencia = referencia or timezone.localdate()
    return referencia.year - nacimiento.year - (
        (referencia.month, referencia.day) < (nacimiento.month, nacimiento.day)
    )


def validar_fecha_nacimiento(valor, edad_minima=4, edad_maxima=100):
    """Valida una fecha de nacimiento real, pasada y con edad razonable."""
    if not isinstance(valor, date):
        _error('Ingrese una fecha de nacimiento válida.')
    hoy = timezone.localdate()
    if valor > hoy:
        _error('La fecha de nacimiento no puede estar en el futuro.')
    edad = calcular_edad(valor, hoy)
    if edad < edad_minima:
        _error(
            f'La persona debe tener al menos {edad_minima} años para '
            'registrarse.'
        )
    if edad > edad_maxima:
        _error('La fecha de nacimiento no es plausible (más de 100 años).')
    return valor


def validar_fecha_pasada(valor, campo='fecha', permitir_hoy=True):
    """Valida fechas históricas como la fundación de un club."""
    if not isinstance(valor, date):
        _error(f'Ingrese una {campo} válida.')
    hoy = timezone.localdate()
    if valor > hoy and not (permitir_hoy and valor == hoy):
        _error(f'La {campo} no puede estar en el futuro.')
    if valor.year < 1900:
        _error(f'La {campo} no puede ser anterior a 1900.')
    return valor


# ---------------------------------------------------------------------------
# Correos, direcciones y textos
# ---------------------------------------------------------------------------


def validar_correo(valor, maximo=150):
    """Valida el formato de un correo y normaliza el dominio a minúsculas."""
    texto = _texto(valor)
    if not texto:
        return ''
    if len(texto) > maximo:
        _error(f'El correo no puede superar los {maximo} caracteres.')
    if any(caracter in _CARACTERES_PELIGROSOS for caracter in texto):
        _error('El correo contiene caracteres no permitidos.')
    try:
        validate_email(texto)
    except ValidationError:
        _error(
            'Ingrese un correo electrónico válido '
            '(ej. nombre.apellido@dominio.bo).'
        )
    usuario, dominio = texto.rsplit('@', 1)
    if len(usuario) > 64:
        _error('La parte antes de @ no puede superar los 64 caracteres.')
    if len(dominio) > 255:
        _error('El dominio del correo no puede superar los 255 caracteres.')
    return f'{usuario}@{dominio.lower()}'


def validar_correo_unico(valor, modelo, pk=None, campo='email'):
    """Valida formato y unicidad de correo (sin distinguir mayúsculas)."""
    normalizado = validar_correo(valor)
    if not normalizado:
        return ''
    existentes = modelo.objects.filter(**{f'{campo}__iexact': normalizado})
    if pk:
        existentes = existentes.exclude(pk=pk)
    if existentes.exists():
        _error('Ya existe un registro con ese correo electrónico.')
    return normalizado


def validar_direccion(valor, maximo=220):
    """Valida una dirección: texto normal, sin marcado ni controles."""
    texto = _compactar_espacios(valor)
    if not texto:
        return ''
    if len(texto) < 3:
        _error('La dirección es demasiado corta.')
    if len(texto) > maximo:
        _error(f'La dirección no puede superar los {maximo} caracteres.')
    if any(caracter in _CARACTERES_PELIGROSOS for caracter in texto):
        _error('La dirección contiene caracteres no permitidos.')
    if _RE_PELIGRO_TEXTO.search(texto):
        _error('La dirección contiene contenido no permitido.')
    return texto


def validar_texto_libre(valor, campo='texto', maximo=1000, obligatorio=False):
    """Valida observaciones, descripciones y reglamentos.

    Permite puntuación normal, pero bloquea etiquetas de script, manejadores
    de eventos, caracteres de control y contenido nulo.
    """
    texto = _texto(valor)
    if not texto:
        if obligatorio:
            _error(f'El {campo} es obligatorio.')
        return ''
    if len(texto) > maximo:
        _error(f'El {campo} no puede superar los {maximo} caracteres.')
    if any(caracter in texto for caracter in '<>\x00'):
        _error(f'El {campo} no puede contener <, > ni caracteres de control.')
    if _RE_PELIGRO_TEXTO.search(texto):
        _error(f'El {campo} contiene contenido no permitido.')
    return texto


def validar_usuario(valor):
    """Valida el nombre de usuario de acceso (4 a 30 caracteres seguros)."""
    texto = _texto(valor)
    if not texto:
        _error('El usuario de acceso es obligatorio.')
    if not _RE_USUARIO.match(texto):
        _error(
            'El usuario debe tener entre 4 y 30 caracteres y solo puede '
            'usar letras sin tildes, números, punto, guion y guion bajo.'
        )
    return texto
