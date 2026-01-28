import httpx
from typing import Optional, Dict, Any, List
import re
import xml.etree.ElementTree as ET

GROBID_URL = "http://localhost:8070"

async def procesar_pdf_grobid(ruta_archivo: str) -> Optional[Dict[str, Any]]:
    """Procesa un PDF con GROBID usando múltiples endpoints para mejor extracción"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(ruta_archivo, 'rb') as archivo:
                files = {'input': archivo}
                
                # 1. Procesar documento completo
                response_full = await client.post(
                    f"{GROBID_URL}/api/processFulltextDocument",
                    files=files,
                    data={
                        'consolidateHeader': '1',  # Mejora extracción de metadatos
                        'consolidateCitations': '1',  # Mejora extracción de referencias
                        'includeRawCitations': '1',  # Incluye citas sin procesar
                        'includeRawAffiliations': '0',
                        'teiCoordinates': ['ref', 'biblStruct']  # Coordenadas de referencias
                    }
                )
                
                if response_full.status_code != 200:
                    return {"error": f"Error GROBID: {response_full.status_code}", "status": "error"}
                
                xml_content = response_full.text
                
                # 2. Procesar solo referencias para comparación
                archivo.seek(0)
                files_ref = {'input': archivo}
                response_refs = await client.post(
                    f"{GROBID_URL}/api/processReferences",
                    files=files_ref,
                    data={'consolidateCitations': '1'}
                )
                
                referencias_adicionales = []
                if response_refs.status_code == 200:
                    referencias_adicionales = extraer_referencias_de_xml(response_refs.text)
                
                return {
                    "xml": xml_content,
                    "referencias_xml": response_refs.text if response_refs.status_code == 200 else None,
                    "referencias_adicionales": referencias_adicionales,
                    "status": "success"
                }
                
    except Exception as e:
        return {"error": str(e), "status": "error"}

def extraer_referencias_de_xml(xml_content: str) -> List[Dict[str, Any]]:
    """Extrae referencias del XML de GROBID usando parsing XML mejorado"""
    referencias = []
    
    try:
        # Limpiar namespace para facilitar parsing
        xml_clean = re.sub(r'xmlns="[^"]+"', '', xml_content)
        root = ET.fromstring(xml_clean)
        
        # Buscar todas las referencias bibliográficas
        for biblStruct in root.findall('.//biblStruct'):
            ref_data = {
                "autores": [],
                "año": None,
                "titulo": None,
                "raw": None
            }
            
            # Extraer autores
            for author in biblStruct.findall('.//author/persName'):
                surname = author.find('.//surname')
                forename = author.find('.//forename')
                
                autor_nombre = ""
                if surname is not None and surname.text:
                    autor_nombre = surname.text.strip()
                if forename is not None and forename.text:
                    autor_nombre = f"{forename.text.strip()} {autor_nombre}" if autor_nombre else forename.text.strip()
                
                if autor_nombre:
                    ref_data["autores"].append(autor_nombre)
            
            # Extraer año
            date_elem = biblStruct.find('.//date[@when]')
            if date_elem is not None:
                when = date_elem.get('when')
                if when:
                    year_match = re.search(r'\d{4}', when)
                    if year_match:
                        ref_data["año"] = year_match.group()
            
            # Extraer título
            title_elem = biblStruct.find('.//title[@level="a"]')
            if title_elem is None:
                title_elem = biblStruct.find('.//title')
            if title_elem is not None and title_elem.text:
                ref_data["titulo"] = title_elem.text.strip()
            
            # Texto completo de la referencia
            ref_data["raw"] = ET.tostring(biblStruct, encoding='unicode', method='text')
            
            referencias.append(ref_data)
            
    except ET.ParseError:
        # Fallback a regex si XML está mal formado
        referencias = extraer_referencias_regex(xml_content)
    
    return referencias

def extraer_referencias_regex(xml_content: str) -> List[Dict[str, Any]]:
    """Método de respaldo usando regex para extraer referencias"""
    referencias = []
    
    patron_biblStruct = re.compile(r'<biblStruct[^>]*>(.*?)</biblStruct>', re.DOTALL)
    matches = patron_biblStruct.findall(xml_content)
    
    for match in matches:
        autor_patron = re.compile(r'<surname[^>]*>(.*?)</surname>', re.DOTALL)
        autores = [a.strip() for a in autor_patron.findall(match) if a.strip()]
        
        year_patron = re.compile(r'when="(\d{4})"')
        year = year_patron.findall(match)
        
        title_patron = re.compile(r'<title[^>]*>(.*?)</title>', re.DOTALL)
        titulo = title_patron.findall(match)
        
        referencias.append({
            "autores": autores,
            "año": year[0] if year else None,
            "titulo": re.sub(r'<[^>]+>', '', titulo[0]).strip() if titulo else None,
            "raw": match
        })
    
    return referencias

def extraer_citas_de_xml(xml_content: str) -> List[str]:
    """Extrae citas del cuerpo del documento con mejor precisión"""
    citas = []
    
    try:
        xml_clean = re.sub(r'xmlns="[^"]+"', '', xml_content)
        root = ET.fromstring(xml_clean)
        
        # Buscar referencias en el texto
        for ref in root.findall('.//ref[@type="bibr"]'):
            cita_text = ''.join(ref.itertext()).strip()
            if cita_text:
                citas.append(cita_text)
                
    except ET.ParseError:
        # Fallback a regex
        patron_citas = re.compile(r'<ref[^>]*type="bibr"[^>]*>(.*?)</ref>', re.DOTALL)
        citas = [re.sub(r'<[^>]+>', '', c).strip() for c in patron_citas.findall(xml_content)]
    
    return citas

def normalizar_referencia(ref: Dict[str, Any]) -> str:
    """Normaliza una referencia para facilitar comparación"""
    partes = []
    
    if ref.get("autores"):
        # Tomar primer autor
        autor = ref["autores"][0].split()[-1] if ref["autores"] else ""
        partes.append(autor.lower())
    
    if ref.get("año"):
        partes.append(str(ref["año"]))
    
    return ", ".join(partes) if partes else ""