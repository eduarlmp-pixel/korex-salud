@echo off
echo.
echo  QMS Salud - Instalacion
echo  ========================

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no encontrado. Instalalo desde python.org
    pause
    exit /b 1
)

REM Crear entorno virtual
if not exist venv (
    echo  Creando entorno virtual...
    python -m venv venv
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar dependencias
echo  Instalando dependencias...
pip install -r requirements.txt -q

REM Seed de base de datos
echo  Iniciando base de datos con datos de demo...
python seed.py

echo.
echo  Todo listo!
echo.
echo  Usuarios disponibles:
echo    admin@qms.co   / admin123
echo    calidad@qms.co / calidad123
echo.
echo  Abriendo en http://localhost:8000
echo  Presiona Ctrl+C para detener
echo.

start http://localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
