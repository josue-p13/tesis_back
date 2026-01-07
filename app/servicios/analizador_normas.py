import re
from typing import Optional, Dict, Any
from app.modelos.schemas import ResultadoAnalisis, TipoNorma, CitaDetalle

PALABRAS_REFERENCIAS = [
    "referencias", "reference", "references", "bibliografía", "bibliografia",
    "bibliography", "fuentes", "sources", "works cited", "literatura citada"
]

def validar_cita_apa(cita: str) -> tuple[bool, Optional[str]]:
    """Valida si una cita cumple con formato APA y retorna razón si no es válida"""
    patrones_validos = [
        (r'^\([A-Z][a-zá-ú]+,\s*\d{4}\)$', "Formato básico válido"),
        (r'^\([A-Z][a-zá-ú]+\s+&\s+[A-Z][a-zá-ú]+,\s*\d{4}\)$', "Dos autores válido"),
        (r'^\([A-Z][a-zá-ú]+\s+et\s+al\.,\s*\d{4}\)$', "Et al. válido"),
        (r'^\([A-Z][a-zá-ú]+\s+y\s+[A-Z][a-zá-ú]+,\s*\d{4}\)$', "Dos autores en español válido"),
        (r'^\([A-Z][a-zá-ú]+\s+y\s+otros,\s*\d{4}\)$', "Y otros válido"),
    ]
    
    for patron, _ in patrones_validos:
        if re.match(patron, cita):
            return True, None
    
    razones = []
    if not cita.startswith('(') or not cita.endswith(')'):
        razones.append("No está entre paréntesis")
    if not re.search(r'\d{4}', cita):
        razones.append("Falta el año")
    if not re.search(r'[A-Z][a-z]+', cita):
        razones.append("Falta apellido con mayúscula inicial")
    if not ',' in cita:
        razones.append("Falta la coma entre autor y año")
    
    return False, "; ".join(razones) if razones else "Formato general incorrecto"

