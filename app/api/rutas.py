from fastapi import APIRouter, UploadFile, File, HTTPException
from app.modelos.schemas import ResultadoAnalisis, TipoNorma
from app.servicios.extractor_texto import extraer_texto
from app.servicios.analizador_normas import analizar_norma_apa, analizar_norma_ieee
from app.utils.archivo_helper import guardar_archivo_temporal, eliminar_archivo_temporal

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
        
        if norma == TipoNorma.APA:
            resultado = analizar_norma_apa(texto)
        else:
            resultado = analizar_norma_ieee(texto)
        
        # Imprimir resultado en consola
        print(f"\n{'='*50}")
        print(f"ANÁLISIS DE DOCUMENTO: {archivo.filename}")
        print(f"NORMA: {resultado.norma.value.upper()}")
        print(f"CUMPLE: {'SÍ' if resultado.cumple else 'NO'}")
        print(f"DETALLES: {resultado.detalles}")
        if resultado.errores:
            print(f"ERRORES ENCONTRADOS:")
            for error in resultado.errores:
                print(f"  - {error}")
        print(f"{'='*50}\n")
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar archivo: {str(e)}")
    finally:
        if ruta_temp:
            eliminar_archivo_temporal(ruta_temp)
