# Extracción de Referencias Completas

## 🎯 Objetivo

Extraer el **texto completo** de TODAS las referencias bibliográficas del documento, independientemente de si están completas o son válidas según las normas APA/IEEE. 

La validación solo sirve para el reporte, pero NO descarta referencias. El texto completo se guarda para procesamiento posterior con modelos de IA.

## 🔄 Cambios Implementados

### 1. Schema `CitaDetalle` (app/modelos/schemas.py)

Se agregó el campo `texto_completo` para guardar el texto original completo:

```python
class CitaDetalle(BaseModel):
    texto: str                          # Resumen o formato corto
    valida: bool                        # Si cumple con la norma
    razon: Optional[str] = None         # Razón de invalidez
    texto_completo: Optional[str] = None  # ✨ NUEVO: Texto completo original
```

### 2. Schema `ResultadoAnalisis` (app/modelos/schemas.py)

Se agregó la lista `referencias_completas` con TODAS las referencias extraídas:

```python
class ResultadoAnalisis(BaseModel):
    cumple: bool
    norma: TipoNorma
    errores: list[str]
    detalles: str
    citas_validas: List[CitaDetalle] = []
    citas_invalidas: List[CitaDetalle] = []
    total_citas: int = 0
    archivo_reporte: Optional[str] = None
    referencias_completas: List[str] = []  # ✨ NUEVO: Lista completa
```

### 3. Analizador de Normas (app/servicios/analizador_normas.py)

Ahora extrae TODAS las referencias del documento usando `extraer_referencias_del_texto()`:

```python
# Extraer TODAS las referencias del texto (sección bibliografía)
from app.api.rutas import extraer_referencias_del_texto
referencias_completas = extraer_referencias_del_texto(texto)
```

Y las incluye en el resultado:

```python
return ResultadoAnalisis(
    # ...otros campos...
    referencias_completas=referencias_completas  # ✨ Lista completa
)
```

### 4. Generador de Reporte (app/utils/generador_reporte.py)

El reporte TXT ahora incluye una sección al final con todas las referencias completas:

```
======================================================================
REFERENCIAS COMPLETAS EXTRAÍDAS (35)
======================================================================

1. Bernal, F., Albarracín, C., Gaona, J., & Nieto, J. (s.f.). ferestrepoca...

2. Date, C. (2001). Introducción a los sistemas de bases de datos...

3. devCamp. (2020). devCamp by Bottega. Obtenido de https://devcamp.es/...
```

## 📊 Ejemplo de Respuesta API

```json
{
  "cumple": true,
  "norma": "apa",
  "errores": [],
  "detalles": "Referencias GROBID: 26. Citas en texto: 38. Válidas: 37, Inválidas: 27",
  "citas_validas": [
    {
      "texto": "Ref: Date, 2001",
      "valida": true,
      "razon": null,
      "texto_completo": "Date C. J. 2001 Introducción a los sistemas de bases de datos..."
    }
  ],
  "citas_invalidas": [
    {
      "texto": "Ref: Sin título...",
      "valida": false,
      "razon": "Falta año",
      "texto_completo": "Microsoft. (s.f.). visual studio code. Obtenido de..."
    }
  ],
  "total_citas": 64,
  "archivo_reporte": "archivos_temp/reporte_documento.pdf_20260125_123456.txt",
  "referencias_completas": [
    "Bernal, F., Albarracín, C., Gaona, J., & Nieto, J. (s.f.). ferestrepoca. Obtenido de http://ferestrepoca.github.io/paradigmas-de-programacion/paralela/paralela_teoria/index.html#twelve",
    "Date, C. (2001). Introducción a los sistemas de bases de datos. Pearson Educación.",
    "devCamp. (2020). devCamp by Bottega. Obtenido de https://devcamp.es/que-es-libreria-programacion/...",
    "... (todas las referencias, incluso incompletas)"
  ]
}
```

## 🔍 Flujo de Procesamiento

```
1. PDF → Extracción de texto (PyPDF)
           ↓
2. Texto → GROBID (análisis estructurado XML)
           ↓
3. XML → Referencias estructuradas (autor, año, título)
           ↓
4. Texto → Sección REFERENCIAS (texto plano completo)
           ↓ (SOLO de la sección bibliografía, NO del cuerpo)
           ↓
5. Filtrado → Elimina duplicados y citas cortas tipo "(Autor, 2020)"
           ↓
6. Validación → Marca válidas/inválidas (NO descarta)
           ↓
7. Resultado → {
                 citas_validas: [...],      # Citas del texto + referencias
                 citas_invalidas: [...],    # Citas del texto + referencias
                 referencias_completas: [...] # SOLO sección bibliografía
               }
```

## ⚠️ Importante: Diferencia entre Citas y Referencias

### Citas en el Texto (cuerpo del documento)
```
"Según Gallego (2012), la metodología..."
"Como menciona INAMHI (2013), los datos..."
"Varios autores (Date, 2001; Sierra, 2015) afirman..."
```
Estas aparecen en `citas_validas` o `citas_invalidas` pero **NO** en `referencias_completas`.

