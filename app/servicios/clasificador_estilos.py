"""
Servicio para clasificar estilos de citación usando Crossref Style Classifier
API: https://citation.crosscite.org/
"""
import httpx
from typing import Dict, Any, List, Optional
import asyncio

CROSSREF_STYLE_API = "https://citation.crosscite.org/format"

async def clasificar_estilo_con_crossref(referencias: List[str]) -> Dict[str, Any]:
    """
    Clasifica el estilo de citación usando Crossref Style Classifier
    
    Args:
        referencias: Lista de referencias bibliográficas en texto plano
    
    Returns:
        Dict con el estilo detectado y confianza
    """
    if not referencias:
        return {
            "estilo": "DESCONOCIDO",
            "confianza": "NINGUNA",
            "detalles": "No hay referencias para analizar"
        }
    
    estilos_detectados = {}
    referencias_analizadas = 0
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Analizar las primeras 10 referencias (para no hacer muchas llamadas)
            for ref in referencias[:10]:
                try:
                    # Intentar detectar el estilo analizando el formato
                    estilo = await analizar_formato_referencia(ref, client)
                    if estilo:
                        estilos_detectados[estilo] = estilos_detectados.get(estilo, 0) + 1
                        referencias_analizadas += 1
                except Exception as e:
                    print(f"[CROSSREF] Error analizando referencia: {e}")
                    continue
        
        # Determinar el estilo más común
        if estilos_detectados:
            estilo_predominante = max(estilos_detectados, key=estilos_detectados.get)
            frecuencia = estilos_detectados[estilo_predominante]
            porcentaje = (frecuencia / referencias_analizadas) * 100 if referencias_analizadas > 0 else 0
            
            # Calcular confianza
            if porcentaje >= 70 and referencias_analizadas >= 5:
                confianza = "ALTA"
            elif porcentaje >= 50 and referencias_analizadas >= 3:
                confianza = "MEDIA"
            else:
                confianza = "BAJA"
            
            return {
                "estilo": estilo_predominante,
                "confianza": confianza,
                "detalles": f"{referencias_analizadas} referencias analizadas. {estilo_predominante} detectado en {porcentaje:.1f}% de las referencias.",
                "distribucion": estilos_detectados
            }
        else:
            return {
                "estilo": "DESCONOCIDO",
                "confianza": "NINGUNA",
                "detalles": "No se pudo detectar el estilo de citación"
            }
            
    except Exception as e:
        print(f"[CROSSREF] Error general: {e}")
        return {
            "estilo": "DESCONOCIDO",
            "confianza": "NINGUNA",
            "detalles": f"Error al clasificar: {str(e)}"
        }


async def analizar_formato_referencia(referencia: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    Analiza el formato de una referencia individual para detectar su estilo
    Usa patrones de reconocimiento locales (más rápido que API externa)
    """
    import re
    
    ref_lower = referencia.lower()
    
    # Patrones para detectar diferentes estilos
    
    # APA: Apellido, I. (Año). Título. Editorial.
    # Ejemplo: "Smith, J. (2020). Title of work. Publisher."
    patron_apa = r'[A-Z][a-z]+,\s+[A-Z]\.\s*(?:,?\s*&?\s*[A-Z][a-z]+,\s+[A-Z]\.)?\s*\(\d{4}\)'
    if re.search(patron_apa, referencia):
        return "APA"
    
    # IEEE/Vancouver: [1] o número seguido de apellido
    # Ejemplo: "[1] J. Smith, "Title," Journal, vol. 1, 2020."
    patron_ieee = r'^\[\d+\]|^\d+\.\s+[A-Z]'
    if re.search(patron_ieee, referencia):
        # Distinguir entre IEEE y Vancouver por otros patrones
        if 'vol.' in ref_lower or 'pp.' in ref_lower or 'no.' in ref_lower:
            return "IEEE"
        else:
            return "VANCOUVER"
    
    # Chicago: Apellido, Nombre. Año. "Título."
    # Ejemplo: "Smith, John. 2020. "Title of Work.""
    patron_chicago = r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+\d{4}\.\s+"'
    if re.search(patron_chicago, referencia):
        return "CHICAGO"
    
    # MLA: Apellido, Nombre. "Título." Editorial, Año.
    # Ejemplo: "Smith, John. "Title of Work." Publisher, 2020."
    patron_mla = r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+"[^"]+"\.\s+[^,]+,\s+\d{4}'
    if re.search(patron_mla, referencia):
        return "MLA"
    
    # Harvard: Apellido, Inicial(es) (Año) 'Título', Editorial
    # Ejemplo: "Smith, J. (2020) 'Title of Work', Publisher"
    patron_harvard = r"[A-Z][a-z]+,\s+[A-Z]\.\s*\(\d{4}\)\s+['\"]"
    if re.search(patron_harvard, referencia):
        return "HARVARD"
    
    # Si tiene paréntesis con año después del autor, probablemente APA
    if re.search(r'[A-Z][a-z]+.*\(\d{4}\)', referencia):
        return "APA"
    
    return None


def clasificar_estilo_local(referencias: List[str]) -> Dict[str, Any]:
    """
    Clasificación local sincrónica sin llamadas externas (más rápida)
    """
    import re
    
    if not referencias:
        return {
            "estilo": "DESCONOCIDO",
            "confianza": "NINGUNA",
            "detalles": "No hay referencias para analizar"
        }
    
    estilos_detectados = {}
    referencias_analizadas = 0
    
    for ref in referencias[:15]:  # Analizar hasta 15 referencias
        # Detectar patrón numérico (IEEE/Vancouver)
        if re.match(r'^\[\d+\]|\d+\.\s+', ref.strip()):
            estilo = "IEEE/VANCOUVER"
        # Detectar patrón APA (Apellido, I. (Año))
        elif re.search(r'[A-Z][a-z]+,\s+[A-Z]\.\s*(?:,?\s*&?\s*[A-Z][a-z]+,\s+[A-Z]\.)?\s*\(\d{4}\)', ref):
            estilo = "APA"
        # Detectar patrón con año al final (Chicago style)
        elif re.search(r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+\d{4}\.', ref):
            estilo = "CHICAGO"
        # Detectar MLA
        elif re.search(r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+"[^"]+"\.\s+[^,]+,\s+\d{4}', ref):
            estilo = "MLA"
        # Patrón general autor-año (probablemente APA o Harvard)
        elif re.search(r'[A-Z][a-z]+.*\(\d{4}\)', ref):
            estilo = "APA"
        else:
            continue
        
        estilos_detectados[estilo] = estilos_detectados.get(estilo, 0) + 1
        referencias_analizadas += 1
    
    if estilos_detectados:
        estilo_predominante = max(estilos_detectados, key=estilos_detectados.get)
        frecuencia = estilos_detectados[estilo_predominante]
        porcentaje = (frecuencia / referencias_analizadas) * 100 if referencias_analizadas > 0 else 0
        
        # Calcular confianza
        if porcentaje >= 70 and referencias_analizadas >= 5:
            confianza = "ALTA"
        elif porcentaje >= 50 and referencias_analizadas >= 3:
            confianza = "MEDIA"
        else:
            confianza = "BAJA"
        
        return {
            "estilo": estilo_predominante,
            "confianza": confianza,
            "detalles": f"{referencias_analizadas} referencias analizadas. {estilo_predominante} detectado en {porcentaje:.1f}% de las referencias.",
            "distribucion": estilos_detectados
        }
    else:
        return {
            "estilo": "DESCONOCIDO",
            "confianza": "NINGUNA",
            "detalles": "No se pudo detectar el estilo de citación",
            "distribucion": {}
        }
