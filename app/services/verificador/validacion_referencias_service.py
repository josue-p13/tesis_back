import asyncio
from typing import Any, Dict, List, Optional, Tuple
from app.core.config import config

from app.services.obtener.text_utils_service import _similitud_titulos, _extraer_arxiv_id, _resultado_base, _normalizar
from app.services.language_service import traducir_si_es_espanol
from app.services.verificador import (
    api_openalex_service       as openalex,
    api_crossref_service       as crossref,
    api_semanticscholar_service as ss,
    api_pubmed_service         as pubmed,
    api_core_service           as core,
    api_googlebooks_service    as gbooks,
    api_serper_service         as serper,
)
from app.services.verificador.api_serper_service import SerperAuthError
from app.services.verificador.http_client import HTTP_CLIENT
from app.services.db.database_service import DatabaseService


# ──────────────────────────── búsqueda en BD local (caché) ────────────────────────────

def buscar_en_bd_primero(ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Busca la referencia en la BD antes de consultar APIs externas.
    Prioridad:
      1. DOI exacto
      2. Similitud de título (incluye publicacion y titulo_original)

    Si no se encuentra aquí, el flujo continúa a APIs académicas.
    Gemini entra después de APIs, no aquí.
    """
    def _formatear(resultado: Dict) -> Dict[str, Any]:
        return {
            "encontrado": True,
            "fuente": f"{resultado.get('fuente_verificacion', 'BD')} (desde BD)",
            "titulo_verificado": resultado.get('titulo', ''),
            "doi_encontrado": resultado.get('doi', ''),
            "citaciones": resultado.get('citaciones', 0),
            "url": resultado.get('url_verificada', ''),
            "autores_verificados": resultado.get('autores', ''),
            "desde_bd": True,
        }

    try:
        with DatabaseService() as db:
            # 1. Búsqueda por DOI exacto (más confiable)
            if ref.get('doi'):
                resultado = db.buscar_por_doi(ref['doi']) 
                if resultado:
                    return _formatear(resultado)

            # 2. Búsqueda por similitud de título (incluye publicacion y titulo_original)
            if ref.get('titulo'):
                resultado = db.buscar_por_titulo_similitud(
                    ref['titulo'],
                    ref.get('autores', '')
                )
                if resultado:
                    return _formatear(resultado)

            return None

    except ConnectionError:
        return None
    except Exception:
        return None


def _buscar_en_bd_por_score(ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Busca en BD candidatos obtenidos por autores/raw y elige el mejor
    mediante un scoring combinado programático.

    Solo se llama cuando BD simple (DOI + similitud título) y APIs académicas
    ya fallaron. Resuelve el caso en que el título en BD difiere del PDF
    (p.ej. título y publicación invertidos por Google Scholar).

    Scoring:
        similitud_titulo  * 0.40  — Jaccard sobre titulo, titulo_original y texto_raw (max)
        match_año         * 0.30  — coincidencia exacta del año (0 o 1)
        similitud_autores * 0.20  — tokens de apellidos compartidos
        similitud_raw     * 0.10  — Jaccard del texto_raw completo

    Threshold: score >= 0.65 para considerar que es la misma referencia.
    """
    def _formatear(resultado: Dict) -> Dict[str, Any]:
        return {
            "encontrado": True,
            "fuente": f"{resultado.get('fuente_verificacion', 'BD')} (desde BD por score)",
            "titulo_verificado": resultado.get('titulo', ''),
            "doi_encontrado": resultado.get('doi', ''),
            "citaciones": resultado.get('citaciones', 0),
            "url": resultado.get('url_verificada', ''),
            "autores_verificados": resultado.get('autores', ''),
            "desde_bd": True,
        }

    def _score_año(año_ref: str, año_bd: str) -> float:
        if not año_ref or not año_bd:
            return 0.0
        return 1.0 if año_ref.strip() == año_bd.strip() else 0.0

    def _score_autores(autores_ref: str, autores_bd: str) -> float:
        if not autores_ref or not autores_bd:
            return 0.0
        tokens_ref = set(t for t in _normalizar(autores_ref).split() if len(t) > 2)
        tokens_bd  = set(t for t in _normalizar(autores_bd).split()  if len(t) > 2)
        if not tokens_ref:
            return 0.0
        return len(tokens_ref & tokens_bd) / len(tokens_ref)

    THRESHOLD = config.SIMILITUD_TITULO_THRESHOLD

    try:
        with DatabaseService() as db:
            candidatos = db.obtener_candidatos_por_autores_y_raw(
                autores=ref.get('autores', ''),
                texto_raw=ref.get('raw', '')
            )

        if not candidatos:
            return None

        titulo_ref = ref.get('titulo', '')
        año_ref    = ref.get('año') or ref.get('anio', '')
        autores_ref = ref.get('autores', '')
        raw_ref    = ref.get('raw', '')

        mejor_score = 0.0
        mejor_candidato = None

        for c in candidatos:
            # similitud titulo: máximo contra titulo, titulo_original y texto_raw del candidato
            sim_titulo = max(
                _similitud_titulos(titulo_ref, c.get('titulo', '') or ''),
                _similitud_titulos(titulo_ref, c.get('titulo_original', '') or ''),
                _similitud_titulos(titulo_ref, c.get('texto_raw', '') or ''),
            )
            match_año       = _score_año(año_ref, c.get('año', '') or '')
            sim_autores     = _score_autores(autores_ref, c.get('autores', '') or '')
            sim_raw         = _similitud_titulos(raw_ref, c.get('texto_raw', '') or '')

            score = (
                sim_titulo  * 0.40
                + match_año * 0.30
                + sim_autores * 0.20
                + sim_raw   * 0.10
            )

            if score > mejor_score:
                mejor_score = score
                mejor_candidato = c

        if mejor_candidato and mejor_score >= THRESHOLD:
            print(
                f"[BD-score] Match por score ({mejor_score:.2f}): "
                f"{mejor_candidato.get('titulo', '')[:60]}"
            )
            return _formatear(mejor_candidato)

        return None

    except Exception as e:
        print(f"[BD-score] Error al calcular score: {e}")
        return None


async def guardar_en_bd_si_verificada(ref_original: Dict[str, Any], datos_validacion: Dict[str, Any]):
    """
    Guarda la referencia en BD solo si fue verificada exitosamente.
    
    Args:
        ref_original: Referencia original extraída
        datos_validacion: Datos obtenidos de la validación
    """
    # Solo guardar si fue encontrada y NO es una URL web simple
    if not datos_validacion.get("encontrado"):
        return
    
    # No guardar referencias web sin verificación académica
    fuente = datos_validacion.get("fuente", "")
    if "URL web" in fuente or "referencia web" in fuente.lower():
        return
    
    try:
        with DatabaseService() as db:
            # Preparar datos de verificación
            datos_verificacion = {
                "fuente": datos_validacion.get("fuente", ""),
                "citaciones": datos_validacion.get("citaciones", 0),
                "url": datos_validacion.get("url", "")
            }
            
            # Crear referencia completa combinando datos originales y validados
            referencia_completa = {
                "titulo": datos_validacion.get("titulo_verificado") or ref_original.get("titulo", ""),
                "titulo_original": ref_original.get("titulo", ""),  # título tal como vino del PDF
                "autores": datos_validacion.get("autores_verificados") or ref_original.get("autores", ""),
                "año": ref_original.get("año") or ref_original.get("anio", ""),
                "publicacion": ref_original.get("publicacion", ""),
                "doi": datos_validacion.get("doi_encontrado") or datos_validacion.get("doi") or ref_original.get("doi", ""),
                "volumen": ref_original.get("volumen", ""),
                "paginas": ref_original.get("paginas", ""),
                "raw": ref_original.get("raw", "")
            }
            
            # Guardar en BD
            db.guardar_referencia(
                referencia_completa, 
                fuente_documento="validacion_automatica",
                datos_verificacion=datos_verificacion
            )
            
    except Exception as e:
        print(f"Error al guardar en BD: {e}")


# ──────────────────────────── búsqueda por DOI ────────────────────────────

async def buscar_por_doi(doi: str) -> Dict[str, Any]:
    resultado = {"doi": doi, "encontrado": False}
    for buscar in (openalex.buscar_doi, crossref.buscar_doi, ss.buscar_doi, pubmed.buscar_doi, core.buscar_doi):
        datos = await buscar(doi)
        if datos:
            resultado.update(datos)
            return resultado
    return resultado


# ──────────────────────────── búsqueda por arXiv ────────────────────────────

async def buscar_por_arxiv_id(arxiv_id: str) -> Dict[str, Any]:
    datos = await ss.buscar_arxiv(arxiv_id)
    return datos if datos else _resultado_base()


# ──────────────────────────── búsqueda por título ────────────────────────────

async def buscar_por_titulo(titulo: str, autores: str = "") -> Dict[str, Any]:
    """
    Busca en APIs académicas y Google Books.
    Intenta primero con el título original; si falla, reintenta con traducción al inglés.
    """
    resultado   = {"titulo_buscado": titulo, "encontrado": False}
    t_traducido = None

    # Lista de servicios académicos a consultar
    SERVICIOS_ACADEMICOS = [
        openalex.buscar_titulo,
        crossref.buscar_titulo,
        ss.buscar_titulo,
        pubmed.buscar_titulo,
        core.buscar_titulo,
    ]

    async def _realizar_busqueda(t: str) -> List[Dict[str, Any]]:
        return [
            r for r in await asyncio.gather(*[s(t, autores) for s in SERVICIOS_ACADEMICOS])
            if r is not None
        ]

    # Intento 1: título original
    candidatos = await _realizar_busqueda(titulo)

    # Intento 2: traducción al inglés
    if not candidatos:
        t_traducido = await traducir_si_es_espanol(titulo)
        if t_traducido != titulo:
            print(f"[APIs] Reintentando con traducción: {t_traducido[:50]}...")
            candidatos = await _realizar_busqueda(t_traducido)

    # Fallback: Google Books
    if not candidatos:
        t_final  = t_traducido if t_traducido and t_traducido != titulo else titulo
        datos_gb = await gbooks.buscar_titulo(t_final, autores)
        if not datos_gb and t_final != titulo:
            datos_gb = await gbooks.buscar_titulo(titulo, autores)

        if datos_gb:
            resultado.update({
                "encontrado":         True,
                "fuente":             datos_gb["fuente"],
                "titulo_verificado":  datos_gb["titulo"],
                "doi_encontrado":     "",
                "citaciones":         0,
                "url":                datos_gb["url"],
                "autores_verificados": datos_gb.get("autores", ""),
            })
            if datos_gb.get("isbn"):
                resultado["isbn"] = datos_gb["isbn"]
        return resultado

    mejor = max(
        candidatos,
        key=lambda c: _similitud_titulos(titulo, c["titulo"]) + min(c.get("citaciones", 0) / 1000, 0.3),
    )
    resultado.update({
        "encontrado":          True,
        "fuente":              mejor["fuente"],
        "titulo_verificado":   mejor["titulo"],
        "doi_encontrado":      mejor["doi"],
        "citaciones":          mejor.get("citaciones", 0),
        "url":                 mejor["url"],
        "autores_verificados": mejor.get("autores", ""),
    })
    return resultado


async def buscar_por_serper(
    titulo: str,
    autores: str = "",
    serper_api_key: str = "",
    usar_serper: bool = False,
    permitir_traduccion: bool = False,
) -> Dict[str, Any]:
    """
    Último recurso: Google Scholar via Serper.
    Intenta primero con título original; si falla, reintenta con traducción al inglés (si se permite).
    """
    resultado = {"titulo_buscado": titulo, "encontrado": False}
    if not usar_serper or not serper_api_key:
        return resultado

    # Intento 1: título original
    datos = await serper.buscar_titulo_google_scholar(titulo, autores, serper_api_key=serper_api_key)

    # Intento 2: traducción al inglés (opcional)
    if (not datos or not datos.get("encontrado")) and permitir_traduccion:
        t_traducido = await traducir_si_es_espanol(titulo)
        if t_traducido != titulo:
            print(f"[Serper] Reintentando con traducción: {t_traducido[:50]}...")
            datos = await serper.buscar_titulo_google_scholar(
                t_traducido, autores,
                serper_api_key=serper_api_key,
                titulo_alternativo=titulo,
            )

    if datos and datos.get("encontrado"):
        resultado.update({
            "encontrado":          True,
            "fuente":              datos["fuente"],
            "titulo_verificado":   datos["titulo"],
            "doi_encontrado":      "",
            "citaciones":          datos.get("citaciones", 0),
            "url":                 datos["url"],
            "autores_verificados": datos.get("autores", ""),
        })
    return resultado


# ──────────────────────────── verificación de URL web ────────────────────────────

async def _verificar_url(url: str) -> bool:
    """Verifica que una URL web sea accesible haciendo un HEAD request."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    try:
        resp = await HTTP_CLIENT.head(url, headers=headers, follow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False


# ──────────────────────────── validación individual y masiva ────────────────────────────

async def _validar_referencia_individual(
    ref: Dict[str, Any],
    indice: int,
    serper_api_key: str = "",
    usar_serper: bool = False,
    permitir_traduccion: bool = False,
) -> Dict[str, Any]:
    resultado = {
        "indice": indice + 1,
        "titulo_original": ref.get("titulo", "Sin título"),
        "autores": ref.get("autores", ""),
        "año": ref.get("año") or ref.get("anio", ""),
        "doi_original": ref.get("doi", ""),
    }

    # ═══════════════════════════════════════════════════════════
    # PASO 1: BD LOCAL — DOI exacto o similitud de título
    # ═══════════════════════════════════════════════════════════
    datos_bd = buscar_en_bd_primero(ref)
    if datos_bd and datos_bd.get("encontrado"):
        resultado["validacion"] = datos_bd
        resultado["estado"] = "VERIFICADA (BD)"
        resultado["con_doi"] = bool(ref.get("doi"))
        if datos_bd.get("doi_encontrado"):
            resultado["doi_sugerido"] = datos_bd["doi_encontrado"]
        return resultado

    # ── PASO 2: APIs académicas ───────────────────────────────────────────
    datos_apis = None

    if ref.get("doi"):
        resultado["con_doi"] = True
        datos = await buscar_por_doi(ref["doi"])
        if datos["encontrado"]:
            datos_apis = datos
            resultado["estado"] = "VERIFICADA"
        elif ref.get("titulo"):
            # Si el DOI falló, intentamos buscar por el título que viene en la ref
            datos_titulo = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
            if datos_titulo["encontrado"]:
                datos_apis = datos_titulo
                resultado["estado"] = "ENCONTRADA_POR_TITULO (DOI fallido)"
            else:
                resultado["estado"] = "DOI_NO_ENCONTRADO"
        else:
            resultado["estado"] = "DOI_NO_ENCONTRADO"

    elif ref.get("url"):
        resultado["con_doi"] = False
        url_ref  = ref["url"]
        arxiv_id = _extraer_arxiv_id(url_ref)
        if arxiv_id:
            datos_arxiv = await buscar_por_arxiv_id(arxiv_id)
            if datos_arxiv["encontrado"]:
                await guardar_en_bd_si_verificada(ref, datos_arxiv)
                resultado.update({
                    "validacion":     datos_arxiv,
                    "estado":         "VERIFICADA",
                    "guardado_en_bd": True,
                })
                if datos_arxiv.get("doi_encontrado"):
                    resultado["doi_sugerido"] = datos_arxiv["doi_encontrado"]
                return resultado

        url_accesible = await _verificar_url(url_ref)
        datos_url     = {"encontrado": url_accesible, "fuente": "URL web", "url": url_ref}
        resultado.update({
            "validacion": datos_url,
            "estado":     "REFERENCIA_WEB" if url_accesible else "URL_NO_ACCESIBLE",
        })
        if url_accesible:
            await guardar_en_bd_si_verificada(ref, datos_url)
            resultado["guardado_en_bd"] = True
        return resultado

    elif ref.get("titulo"):
        resultado["con_doi"] = False
        datos = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
        if datos["encontrado"]:
            datos_apis = datos
            resultado["estado"] = "ENCONTRADA_POR_TITULO"
        else:
            resultado["estado"] = "NO_ENCONTRADA"

    else:
        resultado.update({"validacion": {"encontrado": False}, "estado": "SIN_DATOS_PARA_BUSCAR", "con_doi": False})
        return resultado

    if datos_apis:
        await guardar_en_bd_si_verificada(ref, datos_apis)
        resultado.update({
            "validacion":     datos_apis,
            "guardado_en_bd": True,
        })
        if datos_apis.get("doi_encontrado"):
            resultado["doi_sugerido"] = datos_apis["doi_encontrado"]
        return resultado

    # ── PASO 3: BD por score ──────────────────────────────────────────────
    datos_score = _buscar_en_bd_por_score(ref)
    if datos_score and datos_score.get("encontrado"):
        resultado.update({
            "validacion": datos_score,
            "estado":     "VERIFICADA (BD por score)",
        })
        if datos_score.get("doi_encontrado"):
            resultado["doi_sugerido"] = datos_score["doi_encontrado"]
        return resultado

    # ── PASO 4: Serper (último recurso) ───────────────────────────────────
    if ref.get("titulo") and usar_serper and serper_api_key:
        print(f"[Serper] Último recurso para: {ref['titulo'][:60]}")
        datos_serper = await buscar_por_serper(
            ref["titulo"], ref.get("autores", ""),
            serper_api_key=serper_api_key,
            usar_serper=usar_serper,
            permitir_traduccion=permitir_traduccion,
        )
        if datos_serper and datos_serper.get("encontrado"):
            await guardar_en_bd_si_verificada(ref, datos_serper)
            resultado.update({
                "validacion":     datos_serper,
                "estado":         "ENCONTRADA_GOOGLE_SCHOLAR",
                "guardado_en_bd": True,
            })
            if datos_serper.get("doi_encontrado"):
                resultado["doi_sugerido"] = datos_serper["doi_encontrado"]
            return resultado

    resultado["validacion" ] = {"encontrado": False}
    return resultado


async def validar_referencias(
    referencias: List[Dict],
    serper_api_key: str = "",
    usar_serper: bool = False,
    permitir_traduccion: bool = False,
) -> Dict[str, Any]:
    resultados = await asyncio.gather(*[
        _validar_referencia_individual(
            ref, i,
            serper_api_key=serper_api_key,
            usar_serper=usar_serper,
            permitir_traduccion=permitir_traduccion
        )
        for i, ref in enumerate(referencias)
    ])

    encontradas = no_encontradas = con_doi = sin_doi = desde_bd = guardadas_bd = desde_google_scholar = 0
    for r in resultados:
        if r["validacion"]["encontrado"]:
            encontradas += 1
            # Contar si vino desde BD
            if r["validacion"].get("desde_bd"):
                desde_bd += 1
            # Contar si se guardó en BD (las que NO vinieron de BD y fueron encontradas)
            elif r["estado"] not in ["REFERENCIA_WEB", "URL_NO_ACCESIBLE"]:
                guardadas_bd += 1
            
            # Contar si vino de Google Scholar
            fuente = r["validacion"].get("fuente", "")
            if "Google Scholar" in fuente or "Serper" in fuente:
                desde_google_scholar += 1
        else:
            no_encontradas += 1
        con_doi_val = r.pop("con_doi", False)
        if con_doi_val:
            con_doi += 1
        else:
            sin_doi += 1

    return {
        "total": len(referencias),
        "encontradas": encontradas,
        "no_encontradas": no_encontradas,
        "con_doi_original": con_doi,
        "sin_doi_original": sin_doi,
        "porcentaje_verificadas": round(encontradas / len(referencias) * 100, 1) if referencias else 0,
        "estadisticas_bd": {
            "servidas_desde_bd": desde_bd,
            "nuevas_guardadas_en_bd": guardadas_bd,
        },
        "estadisticas_google_scholar": {
            "encontradas_por_serper": desde_google_scholar,
            "serper_habilitado": usar_serper,
        },
        "referencias": list(resultados),
    }


async def cerrar_cliente():
    await HTTP_CLIENT.aclose()
