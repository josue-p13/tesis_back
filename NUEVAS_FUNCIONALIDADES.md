# Nuevas Funcionalidades - Mejoras en GROBID y Comparación de Referencias

## 🚀 Cambios Implementados

### 1. Mejoras en el Servicio GROBID

Se han implementado mejoras significativas en la extracción de referencias usando GROBID:

#### Características mejoradas:
- **Múltiples endpoints**: Ahora usa tanto `/api/processFulltextDocument` como `/api/processReferences` para mejor extracción
- **Parámetros de consolidación**: Activa consolidación de citas y referencias para mayor precisión
- **Parsing XML robusto**: Usa `xml.etree.ElementTree` con fallback a regex
- **Extracción mejorada**: Extrae autores, años y títulos de manera más precisa
- **Timeout aumentado**: De 30 a 60 segundos para documentos grandes

#### Archivos modificados:
- `app/servicios/servicio_grobid.py`

### 2. Nuevo Endpoint: Comparación de Referencias

Se ha agregado un nuevo endpoint para comparar las referencias del PDF con las detectadas por GROBID.

#### Endpoint:
```
POST /api/comparar-referencias
```

#### Descripción:
Compara las referencias extraídas directamente del texto del PDF con las que GROBID detectó en formato estructurado.

#### Request:
```bash
curl -X POST "http://localhost:8000/api/comparar-referencias" \
  -H "Content-Type: multipart/form-data" \
  -F "archivo=@tu_documento.pdf"
```

#### Response:
```json
{
  "total_referencias_texto": 35,
  "total_referencias_grobid": 26,
  "referencias_detectadas": [
    {
      "referencia_original": "Date, C. (2001). Introducción a los sistemas de bases de datos...",
      "referencia_grobid": {
        "autores": ["Date"],
        "año": "2001",
        "titulo": "Introducción a los sistemas de bases de datos"
      },
      "similitud": 0.9
    }
  ],
  "referencias_no_detectadas": [
    "Bernal, F., Albarracín, C., Gaona, J., & Nieto, J. (s.f.)...",
    "Microsoft. (s.f.). visual studio code..."
  ],
  "referencias_parciales": [
    "M, P., L, R., & F, F. (2017). Administración de base de datos..."
  ],
  "tasa_deteccion": 74.29
}
```

#### Archivos modificados:
- `app/api/rutas.py` - Nuevo endpoint y funciones auxiliares
- `app/modelos/schemas.py` - Nuevo modelo `ComparacionReferencias`

### 3. Algoritmo de Similitud

El endpoint usa un algoritmo de similitud que compara:
- **Autores** (40% del peso)
- **Año** (30% del peso)
- **Título** (30% del peso)

#### Umbrales:
- Similitud >= 0.8: Referencia detectada correctamente
- Similitud >= 0.5: Referencia parcialmente detectada
- Similitud < 0.5: Referencia no detectada

## 📝 Funciones Auxiliares Agregadas

### `extraer_referencias_del_texto(texto: str) -> List[str]`
Extrae referencias de la sección de bibliografía del documento. Busca patrones como:
- REFERENCIAS
- BIBLIOGRAFÍA
- REFERENCES
- BIBLIOGRAPHY

### `calcular_similitud_referencias(ref_texto: str, ref_grobid: Dict) -> float`
Calcula el índice de similitud entre una referencia de texto plano y una referencia estructurada de GROBID.

### `normalizar_referencia(ref: Dict) -> str`
Normaliza una referencia a formato "Autor, Año" para facilitar comparaciones.

## 🧪 Cómo Probar

### 1. Asegúrate de que GROBID esté corriendo:
```bash
cd tesis_APIs_locales
docker-compose up -d
```

### 2. Inicia el backend:
```bash
cd tesis_back
python main.py
```

### 3. Prueba el endpoint de comparación:
```bash
# Usando curl
curl -X POST "http://localhost:8000/api/comparar-referencias" \
  -F "archivo=@UPS-TTS974.pdf"

# O desde Python
import requests

with open("UPS-TTS974.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/comparar-referencias",
        files={"archivo": f}
    )
    print(response.json())
```

### 4. Prueba el endpoint de análisis mejorado:
```bash
curl -X POST "http://localhost:8000/api/analizar/apa" \
  -F "archivo=@UPS-TTS974.pdf"
```

## 📊 Resultados Esperados

Con las mejoras implementadas, deberías ver:
- **Mayor tasa de detección** de referencias (de ~74% a potencialmente 80-90%)
- **Mejor extracción** de autores, años y títulos
- **Análisis detallado** de qué referencias faltan o están parcialmente detectadas
- **Información útil** para mejorar el documento o ajustar el procesamiento

## 🔧 Próximas Mejoras Recomendadas

1. **Post-procesamiento inteligente**: Limpiar y normalizar referencias antes de comparar
2. **Machine Learning**: Entrenar modelos personalizados para tu tipo de documentos
3. **OCR mejorado**: Si trabajas con PDFs escaneados, usar Tesseract u otro OCR antes de GROBID
4. **Cache de resultados**: Guardar resultados de GROBID para no reprocesar documentos
5. **Interfaz web**: Crear un frontend para visualizar las comparaciones

## 💡 Notas Importantes

- GROBID funciona mejor con PDFs generados digitalmente que con escaneos
- La calidad del PDF afecta significativamente la tasa de detección
- Referencias con formato no estándar son más difíciles de detectar
- El endpoint de comparación NO modifica el documento, solo analiza

## 🐛 Troubleshooting

### GROBID no responde
```bash
# Verificar que Docker esté corriendo
docker ps

# Reiniciar GROBID
cd tesis_APIs_locales
docker-compose restart

# Ver logs
docker-compose logs -f
```

### Error de timeout
Si tienes documentos muy grandes, puedes aumentar el timeout en `servicio_grobid.py`:
```python
async with httpx.AsyncClient(timeout=120.0) as client:  # Aumentar de 60 a 120
```

### Baja tasa de detección
- Verifica que el PDF tenga una sección de referencias clara
- Revisa que los nombres de sección sean estándar (REFERENCIAS, BIBLIOGRAFÍA, etc.)
- Considera limpiar el PDF antes de procesarlo

## 📚 Documentación Relacionada

- [GROBID Documentation](https://grobid.readthedocs.io/)
- [GROBID REST API](https://grobid.readthedocs.io/en/latest/Grobid-service/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
