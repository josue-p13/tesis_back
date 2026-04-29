from fastapi import UploadFile
import httpx
from typing import List, Dict, Tuple
import re

import fitz

from app.services.obtener.xml_parser_service import parsear_referencias_xml
from app.services.db.database_service import DatabaseService
from app.core.config import config


GROBID_URL_BASE = config.GROBID_URL + "/api"


_REFERENCIAS_HEADER_RE = re.compile(
    r"(?im)^\s*(?:references|referencias|bibliograf[ií]a|literature\s+cited|works\s+cited|cited\s+literature)\s*$"
)


def segmentar_pdf_para_referencias(
    contenido_pdf: bytes,
    *,
    scan_last_pages: int = 35,
    fallback_last_pages: int = 20,
) -> bytes:
    if not contenido_pdf:
        return contenido_pdf

    try:
        doc = fitz.open(stream=contenido_pdf, filetype="pdf")
    except Exception:
        return contenido_pdf

    try:
        total_paginas = doc.page_count
        if total_paginas <= 1:
            return contenido_pdf

        inicio_scan = max(0, total_paginas - max(1, scan_last_pages))
        pagina_inicio = None

        for i in range(inicio_scan, total_paginas):
            texto = doc.load_page(i).get_text("text") or ""
            if _REFERENCIAS_HEADER_RE.search(texto):
                pagina_inicio = i
                break

        if pagina_inicio is None:
            pagina_inicio = max(0, total_paginas - max(1, fallback_last_pages))

        if pagina_inicio <= 0:
            return contenido_pdf

        recortado = fitz.open()
        recortado.insert_pdf(doc, from_page=pagina_inicio, to_page=total_paginas - 1)
        return recortado.tobytes(deflate=True, garbage=4)
    finally:
        try:
            doc.close()
        except Exception:
            pass


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
        contenido_pdf = segmentar_pdf_para_referencias(contenido_pdf)
        
        # Endpoint específico para procesar referencias
        endpoint = f"{GROBID_URL_BASE}/processReferences"
        
        files = {"input": (pdf.filename, contenido_pdf, "application/pdf")}
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
