from typing import Any, Dict, Optional

from app.services.apis.http_client import _get, PUBMED_BASE, PUBMED_PARAMS
from app.services.text_utils_service import _validar_resultado


async def buscar_doi(doi: str) -> Optional[Dict[str, Any]]:
    try:
        resp = await _get(
            f"{PUBMED_BASE}/esearch.fcgi",
            params={**PUBMED_PARAMS, "term": f"{doi}[doi]", "retmax": 1},
        )
        if resp.status_code != 200:
            return None
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None
        resp2 = await _get(
            f"{PUBMED_BASE}/esummary.fcgi",
            params={**PUBMED_PARAMS, "id": ids[0]},
        )
        if resp2.status_code != 200:
            return None
        paper = resp2.json().get("result", {}).get(ids[0], {})
        return {
            "encontrado": True,
            "fuente": "PubMed",
            "titulo_verificado": paper.get("title", "").rstrip("."),
            "doi_encontrado": doi,
            "citaciones": 0,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/",
        }
    except Exception:
        pass
    return None


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    try:
        termino = f"{titulo[:200]}[Title/Abstract]"
        if autores:
            termino += f" AND {autores.split(',')[0].strip()}[Author]"
        resp = await _get(
            f"{PUBMED_BASE}/esearch.fcgi",
            params={**PUBMED_PARAMS, "term": termino, "retmax": 10},
        )
        if resp.status_code != 200:
            return None
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return None
        resp2 = await _get(
            f"{PUBMED_BASE}/esummary.fcgi",
            params={**PUBMED_PARAMS, "id": ",".join(ids)},
        )
        if resp2.status_code != 200:
            return None
        data = resp2.json().get("result", {})
        for pmid in ids:
            paper   = data.get(pmid, {})
            t_verif = paper.get("title", "").rstrip(".")
            nombres = [a.get("name", "") for a in paper.get("authors", [])]
            if not _validar_resultado(titulo, t_verif, autores, nombres):
                continue
            doi = next(
                (aid.get("value", "") for aid in paper.get("articleids", []) if aid.get("idtype") == "doi"),
                "",
            )
            if not doi:
                eloc = paper.get("elocationid", "")
                if "doi:" in eloc.lower():
                    doi = eloc.lower().split("doi:")[1].split()[0]
            return {
                "fuente": "PubMed",
                "titulo": t_verif,
                "doi": doi,
                "citaciones": 0,
                "url": f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
    except Exception:
        pass
    return None
