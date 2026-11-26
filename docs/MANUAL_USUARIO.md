# Manual de usuario y puesta en marcha — A.F.O. Oruro

Sistema de Gestión Deportiva de la Asociación de Fútbol Oruro.

Este manual permite que otra persona instale el proyecto desde cero, lo abra en
su computadora y lo utilice. Está pensado para Windows (PowerShell); al final se
indican las diferencias para macOS y Linux.

---

## 1. Qué es el sistema

Aplicación web desarrollada con **Django 6** y **PostgreSQL/Supabase** para
administrar:

- Clubes afiliados y sus equipos.
- Deportistas (fichajes) y categorías.
- Campeonatos, fixture y partidos.
- Árbitros y designaciones.
- Tesorería y pagos.
- Usuarios, roles, auditoría y accesos.
- Portal público con noticias, clubes, canchas y resultados.

La interfaz está construida con plantillas Django, Tailwind CSS compilado y
JavaScript sin frameworks. **No requiere Node.js** para funcionar.

---

## 2. Programas que se deben instalar

| Programa | Versión recomendada | Para qué sirve | ¿Obligatorio? |
|---|---|---|---|
| **Git** | 2.40 o superior | Descargar y actualizar el proyecto | Sí |
| **Python** | **3.13** (mínimo 3.12) | Ejecutar Django y el sistema | Sí |
| **Navegador** | Chrome, Edge o Firefox actualizado | Abrir la aplicación | Sí |
| **VS Code** | Última versión | Editar el código cómodamente | Recomendado |
| **Supabase** | Cuenta gratuita (nube) | Base de datos PostgreSQL | Sí, salvo que use PostgreSQL local |
| **PostgreSQL** | 16 o 17 | Alternativa local a Supabase | Opcional |
| **Node.js** | — | **No se necesita** | No |

> El proyecto usa `psycopg[binary]`, que ya incluye el controlador de
> PostgreSQL. No hace falta instalar el cliente de PostgreSQL para ejecutar la
> aplicación, solo si desea usar `pg_dump` para respaldos.

---

## 3. Instalación paso a paso (Windows)

### 3.1 Instalar Git

1. Descargue Git desde <https://git-scm.com/download/win>.
2. Ejecute el instalador y deje las opciones por defecto.
3. Abra **PowerShell** y verifique:

```powershell
git --version
```

Debe mostrar algo como `git version 2.4x`.

### 3.2 Instalar Python

1. Descargue Python 3.13 desde <https://www.python.org/downloads/windows/>.
2. Ejecute el instalador y marque **“Add python.exe to PATH”**.
3. Verifique en PowerShell:

```powershell
python --version
py --version
```

Debe mostrar `Python 3.13.x` (o superior). Si `python` no se reconoce, cierre y
vuelva a abrir PowerShell; si persiste, reinstale marcando la opción del PATH.

### 3.3 Instalar VS Code (opcional)

1. Descargue <https://code.visualstudio.com/>.
2. Instale la extensión **Python** de Microsoft.
3. Abra la carpeta del proyecto con **Archivo → Abrir carpeta**.
4. Seleccione el intérprete: `Ctrl + Shift + P` → **Python: Select
   Interpreter** → `.venv\Scripts\python.exe`.

### 3.4 Base de datos

Tiene dos opciones.

#### Opción A — Supabase (recomendada, sin instalar nada)

1. Cree una cuenta en <https://supabase.com>.
2. Cree un proyecto nuevo y guarde la contraseña de la base.
3. En el panel del proyecto vaya a **Connect** (o **Project Settings →
   Database**) y copie la cadena de conexión **Session pooler** (puerto 5432).
4. Reemplace `[YOUR-PASSWORD]` por la contraseña real y asegúrese de que termine
   en `?sslmode=require`.

Ejemplo del formato:

```text
postgresql://postgres.abcdefgh:MI_CLAVE@aws-1-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

> Si el servicio web está en Render (región Ohio), conviene que Supabase esté en
> una región cercana (por ejemplo `us-east-1`) para reducir la latencia.

#### Opción B — PostgreSQL local

1. Descargue PostgreSQL 16/17 desde <https://www.postgresql.org/download/windows/>.
2. Instale y anote el usuario, la contraseña y el puerto (5432).
3. Cree una base de datos, por ejemplo `afo`.
4. La cadena quedará así:

```text
postgresql://postgres:MI_CLAVE@localhost:5432/afo
```

#### Opción C — SQLite (solo pruebas locales)

No requiere instalar nada. En `.env` use:

```text
DATABASE_URL=sqlite:///db.sqlite3
```

Sirve para probar el sistema, pero no se recomienda para producción.

---

## 4. Obtener el proyecto

En PowerShell, ubíquese en la carpeta donde desea guardarlo:

```powershell
cd C:\Proyectos
git clone https://github.com/AxelSRios/Sis_Deportes.git
cd Sis_Deportes
```

Si el repositorio es privado, Git le pedirá iniciar sesión con GitHub.

---

## 5. Crear el entorno virtual e instalar dependencias

```powershell
# Crear el entorno (una sola vez)
py -3.13 -m venv .venv

