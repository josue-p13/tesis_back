# Sistema de Extracción de Referencias Bibliográficas

Backend para extracción y análisis de referencias bibliográficas desde documentos PDF académicos.

## Características

- **Extracción de referencias**: Procesa archivos PDF y extrae referencias bibliográficas usando GROBID
- **Detección de estilo de citación**: Identifica automáticamente el estilo de citación utilizado:
  - IEEE (Institute of Electrical and Electronics Engineers)
  - APA (American Psychological Association)
  - Vancouver (Estilo médico)
  - Harvard
  - Chicago
  - MLA (Modern Language Association)
- **Análisis estructurado**: Extrae información estructurada de cada referencia (autores, título, año, publicación, etc.)
- **API REST**: Interfaz RESTful para integración con aplicaciones frontend

## Tecnologías

- **FastAPI**: Framework web moderno y de alto rendimiento
- **Python 3.x**: Lenguaje de programación
- **GROBID**: Servicio de extracción de referencias bibliográficas
- **RegEx**: Análisis de patrones para detección de estilos

## Estructura del Proyecto

```
back_def/
├── app/
│   ├── controllers/        # Controladores de rutas API
│   ├── core/              # Configuración y utilidades centrales
│   ├── services/          # Lógica de negocio
│   │   ├── grobid_service.py                    # Integración con GROBID
│   │   └── citation_style_detector_service.py   # Detección de estilos
│   ├── tests/             # Archivos de prueba
│   └── main.py            # Punto de entrada de la aplicación
├── requirements.txt       # Dependencias del proyecto
└── README.md             # Documentación
```

## Instalación

### Requisitos Previos

- Python 3.8 o superior
- GROBID ejecutándose (por defecto en `http://localhost:8070`)

### Pasos de Instalación

1. Clonar el repositorio:
```bash
git clone <url-del-repositorio>
cd back_def
```

2. Crear entorno virtual:
```bash
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

## Uso

### Iniciar el Servidor

```bash
uvicorn app.main:app --reload
```

El servidor estará disponible en `http://localhost:8000`

### Documentación Interactiva

Una vez iniciado el servidor, accede a:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints Principales

#### Procesar Documento PDF

```http
POST /documents/process
Content-Type: multipart/form-data

file: [archivo.pdf]
```

**Respuesta:**
```json
{
  "referencias": [
    {
      "raw": "Texto original de la referencia",
      "autores": "Apellido I, Apellido2 J",
      "titulo": "Título del artículo",
      "año": "2021",
      "publicacion": "Nombre de la revista",
      "volumen": "12",
      "paginas": "464-74"
    }
  ],
  "estilo_citacion": "Vancouver",
  "total_referencias": 20
}
```

## Detección de Estilos de Citación

El sistema utiliza patrones RegEx avanzados para identificar el estilo de citación:

### IEEE
- Referencias numeradas con corchetes: `[1]`, `[2]`
- Uso de "et al.", "pp.", "vol.", "no."
- Comillas en títulos sin paréntesis en año

### Vancouver
- Referencias numeradas: `1.`, `2.`
- Formato de autor: `Apellido Inicial` (sin coma entre ellos)
- Año con punto y coma: `2021; 398:`
- Volumen y páginas: `12:464-74`
- Revistas médicas abreviadas: Lancet, JAMA, BMJ, etc.

### APA
- Año entre paréntesis seguido de punto: `(2024).`
- Formato: `Autor, A. (Año). Título.`

### Harvard
- Año entre paréntesis SIN punto: `(2024)`
- Formato: `Autor, A. (Año) Título`

## Configuración GROBID

El servicio GROBID debe estar ejecutándose para el procesamiento de PDFs. 

Para iniciar GROBID localmente:
```bash
docker run -d -p 8070:8070 lfoppiano/grobid:0.7.3
```

O modificar la URL en `app/core/config.py` si GROBID está en otro servidor.

## Desarrollo

### Ejecutar en Modo Desarrollo

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Estructura de Servicios

- **grobid_service.py**: Comunicación con GROBID para extracción de referencias
- **citation_style_detector_service.py**: Análisis de patrones y detección de estilos

## Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/NuevaCaracteristica`)
3. Commit tus cambios (`git commit -m 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/NuevaCaracteristica`)
5. Abre un Pull Request

## Licencia

[Especificar licencia]

## Contacto

[Tu información de contacto]
