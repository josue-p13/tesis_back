import httpx
from typing import Optional, Dict, Any, List
import re
import xml.etree.ElementTree as ET
import asyncio

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

async def procesar_cita_grobid(texto_cita: str) -> Dict[str, Any]:
    """
    Envía una cita individual a GROBID para estructurarla en campos separados.
    
    Args:
        texto_cita: Texto completo de la referencia bibliográfica
        
    Returns:
        Dict con campos estructurados: autores, titulo, año, doi, etc.
    """
    # Limpiar el número de referencia [1], [2], etc.
    texto_limpio = re.sub(r'^\[\d+\]\s*', '', texto_cita)
    
    print(f"[GROBID-CITA] Procesando: {texto_limpio[:80]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{GROBID_URL}/api/processCitation",
                data={
                    'citations': texto_limpio,
                    'consolidateCitations': '1'
                }
            )
            
            print(f"[GROBID-CITA] Status: {response.status_code}")
            
            if response.status_code == 200:
                xml_content = response.text
                print(f"[GROBID-CITA] XML length: {len(xml_content)} chars")
                
                if not xml_content or len(xml_content.strip()) < 50:
                    return {
                        "status": "error",
                        "texto_original": texto_cita,
                        "motivo": "Respuesta vacía de GROBID (XML muy corto)"
                    }
                
                # Guardar XML para debug
                if "<biblStruct" not in xml_content:
                    print(f"[GROBID-CITA] ⚠️ WARNING: No se encontró <biblStruct> en el XML")
                    print(f"[GROBID-CITA] XML recibido: {xml_content[:500]}")
                
                resultado = parsear_cita_xml(xml_content, texto_cita, texto_limpio)
                
                if resultado.get("status") == "success":
                    print(f"[GROBID-CITA] ✓ Éxito - Autores: {len(resultado.get('autores', []))}, Título: {bool(resultado.get('titulo'))}")
                else:
                    print(f"[GROBID-CITA] ✗ Error: {resultado.get('motivo', 'Sin motivo')}")
                
                return resultado
            else:
                error_text = response.text
                motivo = f"GROBID retornó HTTP {response.status_code}"
                if error_text:
                    motivo += f": {error_text[:200]}"
                print(f"[GROBID-CITA] ✗ {motivo}")
                return {
                    "status": "error",
                    "texto_original": texto_cita,
                    "motivo": motivo
                }
    except asyncio.TimeoutError:
        motivo = "Timeout de 30 segundos al esperar respuesta de GROBID"
        print(f"[GROBID-CITA] ✗ {motivo}")
        return {
            "status": "error",
            "texto_original": texto_cita,
            "motivo": motivo
        }
    except Exception as e:
        motivo = f"Excepción al conectar con GROBID: {type(e).__name__} - {str(e)}"
        print(f"[GROBID-CITA] ✗ {motivo}")
        return {
            "status": "error",
            "texto_original": texto_cita,
            "motivo": motivo
        }

