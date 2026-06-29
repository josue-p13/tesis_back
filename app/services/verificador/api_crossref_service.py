from typing import Any, Dict, Optional

from app.services.verificador.http_client import _get, CROSSREF_BASE
from app.services.obtener.text_utils_service import _validar_resultado


async def buscar_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(f"{CROSSREF_BASE}/works/{doi}")
        if resp.status_code == 200:
            data = resp.json().get("message", {})
            return {
                "encontrado": True,
                "fuente": "CrossRef",
                "titulo_verificado": data.get("title", [""])[0] if data.get("title") else "",
                "doi_encontrado": doi,
                "citaciones": 0,
                "url": f"https://doi.org/{doi}",
            }
    except Exception:
        pass
    return None


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(f"{CROSSREF_BASE}/works", params={"query.title": titulo[:100], "rows": 5})
        if resp.status_code == 200:
            for item in resp.json().get("message", {}).get("items", []):
                t_verif = item.get("title", [""])[0]
                nombres = [a.get("family", "") or a.get("name", "") for a in item.get("author", [])]
                if not _validar_resultado(titulo, t_verif, autores, nombres):
                    continue
                doi = item.get("DOI", "")
                return {
                    "fuente": "CrossRef",
                    "titulo": t_verif,
                    "doi": doi,
                    "citaciones": 0,
                    "url": f"https://doi.org/{doi}" if doi else "",
                }
    except Exception:
        pass
    return None
