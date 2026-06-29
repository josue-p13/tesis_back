import unicodedata
import re
from typing import Any, Dict

SIMILITUD_MINIMA = 0.4
SIMILITUD_ALTA   = 0.8


def _normalizar(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto.lower())
    
    # Eliminar guiones en palabras compuestas (ej: "socio-cultural" → "sociocultural")
    # Reemplazar guión entre letras por nada (une la palabra)
    texto = re.sub(r'(\w)-(\w)', r'\1\2', texto)
    
    for char in ("-", ":", ".", "®", "©"):
        texto = texto.replace(char, " " if char not in ("®", "©") else "")
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _similitud_titulos(titulo_original: str, titulo_verificado: str) -> float:
    if not titulo_original or not titulo_verificado:
        return 0.0
    palabras_orig  = set(_normalizar(titulo_original).split())
    palabras_verif = set(_normalizar(titulo_verificado).split())
    union = len(palabras_orig | palabras_verif)
    return 0.0 if union == 0 else len(palabras_orig & palabras_verif) / union


def _score_autores(autores_ref: str, nombres_api: list) -> float:
    if not autores_ref:
        return 1.0
    if not nombres_api:
        return 0.0
    partes_ref = {
        token
        for autor in autores_ref.split(",")
        for token in _normalizar(autor).split()
        if len(token) > 1
    }
    if not partes_ref:
        return 1.0
    nombres_api_norm = _normalizar(" ".join(nombres_api))
    coincidencias = sum(1 for parte in partes_ref if parte in nombres_api_norm)
    return coincidencias / len(partes_ref)


def _validar_resultado(titulo_orig: str, titulo_verif: str, autores_ref: str, nombres_api: list) -> bool:
    """Título muy similar reduce la exigencia en autores, pero nunca los ignora."""
    similitud_titulo = _similitud_titulos(titulo_orig, titulo_verif)
    if similitud_titulo < SIMILITUD_MINIMA:
        return False
    score_autores = _score_autores(autores_ref, nombres_api)
    if similitud_titulo >= SIMILITUD_ALTA:
        return score_autores >= 0.2
    return score_autores >= 0.3


def _extraer_arxiv_id(url: str) -> str:
    if "arxiv.org/abs/" not in url:
        return ""
    return url.split("arxiv.org/abs/")[-1].split("/")[0].rstrip(".")


def _resultado_base() -> Dict[str, Any]:
    return {
        "encontrado": False,
        "fuente": "",
        "titulo_verificado": "",
        "doi_encontrado": "",
        "citaciones": 0,
        "url": "",
    }