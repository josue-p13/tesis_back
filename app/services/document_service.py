from fastapi import UploadFile
import httpx
from typing import List, Dict

from app.services.xml_parser_service import parsear_referencias_xml


GROBID_URL_BASE = "http://localhost:8070/api"


async def extraer_referencias_grobid(pdf: UploadFile) -> List[Dict[str, str]]:
    """
    Extrae las referencias bibliográficas de un PDF usando GROBID.
    
    Args:
        pdf: Archivo PDF subido
        
    Returns:
        Lista de diccionarios con las referencias extraídas
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
        
        return referencias



