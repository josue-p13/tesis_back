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