### Referencias Bibliográficas (sección REFERENCIAS)
```
Gallego, M. T. (2012). Metodología scrum. Editorial.
INAMHI, P. (2013). Propuesta para el formato de archivo...
Date, C. (2001). Introducción a los sistemas de bases de datos...
```
Estas aparecen en `referencias_completas` (texto completo).

### Sin Duplicados
El sistema ahora:
- ✅ Detecta y elimina duplicados en `referencias_completas`
- ✅ Filtra citas cortas tipo "(Autor, 2020)" de las referencias completas
- ✅ Solo incluye referencias de mínimo 30 caracteres (referencias reales)
- ✅ Normaliza espacios para evitar duplicados por formato

## 🎓 Casos de Uso

### 1. Entrenamiento de Modelos de IA

```python
# Obtener todas las referencias para entrenar un modelo
response = requests.post(
    "http://localhost:8000/api/analizar/apa",
    files={"archivo": open("tesis.pdf", "rb")}
)

resultado = response.json()

# Todas las referencias completas, incluso las "inválidas"
referencias = resultado["referencias_completas"]

# Enviar a un modelo de NLP
modelo.entrenar(referencias)
```

### 2. Normalización con IA

```python
# Las referencias "inválidas" pueden tener datos útiles
for cita in resultado["citas_invalidas"]:
    texto_original = cita["texto_completo"]
    razon = cita["razon"]
    
    # Usar IA para intentar completar la referencia
    if "Falta año" in razon:
        año_predicho = modelo_ia.predecir_año(texto_original)
        referencia_corregida = agregar_año(texto_original, año_predicho)
```

### 3. Análisis de Calidad

```python
# Obtener todas las referencias y analizar patrones
total_refs = len(resultado["referencias_completas"])
total_validas = len(resultado["citas_validas"])
total_invalidas = len(resultado["citas_invalidas"])

tasa_validez = (total_validas / total_refs) * 100
print(f"Calidad de referencias: {tasa_validez}%")

# Ver qué tipos de errores son más comunes
errores = {}
for cita in resultado["citas_invalidas"]:
    razon = cita["razon"]
    errores[razon] = errores.get(razon, 0) + 1

print("Errores más comunes:", errores)
```

## ✅ Ventajas

1. **No se pierde información**: Incluso referencias incompletas se guardan
2. **Texto completo disponible**: Para procesamiento posterior con IA
3. **Validación informativa**: Sabes qué está mal pero no descartas datos
4. **Flexible**: Puedes decidir qué hacer con referencias inválidas después
5. **Ideal para ML**: Tienes dataset completo para entrenar modelos

## 📝 Ejemplo Práctico

Si el documento tiene esta referencia incompleta:

```
Microsoft. (s.f.). visual studio code. Obtenido de https://code.visualstudio.com/docs
```

### Antes (solo validación):
- ❌ Se marca como inválida
- ❌ Se guarda solo "Ref: Sin título..."
- ❌ Se pierde el texto completo

### Ahora (extracción completa):
- ✅ Se marca como inválida
- ✅ Se guarda "Ref: Sin título..." (resumen)
- ✅ Se guarda texto completo en `texto_completo`
- ✅ Se incluye en `referencias_completas`
- ✅ Puedes usarla para entrenar un modelo que prediga el año

## 🚀 Cómo Probar

```bash
# 1. Analizar documento
curl -X POST "http://localhost:8000/api/analizar/apa" \
  -F "archivo=@documento.pdf"

# 2. Verificar en la respuesta JSON
{
  "referencias_completas": [
    "Primera referencia completa...",
    "Segunda referencia completa (incluso sin año)...",
    "Tercera referencia completa..."
  ]
}

# 3. Revisar el reporte TXT generado
# Tendrá una sección "REFERENCIAS COMPLETAS EXTRAÍDAS"
```

## 🔧 Configuración

No requiere configuración adicional. Los cambios son automáticos en:
- ✅ Endpoint `/api/analizar/{norma}`
- ✅ Reporte TXT generado
- ✅ Respuesta JSON

## 💡 Tips

1. **Filtrado posterior**: Puedes filtrar `referencias_completas` según tus necesidades
2. **Combinación de fuentes**: Las referencias vienen de GROBID + extracción de texto
3. **Duplicados**: Puede haber duplicados entre referencias válidas/inválidas y referencias_completas
4. **Procesamiento con IA**: Usa `referencias_completas` como dataset de entrada
5. **Validación customizada**: Puedes crear tus propias reglas de validación

## 📚 Recursos Relacionados

- [NUEVAS_FUNCIONALIDADES.md](NUEVAS_FUNCIONALIDADES.md) - Mejoras en GROBID
- [README.md](README.md) - Documentación general
- API Docs: http://localhost:8000/docs
