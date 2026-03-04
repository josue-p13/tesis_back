import httpx
from typing import Optional, Dict, Any, List
import re
import xml.etree.ElementTree as ET

GROBID_URL = "http://localhost:8070"

async def procesar_pdf_grobid(ruta_archivo: str) -> Optional[Dict[str, Any]]:
    """Procesa un PDF con GROBID para extraer referencias y citas"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(ruta_archivo, 'rb') as archivo:
                files = {'input': archivo}
                
                response = await client.post(
                    f"{GROBID_URL}/api/processFulltextDocument",
                    files=files,
                    data={
                        'consolidateHeader': '0',
                        'consolidateCitations': '0',
                        'includeRawCitations': '1',
                        'includeRawAffiliations': '0',
                    }
                )
                
                if response.status_code != 200:
                    return {"error": f"Error GROBID: {response.status_code}", "status": "error"}
                
                return {
                    "xml": response.text,
                    "status": "success"
                }
                
    except Exception as e:
        return {"error": str(e), "status": "error"}


def extraer_referencias_de_xml(xml_content: str) -> List[Dict[str, Any]]:
    """Extrae referencias completas del XML de GROBID (solo de la sección de bibliografía)"""
    referencias = []
    
    try:
        xml_clean = re.sub(r'xmlns="[^"]+"', '', xml_content)
        root = ET.fromstring(xml_clean)
        
        # Buscar SOLO en la sección de bibliografía
        listbibl = root.find('.//back//div[@type="references"]//listBibl')
        if listbibl is None:
            listbibl = root.find('.//listBibl')
        
        if listbibl is None:
            print("[GROBID] No se encontró sección de bibliografía en el XML")
            return []
        
        for bibl_struct in listbibl.findall('.//biblStruct'):
            ref_data = _parsear_biblstruct(bibl_struct)
            referencias.append(ref_data)
                
    except (ET.ParseError, Exception) as e:
        print(f"[GROBID] Error al parsear XML: {e}")
    
    return referencias


def _parsear_biblstruct(bibl_struct) -> Dict[str, Any]:
    """Extrae todos los campos de un elemento <biblStruct>"""
    ref_data = {
        "autores": [],
        "año": None,
        "titulo": None,
        "revista": None,
        "volumen": None,
        "numero": None,
        "paginas": None,
        "doi": None,
        "editorial": None,
        "ciudad": None,
        "tipo": None,
        "raw": None
    }
    
    for author in bibl_struct.findall('.//author/persName'):
        surname = author.find('.//surname')
        forename = author.find('.//forename')
        
        autor_nombre = ""
        if surname is not None and surname.text:
            autor_nombre = surname.text.strip()
        if forename is not None and forename.text:
            autor_nombre = f"{forename.text.strip()} {autor_nombre}" if autor_nombre else forename.text.strip()
        
        if autor_nombre:
            ref_data["autores"].append(autor_nombre)
    
    # --- TÍTULO (artículo) ---
    title_a = bibl_struct.find('.//title[@level="a"]')
    if title_a is not None and title_a.text:
        ref_data["titulo"] = title_a.text.strip()
    
    # --- TÍTULO (libro/monografía) - solo si no hay título de artículo ---
    if not ref_data["titulo"]:
        title_m = bibl_struct.find('.//title[@level="m"]')
        if title_m is not None and title_m.text:
            ref_data["titulo"] = title_m.text.strip()
            ref_data["tipo"] = "Libro"
    
    # --- REVISTA/JOURNAL ---
    revista_elem = bibl_struct.find('.//title[@level="j"]')
    if revista_elem is not None and revista_elem.text:
        ref_data["revista"] = revista_elem.text.strip()
    
    # Si no hay título de artículo ni de libro, usar título sin level como último recurso
    if not ref_data["titulo"]:
        title_any = bibl_struct.find('.//title')
        if title_any is not None and title_any.text:
            # Evitar usar el título de revista como título principal
            if title_any.text.strip() != ref_data.get("revista"):
                ref_data["titulo"] = title_any.text.strip()
    
    # --- VOLUMEN ---
    volumen_elem = bibl_struct.find('.//biblScope[@unit="volume"]')
    if volumen_elem is not None and volumen_elem.text:
        ref_data["volumen"] = volumen_elem.text.strip()
    
    # --- NÚMERO ---
    numero_elem = bibl_struct.find('.//biblScope[@unit="issue"]')
    if numero_elem is not None and numero_elem.text:
        ref_data["numero"] = numero_elem.text.strip()
    
    # --- PÁGINAS ---
    paginas_elem = bibl_struct.find('.//biblScope[@unit="page"]')
    if paginas_elem is not None:
        from_page = paginas_elem.get('from')
        to_page = paginas_elem.get('to')
        if from_page and to_page:
            ref_data["paginas"] = f"{from_page}-{to_page}"
        elif from_page:
            ref_data["paginas"] = from_page
        elif paginas_elem.text:
            ref_data["paginas"] = paginas_elem.text.strip()
    
    # --- DOI ---
    doi_elem = bibl_struct.find('.//idno[@type="DOI"]')
    if doi_elem is not None and doi_elem.text:
        ref_data["doi"] = doi_elem.text.strip()
    
    # --- EDITORIAL ---
    editorial_elem = bibl_struct.find('.//publisher')
    if editorial_elem is not None and editorial_elem.text:
        ref_data["editorial"] = editorial_elem.text.strip()
    
    # --- CIUDAD ---
    ciudad_elem = bibl_struct.find('.//pubPlace')
    if ciudad_elem is not None and ciudad_elem.text:
        ref_data["ciudad"] = ciudad_elem.text.strip()
    
    # --- TEXTO ORIGINAL (extraer antes para validar año) ---
    raw_note = bibl_struct.find('.//note[@type="raw_reference"]')
    if raw_note is not None:
        ref_data["raw"] = ''.join(raw_note.itertext()).strip()
    else:
        ref_data["raw"] = ET.tostring(bibl_struct, encoding='unicode', method='text').strip()
    
    # --- AÑO (con validación contra texto original) ---
    anio_grobid = None
    date_elem = bibl_struct.find('.//date[@when]')
    if date_elem is not None:
        when = date_elem.get('when')
        if when:
            year_match = re.search(r'\d{4}', when)
            if year_match:
                anio_grobid = year_match.group()
    
    # Validar: si el texto original tiene un año claro entre paréntesis (APA)
    # o al final (IEEE), verificar que coincida con lo que GROBID detectó
    raw_text = ref_data.get("raw", "")
    if raw_text:
        # Buscar año en formato APA: (2020) o (2020, Enero)
        anio_raw = re.search(r'\((\d{4})(?:[,\)])', raw_text)
        if anio_raw:
            anio_real = anio_raw.group(1)
            if anio_grobid != anio_real:
                # GROBID se confundió (ej: tomó páginas como año)
                anio_grobid = anio_real
    
    ref_data["año"] = anio_grobid
    
    return ref_data


async def procesar_cita_grobid(texto_cita: str) -> Dict[str, Any]:
    """Procesa una cita individual con GROBID (fallback cuando el XML principal no tiene referencias)"""
    texto_limpio = re.sub(r'^\[\d+\]\s*', '', texto_cita)
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GROBID_URL}/api/processCitation",
                data={'citations': texto_limpio, 'consolidateCitations': '0'}
            )
            
            if response.status_code != 200:
                return {"status": "error", "texto_original": texto_cita, "motivo": f"HTTP {response.status_code}"}
            
            xml_content = response.text
            if not xml_content or len(xml_content.strip()) < 50:
                return {"status": "error", "texto_original": texto_cita, "motivo": "Respuesta vacía de GROBID"}
            
            # Reusar _parsear_biblstruct en vez de duplicar lógica
            try:
                root = ET.fromstring(xml_content)
                biblstruct = root if root.tag in ['biblStruct', '{http://www.tei-c.org/ns/1.0}biblStruct'] else root.find('.//biblStruct')
                
                if biblstruct is None:
                    return {"status": "error", "texto_original": texto_cita, "motivo": "No se encontró <biblStruct> en XML"}
                
                ref_data = _parsear_biblstruct(biblstruct)
                ref_data["status"] = "success"
                ref_data["texto_original"] = texto_cita
                return ref_data
                
            except ET.ParseError as e:
                return {"status": "error", "texto_original": texto_cita, "motivo": f"XML malformado: {e}"}
            
    except Exception as e:
        return {"status": "error", "texto_original": texto_cita, "motivo": f"{type(e).__name__}: {e}"}