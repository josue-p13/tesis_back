from typing import Any, Dict, Optional

from app.services.apis.http_client import _get, GOOGLEBOOKS_BASE
from app.services.text_utils_service import _validar_resultado, _normalizar


async def buscar_titulo(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    """Fallback para libros no encontrados en APIs académicas."""
    try:
        query = titulo[:150]
        if autores:
            primer_apellido = _normalizar(autores.split(",")[0]).split()[-1]
            if primer_apellido:
                query += f"+inauthor:{primer_apellido}"
        resp = await _get(
            f"{GOOGLEBOOKS_BASE}/volumes",
            params={"q": query, "maxResults": 10, "printType": "books"},
        )
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                info    = item.get("volumeInfo", {})
                t_verif = info.get("title", "")
                nombres = info.get("authors", [])
                if not _validar_resultado(titulo, t_verif, autores, nombres):
                    continue
                isbn = next(
                    (i["identifier"] for i in info.get("industryIdentifiers", [])
                     if i.get("type") in ("ISBN_13", "ISBN_10")),
                    "",
                )
                return {
                    "fuente": "Google Books",
                    "titulo": t_verif,
                    "doi": "",
                    "citaciones": 0,
                    "isbn": isbn,
                    "url": info.get("infoLink", "") or info.get("previewLink", ""),
                }
    except Exception:
        pass
    return None
