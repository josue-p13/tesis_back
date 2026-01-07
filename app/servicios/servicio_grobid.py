import httpx
from typing import Optional, Dict, Any

GROBID_URL = "http://localhost:8070"

async def procesar_pdf_grobid(ruta_archivo: str) -> Optional[Dict[str, Any]]:
    """Procesa un PDF con GROBID y retorna la estructura del documento"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(ruta_archivo, 'rb') as archivo:
                files = {'input': archivo}
                response = await client.post(
                    f"{GROBID_URL}/api/processFulltextDocument",
                    files=files
                )
                
                if response.status_code == 200:
                    return {"xml": response.text, "status": "success"}
                else:
                    return {"error": f"Error GROBID: {response.status_code}", "status": "error"}
    except Exception as e:
        return {"error": str(e), "status": "error"}

def extraer_referencias_de_xml(xml_content: str) -> list:
    """Extrae referencias del XML de GROBID"""
    import re
    referencias = []
    
    patron_biblStruct = re.compile(r'<biblStruct[^>]*>(.*?)</biblStruct>', re.DOTALL)
    matches = patron_biblStruct.findall(xml_content)
    
    for match in matches:
        autor_patron = re.compile(r'<persName[^>]*>.*?<surname[^>]*>(.*?)</surname>.*?</persName>', re.DOTALL)
        autores = autor_patron.findall(match)
        
        year_patron = re.compile(r'<date[^>]*when="(\d{4})"[^>]*>', re.DOTALL)
        year = year_patron.findall(match)
        
        title_patron = re.compile(r'<title[^>]*level="a"[^>]*>(.*?)</title>', re.DOTALL)
        titulo = title_patron.findall(match)
        
        if autores or year or titulo:
            referencias.append({
                "autores": autores,
                "año": year[0] if year else None,
                "titulo": titulo[0] if titulo else None
            })
    
    return referencias

def extraer_citas_de_xml(xml_content: str) -> list:
    """Extrae citas del cuerpo del documento"""
    import re
    patron_citas = re.compile(r'<ref[^>]*type="bibr"[^>]*>(.*?)</ref>', re.DOTALL)
    citas = patron_citas.findall(xml_content)
    return citas