def parsear_cita_xml(xml_str: str, texto_original: str, texto_limpio: str = None) -> Dict[str, Any]:
    """Parsea el XML de GROBID y extrae campos estructurados de la cita"""
    try:
        root = ET.fromstring(xml_str)
        
        resultado = {
            "status": "success",
            "autores": [],
            "titulo": None,
            "año": None,
            "revista": None,
            "volumen": None,
            "numero": None,
            "paginas": None,
            "doi": None,
            "editorial": None,
            "ciudad": None,
            "tipo": None,
            "texto_original": texto_original
        }
        
        # En processCitation, <biblStruct> es el elemento root (sin namespace TEI)
        biblstruct = root if root.tag in ['biblStruct', '{http://www.tei-c.org/ns/1.0}biblStruct'] else None
        
        if biblstruct is None:
            # Buscar dentro del árbol por si acaso
            biblstruct = root.find('.//biblStruct')
            if biblstruct is None:
                elementos = [elem.tag for elem in root.iter()]
                elementos_unicos = list(set(elementos))[:10]
                return {
                    "status": "error",
                    "texto_original": texto_original,
                    "motivo": f"No se encontró <biblStruct>. Root tag: {root.tag}. Elementos: {', '.join(elementos_unicos)}"
                }
        
        # Extraer autores (sin namespace ya que el XML no lo usa)
        for author in biblstruct.findall('.//author'):
            persname = author.find('.//persName')
            if persname is not None:
                apellido = persname.find('surname')
                nombre = persname.find('forename[@type="first"]')
                
                autor_completo = ""
                if apellido is not None and apellido.text:
                    autor_completo = apellido.text.strip()
                if nombre is not None and nombre.text:
                    inicial = nombre.text.strip()[0] + "." if nombre.text.strip() else ""
                    if autor_completo:
                        autor_completo += f", {inicial}"
                    else:
                        autor_completo = inicial
                
                if autor_completo:
                    resultado["autores"].append(autor_completo)
        
        # Extraer título
        titulo_elem = biblstruct.find('.//title[@level="a"]')
        if titulo_elem is not None and titulo_elem.text:
            resultado["titulo"] = titulo_elem.text.strip()
        
        if not resultado["titulo"]:
            titulo_elem = biblstruct.find('.//title[@level="m"]')
            if titulo_elem is not None and titulo_elem.text:
                resultado["titulo"] = titulo_elem.text.strip()
                resultado["tipo"] = "Libro"
        
        # Extraer año
        fecha_elem = biblstruct.find('.//date[@type="published"]')
        if fecha_elem is not None:
            when = fecha_elem.get('when')
            if when:
                resultado["año"] = when[:4] if len(when) >= 4 else when
        
        # Extraer revista/journal
        revista_elem = biblstruct.find('.//title[@level="j"]')
        if revista_elem is not None and revista_elem.text:
            resultado["revista"] = revista_elem.text.strip()
        
        # Extraer volumen
        volumen_elem = biblstruct.find('.//biblScope[@unit="volume"]')
        if volumen_elem is not None and volumen_elem.text:
            resultado["volumen"] = volumen_elem.text.strip()
        
        # Extraer número
        numero_elem = biblstruct.find('.//biblScope[@unit="issue"]')
        if numero_elem is not None and numero_elem.text:
            resultado["numero"] = numero_elem.text.strip()
        
        # Extraer páginas
        paginas_elem = biblstruct.find('.//biblScope[@unit="page"]')
        if paginas_elem is not None:
            from_page = paginas_elem.get('from')
            to_page = paginas_elem.get('to')
            if from_page and to_page:
                resultado["paginas"] = f"{from_page}-{to_page}"
            elif from_page:
                resultado["paginas"] = from_page
        
        # Extraer DOI
        doi_elem = biblstruct.find('.//idno[@type="DOI"]')
        if doi_elem is not None and doi_elem.text:
            resultado["doi"] = doi_elem.text.strip()
        
        # Extraer editorial
        editorial_elem = biblstruct.find('.//publisher')
        if editorial_elem is not None and editorial_elem.text:
            resultado["editorial"] = editorial_elem.text.strip()
        
        # Extraer ciudad
        ciudad_elem = biblstruct.find('.//pubPlace')
        if ciudad_elem is not None and ciudad_elem.text:
            resultado["ciudad"] = ciudad_elem.text.strip()
        
        # Verificar que al menos tengamos autor o título
        if not resultado["autores"] and not resultado["titulo"]:
            return {
                "status": "error",
                "texto_original": texto_original,
                "motivo": "GROBID procesó el XML pero no se pudo extraer ni autor ni título (posiblemente formato incorrecto)"
            }
        
        return resultado
        
    except ET.ParseError as e:
        # Guardar XML problemático para debug
        xml_preview = xml_str[:500].replace('\n', ' ')
        return {
            "status": "error",
            "texto_original": texto_original,
            "motivo": f"XML malformado retornado por GROBID. Error: {str(e)}. Vista previa: {xml_preview}"
        }
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return {
            "status": "error",
            "texto_original": texto_original,
            "motivo": f"Excepción al parsear XML: {type(e).__name__} - {str(e)}. Traceback: {tb[:300]}"
        }