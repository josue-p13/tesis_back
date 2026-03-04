from typing import List, Dict
from pathlib import Path
from datetime import datetime

from app.services.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo


# Obtener el directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUTS_DIR = BASE_DIR / "referencias"


def generar_txt_referencias(referencias: List[Dict[str, str]], nombre_archivo: str | None = None) -> str:
    """
    Genera un archivo TXT con las referencias formateadas.
    
    Args:
        referencias: Lista de referencias extraídas
        nombre_archivo: Nombre del archivo (opcional, se genera automáticamente si no se proporciona)
        
    Returns:
        Ruta del archivo TXT generado
    """
    # Crear directorio de salida si no existe
    print(f"[DEBUG] Creando directorio: {OUTPUTS_DIR}")
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[DEBUG] Directorio creado exitosamente")
    
    # DEBUG: Mostrar qué está llegando realmente
    print(f"\n[DEBUG] Total referencias recibidas: {len(referencias)}")
    if referencias:
        print(f"[DEBUG] Primera referencia completa:")
        for campo, valor in referencias[0].items():
            print(f"  - {campo}: {valor[:100] if isinstance(valor, str) and len(valor) > 100 else valor}")
        
        # Verificar si tienen el campo 'raw'
        refs_con_raw = sum(1 for ref in referencias if 'raw' in ref and ref['raw'])
        print(f"[DEBUG] Referencias con campo 'raw': {refs_con_raw}/{len(referencias)}")
    
    # Generar nombre de archivo si no se proporciona
    if not nombre_archivo:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"referencias_{timestamp}.txt"
    
    ruta_archivo = OUTPUTS_DIR / nombre_archivo
    print(f"[DEBUG] Ruta del archivo: {ruta_archivo}")
    
    # Detectar estilo de citación
    estilo = detectar_estilo_citacion(referencias)
    descripcion_estilo = obtener_descripcion_estilo(estilo)
    
    # Generar contenido del archivo
    contenido = "=" * 80 + "\n"
    contenido += "REFERENCIAS BIBLIOGRÁFICAS EXTRAÍDAS\n"
    contenido += "=" * 80 + "\n\n"
    contenido += f"Estilo de citación detectado: {estilo}\n"
    contenido += f"{descripcion_estilo}\n\n"
    contenido += f"Total de referencias: {len(referencias)}\n"
    contenido += f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    contenido += "=" * 80 + "\n\n"
    
    for idx, ref in enumerate(referencias, 1):
        contenido += f"[{idx}] "
        contenido += "-" * 75 + "\n"
        
        # Texto original (RAW) - NUEVO: Mostrar primero si existe
        if 'raw' in ref:
            contenido += f"Texto original: {ref['raw']}\n"
            contenido += "\n"
        
        # Autores
        if 'autores' in ref:
            contenido += f"Autores: {ref['autores']}\n"
        
        # Título
        if 'titulo' in ref:
            contenido += f"Título: {ref['titulo']}\n"
        
        # Publicación
        if 'publicacion' in ref:
            contenido += f"Publicación: {ref['publicacion']}\n"
        
        # Año
        if 'año' in ref:
            contenido += f"Año: {ref['año']}\n"
        
        # Volumen
        if 'volumen' in ref:
            contenido += f"Volumen: {ref['volumen']}\n"
        
        # Páginas
        if 'paginas' in ref:
            contenido += f"Páginas: {ref['paginas']}\n"
        
        # DOI
        if 'doi' in ref:
            contenido += f"DOI: {ref['doi']}\n"
        
        contenido += "\n"
    
    # Escribir archivo
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    return str(ruta_archivo)


def generar_txt_resumen(referencias: List[Dict[str, str]], nombre_archivo: str | None = None) -> str:
    """
    Genera un archivo TXT con un resumen simple de las referencias.
    Lista solo: autores, título, publicación y año de cada referencia.
    
    Args:
        referencias: Lista de referencias extraídas
        nombre_archivo: Nombre del archivo (opcional, se genera automáticamente si no se proporciona)
        
    Returns:
        Ruta del archivo TXT generado
    """
    # Crear directorio de salida si no existe
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo si no se proporciona
    if not nombre_archivo:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"resumen_{timestamp}.txt"
    
    ruta_archivo = OUTPUTS_DIR / nombre_archivo
    print(f"[DEBUG] Generando archivo de resumen: {ruta_archivo}")
    
    # Generar contenido del archivo
    contenido = "=" * 80 + "\n"
    contenido += "RESUMEN DE REFERENCIAS\n"
    contenido += "=" * 80 + "\n\n"
    contenido += f"Total de referencias: {len(referencias)}\n"
    contenido += f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for idx, ref in enumerate(referencias, 1):
        contenido += f"{idx}. "
        
        # Autores
        if 'año' in ref:
            contenido += f"{ref['año']}"
        
        # # Título
        # if 'titulo' in ref:
        #     contenido += f'"{ref["titulo"]}". '
        
        # # Publicación
        # if 'publicacion' in ref:
        #     contenido += f"{ref['publicacion']}. "
        
        # # Año
        # if 'año' in ref:
        #     contenido += f"({ref['año']})"
        
        contenido += "\n\n"
    
    # Escribir archivo
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    return str(ruta_archivo)


