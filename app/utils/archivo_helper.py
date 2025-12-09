import os
from pathlib import Path

def guardar_archivo_temporal(contenido: bytes, nombre_archivo: str) -> str:
    ruta_temp = Path("archivos_temp") / nombre_archivo
    with open(ruta_temp, "wb") as archivo:
        archivo.write(contenido)
    return str(ruta_temp)

def eliminar_archivo_temporal(ruta_archivo: str):
    if os.path.exists(ruta_archivo):
        os.remove(ruta_archivo)
