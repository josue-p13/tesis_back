#!/usr/bin/env python3
"""
Script de prueba para el nuevo detector de estilos de citación.
"""

from app.services.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo

# Casos de prueba con diferentes estilos

# IEEE: Referencias con [1], [2]
referencias_ieee = [
    {
        'raw': '[1] J. Smith and A. Jones, "A novel approach to AI," IEEE Trans. Neural Networks, vol. 12, no. 3, pp. 45-67, 2020.',
        'autores': 'J. Smith, A. Jones',
        'titulo': 'A novel approach to AI',
        'año': '2020'
    },
    {
        'raw': '[2] M. García, "Machine learning basics," ACM Computing Surveys, vol. 8, pp. 120-135, 2019.',
        'autores': 'M. García',
        'titulo': 'Machine learning basics',
        'año': '2019'
    }
]

# Vancouver: Referencias con 1., 2.
referencias_vancouver = [
    {
        'raw': '1. Smith AB, Jones CD. Novel treatment approaches. Med J. 2020;15(3):234-45.',
        'autores': 'Smith AB, Jones CD',
        'titulo': 'Novel treatment approaches',
        'año': '2020'
    },
    {
        'raw': '2. García M, López P. Clinical trials overview. Health Res. 2019;8:120-35.',
        'autores': 'García M, López P',
        'titulo': 'Clinical trials overview',
        'año': '2019'
    }
]

# APA: Referencias con (año).
referencias_apa = [
    {
        'raw': 'Smith, J., & Jones, A. (2020). A novel approach to artificial intelligence. Journal of AI Research, 12(3), 45-67.',
        'autores': 'Smith, J., & Jones, A.',
        'titulo': 'A novel approach to artificial intelligence',
        'año': '2020'
    },
    {
        'raw': 'García, M. (2019). Machine learning fundamentals. Psychology Review, 8, 120-135.',
        'autores': 'García, M.',
        'titulo': 'Machine learning fundamentals',
        'año': '2019'
    }
]

# Harvard: Referencias con (año) MAYÚSCULAS
referencias_harvard = [
    {
        'raw': 'SMITH, J. and JONES, A. (2020) A novel approach to AI. Journal of Research, 12(3), pp. 45-67.',
        'autores': 'SMITH, J., JONES, A.',
        'titulo': 'A novel approach to AI',
        'año': '2020'
    },
    {
        'raw': 'GARCÍA, M. (2019) Machine learning basics. Research Review, 8, pp. 120-135.',
        'autores': 'GARCÍA, M.',
        'titulo': 'Machine learning basics',
        'año': '2019'
    }
]

# Sin campo 'raw' - debe construir desde campos estructurados
referencias_sin_raw = [
    {
        'autores': 'Smith, J., Jones, A.',
        'año': '2020',
        'titulo': 'A novel approach to AI',
        'publicacion': 'Journal of AI Research',
        'volumen': '12',
        'paginas': '45-67'
    },
    {
        'autores': 'García, M.',
        'año': '2019',
        'titulo': 'Machine learning basics',
        'publicacion': 'Psychology Review',
        'volumen': '8',
        'paginas': '120-135'
    }
]


def probar_detector():
    """Ejecuta pruebas del detector de estilos."""
    
    print("=" * 80)
    print("PRUEBA DEL DETECTOR DE ESTILOS DE CITACIÓN")
    print("=" * 80)
    print()
    
    casos_prueba = [
        ("IEEE (con [1], [2])", referencias_ieee),
        ("Vancouver (con 1., 2.)", referencias_vancouver),
        ("APA (con (año).)", referencias_apa),
        ("Harvard (con (año) MAYÚSCULAS)", referencias_harvard),
        ("Sin campo 'raw' (construcción automática)", referencias_sin_raw)
    ]
    
    for nombre_caso, referencias in casos_prueba:
        print(f"\n{'=' * 80}")
        print(f"CASO: {nombre_caso}")
        print(f"{'=' * 80}")
        
        # Detectar estilo
        estilo = detectar_estilo_citacion(referencias)
        descripcion = obtener_descripcion_estilo(estilo)
        
        print(f"\nEstilo detectado: {estilo}")
        print(f"Descripción: {descripcion}")
        print(f"Total referencias analizadas: {len(referencias)}")
        
        # Mostrar primeras 2 referencias de ejemplo
        print(f"\nEjemplo de referencias:")
        for i, ref in enumerate(referencias[:2], 1):
            if 'raw' in ref:
                print(f"  [{i}] {ref['raw'][:100]}...")
            else:
                print(f"  [{i}] Autores: {ref.get('autores', 'N/A')}, Año: {ref.get('año', 'N/A')}")
    
    print(f"\n{'=' * 80}")
    print("PRUEBAS COMPLETADAS")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    probar_detector()
