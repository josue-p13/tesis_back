#!/bin/bash

# Script para iniciar el servidor backend con todas las dependencias

echo "🚀 Iniciando Backend de Referencias Bibliográficas"
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: No se encuentra app/main.py"
    echo "   Ejecuta este script desde el directorio back_def/"
    exit 1
fi

# Verificar que existe el archivo .env
if [ ! -f ".env" ]; then
    echo "⚠️  No se encuentra .env, copiando desde .env.example..."
    cp .env.example .env
    echo "✓ Archivo .env creado"
fi

# Verificar que Docker está corriendo
if ! docker ps > /dev/null 2>&1; then
    echo "❌ Error: Docker no está corriendo"
    exit 1
fi

# Verificar servicios Docker
echo "📦 Verificando servicios Docker..."
if ! docker ps | grep -q "referencias-db"; then
    echo "⚠️  PostgreSQL no está corriendo"
    echo "   Ejecuta: cd ../APIs_locales && docker compose up -d"
    exit 1
fi

if ! docker ps | grep -q "grobid-service"; then
    echo "⚠️  GROBID no está corriendo"
    echo "   Ejecuta: cd ../APIs_locales && docker compose up -d"
    exit 1
fi

echo "✓ PostgreSQL corriendo"
echo "✓ GROBID corriendo"
echo ""

# Verificar conexión a PostgreSQL
echo "🔌 Verificando conexión a PostgreSQL..."
python3 -c "
from app.services.database_service import DatabaseService
db = DatabaseService()
if db.conectar():
    print('✓ Conexión a PostgreSQL exitosa')
    db.desconectar()
else:
    print('❌ No se pudo conectar a PostgreSQL')
    exit(1)
" || exit 1

echo ""
echo "✓ Todo listo!"
echo ""
echo "📡 Iniciando servidor en http://localhost:8000"
echo "📚 Documentación API: http://localhost:8000/docs"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

# Iniciar uvicorn
uvicorn app.main:app --reload --port 8000
