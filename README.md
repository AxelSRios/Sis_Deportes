# Sistema de Gestión Deportiva AFO · Oruro

Plataforma institucional para clubes, competencias, arbitraje, tesorería y
administración de la Asociación de Fútbol Oruro.

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
