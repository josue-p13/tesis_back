from typing import Any, Dict, Optional
import httpx

from app.core.config import config
# No necesitamos importar _validar_resultado aquí


SERPER_BASE_URL = "https://google.serper.dev"


async def buscar_titulo_google_scholar(titulo: str, autores: str = "") -> Optional[Dict[str, Any]]:
    """
    Busca una referencia en Google Scholar usando Serper.dev API.
    
    Args:
        titulo: Título de la publicación
        autores: Autores (opcional)
        
    Returns:
        Diccionario con datos de la referencia si se encuentra, None si no
    """
    # Verificar que Serper esté habilitado y configurado
    if not config.USAR_SERPER:
        return None
    
    if not config.SERPER_API_KEY:
        print("Warning: SERPER_API_KEY no configurada")
        return None
    
    if not titulo:
        return None
    
    try:
        # Construir query de búsqueda
        query = f"{titulo}"
        if autores:
            # Tomar solo el primer autor para no hacer la query muy específica
            primer_autor = autores.split(',')[0].strip() if ',' in autores else autores.split(' y ')[0].strip()
            query = f"{titulo} {primer_autor}"
        
        # Limitar longitud de la query
        query = query[:200]
        
        headers = {
            "X-API-KEY": config.SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": query,
            "gl": "us",  # Geolocalización
            "hl": "en",  # Idioma
            "num": 5     # Número de resultados
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/scholar",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"Serper API error: {response.status_code}")
                return None
            
            data = response.json()
            
            # Procesar resultados
            organic_results = data.get("organic", [])
            
            if not organic_results:
                return None
            
            # Tomar el primer resultado (más relevante)
            primer_resultado = organic_results[0]
            
            # Extraer información
            titulo_encontrado = primer_resultado.get("title", "")
            snippet = primer_resultado.get("snippet", "")
            link = primer_resultado.get("link", "")
            
            # Información de publicación
            # publicationInfo es un STRING con formato: "Autores - Journal, Año - url"
            # Ejemplo: "J Ortiz, J Van Camp, S Wijaya - Public health nutrition, 2014 - cambridge.org"
            publication_info = primer_resultado.get("publicationInfo", "")
            autores_str = ""
            
            if isinstance(publication_info, str) and publication_info:
                # Extraer autores (todo antes del primer " - ")
                partes = publication_info.split(" - ")
                if len(partes) > 0:
                    autores_str = partes[0].strip()
            
            # Citaciones - viene directamente como número en el campo "citedBy"
            citaciones = primer_resultado.get("citedBy", 0)
            if not isinstance(citaciones, int):
                citaciones = 0
            
            # Validar que sea una referencia válida
            resultado = {
                "encontrado": True,
                "fuente": "Google Scholar (Serper)",
                "titulo": titulo_encontrado,
                "autores": autores_str,
                "doi": "",  # Google Scholar no siempre proporciona DOI directo
                "citaciones": citaciones,
                "url": link,
            }
            
            return resultado
            
    except httpx.TimeoutException:
        print(f"Timeout al buscar en Serper: {titulo[:50]}...")
        return None
    except Exception as e:
        print(f"Error al buscar en Serper '{titulo[:50]}...': {e}")
        return None


async def buscar_doi_google_scholar(doi: str) -> Optional[Dict[str, Any]]:
    """
    Busca una referencia por DOI en Google Scholar usando Serper.dev.
    
    Args:
        doi: DOI a buscar
        
    Returns:
        Diccionario con datos de la referencia si se encuentra, None si no
    """
    if not config.USAR_SERPER or not config.SERPER_API_KEY or not doi:
        return None
    
    try:
        headers = {
            "X-API-KEY": config.SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        
        payload = {
            "q": f"doi:{doi}",
            "gl": "us",
            "hl": "en",
            "num": 1
        }
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{SERPER_BASE_URL}/scholar",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            organic_results = data.get("organic", [])
            
            if not organic_results:
                return None
            
            primer_resultado = organic_results[0]
            
            # Citaciones - viene directamente como número
            citaciones = primer_resultado.get("citedBy", 0)
            if not isinstance(citaciones, int):
                citaciones = 0
            
            resultado = {
                "encontrado": True,
                "fuente": "Google Scholar (Serper)",
                "titulo": primer_resultado.get("title", ""),
                "doi": doi,
                "citaciones": citaciones,
                "url": primer_resultado.get("link", ""),
            }
            
            return resultado
            
    except Exception as e:
        print(f"Error al buscar DOI en Serper '{doi}': {e}")
        return None
