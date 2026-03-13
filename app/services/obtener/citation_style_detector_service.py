import re
from typing import List, Dict, Any
from collections import defaultdict


# ──────────────────────────────────────────────────────────────────────────────
# Patrones ACM (Association for Computing Machinery)
#
# Formato ACM estándar:
#   [1] Lastname, F., Lastname2, F2., and Lastname3, F3. Year. Title of article.
#       Journal/Conf Name vol, issue (Month Year), pages. DOI
#
# Diferencia clave con IEEE (también usa corchetes):
#   - ACM: "[1] Smith, J., Jones, A. 2020. Title..." — Apellido, Inicial. INVERTIDO + año suelto
#   - IEEE: "[1] J. Smith, A. Jones, \"Title...\"" — Inicial. Apellido NO invertido + título entre comillas
#
# Señales muy fuertes (peso 4):
#   1. DOI con prefijo 10.1145 — identificador exclusivo de ACM Digital Library
#
# Señales fuertes (peso 3):
#   2. Corchete + Apellido, Inicial. — nombre invertido con coma (diferencia con IEEE)
#   3. Año suelto (sin paréntesis) después de autores: "Smith, J. 2020. Title"
#   4. Formato de volumen ACM: "vol, issue (Mes Año), páginas" — sin "vol." explícito
#   5. "Article X, Y pages." — formato exclusivo de artículos ACM
#   6. Revistas/conferencias ACM conocidas: "Commun. ACM", "ACM Trans.", etc.
#
# Señales moderadas (peso 2):
#   7. "In Proceedings of" o "Proc. of" — conferencias ACM
# ──────────────────────────────────────────────────────────────────────────────

_ACM_PATTERNS = [
    # 1. DOI con prefijo ACM (10.1145) — muy exclusivo
    (r'doi\.org/10\.1145/', 4),

    # 2. Corchete + Apellido, Inicial. — nombre invertido (diferencia con IEEE)
    #    Ej: "[1] Smith, J., Jones, A. ..."
    (r'^\[\d+\]\s+[A-Z][a-z]+,\s+[A-Z]\.', 3),

    # 3. Año suelto después de autores (sin paréntesis)
    #    Ej: "Smith, J. 2020. Title of paper."
    (r'[A-Z]\.\s+\d{4}\.\s+[A-Z]', 3),

    # 4. Formato de volumen/issue ACM: "64, 5 (May 2021), 88-95"
    #    vol, issue (Mes Año), páginas — sin "vol." explícito antes
    (r'\d+,\s+\d+\s+\(\w+\s+\d{4}\),\s*\d+', 3),

    # 5. "Article X, Y pages." — exclusivo de artículos ACM
    (r'Article\s+\d+.*?\d+\s+pages?\.', 3),

    # 6. Revistas y conferencias ACM conocidas
    (r'\b(?:Commun\.?\s*ACM|ACM\s+Trans\.|ACM\s+Comput\.\s+Surv\.|ACM\s+SIGPLAN|ACM\s+SIGCOMM|ACM\s+SIGCHI|CACM|ACM\s+CCS|CHI\s+\d{4}|PLDI|SOSP|OSDI|SIGMOD|VLDB|ICSE|FSE|ISCA|MICRO|ASPLOS)\b', 3),

    # 7. "In Proceedings of the ACM..." o "Proc. of the ACM..."
    (r'\bIn Proceedings of\b|\bProc\.\s+of\b', 2),
]


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

    patrones = defaultdict(int)

    for linea in textos_refs:
        linea = linea.strip()
        if not linea:
            continue

        # ── Vancouver ────────────────────────────────────────────────────────
        vancouver_score = 0

        # Año + punto y coma + volumen + colon: "2015;12:" muy característico
        if re.search(r'\d{4}\s*;\s*\d+:', linea):
            vancouver_score += 5

        # Autores formato "Apellido Inicial" sin coma (ej. "Safi N", "Singh L")
        autores_vancouver = re.findall(r'\b[A-Z][a-z]+\s+[A-Z]{1,3}\b', linea)
        if len(autores_vancouver) >= 2:
            vancouver_score += 3
        elif len(autores_vancouver) == 1:
            vancouver_score += 2

        # volumen:páginas "12:464-74"
        if re.search(r'\d+:\s*\d+-\d+\.?', linea):
            vancouver_score += 2

        # Abreviaturas de revistas médicas
        if re.search(r'\b(?:N Engl J Med|Lancet|JAMA|BMJ|Ann Intern Med|Nat Rev|Am J|Int J Environ Res Public Health)\b', linea):
            vancouver_score += 2

        # Número inicial con punto "1. "
        if re.match(r'^\d+\.\s+', linea):
            vancouver_score += 1

        if vancouver_score >= 4:
            patrones['Vancouver'] += vancouver_score
            continue

        # ── ACM ──────────────────────────────────────────────────────────────
        # ACM también usa corchetes [N] pero con nombre invertido y año suelto.
        # Se evalúa antes de IEEE para capturar las señales específicas de ACM.
        acm_score = 0
        for patron, peso in _ACM_PATTERNS:
            if re.search(patron, linea):
                acm_score += peso

        if acm_score >= 3:
            patrones['ACM'] += acm_score
            continue

        # ── IEEE ─────────────────────────────────────────────────────────────
        if re.match(r'^\[\d+\]', linea):
            patrones['IEEE'] += 3
            continue

        if re.search(r'\bet al\b.*?,.*?(?:pp\.|vol\.|no\.|IEEE)', linea, re.IGNORECASE):
            patrones['IEEE'] += 2
            continue

        # IEEE: título entre comillas + año sin paréntesis
        if re.search(r'"[^"]+",.*?\d{4}', linea) and not re.search(r'\(\d{4}\)', linea):
            patrones['IEEE'] += 2
            continue

        # ── Harvard ──────────────────────────────────────────────────────────
        # (año) sin punto — "Smith, J. (2024) Title"
        if re.search(r'\(\d{4}\)\s+[A-Za-z]', linea) and not re.search(r'\(\d{4}\)\.', linea):
            patrones['Harvard'] += 1
            continue

        # ── APA ──────────────────────────────────────────────────────────────
        # (año). con punto — "Smith, J. (2024). Title"
        if re.search(r'\(\d{4}\)\.\s*', linea):
            patrones['APA'] += 1
            continue

        # ── MLA ──────────────────────────────────────────────────────────────
        # Apellido, Nombre. (nombre invertido con punto al final del nombre)
        if re.search(r'^[A-Z][a-z]+,\s+[A-Z][a-z]+\.', linea):
            patrones['MLA'] += 1
            continue


    if not patrones:
        return {'estilo': 'Desconocido', 'confianza': 0}

    estilo_detectado = max(patrones.keys(), key=lambda k: patrones[k])
    coincidencias = patrones[estilo_detectado]
    total_referencias = len(textos_refs)

    confianza = int((coincidencias / total_referencias) * 100) if total_referencias > 0 else 0

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
