@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0.."
if not exist "backups" mkdir "backups"
".venv\Scripts\python.exe" manage.py backup_bd --etiqueta programado >> "backups\scheduler.log" 2>&1
exit /b %ERRORLEVEL%
