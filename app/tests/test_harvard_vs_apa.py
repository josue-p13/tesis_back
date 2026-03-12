#!/usr/bin/env python3
"""
Test específico para distinguir entre Harvard y APA
La diferencia clave: Harvard usa (año) sin punto, APA usa (año). con punto
"""

from app.services.obtener.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo

# HARVARD: (2024) SIN PUNTO después del paréntesis
referencias_harvard = [
    {
        'raw': 'Smith, J. (2024) A comprehensive guide to machine learning. Journal of AI, 15(3), pp. 45-67.',
        'autores': 'Smith, J.',
        'titulo': 'A comprehensive guide to machine learning',
        'año': '2024'
    },
    {
        'raw': 'García, M. and López, P. (2023) Deep learning fundamentals. Research Review, 8, pp. 120-135.',
        'autores': 'García, M., López, P.',
        'titulo': 'Deep learning fundamentals',
        'año': '2023'
    },
    {
        'raw': 'Johnson, A. (2022) Neural networks in practice. Computing Today, 12(1), pp. 88-102.',
        'autores': 'Johnson, A.',
        'titulo': 'Neural networks in practice',
        'año': '2022'
    }
]

# APA: (2024). CON PUNTO después del paréntesis
referencias_apa = [
    {
        'raw': 'Smith, J. (2024). A comprehensive guide to machine learning. Journal of AI, 15(3), 45-67.',
        'autores': 'Smith, J.',
        'titulo': 'A comprehensive guide to machine learning',
        'año': '2024'
    },
    {
        'raw': 'García, M., & López, P. (2023). Deep learning fundamentals. Research Review, 8, 120-135.',
        'autores': 'García, M., & López, P.',
        'titulo': 'Deep learning fundamentals',
        'año': '2023'
    },
    {
        'raw': 'Johnson, A. (2022). Neural networks in practice. Computing Today, 12(1), 88-102.',
        'autores': 'Johnson, A.',
        'titulo': 'Neural networks in practice',
        'año': '2022'
    }
]


def test_estilos():
    """Prueba la distinción entre Harvard y APA"""
    
    print("=" * 80)
    print("TEST: DISTINCIÓN ENTRE HARVARD Y APA")
    print("=" * 80)
    print()
    
    # Test Harvard
    print("1️⃣  TEST HARVARD - Referencias con (año) SIN PUNTO")
    print("-" * 80)
    print("Ejemplo de referencia:")
    print(f"   {referencias_harvard[0]['raw']}")
    print()
    
    estilo_harvard = detectar_estilo_citacion(referencias_harvard)
    descripcion_harvard = obtener_descripcion_estilo(estilo_harvard)
    
    print(f"✓ Estilo detectado: {estilo_harvard}")
    print(f"✓ Descripción: {descripcion_harvard}")
    
    if estilo_harvard == "Harvard":
        print("✅ CORRECTO: Detectó Harvard")
    else:
        print(f"❌ ERROR: Esperaba 'Harvard' pero obtuvo '{estilo_harvard}'")
    
    print()
    print()
    
    # Test APA
    print("2️⃣  TEST APA - Referencias con (año). CON PUNTO")
    print("-" * 80)
    print("Ejemplo de referencia:")
    print(f"   {referencias_apa[0]['raw']}")
    print()
    
    estilo_apa = detectar_estilo_citacion(referencias_apa)
    descripcion_apa = obtener_descripcion_estilo(estilo_apa)
    
    print(f"✓ Estilo detectado: {estilo_apa}")
    print(f"✓ Descripción: {descripcion_apa}")
    
    if estilo_apa == "APA":
        print("✅ CORRECTO: Detectó APA")
    else:
        print(f"❌ ERROR: Esperaba 'APA' pero obtuvo '{estilo_apa}'")
    
    print()
    print("=" * 80)
    print("RESUMEN DE LA DIFERENCIA:")
    print("=" * 80)
    print("Harvard: (2024) Title    ← Sin punto después del paréntesis")
    print("APA:     (2024). Title   ← Con punto después del paréntesis")
    print("=" * 80)


if __name__ == '__main__':
    test_estilos()
