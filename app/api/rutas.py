from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.modelos.schemas import ResultadoAnalisis, TipoNorma
from app.servicios.extractor_texto import extraer_texto
from app.servicios.analizador_normas import analizar_norma_apa, analizar_norma_ieee
from app.servicios.servicio_grobid import procesar_pdf_grobid
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal
from app.utils.generador_reporte import generar_reporte_txt
import re
from typing import List, Optional

router = APIRouter(prefix="/api", tags=["análisis"])

@router.post("/analizar", response_model=ResultadoAnalisis)
async def analizar_documento(
    archivo: UploadFile = File(...),
    norma: Optional[TipoNorma] = Query(None, description="Norma a validar (opcional). Si no se especifica, se valida contra el estilo detectado automáticamente")
):
    if not archivo.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF o Word")
    
    ruta_temp = None
    resultado = None
    try:
        print(f"[DEBUG] Iniciando análisis de {archivo.filename}")
        contenido = await archivo.read()
        ruta_temp = guardar_archivo_temporal(contenido, archivo.filename)
        print(f"[DEBUG] Archivo guardado en: {ruta_temp}")
        
        texto = extraer_texto(ruta_temp)
        print(f"[DEBUG] Texto extraído. Longitud: {len(texto) if texto else 0} caracteres")
        
        # Intentar procesar con GROBID si es PDF
        datos_grobid = None
        ruta_solo_refs = None
        if archivo.filename.endswith('.pdf'):
            # 1. IDENTIFICAR PÁGINA DE INICIO DE REFERENCIAS usando PyMuPDF
            try:
                import fitz
                doc = fitz.open(ruta_temp)
                pagina_referencias = None
                
                # Buscar de atrás hacia adelante (la bibliografía suele estar al final)
                print(f"[OPTIMIZACIÓN] Buscando sección de referencias en {len(doc)} páginas...")
                for i in range(len(doc)-1, -1, -1):
                    texto_pagina = doc[i].get_text()
                    if re.search(r'\b(REFERENCIAS|BIBLIOGRAF[IÍ]A|REFERENCES|BIBLIOGRAPHY)\b', texto_pagina, re.IGNORECASE):
                        pagina_referencias = i
                        print(f"[OPTIMIZACIÓN] Sección de referencias encontrada en página {i+1}")
                        break
                
                # 2. CREAR PDF TEMPORAL SOLO CON LA BIBLIOGRAFÍA
                if pagina_referencias is not None:
                    ruta_solo_refs = ruta_temp.replace(".pdf", "_solo_refs.pdf")
                    nuevo_doc = fitz.open()
                    # Insertar desde la página detectada hasta el final
                    nuevo_doc.insert_pdf(doc, from_page=pagina_referencias, to_page=len(doc)-1)
                    nuevo_doc.save(ruta_solo_refs)
                    nuevo_doc.close()
                    print(f"[OPTIMIZACIÓN] PDF recortado creado: páginas {pagina_referencias+1} a {len(doc)}")
                
                doc.close()
                
                # 3. ENVIAR A GROBID EL RECORTE (o el completo si no se encontró)
                archivo_a_procesar = ruta_solo_refs if ruta_solo_refs else ruta_temp
                print(f"[DEBUG] Enviando {'RECORTE' if ruta_solo_refs else 'PDF COMPLETO'} a GROBID...")
                datos_grobid = await procesar_pdf_grobid(archivo_a_procesar)
                
                # Limpiar el archivo recortado después de usarlo
                if ruta_solo_refs:
                    eliminar_archivo_temporal(ruta_solo_refs)
                    
            except ImportError:
                print("[ADVERTENCIA] PyMuPDF (fitz) no disponible. Procesando PDF completo...")
                datos_grobid = await procesar_pdf_grobid(ruta_temp)
            except Exception as e:
                print(f"[ERROR] Error al recortar PDF: {e}. Procesando PDF completo...")
                datos_grobid = await procesar_pdf_grobid(ruta_temp)
            
            print(f"[DEBUG] Respuesta GROBID: {type(datos_grobid)} - {datos_grobid}")
            if datos_grobid and datos_grobid.get("status") == "success":
                print("GROBID: Análisis exitoso")
            else:
                print(f"GROBID: {datos_grobid.get('error', 'No disponible') if datos_grobid else 'No data'}, usando análisis básico")
        
        # DETECTAR AUTOMÁTICAMENTE EL ESTILO antes de validar
        referencias_texto = extraer_referencias_del_texto(texto)
        from app.servicios.clasificador_estilos import clasificar_estilo_local
        clasificacion = clasificar_estilo_local(referencias_texto)
        estilo_detectado = clasificacion["estilo"]
        confianza = clasificacion["confianza"]
        
        print(f"[AUTO-DETECT] Estilo detectado: {estilo_detectado} (Confianza: {confianza})")
        
        # Si no se especificó norma, usar el estilo detectado
        if norma is None:
            # Mapear el estilo detectado a una norma
            if estilo_detectado in ["APA"]:
                norma = TipoNorma.APA
            elif estilo_detectado in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER"]:
                norma = TipoNorma.IEEE
            else:
                # Por defecto APA si no se detectó claramente
                norma = TipoNorma.APA
            print(f"[AUTO-MODE] No se especificó norma. Validando automáticamente como: {norma.value.upper()}")
        else:
            print(f"[MANUAL-MODE] Norma especificada manualmente: {norma.value.upper()}")
        
        # Validar según la norma (detectada o especificada)
        if norma == TipoNorma.APA:
            resultado = analizar_norma_apa(texto, datos_grobid)
            print(f"[DEBUG] Resultado APA: {type(resultado)} - {resultado}")
        else:
            resultado = analizar_norma_ieee(texto, datos_grobid)
            print(f"[DEBUG] Resultado IEEE: {type(resultado)} - {resultado}")
        
        # Agregar información del estilo detectado al resultado
        resultado.estilo_detectado = estilo_detectado
        
        # Advertir si hay discrepancia entre norma validada y estilo detectado
        if ((norma == TipoNorma.APA and estilo_detectado not in ["APA", "DESCONOCIDO"]) or
            (norma == TipoNorma.IEEE and estilo_detectado not in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER", "DESCONOCIDO"])):
            advertencia = f"⚠️ Estilo detectado ({estilo_detectado}) difiere de la norma validada ({norma.value.upper()}). "
            resultado.detalles = advertencia + resultado.detalles
            print(f"[ADVERTENCIA] {advertencia}")

        # Generar reporte TXT
        ruta_reporte = generar_reporte_txt(resultado, archivo.filename)
        resultado.archivo_reporte = ruta_reporte

        # Imprimir resultado en consola (solo si resultado existe)
        print(f"\n{'='*70}")
        print(f"ANÁLISIS DE DOCUMENTO: {archivo.filename}")
        print(f"ESTILO DETECTADO: {estilo_detectado} (Confianza: {confianza})")
        print(f"NORMA VALIDADA: {norma.value.upper()}")
        print(f"CUMPLE: {'SÍ' if getattr(resultado, 'cumple', None) else 'NO'}")
        print(f"DETALLES: {getattr(resultado, 'detalles', None)}")
        print(f"TOTAL CITAS: {getattr(resultado, 'total_citas', None)}")
        print(f"  - Válidas: {len(getattr(resultado, 'citas_validas', []) or [])}")
        print(f"  - Inválidas: {len(getattr(resultado, 'citas_invalidas', []) or [])}")
        if getattr(resultado, 'errores', None):
            print(f"ERRORES ENCONTRADOS:")
            for error in resultado.errores:
                print(f"  - {error}")
        print(f"REPORTE GENERADO: {ruta_reporte}")
        print(f"{'='*70}\n")
        
        return resultado
        
    except Exception as e:
        print(f"[DEBUG] Excepción en analizar_documento: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    finally:
        if ruta_temp:
            eliminar_archivo_temporal(ruta_temp)

def extraer_referencias_del_texto(texto: str) -> List[str]:
    """
    Extrae referencias bibliográficas del texto del PDF.
    Busca la sección de referencias y extrae cada entrada.
    """
    referencias = []
    
    print("[EXTRACCIÓN] Buscando sección de referencias...")
    
    # Buscar el inicio de la sección de referencias
    patrones_inicio = [
        r'\bREFERENCIAS\b',
        r'\bREFERENCES\b', 
        r'\bBIBLIOGRAFÍA\b',
        r'\bBIBLIOGRAPHY\b'
    ]
    
    inicio_idx = -1
    for patron in patrones_inicio:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            inicio_idx = match.end()
            print(f"[EXTRACCIÓN] Sección encontrada: {match.group()}")
            break
    
    if inicio_idx == -1:
        print("[EXTRACCIÓN] No se encontró sección de referencias")
        return referencias
    
    # Extraer todo el texto desde el inicio de referencias hasta el final o anexos
    texto_desde_refs = texto[inicio_idx:]
    
    # Buscar dónde termina la sección de referencias
    patrones_fin = [
        r'\n\s*(ANEXO|APÉNDICE|APPENDIX|ANNEX)\s',
        r'\n\s*FIRMA',
        r'\n\s*AUTOR(ES)?:',
        r'\n\s*TUTOR'
    ]
    
    fin_idx = len(texto_desde_refs)
    for patron in patrones_fin:
        match = re.search(patron, texto_desde_refs, re.IGNORECASE)
        if match:
            fin_idx = match.start()
            print(f"[EXTRACCIÓN] Fin de sección detectado: {match.group().strip()}")
            break
    
    seccion_refs = texto_desde_refs[:fin_idx]
    print(f"[EXTRACCIÓN] Longitud de sección: {len(seccion_refs)} caracteres")
    
    # Dividir en líneas y limpiar
    lineas = seccion_refs.split('\n')
    
    ref_actual = ""
    contador = 0
    
    for i, linea in enumerate(lineas):
        linea = linea.strip()
        if not linea:
            continue
        
        # Detectar inicio de una nueva referencia
        # Patrón 1: [1], [2], etc. (IEEE/Vancouver)
        # Patrón 2: Apellido, Inicial(es). (APA, Chicago, MLA, etc.)
        # Patrón 3: Autor et al. o & (continuaciones APA)
        
        es_inicio_ieee = re.match(r'^\[\d+\]\s+', linea)
        es_inicio_apa = re.match(r'^[A-Z][a-záéíóúñüA-Z\'\-]+,\s+[A-Z]\.', linea)
        
        # Verificar que no sea un título de sección (evita "1. Modelos de...")
        es_titulo_seccion = re.match(r'^\d+\.\s+[A-Z][a-z]+\s+[a-z]+\s+[A-Z]', linea)
        
        if (es_inicio_ieee or es_inicio_apa) and not es_titulo_seccion:
            # Guardar la referencia anterior si existe
            if ref_actual:
                referencias.append(ref_actual.strip())
                contador += 1
            ref_actual = linea
        else:
            # Continuación de la referencia actual
            if ref_actual:
                ref_actual += " " + linea
    
    # Agregar la última referencia
    if ref_actual:
        referencias.append(ref_actual.strip())
        contador += 1
    
    print(f"[EXTRACCIÓN] Referencias extraídas: {contador}")
    if referencias:
        print(f"[EXTRACCIÓN] Primera referencia: {referencias[0][:100]}...")
        if len(referencias) > 1:
            print(f"[EXTRACCIÓN] Segunda referencia: {referencias[1][:100]}...")
    
    return referencias