# Permitir scripts locales en PowerShell (una sola vez)
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# Activar el entorno
.\.venv\Scripts\Activate.ps1

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si la activación falla, puede usar el Python del entorno directamente sin
activarlo:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Verifique que Django quedó instalado:

```powershell
python -c "import django; print(django.get_version())"
```

Debe mostrar `6.1.x`.

---

## 6. Configurar las variables de entorno

1. Copie el archivo de ejemplo:

```powershell
Copy-Item .env.example .env
```

2. Abra `.env` con VS Code o Notepad y complete:

```ini
SECRET_KEY=una-clave-larga-y-aleatoria
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=

DATABASE_URL=postgresql://USUARIO:CLAVE@HOST:5432/postgres?sslmode=require
```

3. Genere una `SECRET_KEY` segura:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copie el resultado en `SECRET_KEY`.

### Variables disponibles

| Variable | Uso |
|---|---|
| `SECRET_KEY` | Firma de sesiones y CSRF. Obligatoria |
| `DEBUG` | `1` en desarrollo, `0` en producción |
| `ALLOWED_HOSTS` | Dominios permitidos, separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Orígenes HTTPS confiables en producción |
| `DATABASE_URL` | Cadena de conexión a PostgreSQL o SQLite |
| `AFO_TRUST_X_FORWARDED_FOR` | `1` detrás de un proxy confiable (Render) |
| `AFO_BACKUP_DIR` | Carpeta de respaldos (opcional) |
| `AFO_BACKUP_RETENTION` | Copias a conservar (opcional) |

> `.env` está en `.gitignore`: **nunca** lo suba al repositorio ni comparta sus
> valores.

---

## 7. Preparar la base de datos

Con el entorno activado:

```powershell
python manage.py migrate
python manage.py check
```

`migrate` crea todas las tablas. `check` no debe reportar errores.

---

## 8. Crear las cuentas de usuario

El sistema crea una cuenta por rol con contraseñas aleatorias:

```powershell
python manage.py crear_usuarios_roles
```

| Usuario | Rol |
|---|---|
| `administrador` | Administrador General (superusuario) |
| `dirigente` | Dirigente de Club Afiliado |
| `arbitro` | Comisión Técnica / Árbitros |
| `tesorero` | Tesorero / Finanzas |

Las contraseñas se guardan en un archivo fuera del proyecto:

```text
C:\Users\<USUARIO_WINDOWS>\AFO-credenciales.txt
```

(o en `Documents` si esa carpeta existe). Guarde las claves en un gestor de
contraseñas y elimine el archivo.

Opciones útiles:

```powershell
# Regenerar contraseñas
python manage.py crear_usuarios_roles --restablecer

# Guardar credenciales en otra ruta
python manage.py crear_usuarios_roles --archivo C:\ruta\credenciales.txt

# Eliminar la cuenta antigua "admin" si existiera
python manage.py crear_usuarios_roles --eliminar-legacy
```

---

## 9. Datos iniciales (opcional)

Para probar el sistema con datos de demostración, ejecute en este orden:

```powershell
# 1) Categorías base: Primera A y Primera B
python manage.py cargar_categorias_2026

# 2) 20 clubes afiliados de la gestión 2026
python manage.py cargar_clubes_2026

# 3) Equipos y nóminas (2 equipos por club, 15 a 22 jugadores cada uno)
#    Puede tardar varios minutos si la base está en la nube.
python manage.py cargar_equipos_2026

# 4) Campeonato de Primera A 2026 y su fixture (91 partidos)
python manage.py cargar_campeonato_2026
```

Los comandos son idempotentes: si se ejecutan otra vez no duplican registros.

> Los datos personales generados (nombres, CI, teléfonos) son **ficticios** y
> sirven solo para demostración y pruebas.

Alternativa de demostración breve (50 deportistas):

```powershell
python manage.py cargar_demo_bolivia --cantidad 50
```

---

## 10. Ejecutar el sistema

```powershell
python manage.py runserver
```

