from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Dict, Any

from app.services.document_service import extraer_referencias_grobid
from app.services.file_generator_service import generar_txt_referencias, generar_txt_resumen, generar_txt_validacion
from app.services.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo
from app.services.database_service import DatabaseService
from app.services.validacion_referencias_service import validar_referencias


router = APIRouter()


@router.post("/extraer-referencias")
async def extraer_referencias(
    pdf: UploadFile = File(...), 
    guardar_en_bd: bool = Query(True, description="Guardar referencias en base de datos"),
    validar: bool = Query(True, description="Validar referencias")
) -> Dict[str, Any]:
    if pdf.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail="El archivo debe ser un PDF"
        )
    
    try:
        # Extraer referencias y guardar en BD
        referencias_extraidas, estadisticas_bd = await extraer_referencias_grobid(pdf, guardar_en_bd)
        
        # Detectar estilo de citación
        estilo_citacion = detectar_estilo_citacion(referencias_extraidas)
        descripcion_estilo = obtener_descripcion_estilo(estilo_citacion)
        
        # Generar archivos TXT
        nombre_base = (pdf.filename or "documento").replace('.pdf', '')
        
        # Archivo completo con todos los detalles
        nombre_txt_completo = f"referencias_{nombre_base}.txt"
        ruta_completo = generar_txt_referencias(referencias_extraidas, nombre_txt_completo)
        
        # Archivo resumido solo con autores, título, publicación y año
        nombre_txt_resumen = f"resumen_{nombre_base}.txt"
        ruta_resumen = generar_txt_resumen(referencias_extraidas, nombre_txt_resumen)
        
        response = {
            "total_referencias": len(referencias_extraidas),
            "estilo_citacion": {
                "nombre": estilo_citacion,
                "descripcion": descripcion_estilo
            },
            "referencias": referencias_extraidas,
            "archivos_generados": {
                "completo": ruta_completo,
                "resumen": ruta_resumen
            }
        }
        
        # Agregar estadísticas de BD si se guardaron referencias
        if guardar_en_bd and estadisticas_bd:
            response["base_de_datos"] = estadisticas_bd

        # Si validar=True, usa las referencias ya extraídas directamente — sin construir JSON a mano
        if validar and referencias_extraidas:
            resultado_validacion = await validar_referencias(referencias_extraidas)
            nombre_txt_validacion = f"validacion_{nombre_base}.txt"
            ruta_validacion = generar_txt_validacion(resultado_validacion, nombre_txt_validacion)
            response["archivos_generados"]["validacion"] = ruta_validacion
            response["validacion"] = resultado_validacion
        
        return response
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento: {str(e)}"
        )


@router.get("/referencias")
async def listar_referencias(
    query: str = Query("", description="Búsqueda por texto"),
    limit: int = Query(100, description="Número máximo de resultados", ge=1, le=500),
    offset: int = Query(0, description="Offset para paginación", ge=0)
) -> Dict[str, Any]:
    """
    Lista las referencias almacenadas en la base de datos.
    
    Args:
        query: Texto de búsqueda (busca en título, autores, publicación)
        limit: Número máximo de resultados
        offset: Offset para paginación
        
    Returns:
        JSON con las referencias encontradas
    """
    try:
        with DatabaseService() as db:
            referencias = db.buscar_referencias(query, limit, offset)
            
        return {
            "total_resultados": len(referencias),
            "query": query,
            "limit": limit,
            "offset": offset,
            "referencias": referencias
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al buscar referencias: {str(e)}"
        )


@router.get("/estadisticas")
async def obtener_estadisticas() -> Dict[str, Any]:
    """
    Obtiene estadísticas de las referencias almacenadas.
    
    Returns:
        JSON con estadísticas
    """
    try:
        with DatabaseService() as db:
            estadisticas = db.obtener_estadisticas()
            
        return estadisticas
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener estadísticas: {str(e)}"
        )


