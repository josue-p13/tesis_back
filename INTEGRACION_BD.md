# Integración con Base de Datos PostgreSQL

Este documento explica cómo usar el sistema de almacenamiento de referencias bibliográficas con verificación de duplicados.

## 📋 Requisitos previos

1. Tener Docker y Docker Compose instalados
2. Iniciar los servicios de APIs_locales (GROBID + PostgreSQL + pgAdmin)

## 🚀 Inicio rápido

### 1. Iniciar los servicios Docker

```bash
cd ../APIs_locales
docker-compose up -d
```

Esto iniciará:
- GROBID en `http://localhost:8070`
- PostgreSQL en `localhost:5432`
- pgAdmin en `http://localhost:5050` (Interfaz gráfica)

### 2. Configurar variables de entorno

Copia el archivo `.env.example` a `.env`:

```bash
cp .env.example .env
```

El archivo `.env` ya tiene la configuración por defecto que coincide con Docker Compose.

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Iniciar el backend

```bash
uvicorn app.main:app --reload --port 8000
```

## 🔄 Cómo funciona

### Extracción y almacenamiento automático

Cuando subes un PDF a través del endpoint `/documents/extraer-referencias`:

1. **Extracción**: GROBID extrae las referencias del PDF
2. **Parseo**: El sistema parsea el XML y estructura los datos
3. **Verificación de duplicados**: Se calcula un hash MD5 basado en:
   - Título
   - Autores
   - Año
   - Publicación
   - **NO incluye**: volumen ni páginas (para detección más global)
4. **Almacenamiento**: Solo se guardan referencias nuevas (no duplicadas)

### Campos importantes vs informativos

**Campos para verificar duplicados:**
- titulo
- autores
- año
- publicacion

**Campos solo informativos (no verifican duplicados):**
- volumen
- paginas
- doi
- texto_raw

## 📝 Uso de la API

### Extraer referencias de un PDF

```bash
curl -X POST "http://localhost:8000/documents/extraer-referencias" \
  -H "Content-Type: multipart/form-data" \
  -F "pdf=@documento.pdf" \
  -F "guardar_en_bd=true"
```

**Respuesta:**
```json
{
  "total_referencias": 25,
  "estilo_citacion": {
    "nombre": "IEEE",
    "descripcion": "Institute of Electrical and Electronics Engineers"
  },
  "referencias": [...],
  "archivos_generados": {
    "completo": "referencias/referencias_documento.txt",
    "resumen": "referencias/resumen_documento.txt"
  },
  "base_de_datos": {
    "total": 25,
    "guardadas": 20,
    "duplicadas": 5,
    "errores": 0,
    "detalles": [...]
  }
}
```

### Buscar referencias en la BD

```bash
# Buscar todas las referencias
curl "http://localhost:8000/documents/referencias?limit=10"

# Buscar por texto
curl "http://localhost:8000/documents/referencias?query=machine+learning&limit=20"
```

### Obtener estadísticas

```bash
curl "http://localhost:8000/documents/estadisticas"
```

**Respuesta:**
```json
{
  "total_referencias": 150,
  "años_distintos": 25,
  "autores_distintos": 300,
  "publicaciones_distintas": 80,
  "año_mas_antiguo": "1998",
  "año_mas_reciente": "2024",
  "referencias_con_doi": 120
}
```

## 🔍 Verificación de duplicados

El sistema automáticamente verifica duplicados usando un hash MD5 de:
```
hash = MD5(titulo_normalizado | autores_normalizados | año | publicacion_normalizada)
```

La normalización incluye:
- Convertir a minúsculas
- Eliminar espacios extra

**Ejemplo:**

Estas dos referencias se considerarían duplicadas:

```
Referencia 1:
- Título: "Machine Learning Basics"
- Autores: "John Smith, Mary Doe"
- Año: "2020"
- Publicación: "Journal of AI"
- Volumen: "10"
- Páginas: "100-120"

Referencia 2:
- Título: "Machine Learning Basics"
- Autores: "John Smith, Mary Doe"
- Año: "2020"
- Publicación: "Journal of AI"
- Volumen: "15"  <- Diferente, pero NO importa
- Páginas: "50-70"  <- Diferente, pero NO importa
```

## 🗄️ Acceso directo a la base de datos