Abra en el navegador:

- Aplicación: <http://127.0.0.1:8000/>
- Acceso: <http://127.0.0.1:8000/login/>
- Portal público: <http://127.0.0.1:8000/clubes-publicos/>

Si el puerto 8000 está ocupado:

```powershell
python manage.py runserver 8001
```

Para detener el servidor: `Ctrl + C`.

---

## 11. Uso del sistema

### 11.1 Iniciar sesión

Ingrese con el usuario y la contraseña del archivo de credenciales. El rol se
deduce automáticamente de la cuenta; no se elige en el formulario.

### 11.2 Roles y permisos

| Rol | Puede hacer |
|---|---|
| **Administrador** | Todo: clubes, equipos, deportistas, campeonatos, árbitros, pagos, usuarios, auditoría |
| **Dirigente** | Equipos, deportistas e inscripciones de su club; consulta general |
| **Árbitro** | Partidos y designaciones arbitrales; consulta general |
| **Tesorero** | Tesorería y pagos; consulta general |

Los módulos restringidos (Usuarios, Auditoría, Tesorería) devuelven “Sin
permiso” para los roles que no corresponden.

### 11.3 Módulos principales

| Módulo | Ruta | Para qué |
|---|---|---|
| Panel General | `/panel-general/` | Resumen operativo y accesos rápidos |
| Clubes | `/clubes/` | Padrón de clubes afiliados |
| Equipos | `/equipos/` | Equipos por club, categoría y división |
| Deportistas | `/deportistas/` | Fichajes y datos de jugadores |
| Categorías | `/categorias/` | Primera A/B, Sub 15, Sub 19, etc. |
| Campeonatos | `/campeonatos/` | Torneos y fixture |
| Partidos | `/partidos/` | Programación y resultados |
| Árbitros | `/arbitros/` | Registro de árbitros |
| Asignaciones | `/asignaciones/` | Ternas arbitrales |
| Sanciones | `/sanciones/` | Amonestaciones, suspensiones y multas |
| Tesorería | `/tesoreria/` | Pagos e ingresos |
| Reportes | `/reportes/` | Exportaciones PDF/Excel |
| Usuarios | `/usuarios/` | Cuentas y roles |
| Auditoría | `/auditoria/` | Historial de operaciones |
| Accesos | `/accesos/` | Inicios de sesión y bloqueos |

### 11.4 Tareas frecuentes

**Crear un club:** Clubes → **Nuevo club**. Complete solo datos oficiales; no
invente NIT, personería ni representantes.

**Crear un equipo:** Equipos → **Nuevo equipo**. Seleccione club, categoría
(Primera A/B, Sub 15, Sub 19…), división y temporada.

**Registrar un jugador:** Deportistas → **Nuevo fichaje**. La CI debe ser única
y con formato boliviano (por ejemplo `12345678-OR`).

**Crear un campeonato:** Campeonatos → **Nuevo campeonato**. Luego programe los
partidos desde el fixture o desde **Partidos → Programar partido**.

**Registrar un pago:** Tesorería → **Registrar pago** (solo Administrador y
Tesorero).

---

## 12. Pruebas y mantenimiento

### 12.1 Pruebas automáticas

```powershell
python manage.py test
```

Usa una base SQLite en memoria: **no toca** la base real de Supabase. Todas las
pruebas deben pasar.

### 12.2 Archivos estáticos

En desarrollo Django los sirve solo. Para producción:

```powershell
python manage.py collectstatic --noinput
```

### 12.3 Estilos (Tailwind)

El CSS ya está compilado en `static/css/tailwind.css`; no hace falta Node para
ejecutar el sistema.

Si modifica clases de Tailwind en plantillas, JavaScript o Python, recompile:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_tailwind.ps1
python manage.py collectstatic --noinput
```

El script descarga la herramienta oficial la primera vez (requiere internet).

### 12.4 Respaldos

```powershell
# Crear respaldo
python manage.py backup_bd --etiqueta manual