def analizar_norma_apa(texto: str, datos_grobid: Optional[Dict[str, Any]] = None) -> ResultadoAnalisis:
    errores = []
    texto_lower = texto.lower()
    
    if not texto.strip():
        errores.append("El documento está vacío")
        return ResultadoAnalisis(
            cumple=False,
            norma=TipoNorma.APA,
            errores=errores,
            detalles="Documento vacío"
        )
    
    # Si hay datos de GROBID, usarlos para análisis más profundo
    if datos_grobid and datos_grobid.get("status") == "success":
        from app.servicios.servicio_grobid import extraer_referencias_de_xml, extraer_citas_de_xml
        
        xml_content = datos_grobid.get("xml", "")
        referencias = extraer_referencias_de_xml(xml_content)
        citas_grobid = extraer_citas_de_xml(xml_content)
        
        citas_validas = []
        citas_invalidas = []
        
        # Validar cada referencia extraída por GROBID
        for ref in referencias:
            autores = ref.get("autores", [])
            year = ref.get("año")
            
            if year and autores:
                autor_str = autores[0] if autores else "Desconocido"
                cita_texto = f"Ref: {autor_str}, {year}"
                citas_validas.append(CitaDetalle(texto=cita_texto, valida=True))
            else:
                titulo = ref.get("titulo") or "Sin título"
                razon = []
                if not year:
                    razon.append("Falta año")
                if not autores:
                    razon.append("Falta autor")
                cita_texto = f"Ref: {str(titulo)[:50]}..."
                citas_invalidas.append(CitaDetalle(texto=cita_texto, valida=False, razon="; ".join(razon)))
        
        # Validar citas en el texto extraídas por GROBID
        for cita in citas_grobid:
            cita_limpia = str(cita).strip()
            if cita_limpia:
                es_valida, razon = validar_cita_apa(cita_limpia)
                if es_valida:
                    citas_validas.append(CitaDetalle(texto=cita_limpia, valida=True))
                else:
                    citas_invalidas.append(CitaDetalle(texto=cita_limpia, valida=False, razon=razon or "Formato no reconocido"))
        
        if len(referencias) == 0:
            errores.append("No se detectaron referencias bibliográficas estructuradas")
        
        if len(citas_grobid) == 0:
            errores.append("No se detectaron citas en el texto")
        
        total_citas = len(citas_validas) + len(citas_invalidas)
        cumple = len(errores) == 0
        detalles = f"Referencias GROBID: {len(referencias)}. Citas en texto: {len(citas_grobid)}. Válidas: {len(citas_validas)}, Inválidas: {len(citas_invalidas)}"
        
        return ResultadoAnalisis(
            cumple=cumple,
            norma=TipoNorma.APA,
            errores=errores,
            detalles=detalles,
            citas_validas=citas_validas,
            citas_invalidas=citas_invalidas,
            total_citas=total_citas
        )
    
    # Fallback: Análisis con regex si GROBID no está disponible
    patrones_citas_apa = [
        r'\([A-Z][a-zá-ú]+,?\s+\d{4}\)',
        r'\([A-Z][a-zá-ú]+\s+&\s+[A-Z][a-zá-ú]+,?\s+\d{4}\)',
        r'\([A-Z][a-zá-ú]+\s+et\s+al\.,?\s+\d{4}\)',
        r'\([A-Z][a-zá-ú]+\s+y\s+[A-Z][a-zá-ú]+,?\s+\d{4}\)',
        r'\([A-Z][a-zá-ú]+\s+y\s+otros,?\s+\d{4}\)',
    ]
    
    todas_citas = []
    for patron in patrones_citas_apa:
        citas = re.findall(patron, texto)
        todas_citas.extend(citas)
    
    todas_citas = list(set(todas_citas))
    
    citas_validas = []
    citas_invalidas = []
    
    for cita in todas_citas:
        es_valida, razon = validar_cita_apa(cita)
        if es_valida:
            citas_validas.append(CitaDetalle(texto=cita, valida=True))
        else:
            citas_invalidas.append(CitaDetalle(texto=cita, valida=False, razon=razon))
    
    patron_general = r'\([^)]*\d{4}[^)]*\)'
    posibles_citas = re.findall(patron_general, texto)
    for posible in posibles_citas:
        if posible not in todas_citas:
            es_valida, razon = validar_cita_apa(posible)
            if not es_valida:
                citas_invalidas.append(CitaDetalle(texto=posible, valida=False, razon=razon))
    
    if len(citas_validas) == 0:
        errores.append("No se encontraron citas válidas en formato APA. Ejemplos: (Autor, 2020), (Autor & Otro, 2020), (Autor et al., 2020)")
    
    seccion_encontrada = False
    palabra_encontrada = ""
    for palabra in PALABRAS_REFERENCIAS:
        if palabra in texto_lower:
            seccion_encontrada = True
            palabra_encontrada = palabra
            break
    
    if not seccion_encontrada:
        errores.append(f"No se encontró sección de referencias. Palabras buscadas: {', '.join(PALABRAS_REFERENCIAS[:4])}")
    
    total_citas = len(citas_validas) + len(citas_invalidas)
    cumple = len(errores) == 0
    detalles = f"Citas válidas: {len(citas_validas)}, Inválidas: {len(citas_invalidas)}. Sección: {palabra_encontrada if seccion_encontrada else 'No encontrada'}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.APA,
        errores=errores,
        detalles=detalles,
        citas_validas=citas_validas,
        citas_invalidas=citas_invalidas,
        total_citas=total_citas
    )

