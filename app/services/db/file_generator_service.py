from typing import List, Dict
from pathlib import Path
from datetime import datetime

from app.services.obtener.citation_style_detector_service import detectar_estilo_citacion, obtener_descripcion_estilo


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
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generar nombre de archivo si no se proporciona
    if not nombre_archivo:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"referencias_{timestamp}.txt"
    
    ruta_archivo = OUTPUTS_DIR / nombre_archivo
    
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
    
    # Generar contenido del archivo
    contenido = "=" * 80 + "\n"
    contenido += "RESUMEN DE REFERENCIAS\n"
    contenido += "=" * 80 + "\n\n"
    contenido += f"Total de referencias: {len(referencias)}\n"
    contenido += f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for idx, ref in enumerate(referencias, 1):
        contenido += f"{idx}. "
        if ref.get('autores'):
            contenido += f"{ref['autores']}. "
        if ref.get('titulo'):
            contenido += f'"{ref["titulo"]}". '
        if ref.get('publicacion'):
            contenido += f"{ref['publicacion']}. "
        if ref.get('año'):
            contenido += f"({ref['año']})"
        contenido += "\n\n"
    
    # Escribir archivo
    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)
    
    return str(ruta_archivo)

def generar_txt_validacion(resultado_validacion: Dict, nombre_archivo: str | None = None) -> str:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    if not nombre_archivo:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"validacion_{timestamp}.txt"

    ruta_archivo = OUTPUTS_DIR / nombre_archivo

    total          = resultado_validacion.get("total", 0)
    encontradas    = resultado_validacion.get("encontradas", 0)
    no_encontradas = resultado_validacion.get("no_encontradas", 0)
    porcentaje     = resultado_validacion.get("porcentaje_verificadas", 0)
    referencias    = resultado_validacion.get("referencias", [])

    contenido  = "=" * 80 + "\n"
    contenido += "VALIDACION DE REFERENCIAS\n"
    contenido += "=" * 80 + "\n\n"
    contenido += f"Fecha de validacion : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    contenido += f"Total referencias   : {total}\n"
    contenido += f"Verificadas         : {encontradas}\n"
    contenido += f"No encontradas      : {no_encontradas}\n"
    contenido += f"Porcentaje validas  : {porcentaje}%\n"
    contenido += "=" * 80 + "\n\n"

    ESTADOS = {
        "VERIFICADA":                                    "[OK] VERIFICADA (por DOI)",
        "VERIFICADA (BD Cache)":                         "[✓]  VERIFICADA (desde BD cache)",
        "DOI_NO_ENCONTRADO":                             "[X]  DOI no encontrado",
        "ENCONTRADA_POR_TITULO":                         "[~]  Encontrada por titulo",
        "ENCONTRADA_POR_TITULO (DOI fallido)":           "[~]  Encontrada por titulo (DOI fallido)",
        "ENCONTRADA_GOOGLE_SCHOLAR":                     "[GS] Encontrada en Google Scholar",
        "ENCONTRADA_GOOGLE_SCHOLAR (DOI fallido)":       "[GS] Encontrada en Google Scholar (DOI fallido)",
        "REFERENCIA_WEB":                                "[W]  Referencia web",
        "URL_NO_ACCESIBLE":                              "[!]  URL no accesible",
        "NO_ENCONTRADA":                                 "[X]  No encontrada",
        "SIN_DATOS_PARA_BUSCAR":                         "[?]  Sin datos para buscar",
    }

    for ref in referencias:
        idx      = ref.get("indice", "?")
        titulo   = ref.get("titulo_original", "Sin titulo")
        autores  = ref.get("autores", "")
        anio     = ref.get("año", "")
        doi_orig = ref.get("doi_original", "")
        estado   = ref.get("estado", "DESCONOCIDO")
        val      = ref.get("validacion", {})

        contenido += f"[{idx}] {titulo}\n"
        if autores:
            contenido += f"    Autores  : {autores}\n"
        if anio:
            contenido += f"    Ano      : {anio}\n"
        if doi_orig:
            contenido += f"    DOI orig : {doi_orig}\n"
        contenido += f"    Estado   : {ESTADOS.get(estado, estado)}\n"

        if val.get("encontrado"):
            contenido += f"    Fuente   : {val.get('fuente', '')}\n"
            if val.get("titulo_verificado"):
                contenido += f"    Titulo verificado : {val['titulo_verificado']}\n"
            if val.get("doi_encontrado"):
                contenido += f"    DOI sugerido      : {val['doi_encontrado']}\n"
            if val.get("isbn"):
                contenido += f"    ISBN              : {val['isbn']}\n"
            if val.get("url"):
                contenido += f"    URL               : {val['url']}\n"
            if val.get("url_openalex"):
                contenido += f"    OpenAlex          : {val['url_openalex']}\n"
        elif estado == "URL_NO_ACCESIBLE" and val.get("url"):
            # Mostrar URL incluso si no es accesible para verificacion manual
            contenido += f"    Fuente   : {val.get('fuente', 'URL web')}\n"
            contenido += f"    URL      : {val['url']} (requiere verificacion manual)\n"
        contenido += "\n"

    with open(ruta_archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)

    return str(ruta_archivo)


