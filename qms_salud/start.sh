#!/bin/bash
# Script de instalación y arranque rápido — QMS Salud
set -e

echo ""
echo "🏥  QMS Salud — Instalación"
echo "================================"

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "❌  Python3 no encontrado. Instálalo primero."
    exit 1
fi

echo "✓  Python3 encontrado: $(python3 --version)"

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "→  Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
echo "→  Instalando dependencias..."
pip install -r requirements.txt -q

# Crear .env si no existe
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
fi

# Seed de base de datos
echo "→  Iniciando base de datos con datos de demo..."
python seed.py

echo ""
echo "✅  ¡Todo listo!"
echo ""
echo "   Usuarios disponibles:"
echo "   • admin@qms.co     / admin123"
echo "   • calidad@qms.co   / calidad123"
echo "   • auditor@qms.co   / auditor123"
echo ""
echo "→  Iniciando servidor en http://localhost:8000"
echo "   Presiona Ctrl+C para detener"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
