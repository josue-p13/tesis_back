from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modelos.schemas import ResultadoAnalisis, TipoNorma
from app.servicios.extractor_texto import extraer_texto
from app.servicios.analizador_normas import analizar_norma_apa, analizar_norma_ieee
from app.servicios.servicio_grobid import procesar_pdf_grobid
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal
from app.utils.generador_reporte import generar_reporte_txt

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