# Verificar que el respaldo se puede restaurar
python manage.py verificar_respaldo --restaurar
```

Los respaldos se guardan en `backups/` (ignorada por Git). Más detalles en
[`docs/SEGURIDAD.md`](SEGURIDAD.md).

---

## 13. Publicar en Render (opcional)

1. Cree una cuenta en <https://render.com>.
2. **New → Web Service → Public Git Repository** y pegue la URL del repositorio.
3. Configure:

| Campo | Valor |
|---|---|
| Nombre | `afo-oruro` |
| Rama | `main` |
| Runtime | Python 3 |
| Plan | Free |
| Build Command | `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate` |
| Start Command | `gunicorn sistema_deportes.wsgi:application --bind 0.0.0.0:$PORT --worker-class gthread --workers 1 --threads 4 --timeout 120` |
| Health Check Path | `/health/` |

4. Agregue las variables de entorno:

```text
SECRET_KEY=<clave-generada>
DEBUG=0
ALLOWED_HOSTS=.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
DATABASE_URL=<cadena-de-supabase>
PYTHON_VERSION=3.13.7
AFO_TRUST_X_FORWARDED_FOR=1
```

5. Cree el servicio y espere el despliegue.
6. Verifique `/`, `/login/` y `/health/`.

Notas:

- Con **Public Git Repository**, Render no despliega automáticamente: cada
  cambio requiere **Manual Deploy → Deploy latest commit**.
- El plan Free suspende el servicio tras ~15 minutos sin tráfico; la primera
  visita puede tardar hasta 50 segundos.
- Los archivos subidos a `media/` no son persistentes; use Supabase Storage o
  S3 para imágenes cargadas por formulario.
- El repositorio incluye una GitHub Action que consulta `/health/` cada 10
  minutos para mantener despierta la instancia.

---

## 14. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `python` no se reconoce | Python no está en el PATH | Reinstalar marcando “Add to PATH” y reabrir PowerShell |
| `Activate.ps1` bloqueado | Política de ejecución | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No module named django` | Entorno virtual no activado | Activar `.venv` o usar `.\.venv\Scripts\python.exe` |
| `DisallowedHost` | Dominio no permitido | Agregarlo a `ALLOWED_HOSTS` |
| Error CSRF en producción | Origen no confiable | Configurar `CSRF_TRUSTED_ORIGINS` |
| No conecta a la base | Cadena incorrecta o proyecto pausado | Revisar `DATABASE_URL`, `sslmode=require` y el estado en Supabase |
| Estáticos 404 en producción | Falta `collectstatic` | Ejecutar `collectstatic` en el build |
| Se ven estilos viejos o incompletos | CSS sin recompilar | Ejecutar `scripts\build_tailwind.ps1` y `collectstatic` |
| `That port is already in use` | Otro servidor en el puerto | `python manage.py runserver 8001` |
| La primera visita tarda ~50 s | Plan Free dormido | Esperar o usar un monitor que consulte `/health/` |
| Migración falla por versión de Python | Versión incompatible | Usar Python 3.12+ (recomendado 3.13) |

---

## 15. Seguridad

- No subir `.env`, `backups/`, `media/` ni archivos de credenciales al
  repositorio.
- En producción: `DEBUG=0`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` correctos.
- Usar contraseñas largas y únicas; cambiarlas después del primer ingreso.
- El archivo `AFO-credenciales.txt` debe guardarse en un gestor de contraseñas y
  eliminarse del disco.
- Revisar periódicamente `/accesos/` y `/auditoria/`.
- Mantener respaldos verificados y fuera del equipo principal.

---

## 16. Estructura del proyecto

```text
Sis_Deportes/
├─ manage.py
├─ requirements.txt
├─ render.yaml
├─ .env.example
├─ sistema_deportes/        Configuración (settings, urls, wsgi)
├─ core/                    Modelos, vistas, formularios, comandos
│  ├─ management/commands/  Cargas y mantenimiento
│  ├─ migrations/
│  └─ templatetags/
├─ templates/               Plantillas Django
├─ static/                  CSS, JS e imágenes
│  ├─ css/tailwind.css      Tailwind compilado
│  ├─ img/clubes/           Escudos de clubes
│  └─ img/canchas/          Fotos de escenarios
├─ assets/css/              Entrada de Tailwind (fuente)
├─ scripts/                 Compilación de Tailwind
├─ docs/                    Manual y documentación
└─ backups/                 Respaldos locales (ignorado por Git)
```

---

## Anexo: comandos rápidos

```powershell
# Activar entorno
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install -r requirements.txt

# Migrar y comprobar
python manage.py migrate
python manage.py check

# Crear cuentas por rol
python manage.py crear_usuarios_roles

# Cargar datos de demostración
python manage.py cargar_categorias_2026
python manage.py cargar_clubes_2026
python manage.py cargar_equipos_2026
python manage.py cargar_campeonato_2026

# Ejecutar
python manage.py runserver

# Pruebas
python manage.py test

# Estáticos para producción
python manage.py collectstatic --noinput
```

Con esto, cualquier persona con acceso al repositorio puede instalar, abrir y
usar el sistema.
