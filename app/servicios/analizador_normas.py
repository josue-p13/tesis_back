import re
from app.modelos.schemas import ResultadoAnalisis, TipoNorma

def analizar_norma_apa(texto: str) -> ResultadoAnalisis:
    errores = []
    
    # Verificar márgenes (simulado mediante espaciado)
    if not texto.strip():
        errores.append("El documento está vacío")
    
    # Verificar formato de citas (Apellido, año)
    patron_cita_apa = r'\([A-Z][a-z]+,\s*\d{4}\)'
    citas_encontradas = re.findall(patron_cita_apa, texto)
    
    if len(citas_encontradas) == 0:
        errores.append("No se encontraron citas en formato APA (Apellido, año)")
    
    # Verificar referencias
    if "Referencias" not in texto and "REFERENCIAS" not in texto:
        errores.append("No se encontró sección de Referencias")
    
    cumple = len(errores) == 0
    detalles = f"Citas APA encontradas: {len(citas_encontradas)}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.APA,
        errores=errores,
        detalles=detalles
    )

def analizar_norma_ieee(texto: str) -> ResultadoAnalisis:
    errores = []
    
    if not texto.strip():
        errores.append("El documento está vacío")
    
    # Verificar citas numeradas [1], [2], etc.
    patron_cita_ieee = r'\[\d+\]'
    citas_encontradas = re.findall(patron_cita_ieee, texto)
    
    if len(citas_encontradas) == 0:
        errores.append("No se encontraron citas en formato IEEE [1], [2]...")
    
    # Verificar referencias
    if "References" not in texto and "REFERENCES" not in texto and "Referencias" not in texto:
        errores.append("No se encontró sección de References")
    
    cumple = len(errores) == 0
    detalles = f"Citas IEEE encontradas: {len(citas_encontradas)}"
    
    return ResultadoAnalisis(
        cumple=cumple,
        norma=TipoNorma.IEEE,
        errores=errores,
        detalles=detalles
    )
