from typing import Any, Dict, Optional

from app.core.config import config
from app.services.apis.http_client import _get, CORE_BASE
from app.services.text_utils_service import _validar_resultado


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    if not config.CORE_API_KEY:
        return None
    try:
        resp = await _get(
            f"{CORE_BASE}/search/works",
            params={"q": titulo[:200], "limit": 5},
            headers={"Authorization": f"Bearer {config.CORE_API_KEY}"},
        )
        if resp.status_code == 200:
            for item in resp.json().get("results", []):
                t_verif = item.get("title", "")
                nombres = [a.get("name", "") for a in item.get("authors", [])]
                if not _validar_resultado(titulo, t_verif, autores, nombres):
                    continue
                doi = (item.get("doi") or "").replace("https://doi.org/", "")
                return {
                    "fuente": "CORE",
                    "titulo": t_verif,
                    "doi": doi,
                    "citaciones": 0,
                    "url": f"https://doi.org/{doi}" if doi
                           else item.get("downloadUrl")
                           or (item.get("sourceFulltextUrls") or [""])[0]
                           or "",
                }
    except Exception:
        pass
    return None


async def buscar_doi(doi: str) -> Optional[Dict[str, Any]]:
    if not config.CORE_API_KEY:
        return None
    try:
        resp = await _get(
            f"{CORE_BASE}/search/works",
            params={"q": f"doi:{doi}", "limit": 1},
            headers={"Authorization": f"Bearer {config.CORE_API_KEY}"},
        )
        if resp.status_code == 200:
            items = resp.json().get("results", [])
            if not items:
                return None
            item = items[0]
            doi_limpio = (item.get("doi") or doi).replace("https://doi.org/", "")
            autores = ", ".join(
                a.get("name", "") for a in item.get("authors", []) if a.get("name")
            )
            return {
                "encontrado": True,
                "fuente": "CORE",
                "titulo_verificado": item.get("title", ""),
                "doi_encontrado": doi_limpio,
                "citaciones": 0,
                "url": f"https://doi.org/{doi_limpio}" if doi_limpio
                       else item.get("downloadUrl", "")
                       or (item.get("sourceFulltextUrls") or [""])[0],
                "autores": autores,
            }
    except Exception:
        pass
    return None