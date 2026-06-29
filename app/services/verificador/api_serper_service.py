import re
from typing import Any, Dict, Optional
import httpx
from app.services.obtener.text_utils_service import _similitud_titulos

SERPER_BASE_URL = "https://google.serper.dev"
SIMILITUD_THRESHOLD = 0.65  # Umbral para considerar que es el mismo paper


class SerperAuthError(Exception):
    """
    Se lanza cuando Serper rechaza la API key (HTTP 401 o 403).
    Permite que el caller distinga un error de autenticación
    de un simple "referencia no encontrada".
    """
    def __init__(self, codigo: int):
        self.codigo = codigo
        super().__init__(f"Serper rechazó la API key (HTTP {codigo})")


def validar_formato_key(serper_api_key: str) -> Dict[str, Any]:
    """
    Valida el formato de la API key de Serper sin hacer ningún request.
    Las keys de Serper son strings hexadecimales de exactamente 40 caracteres.

    Returns:
        { "valida": bool, "mensaje": str }
    """
    if not serper_api_key or not serper_api_key.strip():
        return {"valida": False, "mensaje": "La API key está vacía"}

    key = serper_api_key.strip()

    if len(key) != 40:
        return {
            "valida": False,
            "mensaje": f"Formato inválido: debe tener 40 caracteres (tiene {len(key)})"
        }

    if not re.fullmatch(r"[0-9a-f]{40}", key):
        return {
            "valida": False,
            "mensaje": "Formato inválido: solo debe contener caracteres hexadecimales (0-9, a-f)"
        }

    return {"valida": True, "mensaje": "Formato de API key correcto"}


async def buscar_titulo_google_scholar(
    titulo: str, 
    autores: str = "", 
    serper_api_key: str = "",
    titulo_alternativo: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Busca una referencia en Google Scholar usando Serper.dev API.
    La api key llega como parámetro (enviada por el front), no del .env.

    Args:
        titulo: Título a buscar (usualmente el traducido si es español)
        autores: Autores para refinar la búsqueda
        serper_api_key: Key de Serper.dev
        titulo_alternativo: Título original (para comparar similitud si el principal falla)

    Raises:
        SerperAuthError: si Serper responde 401 o 403 (key inválida o sin permisos)

    Returns:
        Diccionario con datos de la referencia si se encuentra y supera similitud, None si no
    """
    if not serper_api_key or not titulo:
        return None

    try:
        # Construir query: "Título del paper" primer_autor
        query = titulo
        if autores:
            primer_autor = autores.split(',')[0].strip() if ',' in autores else autores.split(' y ')[0].strip()
            query = f'"{titulo}" {primer_autor}'
        else:
            query = f'"{titulo}"'

        query = query[:250] # Límite razonable

        headers = {
            "X-API-KEY": serper_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "gl": "us",
            "hl": "en",
            "num": 5
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/scholar",
                json=payload,
                headers=headers
            )

            # Key inválida o sin permisos — lanzar excepción especial
            if response.status_code in (401, 403):
                raise SerperAuthError(response.status_code)

            if response.status_code != 200:
                print(f"[Serper] API error: {response.status_code}")
                return None

            data = response.json()
            organic_results = data.get("organic", [])

            if not organic_results:
                return None

            # Revisamos los primeros resultados para ver si alguno coincide
            for res in organic_results:
                titulo_encontrado = res.get("title", "")
                
                # Validamos similitud contra el título buscado O el alternativo (original)
                similitud = _similitud_titulos(titulo, titulo_encontrado)
                if titulo_alternativo:
                    similitud = max(similitud, _similitud_titulos(titulo_alternativo, titulo_encontrado))

                if similitud >= SIMILITUD_THRESHOLD:
                    link = res.get("link", "")
                    snippet = res.get("snippet", "")
                    publication_info = res.get("publicationInfo", "")
                    
                    autores_str = ""
                    if isinstance(publication_info, str) and publication_info:
                        partes = publication_info.split(" - ")
                        if partes:
                            autores_str = partes[0].strip()

                    citaciones = res.get("citedBy", 0)
                    if not isinstance(citaciones, int):
                        citaciones = 0

                    return {
                        "encontrado": True,
                        "fuente": "Google Scholar (Serper)",
                        "titulo": titulo_encontrado,
                        "autores": autores_str,
                        "doi": "",
                        "citaciones": citaciones,
                        "url": link,
                    }
                else:
                    print(f"[Serper] Rechazado por similitud baja ({similitud:.2f} < {SIMILITUD_THRESHOLD}):")
                    print(f"  - Original:    {titulo}")
                    if titulo_alternativo:
                        print(f"  - Alternativo: {titulo_alternativo}")
                    print(f"  - Encontrado:  {titulo_encontrado}")

            return None

    except SerperAuthError:
        raise  # propagar hacia arriba sin silenciar
    except httpx.TimeoutException:
        print(f"[Serper] Timeout: {titulo[:50]}...")
        return None
    except Exception as e:
        print(f"[Serper] Error buscando '{titulo[:50]}...': {e}")
        return None


async def buscar_doi_google_scholar(
    doi: str, 
    serper_api_key: str = "",
    titulo_ref: str = "",
    titulo_alternativo: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Busca una referencia por DOI en Google Scholar usando Serper.dev.

    Args:
        doi: DOI a buscar
        serper_api_key: Key de Serper
        titulo_ref: Título esperado para validar el resultado
        titulo_alternativo: Título alternativo (original) para validar

    Raises:
        SerperAuthError: si Serper responde 401 o 403
    """
    if not serper_api_key or not doi:
        return None

    try:
        headers = {
            "X-API-KEY": serper_api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": f'"{doi}"',
            "gl": "us",
            "hl": "en",
            "num": 3
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/scholar",
                json=payload,
                headers=headers
            )

            if response.status_code in (401, 403):
                raise SerperAuthError(response.status_code)

            if response.status_code != 200:
                return None

            data = response.json()
            organic_results = data.get("organic", [])

            for res in organic_results:
                titulo_encontrado = res.get("title", "")
                
                # Si tenemos título, validamos que el DOI no nos traiga basura
                if titulo_ref:
                    similitud = _similitud_titulos(titulo_ref, titulo_encontrado)
                    if titulo_alternativo:
                        similitud = max(similitud, _similitud_titulos(titulo_alternativo, titulo_encontrado))
                    
                    if similitud < SIMILITUD_THRESHOLD:
                        print(f"[Serper] DOI rechazado por similitud baja ({similitud:.2f} < {SIMILITUD_THRESHOLD}):")
                        if titulo_ref:
                            print(f"  - Ref:         {titulo_ref}")
                        if titulo_alternativo:
                            print(f"  - Alternativo: {titulo_alternativo}")
                        print(f"  - Encontrado:  {titulo_encontrado}")
                        continue

                citaciones = res.get("citedBy", 0)
                if not isinstance(citaciones, int):
                    citaciones = 0

                return {
                    "encontrado": True,
                    "fuente": "Google Scholar (Serper)",
                    "titulo": titulo_encontrado,
                    "doi": doi,
                    "citaciones": citaciones,
                    "url": res.get("link", ""),
                }
            
            return None

    except SerperAuthError:
        raise
    except Exception as e:
        print(f"[Serper] Error buscando DOI '{doi}': {e}")
        return None
