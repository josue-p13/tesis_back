from pathlib import Path
from datetime import datetime
import os


def guardar_archivo_temporal(contenido: bytes, nombre_archivo: str) -> str:
    """Guarda el archivo subido en una ruta temporal"""
    directorio = Path("archivos_temp")
    directorio.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_temp = f"{timestamp}_{nombre_archivo}"
    ruta = directorio / nombre_temp
    
    with open(ruta, 'wb') as f:
        f.write(contenido)
    
    return str(ruta)


def eliminar_archivo_temporal(ruta: str) -> None:
    """Elimina un archivo temporal"""
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except Exception as e:
        print(f"[WARN] No se pudo eliminar archivo temporal: {e}")
