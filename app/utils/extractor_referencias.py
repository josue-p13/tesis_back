import re
from typing import List


def extraer_referencias_del_texto(texto: str) -> List[str]:
    """Extrae referencias bibliográficas del texto"""
    referencias = []
    
    # Buscar inicio de la sección de referencias
    patrones_inicio = [r'\bREFERENCIAS\b', r'\bREFERENCES\b', r'\bBIBLIOGRAFÍA\b', r'\bBIBLIOGRAPHY\b']
    inicio_idx = -1
    for patron in patrones_inicio:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            inicio_idx = match.end()
            break
    
    if inicio_idx == -1:
        return referencias
    
    # Buscar fin de la sección
    patrones_fin = [r'\n\s*(ANEXO|APÉNDICE|APPENDIX|ANNEX)\s', r'\n\s*FIRMA', r'\n\s*AUTOR(ES)?:', r'\n\s*TUTOR']
    texto_desde_refs = texto[inicio_idx:]
    fin_idx = len(texto_desde_refs)
    
    for patron in patrones_fin:
        match = re.search(patron, texto_desde_refs, re.IGNORECASE)
        if match:
            fin_idx = match.start()
            break
    
    # Procesar líneas
    seccion_refs = texto_desde_refs[:fin_idx]
    lineas = seccion_refs.split('\n')
    ref_actual = ""
    
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        
        # Detectar inicio de nueva referencia
        es_inicio_ieee = re.match(r'^\[\d+\]\s+', linea)
        # Detectar autor: incluye nombres con prefijo en minúscula (de, van, von, el, al-, del)
        es_inicio_apa = re.match(r'^(?:[a-z]{2,3}\s+)?[A-Z][a-záéíóúñüA-Z\'\-]+,\s+[A-Z]\.', linea)
        es_titulo_seccion = re.match(r'^\d+\.\s+[A-Z][a-z]+\s+[a-z]+\s+[A-Z]', linea)
        
        if (es_inicio_ieee or es_inicio_apa) and not es_titulo_seccion:
            if ref_actual:
                referencias.append(ref_actual.strip())
            ref_actual = linea
        else:
            if ref_actual:
                ref_actual += " " + linea
    
    # Agregar última referencia
    if ref_actual:
        referencias.append(ref_actual.strip())
    
    print(f"[EXTRACCIÓN] {len(referencias)} referencias encontradas")
    return referencias
