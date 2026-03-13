#!/usr/bin/env python3
"""
Script para probar GROBID y ver qué datos devuelve realmente
"""
import httpx

# Texto de prueba con referencias en diferentes formatos
texto_prueba_harvard = """
Referencias:

Smith, J. (2024) A comprehensive guide to machine learning. Journal of AI, 15(3), pp. 45-67.

García, M. and López, P. (2023) Deep learning fundamentals. Research Review, 8, pp. 120-135.
"""

texto_prueba_apa = """
Referencias:

Smith, J. (2024). A comprehensive guide to machine learning. Journal of AI, 15(3), 45-67.

García, M., & López, P. (2023). Deep learning fundamentals. Research Review, 8, 120-135.
"""


def probar_grobid(texto: str, nombre: str):
    """Envía texto a GROBID y muestra el XML completo"""
    
    print("=" * 80)
    print(f"PRUEBA GROBID: {nombre}")
    print("=" * 80)
    print("\nTexto enviado:")
    print(texto)
    print("\n" + "-" * 80)
    
    url = "http://localhost:8070/api/processReferences"
    
    try:
        response = httpx.post(
            url,
            data={"input": texto, "consolidate": "0"},
            timeout=30.0
        )
        
        if response.status_code == 200:
            xml_resultado = response.text
            
            print("\nXML devuelto por GROBID:")
            print("-" * 80)
            print(xml_resultado)
            print("-" * 80)
            
            # Buscar específicamente el campo raw
            if 'raw_reference' in xml_resultado:
                print("\nSI contiene 'raw_reference'")
                import re
                raw_matches = re.findall(r'<note type="raw_reference">(.*?)</note>', xml_resultado, re.DOTALL)
                if raw_matches:
                    print("\nContenido de raw_reference:")
                    for i, raw in enumerate(raw_matches, 1):
                        print(f"  [{i}] {raw.strip()}")
            else:
                print("\nNO contiene 'raw_reference'")
            
        else:
            print(f"\nError: {response.status_code}")
            print(response.text[:500])
    
    except Exception as e:
        print(f"\nError al conectar con GROBID: {e}")
    
    print("\n" + "=" * 80 + "\n\n")


if __name__ == '__main__':
    print("\nINVESTIGANDO QUE DEVUELVE GROBID REALMENTE\n")
    
    probar_grobid(texto_prueba_harvard, "HARVARD (2024) sin punto")
    probar_grobid(texto_prueba_apa, "APA (2024). con punto")
