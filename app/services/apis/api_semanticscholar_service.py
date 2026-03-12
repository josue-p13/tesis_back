from typing import Any, Dict, Optional

from app.services.apis.http_client import _get, SEMANTICSCHOLAR_BASE
from app.services.text_utils_service import _validar_resultado

_FIELDS_FULL = "title,authors,year,externalIds,citationCount"


async def buscar_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(
            f"{SEMANTICSCHOLAR_BASE}/paper/DOI:{doi}",
            params={"fields": _FIELDS_FULL},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "encontrado": True,
                "fuente": "Semantic Scholar",
                "titulo_verificado": data.get("title", ""),
                "doi_encontrado": doi,
                "citaciones": data.get("citationCount", 0),
                "url": f"https://doi.org/{doi}",
            }
    except Exception:
        pass
    return None


async def buscar_arxiv(arxiv_id: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(
            f"{SEMANTICSCHOLAR_BASE}/paper/arXiv:{arxiv_id}",
            params={"fields": _FIELDS_FULL},
        )
        if resp.status_code == 200:
            data = resp.json()
            doi  = (data.get("externalIds") or {}).get("DOI", "")
            return {
                "encontrado": True,
                "fuente": "Semantic Scholar (arXiv)",
                "titulo_verificado": data.get("title", ""),
                "doi_encontrado": doi,
                "citaciones": data.get("citationCount", 0),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
            }
    except Exception:
        pass
    return None


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(
            f"{SEMANTICSCHOLAR_BASE}/paper/search",
            params={
                "query": titulo[:100],
                "limit": 5,
                "fields": f"paperId,{_FIELDS_FULL}",
            },
        )
        if resp.status_code == 200:
            for paper in resp.json().get("data", []):
                t_verif  = paper.get("title", "")
                nombres  = [a.get("name", "") for a in paper.get("authors", [])]
                if not _validar_resultado(titulo, t_verif, autores, nombres):
                    continue
                doi      = (paper.get("externalIds") or {}).get("DOI", "")
                paper_id = paper.get("paperId", "")
                return {
                    "fuente": "Semantic Scholar",
                    "titulo": t_verif,
                    "doi": doi,
                    "citaciones": paper.get("citationCount", 0),
                    "url": f"https://doi.org/{doi}" if doi
                           else f"https://www.semanticscholar.org/paper/{paper_id}",
                }
    except Exception:
        pass
    return None
