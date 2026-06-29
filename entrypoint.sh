#!/bin/bash

# 1. Iniciar Grobid en segundo plano desde su directorio correcto
echo "Iniciando Grobid en segundo plano..."
cd /opt/grobid
./grobid-service/bin/grobid-service &

# 2. Esperar a que Grobid esté completamente activo y respondiendo
echo "Esperando a que Grobid esté disponible en http://localhost:8070..."
for i in {1..30}; do
  if curl -s http://localhost:8070/api/isalive > /dev/null; then
    echo "¡Grobid está activo y listo!"
    break
  fi
  echo "Grobid aún se está iniciando, reintentando en 2 segundos... ($i/30)"
  sleep 2
done

# 3. Iniciar el backend de FastAPI en el puerto 7860
echo "Iniciando FastAPI en el puerto 7860..."
cd /app
/app/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 7860
