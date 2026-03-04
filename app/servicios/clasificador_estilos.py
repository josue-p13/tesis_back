from typing import Dict, Any, List
import re


def clasificar_estilo_local(referencias: List[str]) -> Dict[str, Any]:
    """Clasifica el estilo de citación basado en patrones de referencias"""
    
    if not referencias:
        return {
            "estilo": "DESCONOCIDO",
            "detalles": "No hay referencias para analizar"
        }
    
    estilos_detectados = {}
    
    print(f"[CLASIFICADOR] Analizando {min(len(referencias), 15)} de {len(referencias)} referencias")
    for ref in referencias[:15]:
        # Detectar patrón numérico (IEEE/Vancouver)
        if re.match(r'^\[\d+\]|\d+\.\s+', ref.strip()):
            estilo = "IEEE/VANCOUVER"
        # Detectar patrón autor-año: distinguir APA vs Harvard
        elif re.search(r'[A-Z][a-z]+,?\s+[A-Z].*\(\d{4}\)', ref):
            # Harvard: (Año) seguido de espacio y mayúscula (SIN punto después del año)
            # APA:     (Año). seguido de punto
            if re.search(r'\(\d{4}\)\s+[A-Z]', ref):
                estilo = "HARVARD"
            elif re.search(r'\(\d{4}\)\.\s+', ref):
                estilo = "APA"
            else:
                estilo = "APA"  # fallback autor-año
        # Detectar patrón con año al final (Chicago style)
        elif re.search(r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+\d{4}\.', ref):
            estilo = "CHICAGO"
        # Detectar MLA
        elif re.search(r'[A-Z][a-z]+,\s+[A-Z][a-z]+\.\s+"[^"]+"\.\s+[^,]+,\s+\d{4}', ref):
            estilo = "MLA"
        else:
            continue
        
        estilos_detectados[estilo] = estilos_detectados.get(estilo, 0) + 1
    
    if estilos_detectados:
        estilo_predominante = max(estilos_detectados, key=estilos_detectados.get)
        print(f"[CLASIFICADOR] Distribución: {estilos_detectados} → {estilo_predominante}")
        return {
            "estilo": estilo_predominante,
            "detalles": f"{len(referencias)} referencias analizadas",
            "distribucion": estilos_detectados
        }
    else:
        return {
            "estilo": "DESCONOCIDO",
            "detalles": "No se pudo detectar el estilo de citación",
            "distribucion": {}
        }
