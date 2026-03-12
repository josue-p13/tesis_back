import asyncio
from typing import Any, Dict, List

from app.services.text_utils_service import _similitud_titulos, _extraer_arxiv_id, _resultado_base
from app.services.language_service import traducir_si_es_espanol
from app.services.apis import (
    api_openalex_service       as openalex,
    api_crossref_service       as crossref,
    api_semanticscholar_service as ss,
    api_pubmed_service         as pubmed,
    api_core_service           as core,
    api_googlebooks_service    as gbooks,
)
from app.services.apis.http_client import HTTP_CLIENT


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
    resultado = {"titulo_buscado": titulo, "encontrado": False}

    t = await traducir_si_es_espanol(titulo)

    candidatos = [
        r for r in await asyncio.gather(
            openalex.buscar_titulo(t, autores),
            crossref.buscar_titulo(t, autores),
            ss.buscar_titulo(t, autores),
            pubmed.buscar_titulo(t, autores),
            core.buscar_titulo(t, autores),
        )
        if r is not None
    ]

    # Fallback a Google Books solo si ninguna API académica encontró algo
    if not candidatos:
        datos_gb = await gbooks.buscar_titulo(t, autores)
        if datos_gb:
            resultado.update({
                "encontrado": True,
                "fuente": datos_gb["fuente"],
                "titulo_verificado": datos_gb["titulo"],
                "doi_encontrado": "",
                "citaciones": 0,
                "url": datos_gb["url"],
                "autores_verificados": datos_gb.get("autores", ""),
            })
            if datos_gb.get("isbn"):
                resultado["isbn"] = datos_gb["isbn"]
        return resultado

    # Elegir el mejor candidato por similitud de título + citaciones
    mejor = max(
        candidatos,
        key=lambda c: _similitud_titulos(titulo, c["titulo"]) + min(c.get("citaciones", 0) / 1000, 0.3),
    )
    resultado.update({
        "encontrado": True,
        "fuente": mejor["fuente"],
        "titulo_verificado": mejor["titulo"],
        "doi_encontrado": mejor["doi"],
        "citaciones": mejor.get("citaciones", 0),
        "url": mejor["url"],
        "autores_verificados": mejor.get("autores", ""),
    })
    return resultado


# ──────────────────────────── verificación de URL web ────────────────────────────

async def _verificar_url(url: str) -> bool:
    """Verifica que una URL web sea accesible haciendo un HEAD request."""
    try:
        resp = await HTTP_CLIENT.head(url, follow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False


# ──────────────────────────── validación individual y masiva ────────────────────────────

async def _validar_referencia_individual(ref: Dict[str, Any], indice: int) -> Dict[str, Any]:
    resultado = {
        "indice": indice + 1,
        "titulo_original": ref.get("titulo", "Sin título"),
        "autores": ref.get("autores", ""),
        "año": ref.get("año") or ref.get("anio", ""),
        "doi_original": ref.get("doi", ""),
    }

    if ref.get("doi"):
        datos = await buscar_por_doi(ref["doi"])
        resultado["validacion"] = datos
        if datos["encontrado"]:
            resultado["estado"]  = "VERIFICADA"
            resultado["con_doi"] = True
        elif ref.get("titulo"):
            datos_titulo = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
            resultado["validacion"] = datos_titulo
            if datos_titulo["encontrado"]:
                resultado["estado"]  = "ENCONTRADA_POR_TITULO (DOI fallido)"
                resultado["con_doi"] = True
                if datos_titulo.get("doi_encontrado"):
                    resultado["doi_sugerido"] = datos_titulo["doi_encontrado"]
            else:
                resultado["estado"]  = "DOI_NO_ENCONTRADO"
                resultado["con_doi"] = True
        else:
            resultado["estado"]  = "DOI_NO_ENCONTRADO"
            resultado["con_doi"] = True

    elif ref.get("url"):
        url_ref  = ref["url"]
        arxiv_id = _extraer_arxiv_id(url_ref)
        if arxiv_id:
            datos_arxiv = await buscar_por_arxiv_id(arxiv_id)
            if datos_arxiv["encontrado"]:
                resultado["estado"]     = "VERIFICADA"
                resultado["validacion"] = datos_arxiv
                resultado["con_doi"]    = False
                if datos_arxiv.get("doi_encontrado"):
                    resultado["doi_sugerido"] = datos_arxiv["doi_encontrado"]
                return resultado
        url_accesible = await _verificar_url(url_ref)
        resultado["estado"]     = "REFERENCIA_WEB" if url_accesible else "URL_NO_ACCESIBLE"
        resultado["validacion"] = {"encontrado": url_accesible, "fuente": "URL web", "url": url_ref}
        resultado["con_doi"]    = False

    elif ref.get("titulo"):
        datos = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
        resultado["validacion"] = datos
        if datos["encontrado"]:
            resultado["estado"]  = "ENCONTRADA_POR_TITULO"
            resultado["con_doi"] = False
            if datos.get("doi_encontrado"):
                resultado["doi_sugerido"] = datos["doi_encontrado"]
        else:
            resultado["estado"]  = "NO_ENCONTRADA"
            resultado["con_doi"] = False

    else:
        resultado["estado"]     = "SIN_DATOS_PARA_BUSCAR"
        resultado["validacion"] = {"encontrado": False}
        resultado["con_doi"]    = False

    return resultado


async def validar_referencias(referencias: List[Dict]) -> Dict[str, Any]:
    resultados = await asyncio.gather(*[
        _validar_referencia_individual(ref, i) for i, ref in enumerate(referencias)
    ])

    encontradas = no_encontradas = con_doi = sin_doi = 0
    for r in resultados:
        if r["validacion"]["encontrado"]:
            encontradas += 1
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
        "referencias": list(resultados),
    }


async def cerrar_cliente():
    await HTTP_CLIENT.aclose()