import asyncio
from typing import Any, Dict, List, Optional

from app.services.obtener.text_utils_service import _similitud_titulos, _extraer_arxiv_id, _resultado_base
from app.services.language_service import traducir_si_es_espanol
from app.services.verificador import (
    api_openalex_service       as openalex,
    api_crossref_service       as crossref,
    api_semanticscholar_service as ss,
    api_pubmed_service         as pubmed,
    api_core_service           as core,
    api_googlebooks_service    as gbooks,
)
from app.services.verificador.http_client import HTTP_CLIENT
from app.services.db.database_service import DatabaseService


# ──────────────────────────── búsqueda en BD local (caché) ────────────────────────────

def buscar_en_bd_primero(ref: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Busca la referencia en la BD local antes de consultar APIs externas.
    Prioridad: DOI > Título+Autores
    
    Args:
        ref: Referencia a buscar
        
    Returns:
        Datos de la referencia si se encuentra en BD, None si no existe
    """
    try:
        with DatabaseService() as db:
            # 1. Intentar búsqueda por DOI (más confiable)
            if ref.get('doi'):
                resultado = db.buscar_por_doi(ref['doi'])
                if resultado:
                    return {
                        "encontrado": True,
                        "fuente": f"{resultado.get('fuente_verificacion', 'BD Cache')} (desde BD)",
                        "titulo": resultado.get('titulo', ''),
                        "doi": resultado.get('doi', ''),
                        "citaciones": resultado.get('citaciones', 0),
                        "url": resultado.get('url_verificada', ''),
                        "autores": resultado.get('autores', ''),
                        "desde_bd": True  # Flag para identificar que vino de BD
                    }
            
            # 2. Intentar búsqueda por título + autores (similitud)
            if ref.get('titulo'):
                resultado = db.buscar_por_titulo_similitud(
                    ref['titulo'], 
                    ref.get('autores', '')
                )
                if resultado:
                    return {
                        "encontrado": True,
                        "fuente": f"{resultado.get('fuente_verificacion', 'BD Cache')} (desde BD)",
                        "titulo": resultado.get('titulo', ''),
                        "doi": resultado.get('doi', ''),
                        "citaciones": resultado.get('citaciones', 0),
                        "url": resultado.get('url_verificada', ''),
                        "autores": resultado.get('autores', ''),
                        "desde_bd": True
                    }
            
            return None
            
    except Exception as e:
        print(f"Error al buscar en BD: {e}")
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

async def _validar_referencia_individual(ref: Dict[str, Any], indice: int) -> Dict[str, Any]:
    resultado = {
        "indice": indice + 1,
        "titulo_original": ref.get("titulo", "Sin título"),
        "autores": ref.get("autores", ""),
        "año": ref.get("año") or ref.get("anio", ""),
        "doi_original": ref.get("doi", ""),
    }

    # ═══════════════════════════════════════════════════════════
    # PASO 1: BUSCAR PRIMERO EN BD LOCAL (CACHÉ)
    # ═══════════════════════════════════════════════════════════
    datos_bd = buscar_en_bd_primero(ref)
    if datos_bd and datos_bd.get("encontrado"):
        # ¡Encontrada en BD! No necesitamos buscar en APIs externas
        resultado["validacion"] = datos_bd
        resultado["estado"] = "VERIFICADA (BD Cache)"
        resultado["con_doi"] = bool(ref.get("doi"))
        if datos_bd.get("doi"):
            resultado["doi_sugerido"] = datos_bd["doi"]
        return resultado

    # ═══════════════════════════════════════════════════════════
    # PASO 2: NO ESTÁ EN BD - BUSCAR EN APIs EXTERNAS
    # ═══════════════════════════════════════════════════════════

    if ref.get("doi"):
        datos = await buscar_por_doi(ref["doi"])
        resultado["validacion"] = datos
        if datos["encontrado"]:
            resultado["estado"]  = "VERIFICADA"
            resultado["con_doi"] = True
            # Guardar en BD para próximas consultas
            await guardar_en_bd_si_verificada(ref, datos)
        elif ref.get("titulo"):
            datos_titulo = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
            resultado["validacion"] = datos_titulo
            if datos_titulo["encontrado"]:
                resultado["estado"]  = "ENCONTRADA_POR_TITULO (DOI fallido)"
                resultado["con_doi"] = True
                if datos_titulo.get("doi_encontrado"):
                    resultado["doi_sugerido"] = datos_titulo["doi_encontrado"]
                # Guardar en BD
                await guardar_en_bd_si_verificada(ref, datos_titulo)
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
                # Guardar en BD
                await guardar_en_bd_si_verificada(ref, datos_arxiv)
                return resultado
        url_accesible = await _verificar_url(url_ref)
        resultado["estado"]     = "REFERENCIA_WEB" if url_accesible else "URL_NO_ACCESIBLE"
        resultado["validacion"] = {"encontrado": url_accesible, "fuente": "URL web", "url": url_ref}
        resultado["con_doi"]    = False
        # NO guardamos URLs web en BD (sin verificación académica)

    elif ref.get("titulo"):
        datos = await buscar_por_titulo(ref["titulo"], ref.get("autores", ""))
        resultado["validacion"] = datos
        if datos["encontrado"]:
            resultado["estado"]  = "ENCONTRADA_POR_TITULO"
            resultado["con_doi"] = False
            if datos.get("doi_encontrado"):
                resultado["doi_sugerido"] = datos["doi_encontrado"]
            # Guardar en BD
            await guardar_en_bd_si_verificada(ref, datos)
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

    encontradas = no_encontradas = con_doi = sin_doi = desde_bd = guardadas_bd = 0
    for r in resultados:
        if r["validacion"]["encontrado"]:
            encontradas += 1
            # Contar si vino desde BD
            if r["validacion"].get("desde_bd"):
                desde_bd += 1
            # Contar si se guardó en BD (las que NO vinieron de BD y fueron encontradas)
            elif r["estado"] not in ["REFERENCIA_WEB", "URL_NO_ACCESIBLE"]:
                guardadas_bd += 1
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
            "consultadas_desde_cache": desde_bd,
            "nuevas_guardadas": guardadas_bd,
            "total_verificadas_guardadas": guardadas_bd
        },
        "referencias": list(resultados),
    }


async def cerrar_cliente():
    await HTTP_CLIENT.aclose()