from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modelos.schemas import ResultadoAnalisis, TipoNorma
from app.servicios.extractor_texto import extraer_texto
from app.servicios.analizador_normas import analizar_norma_apa, analizar_norma_ieee
from app.servicios.servicio_grobid import procesar_pdf_grobid
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal
from app.utils.generador_reporte import generar_reporte_txt
import re
from typing import List

router = APIRouter(prefix="/api", tags=["análisis"])

@router.post("/analizar/{norma}", response_model=ResultadoAnalisis)
async def analizar_documento(norma: TipoNorma, archivo: UploadFile = File(...)):
    if not archivo.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF o Word")
    
    ruta_temp = None
    try:
        contenido = await archivo.read()
        ruta_temp = guardar_archivo_temporal(contenido, archivo.filename)
        
        texto = extraer_texto(ruta_temp)
        
        # Intentar procesar con GROBID si es PDF
        datos_grobid = None
        if archivo.filename.endswith('.pdf'):
            datos_grobid = await procesar_pdf_grobid(ruta_temp)
            if datos_grobid.get("status") == "success":
                print("GROBID: Análisis exitoso")
            else:
                print(f"GROBID: {datos_grobid.get('error', 'No disponible')}, usando análisis básico")
        
        if norma == TipoNorma.APA:
            resultado = analizar_norma_apa(texto, datos_grobid)
        else:
            resultado = analizar_norma_ieee(texto, datos_grobid)
        
        # Generar reporte TXT
        ruta_reporte = generar_reporte_txt(resultado, archivo.filename)
        resultado.archivo_reporte = ruta_reporte
        
        # Imprimir resultado en consola
        print(f"\n{'='*50}")
        print(f"ANÁLISIS DE DOCUMENTO: {archivo.filename}")
        print(f"NORMA: {resultado.norma.value.upper()}")
        print(f"CUMPLE: {'SÍ' if resultado.cumple else 'NO'}")
        print(f"DETALLES: {resultado.detalles}")
        print(f"TOTAL CITAS: {resultado.total_citas}")
        print(f"  - Válidas: {len(resultado.citas_validas)}")
        print(f"  - Inválidas: {len(resultado.citas_invalidas)}")
        if resultado.errores:
            print(f"ERRORES ENCONTRADOS:")
            for error in resultado.errores:
                print(f"  - {error}")
        print(f"REPORTE GENERADO: {ruta_reporte}")
        print(f"{'='*50}\n")
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    finally:
        if ruta_temp:
            eliminar_archivo_temporal(ruta_temp)

