import re
from typing import List, Dict, Any
from collections import defaultdict


def detectar_estilo_citacion(referencias: List[Dict[str, str]]) -> str:
    """
    Detecta el estilo de citación bibliográfica usando patrones RegEx simples.
    
    Analiza el campo 'raw' (texto original) de las referencias o construye
    texto desde los campos estructurados como fallback.
    
    Estilos soportados:
    - IEEE: [1], [2], etc. (numeración con corchetes)
    - Vancouver: 1., 2., etc. (numeración con punto)
    - APA: (2020). Autor (formato con año entre paréntesis seguido de punto)
    - Harvard: (2020) MAY (formato con año y texto en mayúsculas)
    - Chicago: Formato con nombres completos
    - MLA: Formato con apellido, nombre
    
    Args:
        referencias: Lista de referencias estructuradas extraídas por GROBID
        
    Returns:
        Nombre del estilo detectado o "Desconocido"
    """
    if not referencias or len(referencias) == 0:
        return "Desconocido"
    
    resultado = clasificar_estilo_local(referencias)
    return resultado['estilo']


def clasificar_estilo_local(referencias: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Clasifica el estilo de citación usando análisis de patrones RegEx.
    
    Args:
        referencias: Lista de referencias estructuradas
        
    Returns:
        Dict con 'estilo' (nombre) y 'confianza' (0-100)
    """
    if not referencias:
        return {'estilo': 'Desconocido', 'confianza': 0}
    
    # Construir lista de textos de referencias para análisis
    textos_refs = []
    for ref in referencias:
        # Priorizar el campo 'raw' si existe
        if 'raw' in ref and ref['raw'].strip():
            textos_refs.append(ref['raw'].strip())
        else:
            # Construir texto desde campos estructurados como fallback
            texto_construido = construir_texto_referencia(ref)
            if texto_construido:
                textos_refs.append(texto_construido)
    
    if not textos_refs:
        return {'estilo': 'Desconocido', 'confianza': 0}
    
    # Contadores de patrones por estilo
    patrones = defaultdict(int)
    
    # Analizar cada línea de referencia
    for linea in textos_refs:
        linea = linea.strip()
        if not linea:
            continue
        
        # Verificar primero los patrones de Vancouver INDEPENDIENTEMENTE del número inicial
        # Esto es crucial porque muchas veces las referencias no tienen el número al inicio
        vancouver_score = 0
        
        # Patrón muy característico de Vancouver: año seguido de punto y coma "2015; 12:" o "2021; 398:"
        if re.search(r'\d{4}\s*;\s*\d+:', linea):
            vancouver_score += 5  # Muy característico de Vancouver
        
        # Patrón: "Apellido Inicial" sin coma entre apellido e inicial (ej. "Safi N", "Singh L")
        # Cuenta cuántos autores con este patrón hay
        autores_vancouver = re.findall(r'\b[A-Z][a-z]+\s+[A-Z]{1,3}\b', linea)
        if len(autores_vancouver) >= 2:
            vancouver_score += 3  # Múltiples autores en formato Vancouver
        elif len(autores_vancouver) == 1:
            vancouver_score += 2
        
        # Patrón: volumen:páginas (ej. "398: 1418-82" o "12:464-74")
        if re.search(r'\d+:\s*\d+-\d+\.?', linea):
            vancouver_score += 2
        
        # Patrón: abreviaturas médicas comunes en Vancouver
        if re.search(r'\b(?:N Engl J Med|Lancet|JAMA|BMJ|Ann Intern Med|Nat Rev|Am J|Int J Environ Res Public Health)\b', linea):
            vancouver_score += 2
        
        # Si tiene número al inicio "1. ", sumar punto adicional
        if re.match(r'^\d+\.\s+', linea):
            vancouver_score += 1
        
        # Si acumuló puntos de Vancouver, registrarlo
        if vancouver_score >= 4:  # Umbral mínimo para considerar Vancouver
            patrones['Vancouver'] += vancouver_score
            continue  # No evaluar otros estilos si ya es Vancouver
        
        # IEEE: [1], [2], etc. - DEBE ser verificado después de Vancouver
        if re.match(r'^\[\d+\]', linea):
            patrones['IEEE'] += 3  # Mayor peso para corchetes explícitos
        # Detectar IEEE por patrones característicos: "et al.", "pp.", "vol.", "no."
        elif re.search(r'\bet al\b.*?,.*?(?:pp\.|vol\.|no\.|IEEE)', linea, re.IGNORECASE):
            patrones['IEEE'] += 2
        # Detectar formato IEEE con comillas en título y sin paréntesis en año
        elif re.search(r'"[^"]+",.*?\d{4}', linea) and not re.search(r'\(\d{4}\)', linea):
            patrones['IEEE'] += 2
        
        # Harvard: (año) sin punto - Ejemplo: "Smith, J. (2024) Title of work"
        # IMPORTANTE: Debe chequearse ANTES que APA
        elif re.search(r'\(\d{4}\)\s+[A-Za-z]', linea) and not re.search(r'\(\d{4}\)\.', linea):
            patrones['Harvard'] += 1
        
        # APA: (año). con punto - Ejemplo: "Smith, J. (2024). Title of work"
        elif re.search(r'\(\d{4}\)\.\s*', linea):
            patrones['APA'] += 1
        
        # Chicago: Nombres completos, comas
        elif re.search(r'^[A-Z][a-z]+,\s+[A-Z][a-z]+', linea):
            patrones['Chicago'] += 1
        
        # MLA: Apellido, Nombre.
        elif re.search(r'^[A-Z][a-z]+,\s+[A-Z][a-z]+\.', linea):
            patrones['MLA'] += 1
    
    # Determinar estilo predominante
    if not patrones:
        return {'estilo': 'Desconocido', 'confianza': 0}
    
    estilo_detectado = max(patrones.keys(), key=lambda k: patrones[k])
    coincidencias = patrones[estilo_detectado]
    total_referencias = len(textos_refs)
    
    # Calcular confianza como porcentaje
    confianza = int((coincidencias / total_referencias) * 100) if total_referencias > 0 else 0
    
    # Debug info
    print(f"[DEBUG] Patrones detectados: {dict(patrones)}")
    print(f"[DEBUG] Estilo: {estilo_detectado}, Confianza: {confianza}%")
    
    return {
        'estilo': estilo_detectado,
        'confianza': confianza
    }


def construir_texto_referencia(ref: Dict[str, str]) -> str:
    """
    Construye un texto de referencia desde campos estructurados.
    Se usa como fallback cuando no existe el campo 'raw'.
    
    Args:
        ref: Diccionario con campos de referencia
        
    Returns:
        Texto de referencia construido
    """
    partes = []
    
    # Autores
    if 'autores' in ref and ref['autores']:
        partes.append(ref['autores'])
    
    # Año
    if 'año' in ref and ref['año']:
        partes.append(f"({ref['año']})")
    
    # Título
    if 'titulo' in ref and ref['titulo']:
        partes.append(ref['titulo'])
    
    # Publicación
    if 'publicacion' in ref and ref['publicacion']:
        partes.append(ref['publicacion'])
    
    # Volumen y páginas
    if 'volumen' in ref and ref['volumen']:
        vol_texto = f"Vol. {ref['volumen']}"
        if 'paginas' in ref and ref['paginas']:
            vol_texto += f", pp. {ref['paginas']}"
        partes.append(vol_texto)
    elif 'paginas' in ref and ref['paginas']:
        partes.append(f"pp. {ref['paginas']}")
    
    return ". ".join(partes) if partes else ""


def obtener_descripcion_estilo(estilo: str) -> str:
    """
    Retorna una descripción breve del estilo de citación detectado.
    
    Args:
        estilo: Nombre del estilo (IEEE, APA, etc.)
        
    Returns:
        Descripción del estilo
    """
    descripciones = {
        'IEEE': 'Institute of Electrical and Electronics Engineers - Común en ingeniería y ciencias de la computación',
        'APA': 'American Psychological Association - Común en ciencias sociales y psicología',
        'Vancouver': 'Estilo Vancouver - Común en ciencias médicas y biomédicas',
        'Chicago': 'Chicago Manual of Style - Común en humanidades e historia',
        'Harvard': 'Harvard Style - Común en Reino Unido y ciencias sociales',
        'MLA': 'Modern Language Association - Común en literatura y humanidades',
        'Desconocido': 'No se pudo determinar el estilo de citación'
    }
    
    return descripciones.get(estilo, 'Estilo de citación no especificado')
