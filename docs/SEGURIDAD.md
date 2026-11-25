# Seguridad operativa A.F.O.

## Respaldos de base de datos

La base activa es PostgreSQL 17 en Supabase. El cliente `pg_dump` instalado
(9.5) es anterior al servidor, por lo que el respaldo automático usa el
formato lógico JSON comprimido de Django (`dumpdata`), que incluye usuarios,
roles, permisos e historial. Si en el futuro se instala un cliente PostgreSQL
compatible, `backup_bd` usará `pg_dump` automáticamente.

```powershell
# Respaldo manual
.\.venv\Scripts\python.exe manage.py backup_bd --etiqueta manual

# Verificar integridad y restaurar en un SQLite aislado
.\.venv\Scripts\python.exe manage.py verificar_respaldo --restaurar

# Programar todos los días a las 02:00
.\.venv\Scripts\python.exe manage.py programar_backup --hora 02:00

# Programar cada 6 horas
.\.venv\Scripts\python.exe manage.py programar_backup --cada-horas 6 --hora 00:00

# Consultar o eliminar la tarea de Windows
.\.venv\Scripts\python.exe manage.py programar_backup --estado
.\.venv\Scripts\python.exe manage.py programar_backup --eliminar
```

- Carpeta por defecto: `backups/` (`AFO_BACKUP_DIR`).
- Conservación: 14 copias (`AFO_BACKUP_RETENTION`).
- Bitácora: `backups/backup.log`.
- Manifiesto con SHA-256, formato y conteos: `backups/ultimo_respaldo.json`.
- La restauración de prueba crea un SQLite temporal y nunca toca Supabase.
- La tarea de Windows se ejecuta con el usuario actual. Para un servidor
  desatendido debe crearse con una cuenta de servicio.

## Registro de accesos

Cada evento se guarda en la tabla `registros_acceso`:

- `LOGIN`: autenticación correcta (usuario, rol, IP y fecha).
- `LOGIN_FALLIDO`: credenciales inválidas (usuario intentado, IP y navegador).
- `LOGOUT`: cierre de sesión.
- `BLOQUEO`: límite de intentos alcanzado.

No se almacenan contraseñas ni tokens. La consulta está disponible en
`/accesos/` para el rol Administrador y en el menú **Administración → Accesos
y sesiones**.

```powershell
# Simular o ejecutar la limpieza de registros antiguos
.\.venv\Scripts\python.exe manage.py limpiar_accesos --simular
.\.venv\Scripts\python.exe manage.py limpiar_accesos --dias 365
```

## Variables de entorno opcionales

| Variable | Descripción |
| --- | --- |
| `AFO_BACKUP_DIR` | Carpeta de respaldos. |
| `AFO_BACKUP_RETENTION` | Número de copias a conservar. |
| `AFO_BACKUP_TIMEOUT` | Tiempo máximo de `pg_dump` en segundos. |
| `AFO_BACKUP_PG_DUMP` | Ruta o nombre del ejecutable `pg_dump`. |
| `AFO_TRUST_X_FORWARDED_FOR` | `1` solo si hay un proxy controlado. |
| `AFO_ACCESS_LOG_RETENTION_DAYS` | Días de retención de accesos. |

## Riesgos pendientes de infraestructura

- El proyecto y los respaldos están en una unidad **FAT32**, que no admite
  permisos NTFS: cualquier usuario con acceso al medio puede leerlos.
- Los respaldos incluyen hashes de contraseñas y datos institucionales; deben
  guardarse en un volumen NTFS restringido o cifrado.
- `.env` también reside en la unidad FAT32 y contiene la cadena de conexión.
- `DEBUG=True`, `SECRET_KEY` fija y `ALLOWED_HOSTS=[]` deben cambiarse antes de
  exponer la aplicación a Internet.
- Las cookies de sesión/CSRF no fuerzan HTTPS.
