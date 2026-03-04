from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any

from app.services.document_service import extraer_referencias_grobid
from app.services.file_generator_service import generar_txt_referencias, generar_txt_resumen
from app.services.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo


router = APIRouter()


@router.post("/extraer-referencias")
async def extraer_referencias(pdf: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Extrae las referencias bibliográficas de un PDF usando GROBID 
    y genera 2 archivos TXT: uno completo y otro resumido.
    
    Args:
        pdf: Archivo PDF a procesar
        
    Returns:
        JSON con las referencias y rutas de archivos generados
    """
    # Validar que sea un PDF
    if pdf.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail="El archivo debe ser un PDF"
        )
    
    try:
        # Extraer referencias
        referencias = await extraer_referencias_grobid(pdf)
        
        # Detectar estilo de citación
        estilo_citacion = detectar_estilo_citacion(referencias)
        descripcion_estilo = obtener_descripcion_estilo(estilo_citacion)
        
        # Generar archivos TXT
        nombre_base = pdf.filename.replace('.pdf', '')
        
        # Archivo completo con todos los detalles
        nombre_txt_completo = f"referencias_{nombre_base}.txt"
        ruta_completo = generar_txt_referencias(referencias, nombre_txt_completo)
        
        # Archivo resumido solo con autores, título, publicación y año
        nombre_txt_resumen = f"resumen_{nombre_base}.txt"
        ruta_resumen = generar_txt_resumen(referencias, nombre_txt_resumen)
        
        return {
            "total_referencias": len(referencias),
            "estilo_citacion": {
                "nombre": estilo_citacion,
                "descripcion": descripcion_estilo
            },
            "referencias": referencias,
            "archivos_generados": {
                "completo": ruta_completo,
                "resumen": ruta_resumen
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento: {str(e)}"
        )
