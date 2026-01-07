from datetime import datetime
from pathlib import Path
from app.modelos.schemas import ResultadoAnalisis

def generar_reporte_txt(resultado: ResultadoAnalisis, nombre_archivo: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_reporte = f"reporte_{nombre_archivo}_{timestamp}.txt"
    ruta_reporte = Path("archivos_temp") / nombre_reporte
    
    with open(ruta_reporte, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("REPORTE DE ANÁLISIS DE NORMAS ACADÉMICAS\n")
        f.write("="*70 + "\n\n")
        
        f.write(f"Archivo analizado: {nombre_archivo}\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Norma evaluada: {resultado.norma.value.upper()}\n")
        f.write(f"Resultado: {'✓ CUMPLE' if resultado.cumple else '✗ NO CUMPLE'}\n")
        f.write("\n" + "-"*70 + "\n\n")
        
        f.write(f"RESUMEN:\n")
        f.write(f"{resultado.detalles}\n\n")
        
        if resultado.errores:
            f.write("ERRORES ENCONTRADOS:\n")
            for i, error in enumerate(resultado.errores, 1):
                f.write(f"  {i}. {error}\n")
            f.write("\n")
        
        f.write("-"*70 + "\n")
        f.write(f"ANÁLISIS DE CITAS\n")
        f.write("-"*70 + "\n\n")
        
        f.write(f"Total de citas encontradas: {resultado.total_citas}\n")
        f.write(f"Citas válidas: {len(resultado.citas_validas)}\n")
        f.write(f"Citas inválidas: {len(resultado.citas_invalidas)}\n\n")
        
        if resultado.citas_validas:
            f.write("CITAS VÁLIDAS:\n")
            f.write("-"*70 + "\n")
            for i, cita in enumerate(resultado.citas_validas, 1):
                f.write(f"{i}. {cita.texto}\n")
            f.write("\n")
        
        if resultado.citas_invalidas:
            f.write("CITAS INVÁLIDAS:\n")
            f.write("-"*70 + "\n")
            for i, cita in enumerate(resultado.citas_invalidas, 1):
                f.write(f"{i}. {cita.texto}\n")
                if cita.razon:
                    f.write(f"   Razón: {cita.razon}\n")
            f.write("\n")
        
        f.write("="*70 + "\n")
        f.write("FIN DEL REPORTE\n")
        f.write("="*70 + "\n")
    
    return str(ruta_reporte)
