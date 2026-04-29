import re
from typing import List, Dict, Any
from collections import defaultdict


_ESTILOS_FEATURES = {
    "IEEE": [
        re.compile(r"^\[\d+\]\s*", re.IGNORECASE),
        re.compile(r"\b(?:vol\.|no\.|pp\.|IEEE)\b", re.IGNORECASE),
        re.compile(r"(?:\"[^\"]+\"|“[^”]+”)", re.IGNORECASE),
    ],
    "APA": [
        re.compile(r"\(\d{4}\)\.\s*", re.IGNORECASE),
        re.compile(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ-]+,\s*(?:[A-Z]\.\s*){1,3}", re.IGNORECASE),
        re.compile(r"\b(?:doi:\s*|https?://doi\.org/)\S+", re.IGNORECASE),
    ],
    "Harvard": [
        re.compile(r"\(\d{4}\)\s+(?!\.)", re.IGNORECASE),
        re.compile(r"\(\d{4}\)\s+[A-ZÁÉÍÓÚÑ]", re.IGNORECASE),
        re.compile(r"\bpp\.\s*\d+", re.IGNORECASE),
    ],
    "Vancouver": [
        re.compile(r"^\d+\.\s+", re.IGNORECASE),
        re.compile(r"\d{4}\s*;\s*\d+", re.IGNORECASE),
        re.compile(r"\d+:\s*\d+-\d+", re.IGNORECASE),
    ],
    "ACM": [
        re.compile(r"^\[\d+\]\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ-]+,\s+[A-Z]\.", re.IGNORECASE),
        re.compile(r"\b(?:doi\.org/10\.1145/|10\.1145/)\b", re.IGNORECASE),
        re.compile(r"\b(?:In Proceedings of|Proc\.\s+of|ACM)\b", re.IGNORECASE),
    ],
    "MLA": [
        re.compile(r"^[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ-]+,\s+[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ-]+\.", re.IGNORECASE),
        re.compile(r"\b(?:Accessed|Consultado el|Recuperado el)\b", re.IGNORECASE),
        re.compile(r"\b(?:Print|Web)\b", re.IGNORECASE),
    ],
}


def detectar_estilo_citacion(referencias: List[Dict[str, str]]) -> str:
    """
    Detecta el estilo de citación bibliográfica usando patrones RegEx.

    Analiza el campo 'raw' (texto original) de las referencias o construye
    texto desde los campos estructurados como fallback.

    Estilos soportados:
    - IEEE: [1], [2], etc. (Inicial. Apellido, título entre comillas)
    - ACM: [1], [2], etc. (Apellido, Inicial. año suelto, sin comillas en título)
    - Vancouver: numeración, autores Apellido Inicial sin coma, vol:págs
    - APA: (2020). Autor (formato con año entre paréntesis seguido de punto)
    - Harvard: (2020) sin punto después del año
    - MLA: Apellido, Nombre. (nombre invertido con punto)

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
    Clasifica el estilo de citación usando análisis de patrones RegEx ponderados.

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

    puntajes: Dict[str, int] = defaultdict(int)
    referencias_con_texto = 0

    for linea in textos_refs:
        linea = linea.strip()
        if not linea:
            continue
        referencias_con_texto += 1
        for estilo, features in _ESTILOS_FEATURES.items():
            puntajes[estilo] += sum(1 for patron in features if patron.search(linea))

    if not puntajes or referencias_con_texto == 0:
        return {'estilo': 'Desconocido', 'confianza': 0}

    estilo_detectado = max(puntajes.keys(), key=lambda k: puntajes[k])
    coincidencias = puntajes[estilo_detectado]
    maximo_posible = referencias_con_texto * len(_ESTILOS_FEATURES[estilo_detectado])
    confianza = int((coincidencias / maximo_posible) * 100) if maximo_posible > 0 else 0

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
        'ACM': 'Association for Computing Machinery - Común en ciencias de la computación e informática',
        'APA': 'American Psychological Association - Común en ciencias sociales y psicología',
        'Vancouver': 'Estilo Vancouver - Común en ciencias médicas y biomédicas',
        'Harvard': 'Harvard Style - Común en Reino Unido y ciencias sociales',
        'MLA': 'Modern Language Association - Común en literatura y humanidades',
        'Desconocido': 'No se pudo determinar el estilo de citación'
    }

    return descripciones.get(estilo, 'Estilo de citación no especificado')
