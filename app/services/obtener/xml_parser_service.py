import xml.etree.ElementTree as ET
import re
import unicodedata
from typing import List, Dict


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_AÑO_RE = re.compile(r"\b(19\d{2}|20[0-3]\d)\b")
_MARCADORES_ACCESO_RE = re.compile(
    r"(?i)\b(?:recuperado\s+(?:el|de)|consultado\s+el|retrieved\s+from|accessed\s+on|available\s+at|disponible\s+en|en\s+l[ií]nea|obtenido\s+de)\b"
)
_NUMERO_INICIO_RE = re.compile(r"^\s*(?:\[\d+\]|\d+\.)\s*")
_URL_LINEA_RE = re.compile(r"^\s*https?://\S+\s*$", re.IGNORECASE)
_AÑO_PAREN_RE = re.compile(r"\(\s*(19\d{2}|20[0-3]\d)[a-z]?\s*\)")
_TITULO_COMILLAS_RE = re.compile(r'(?:\"([^\"]{6,200})\"|“([^”]{6,200})”)')
_AUTOR_ANO_INICIO_RE = re.compile(
    r"^\s*[A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ'`\-]+,\s+.{0,60}\(\s*(19\d{2}|20[0-3]\d)[a-z]?\s*\)",
    re.UNICODE,
)
_TIPO_DOC_RE = re.compile(
    r'[.,\s]*\b(?:master\'?s?\s+thesis|phd\s+thesis|tesis\s+(?:de\s+)?'
    r'(?:maestr[ií]a|doctoral|de\s+grado)|doctoral\s+dissertation|'
    r'trabajo\s+(?:fin\s+de\s+(?:m[áa]ster|grado)|de\s+grado))\b\s*$',
    re.IGNORECASE | re.UNICODE
)


