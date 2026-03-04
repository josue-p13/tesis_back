from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.modelos.schemas import ResultadoAnalisis, TipoNorma, CitaDetalle
from app.servicios.analizador_normas import analizar_norma
from app.servicios.servicio_grobid import procesar_pdf_grobid, extraer_referencias_de_xml
from app.servicios.clasificador_estilos import clasificar_estilo_local
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal
from app.utils.generador_reporte import generar_reporte_txt, generar_reporte_estructurado
from typing import Optional

router = APIRouter(prefix="/api", tags=["análisis"])

@router.post("/analizar", response_model=ResultadoAnalisis)
async def analizar_documento(
    archivo: UploadFile = File(...),
    norma: Optional[TipoNorma] = Query(None, description="Norma a validar (opcional). Si no se especifica, se valida contra el estilo detectado automáticamente")
):
    if not archivo.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
    
    ruta_temp = None
    try:
        contenido = await archivo.read()
        ruta_temp = guardar_archivo_temporal(contenido, archivo.filename)
        
        # --- PASO 1: Procesar con GROBID ---
        datos_grobid = await procesar_pdf_grobid(ruta_temp)
        
        if not datos_grobid or datos_grobid.get("status") != "success":
            error_msg = datos_grobid.get('error', 'No disponible') if datos_grobid else 'Sin respuesta'
            raise HTTPException(status_code=502, detail=f"Error de GROBID: {error_msg}")
        
        xml_content = datos_grobid.get("xml", "")
        referencias_grobid = extraer_referencias_de_xml(xml_content)
        
        if not referencias_grobid:
            raise HTTPException(status_code=422, detail="GROBID no pudo extraer referencias del PDF")
        
        print(f"[GROBID] {len(referencias_grobid)} referencias extraídas")
        
        # --- PASO 2: Construir listas de texto y estructuradas ---
        referencias_texto = []
        referencias_estructuradas = []
        
        for ref_data in referencias_grobid:
            texto_ref = ref_data.get("raw", "").strip()
            
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
                referencias_texto.append(texto_ref)
            
            ref_data["status"] = "success"
            ref_data["texto_original"] = texto_ref or "N/A"
            referencias_estructuradas.append(ref_data)
        
        # --- PASO 3: Clasificar estilo ---
        clasificacion = clasificar_estilo_local(referencias_texto)
        estilo_detectado = clasificacion["estilo"]
        
        if norma is None:
            if estilo_detectado in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER"]:
                norma = TipoNorma.IEEE
            elif estilo_detectado == "HARVARD":
                norma = TipoNorma.HARVARD
            else:
                norma = TipoNorma.APA
        
        # --- PASO 4: Crear resultado ---
        resultado = analizar_norma(referencias_texto, norma)
        resultado.estilo_detectado = estilo_detectado
        
        if ((norma == TipoNorma.APA and estilo_detectado not in ["APA", "DESCONOCIDO"]) or
            (norma == TipoNorma.HARVARD and estilo_detectado not in ["HARVARD", "DESCONOCIDO"]) or
            (norma == TipoNorma.IEEE and estilo_detectado not in ["IEEE", "IEEE/VANCOUVER", "VANCOUVER", "DESCONOCIDO"])):
            advertencia = f"Estilo detectado ({estilo_detectado}) difiere de la norma validada ({norma.value.upper()}). "
            resultado.detalles = advertencia + resultado.detalles
        
        # --- PASO 5: Generar reportes ---
        ruta_reporte_original = generar_reporte_txt(resultado, archivo.filename)
        ruta_reporte_estructurado = generar_reporte_estructurado(referencias_estructuradas, archivo.filename)
        resultado.archivo_reporte = ruta_reporte_original

        print(f"\n{'='*70}")
        print(f"Archivo: {archivo.filename}")
        print(f"Estilo detectado: {estilo_detectado}")
        print(f"Norma: {norma.value.upper()} | Cumple: {'✓' if resultado.cumple else '✗'}")
        print(f"Referencias: {resultado.total_citas} | Errores: {len(resultado.errores)}")
        print(f"Reportes: {ruta_reporte_original.split('/')[-1]} | {ruta_reporte_estructurado.split('/')[-1]}")
        print(f"{'='*70}\n")
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    finally:
        if ruta_temp:
            eliminar_archivo_temporal(ruta_temp)
