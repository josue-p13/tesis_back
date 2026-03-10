from fastapi import UploadFile
import httpx
from typing import List, Dict, Tuple

from app.services.xml_parser_service import parsear_referencias_xml
from app.services.database_service import DatabaseService
from app.core.config import config


GROBID_URL_BASE = config.GROBID_URL + "/api"


async def extraer_referencias_grobid(pdf: UploadFile, guardar_en_bd: bool = True) -> Tuple[List[Dict[str, str]], Dict]:
    """
    Extrae las referencias bibliográficas de un PDF usando GROBID.
    Opcionalmente guarda las referencias en la base de datos.
    
    Args:
        pdf: Archivo PDF subido
        guardar_en_bd: Si es True, guarda las referencias en la base de datos
        
    Returns:
        Tupla de (referencias_extraidas, estadisticas_bd)
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        contenido_pdf = await pdf.read()
        
        # Endpoint específico para procesar referencias
        endpoint = f"{GROBID_URL_BASE}/processReferences"
        
        files = {"input": (pdf.filename, contenido_pdf, "application/pdf")}
        
        # IMPORTANTE: includeRawCitations=1 hace que GROBID incluya el texto original
        # de cada referencia en el campo <note type="raw_reference">
        # Esto es CRUCIAL para detectar el estilo de citación (Harvard vs APA, etc.)
        data = {"includeRawCitations": "1"}
        
        response = await client.post(endpoint, files=files, data=data)
        response.raise_for_status()
        
        # GROBID devuelve XML, lo parseamos
        xml_contenido = response.text
        referencias = parsear_referencias_xml(xml_contenido)
        
        # Guardar en base de datos si está habilitado
        estadisticas_bd = {}
        if guardar_en_bd and referencias:
            try:
                with DatabaseService() as db:
                    estadisticas_bd = db.guardar_multiples_referencias(
                        referencias, 
                        fuente_documento=pdf.filename or "documento_sin_nombre.pdf"
                    )
            except Exception as e:
                print(f"Error al guardar referencias en BD: {e}")
                estadisticas_bd = {"error": str(e)}
        
        return referencias, estadisticas_bd



