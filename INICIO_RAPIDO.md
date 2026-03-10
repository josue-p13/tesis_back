# 🚀 Inicio Rápido del Sistema

## 📋 Requisitos previos
- Docker y Docker Compose instalados
- Python 3.8+ instalado
- pip instalado

## 🔧 Instalación (primera vez)

### 1. Instalar dependencias de Python
```bash
cd back_def
pip install -r requirements.txt
```

### 2. Configurar variables de entorno
```bash
# El archivo .env ya existe, pero puedes verificar/editar
cat .env
```

### 3. Iniciar servicios Docker
```bash
cd ../APIs_locales
docker compose up -d
```

Esto iniciará:
- PostgreSQL (puerto 5432)
- GROBID (puerto 8070)
- pgAdmin (puerto 5050)

## ▶️ Iniciar el backend

### Opción 1: Usando el script (recomendado)
```bash
cd back_def
./start.sh
```

### Opción 2: Manual
```bash
cd back_def
uvicorn app.main:app --reload --port 8000
```

## 🌐 URLs de acceso

| Servicio | URL |
|----------|-----|
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **pgAdmin** | http://localhost:5050 |
| **GROBID** | http://localhost:8070 |

## 🔐 Credenciales

**pgAdmin:**
- Email: `admin@admin.com`
- Password: `admin123`

**PostgreSQL (desde pgAdmin):**
- Host: `postgres`
- Port: `5432`
- Database: `referencias_db`
- User: `referencias_user`
- Password: `referencias_pass`

## ✅ Verificar que todo funciona

### 1. Verificar servicios Docker
```bash
docker ps
```

Deberías ver:
- `referencias-db` (PostgreSQL)
- `grobid-service` (GROBID)
- `pgadmin-referencias` (pgAdmin)

### 2. Probar el backend
Abre en tu navegador: http://localhost:8000/docs

Deberías ver la interfaz de Swagger con los endpoints disponibles.

### 3. Probar subir un PDF
En la interfaz de Swagger:
1. Expande el endpoint `POST /documents/extraer-referencias`
2. Click en "Try it out"
3. Sube un archivo PDF
4. Click en "Execute"

## 🛑 Detener todo

### Detener backend
Presiona `Ctrl+C` en la terminal donde corre uvicorn

### Detener servicios Docker
```bash
cd APIs_locales
docker compose down
```

## 🔧 Troubleshooting

### Error: "No module named 'psycopg2'"
```bash
cd back_def
pip install -r requirements.txt
```

### Error: "No se puede conectar a PostgreSQL"
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Si no está corriendo, iniciar servicios
cd APIs_locales
docker compose up -d
```

### Error: "GROBID no responde"
```bash
# Reiniciar GROBID
docker restart grobid-service

# Esperar 30-60 segundos y verificar
curl http://localhost:8070/api/isalive
```

### Limpiar la base de datos
```bash
# Opción 1: Desde psql
psql -h localhost -U referencias_user -d referencias_db -c "TRUNCATE referencias;"

# Opción 2: Desde pgAdmin
# Query Tool → TRUNCATE referencias RESTART IDENTITY CASCADE;
```

## 📝 Uso básico

### Extraer referencias de un PDF (cURL)
```bash
curl -X POST "http://localhost:8000/documents/extraer-referencias" \
  -F "pdf=@documento.pdf" \
  -F "guardar_en_bd=true"
```

### Buscar referencias almacenadas
```bash
curl "http://localhost:8000/documents/referencias?query=machine+learning&limit=10"
```

### Ver estadísticas
```bash
curl "http://localhost:8000/documents/estadisticas"
```

## 📊 Flujo completo

1. **Iniciar servicios Docker**
   ```bash
   cd APIs_locales && docker compose up -d
   ```

2. **Iniciar backend**
   ```bash
   cd back_def && ./start.sh
   ```

3. **Subir PDF** → El sistema automáticamente:
   - Extrae referencias con GROBID
   - Parsea y estructura los datos
   - Verifica duplicados
   - Guarda en PostgreSQL
   - Genera archivos TXT

4. **Ver resultados**:
   - API: http://localhost:8000/docs
   - pgAdmin: http://localhost:5050
   - Archivos TXT: `back_def/referencias/`

## 📚 Más información

- **Guía completa**: Ver `INTEGRACION_BD.md`
- **Referencia rápida**: Ver `../GUIA_RAPIDA.md`
- **README APIs**: Ver `../APIs_locales/README.md`