def extraer_referencias_del_texto(texto: str) -> List[str]:
    """Extrae SOLO referencias bibliográficas reales de la sección de bibliografía"""
    referencias = []
    
    # Buscar sección de referencias (puede tener varios nombres)
    patrones_seccion = [
        r'(?:^|\n)\s*REFERENCIAS\s*\n(.*?)(?:\n\s*(?:ANEXO|AP[ÉE]NDICE|AUTOR|FIRMA|NOTA|FIN|=+)|\Z)',
        r'(?:^|\n)\s*BIBLIOGRAF[IÍ]A\s*\n(.*?)(?:\n\s*(?:ANEXO|AP[ÉE]NDICE|AUTOR|FIRMA|NOTA|FIN|=+)|\Z)',
        r'(?:^|\n)\s*REFERENCES\s*\n(.*?)(?:\n\s*(?:ANNEXE?|APPENDIX|AUTHOR|NOTE|END|=+)|\Z)',
        r'(?:^|\n)\s*BIBLIOGRAPHY\s*\n(.*?)(?:\n\s*(?:ANNEXE?|APPENDIX|AUTHOR|NOTE|END|=+)|\Z)'
    ]
    
    seccion_refs = None
    for patron in patrones_seccion:
        match = re.search(patron, texto, re.IGNORECASE | re.DOTALL)
        if match:
            seccion_refs = match.group(1)
            break
    
    if not seccion_refs:
        # Si no encuentra sección explícita, no extraer nada
        return referencias
    
    # Limpiar líneas vacías múltiples
    seccion_refs = re.sub(r'\n\s*\n+', '\n\n', seccion_refs)
    
    # Dividir por líneas y agrupar referencias
    lineas = seccion_refs.split('\n')
    ref_actual = ""
    
    for linea in lineas:
        linea_original = linea
        linea = linea.strip()
        
        # Saltar líneas vacías
        if not linea:
            continue
        
        # Detectar si termina la sección de referencias
        if re.match(r'^(ANEXO|AP[ÉE]NDICE|AUTOR|FIRMA|TUTOR|NOTA|=+)', linea, re.IGNORECASE):
            break
        
        # Detectar si es inicio de nueva referencia bibliográfica
        # CRITERIOS ESTRICTOS:
        # 1. Formato numerado: "1." o "[1]"
        # 2. Apellido(s) seguido de inicial(es) o nombre completo
        # 3. Debe tener patrón de referencia bibliográfica (autor, año, título)
        
        es_inicio_referencia = False
        
        # Formato numerado
        if re.match(r'^\d+\.\s+[A-ZÑ][a-zá-úñü]+,?\s+[A-Z]\.?', linea):
            es_inicio_referencia = True
        # Formato con corchetes IEEE
        elif re.match(r'^\[\d+\]\s+[A-ZÑ][a-zá-úñü]+', linea):
            es_inicio_referencia = True
        # Formato APA: Apellido, I., o Apellido, Nombre.
        elif re.match(r'^[A-ZÑ][a-zá-úñü]+,\s+[A-Z]\.', linea):
            es_inicio_referencia = True
        # Formato: Apellido, A., & Apellido2, B.
        elif re.match(r'^[A-ZÑ][a-zá-úñü]+,\s+[A-Z]\.\s*,?\s*(&|y)\s+[A-ZÑ]', linea):
            es_inicio_referencia = True
        # Organización como autor (ej: "Higher Education Policy Institute")
        elif re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+.*\.\s+\(\d{4}\)', linea):
            es_inicio_referencia = True
        
        # NO es referencia si:
        # - Es un párrafo normal (no tiene estructura de referencia)
        # - Comienza con "En el", "El uso", "La necesidad", etc. (texto narrativo)
        # - No contiene patrones típicos de referencias (año entre paréntesis, punto después del año, etc.)
        
        patron_texto_narrativo = re.match(
            r'^(En\s+el|El\s+uso|La\s+necesidad|Este\s+art|Los\s+LLM|Según|Nota\.|La\s+última|La\s+ingenier)',
            linea,
            re.IGNORECASE
        )
        
        if patron_texto_narrativo:
            es_inicio_referencia = False
        
        # Debe tener indicadores de ser una referencia real:
        # - Año en formato (YYYY) o YYYY. 
        # - Puntos separando elementos
        # - Título entrecomillado o cursiva
        if es_inicio_referencia:
            tiene_estructura_ref = (
                re.search(r'\(\d{4}\)', linea) or  # Año entre paréntesis
                re.search(r'\d{4}\)', linea) or    # Cierre de año
                re.search(r',\s+\d{4}', linea) or  # Coma + año
                re.search(r'\.\s+\(\d{4}', linea)  # Punto + año entre paréntesis
            )
            if not tiene_estructura_ref:
                es_inicio_referencia = False
        
        if es_inicio_referencia:
            # Guardar referencia anterior si existe
            if ref_actual:
                ref_limpia = ref_actual.strip()
                # Última validación antes de agregar
                if es_referencia_valida(ref_limpia):
                    referencias.append(ref_limpia)
            ref_actual = linea
        else:
            # Continuar referencia anterior
            if ref_actual:
                ref_actual += " " + linea
    
    # Agregar última referencia
    if ref_actual:
        ref_limpia = ref_actual.strip()
        if es_referencia_valida(ref_limpia):
            referencias.append(ref_limpia)
    
    # Eliminar duplicados manteniendo orden
    referencias_unicas = []
    referencias_vistas = set()
    
    for ref in referencias:
        ref_normalizada = re.sub(r'\s+', ' ', ref.lower().strip())
        if ref_normalizada not in referencias_vistas:
            referencias_vistas.add(ref_normalizada)
            referencias_unicas.append(ref)
    
    return referencias_unicas

def es_referencia_valida(ref: str) -> bool:
    """Valida que un texto sea realmente una referencia bibliográfica"""
    # 1. Debe tener longitud mínima razonable
    if len(ref) < 30:
        return False
    
    # 2. Debe tener un año válido (1900-2099)
    if not re.search(r'\b(19|20)\d{2}\b', ref):
        return False
    
    # 3. Debe tener estructura de referencia (autor + año + algo más)
    # Al menos 2 puntos o comas estructurales
    puntos_estructurales = ref.count('.') + ref.count(',')
    if puntos_estructurales < 2:
        return False
    
    # 4. NO debe ser texto narrativo
    if re.match(r'^(En\s+el|El\s+uso|La\s+necesidad|Este\s+art|Los\s+LLM|Según|La\s+última|La\s+ingenier)', ref, re.IGNORECASE):
        return False
    
    # 5. NO debe contener frases típicas de texto corrido
    frases_texto = [
        'se ha convertido en',
        'han demostrado que',
        'este sistema',
        'la implementación de',
        'es lo que impulsa',
        'operan prediciendo',
        'compromete gravemente',
        'resulta indispensable'
    ]
    for frase in frases_texto:
        if frase in ref.lower():
            return False
    
    return True