def analizar_norma_ieee(texto: str, datos_grobid: Optional[Dict[str, Any]] = None) -> ResultadoAnalisis:
    errores = []
    texto_lower = texto.lower()
    
    if not texto.strip():
        errores.append("El documento está vacío")
        return ResultadoAnalisis(
            cumple=False,
            norma=TipoNorma.IEEE,
            errores=errores,
            detalles="Documento vacío"
        )
    
    # Si hay datos de GROBID, usarlos para análisis más profundo
    if datos_grobid and datos_grobid.get("status") == "success":
        from app.servicios.servicio_grobid import extraer_referencias_de_xml, extraer_citas_de_xml
        
        xml_content = datos_grobid.get("xml", "")
        referencias = extraer_referencias_de_xml(xml_content)
        citas_grobid = extraer_citas_de_xml(xml_content)
        
        citas_validas = []
        citas_invalidas = []
        
        # Validar cada referencia extraída por GROBID
        for i, ref in enumerate(referencias, 1):
            cita_texto = f"[{i}] Ref bibliográfica"
            citas_validas.append(CitaDetalle(texto=cita_texto, valida=True))
        
        # Validar citas en el texto extraídas por GROBID
        for cita in citas_grobid:
            cita_limpia = str(cita).strip()
            if cita_limpia and re.match(r'^\[\d+(\s*[-,]\s*\d+)*\]$', cita_limpia):
                citas_validas.append(CitaDetalle(texto=cita_limpia, valida=True))
            elif cita_limpia:
                citas_invalidas.append(CitaDetalle(texto=cita_limpia, valida=False, razon="No sigue formato IEEE [número]"))
        
        if len(referencias) == 0:
            errores.append("No se detectaron referencias bibliográficas estructuradas")
        
        if len(citas_grobid) == 0:
            errores.append("No se detectaron citas en el texto")
        
        total_citas = len(citas_validas) + len(citas_invalidas)
        cumple = len(errores) == 0
        detalles = f"Referencias GROBID: {len(referencias)}. Citas en texto: {len(citas_grobid)}. Válidas: {len(citas_validas)}, Inválidas: {len(citas_invalidas)}"
        
        return ResultadoAnalisis(
            cumple=cumple,
            norma=TipoNorma.IEEE,
            errores=errores,
            detalles=detalles,
            citas_validas=citas_validas,
            citas_invalidas=citas_invalidas,
            total_citas=total_citas
        )
    
    # Fallback: Análisis con regex si GROBID no está disponible
    patrones_citas_ieee = [
        r'\[\d+\]',
        r'\[\d+\s*-\s*\d+\]',
        r'\[\d+\s*,\s*\d+\]',
        r'\[\d+\s*,\s*\d+\s*-\s*\d+\]',
    ]
    
    todas_citas = []
    for patron in patrones_citas_ieee:
        citas = re.findall(patron, texto)
        todas_citas.extend(citas)
    
    citas_unicas = list(set(todas_citas))
    
    citas_validas = []
    citas_invalidas = []
    
    for cita in citas_unicas:
        if re.match(r'^\[\d+(\s*[-,]\s*\d+)*\]$', cita):
            citas_validas.append(CitaDetalle(texto=cita, valida=True))
        else:
            citas_invalidas.append(CitaDetalle(texto=cita, valida=False, razon="Formato IEEE incorrecto"))
    
    patron_general = r'\[[^\]]*\d+[^\]]*\]'
    posibles_citas = re.findall(patron_general, texto)
    for posible in posibles_citas:
        if posible not in citas_unicas:
            if not re.match(r'^\[\d+(\s*[-,]\s*\d+)*\]$', posible):
                razon = "No sigue formato IEEE estándar [número]"
                citas_invalidas.append(CitaDetalle(texto=posible, valida=False, razon=razon))
    
    if len(citas_validas) == 0:
        errores.append("No se encontraron citas válidas en formato IEEE. Ejemplos: [1], [2], [1-3], [1,2]")
    
    seccion_encontrada = False
    palabra_encontrada = ""
    for palabra in PALABRAS_REFERENCIAS:
        if palabra in texto_lower:
            seccion_encontrada = True
            palabra_encontrada = palabra
            break
    
    if not seccion_encontrada:
        errores.append(f"No se encontró sección de referencias. Palabras buscadas: {', '.join(PALABRAS_REFERENCIAS[:4])}")
    
    total_citas = len(citas_validas) + len(citas_invalidas)
    cumple = len(errores) == 0
    detalles = f"Citas válidas: {len(citas_validas)}, Inválidas: {len(citas_invalidas)}. Sección: {palabra_encontrada if seccion_encontrada else 'No encontrada'}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.IEEE,
        errores=errores,
        detalles=detalles,
        citas_validas=citas_validas,
        citas_invalidas=citas_invalidas,
        total_citas=total_citas
    )
