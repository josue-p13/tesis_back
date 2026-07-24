import re
from typing import List, Dict, Any
from collections import defaultdict


def detectar_estilo_citacion(referencias: List[Dict[str, str]]) -> str:
    """
    Detecta el estilo de citación bibliográfica usando patrones RegEx.

    Analiza el campo 'raw' (texto original) de las referencias o construye
    texto desde los campos estructurados como fallback.

    Estilos soportados:
    - IEEE: [1], [2], etc. (Inicial. Apellido, título entre comillas)
    - Vancouver: numeración, autores Apellido Inicial sin coma, vol:págs
    - APA: (2020). Autor (formato con año entre paréntesis seguido de punto)

    Args:
        referencias: Lista de referencias estructuradas extraídas por GROBID

    Returns:
        Nombre del estilo detectado o "Desconocido"
    """
    if not referencias:
        return "Desconocido"

    resultado = clasificar_estilo_local(referencias)
    return resultado['estilo']


def clasificar_estilo_local(referencias: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Clasifica el estilo de citación usando análisis de patrones RegEx ponderados acumulativos (soft-voting).

    Args:
        referencias: Lista de referencias estructuradas

    Returns:
        Dict con 'estilo' (nombre) y 'confianza' (0-100)
    """
    if not referencias:
        return {'estilo': 'Desconocido', 'confianza': 0}

    textos_refs = []
    for ref in referencias:
        if 'raw' in ref and ref['raw'].strip():
            textos_refs.append(ref['raw'].strip())
        else:
            texto_construido = construir_texto_referencia(ref)
            if texto_construido:
                textos_refs.append(texto_construido)

    if not textos_refs:
        return {'estilo': 'Desconocido', 'confianza': 0}

    votos = defaultdict(float)

    for linea in textos_refs:
        linea = linea.strip()
        if not linea:
            continue

        score_ieee = 0.0
        score_apa = 0.0
        score_vancouver = 0.0

        # ── 1. Indicadores de IEEE ──
        # Corchete inicial de numeración "[1]" o "[12]"
        if re.match(r'^\[\d+\]', linea):
            score_ieee += 5.0
        # Presencia de número entre corchetes en cualquier parte
        elif re.search(r'\[\d+\]', linea):
            score_ieee += 2.0

        # Presencia de páginas "pp. X-Y"
        if re.search(r'\bpp\.\s*\d+', linea):
            score_ieee += 2.0
        # Presencia de volumen "vol. X"
        if re.search(r'\bvol\.\s*\d+', linea):
            score_ieee += 1.5
        # Presencia de número/edición "no. X"
        if re.search(r'\bno\.\s*\d+', linea):
            score_ieee += 1.5

        # Título entre comillas (rectas o tipográficas)
        if re.search(r'["“\'‘].+?["”\'’]', linea):
            score_ieee += 2.0

        # Autores con iniciales primero (ej: "J. Smith" o "J. N. Smith")
        if re.search(r'\b[A-Z]\.\s*(?:[A-Z]\.\s*)*[A-Z][a-z]+', linea):
            score_ieee += 2.0

        # Año de 4 dígitos cerca del final
        if re.search(r'\b(19\d{2}|20[0-3]\d)\b\.?$', linea):
            score_ieee += 2.0

        # ── 2. Indicadores de APA / Harvard ──
        # Año entre paréntesis (ej: "(2020)")
        match_anio_parentesis = re.search(r'\((19\d{2}|20[0-3]\d)[a-z]?\)', linea)
        if match_anio_parentesis:
            score_apa += 4.0
            # Año entre paréntesis con punto después "(2020)."
            if re.search(r'\((19\d{2}|20[0-3]\d)[a-z]?\)\.', linea):
                score_apa += 2.0

        # Símbolo ampersand "&" para separar autores
        if '&' in linea:
            score_apa += 3.0

        # Autores invertidos: Apellido, Inicial. (ej: "Smith, J.")
        if re.search(r'\b[A-Z][a-zA-Záéíóúüñ\-]+,\s+[A-Z]\.', linea):
            score_apa += 3.0

        # Volumen(Número) sin punto y coma anterior: ej "12(3)"
        if re.search(r'\b\d+\(\d+\)', linea) and not re.search(r';\s*\d+', linea):
            score_apa += 2.0

        # ── 3. Indicadores de Vancouver ──
        # Año + punto y coma + volumen/edición: "2015;12" o "2015;12(3)"
        if re.search(r'\b(19\d{2}|20[0-3]\d)\s*;\s*\d+', linea):
            score_vancouver += 5.0
            if re.search(r'\b(19\d{2}|20[0-3]\d)\s*;\s*\d+(?:\(\d+\))?\s*:', linea):
                score_vancouver += 2.0

        # Número inicial con punto "1. " o "1 " al inicio seguido de letra
        if re.match(r'^\d+\.\s+', linea) or re.match(r'^\d+\s+[A-Z]', linea):
            score_vancouver += 1.5

        # Volumen y páginas separados por dos puntos: "12:123-145" o "12(3):123-145"
        if re.search(r'\b\d+(?:\(\d+\))?\s*:\s*\d+-\d+', linea):
            score_vancouver += 3.0

        # Autores formato Apellido Inicial sin coma (ej: "Smith J", "Jones AB")
        if re.search(r'\b[A-Z][a-zA-Záéíóúüñ\-]+\s+[A-Z]{1,3}\b', linea):
            score_vancouver += 2.5

        # Abreviaturas de revistas biomédicas comunes
        if re.search(r'\b(?:N Engl J Med|Lancet|JAMA|BMJ|Ann Intern Med|Nat Rev|Am J|Int J Environ Res Public Health)\b', linea):
            score_vancouver += 2.0

        # Sumar los pesos
        if score_ieee > 0:
            votos['IEEE'] += score_ieee
        if score_apa > 0:
            votos['APA'] += score_apa
        if score_vancouver > 0:
            votos['Vancouver'] += score_vancouver

    if not votos:
        return {'estilo': 'Desconocido', 'confianza': 0}

    estilo_detectado = max(votos.keys(), key=lambda k: votos[k])

    # Confianza basada en la proporción del ganador frente al total de votos acumulados
    total_votos = sum(votos.values())
    confianza = int((votos[estilo_detectado] / total_votos) * 100) if total_votos > 0 else 0

    # Umbral de peso mínimo acumulado para considerar una clasificación válida (ej. al menos 0.5 puntos por referencia promedio)
    if votos[estilo_detectado] < len(textos_refs) * 0.5:
        return {'estilo': 'Desconocido', 'confianza': 0}

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

    if 'autores' in ref and ref['autores']:
        partes.append(ref['autores'])

    if 'año' in ref and ref['año']:
        partes.append(f"({ref['año']})")

    if 'titulo' in ref and ref['titulo']:
        partes.append(ref['titulo'])

    if 'publicacion' in ref and ref['publicacion']:
        partes.append(ref['publicacion'])

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
        'Desconocido': 'No se pudo determinar el estilo de citación'
    }

    return descripciones.get(estilo, 'Estilo de citación no especificado')
