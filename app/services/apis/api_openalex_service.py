from typing import Any, Dict, Optional

from app.services.apis.http_client import _get, OPENALEX_BASE
from app.services.text_utils_service import _validar_resultado


async def buscar_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(f"{OPENALEX_BASE}/works/doi:{doi}")
        if resp.status_code == 200:
            data = resp.json()
            return {
                "encontrado": True,
                "fuente": "OpenAlex",
                "titulo_verificado": data.get("title", ""),
                "doi_encontrado": doi,
                "citaciones": data.get("cited_by_count", 0),
                "url": f"https://doi.org/{doi}",
                "url_openalex": data.get("id", ""),
            }
    except Exception:
        pass
    return None


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(f"{OPENALEX_BASE}/works", params={"search": titulo[:300], "per_page": 5})
        if resp.status_code == 200:
            for work in resp.json().get("results", []):
                t_verif = work.get("title", "")
                nombres = [
                    a["author"]["display_name"]
                    for a in work.get("authorships", [])
                    if a.get("author", {}).get("display_name")
                ]
                if not _validar_resultado(titulo, t_verif, autores, nombres):
                    continue
                doi = work.get("doi", "").replace("https://doi.org/", "")
                return {
                    "fuente": "OpenAlex",
                    "titulo": t_verif,
                    "doi": doi,
                    "citaciones": work.get("cited_by_count", 0),
                    "url": f"https://doi.org/{doi}" if doi else "",
                }
    except Exception:
        pass
    return None
