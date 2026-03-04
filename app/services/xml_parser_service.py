import xml.etree.ElementTree as ET
from typing import List, Dict


def parsear_referencias_xml(xml_texto: str) -> List[Dict[str, str]]:
    """
    Parsea el XML de GROBID y extrae las referencias estructuradas.
    
    Args:
        xml_texto: Contenido XML devuelto por GROBID
        
    Returns:
        Lista de referencias estructuradas
    """
    try:
        root = ET.fromstring(xml_texto)
        
        # Namespace de TEI (formato usado por GROBID)
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        
        referencias = []
        
        # Buscar todas las referencias bibliográficas
        for biblStruct in root.findall('.//tei:listBibl/tei:biblStruct', ns):
            ref = {}
            
            # Extraer texto raw (completo de la referencia si está disponible)
            # GROBID puede incluir el texto original en el elemento note[@type="raw_reference"]
            raw_elem = biblStruct.find('.//tei:note[@type="raw_reference"]', ns)
            if raw_elem is not None and raw_elem.text:
                ref['raw'] = raw_elem.text.strip()
            
            # Extraer título
            titulo_elem = biblStruct.find('.//tei:analytic/tei:title[@type="main"]', ns)
            if titulo_elem is not None and titulo_elem.text:
                ref['titulo'] = titulo_elem.text.strip()
            else:
                # Intentar con título de monografía
                titulo_elem = biblStruct.find('.//tei:monogr/tei:title', ns)
                if titulo_elem is not None and titulo_elem.text:
                    ref['titulo'] = titulo_elem.text.strip()
            
            # Extraer autores
            autores = []
            
            # Primero intentar en analytic (para artículos de revista)
            for autor in biblStruct.findall('.//tei:analytic/tei:author', ns):
                nombre_completo = []
                nombre_elem = autor.find('.//tei:forename', ns)
                if nombre_elem is not None and nombre_elem.text:
                    nombre_completo.append(nombre_elem.text.strip())
                
                apellido_elem = autor.find('.//tei:surname', ns)
                if apellido_elem is not None and apellido_elem.text:
                    nombre_completo.append(apellido_elem.text.strip())
                
                if nombre_completo:
                    autores.append(' '.join(nombre_completo))
            
            # Si no hay autores en analytic, buscar en monogr (para libros/monografías)
            if not autores:
                for autor in biblStruct.findall('.//tei:monogr/tei:author', ns):
                    nombre_completo = []
                    nombre_elem = autor.find('.//tei:forename', ns)
                    if nombre_elem is not None and nombre_elem.text:
                        nombre_completo.append(nombre_elem.text.strip())
                    
                    apellido_elem = autor.find('.//tei:surname', ns)
                    if apellido_elem is not None and apellido_elem.text:
                        nombre_completo.append(apellido_elem.text.strip())
                    
                    if nombre_completo:
                        autores.append(' '.join(nombre_completo))
            
            if autores:
                ref['autores'] = ', '.join(autores)
            
            # Extraer año - buscar en múltiples ubicaciones y validar
            año = None
            
            # Intento 1: Buscar en date[@type="published"] con atributo 'when'
            fecha_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:date[@type="published"]', ns)
            if fecha_elem is not None:
                when_attr = fecha_elem.get('when')
                if when_attr:
                    # Extraer solo el año (primeros 4 dígitos)
                    año_match = when_attr[:4] if len(when_attr) >= 4 else when_attr
                    if año_match.isdigit() and 1900 <= int(año_match) <= 2030:
                        año = año_match
                
                # Si no hay atributo 'when', intentar con el texto
                if not año and fecha_elem.text:
                    texto_fecha = fecha_elem.text.strip()
                    # Buscar un año de 4 dígitos en el texto
                    import re
                    match = re.search(r'\b(19\d{2}|20[0-3]\d)\b', texto_fecha)
                    if match:
                        año = match.group(1)
            
            # Intento 2: Buscar en cualquier date sin tipo específico
            if not año:
                fecha_elems = biblStruct.findall('.//tei:monogr/tei:imprint/tei:date', ns)
                for fecha_elem in fecha_elems:
                    when_attr = fecha_elem.get('when')
                    if when_attr:
                        año_match = when_attr[:4] if len(when_attr) >= 4 else when_attr
                        if año_match.isdigit() and 1900 <= int(año_match) <= 2030:
                            año = año_match
                            break
            
            if año:
                ref['año'] = año
            
            # Extraer revista/publicación
            revista_elem = biblStruct.find('.//tei:monogr/tei:title', ns)
            if revista_elem is not None and revista_elem.text:
                ref['publicacion'] = revista_elem.text.strip()
            
            # Extraer DOI
            doi_elem = biblStruct.find('.//tei:idno[@type="DOI"]', ns)
            if doi_elem is not None and doi_elem.text:
                ref['doi'] = doi_elem.text.strip()
            
            # Extraer volumen y páginas
            volumen_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:biblScope[@unit="volume"]', ns)
            if volumen_elem is not None and volumen_elem.text:
                ref['volumen'] = volumen_elem.text.strip()
            
            paginas_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:biblScope[@unit="page"]', ns)
            if paginas_elem is not None:
                pagina_inicio = paginas_elem.get('from', '')
                pagina_fin = paginas_elem.get('to', '')
                if pagina_inicio and pagina_fin:
                    ref['paginas'] = f"{pagina_inicio}-{pagina_fin}"
                elif pagina_inicio:
                    ref['paginas'] = pagina_inicio
            
            if ref:  # Solo agregar si se extrajo al menos un campo
                referencias.append(ref)
        
        return referencias
    
    except ET.ParseError as e:
        # Si hay error al parsear, devolver el XML crudo
        return [{"error": f"Error al parsear XML: {str(e)}", "xml_raw": xml_texto[:500]}]


