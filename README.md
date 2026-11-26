# Sistema de Gestión Deportiva AFO · Oruro

Plataforma institucional para clubes, competencias, arbitraje, tesorería y
administración de la Asociación de Fútbol Oruro.

## Manual completo

Guía paso a paso para instalar Python, Git, la base de datos y abrir el
proyecto desde cero:

[`docs/MANUAL_USUARIO.md`](docs/MANUAL_USUARIO.md)

También disponible en PDF y LaTeX:

- [`docs/MANUAL_USUARIO.pdf`](docs/MANUAL_USUARIO.pdf)
- [`docs/MANUAL_USUARIO.tex`](docs/MANUAL_USUARIO.tex)

## Configuración local

```powershell
# 1. Crear el entorno y instalar dependencias
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Configurar variables de entorno
Copy-Item .env.example .env
# Edite .env y defina SECRET_KEY y DATABASE_URL

# 3. Preparar la base y ejecutar
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

`.env` está excluido de Git. No incluya credenciales en el código ni en
capturas de pantalla.

## Seguridad operativa

- Respaldos automáticos, verificación de restauración y tarea programada:
  `docs/SEGURIDAD.md`.
- Registro de inicios, cierres e intentos fallidos: `/accesos/` (Administración).
- Pruebas: `.\.venv\Scripts\python.exe manage.py test core`.

## Estilos (Tailwind CSS)

El CSS de utilidades se compila en el repositorio y se sirve como archivo
estático (`static/css/tailwind.css`). No se usa el CDN de Tailwind en el
navegador, lo que evita compilar estilos en cada visita.

Si agrega o cambia clases de Tailwind en `templates/`, `static/js/` o
`core/`, recompile antes de desplegar:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_tailwind.ps1
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

La configuración institucional (paleta y tipografía) está en
`tailwind.config.js` y `static/js/tailwind-config.js`.

## Despliegue en Render

El proyecto incluye `render.yaml` para un Web Service gratuito con Gunicorn,
WhiteNoise y Supabase. En Render configure estas variables:

- `SECRET_KEY` (Render puede generarla)
- `DEBUG=0`
- `ALLOWED_HOSTS=.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://*.onrender.com`
- `DATABASE_URL` de Supabase
- `AFO_TRUST_X_FORWARDED_FOR=1`
- `PYTHON_VERSION=3.13.7` (ajuste según la versión disponible en Render)

Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`.

Start: `gunicorn sistema_deportes.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.

Los archivos subidos a `media/` no son persistentes en el plan gratuito; use
Supabase Storage o S3.
