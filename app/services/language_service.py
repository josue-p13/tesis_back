import asyncio

from deep_translator import GoogleTranslator
from langdetect import detect


async def traducir_si_es_espanol(titulo: str) -> str:
    """Detecta el idioma y devuelve el título traducido al inglés si está en español."""
    try:
        if await asyncio.to_thread(detect, titulo) == "es":
            traduccion = await asyncio.to_thread(
                GoogleTranslator(source="es", target="en").translate, titulo
            )
            return traduccion or titulo
    except Exception:
        pass
    return titulo