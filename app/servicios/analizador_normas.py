import re
from typing import Optional, Dict, Any
from app.modelos.schemas import ResultadoAnalisis, TipoNorma, CitaDetalle

PALABRAS_REFERENCIAS = [
    "referencias", "reference", "references", "bibliografía", "bibliografia",
    "bibliography", "fuentes", "sources", "works cited", "literatura citada"
]

def detectar_estilo_citacion(texto: str, citas_grobid: list) -> str:
    """
    Detecta automáticamente el estilo de citación usado en el documento.
    
    Args:
        texto: Texto completo del documento
        citas_grobid: Lista de citas extraídas por GROBID
    
    Returns:
        'APA', 'IEEE', 'VANCOUVER', o 'DESCONOCIDO'
    """
    # Contadores para cada estilo
    contador_apa = 0
    contador_numerico = 0
    
    print(f"[DETECTOR] Analizando {len(citas_grobid)} citas...")
    
    # Analizar todas las citas extraídas por GROBID
    for cita in citas_grobid:
        cita_str = str(cita).strip()
        
        # Patrón APA: (Autor, año) o (Autor et al., año)
        if re.match(r'\([A-Z][a-zá-úñ]+(?:\s+(?:et\s+al\.|&|y)\s+[A-Z][a-zá-úñ]+)?,\s*\d{4}\)', cita_str):
            contador_apa += 1
            print(f"[DETECTOR] APA detectado: {cita_str}")
        
        # Patrón numérico entre corchetes: [1], [2,3], [1-5]
        elif re.match(r'\[\d+(?:\s*[-,]\s*\d+)*\]', cita_str):
            contador_numerico += 1
            print(f"[DETECTOR] IEEE/Vancouver detectado: {cita_str}")
    
    # Analizar también patrones en el texto completo
    patron_apa_texto = len(re.findall(r'\([A-Z][a-zá-úñ]+[^)]*,\s*\d{4}\)', texto))
    patron_numerico_texto = len(re.findall(r'\[\d+(?:\s*[-,]\s*\d+)*\]', texto))
    
    contador_apa += patron_apa_texto
    contador_numerico += patron_numerico_texto
    
    print(f"[DETECTOR] Contadores finales - APA: {contador_apa}, Numérico: {contador_numerico}")
    
    # Decisión basada en mayoría
    total = contador_apa + contador_numerico
    
    if total == 0:
        return "DESCONOCIDO"
    
    # Si más del 50% son de un estilo, se considera ese estilo
    if contador_apa / total > 0.5:
        return "APA"
    elif contador_numerico / total > 0.5:
        return "IEEE"
    else:
        # En caso de empate, preferir el que tenga más
        if contador_apa > contador_numerico:
            return "APA"
        elif contador_numerico > 0:
            return "IEEE"
        else:
            return "DESCONOCIDO"

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
    
    # Usar SIEMPRE GROBID para análisis
    if not (datos_grobid and datos_grobid.get("status") == "success"):
        errores.append("No se pudo obtener datos válidos de GROBID para el análisis APA.")
        return ResultadoAnalisis(
            cumple=False,
            norma=TipoNorma.APA,
            errores=errores,
            detalles="No se pudo analizar el documento con GROBID"
        )
    
    # Código de GROBID cuando el análisis es exitoso
    from app.servicios.servicio_grobid import extraer_referencias_de_xml, extraer_citas_de_xml
    
    xml_content = datos_grobid.get("xml", "")
    referencias = extraer_referencias_de_xml(xml_content)
    citas_grobid = extraer_citas_de_xml(xml_content)
    
    # Extraer TODAS las referencias del texto (sección bibliografía)
    from app.api.rutas import extraer_referencias_del_texto
    referencias_completas = extraer_referencias_del_texto(texto)
    
    citas_validas = []
    citas_invalidas = []
    
    for ref_texto in referencias_completas:
        citas_validas.append(CitaDetalle(
            texto=ref_texto,
            valida=True
        ))
    
    if len(referencias_completas) == 0:
        errores.append("No se detectaron referencias bibliográficas")
    
    total_citas = len(citas_validas)
    cumple = len(errores) == 0
    detalles = f"Referencias extraídas: {len(referencias_completas)}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.APA,
        errores=errores,
        detalles=detalles,
        citas_validas=citas_validas,
        citas_invalidas=citas_invalidas,
        total_citas=total_citas,
        referencias_completas=referencias_completas
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
    
    # Usar SIEMPRE GROBID para análisis
    if not (datos_grobid and datos_grobid.get("status") == "success"):
        errores.append("No se pudo obtener datos válidos de GROBID para el análisis IEEE.")
        return ResultadoAnalisis(
            cumple=False,
            norma=TipoNorma.IEEE,
            errores=errores,
            detalles="No se pudo analizar el documento con GROBID"
        )
    
    # Código de GROBID cuando el análisis es exitoso
    from app.servicios.servicio_grobid import extraer_referencias_de_xml, extraer_citas_de_xml
    
    xml_content = datos_grobid.get("xml", "")
    referencias = extraer_referencias_de_xml(xml_content)
    citas_grobid = extraer_citas_de_xml(xml_content)
    
    # Extraer TODAS las referencias del texto (sección bibliografía)
    from app.api.rutas import extraer_referencias_del_texto
    referencias_completas = extraer_referencias_del_texto(texto)
    
    citas_validas = []
    citas_invalidas = []
    
    for i, ref_texto in enumerate(referencias_completas, 1):
        citas_validas.append(CitaDetalle(
            texto=f"[{i}] {ref_texto}",
            valida=True
        ))
    
    if len(referencias_completas) == 0:
        errores.append("No se detectaron referencias bibliográficas")
    
    total_citas = len(citas_validas)
    cumple = len(errores) == 0
    detalles = f"Referencias extraídas: {len(referencias_completas)}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.IEEE,
        errores=errores,
        detalles=detalles,
        citas_validas=citas_validas,
        citas_invalidas=citas_invalidas,
        total_citas=total_citas,
        referencias_completas=referencias_completas
    )
    