### Usando psql

```bash
psql -h localhost -U referencias_user -d referencias_db
```

Password: `referencias_pass`

### Consultas útiles

```sql
-- Ver todas las referencias
SELECT id, titulo, autores, año FROM referencias LIMIT 10;

-- Buscar referencias por año
SELECT * FROM referencias WHERE año = '2020';

-- Buscar por autor
SELECT * FROM referencias WHERE autores ILIKE '%Smith%';

-- Referencias más recientes
SELECT titulo, autores, año FROM referencias 
ORDER BY fecha_creacion DESC LIMIT 5;

-- Ver estadísticas
SELECT * FROM estadisticas_referencias;
```

## 🖥️ Administración gráfica con pgAdmin

### Acceso a pgAdmin

1. **Abrir en el navegador:**
   ```
   http://localhost:5050
   ```

2. **Credenciales de login:**
   - Email: `admin@admin.com`
   - Contraseña: `admin123`

### Configurar la conexión a PostgreSQL (primera vez)

1. Una vez dentro de pgAdmin, click derecho en **"Servers"** en el panel izquierdo
2. Selecciona **"Register" → "Server"**

3. **Pestaña "General":**
   - Name: `Referencias DB` (o el nombre que prefieras)

4. **Pestaña "Connection":**
   - Host name/address: `postgres` (importante: usar el nombre del contenedor)
   - Port: `5432`
   - Maintenance database: `referencias_db`
   - Username: `referencias_user`
   - Password: `referencias_pass`
   - ✅ Marca "Save password" (opcional, para no ingresarla cada vez)

5. Click en **"Save"**

### Explorar las referencias

1. **Ver la tabla:**
   - Navega a: `Servers` → `Referencias DB` → `Databases` → `referencias_db` → `Schemas` → `public` → `Tables`
   - Click derecho en `referencias` → **"View/Edit Data"** → **"All Rows"**
   - Aquí verás todas las referencias almacenadas en formato de tabla

2. **Filtrar datos:**
   - En la vista de datos, usa el icono de filtro (embudo) en la barra de herramientas
   - Puedes filtrar por cualquier columna

3. **Ordenar datos:**
   - Click en el encabezado de cualquier columna para ordenar

### Ejecutar consultas SQL personalizadas

1. Click derecho en `referencias_db` → **"Query Tool"**
2. Escribe tu consulta SQL
3. Presiona **F5** o click en el botón de "Play" para ejecutar

**Ejemplos de consultas útiles:**

```sql
-- Ver referencias recientes (últimos 7 días)
SELECT titulo, autores, año, fecha_creacion 
FROM referencias 
WHERE fecha_creacion >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY fecha_creacion DESC;

-- Contar referencias por año
SELECT año, COUNT(*) as total 
FROM referencias 
WHERE año IS NOT NULL 
GROUP BY año 
ORDER BY año DESC;

-- Buscar referencias sobre un tema específico
SELECT titulo, autores, año, publicacion
FROM referencias 
WHERE titulo ILIKE '%machine learning%' 
   OR titulo ILIKE '%deep learning%'
ORDER BY año DESC;

-- Ver referencias duplicadas (por hash)
SELECT hash_unico, COUNT(*) as veces
FROM referencias
GROUP BY hash_unico
HAVING COUNT(*) > 1;

-- Top 10 autores con más publicaciones
SELECT autores, COUNT(*) as total
FROM referencias
WHERE autores IS NOT NULL
GROUP BY autores
ORDER BY total DESC
LIMIT 10;

-- Referencias por fuente de documento
SELECT fuente_documento, COUNT(*) as total
FROM referencias
GROUP BY fuente_documento
ORDER BY total DESC;

-- Ver estadísticas completas
SELECT * FROM estadisticas_referencias;
```

### Exportar datos

1. Ejecuta tu consulta en el Query Tool
2. Click en el botón **"Download as CSV"** (F8) en la barra de herramientas
3. Elige el formato de exportación:
   - CSV
   - Excel
   - Texto plano

### Editar datos manualmente

1. En la vista de datos (View/Edit Data)
2. Doble click en cualquier celda para editarla
3. Presiona Enter para guardar
4. Click en el botón **"Save"** (F6) para confirmar los cambios

### Crear respaldos (Backup)