def _normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    texto = unicodedata.normalize("NFKC", texto)
    texto = texto.replace("\u00a0", " ").replace("\u200b", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def _strip_puntuacion_final(texto: str) -> str:
    return texto.rstrip(" \t\r\n,;:.")


def _extraer_url(texto: str) -> str:
    if not texto:
        return ""
    match = _URL_RE.search(texto)
    if not match:
        return ""
    url = match.group(0).strip().strip("()[]{}<>.,;")
    return url


def _extraer_doi(texto: str) -> str:
    if not texto:
        return ""
    match = _DOI_RE.search(texto)
    if match:
        doi = match.group(0)
    else:
        match = re.search(r"https?://doi\.org/(\S+)", texto, re.IGNORECASE)
        if not match:
            return ""
        doi = match.group(1)
    doi = doi.strip().strip("()[]{}<>.,;")
    doi = doi.rstrip(".")
    return doi


def _extraer_año(texto: str) -> str:
    if not texto:
        return ""
    match = _AÑO_RE.search(texto)
    if not match:
        return ""
    año = match.group(1)
    return año if 1900 <= int(año) <= 2030 else ""


def _cortar_en_marcador_acceso(texto: str) -> str:
    if not texto:
        return ""
    match = _MARCADORES_ACCESO_RE.search(texto)
    if not match:
        return texto
    return texto[:match.start()].strip()


def _limpiar_campo_textual(texto: str) -> str:
    texto = _normalizar_texto(texto)
    texto = _cortar_en_marcador_acceso(texto)
    texto = _TIPO_DOC_RE.sub("", texto)   # Bug 3 fix: elimina "Master's thesis", "Tesis de maestría", etc.
    texto = _URL_RE.sub("", texto)
    texto = _normalizar_texto(texto)
    texto = _strip_puntuacion_final(texto)
    return texto


def _quitar_prefijo_enumeracion(texto: str) -> str:
    return _NUMERO_INICIO_RE.sub("", texto or "").strip()


def _es_inicio_referencia_linea(linea: str) -> bool:
    if not linea:
        return False
    linea = linea.strip()
    if not linea:
        return False
    if _NUMERO_INICIO_RE.match(linea):
        return True
    if _URL_LINEA_RE.match(linea):
        return True
    if _AUTOR_ANO_INICIO_RE.match(linea):
        return True
    if _URL_RE.search(linea) and len(linea) <= 200:
        return True
    return False


def _split_raw_referencias(raw: str) -> List[str]:
    if not raw:
        return []

    raw = unicodedata.normalize("NFKC", raw)
    raw = raw.replace("\u00a0", " ").replace("\u200b", " ")
    raw = raw.replace("\\n", "\n")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    lineas: List[str] = []
    for l in raw.split("\n"):
        ln = _normalizar_texto(l)
        if ln:
            lineas.append(ln)

    if len(lineas) <= 1:
        raw_una_linea = _normalizar_texto(raw)

        # Estilo numerado [N]
        cortes = [m.start() for m in re.finditer(r"\[\d+\]\s+", raw_una_linea) if m.start() > 0]
        if cortes:
            puntos = [0] + cortes + [len(raw_una_linea)]
            partes = [raw_una_linea[puntos[i]:puntos[i + 1]].strip() for i in range(len(puntos) - 1)]
            partes = [p for p in partes if len(p) >= 15]
            if len(partes) >= 2:
                return partes

        # Bug 2 fix: APA fusionado en una sola línea sin saltos
        cortes_apa = [
            m.start() for m in re.finditer(
                r'(?<=\.)\s+(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ\w.-]+(?:,\s[A-Z][a-z]|\s\())',
                raw_una_linea
            )
            if m.start() > 20
        ]
        if cortes_apa:
            puntos = [0] + cortes_apa + [len(raw_una_linea)]
            partes = [raw_una_linea[puntos[i]:puntos[i + 1]].strip() for i in range(len(puntos) - 1)]
            partes = [p for p in partes if _AÑO_RE.search(p) and len(p) >= 15]
            if len(partes) >= 2:
                return partes

        return [raw_una_linea]

    segmentos: List[str] = []
    actual: List[str] = []

    for linea in lineas:
        if _es_inicio_referencia_linea(linea) and actual:
            segmentos.append(_normalizar_texto(" ".join(actual)))
            actual = [linea]
        else:
            actual.append(linea)

    if actual:
        segmentos.append(_normalizar_texto(" ".join(actual)))

    segmentos = [s for s in segmentos if len(s) >= 15]
    return segmentos if len(segmentos) >= 2 else [_normalizar_texto(raw)]


def _extraer_titulo_desde_raw(raw: str) -> str:
    if not raw:
        return ""

    match = _TITULO_COMILLAS_RE.search(raw)
    if match:
        titulo = match.group(1) or match.group(2) or ""
        titulo = _limpiar_campo_textual(titulo)
        if 6 <= len(titulo) <= 220:
            return titulo

    match_paren = _AÑO_PAREN_RE.search(raw)
    if match_paren:
        idx = match_paren.end()
    else:
        match_año = _AÑO_RE.search(raw)
        idx = match_año.end() if match_año else 0

    if idx <= 0:
        return ""

    after = raw[idx:]
    after = re.sub(r"^[\s\)\]\}\.,;:-]+", "", after).strip()
    after = _cortar_en_marcador_acceso(after)
    after = re.split(r"\s(?:doi:\s*|https?://)", after, maxsplit=1, flags=re.IGNORECASE)[0]
    after = after.split(". ", 1)[0]
    titulo = _limpiar_campo_textual(after)
    if 6 <= len(titulo) <= 220:
        return titulo
    return ""


def _extraer_autores_desde_raw(raw: str) -> str:
    if not raw:
        return ""

    match_paren = _AÑO_PAREN_RE.search(raw)
    if not match_paren or match_paren.start() > 160:
        return ""

    candidatos = raw[:match_paren.start()]
    candidatos = _quitar_prefijo_enumeracion(candidatos)
    candidatos = candidatos.strip().strip(" ,;:.")
    candidatos = _normalizar_texto(candidatos)

    if 3 <= len(candidatos) <= 200:
        return candidatos
    return ""


def _limpiar_referencia(ref: Dict[str, str]) -> Dict[str, str]:
    raw = _normalizar_texto(ref.get("raw", ""))

    if raw:
        ref["raw"] = raw

    for campo in ("titulo", "publicacion"):
        if campo in ref and ref[campo]:
            ref[campo] = _limpiar_campo_textual(ref[campo])

    if not ref.get("url"):
        url = _extraer_url(raw) or _extraer_url(ref.get("titulo", "")) or _extraer_url(ref.get("publicacion", ""))
        if url:
            ref["url"] = url

    if not ref.get("doi"):
        doi = _extraer_doi(raw) or _extraer_doi(ref.get("titulo", "")) or _extraer_doi(ref.get("publicacion", ""))
        if doi:
            ref["doi"] = doi

    if not ref.get("año"):
        año = _extraer_año(raw)
        if año:
            ref["año"] = año

    titulo_actual = ref.get("titulo") or ""
    publicacion_actual = ref.get("publicacion") or ""
    if not titulo_actual or titulo_actual == publicacion_actual:
        titulo = _extraer_titulo_desde_raw(raw)
        if titulo:
            ref["titulo"] = titulo

    if not ref.get("autores"):
        autores = _extraer_autores_desde_raw(raw)
        if autores:
            ref["autores"] = autores

    if "titulo" in ref and ref.get("titulo") in ("", None):
        ref.pop("titulo", None)

    if "publicacion" in ref and ref.get("publicacion") in ("", None):
        ref.pop("publicacion", None)

    return ref


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
        ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
        referencias = []

        for biblStruct in root.findall('.//tei:listBibl/tei:biblStruct', ns):
            ref_base: Dict[str, str] = {}

            raw_elem = biblStruct.find('.//tei:note[@type="raw_reference"]', ns)
            if raw_elem is not None and raw_elem.text:
                ref_base['raw'] = raw_elem.text.strip()

            # Bug 1 fix: respetar modelo TEI — analytic=artículo, monogr=revista/libro
            titulo_analytic = ""
            titulo_monogr = ""

            titulo_elem = biblStruct.find('.//tei:analytic/tei:title[@type="main"]', ns)
            if titulo_elem is not None and titulo_elem.text:
                titulo_analytic = titulo_elem.text.strip()

            titulo_monogr_elem = biblStruct.find('.//tei:monogr/tei:title', ns)
            if titulo_monogr_elem is not None and titulo_monogr_elem.text:
                titulo_monogr = titulo_monogr_elem.text.strip()

            if titulo_analytic:
                ref_base['titulo'] = titulo_analytic
                if titulo_monogr and titulo_monogr != titulo_analytic:
                    ref_base['publicacion'] = titulo_monogr
            else:
                if titulo_monogr:
                    ref_base['titulo'] = titulo_monogr
                # publicacion queda vacío intencionalmente para libros/tesis/webs

            # Autores
            autores = []
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
                ref_base['autores'] = ', '.join(autores)

            # Año
            año = None
            fecha_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:date[@type="published"]', ns)
            if fecha_elem is not None:
                when_attr = fecha_elem.get('when')
                if when_attr:
                    año_match = when_attr[:4] if len(when_attr) >= 4 else when_attr
                    if año_match.isdigit() and 1900 <= int(año_match) <= 2030:
                        año = año_match
                if not año and fecha_elem.text:
                    m = re.search(r'\b(19\d{2}|20[0-3]\d)\b', fecha_elem.text.strip())
                    if m:
                        año = m.group(1)

            if not año:
                for fecha_elem in biblStruct.findall('.//tei:monogr/tei:imprint/tei:date', ns):
                    when_attr = fecha_elem.get('when')
                    if when_attr:
                        año_match = when_attr[:4] if len(when_attr) >= 4 else when_attr
                        if año_match.isdigit() and 1900 <= int(año_match) <= 2030:
                            año = año_match
                            break

            if año:
                ref_base['año'] = año

            # DOI
            doi_elem = biblStruct.find('.//tei:idno[@type="DOI"]', ns)
            if doi_elem is not None and doi_elem.text:
                ref_base['doi'] = doi_elem.text.strip()

            # URL
            ptr_elem = biblStruct.find('.//tei:ptr', ns)
            if ptr_elem is not None:
                target = ptr_elem.get('target', '').strip()
                if target.startswith('http'):
                    ref_base['url'] = target

            # Volumen y páginas
            volumen_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:biblScope[@unit="volume"]', ns)
            if volumen_elem is not None and volumen_elem.text:
                ref_base['volumen'] = volumen_elem.text.strip()

            paginas_elem = biblStruct.find('.//tei:monogr/tei:imprint/tei:biblScope[@unit="page"]', ns)
            if paginas_elem is not None:
                pagina_inicio = paginas_elem.get('from', '')
                pagina_fin = paginas_elem.get('to', '')
                if pagina_inicio and pagina_fin:
                    ref_base['paginas'] = f"{pagina_inicio}-{pagina_fin}"
                elif pagina_inicio:
                    ref_base['paginas'] = pagina_inicio

            # Bug 2 fix: dividir referencias fusionadas por GROBID
            raw_texto = ref_base.get("raw", "")
            partes_raw = _split_raw_referencias(raw_texto) if raw_texto else []
            if len(partes_raw) >= 2:
                # En referencias fusionadas, no heredamos campos textuales (titulo/autores/publicacion)
                # para evitar contaminar segmentos; solo campos técnicos seguros.
                campos_tei = ("doi", "url", "volumen", "paginas")
                for idx, parte in enumerate(partes_raw):
                    ref_parte: Dict[str, str] = {"raw": parte}
                    if idx == 0:
                        for campo in campos_tei:
                            if campo in ref_base and ref_base[campo]:
                                ref_parte[campo] = ref_base[campo]
                    referencias.append(_limpiar_referencia(ref_parte))
                continue

            if ref_base:
                referencias.append(_limpiar_referencia(ref_base))

        return referencias

    except ET.ParseError as e:
        return [{"error": f"Error al parsear XML: {str(e)}", "xml_raw": xml_texto[:500]}]
