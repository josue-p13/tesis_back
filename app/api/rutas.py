from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.modelos.schemas import ResultadoAnalisis, TipoNorma, CitaDetalle
from app.servicios.extractor_texto import extraer_texto
from app.servicios.analizador_normas import analizar_norma
from app.servicios.servicio_grobid import procesar_pdf_grobid, procesar_cita_grobid, extraer_referencias_de_xml
from app.servicios.clasificador_estilos import clasificar_estilo_local
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal
from app.utils.generador_reporte import generar_reporte_txt, generar_reporte_estructurado
from app.utils.extractor_referencias import extraer_referencias_del_texto
from typing import Optional

router = APIRouter(prefix="/api", tags=["análisis"])

@router.post("/analizar", response_model=ResultadoAnalisis)
async def analizar_documento(
    archivo: UploadFile = File(...),
    norma: Optional[TipoNorma] = Query(None, description="Norma a validar (opcional). Si no se especifica, se valida contra el estilo detectado automáticamente")
):
    if not archivo.filename.endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF o Word")
    
    ruta_temp = None
    try:
        contenido = await archivo.read()
        ruta_temp = guardar_archivo_temporal(contenido, archivo.filename)
        
        texto = extraer_texto(ruta_temp)
        
        # Procesar con GROBID si es PDF
        datos_grobid = None
        if archivo.filename.endswith('.pdf'):
            datos_grobid = await procesar_pdf_grobid(ruta_temp)
            if datos_grobid and datos_grobid.get("status") == "success":
                print("[GROBID] Análisis exitoso")
            else:
                print(f"[GROBID] Error: {datos_grobid.get('error', 'No disponible') if datos_grobid else 'Sin respuesta'}")
        
        # Extraer referencias del texto
        referencias_texto = extraer_referencias_del_texto(texto)
        clasificacion = clasificar_estilo_local(referencias_texto)
        estilo_detectado = clasificacion["estilo"]
        
        # Si no se especificó norma, usar el estilo detectado
        if norma is None:
            if estilo_detectado in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER"]:
                norma = TipoNorma.IEEE
            elif estilo_detectado == "HARVARD":
                norma = TipoNorma.HARVARD
            else:
                norma = TipoNorma.APA
        
        # Crear resultado base con las referencias del texto
        resultado = analizar_norma(referencias_texto, norma)
        resultado.estilo_detectado = estilo_detectado
        
        # Advertir si hay discrepancia
        if ((norma == TipoNorma.APA and estilo_detectado not in ["APA", "DESCONOCIDO"]) or
            (norma == TipoNorma.HARVARD and estilo_detectado not in ["HARVARD", "DESCONOCIDO"]) or
            (norma == TipoNorma.IEEE and estilo_detectado not in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER", "DESCONOCIDO"])):
            advertencia = f"Estilo detectado ({estilo_detectado}) difiere de la norma validada ({norma.value.upper()}). "
            resultado.detalles = advertencia + resultado.detalles

        referencias_estructuradas = []

        if datos_grobid and datos_grobid.get("status") == "success":
            xml_content = datos_grobid.get("xml", "")
            referencias_grobid = extraer_referencias_de_xml(xml_content)
            
            if referencias_grobid:
                print(f"[GROBID-XML] {len(referencias_grobid)} referencias extraídas del XML")
                
                # GROBID es la fuente de verdad: sincronizar ambos reportes
                resultado.referencias_completas = []
                resultado.citas_validas = []
                
                for ref_data in referencias_grobid:
                    texto_ref = ref_data.get("raw", "").strip()
                    
                    # Si no hay texto raw, construir texto desde los campos disponibles
                    if not texto_ref:
                        partes = []
                        if ref_data.get("autores"):
                            partes.append(", ".join(ref_data["autores"]))
                        if ref_data.get("año"):
                            partes.append(f"({ref_data['año']})")
                        if ref_data.get("titulo"):
                            partes.append(ref_data["titulo"])
                        texto_ref = " ".join(partes) if partes else ""
                    
                    if texto_ref:
                        resultado.referencias_completas.append(texto_ref)
                        resultado.citas_validas.append(CitaDetalle(texto=texto_ref, valida=True))
                    
                    ref_data["status"] = "success"
                    ref_data["texto_original"] = texto_ref or "N/A"
                    referencias_estructuradas.append(ref_data)
                
                resultado.total_citas = len(resultado.citas_validas)
                resultado.detalles = f"Referencias extraídas: {resultado.total_citas}"
            else:
                print("[GROBID-XML] Sin referencias en XML, usando fallback")
        
        if not referencias_estructuradas:
            print(f"[FALLBACK] Procesando {len(resultado.referencias_completas)} referencias individualmente...")
            for ref_texto in resultado.referencias_completas:
                ref_estructurada = await procesar_cita_grobid(ref_texto)
                referencias_estructuradas.append(ref_estructurada)
        
        # Generar reportes
        ruta_reporte_original = generar_reporte_txt(resultado, archivo.filename)
        ruta_reporte_estructurado = generar_reporte_estructurado(referencias_estructuradas, archivo.filename)
        resultado.archivo_reporte = ruta_reporte_original

        # Resumen en consola
        print(f"\n{'='*70}")
        print(f"Archivo: {archivo.filename}")
        print(f"Estilo detectado: {estilo_detectado}")
        print(f"Norma: {norma.value.upper()} | Cumple: {'✓' if resultado.cumple else '✗'}")
        print(f"Referencias: {resultado.total_citas} | Errores: {len(resultado.errores)}")
        print(f"Reportes: {ruta_reporte_original.split('/')[-1]} | {ruta_reporte_estructurado.split('/')[-1]}")
        print(f"{'='*70}\n")
        
        return resultado
        
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    finally:
        if ruta_temp:
            eliminar_archivo_temporal(ruta_temp)