1. Click derecho en `referencias_db` → **"Backup..."**
2. Configura las opciones:
   - Filename: `referencias_backup_2026-03-09.backup`
   - Format: **"Custom"** o **"Plain"** (SQL)
3. Click en **"Backup"**

### Restaurar desde backup

1. Click derecho en `referencias_db` → **"Restore..."**
2. Selecciona el archivo de backup
3. Click en **"Restore"**

## 🐍 Uso programático en Python

```python
from app.services.database_service import DatabaseService

# Crear instancia del servicio
with DatabaseService() as db:
    # Verificar si una referencia es duplicada
    es_duplicado, ref_existente = db.verificar_duplicado(
        titulo="Machine Learning Basics",
        autores="John Smith",
        año="2020",
        publicacion="Journal of AI"
    )
    
    if es_duplicado:
        print(f"Referencia duplicada con ID: {ref_existente['id']}")
    else:
        print("Referencia nueva")
    
    # Guardar una referencia
    referencia = {
        'titulo': 'New Paper on AI',
        'autores': 'Jane Doe',
        'año': '2024',
        'publicacion': 'AI Conference',
        'volumen': '5',
        'paginas': '10-20'
    }
    
    guardado, ref_id, mensaje = db.guardar_referencia(
        referencia, 
        fuente_documento="paper.pdf"
    )
    
    if guardado:
        print(f"Guardado con ID: {ref_id}")
    else:
        print(f"No guardado: {mensaje}")
    
    # Buscar referencias
    resultados = db.buscar_referencias(query="AI", limit=10)
    for ref in resultados:
        print(f"{ref['titulo']} - {ref['año']}")
    
    # Obtener estadísticas
    stats = db.obtener_estadisticas()
    print(f"Total de referencias: {stats['total_referencias']}")
```

## 🔧 Solución de problemas

### Error: No se puede conectar a PostgreSQL

```bash
# Verificar que el contenedor está corriendo
docker ps | grep postgres

# Ver logs del contenedor
docker logs referencias-db

# Reiniciar el servicio
cd ../APIs_locales
docker-compose restart postgres
```

### Error: No se puede conectar a GROBID

```bash
# Verificar que GROBID está corriendo
curl http://localhost:8070/api/isalive

# Ver logs
docker logs grobid-service

# Reiniciar
cd ../APIs_locales
docker-compose restart grobid
```

### Limpiar la base de datos

**Opción 1: Desde pgAdmin (interfaz gráfica)**
```
1. Abrir pgAdmin → Query Tool
2. Ejecutar: TRUNCATE referencias RESTART IDENTITY CASCADE;
3. Esto borrará todos los datos pero mantendrá la estructura
```

**Opción 2: Eliminar y recrear (terminal)**
```bash
cd ../APIs_locales
docker-compose down -v
docker-compose up -d
```

**Opción 3: Solo borrar referencias (terminal)**
```bash
psql -h localhost -U referencias_user -d referencias_db -c "TRUNCATE referencias;"
```

### Error: No se puede acceder a pgAdmin

```bash
# Verificar que el contenedor está corriendo
docker ps | grep pgadmin

# Ver logs
docker logs pgadmin-referencias

# Reiniciar el servicio
cd ../APIs_locales
docker-compose restart pgadmin
```

## 📊 Estructura de archivos

```
back_def/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py              # Configuración de BD y GROBID
│   ├── controllers/
│   │   └── document_controller.py # Endpoints de la API
│   ├── services/
│   │   ├── database_service.py    # Lógica de BD y duplicados
│   │   ├── document_service.py    # Extracción con GROBID
│   │   └── xml_parser_service.py  # Parseo de XML
│   └── main.py
├── referencias/                    # Archivos TXT generados
├── .env                           # Configuración (NO commitar)
├── .env.example                   # Plantilla de configuración
└── requirements.txt

APIs_locales/
├── docker-compose.yml             # Docker services
├── init-db.sql                    # Script de inicialización de BD
└── README.md
```

## 🎯 Próximos pasos

1. Personalizar la lógica de verificación de duplicados si es necesario
2. Agregar más índices a la BD para mejorar el rendimiento
3. Implementar exportación de referencias a formatos como BibTeX, RIS, etc.
4. Crear dashboard para visualizar estadísticas
